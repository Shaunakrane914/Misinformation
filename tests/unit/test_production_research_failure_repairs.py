"""October production failures: synthetic offline controls, not live proof."""
import time
from unittest.mock import MagicMock, patch

import pytest

from backend.services.research.deep_reader import DeepReader
from backend.services.research.research_models import EvidenceItem, ResearchRequest
from backend.services.report_builder import ReportBuilder


def candidate(code, *, url=None, title=None, **kwargs):
    return EvidenceItem(id=code, canonical_url=url or f"https://publisher.example/{code}",
                        title=title or "ExampleCo counterfeit seizure report",
                        source_domain="publisher.example", relevance_score=0.8,
                        source_quality_score=0.8, **kwargs)


def test_expired_source_wait_cannot_launch_search_in_clock_rounding_sliver():
    from backend.infrastructure.acquisition.service import AgentReachService
    from backend.services.agent_reach.native.operation_capabilities import RuntimeOperationCapabilities
    service = AgentReachService()
    search = MagicMock()
    service.registry.get_channel("news").search = search
    executor = MagicMock()
    # Simulate a platform wait timing out while monotonic still has time left.
    executor.submit.return_value.result.side_effect = TimeoutError()
    with patch("backend.infrastructure.acquisition.service.concurrent.futures.ThreadPoolExecutor", return_value=executor), \
         patch("backend.infrastructure.acquisition.service.runtime_operation_capabilities", RuntimeOperationCapabilities()):
        result = service.retrieve_many({"news": ["topic"]}, source_url="https://publisher.example/report", timeout=1)
    search.assert_not_called()
    assert result.source_article["status"] == "failed"
    assert result.query_records[0].status == "NOT_SUBMITTED"
    assert result.query_records[0].provider_started is False


def test_unresolved_wrappers_are_not_one_publisher_quota():
    items = [candidate(str(i), url=f"https://news.google.com/rss/articles/{i}",
                       query_class="counterfeit") for i in range(6)]
    for item in items:
        item.source_domain = "news.google.com"
    selected, _ = DeepReader()._select_read_candidates(items, max_reads=6)
    assert len(selected) == 6
    assert {item.source_domain for item in items} == {"news.google.com"}


def test_objective_matches_cannot_be_displaced_by_different_query_class():
    incident = [candidate(str(i), query_class="counterfeit", metadata={"objective_read_match": True}) for i in range(3)]
    stock = candidate("stock", title="ExampleCo stock falls", query_class="market",
                      metadata={"objective_read_match": False, "defer_non_objective_read": True})
    selected, _ = DeepReader()._select_read_candidates(incident + [stock], max_reads=4)
    assert stock not in selected


@pytest.mark.parametrize("result,kind", [
    ({"status": "error", "error": "timed out https://example.com/?token=SECRET"}, "TIMEOUT"),
    ({"status": "blocked_ssrf", "error": "private network"}, "ACCESS_REJECTED"),
    ({"status": "failed", "runtime_decision": {"decision": "EXCLUDE"}}, "ACCESS_REJECTED"),
    ({"status": "failed", "error": "HTTP 403 forbidden"}, "HTTP_FAILURE"),
    ({"status": "success", "markdown": ""}, "EMPTY_EXTRACTION"),
    ({"status": "success", "markdown": "Verify you are human. Complete the CAPTCHA before proceeding."}, "CHALLENGE_PAGE"),
])
def test_failed_reads_explain_category_without_retaining_secret(result, kind):
    from backend.services import agent_reach
    with patch.object(agent_reach.agent_reach_service, "read", return_value=result):
        records, telemetry = DeepReader().deep_read([candidate("a")], max_reads=1, timeout_per_read=1)
    assert not records
    attempt = telemetry["acquisition_attempts"][0]
    assert attempt["failure_kind"] == kind
    assert "SECRET" not in str(attempt)
    assert attempt["useful_content_extracted"] is False


