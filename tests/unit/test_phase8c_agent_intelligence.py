"""
Aegis Protocol — Phase 8C 4-Agent Intelligence Upgrade Tests
=============================================================
Evaluates Stage 8C intelligence capabilities:
1. Shared Claim Intelligence Layer:
   - Atomic claim extraction
   - 5-dimensional contradiction & divergence detection
   - Calibrated confidence scoring & non-binary epistemic verdicts
   - Strict evidence grounding and citations
2. Specialized Agent Intelligence:
   - Scout: SEC filing numerical comparison and corporate rumor debunking
   - Trending: Bot amplification, claim mutations, narrative acceleration
   - BrandShield: Executive impersonation, smear vs organic criticism, counterfeit domains
   - Personal Watch: VIP identity separation, doxxing exposure, deepfake allegations, quote attribution
"""

import pytest
from backend.services.research.claim_intelligence import (
    ClaimIntelligenceEngine,
    claim_intelligence_engine,
    extract_numeric_facts,
)
from backend.services.research.research_models import (
    AtomicClaim,
    ClaimVerdict,
    ConfidenceLevel,
    ContradictionType,
    EvidenceItem,
    SourceRole,
    SourceTier,
)
from backend.agents.scout.assessment import (
    compare_sec_filing_numbers,
    evaluate_corporate_rumor,
)
from backend.agents.trending.assessment import (
    detect_bot_amplification,
    track_claim_mutations,
)
from backend.agents.trending.temporal import (
    track_narrative_acceleration,
)
from backend.agents.brandshield.assessment import (
    classify_smear_vs_organic_criticism,
    detect_counterfeit_domains,
    detect_executive_impersonation,
)
from backend.agents.personal_watch.assessment import (
    assess_synthetic_media_allegations,
    detect_doxxing_exposure,
    verify_identity_match,
    verify_quote_attribution,
)


# =============================================================================
# 1. SHARED INTELLIGENCE LAYER: ATOMIC CLAIM EXTRACTION
# =============================================================================

def test_atomic_claim_extraction_decomposes_compound_text():
    engine = ClaimIntelligenceEngine()
    compound_text = (
        "Acme Corp announced a $12 billion acquisition of Stark AI yesterday in Delaware. "
        "Additionally, CEO Jane Doe resigned after an SEC investigation into fraud."
    )
    claims = engine.decompose_claims(compound_text)
    assert len(claims) >= 2

    c1 = claims[0]
    assert c1.entity in ("Acme Corp", "Acme")
    assert "QUANTITATIVE_VALUE" in c1.verifiable_dimensions
    assert "TEMPORAL_ANCHOR" in c1.verifiable_dimensions or "GEOGRAPHIC_SCOPE" in c1.verifiable_dimensions
    assert c1.claim_type == "NUMERICAL"

    c2 = claims[1]
    assert "Jane Doe" in c2.claim_text or "Jane" in c2.entity
    assert "ACTION_EVENT" in c2.verifiable_dimensions
    assert c2.verdict == ClaimVerdict.UNVERIFIED.value


def test_atomic_claim_extraction_handles_empty_input():
    engine = ClaimIntelligenceEngine()
    assert engine.decompose_claims("") == []
    assert engine.decompose_claims("   ") == []


# =============================================================================
# 2. SHARED INTELLIGENCE LAYER: 5-DIMENSIONAL CONTRADICTION DETECTION
# =============================================================================

def test_contradiction_axis_1_factual_contradiction():
    engine = ClaimIntelligenceEngine()
    ev1 = EvidenceItem(
        id="ev_01",
        title="Acme Corp signs definitive merger with Stark AI",
        snippet="Acme Corp agrees to acquire Stark AI in major buyout.",
        source_name="Tech Wire"
    )
    ev2 = EvidenceItem(
        id="ev_02",
        title="Acme Corp denies rumors of Stark AI buyout",
        snippet="Acme Corp officially refuted and dismissed all claims of talks with Stark AI as unfounded.",
        source_name="Acme Official PR",
        primary_source=True
    )
    contradictions = engine.detect_contradictions([ev1, ev2], target_name="Acme Corp")
    assert len(contradictions) >= 1
    c = contradictions[0]
    assert c["type"] in (ContradictionType.FACTUAL_CONTRADICTION.value, ContradictionType.CREDIBILITY_ASYMMETRY.value)
    assert c["severity"] == "HIGH"


