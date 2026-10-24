"""Narrow presentation-contract controls, not live acquisition/accuracy proof."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from backend.services.report_builder import ReportBuilder


def test_rejected_capture_stays_inspectable_without_becoming_evidence():
    body = "A captured article with an unknown publication date. " * 10
    data = {"evidence": [], "research_corpus": {
        "raw_candidates": [{"id": "ev_capture", "canonical_url": "https://example.org/article",
            "title": "Captured article", "metadata": {"harvest_acquisition_eligible": True}}],
        "raw_acquisition_pool": {"sources": [{"source_id": "ev_capture", "source_type": "ARTICLE_BODY",
            "readable_text": body, "content_depth": "PARTIAL_CONTENT", "read_status": "SUCCESS",
            "qualification_status": "REJECTED", "qualification_reasons": ["MISSING_PUBLICATION_DATE"]}]}}}
    original = deepcopy(data)
    report = ReportBuilder.from_trending_result(query="sample topic", trend_data=data).to_dict()
    assert sum(len(bucket) for bucket in report["evidence"].values()) == 0
    assert len(report["discovery"]) == 1
    inspection = report["discovery"][0]["extraction"]
    assert inspection["evidentiary_use"] == "DISCOVERY_ONLY"
    assert inspection["read_status"] == "SUCCESS"
    assert inspection["qualification_reasons"] == ["MISSING_PUBLICATION_DATE"]
    assert inspection["captured_text_sha256"] == hashlib.sha256(body.encode()).hexdigest()
    assert data == original


def test_warning_context_is_projected_without_accusing_the_publisher():
    report = ReportBuilder.from_brandshield_result(query="Example", brand_data={
        "assessment_status": "SOURCE_REPORTS_ONLY", "source_assessments": [{
            "evidence_id": "ev_warning", "source_url": "https://example.org/advice",
            "classification": "WARNING_ADVISORY", "actor_url": None, "epistemic_state": "UNVERIFIED"}]}).to_dict()
    observed = report["agent_intelligence"]["source_assessments"][0]
    assert observed["actor_url"] is None
    assert observed["classification"] == "WARNING_ADVISORY"
    assert not any("Submit DMCA" in step for step in report["next_steps"])


def test_reported_quote_and_development_remain_unverified_observations():
    quote = {"evidence_id": "ev_quote", "speaker": "Example Person", "identity_authenticated": False,
             "quotation": {"text": "A source-attributed quotation.", "start": 4, "end": 33}}
    personal = ReportBuilder.from_personal_result(query="Example Person", personal_data={
        "public_statements": [quote], "changes": [{"description": "Initial sample; no prior window."}],
        "timeline": [{"timestamp": "2026-10-20T10:00:00Z", "event_description": "Source-reported quotation"}]}).to_dict()
    assert personal["agent_intelligence"]["public_statements"] == [quote]
    assert personal["changes"] == ["Initial sample; no prior window."]
    assert personal["timeline"][0]["description"] == "Source-reported quotation"
    development = {"title": "Reported deployment", "evidence_id": "ev_article", "published_at": "2026-10-20",
                   "observation_scope": "SOURCE_REPORTED_DEVELOPMENT"}
    trending = ReportBuilder.from_trending_result(query="sample topic", trend_data={
        "recent_developments": [development]}).to_dict()
    assert trending["agent_intelligence"]["recent_developments"] == [development]


def test_empty_trending_report_explains_freshness_and_access_not_absence():
    report = ReportBuilder.from_trending_result(query="sample topic", trend_data={
        "retrieval_trace": {"acquisition_metrics": {"article_bodies": 1, "failed_reads_by_cause": {"HTTP_FAILURE": 2}},
                            "acquisition": {"status": "INSUFFICIENT_EVIDENCE"}},
        "research_corpus": {"raw_acquisition_pool": {"sources": [{"source_id": "old",
            "qualification_reasons": ["TEMPORAL_STALE: older than window"]}]}}}).to_dict()
    assert "48-hour" in report["summary"] and "TEMPORAL_STALE: 1" in report["summary"]
    assert "2 failed read(s)" in report["summary"]
    assert "not current article evidence" in report["summary"]
    assert "absence of new developments" in report["summary"]


@pytest.mark.parametrize("finding_field", ["findings", "findings_structured"])
def test_scout_genuine_passage_is_not_augmented_with_legacy_forecast_headline(finding_field):
    # Genuine Oct21 Infosys excerpt, not a fresh investigation or full article.
    fixture = json.loads((Path(__file__).parents[1] / "fixtures" / "scout_financial_context_2026-10-21.json").read_text(encoding="utf-8"))
    source = deepcopy(fixture["records"][0])
    source["relevant_excerpt"] = source["content"]
    finding = {"finding_id": "current-financial-passage", "statement": source["content"],
        "supporting_evidence_ids": [source["evidence_id"]], "epistemic_state": "UNVERIFIED"}
    data = {finding_field: [finding], "sources": [source],
        "catalysts": {"positive": [{"catalyst": source["title"], "evidence_ids": [source["evidence_id"]]}]}}
    before = deepcopy(data)
    report = ReportBuilder.from_scout_result(query="Infosys", scout_data=data).to_dict()
    assert report["findings"] == [source["content"]]
    assert len(report["finding_details"]) == 1
    assert report["finding_details"][0]["supporting_evidence_ids"] == [source["evidence_id"]]
    assert "FY27 growth seen" not in " ".join(report["findings"])
    assert data == before


@pytest.mark.parametrize("canonical", [[], [{}], [{"statement": ""}]])
def test_scout_legacy_catalyst_fallback_survives_missing_canonical_text(canonical):
    report = ReportBuilder.from_scout_result(query="Example", scout_data={
        "findings": canonical, "catalysts": {"positive": [{"catalyst": "Legacy observed growth"}]}}).to_dict()
    assert report["findings"] == ["positive: Legacy observed growth"]


def test_personal_canonical_passage_does_not_gain_legacy_threat_dictionary_strings():
    passage = "The acquired publisher reports an impersonation allegation; this is not independent proof of a threat."
    report = ReportBuilder.from_personal_result(query="Example Person", personal_data={
        "findings": [{"statement": passage, "supporting_evidence_ids": ["ev_report"], "epistemic_state": "UNVERIFIED"}],
        "threats": [{"threat_type": "IMPERSONATION", "title": "Legacy threat heading", "evidence_ids": ["ev_report"]}]}).to_dict()
    assert report["findings"] == [passage]
    assert report["finding_details"][0]["supporting_evidence_ids"] == ["ev_report"]
