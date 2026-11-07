"""Regression controls for failures observed in the live user journeys."""
import hashlib

import pytest

from backend.services.claim_intelligence.claim_extractor import claim_extractor
from backend.services.claim_intelligence.corroboration import corroboration_detector
from backend.services.claim_intelligence.stance_analysis import stance_analyzer
from backend.services.claim_intelligence.models import StanceType


@pytest.mark.parametrize("query", ["Tim Cook", "AAPL", "Nike", "Shah Rukh Khan", "battery recycling",
    "Find the most recent Tim Cook public statements", "Investigate Nike counterfeit incidents"])
def test_subjects_and_research_instructions_are_not_allegations(query):
    assert claim_extractor.extract_claims(query) == []


def test_real_assertion_keeps_whole_subject():
    claim = claim_extractor.extract_claims("Tim Cook said the device was discontinued", "Tim Cook")[0]
    assert claim.target_entity == "Tim Cook"


def test_announcement_of_different_event_cannot_support_resignation():
    claim = claim_extractor.extract_claims("Tim Cook resigned today", "Tim Cook")[0]
    body = "Tim Cook announced a new application preview at the conference."
    link = stance_analyzer.evaluate_passage(claim, body, "s1", "https://publisher.example/news", "Publisher", body)
    assert link.stance != StanceType.SUPPORTS


def test_exact_offsets_cannot_be_invented_for_normalized_or_missing_text():
    claim = claim_extractor.extract_claims("Nike recalled the shoes", "Nike")[0]
    body = "Nike  recalled the shoes."
    bad = stance_analyzer.evaluate_passage(claim, "Nike recalled the shoes.", "s", "https://publisher.example/a", "Publisher", body)
    assert bad.stance == StanceType.IRRELEVANT
    assert bad.passage_offsets == (-1, -1)
    good = stance_analyzer.evaluate_passage(claim, body, "s", "https://publisher.example/a", "Publisher", body)
    start, end = good.passage_offsets
    assert body[start:end] == good.passage_text
    assert good.captured_text_sha256 == hashlib.sha256(body.encode()).hexdigest()


def test_single_source_and_same_publisher_cannot_become_independent_confirmation():
    summary, _ = corroboration_detector.analyze_sources([
        {"id": "a", "url": "https://publisher.example/a", "snippet": "First reported event."},
        {"id": "b", "url": "https://publisher.example/b", "snippet": "A different reported event."}])
    assert summary.unique_publishers == 1
    assert summary.observed_origin_groups == 1
    assert summary.independent_evidence_chains is None
    assert summary.corroboration_ratio is None
    assert not summary.independence_verified


def test_saved_report_survives_new_connection_and_has_exact_permalink(tmp_path, monkeypatch):
    from backend.db import database
    from backend.services.investigation_history import save_report, get_report, recent_reports
    monkeypatch.setattr(database, "SQLITE_DB_PATH", str(tmp_path / "history.sqlite"))
    original = {"_meta": {"agent": "personal_watch", "query": "Tim Cook"}, "summary": "Attributed reporting", "findings": []}
    saved = save_report(original)
    identifier = saved["_meta"]["investigation_id"]
    assert get_report(identifier) == saved
    assert saved["_meta"]["permalink"] == "/status.html?report=" + identifier
    assert "investigation_id" not in original["_meta"]
    assert recent_reports([]) == []  # no global enumeration of other users' queries
    assert recent_reports([identifier])[0]["query"] == "Tim Cook"
    assert get_report("../etc/passwd") is None


def test_topic_first_objectives_never_become_findings_or_pollute_search():
    from backend.services.research.claim_intelligence import ClaimIntelligenceEngine
    from backend.services.research.research_objectives import discovery_objective
    query = "Indian semiconductor manufacturing developments in the past seven days; show dated reporting and distinguish event dates."
    assert ClaimIntelligenceEngine().decompose_claims(query) == []
    cleaned = discovery_objective(query, "Indian semiconductor manufacturing")
    assert "past seven days" in cleaned and "show dated" not in cleaned
    assert "not" in discovery_objective("Investigate whether Nike did not recall products; preserve not confirmed qualifiers", "Nike")


def test_annual_revenue_cannot_inherit_a_document_quarter():
    from backend.services.research.financial_observations import financial_observations
    text = "For the quarter ended September 26, 2026. Revenue was USD 114.5 billion.\n\nAnnual revenue was USD 479 billion."
    rows = financial_observations(text, "issuer")
    assert rows[0]["period_end"] == "2026-09-26"
    assert rows[1]["period_end"] is None
    assert all(text[row["start"]:row["end"]] == row["text"] for row in rows)