def test_contradiction_axis_2_temporal_divergence():
    engine = ClaimIntelligenceEngine()
    ev_old = EvidenceItem(
        id="ev_old",
        title="CEO John Doe announces resignation from Acme",
        snippet="In 2021 John Doe stepped down from Acme Corp leadership.",
        source_name="Archive News",
        published_at="2021-05-01T00:00:00Z"
    )
    ev_new = EvidenceItem(
        id="ev_new",
        title="John Doe returns as Acme CEO in executive restructuring",
        snippet="John Doe returns to lead Acme Corp after earlier departure.",
        source_name="Current Times",
        published_at="2026-10-01T00:00:00Z"
    )
    contradictions = engine.detect_contradictions([ev_old, ev_new], target_name="John Doe")
    assert any(c["type"] == ContradictionType.TEMPORAL_DIVERGENCE.value for c in contradictions)


def test_contradiction_axis_3_numerical_discrepancy():
    engine = ClaimIntelligenceEngine()
    ev1 = EvidenceItem(
        id="ev_n1",
        title="Stark AI deal valued at $10.0 billion",
        snippet="Stark AI deal valued at $10.0 billion cash.",
        source_name="Wire One"
    )
    ev2 = EvidenceItem(
        id="ev_n2",
        title="Stark AI deal valued at $18.5 billion",
        snippet="Stark AI deal valued at $18.5 billion cash.",
        source_name="Wire Two"
    )
    contradictions = engine.detect_contradictions([ev1, ev2], target_name="Stark AI")
    num_conts = [c for c in contradictions if c["type"] == ContradictionType.NUMERICAL_DISCREPANCY.value]
    assert len(num_conts) >= 1
    assert num_conts[0]["discrepancy_ratio"] > 1.25


def test_contradiction_axis_4_scope_context_mismatch():
    engine = ClaimIntelligenceEngine()
    ev_ohio = EvidenceItem(
        id="ev_s1",
        title="Chemical spill incident reported in Ohio facility",
        snippet="Spill contained at Ohio manufacturing center.",
        source_name="Local News",
        metadata={"proposition_id": "spill-event-1"}
    )
    ev_florida = EvidenceItem(
        id="ev_s2",
        title="Chemical spill incident reported in Florida plant",
        snippet="Spill contained at Florida manufacturing site.",
        source_name="Southern News",
        metadata={"proposition_id": "spill-event-1"}
    )
    contradictions = engine.detect_contradictions([ev_ohio, ev_florida], target_name="Chemical spill incident")
    scope_conts = [c for c in contradictions if c["type"] == ContradictionType.SCOPE_CONTEXT_MISMATCH.value]
    assert len(scope_conts) >= 1


def test_contradiction_axis_5_credibility_asymmetry():
    engine = ClaimIntelligenceEngine()
    ev_rumor = EvidenceItem(
        id="ev_soc",
        title="Acme Corp bankruptcy filing imminent according to forum leaker",
        snippet="Acme Corp preparing Chapter 11 bankruptcy filing next week.",
        source_name="Reddit Forum",
        source_role=SourceRole.COMMUNITY.value,
        source_tier=SourceTier.TIER_3_SOCIAL_SIGNALS.value
    )
    ev_official = EvidenceItem(
        id="ev_sec",
        title="Acme Corp 10-Q filing officially denies and dismisses bankruptcy rumors",
        snippet="Acme Corp officially refuted and rejected bankruptcy rumors with $4B cash reserves in regulatory filing.",
        source_name="SEC EDGAR",
        source_role=SourceRole.PRIMARY.value,
        source_tier=SourceTier.TIER_1_OFFICIAL_FILING.value,
        primary_source=True
    )
    contradictions = engine.detect_contradictions([ev_rumor, ev_official], target_name="Acme Corp")
    asym_conts = [c for c in contradictions if c["type"] == ContradictionType.CREDIBILITY_ASYMMETRY.value]
    assert len(asym_conts) >= 1
    assert asym_conts[0]["severity"] == "HIGH"


# =============================================================================
# 3. SHARED INTELLIGENCE LAYER: CALIBRATED VERDICTS & CITATIONS
# =============================================================================

def test_calibrated_verdicts_zero_evidence_guard():
    engine = ClaimIntelligenceEngine()
    claim = AtomicClaim(claim_id="c_01", claim_text="Stark AI cures all cyber attacks")
    evaluated = engine.evaluate_claim(claim, [])
    assert evaluated.verdict == ClaimVerdict.INSUFFICIENT_EVIDENCE.value
    assert evaluated.confidence == 0.0
    assert evaluated.evidence_citations == []