def test_replacements_use_remaining_attempt_budget_not_new_unbounded_retries():
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_budget import ResearchBudget
    from backend.services import agent_reach
    items = [candidate(str(i)) for i in range(5)]
    calls = []
    def read(url, **kwargs):
        calls.append(url)
        if url.endswith(("/0", "/1")):
            return {"status": "failed", "error": "HTTP 503"}
        return {"status": "success", "markdown": "ExampleCo counterfeit goods were seized, according to the captured agency report. This is an allegation requiring review."}
    with patch.object(agent_reach.agent_reach_service, "read", side_effect=read):
        result = DeepReadingStage().run(ResearchRequest(target="ExampleCo", domain="brand", deep_read_budget=4),
            ResearchBudget(deep_read_budget=4), RankedEvidence(items, items, {}, []), time.monotonic(), 30)
    assert result.investigated
    assert len(calls) <= 4 and len(calls) == len(set(calls))
    assert result.telemetry["replacement_read_rounds"] >= 1
    assert result.telemetry["attempted"] == len(calls)
    assert all(item.acquired_id and item.acquisition_attempt_id for item in result.investigated)


def test_resolution_failure_keeps_bounded_rejection_observations():
    from backend.services.agent_reach.channels import EvidenceFragment, RetrievalResult
    item = candidate("w", url="https://news.google.com/rss/articles/opaque", title="ExampleCo counterfeit products seized in warehouse")
    service = MagicMock()
    service.retrieve_many.return_value = RetrievalResult(query="q", domain="brand", fragments=[
        EvidenceFragment(platform="web", title="Unrelated product launch", url="https://other.example/a?token=SECRET")])
    url, trace = DeepReader()._resolve_wrapper(item, service)
    assert url is None
    assert trace["candidates"][0]["rejection_reason"] == "TITLE_MISMATCH"
    assert "SECRET" not in str(trace["candidates"])


def test_headline_disagreement_is_not_established_contradiction():
    from backend.services.research.contradiction_detector import ContradictionDetector
    a = candidate("a", title="ExampleCo acquisition battery startup talks")
    b = candidate("b", title="ExampleCo denies battery startup acquisition rumors")
    rows = ContradictionDetector().detect_contradictions([a, b], "ExampleCo")
    assert rows and rows[0]["type"] == "POSSIBLE_DISAGREEMENT"
    assert rows[0]["established"] is False
    assert not a.contradiction_flag and not b.contradiction_flag


def test_disagreement_preserves_exact_captured_passage_references():
    from backend.services.research.contradiction_detector import ContradictionDetector
    a = candidate("a", title="ExampleCo battery startup acquisition", content_depth="PARTIAL_CONTENT",
                  content="ExampleCo is in talks to acquire the battery startup, according to the publisher's report.")
    b = candidate("b", title="ExampleCo denies battery startup acquisition", content_depth="PARTIAL_CONTENT",
                  content="ExampleCo denies it is in talks to acquire the battery startup, according to its statement.")
    rows = ContradictionDetector().detect_contradictions([a, b], "ExampleCo")
    refs = rows[0]["passage_references"]
    assert {ref["evidence_id"] for ref in refs} == {"a", "b"}
    for ref in refs:
        item = a if ref["evidence_id"] == "a" else b
        assert item.content[ref["start"]:ref["end"]] == ref["text"]
    assert rows[0]["claim_support_verified"] is False


def test_scout_context_headings_do_not_become_disagreements():
    report = ReportBuilder.from_scout_result(query="ExampleCo", scout_data={
        "contradictions": {"for": ["Revenue grew"], "against": ["Shares fell"], "unresolved": ["Annual reports"]}})
    assert not report.disagreements and not report.detailed_contradictions


def test_personal_changes_are_readable_not_dictionary_repr():
    report = ReportBuilder.from_personal_result(query="Public Person", personal_data={
        "changes": [{"change_type": "BASELINE_INITIALIZED", "description": "Initial sample baseline established.", "severity": "INFO"}]})
    assert report.changes == ["Initial sample baseline established."]


