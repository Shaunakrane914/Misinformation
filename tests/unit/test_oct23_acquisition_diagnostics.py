"""Offline telemetry regressions; never a new live-recall/accuracy claim.

Dyson's count/type/reason observations below come from the authorized Oct23
native batch. Bodies/credentials are not copied; miniature article text in
the other controls is synthetic and explicitly separate from that observation.
"""
from copy import deepcopy

import pytest

from backend.application.research.contracts import QueryPlan, ReadEvidence
from backend.schemas.unified_report import UnifiedReport
from backend.services.report_builder import _captured_observation_brief, _complete_agent_report
from backend.services.research.acquisition_status import acquisition_outcome
from backend.services.research.discovery_funnel import build_discovery_funnel, summarize_qualification_decisions
from backend.services.research.research_models import EvidenceItem


def test_navigation_audit_does_not_hide_actual_source_rejections_behind_sample_cap():
    links = [{"parent_id": "home", "url": f"https://publisher.example/navigation/{i}",
              "reason": "SUBJECT_NOT_OBSERVED_IN_LEAD"} for i in range(138)]
    sources = [{"evidence_id": f"source-{i}", "url": f"https://publisher.example/capture/{i}",
                "rejection_stage": "BODY_STRUCTURE", "rejection_reason": "NO_STRUCTURAL_BODY"} for i in range(4)]
    result = summarize_qualification_decisions(links + sources)
    assert result["publisher_link_decision_count"] == 138
    assert result["publisher_link_discard_reasons"] == {"SUBJECT_NOT_OBSERVED_IN_LEAD": 138}
    assert result["rejected_candidate_count"] == 4
    assert result["qualification_decision_count"] == 4
    assert result["qualification_rejection_counts_by_reason"] == {"NO_STRUCTURAL_BODY": 4}
    assert len(result["qualification_rejections"]) == 4
    assert all(row["rejection_stage"] == "BODY_STRUCTURE" for row in result["qualification_rejections"])


def test_repeated_qualification_decisions_are_not_distinct_rejected_sources():
    result = summarize_qualification_decisions([
        {"candidate_id": "one", "url": "https://publisher.example/story#one", "reason": "SUBJECT_MISMATCH"},
        {"candidate_id": "two", "url": "https://publisher.example/story#two", "reason": "SUBJECT_MISMATCH"},
        {"candidate_id": "two", "url": "https://publisher.example/story", "rejection_reason": "NO_RELEVANT_PASSAGE",
         "rejection_stage": "PASSAGE_QUALIFICATION"}])
    assert result["rejected_candidate_count"] == 1
    assert result["qualification_decision_count"] == 3
    assert result["qualification_rejection_counts_by_reason"] == {"SUBJECT_MISMATCH": 1, "NO_RELEVANT_PASSAGE": 1}


def test_missing_identity_remains_a_decision_not_an_invented_source():
    result = summarize_qualification_decisions([{"rejection_stage": "TEMPORAL_GATE_ERROR"},
        {"evidence_id": "accepted", "is_accepted": True}, None])
    assert result["qualification_decision_count"] == 1
    assert result["rejected_candidate_count"] == 0
    assert result["qualification_decisions_without_identity"] == 1


def test_saved_dyson_counts_replay_as_captured_but_unqualified_not_zero_acquisition():
    # Sanitized measurement projection of Oct23's native response; not a live run.
    types = ["PUBLISHER_HOMEPAGE", "SOURCE_INDEX", "PUBLISHER_HOMEPAGE", "DISCOVERY_LEAD"]
    data = {"retrieval_trace": {"acquisition": {"status": "INSUFFICIENT_EVIDENCE"},
        "acquisition_metrics": {"successful_captures": 4, "article_bodies": 0,
            "failed_reads_by_cause": {"PUBLISHER_UNRESOLVED": 3, "PROVIDER_FAILURE": 1}},
        "discovery_funnel": {"raw_capture_count": 4, "successful_body_captures": 0,
            "qualified_evidence": 0, "qualification_rejections": [{"parent_id": "homepage",
                "url": f"https://www.wral.com/navigation/{i}", "reason": "SUBJECT_NOT_OBSERVED_IN_LEAD"}
                for i in range(100)]}},
        "research_corpus": {"raw_acquisition_pool": {"sources": [{"source_id": str(i), "source_type": kind,
            "qualification_reasons": ["Insufficient entity match confidence (0.0 < 0.35)"]}
            for i, kind in enumerate(types)]}}}
    before = deepcopy(data)
    result = _complete_agent_report(UnifiedReport(agent="brandshield", query="Dyson"), data, None, 0)
    assert result.investigation_status == "INSUFFICIENT_EVIDENCE"
    assert "4 raw capture(s)" in result.summary and "0 article body/bodies" in result.summary
    assert "PUBLISHER_UNRESOLVED: 3" in result.summary
    assert "UNSPECIFIED" not in result.summary
    assert not result.findings and not result.evidence.primary
    assert result.processing_notes["discovery_funnel"]["qualification_decision_count"] == 0
    assert result.processing_notes["discovery_funnel"]["publisher_link_decision_count"] == 100
    assert data == before


@pytest.mark.parametrize("agent", ["scout", "brandshield", "trending", "personal_watch"])
def test_all_agents_disclose_raw_capture_count_even_when_no_eligible_sources(agent):
    data = {"retrieval_trace": {"acquisition_metrics": {"successful_captures": 4, "article_bodies": 0},
                               "acquisition": {"status": "COMPLETED"}}}
    result = _complete_agent_report(UnifiedReport(agent=agent, query="Example"), data, None, 0)
    assert "4 raw capture(s)" in result.summary
    assert result.investigation_status == "INSUFFICIENT_EVIDENCE"
    assert result.processing_notes["captured_source_summary"]["displayed_qualified_sources"] == 0