def test_calibrated_verdicts_multi_primary_supported():
    engine = ClaimIntelligenceEngine()
    claim = AtomicClaim(claim_id="c_02", claim_text="Acme Corp acquires Stark AI", entity="Acme Corp")
    ev1 = EvidenceItem(
        id="ev_p1",
        canonical_url="https://acme.com/press",
        title="Acme Corp Completes Acquisition of Stark AI",
        snippet="Acme Corp officially acquires Stark AI.",
        source_name="Acme Press",
        source_role=SourceRole.PRIMARY.value,
        primary_source=True
    )
    ev2 = EvidenceItem(
        id="ev_p2",
        canonical_url="https://sec.gov/filing/8k",
        title="Acme Corp 8-K: Material Acquisition Agreement Stark AI",
        snippet="Form 8-K confirms acquisition of Stark AI.",
        source_name="SEC",
        source_role=SourceRole.PRIMARY.value,
        primary_source=True
    )
    evaluated = engine.evaluate_claim(claim, [ev1, ev2])
    assert evaluated.verdict == ClaimVerdict.SUPPORTED.value
    assert evaluated.confidence >= 0.85
    assert len(evaluated.evidence_citations) == 2


def test_calibrated_verdicts_official_refuted():
    engine = ClaimIntelligenceEngine()
    claim = AtomicClaim(claim_id="c_03", claim_text="Acme Corp files for bankruptcy", entity="Acme Corp")
    ev_debunk = EvidenceItem(
        id="ev_d1",
        canonical_url="https://acme.com/statement",
        title="Acme Corp Denies False Rumors of Bankruptcy",
        snippet="Acme Corp did not file for bankruptcy.",
        source_name="Acme PR",
        source_role=SourceRole.PRIMARY.value,
        primary_source=True
    )
    evaluated = engine.evaluate_claim(claim, [ev_debunk])
    assert evaluated.verdict == ClaimVerdict.REFUTED.value
    assert evaluated.confidence >= 0.85


def test_synthesize_intelligence_end_to_end():
    engine = ClaimIntelligenceEngine()
    text = "Acme Corp reported $10 billion in quarterly profit."
    ev = EvidenceItem(
        id="ev_rep",
        canonical_url="https://reuters.com/acme",
        title="Acme Corp posts $10 billion quarterly profit",
        snippet="Quarterly profit reached $10 billion.",
        source_name="Reuters",
        source_role=SourceRole.SECONDARY.value
    )
    synthesis = engine.synthesize_intelligence(text, [ev], target_name="Acme Corp")
    assert "overall_verdict" in synthesis
    assert "overall_confidence" in synthesis
    assert len(synthesis["claims"]) >= 1
    assert len(synthesis["citations"]) >= 1


# =============================================================================
# 4. AGENT 1: SCOUT INTELLIGENCE
# =============================================================================

def test_scout_sec_filing_numerical_comparison_detects_whisper_divergence():
    filing = {
        "revenue": 30.0e9,
        "net_income": 16.6e9,
        "period": "Q2 2026",
        "unit": "USD",
        "source_url": "https://www.sec.gov/edgar/acme-10q"
    }
    claims = [
        {"metric": "revenue", "claimed_value": 45.0e9, "period": "Q2 2026", "unit": "USD", "raw_text": "$45B Revenue rumor", "url": "https://x.com/leaker"},
        {"metric": "net_income", "claimed_value": 16.5e9, "period": "Q2 2026", "unit": "USD", "raw_text": "$16.5B net income", "url": "https://reuters.com/acme"}
    ]
    res = compare_sec_filing_numbers(filing, claims)
    assert res["status"] == "ANOMALIES_DETECTED"
    assert res["anomalies_detected"] == 1

    comp_rev = [c for c in res["comparisons"] if c["metric"] == "revenue"][0]
    assert comp_rev["verdict"] == "REFUTED"
    assert comp_rev["status"] == "CONTRADICTED_BY_OFFICIAL_FILING"

    comp_ni = [c for c in res["comparisons"] if c["metric"] == "net_income"][0]
    assert comp_ni["verdict"] == "SUPPORTED"


def test_scout_corporate_rumor_debunking():
    evidence = [
        {
            "evidence_id": "ev_sc_1",
            "url": "https://sec.gov/edgar/filing",
            "title": "Acme Corp 8-K: Denial of Acquisition Talks",
            "snippet": "Acme Corp officially dismissed and rejected reports that it is in talks to acquire competitor.",
            "source": "SEC EDGAR",
            "source_role": "PRIMARY",
            "source_tier": "TIER_1_OFFICIAL_FILING",
            "primary_source": True
        }
    ]
    res = evaluate_corporate_rumor("ACME", "Acme in talks to acquire competitor", evidence)
    assert res["verdict"] in ("REFUTED", "CONTRADICTED")
    assert res["confidence"] >= 0.80
    assert len(res["citations"]) >= 1