def test_adaptive_queries_preserve_specialist_objective():
    from backend.services.agent_reach.planner import RetrievalPlanner
    planner = RetrievalPlanner()
    for domain, target in (("brand", "ExampleCo"), ("personal", "Public Person")):
        queries = planner.plan_adaptive_follow_ups(target, evidence_items=[{"title": "Amid Hype New Product"}],
                                                   domain=domain, intent="Investigate impersonation", max_follow_ups=2)
        assert queries and all("announcement statement partnership" not in q["query_text"] for q in queries)
        assert any("impersonation" in q["query_text"] or "deepfake" in q["query_text"] for q in queries)


def test_successful_body_retains_ids_and_public_attribution_conflict():
    from backend.services import agent_reach
    from backend.schemas.evidence_inspection import public_capture_metadata
    item = candidate("canonical", source_name="Feed attribution")
    body = "ExampleCo counterfeit goods were seized, according to the attributable captured report."
    with patch.object(agent_reach.agent_reach_service, "read", return_value={
            "status": "success", "markdown": body, "page_metadata": {"author": "Captured byline"}}):
        records, telemetry = DeepReader().deep_read([item], max_reads=1, timeout_per_read=1)
    assert records[0].id == "canonical" and records[0].content == body
    assert telemetry["acquisition_attempts"][0]["failure_kind"] is None
    source = item.to_dict()
    source["metadata"] = public_capture_metadata(item)
    report = ReportBuilder.from_scout_result(query="ExampleCo", scout_data={"sources": [source]})
    shared = report.to_dict()["evidence"]["independent"][0]
    assert shared["evidence_id"] == "canonical"
    assert shared["source"]["name"] == "Captured byline"
    assert shared["source"]["discovery_attribution"] == "Feed attribution"
    assert shared["source"]["attribution_conflict"] is True


def test_expired_read_stage_does_not_open_new_read():
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_budget import ResearchBudget
    from backend.services import agent_reach
    items = [candidate("pending")]
    with patch.object(agent_reach.agent_reach_service, "read") as read:
        result = DeepReadingStage().run(ResearchRequest(target="ExampleCo", domain="brand"),
            ResearchBudget(), RankedEvidence(items, items, {}, []), time.monotonic() - 10, 1)
    read.assert_not_called()
    assert not result.investigated
    assert result.telemetry["read_failure_reason"] == "READING_DEADLINE_EXHAUSTED"


def test_completed_discovery_with_starved_reading_is_acquisition_failure():
    from backend.services.research.acquisition_status import acquisition_outcome
    outcome = acquisition_outcome([{"status": "SUCCESS"}], 0, 0, "READING_DEADLINE_EXHAUSTED")
    assert outcome["status"] == "ACQUISITION_FAILED"
    assert "before a source read could start" in outcome["message"]


def test_empty_trending_cannot_infer_stable_public_attention(monkeypatch):
    from backend.agents.trending.agent import TrendingAgent
    agent = TrendingAgent()
    monkeypatch.setattr(agent, "scan_trends", lambda **kwargs: {"evidence": [], "trends": [
        {"topic": "An allegation", "velocity": {"label": "STABLE"}}]})
    report = agent.generate_trending_intelligence("Example Subject")
    assert not report["inferred"]
    assert any("UNASSESSED" in text for text in report["uncertain"])


@pytest.mark.parametrize("agent,method,key", [
    ("scout", "from_scout_result", "scout_data"),
    ("trending", "from_trending_result", "trend_data"),
    ("brandshield", "from_brandshield_result", "brand_data"),
    ("personal_watch", "from_personal_result", "personal_data"),
])
def test_all_failed_reads_remain_explicit_at_every_shared_agent_boundary(agent, method, key):
    data = {"findings": ["Unsupported legacy finding"], "deep_research_trace": {
        "deep_read_attempted": 1, "query_records": [{"status": "TIMEOUT", "channel": "web"}]}}
    report = getattr(ReportBuilder, method)(query="Example Subject", **{key: data})
    assert report.investigation_status == "ACQUISITION_FAILED"
    assert not report.findings and not report.agent_intelligence
