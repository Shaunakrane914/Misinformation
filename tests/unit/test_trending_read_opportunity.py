"""Offline read-allocation regressions; no live acquisition or AI proof.

The first test uses exact public title/publisher metadata from the saved genuine
2026-10-20 Trending capture. All other source responses are explicitly synthetic.
"""
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from backend.services.agent_reach.channels import RetrievalResult
from backend.services.research.harvesting import (
    HarvestingEngine, _observed_publisher, _read_priority, _unread_wrapper_hubs,
)
from backend.services.research.research_models import EvidenceItem
from backend.services.research.research_profiles import QUICK


def lead(key, title, publisher="https://publisher.test", **metadata):
    return EvidenceItem(id=key, canonical_url="https://news.google.com/rss/articles/" + key,
        title=title, snippet=title, channel="news", published_at=datetime.now(timezone.utc).isoformat(),
        metadata={"publisher_source_url": publisher, "harvest_temporal_priority": 0, **metadata})


def test_genuine_unread_title_beats_arbitrary_hash_before_reading():
    # Exact observed titles/source declarations; neither is an acquired body.
    qnetic = lead("z", "Qnetic testing flywheel to compete with lithium-ion for grid-connected energy storage - pv magazine USA",
                  "https://pv-magazine-usa.com")
    akaysha = lead("a", "Akaysha Energy secures AU$1.75 billion portfolio financing for Australian BESS expansion - Energy-Storage.News",
                   "https://www.energy-storage.news")
    candidates = [akaysha, qnetic]
    candidates.sort(key=lambda item: _read_priority(item, "grid-scale energy storage", "trending", Counter(), Counter()))
    assert candidates[0] is qnetic
    assert not qnetic.acquired_id and not qnetic.content


def test_declared_publisher_hint_diversifies_wrapper_slots_not_independence():
    repeated = lead("a", "thermal energy storage project deployment", "https://one.test")
    unseen = lead("z", "thermal energy storage project deployment", "https://two.test")
    counts = Counter({"one.test": 1})
    assert _read_priority(unseen, "thermal energy storage", "trending", Counter(), counts) < _read_priority(
        repeated, "thermal energy storage", "trending", Counter(), counts)
    assert "source_independence_group" not in unseen.metadata


def test_non_trending_priority_preserves_target_independence_but_diversifies_publishers():
    item = lead("a", "Acme quarterly results")
    before = _read_priority(item, "Acme", "financial", Counter(), Counter())
    assert before == _read_priority(item, "unrelated", "financial", Counter(), Counter())
    # All four domains now share publisher diversity as a tie-breaker, not as
    # relevance evidence. Original fresh/task/article priorities remain first.
    assert before < _read_priority(item, "Acme", "financial", Counter(), Counter({"publisher.test": 9}))


@pytest.mark.parametrize("url", ["https://user:secret@publisher.test", "javascript:bad", "//publisher.test"])
def test_unsafe_publisher_hint_grants_no_identity_or_hub(url):
    item = lead("a", "thermal energy storage", url)
    assert _observed_publisher(item) == "news.google.com"
    assert _unread_wrapper_hubs([item], [], 2) == []


def test_hubs_use_exact_observed_public_root_without_fabricating_attempt():
    item = lead("a", "thermal energy storage", "https://publisher.test")
    hubs = _unread_wrapper_hubs([item], [], 1)
    assert len(hubs) == 1 and hubs[0].canonical_url == "https://publisher.test"
    assert hubs[0].metadata["hub_read_basis"] == "UNREAD_WRAPPER_ALLOWANCE_EXHAUSTED"
    assert not hubs[0].content and not hubs[0].acquired_id
    assert _unread_wrapper_hubs([item], ["https://publisher.test/"], 1) == []


class OfflineService:
    """Synthetic normal-service boundary, no external requests."""
    def __init__(self, pages=None):
        self.pages, self.reads = pages or {}, []

    def retrieve_many(self, plan, **kwargs):
        return RetrievalResult(query="thermal energy storage", domain="trending")

    def read(self, url, max_chars=12_000):
        self.reads.append(url)
        return self.pages.get(url, {"status": "failed", "status_code": 403, "error": "HTTP 403"})


def page(scope="article", links=()):
    return {"status": "success", "markdown": "Thermal energy storage project deployment was announced. " * 40,
            "page_metadata": {"content_scope": scope, "body_quality": {
                "body_kind": "ARTICLE_BODY" if scope == "article" else "UNCLASSIFIED_PAGE"},
                "observed_links": list(links)}}