# =============================================================================
# 5. AGENT 2: TRENDING INTELLIGENCE
# =============================================================================

def test_trending_bot_amplification_detects_burst_and_copypasta():
    posts = [
        {
            "author": "user948271",
            "content": "Secret lab leaked dangerous prototype! Boycott Acme now! #AcmeExposed",
            "published_at": "2026-10-13T10:00:00Z"
        },
        {
            "author": "user948272",
            "content": "Secret lab leaked dangerous prototype! Boycott Acme now! #AcmeExposed",
            "published_at": "2026-10-13T10:02:00Z"
        },
        {
            "author": "bot_pulse99",
            "content": "Secret lab leaked dangerous prototype! Boycott Acme now! #AcmeExposed",
            "published_at": "2026-10-13T10:04:00Z"
        }
    ]
    res = detect_bot_amplification(posts)
    assert res["burst_detected"] is True
    assert res["copypasta_clusters"] >= 1
    assert res["amplification_risk"] in ("HIGH_PATTERN_SIMILARITY", "ELEVATED_SUSPICIOUS_ACTIVITY")
    assert res["automation_verified"] is False
    assert res["coordination_score"] >= 65


def test_trending_claim_mutations_tracks_sensationalism_drift():
    seed = "Acme software update causes battery drain"
    variants = [
        "Acme software update causes minor battery drain",
        "Leaked secret: Acme software update deadly battery explosion scandal exposed!"
    ]
    res = track_claim_mutations(seed, variants)
    assert res["mutation_count"] == 2
    assert res["max_sensationalism_drift"] > 0.5
    escalated = [m for m in res["mutations"] if m["mutation_type"] == "INFLAMMATORY_ESCALATION"]
    assert len(escalated) == 1
    assert "deadly" in escalated[0]["inflammatory_modifiers_added"]


def test_trending_narrative_acceleration():
    snapshots = [
        {"timestamp": "2026-10-13T08:00:00Z", "signal_count": 10},
        {"timestamp": "2026-10-13T09:00:00Z", "signal_count": 40},
        {"timestamp": "2026-10-13T10:00:00Z", "signal_count": 120},
    ]
    res = track_narrative_acceleration(snapshots)
    assert res["status"] == "ANALYSIS_COMPLETE"
    assert res["current_velocity"] > 0
    assert res["acceleration"] > 0
    assert res["trend_dynamics"] in ("PARABOLIC_EXPLOSIVE_GROWTH", "ACCELERATING_SPREAD")


# =============================================================================
# 6. AGENT 3: BRANDSHIELD INTELLIGENCE
# =============================================================================

def test_brandshield_executive_impersonation_detection():
    profiles = [
        {
            "handle": "tim_cook_official1",
            "name": "Tim Cook",
            "bio": "Apple CEO. DM for crypto giveaway and private investment opportunities!",
            "verified": False,
            "platform": "Twitter"
        },
        {
            "handle": "tim_cook",
            "name": "Tim Cook",
            "bio": "CEO Apple",
            "verified": True,
            "platform": "Twitter"
        }
    ]
    res = detect_executive_impersonation("Apple", "Tim Cook", profiles)
    assert res["profiles_analyzed"] == 2
    assert len(res["impersonation_threats"]) == 1
    t = res["impersonation_threats"][0]
    assert t["classification"] == "SUSPECTED_IMPERSONATION_REQUIRES_REVIEW"
    assert t["risk_level"] == "CRITICAL_FRAUDULENT_IMPERSONATION"


