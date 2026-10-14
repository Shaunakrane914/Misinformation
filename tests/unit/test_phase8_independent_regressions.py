"""Independent negative controls for source authority and proposition grounding."""

import pytest

from backend.services.research.claim_intelligence import ClaimIntelligenceEngine
from backend.services.research.research_models import AtomicClaim, EvidenceItem
from backend.services.research.source_quality import SourceQualityEngine
from backend.services.research.source_independence import SourceIndependenceEngine
from backend.agents.personal_watch.assessment import assess_synthetic_media_allegations


def test_unrelated_retrieved_record_never_becomes_model_citation(monkeypatch):
    from backend.agents.personal_watch.assessment import synthesize_personal_threats
    import backend.services.intelligence as intelligence
    monkeypatch.setattr(intelligence, "call_gemini_text", lambda prompt: '{"threats":[{"title":"Invented allegation","evidence_ids":["nonexistent"]}],"claims":[]}')
    result = synthesize_personal_threats({"name": "Public Subject"}, [{
        "evidence_id": "real", "platform": "web", "source": "Publisher", "title": "Unrelated documentation",
        "snippet": "Documentation", "url": "https://example.org/doc",
    }])
    assert result["threats"] == []


def test_unlinked_personal_dossier_keeps_empty_evidence_chain():
    from backend.agents.personal_watch.dossier import build_investigation_dossiers
    result = build_investigation_dossiers([{"threat_id": "t", "evidence_ids": ["unknown"]}],
                                          [{"evidence_id": "real", "title": "Unrelated"}], [])
    assert result[0]["evidence_chain"] == []
    assert result[0]["first_observed_at"] == ""


def test_different_financial_metrics_are_not_a_numerical_contradiction():
    items = [evidence("a", "Acme revenue was 100 billion in 2024"),
             evidence("b", "Acme profit was 5 billion in 2024")]
    contradictions = ClaimIntelligenceEngine().detect_contradictions(items, "Acme")
    assert not any(c["type"] == "NUMERICAL_DISCREPANCY" for c in contradictions)


def test_actual_support_navigation_is_not_a_confirmed_customer_grievance():
    from backend.agents.brandshield.assessment import heuristic_threat_synthesis
    sample = [{"evidence_id": "ev_public_support", "title": "Official Apple Support", "url": "https://support.apple.com/",
               "platform": "web", "snippet": "Apple Support Need help? Billing and payments Reset Apple Account password Change a subscription"}]
    result = heuristic_threat_synthesis({"brand": "Apple", "resolved_entity": "Apple"}, sample)
    assert not any(t["type"] == "CUSTOMER_COMPLAINT" for t in result["threats"])
    assert result["narratives"][0]["threat_level"] == "unassessed"
    assert "consumer sentiment" in result["narratives"][0]["description"]


@pytest.mark.parametrize("url", [
    "https://sec.gov.attacker.example/form-10-k.htm",
    "https://notsec.gov/form-10-k.htm",
    "https://attacker.example/sec.gov/form-10-k.htm",
    "https://sec.gov@attacker.example/form-10-k.htm",
    "https://sec.gov:invalid/form-10-k.htm",
])
def test_filing_words_cannot_promote_spoofed_regulator(url):
    item = EvidenceItem(id="spoof", canonical_url=url, title="SEC filing Form 10-K",
                        source_domain="sec.gov", content="Regulatory filing court order")
    SourceQualityEngine().classify_and_score(item, "Microsoft")
    assert not item.official_source
    assert not item.primary_source
    assert item.source_tier != "TIER_1_OFFICIAL_FILING"


@pytest.mark.parametrize("url", ["https://www.sec.gov/", "https://www.sec.gov/search"])
def test_regulator_landing_is_not_a_filing(url):
    item = EvidenceItem(id="landing", canonical_url=url, title="Search SEC filings")
    SourceQualityEngine().classify_and_score(item)
    assert item.official_source
    assert not item.primary_source
    assert item.source_tier != "TIER_1_OFFICIAL_FILING"


def evidence(id, text, url="https://example.org/report", **kwargs):
    return EvidenceItem(id=id, title=text, snippet=text, canonical_url=url, **kwargs)


def test_entity_presence_does_not_support_unrelated_claim():
    claim = AtomicClaim(claim_id="claim", entity="Acme", claim_text="Acme acquired Orion")
    items = [evidence("1", "Acme publishes accessibility guidance", "https://acme.com/a", primary_source=True),
             evidence("2", "Acme launches developer documentation", "https://acme.com/b", primary_source=True)]
    result = ClaimIntelligenceEngine().evaluate_claim(claim, items)
    assert result.verdict == "INSUFFICIENT_EVIDENCE"
    assert not result.supporting_evidence_ids