def test_unread_wrapper_gets_existing_hub_feed_article_slots_after_first_publisher_blocks():
    first = lead("a", "thermal energy storage project deployment", "https://blocked.test")
    second = lead("z", "energy storage project opens", "https://alternate.test")
    feed, article = "https://alternate.test/feed.xml", "https://alternate.test/thermal-storage-opens"
    service = OfflineService({
        "https://alternate.test": page("NEWS_INDEX", [{"url": feed, "text": "News feed", "kind": "FEED_INDEX"}]),
        feed: page("FEED_INDEX", [{"url": article, "text": "Thermal energy storage project deployment"}]),
        article: page(),
    })
    profile = replace(QUICK, max_queries=1, max_discovery_reads=3, host_spacing_seconds=0)
    result = HarvestingEngine(service).run("thermal energy storage", "trending", profile=profile,
                                         initial_candidates=[first, second])
    assert article in service.reads
    assert result.metrics["article_bodies"] == 1
    assert result.metrics["reads_attempted"] == 5 <= profile.max_reads
    attempts = result.read_telemetry["acquisition_attempts"]
    assert sum("news.google.com" in row["url"] for row in attempts) == profile.max_wrapper_reads
    assert not any(row["url"] == second.canonical_url for row in attempts)
    unread = next(item for item in result.candidates if item.canonical_url == second.canonical_url)
    assert unread.metadata["harvest_unread_reason"] == "WRAPPER_READ_BUDGET_EXHAUSTED"


def test_exhausted_wrapper_cap_is_explicitly_unread_not_failed_source():
    candidates = [lead(str(i), "thermal energy storage project", f"https://publisher{i}.test") for i in range(3)]
    profile = replace(QUICK, max_queries=1, max_discovery_reads=0, host_spacing_seconds=0)
    result = HarvestingEngine(OfflineService()).run("thermal energy storage", "trending", profile=profile,
                                                  initial_candidates=candidates)
    assert result.metrics["reads_attempted"] == 1
    assert result.metrics["eligible_candidates_unread"] == 3
    assert result.metrics["unread_by_reason"] == {"WRAPPER_READ_BUDGET_EXHAUSTED": 2,
                                               "DISCOVERY_READ_BUDGET_EXHAUSTED": 1}
    unread = [row for row in result.read_telemetry["candidate_selection_audit"] if row.get("selected") is False]
    assert len(unread) == 3
    assert all(row["selection_decision"] == "NOT_SELECTED" and row["rejection_reason"] is None for row in unread)


def test_no_hub_is_admitted_without_an_article_continuation_slot():
    candidates = [lead(str(i), "thermal energy storage project", f"https://publisher{i}.test") for i in range(2)]
    profile = replace(QUICK, max_queries=1, max_reads=2, host_spacing_seconds=0)
    result = HarvestingEngine(OfflineService()).run("thermal energy storage", "trending", profile=profile,
                                                  initial_candidates=candidates)
    assert result.metrics["reads_attempted"] == 2
    assert len(result.candidates) == 3  # first failed wrapper's already-existing hub path
    assert not any(item.metadata.get("hub_read_basis") for item in result.candidates)


def test_unacquired_feed_wrapper_is_not_primary_or_official_document():
    item = lead("a", "thermal energy storage project", "https://publisher.test")
    item.primary_source = item.official_source = True
    item.source_role, item.source_tier = "PRIMARY", "TIER_1_ORIGINAL_DOCUMENT"
    item.content_depth = "PRIMARY_DOCUMENT"
    item.metadata.update(source_role="PRIMARY", primary_source=True, official_source=True,
                         authority_scope="CORPORATE_DOCUMENT")
    profile = replace(QUICK, max_queries=1, max_reads=1, host_spacing_seconds=0)
    result = HarvestingEngine(OfflineService()).run("thermal energy storage", "trending", profile=profile,
                                                  initial_candidates=[item])
    retained = result.candidates[0]
    assert retained.source_role == "DISCOVERY" and retained.content_depth == "INDEX_SNIPPET"
    assert not retained.primary_source and not retained.official_source
    assert retained.metadata["publisher_identity_verified"] is False
    assert retained.metadata["publisher_source_url"] == "https://publisher.test"
    assert retained.metadata["discovery_source_claims"]["primary_source"] is True
    assert retained.metadata["discovery_source_claims"]["verified"] is False
    audit = result.read_telemetry["candidate_selection_audit"]
    assert all(row.get("selection_reason") != "PRIMARY_DOCUMENT" for row in audit)