def test_structured_financial_body_survives_reader_pool_and_issuer_qualification(monkeypatch):
    from types import SimpleNamespace
    from backend.services.research.financial_structured import xbrl_document, qualified_document
    from backend.services.research.deep_reader import DeepReader
    from backend.services.research.research_models import EvidenceItem
    from backend.services.research.raw_pool import RawAcquisitionPool
    from backend.services.research.source_registry import source_registry
    url = "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/NetIncomeLoss.json"
    data = {"cik": 320193, "entityName": "Apple Inc.", "tag": "NetIncomeLoss", "taxonomy": "us-gaap",
        "units": {"USD": [{"start": "2026-07-01", "end": "2026-09-30", "val": 100,
            "accn": "0000320193-26-000001", "form": "10-Q", "filed": "2026-11-01", "fy": 2026, "fp": "Q4"}]}}
    body, document = xbrl_document(data, url, "a" * 64)
    response = {"status": "success", "content": body, "content_depth": "STRUCTURED_PUBLIC_DATA",
        "page_metadata": {"content_scope": "STRUCTURED_FINANCIAL_DATA", "financial_document": document}}
    permission = {"eligible": True, "status": "EXISTING_ROUTE_POLICY"}
    monkeypatch.setattr(source_registry, "body_decision", lambda *a, **kw: permission)
    monkeypatch.setattr(source_registry, "robots_decision", lambda *a, **kw: permission)
    monkeypatch.setattr(source_registry, "excerpt_decision", lambda *a, **kw: permission)
    item = EvidenceItem(id="issuer", canonical_url=url, title="Apple financial disclosure", metadata={"candidate_score": .95})
    captured, telemetry = DeepReader().deep_read([item], max_reads=1, service=SimpleNamespace(read=lambda *a, **kw: response))
    assert telemetry["successful"] == 1
    assert captured[0].content_depth == "STRUCTURED_PUBLIC_DATA"
    pool = RawAcquisitionPool("financial-boundary")
    pool.add_capture(captured[0])
    record = pool.get("issuer")
    assert record["source_type"] == "STRUCTURED_PUBLIC_DATA"  # not an article or discovery snippet
    assert record["readable_text"] == body
    assert record["page_metadata"]["financial_document"]["body_sha256"] == hashlib.sha256(body.encode()).hexdigest()
    restored = pool.to_evidence_items()[0]
    assert qualified_document(restored, "Apple")["facts"][0]["value"] == "100"
    from backend.services.research.source_quality import source_quality_engine
    source_quality_engine.classify_and_score(restored, "Apple")
    assert restored.primary_source  # original SEC JSON is primary data, not secondary reporting
    assert qualified_document(restored, "Infosys") is None
    restored.content += " changed"
    assert qualified_document(restored, "Apple") is None
    source_quality_engine.classify_and_score(restored, "Apple")
    assert not restored.primary_source


def test_zero_fit_is_not_authorship_confidence_and_consensus_has_no_model_call():
    import asyncio
    import json
    from backend.services.threat_instruments import compute_mandelbrot_fit
    from backend.api.threat_lab import lab_consensus, ConsensusRequest
    result = compute_mandelbrot_fit("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima")
    assert result["r_squared"] == 0 and result["confidence"] is None
    assert result["verdict"] == "AUTHORSHIP_UNDETERMINED"
    response = asyncio.run(lab_consensus(ConsensusRequest(claim="An unresearched allegation")))
    assert json.loads(response.body)["verdict_scope"] == "NOT_A_FACT_CHECK"


def test_distinct_stories_from_one_host_do_not_become_syndication():
    summary, _ = corroboration_detector.analyze_sources([
        {"id": str(i), "url": f"https://publisher.example/{i}", "body": body}
        for i, body in enumerate(["Alpha beta gamma delta", "Sun moon stars planets", "River lake ocean stream", "Copper silver gold iron"])])
    assert not summary.corroboration_illusion_detected
    assert summary.syndicated_reprints_count == 0


def test_report_scope_uses_executed_trending_window_not_subject_label():
    from backend.services.report_builder import ReportBuilder
    report = ReportBuilder.from_trending_result(query="Semiconductor manufacturing", trend_data={
        "retrieval_trace": {"trending_window_hours": 168}, "sources": []})
    assert "168-hour" in report.summary
    assert "48-hour" not in report.summary
    assert report.processing_notes["task_answer"]["task_passages"] == 0


def test_benchmark_endpoint_is_scoped_and_omits_machine_details():
    import json
    from backend.api.system import published_benchmarks
    result = published_benchmarks()
    assert result["classification"]["test_samples"] == 2948
    assert result["live_research_accuracy"] is None
    assert "filepath" not in json.dumps(result)


@pytest.mark.parametrize("query,body,expected", [
    ("Nike counterfeit incidents", "A religious authority ruled against wearing Nike clothes.", False),
    ("Nike counterfeit incidents", "Nike clothes are popular, although many are counterfeit.\n\nAn institution issued a ruling banning wearing Nike clothing.", False),
    ("Nike counterfeit incidents", "Investigators seized counterfeit Nike shoes from an unauthorized seller.", True),
    ("Nike phishing incidents", "Investigators seized counterfeit Nike shoes.", False),
    ("Nike customer complaints", "I ordered Nike shoes and never received my order or my refund.", True),
    ("Tim Cook misattributed statements", "Tim Cook said the new device was an important milestone in an interview.", False),
    ("Tim Cook public statements", "Tim Cook said the new device was an important milestone in an interview.", True),
])
def test_source_bodies_must_address_explicit_specialist_task(query, body, expected):
    from backend.services.research.research_models import EvidenceItem
    from backend.services.research.specialist_planning import matches_specialist_body
    personal = query.startswith("Tim")
    item = EvidenceItem(id="actual-capture", content=body, content_depth="PARTIAL_CONTENT")
    assert matches_specialist_body(item, query, "Tim Cook" if personal else "Nike", "personal" if personal else "brand") is expected