def test_duplicate_primary_records_are_not_independent_confirmation():
    claim = AtomicClaim(claim_id="claim", entity="Acme", claim_text="Acme acquired Orion")
    items = [evidence(str(i), "Acme acquired Orion", "https://acme.com/announcement", primary_source=True)
             for i in range(3)]
    result = ClaimIntelligenceEngine().evaluate_claim(claim, items)
    assert result.verdict != "SUPPORTED"
    assert len(result.evidence_citations) == 1


def test_negated_claim_cannot_be_supported_by_opposite_statement():
    claim = AtomicClaim(claim_id="claim", entity="Acme", claim_text="Acme did not acquire Orion")
    result = ClaimIntelligenceEngine().evaluate_claim(claim, [
        evidence("1", "Acme acquired Orion", "https://acme.com/a", primary_source=True),
        evidence("2", "Acme acquired Orion", "https://news.example/b", source_role="SECONDARY")])
    assert result.verdict != "SUPPORTED"


def test_missing_url_and_date_do_not_become_verified_recent_citation():
    claim = AtomicClaim(claim_id="claim", entity="Acme", claim_text="Acme acquired Orion")
    result = ClaimIntelligenceEngine().evaluate_claim(claim, [
        evidence("1", "Acme acquired Orion", "", primary_source=True),
        evidence("2", "Acme acquired Orion", "", primary_source=True)])
    assert result.verdict not in {"SUPPORTED", "REFUTED"}
    assert all(c["published_at"] == "" for c in result.evidence_citations)


def test_different_reporting_periods_are_not_numeric_conflicts():
    items = [evidence("1", "Acme annual revenue in 2023 was $10 billion"),
             evidence("2", "Acme annual revenue in 2024 was $18 billion")]
    conflicts = ClaimIntelligenceEngine().detect_contradictions(items, "Acme")
    assert not any(c["type"] == "NUMERICAL_DISCREPANCY" for c in conflicts)


def test_two_geographic_events_can_both_be_true():
    items = [evidence("1", "Acme opened a manufacturing plant in Ohio"),
             evidence("2", "Acme opened a manufacturing plant in Florida")]
    assert not ClaimIntelligenceEngine().detect_contradictions(items, "Acme")


def test_publisher_subdomains_do_not_count_as_independent_origins():
    items = [evidence("1", "Acme earnings announcement", "https://news.acme.com/a", source_domain="news.acme.com"),
             evidence("2", "Acme investor statement", "https://ir.acme.com/b", source_domain="ir.acme.com")]
    _, groups = SourceIndependenceEngine().cluster_independence(items)
    assert len(groups) == 1


def test_primary_page_mentioning_video_does_not_verify_recording():
    result = assess_synthetic_media_allegations([{
        "title": "Acme video product documentation", "url": "https://acme.com/docs",
        "source_role": "PRIMARY", "content": "How to upload a video."}])
    assert result["epistemic_state"] != "AUTHENTIC_VERIFIED_RECORDING"
    assert result["media_assets_analyzed"] == 0


def test_observed_redirect_origin_overrides_declared_canonical_authority():
    item = EvidenceItem(id="redirect", canonical_url="https://sec.gov/filing.htm",
                        title="Form 10-K", metadata={"observed_final_endpoint": "https://attacker.example/filing.htm"})
    SourceQualityEngine().classify_and_score(item)
    assert not item.official_source


def test_conditional_and_attribution_scope_is_not_dropped_during_decomposition():
    raw = 'If Acme acquires Orion, it could expand. He said "It failed. It stopped."'
    claims = ClaimIntelligenceEngine().decompose_claims(raw)
    assert [c.claim_text for c in claims] == [raw]


def test_filing_numbers_from_different_periods_do_not_refute_claim():
    from backend.agents.scout.assessment import compare_sec_filing_numbers
    result = compare_sec_filing_numbers({"revenue": 10, "period": "2023", "unit": "USD", "source_url": "https://sec.gov/filing.htm"},
                                       [{"metric": "revenue", "claimed_value": 20, "period": "2024", "unit": "USD"}])
    assert result["comparisons"][0]["verdict"] == "UNVERIFIED"


def test_repeated_criticism_does_not_prove_malicious_campaign():
    from backend.agents.brandshield.assessment import classify_smear_vs_organic_criticism
    result = classify_smear_vs_organic_criticism([{"content": "Acme is terrible"}] * 3)
    assert not result["smear_campaign_detected"]
    assert result["classification"] == "REPETITION_REQUIRES_REVIEW"


def test_acquisition_role_assignment_does_not_trust_filing_title():
    from backend.infrastructure.acquisition.service import AgentReachService
    from backend.services.agent_reach.channels import EvidenceFragment
    fragment = EvidenceFragment(platform="web", title="Official SEC filing Form 10-K",
                                content="A fabricated regulatory filing", url="https://sec.gov.attacker.example/document")
    AgentReachService()._assign_source_roles([fragment])
    assert fragment.raw_metadata["source_role"] != "PRIMARY"
    assert not fragment.raw_metadata["official_source"]