def test_brandshield_smear_vs_organic_criticism_differentiates_feedback():
    organic_reviews = [
        {
            "title": "Shoes were slightly tight in the toe box",
            "content": "Delivered on Tuesday. Size 10 fit smaller than expected, material feels stiff.",
            "published_at": "2026-10-01T12:00:00Z"
        },
        {
            "title": "Good cushioning but customer support was slow with refund",
            "content": "Asked customer support for receipt refund. Took 4 days to answer shipping questions.",
            "published_at": "2026-10-04T15:00:00Z"
        }
    ]
    res_organic = classify_smear_vs_organic_criticism(organic_reviews)
    assert res_organic["classification"] == "PRODUCT_FEEDBACK_IN_SAMPLE"
    assert res_organic["smear_campaign_detected"] is False

    coordinated_smear = [
        {
            "title": "DO NOT BUY TOTAL SCAM HORRIBLE PRODUCT BOYCOTT",
            "content": "DO NOT BUY TOTAL SCAM HORRIBLE PRODUCT BOYCOTT! Terrible company scamming everyone!",
            "published_at": "2026-10-13T10:00:00Z"
        },
        {
            "title": "DO NOT BUY TOTAL SCAM HORRIBLE PRODUCT BOYCOTT",
            "content": "DO NOT BUY TOTAL SCAM HORRIBLE PRODUCT BOYCOTT! Terrible company scamming everyone!",
            "published_at": "2026-10-13T10:05:00Z"
        }
    ]
    res_smear = classify_smear_vs_organic_criticism(coordinated_smear)
    assert res_smear["classification"] == "REPETITION_REQUIRES_REVIEW"
    assert res_smear["smear_campaign_detected"] is False


def test_brandshield_counterfeit_domain_detection():
    candidates = [
        "https://apple.com/iphone",
        "http://aple-support-auth.com/login",
        "https://nike-outlet-deals.shop/sale"
    ]
    findings = detect_counterfeit_domains("apple.com", candidates)
    assert len(findings) == 2
    typo_finding = [f for f in findings if "aple-support-auth" in f["candidate_domain"]][0]
    assert typo_finding["threat_type"] == "TYPOSQUAT_PHISHING"


# =============================================================================
# 7. AGENT 4: PERSONAL WATCH INTELLIGENCE
# =============================================================================

def test_personal_watch_identity_separation_rejects_namesake():
    catalog = {
        "canonical_name": "Satya Nadella",
        "affiliations": ["Microsoft"],
        "titles": ["CEO", "Chairman"]
    }
    target_match = {
        "title": "Satya Nadella details Microsoft cloud infrastructure strategy",
        "snippet": "Microsoft CEO Satya Nadella outlined AI advancements.",
        "author": "TechCrunch"
    }
    res_match = verify_identity_match(catalog, target_match)
    assert res_match["match_status"] == "CONTEXTUAL_MATCH_UNVERIFIED"
    assert res_match["identity_authenticated"] is False
    assert res_match["match_confidence"] >= 0.75

    namesake = {
        "title": "Satya Nadella opens local pediatric dentist clinic",
        "snippet": "Dr. Satya Nadella, local dentist in Ohio, announced office hours.",
        "author": "Local Gazette"
    }
    res_namesake = verify_identity_match(catalog, namesake)
    assert res_namesake["match_status"] == "MATCH_REJECTED_NAMESAKE"
    assert res_namesake["match_confidence"] <= 0.30


def test_personal_watch_doxxing_exposure_detects_pii():
    text_with_pii = (
        "Leaked records for VIP: Home address 742 Evergreen Terrace, Springfield, "
        "Phone: 206-555-0199, SSN: 123-45-6789, Personal email: vip_private@gmail.com"
    )
    res = detect_doxxing_exposure("VIP Person", text_with_pii)
    assert res["status"] == "PII_PATTERN_REQUIRES_REVIEW"
    assert res["unauthorized_exposure_verified"] is False
    assert res["exposure_severity"] == "CRITICAL"
    assert res["pii_findings_count"] == 4
    types = {f["type"] for f in res["findings"]}
    assert "GOVERNMENT_ID_SSN" in types
    assert "PHONE_NUMBER" in types
    assert "PERSONAL_EMAIL" in types
    assert "RESIDENTIAL_ADDRESS" in types


def test_personal_watch_synthetic_media_allegations():
    evidence = [
        {
            "title": "Reuters Fact-Check: Viral video of CEO is authentic, deepfake claim debunked",
            "snippet": "Fact-check confirms original footage is authentic video from public conference.",
            "source_role": "PRIMARY"
        }
    ]
    res = assess_synthetic_media_allegations(evidence)
    assert res["epistemic_state"] == "REPORTED_DEBUNKING_UNVERIFIED"
    assert res["media_assets_analyzed"] == 0


def test_personal_watch_quote_attribution():
    evidence = [
        {
            "title": "Spokesperson: CEO never uttered controversial statement circulating on social media",
            "snippet": "Reporting confirms viral statement claiming executive plans to fire all employees is a fabricated quote never said by the executive.",
            "source_role": "PRIMARY_OFFICIAL"
        }
    ]
    res = verify_quote_attribution("CEO", "We plan to fire all employees tomorrow", evidence)
    assert res["verdict"] == "REPORTED_MISATTRIBUTION_UNVERIFIED"
    assert res["assessment_is_heuristic"] is True