def test_raw_capture_prevents_old_qualified_list_based_acquisition_failure():
    data = {"retrieval_trace": {"acquisition_metrics": {"successful_captures": 1, "article_bodies": 1},
                               "acquisition": {"status": "ACQUISITION_FAILED", "message": "Old filtered-list failure"}}}
    result = _complete_agent_report(UnifiedReport(agent="scout"), data, None, 0)
    assert result.investigation_status == "INSUFFICIENT_EVIDENCE"
    assert result.processing_notes["acquisition"]["reported_status"] == "ACQUISITION_FAILED"
    assert "1 raw capture(s)" in result.summary and "Old filtered-list failure" not in result.summary


def test_report_building_does_not_append_discovery_into_original_ranked_candidates():
    lead = {"id": "lead", "canonical_url": "https://publisher.example/story", "title": "Observed lead",
            "metadata": {"harvest_acquisition_eligible": True}}
    data = {"research_corpus": {"ranked_candidates": [lead], "raw_candidates": [lead],
                               "raw_acquisition_pool": {"sources": []}}}
    before = deepcopy(data)
    _complete_agent_report(UnifiedReport(agent="scout"), data, None, 0)
    assert data == before


def test_empty_after_all_provider_timeouts_remains_acquisition_failure():
    result = acquisition_outcome([{"status": "TIMEOUT"}] * 9, raw_capture_count=0, qualified_count=0)
    assert result["status"] == "ACQUISITION_FAILED"
    assert "9 timeout" in result["message"]
    assert "does not mean no information exists" in result["message"]


@pytest.mark.parametrize("qualified,expected", [(0, "INSUFFICIENT_EVIDENCE"), (1, "COMPLETED")])
def test_successful_capture_and_qualified_evidence_are_separate_outcomes(qualified, expected):
    result = acquisition_outcome([{"status": "SUCCESS"}], qualified, 8, raw_capture_count=4, qualified_count=qualified)
    assert result["status"] == expected and result["raw_capture_count"] == 4
    assert result["qualified_sources"] == qualified


def test_completed_read_does_not_point_back_to_empty_post_read_accepted_list():
    item = EvidenceItem(id="article", canonical_url="https://publisher.example/observed-article", title="Example report",
        content="A synthetic article body that does not support the requested allegation.", content_depth="PARTIAL_CONTENT",
        metadata={"read_success": True}, extraction_status="NO_RELEVANT_PASSAGE")
    read = ReadEvidence([item], {"attempted": 1, "acquisition_attempts": [{"status": "SUCCESS"}]})
    result = build_discovery_funnel(QueryPlan(None, {}, {}), [{"status": "SUCCESS"}], [item], [], [], read, [])
    assert result["first_observed_empty_boundary"] == "BODY_OR_PASSAGE_QUALIFICATION"


def test_read_budget_exhaustion_is_not_called_candidate_rejection():
    item = EvidenceItem(id="lead", canonical_url="https://publisher.example/story")
    read = ReadEvidence([], {"attempted": 0, "read_failure_reason": "READING_DEADLINE_EXHAUSTED"})
    result = build_discovery_funnel(QueryPlan(None, {}, {}), [{"status": "SUCCESS"}], [item], [], [], read, [])
    assert result["first_observed_empty_boundary"] == "READING_BUDGET"


def test_search_url_count_distinguishes_repeated_decision_observations():
    decisions = [{"url": "https://publisher.example/story#one", "discard_reason": "SUBJECT_MISMATCH"},
                 {"url": "https://publisher.example/story#two", "discard_reason": "SUBJECT_MISMATCH"}]
    result = build_discovery_funnel(QueryPlan(None, {}, {}), [{"status": "SUCCESS", "search_attempts": [
        {"decisions": decisions, "response_received": True}]}], [], [], [], ReadEvidence([], {}), [])
    assert result["candidate_urls_observed_in_search_sample"] == 1
    assert result["candidate_url_decision_events_observed_in_search_sample"] == 2


def test_financial_brief_prefers_complete_target_assertion_without_altering_it():
    calendar = "The publisher lists Example Corp among several companies scheduled to host a quarterly webcast next week."
    actual = "Example Corp reported quarterly revenue of USD 12 million, but the publisher says these figures remain unaudited."
    sources = [{"id": key, "canonical_url": "https://publisher.example/" + key,
                "content": text, "content_depth": "PARTIAL_CONTENT"} for key, text in [("calendar", calendar), ("actual", actual)]]
    details = [{"statement": text, "supporting_evidence_ids": [key], "metadata": {"observation_only": True,
        "financial_context": {"content_kind": kind, "financial_assessment_eligible": True,
            "issuer_mention": "Example Corp", "result_scope": "REPORTED_SOURCE_ASSERTION"}}}
        for key, text, kind in [("calendar", calendar, "FINANCIAL_CONTEXT_INCOMPLETE"),
                                ("actual", actual, "FINANCIAL_PERFORMANCE_ASSERTION")]]
    before = deepcopy(details)
    result = _captured_observation_brief({"sources": sources}, details)
    assert actual in result and calendar not in result
    assert "remain unaudited" in result and "not independently verified" in result
    assert details == before
