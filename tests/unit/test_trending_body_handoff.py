"""Offline controls for acquired-body handoff and event-passage selection.

All source prose below is synthetic. Fresh live bytes are separately replayed
by the terminal audit; these controls do not establish provider availability.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.agents.trending.models import TrendEvidence
from backend.services.research.passage_extractor import PassageExtractor
from backend.services.research.relevance_gate import RelevanceGate
from backend.services.research.research_models import EvidenceItem


REFERENCE = datetime(2026, 10, 20, 13, tzinfo=timezone.utc)
TOPIC = "thermal energy storage"
PREVIEW = "The pilot has begun testing a new energy storage prototype at a research facility."
BODY = PREVIEW + "\n\n" + (
    "The installation is designed for thermal energy storage at industrial sites. "
    "The publisher reports that testing is underway, not that commercial operation is proven."
)


def native(*, acquired=True, kind="ARTICLE_BODY", date="2026-10-20T11:00:00Z"):
    return TrendEvidence(evidence_id="canonical-native-id", platform="web", source="publisher.test",
        title="Prototype begins pilot testing", url="https://publisher.test/prototype",
        content=BODY, snippet=PREVIEW, published_at=date,
        acquired_candidate_id="native-read-id" if acquired else None,
        metadata={"read_success": acquired, "layer2_eligible": True, "content_depth": "PARTIAL_CONTENT",
                  "relevant_excerpt": PREVIEW,
                  "page_metadata": {"body_quality": {"body_kind": kind}}})


def test_short_preview_cannot_hide_acquired_body_topic_at_specialist_gate():
    item = native()
    gate = RelevanceGate(reference_time=REFERENCE)
    accepted, rejected = gate.filter_candidates([item], TOPIC, domain="trending")
    assert accepted == [item] and not rejected
    assert item.metadata["temporal_status"] == "FRESH"
    assert item.snippet == PREVIEW and item.content == BODY
    assert item.evidence_id == "canonical-native-id"


@pytest.mark.parametrize("change", ["unacquired", "metadata_only", "index", "missing_read_id", "layer2_rejected"])
def test_body_context_does_not_upgrade_unacquired_or_index_leads(change):
    item = native(acquired=change != "unacquired", kind="NEWS_INDEX" if change == "index" else "ARTICLE_BODY")
    if change == "metadata_only":
        item.metadata["content_depth"] = "METADATA"
    if change == "missing_read_id":
        item.acquired_candidate_id = None
    if change == "layer2_rejected":
        item.metadata["layer2_eligible"] = False
    assessment = RelevanceGate(reference_time=REFERENCE).evaluate_item(item, TOPIC, domain="trending")
    assert not assessment.is_accepted


@pytest.mark.parametrize("date,status", [("2026-09-20T11:00:00Z", "STALE"), ("", "MISSING_TIMESTAMP"),
                                        ("2026-10-22T11:00:00Z", "FUTURE_DATED")])
def test_acquired_body_does_not_bypass_publication_gate(date, status):
    assessment = RelevanceGate(reference_time=REFERENCE).evaluate_item(native(date=date), TOPIC, domain="trending")
    assert not assessment.is_accepted and assessment.temporal_status == status


def test_unrelated_body_remains_rejected_despite_valid_acquisition():
    item = native()
    item.content = "A local museum has announced its new pottery exhibition and visitor programme."
    assert not RelevanceGate(reference_time=REFERENCE).evaluate_item(item, TOPIC, domain="trending").is_accepted


def test_current_article_lead_beats_number_heavy_historical_background():
    lead = ("Aster has begun testing its thermal energy storage prototype at an industrial research centre. "
            "Its capacity is expected to reach 200 kWh; these are pilot targets, not proven commercial results.")
    history = ("Historically, thermal energy storage was used in limited facilities. A spokesperson reported "
               "that 400 units were deployed between 2011 and 2014, with 200 units at each site and 20 MW capacity.")
    item = EvidenceItem(id="source", canonical_url="https://publisher.test/prototype", title="Aster begins storage pilot",
        content=lead + "\n\n" + history, content_depth="PARTIAL_CONTENT", published_at="2026-10-20T11:00:00Z",
        metadata={"read_success": True, "temporal_required": True, "temporal_eligible": True})
    PassageExtractor().extract_passages([item], TOPIC, domain="trending")
    assert item.relevant_excerpt == lead
    assert item.content[item.excerpt_start:item.excerpt_end] == lead
    assert "expected" in item.relevant_excerpt
    assert history in item.content  # selection never erases original context


def test_offline_replay_preserves_only_exact_recorded_acquisition_ids():
    from backend.services.research.raw_pool import RawAcquisitionPool
    from scripts.audits.replay_specialist_completion import saved_harvest

    source = EvidenceItem(id="saved-id", canonical_url="https://publisher.test/prototype", title="Pilot article",
        content=BODY, content_depth="PARTIAL_CONTENT", read_status="SUCCESS", acquired_id="actual-saved-read",
        acquisition_attempt_id="actual-saved-attempt", metadata={"read_success": True,
            "page_metadata": {"body_quality": {"body_kind": "ARTICLE_BODY"}}})
    pool = RawAcquisitionPool("saved-pool")
    pool.add_capture(source)
    payload = {"research_corpus": {"raw_acquisition_pool": pool.export(include_text=True),
                                   "deep_read_sources": [source.to_dict()]}}
    restored = saved_harvest(payload).captures[0]
    assert restored.acquired_id == source.acquired_id
    assert restored.acquisition_attempt_id == source.acquisition_attempt_id
    payload["research_corpus"]["deep_read_sources"][0]["content"] = "A different captured body."
    assert not saved_harvest(payload).captures[0].acquired_id


def test_complete_agent_keeps_acquired_body_citation_and_observed_publisher(monkeypatch):
    from backend.agents.trending.agent import TrendingAgent

    source = EvidenceItem(id="canonical-native-id", canonical_url="https://publisher.test/prototype",
        source_domain="publisher.test", channel="web", title="Prototype begins pilot testing", content=BODY,
        relevant_excerpt=PREVIEW, content_depth="PARTIAL_CONTENT", acquired_id="actual-saved-read",
        published_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        metadata={"read_success": True, "layer2_eligible": True,
                  "page_metadata": {"body_quality": {"body_kind": "ARTICLE_BODY"}}})
    monkeypatch.setattr("backend.agents.trending.agent.research_engine.investigate", lambda request:
        SimpleNamespace(telemetry={}, findings=[], contradictions=[], research_corpus={}, evidence=[source]))
    result = TrendingAgent().scan(TOPIC)
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["evidence_id"] == source.id
    assert result["evidence"][0]["source"] == "publisher.test"
    assert result["evidence"][0]["author"] == ""  # transport/publisher is not authorship
    assert result["recent_developments"][0]["evidence_id"] == source.id
    assert result["telemetry"]["popularity_growth_measured"] is False


def test_offline_replay_uses_saved_clock_at_both_body_and_specialist_gates():
    from backend.services.research.raw_pool import RawAcquisitionPool
    from scripts.audits.replay_specialist_completion import replay

    # Explicit synthetic historical capture: fresh only relative to its saved
    # observation, never represented as a newly acquired current article.
    reference = datetime(2020, 1, 2, 12, tzinfo=timezone.utc)
    source = EvidenceItem(id="saved-source", canonical_url="https://publisher.test/prototype",
        source_domain="publisher.test", title="Thermal energy storage pilot begins", channel="web",
        content=BODY, content_depth="PARTIAL_CONTENT", acquired_id="saved-read", read_status="SUCCESS",
        published_at="2020-01-02T10:00:00Z", metadata={"read_success": True,
            "page_metadata": {"published": "2020-01-02T10:00:00Z", "body_quality": {"body_kind": "ARTICLE_BODY"}}})
    pool = RawAcquisitionPool("synthetic-historical-capture")
    pool.add_capture(source)
    payload = {"research_corpus": {"raw_acquisition_pool": pool.export(include_text=True),
                                   "deep_read_sources": [source.to_dict()]}}
    result, _ = replay(payload, "trending", TOPIC, reference_time=reference)
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["published_at"] == source.published_at
    assert result["recent_developments"][0]["evidence_id"] == source.id
