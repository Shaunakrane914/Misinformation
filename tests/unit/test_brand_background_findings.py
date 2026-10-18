"""Background captures remain inspectable but are not invented findings."""
from backend.agents.brandshield.agent import BrandShieldAgent
from backend.services.report_builder import ReportBuilder


def test_catalog_is_background_not_genuine_issue_or_safe(monkeypatch):
    agent = BrandShieldAgent()
    evidence = [{"evidence_id": "catalog", "platform": "Web", "title": "Nike Cyclone shoes",
        "snippet": "Shop all shoes. Add to cart. Privacy policy.", "content": "Shop all shoes. Add to cart. Privacy policy.",
        "url": "https://example.org/shop", "content_depth": "PARTIAL_CONTENT"}]
    monkeypatch.setattr(agent, "search_brand_evidence", lambda *a: (evidence, {}, {}, 0))
    monkeypatch.setattr(agent, "_synthesize_brand_threats", lambda *a: {"threats": []})
    result = agent.scan("Nike")
    assert result["findings"] == []
    assert result["total_findings"] == result["safe_count"] == 0
    assert result["safety_assessment"] == "NOT_ESTABLISHED"
    assert result["background_evidence_ids"] == ["catalog"]
    assert result["evidence"] == evidence
    report = ReportBuilder.from_brandshield_result(query="Nike", brand_data=result)
    assert report.findings == []
    assert sum(len(bucket) for bucket in (report.evidence.primary, report.evidence.independent, report.evidence.community)) == 1
    assert report.processing_notes["specialist_coverage"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert "not a finding or proof of safety" in report.summary
    assert not any("Submit DMCA" in step for step in report.next_steps)


def test_profile_only_report_has_specific_gap_and_observed_lead():
    result = {"summary": {"sources_scanned": 1}, "evidence": [{
        "evidence_id": "profile", "title": "Profile", "content": "Short public biography",
        "url": "https://x.com/person", "content_depth": "PROFILE_METADATA"}],
        "research_corpus": {"ranked_candidates": [{"id": "lead", "title": "Public Person deepfake report",
            "canonical_url": "https://publisher.example/report", "content_depth": "INDEX_SNIPPET"}]},
        "retrieval_trace": {"acquisition_attempts": [{"status": "FAILED"}]}}
    report = ReportBuilder.from_personal_result(query="Public Person", personal_data=result)
    assert report.findings == []
    coverage = report.processing_notes["specialist_coverage"]
    assert coverage["status"] == "INSUFFICIENT_EVIDENCE"
    assert coverage["profiles"] == coverage["failed_reads"] == coverage["discovery_only"] == 1
    assert coverage["task_text_candidates"] == 0
    assert "1 profile(s)" in report.summary
    assert "Public Person deepfake report" in report.next_steps[0]
    assert "not confirmation" in report.next_steps[0]
