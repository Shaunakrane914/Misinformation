"""Synthetic offline controls, not live retrieval/accuracy evidence."""
from datetime import datetime, timezone
from unittest.mock import patch
import pytest

from backend.services.research.research_models import EvidenceItem, ResearchRequest
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.harvesting import HarvestResult
from backend.application.research.harvest_pipeline import run_harvest_pipeline


def capture(subject="Cedar Instruments"):
    body = (f"{subject} reported quarterly revenue of USD 14 million and operating profit of USD 2 million. "
            "The company said these unaudited figures cover the June quarter, not the full year.")
    return EvidenceItem(id="original_native_id", canonical_url="https://publisher.example/report/earnings",
        title=subject + " reports quarterly earnings", content=body, snippet=subject + " preview",
        content_depth="PARTIAL_CONTENT", read_status="SUCCESS", acquisition_attempt_id="attempt1",
        acquired_id="capture1", published_at=datetime.now(timezone.utc).isoformat(),
        metadata={"read_success": True, "page_metadata": {"content_scope": "article", "body_quality": {"body_kind": "ARTICLE_BODY"}}})


def harvest(item):
    return HarvestResult(candidates=[item], captures=[item], metrics={"halt_reason": "CONTROL"},
        read_telemetry={"attempted": 1, "successful": 1, "total_chars_read": len(item.content),
                        "acquisition_attempts": [{"candidate_id": item.id, "url": item.canonical_url, "status": "SUCCESS"}]})


@pytest.mark.parametrize("domain", ["financial", "brand", "personal", "trending"])
def test_all_specialists_share_raw_pool_without_fabricating_findings(domain):
    item = capture()
    with patch("backend.services.research.harvesting.HarvestingEngine.run", return_value=harvest(item)), \
         patch("backend.application.research.assembly.DossierRegistrationStage.run"):
        result = run_harvest_pipeline(ResearchRequest(target="Cedar Instruments", domain=domain),
                                     ResearchBudget(timeout_seconds=30, deep_read_budget=12), "STANDARD")
    pool = result.research_corpus["raw_acquisition_pool"]
    source = pool["sources"][0]
    assert source["source_id"] == "original_native_id"
    assert source["readable_text"] == item.content
    assert result.telemetry["research_profile"] == "STANDARD"
    assert result.telemetry["acquisition_metrics"]["article_bodies"] == 1
    if domain in {"brand", "personal"}:
        assert not result.findings  # Earnings are not a counterfeit/identity incident.
        assert result.telemetry["acquisition"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_body_subject_mismatch_cannot_reuse_a_favorable_discovery_title():
    item = capture("Unrelated Metals")
    item.title = "Cedar Instruments earnings announcement"
    with patch("backend.services.research.harvesting.HarvestingEngine.run", return_value=harvest(item)), \
         patch("backend.application.research.assembly.DossierRegistrationStage.run"):
        result = run_harvest_pipeline(ResearchRequest(target="Cedar Instruments", domain="financial"),
                                     ResearchBudget(timeout_seconds=30), "STANDARD")
    # Even if a headline passes the entity gate, no captured target paragraph
    # supports the agent objective, so it cannot become a usable finding.
    assert not result.findings
    assert result.telemetry["acquisition_metrics"]["qualified_source_count"] == 0


def test_request_budget_counts_retries_redirects_and_closes_late_workers():
    from backend.infrastructure.acquisition.network.budget import PublicRequestBudget, public_request_budget, reserve_public_request
    budget = PublicRequestBudget(total=3, per_host=2)
    with public_request_budget(budget):
        reserve_public_request("https://one.example/a")
        reserve_public_request("https://one.example/b")
        with pytest.raises(TimeoutError):
            reserve_public_request("https://one.example/c")
        reserve_public_request("https://two.example/a")
        with pytest.raises(TimeoutError):
            reserve_public_request("https://three.example/a")
        budget.close()
        with pytest.raises(TimeoutError):
            reserve_public_request("https://two.example/b")
    assert budget.snapshot()["native_http_admissions"] == 3


def test_profile_context_is_request_local_and_reset_on_error():
    from backend.api.agents import _run_bounded_scan
    from backend.application.research.progress import requested_research_profile
    assert _run_bounded_scan("scout", requested_research_profile.get, "DEEP") == "DEEP"
    assert requested_research_profile.get() is None
    with pytest.raises(RuntimeError):
        _run_bounded_scan("scout", lambda: (_ for _ in ()).throw(RuntimeError()), "QUICK")
    assert requested_research_profile.get() is None


def test_raw_homepage_survives_buffer_but_never_reaches_specialist_inputs():
    article = capture()
    home = capture()
    home.id, home.canonical_url = "homepage", "https://store.example/"
    home.content = "Cedar Instruments profit scam giveaway shop all contact us privacy policy."
    raw = harvest(article)
    raw.candidates.append(home)
    raw.captures.append(home)
    with patch("backend.services.research.harvesting.HarvestingEngine.run", return_value=raw), \
         patch("backend.application.research.assembly.DossierRegistrationStage.run"):
        result = run_harvest_pipeline(ResearchRequest(target="Cedar Instruments", domain="financial"),
                                     ResearchBudget(timeout_seconds=30), "STANDARD")
    assert [item.id for item in result.evidence] == ["original_native_id"]
    assert len(result.research_corpus["raw_acquisition_pool"]["sources"]) == 2
    assert result.telemetry["discovery_funnel"]["qualified_evidence"] == 1
    assert result.telemetry["discovery_funnel"]["extracted_article_bodies"] == 1
    assert all("homepage" not in finding.supporting_evidence_ids for finding in result.findings)


def test_legitimate_promotional_reporting_is_not_brand_risk_evidence():
    from backend.services.research.content_roles import matches_objective
    assert not matches_objective("Cedar announced a collaboration with a legitimate promotional sweepstakes and an exclusive giveaway.", "brand")
    assert matches_objective("Cedar giveaway impersonators ask victims to send bitcoin to receive double the amount.", "brand")
    assert matches_objective("Cedar warns that a fake giveaway steals passwords.", "brand")


def test_multiple_pipeline_scopes_inside_one_api_scan_share_advisory_identity():
    from backend.api.agents import _run_bounded_scan
    from backend.infrastructure.llm.advisory_policy import _investigation, investigation_scope
    def scan():
        parent = _investigation.get()
        assert parent
        with investigation_scope():
            first = _investigation.get()
        with investigation_scope():
            second = _investigation.get()
        assert first == second == parent
        return parent
    assert _run_bounded_scan("scout", scan)
    assert _investigation.get() is None
