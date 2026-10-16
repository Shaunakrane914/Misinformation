"""Controlled regressions from observed failures, not held-out accuracy claims."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.application.research.synthesis import synthesize_grounded_findings
from backend.services.research.passage_extractor import passage_extractor
from backend.services.research.research_models import EvidenceItem, ResearchRequest
from backend.schemas.unified_report import QueryTelemetry
from backend.agents.personal_watch.monitoring import normalize_item
from backend.agents.brandshield.scanning import search_brand_evidence


def record(text, depth="PARTIAL_CONTENT", url="https://example.org/announcement"):
    return EvidenceItem(id="canonical-1", title="Example announcement", content=text, snippet=text,
                        canonical_url=url, channel="web", content_depth=depth,
                        query_class="general_news", source_name="Example", source_role="SECONDARY")


@pytest.mark.parametrize("text,depth", [
    ("Example Store Home Men Women Kids Shop All New Arrivals Toggle navigation Privacy Policy Contact Us", "PARTIAL_CONTENT"),
    ("Example chief executive officer", "PROFILE_METADATA"),
    ("Example announced a product recall", "SEARCH_SNIPPET"),
])
def test_navigation_metadata_and_search_snippets_cannot_be_supported_findings(text, depth):
    item = record(text, depth)
    passage_extractor.extract_passages([item], "Example", "investigate product announcements")
    assert synthesize_grounded_findings("Example", "brand", [item], []) == []


def test_real_announcement_body_still_produces_cited_observation():
    item = record("Example announced a recall of Widget batteries on 15 October 2026 after reports of overheating.")
    passage_extractor.extract_passages([item], "Example", "investigate product recall")
    findings = synthesize_grounded_findings("Example", "brand", [item], [])
    assert findings and findings[0].supporting_evidence_ids == ["canonical-1"]
    assert findings[0].epistemic_state == "UNVERIFIED"
    assert findings[0].metadata["citation_entailment_verified"] is False


def test_personal_normalization_preserves_canonical_id():
    item = normalize_item({"evidence_id":"canonical-1", "url":"https://example.org/announcement", "title":"Example"},
                          "Web", "SECONDARY", "Example")
    assert item["evidence_id"] == "canonical-1"


def test_brand_normalization_preserves_canonical_id():
    item = record("Example announced a product recall following a battery investigation.")
    result = SimpleNamespace(evidence=[item],telemetry={"channel_health":{}})
    from backend.services.research import research_engine
    with patch.object(research_engine,"investigate",return_value=result):
        records, _, _, _, _ = search_brand_evidence({"brand":"Example","resolved_entity":"Example"})
    assert records[0]["evidence_id"] == "canonical-1"


def test_skipped_query_is_not_a_submitted_query():
    telemetry = QueryTelemetry.from_execution_log([{"status":"SUCCESS"},{"status":"SKIPPED"},{"status":"PLANNED"}])
    assert telemetry.queries_submitted == 1
    assert telemetry.queries_started == 1
    assert telemetry.queries_skipped == 1


def test_tata_safety_notice_is_not_an_attacker_signal():
    from backend.agents.brandshield.assessment import heuristic_threat_synthesis
    notice = {"evidence_id":"notice", "platform":"web", "title":"Tata group careers", "url":"https://www.tata.com/",
              "source":"Tata", "source_role":"DISCOVERY", "source_tier":"TIER_3_AGGREGATE", "content_depth":"PARTIAL_CONTENT",
              "content":"Beware of Job Scams. We do not charge or accept any security deposit from job seekers. Read our disclaimer.",
              "snippet":"Beware of Job Scams.", "published_at":""}
    result = heuristic_threat_synthesis({"brand":"Tata Motors","resolved_entity":"Tata Motors"}, [notice])
    assert not any(t.get("type") == "PHISHING_SCAM" for t in result["threats"])


def test_broad_discovery_reserves_read_and_synthesis_time():
    from backend.application.research.acquisition import BroadDiscoveryStage
    from backend.application.research.contracts import QueryPlan
    from backend.services.research.research_budget import ResearchBudget
    plan = QueryPlan(planner=None,channel_queries={"web":[{"query_text":"Example recall"}]},query_classes=[])
    with patch("backend.services.agent_reach.agent_reach_service.retrieve_many") as retrieve:
        BroadDiscoveryStage().run(ResearchRequest(target="Example"),ResearchBudget(timeout_seconds=20),15,plan)
    assert retrieve.call_args.kwargs["timeout"] <= 6.75


def test_direct_filing_is_read_before_corporate_landing():
    from backend.services.research.source_quality import source_quality_engine
    from backend.services.research.deep_reader import DeepReader
    landing = record("Apple store navigation and product categories", url="https://apple.com/")
    filing = record("Apple reported quarterly earnings in its Form 10-Q.", url="https://sec.gov/Archives/filing.htm")
    filing.id = "filing"
    for item in (landing, filing):
        source_quality_engine.classify_and_score(item, "Apple (AAPL)")
        item.relevance_score = 0.8
    selected, _ = DeepReader()._select_read_candidates([landing, filing], max_reads=1)
    assert selected[0].id == filing.id
    assert landing.official_source and not landing.primary_source
    assert landing.metadata["authority_scope"] == "CORPORATE_LANDING"


def test_scout_model_cannot_invent_citations_or_declare_low_risk():
    from backend.services.research.model_grounding import constrain_financial_extractions
    parsed = {"catalysts": {"positive": [{"catalyst": "Invented earnings", "evidence_ids": ["fake"]},
                                       {"catalyst": "Cited observation", "evidence_ids": ["real"]}]},
              "misinformation": {"status": "NOMINAL", "manipulation_risk": "LOW"},
              "risks": ["Uncited assertion"]}
    result = constrain_financial_extractions(parsed, [{"evidence_id": "real"}])
    assert len(result["catalysts"]["positive"]) == 1
    assert result["catalysts"]["positive"][0]["citation_entailment_verified"] is False
    assert result["misinformation"]["manipulation_risk"] == "UNASSESSED"
    assert result["risks"] == []


def test_escalation_cannot_spend_reserved_read_time():
    from backend.application.research.reading import PrimaryEscalationStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.research.research_budget import ResearchBudget
    ranked = RankedEvidence(accepted=[], ranked=[], clusters={}, rejected=[])
    with patch("backend.application.research.reading.time.time", return_value=107), \
            patch("backend.services.research.primary_source_escalator.primary_source_escalator.escalate") as escalate:
        result = PrimaryEscalationStage().run(ResearchRequest(target="Example"), ResearchBudget(), ranked, 100, 15)
    escalate.assert_not_called()
    assert result.primaries == []


def test_exact_claim_not_purpose_boilerplate_reaches_source_planner():
    from backend.application.research.acquisition import QueryPlanningStage
    exact = 'Example did not announce "Widget 9" in 2025.'
    request = ResearchRequest(target="Example", intent="Detect phishing and deepfakes across all networks",
                              extra_params={"claim_text": exact})
    with patch("backend.services.agent_reach.source_planner.source_planning_engine.plan") as plan:
        plan.return_value.channels = []
        QueryPlanningStage().run(request)
    assert plan.call_args.args[0] == exact
    assert plan.call_args.kwargs["entity"] == "Example"


def test_personal_entity_scan_keeps_identity_intent_without_boilerplate_query():
    from backend.services.agent_reach.source_planner import SourcePlanningEngine
    assert SourcePlanningEngine._classify_intent("Sam Altman", "personal") == "identity_attribution"
    assert SourcePlanningEngine._classify_intent("Example quarterly revenue", "financial") == "financial_integrity"


def test_parent_group_does_not_substitute_for_requested_issuer():
    item = record("Tata announced a new Air India route and is investing in airline facilities.")
    passage_extractor.extract_passages([item], "Tata Motors (TATAMOTORS.NS)", "financial results")
    assert item.extraction_status == "NO_RELEVANT_PASSAGE"
    assert synthesize_grounded_findings("Tata Motors", "financial", [item], []) == []


@pytest.mark.parametrize("domain", ["financial", "trending", "brand", "personal"])
def test_specialist_claim_runs_shared_assessment_and_preserves_citations(domain):
    from backend.application.research.synthesis import GroundedSynthesisStage
    from backend.application.research.contracts import RankedEvidence, ReadEvidence
    from backend.services.research.source_quality import source_quality_engine
    item = record("Apple revenue was $10 billion in 2025.", url="https://apple.com/newsroom/results")
    source_quality_engine.classify_and_score(item, "Apple")
    ranked = RankedEvidence(accepted=[item], ranked=[item], clusters={}, rejected=[])
    request = ResearchRequest(target="Apple", domain=domain,
                              extra_params={"claim_text": "Apple revenue was $50 billion in 2025."})
    analysis = GroundedSynthesisStage().run(request, ranked, ReadEvidence([item], {}))
    finding = analysis.findings[0]
    assert finding.epistemic_state == "REFUTED"
    assert finding.contradicting_evidence_ids == ["canonical-1"]
    assert finding.metadata["claim_assessment"]["evidence_citations"][0]["relevant_excerpt"] in item.content


def test_claim_without_acquired_evidence_abstains_not_ranked_candidate_support():
    from backend.application.research.synthesis import GroundedSynthesisStage
    from backend.application.research.contracts import RankedEvidence, ReadEvidence
    item = record("Apple revenue was $50 billion in 2025.", depth="SEARCH_SNIPPET")
    ranked = RankedEvidence(accepted=[item], ranked=[item], clusters={}, rejected=[])
    request = ResearchRequest(target="Apple", extra_params={"claim_text": item.content})
    finding = GroundedSynthesisStage().run(request, ranked, ReadEvidence([], {})).findings[0]
    assert finding.metadata["claim_assessment"]["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert not finding.supporting_evidence_ids


def test_user_supplied_body_survives_qualification_without_duplicate_read():
    from backend.application.research.acquisition import CandidateQualificationStage
    from backend.application.research.reading import DeepReadingStage
    from backend.application.research.synthesis import GroundedSynthesisStage
    from backend.application.research.contracts import RankedEvidence
    from backend.services.agent_reach.channels import RetrievalResult
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.report_builder import ReportBuilder
    text = "Apple revenue was $10 billion in 2025, according to the quarterly results announcement."
    request = ResearchRequest(target="Apple", domain="financial", source_url="https://apple.com/newsroom/results",
                              extra_params={"claim_text": "Apple quarterly revenue was $50 billion in 2025."})
    retrieval = RetrievalResult(query="Apple", domain="financial", fragments=[], source_article={
        "status": "success", "url": request.source_url, "title": "Apple quarterly results", "markdown": text})
    discovery = CandidateQualificationStage().run(request, retrieval)
    assert len(discovery.accepted) == 1
    ranked = RankedEvidence(discovery.accepted, discovery.accepted, {}, discovery.rejected)
    with patch("backend.services.research.deep_reader.deep_reader.deep_read") as reader:
        read = DeepReadingStage().run(request, ResearchBudget(), ranked, 0, 0)
    reader.assert_not_called()
    assert read.investigated[0].content == text
    assert read.telemetry["reused_acquired_count"] == 1
    findings = GroundedSynthesisStage().run(request, ranked, read).findings
    assert findings[0].metadata["claim_assessment"]["verdict"] == "REFUTED"
    report = ReportBuilder.from_scout_result(query=request.target, scout_data={
        "findings": [finding.to_dict() for finding in findings],
        "sources": [source.to_dict() for source in read.investigated]}).to_dict()
    assert report["claim_decomposition"][0]["verdict"] == "REFUTED"
    assert report["finding_details"][0]["contradicting_evidence_ids"] == [read.investigated[0].id]
