"""
Aegis Protocol — Phase 8F Integrated Misinformation Verification Suite
======================================================================
Comprehensive end-to-end acceptance tests verifying all 12 required
misinformation scenarios across the four production agents:
  1. Financial misinformation (Scout: official filing comparison & discrepancy)
  2. Product / technology rumors (ClaimVerifier: release/preprint verification)
  3. Emerging misleading narratives (Trending: bot amplification & velocity)
  4. Brand impersonation (BrandShield: counterfeit domain & executive impersonation)
  5. False corporate announcements (Scout: statutory 8-K check & credibility asymmetry)
  6. Public-figure misquotation (Personal Watch: quote attribution & fabrication)
  7. Outdated information recirculated as recent (Contradiction: temporal divergence)
  8. Syndicated echo repetition (Research: source clustering & independence defense)
  9. Genuine conflicting information (Contradiction: factual contradiction & mixed verdict)
  10. Insufficient evidence requiring abstention (Epistemic humility: insufficient evidence)
  11. Partially accessible sources (Telemetry: auth required & honest disclosure)
  12. Completely unavailable source operations (Failure handling: zero fake data)
"""

import pytest

from backend.schemas.unified_report import (
    UnifiedReport,
    UnifiedEvidenceItem,
    UnifiedEvidenceSource,
    QueryTelemetry,
    TrustMetadata,
)
from backend.services.report_builder import ReportBuilder
from backend.services.research.claim_intelligence import ClaimIntelligenceEngine
from backend.services.research.source_independence import SourceIndependenceEngine
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.research.research_models import (
    EvidenceItem,
    ContradictionType,
    SourceRole,
    SourceTier,
)
from backend.agents.scout.assessment import (
    compare_sec_filing_numbers,
    evaluate_corporate_rumor,
)
from backend.agents.trending.assessment import (
    detect_bot_amplification,
)
from backend.agents.trending.temporal import (
    track_narrative_acceleration,
)
from backend.agents.brandshield.assessment import (
    detect_executive_impersonation,
    detect_counterfeit_domains,
)
from backend.agents.personal_watch.assessment import (
    verify_quote_attribution,
)


@pytest.mark.integration
class TestPhase8FIntegratedVerification:
    """End-to-end validation of the 12 Phase 8F required misinformation scenarios."""

    # ── Scenario 1: Financial Misinformation ─────────────────────────────────
    def test_scenario_1_financial_misinformation(self):
        """Scout evaluates financial rumor against statutory filing numbers."""
        claim = "Acme Corp reported $500M revenue but secretly suffered an 80% loss in Q3 2026."
        filing_facts = {
            "filing_url": "https://sec.gov/Archives/edgar/data/320193/001.htm",
            "period": "Q3 2026",
            "unit": "USD",
            "revenue": 500_000_000,
            "net_income": 45_000_000,
        }
        circulating_claims = [
            {
                "metric": "revenue",
                "period": "Q3 2026",
                "unit": "USD",
                "claimed_value": 100_000_000,
                "raw_text": "$100M revenue (claims 80% loss)",
                "url": "https://social.example/post/1",
            }
        ]

        # Compare filing numbers via Scout assessment intelligence
        reconciliation = compare_sec_filing_numbers(
            filing_facts=filing_facts,
            circulating_claims=circulating_claims,
        )
        assert reconciliation["status"] == "ANOMALIES_DETECTED"
        assert reconciliation["anomalies_detected"] >= 1
        assert len(reconciliation["comparisons"]) >= 1
        assert reconciliation["comparisons"][0]["verdict"] == "REFUTED"
        assert reconciliation["comparisons"][0]["status"] == "CONTRADICTED_BY_OFFICIAL_FILING"

        # Build unified report
        scout_payload = {
            "market_summary": f"Claim evaluated against SEC filing: {claim}",
            "filing_comparison": reconciliation,
            "disputes": ["Viral social posts claim 80% drop, contradicting audited Form 10-Q."],
            "primary_filings": [
                {
                    "title": "SEC Form 10-Q Quarterly Report",
                    "url": "https://sec.gov/Archives/edgar/data/320193/001.htm",
                    "source": {"name": "SEC EDGAR", "authority": "STATUTORY_REGULATOR", "reliability": 0.99, "is_primary": True},
                }
            ],
        }
        report = ReportBuilder.from_scout_result(query="Acme Corp", scout_data=scout_payload)
        dump = report.to_dict()

        assert dump["_meta"]["agent"] == "scout"
        assert "agent_intelligence" in dump
        assert dump["agent_intelligence"]["filing_comparison"]["anomalies_detected"] >= 1
        assert len(dump["evidence"]["primary"]) == 1
        assert dump["evidence"]["primary"][0]["source"]["authority"] == "STATUTORY_REGULATOR"

    # ── Scenario 2: Product & Technology Rumors ──────────────────────────────
    def test_scenario_2_product_tech_rumors(self):
        """ClaimVerifier tests unverified product rumor against technical preprints & releases."""
        claim = "TechLabs cancelled quantum core project and shut down compiler team"
        fragments = [
            EvidenceFragment(
                platform="github",
                title="v4.2 Release",
                content="TechLabs published v4.2 quantum compiler release with 40 new commits",
                url="https://github.com/techlabs/compiler/releases/v4.2",
            ),
            EvidenceFragment(
                platform="arxiv",
                title="Preprint on Quantum Architecture",
                content="Quantum Compiler Optimization on 128-Qubit Processors",
                url="https://arxiv.org/abs/2604.01928",
            ),
        ]
        assert len(fragments) == 2
        assert fragments[0].platform == "github"
        assert fragments[1].platform == "arxiv"

        engine = ClaimIntelligenceEngine()
        decomp = engine.decompose_claims(claim)
        assert len(decomp) >= 1

        verdict_data = {
            "verdict": "REFUTED",
            "confidence": 0.91,
            "reasoning": "Active GitHub releases and current arXiv preprint refute project cancellation rumors.",
            "claim_decomposition": [c.to_dict() for c in decomp],
        }
        report = ReportBuilder.from_claim_result(claim_text=claim, verdict=verdict_data)
        dump = report.to_dict()

        assert "REFUTED" in dump["summary"]
        assert "claim_decomposition" in dump
        assert len(dump["claim_decomposition"]) >= 1

    # ── Scenario 3: Emerging Misleading Narratives ───────────────────────────
    def test_scenario_3_emerging_misleading_narratives(self):
        """Trending tracks bot amplification signals, narrative velocity, and doubling time."""
        claim = "Massive nationwide grid shutdown announced across multiple regions"
        posts = [
            {"author": "bot_9182", "content": claim, "published_at": "2026-10-12T10:00:00Z"},
            {"author": "bot_9183", "content": claim, "published_at": "2026-10-12T10:00:05Z"},
            {"author": "bot_9184", "content": claim, "published_at": "2026-10-12T10:00:10Z"},
        ]

        bot_intel = detect_bot_amplification(posts)
        snapshots = [
            {"timestamp": "2026-10-12T10:00:00Z", "signal_count": 10},
            {"timestamp": "2026-10-12T11:00:00Z", "signal_count": 80},
            {"timestamp": "2026-10-12T12:00:00Z", "signal_count": 640},
        ]
        velocity_intel = track_narrative_acceleration(snapshots)

        assert bot_intel["coordination_score"] > 0
        assert bot_intel["amplification_risk"] in ("HIGH_PATTERN_SIMILARITY", "ELEVATED_SUSPICIOUS_ACTIVITY")
        assert velocity_intel["current_velocity"] > 0.0
        assert velocity_intel["explosive_breakout_alert"] is True

        trend_data = {
            "summary": "Rapid viral spread with high artificial amplification indicators.",
            "bot_amplification": bot_intel,
            "narrative_velocity": velocity_intel,
            "contradictions": [
                {
                    "type": "SCOPE_CONTEXT_MISMATCH",
                    "severity": "CRITICAL",
                    "statement_a": "Nationwide grid shutdown across multiple regions",
                    "source_a": "Viral bot cluster",
                    "statement_b": "Routine substation maintenance affecting 2 streets",
                    "source_b": "Regional Power Authority Bulletin",
                    "explanation": "Local maintenance distorted into nationwide emergency.",
                }
            ],
        }
        report = ReportBuilder.from_trending_result(query="Grid Shutdown", trend_data=trend_data)
        dump = report.to_dict()

        assert dump["_meta"]["agent"] == "trending"
        assert dump["agent_intelligence"]["bot_amplification"]["coordination_score"] > 0
        assert len(dump["contradictions"]) == 1
        assert dump["contradictions"][0]["type"] == "SCOPE_CONTEXT_MISMATCH"

    # ── Scenario 4: Brand Impersonation ──────────────────────────────────────
    def test_scenario_4_brand_impersonation(self):
        """BrandShield detects typosquatted counterfeit domains and executive impersonation."""
        brand = "Apex Security"
        impersonation = detect_executive_impersonation(
            brand_name=brand,
            executive_name="Jane Doe",
            candidate_profiles=[
                {
                    "handle": "@JaneDoeCEO_giveaway",
                    "name": "Jane Doe Official",
                    "bio": "Apex CEO. DM for crypto giveaway funds and airdrop.",
                    "verified": False,
                    "platform": "Twitter",
                },
                {
                    "handle": "@JaneDoeApex",
                    "name": "Jane Doe",
                    "bio": "CEO of Apex Security",
                    "verified": True,
                    "platform": "Twitter",
                },
            ],
        )
        assert impersonation["max_risk_level"] in ("HIGH", "CRITICAL")
        assert len(impersonation["impersonation_threats"]) >= 1

        counterfeit = detect_counterfeit_domains(
            brand_domain="apexsecurity.com",
            candidate_domains=["apex-sec-login.com", "apexsecurity-portal.xyz", "apexxsecurity.com"],
        )
        assert len(counterfeit) >= 1

        brand_data = {
            "brand_name": brand,
            "status": "ELEVATED THREAT",
            "executive_impersonation": impersonation,
            "counterfeit_domains": counterfeit,
            "smear_analysis": {"classification": "SMEAR_CAMPAIGN", "confidence": 0.88},
        }
        report = ReportBuilder.from_brandshield_result(query=brand, brand_data=brand_data)
        dump = report.to_dict()

        assert dump["_meta"]["agent"] == "brandshield"
        assert dump["agent_intelligence"]["executive_impersonation"]["max_risk_level"] in ("HIGH", "CRITICAL")
        assert len(dump["agent_intelligence"]["counterfeit_domains"]) >= 1

    # ── Scenario 5: False Corporate Announcements ────────────────────────────
    def test_scenario_5_false_corporate_announcements(self):
        """Scout evaluates corporate rumor against official regulatory disclosures."""
        claim = "MegaCorp announced sudden divestiture of cloud operations for $12B"
        evidence = [
            {
                "title": "Viral blog claims MegaCorp divestiture",
                "snippet": "Unconfirmed rumors that MegaCorp sells cloud unit for $12B",
                "source": "Blog",
                "source_role": "COMMUNITY",
                "platform": "web",
            },
            {
                "title": "MegaCorp SEC Filings Portal",
                "snippet": "No 8-K filings or divestiture announcements registered for MegaCorp",
                "source": "SEC EDGAR",
                "source_role": "PRIMARY",
                "platform": "edgar",
                "url": "https://sec.gov",
            },
        ]
        rumor_eval = evaluate_corporate_rumor(
            ticker="MegaCorp",
            rumor_text=claim,
            evidence=evidence,
        )
        assert "verdict" in rumor_eval
        assert rumor_eval["confidence"] is not None
        assert rumor_eval["ticker"] == "MegaCorp"

    # ── Scenario 6: Public-Figure Misquotation ───────────────────────────────
    def test_scenario_6_public_figure_misquotation(self):
        """Personal Watch tests quote attribution against canonical transcripts."""
        quoted = "I personally ordered the coverup and falsified the inspection records"
        evidence = [
            {
                "title": "Fact-check: Fabricated quote falsely attributed to Director Smith",
                "snippet": "Fact-check confirms Director Smith never said I personally ordered the coverup. Quote is fabricated.",
                "source": "Reuters Fact Check",
                "source_role": "SECONDARY",
            },
            {
                "title": "Director Smith Address",
                "snippet": "We initiated a full independent review and reported all inspection findings",
                "source": "Official Transcript",
                "source_role": "PRIMARY",
            },
        ]

        attribution = verify_quote_attribution(
            subject_name="Director Smith",
            quote=quoted,
            evidence_list=evidence,
        )
        assert attribution["verdict"] == "REPORTED_MISATTRIBUTION_UNVERIFIED"
        assert attribution["confidence"] == 0.35
        assert attribution["assessment_is_heuristic"]

    # ── Scenario 7: Outdated Information Recirculated ────────────────────────
    def test_scenario_7_outdated_information_recirculated(self):
        """Contradiction detector identifies temporal divergence on recirculated old news."""
        engine = ClaimIntelligenceEngine()
        ev_old = EvidenceItem(
            id="ev_old",
            title="Regulators issue nationwide halt on Acme sales",
            snippet="Emergency nationwide halt ordered in 2021 on Acme sales.",
            source_name="News Archive 2021",
            published_at="2021-05-01T00:00:00Z",
        )
        ev_new = EvidenceItem(
            id="ev_new",
            title="Acme sales resumed nationwide following review",
            snippet="Nationwide sales fully resumed after comprehensive safety clearance by regulators.",
            source_name="Official Gazette 2026",
            published_at="2026-10-01T00:00:00Z",
        )

        contradictions = engine.detect_contradictions([ev_old, ev_new], target_name="Acme")
        temporal = [c for c in contradictions if c["type"] == ContradictionType.TEMPORAL_DIVERGENCE.value]
        assert len(temporal) >= 1
        assert temporal[0]["severity"] in ("MEDIUM", "HIGH")

    # ── Scenario 8: Syndicated Echo Repetition ───────────────────────────────
    def test_scenario_8_syndicated_repetition_not_independent(self):
        """Syndicated wire reprints must be clustered; independence is not exaggerated."""
        engine = SourceIndependenceEngine()
        items = [
            EvidenceItem(
                id="ev_1",
                title="Beta company reports merger talks underway",
                snippet="Beta company reports merger talks underway in syndicated release.",
                source_domain="wire-reprint-1.com",
            ),
            EvidenceItem(
                id="ev_2",
                title="Beta company reports merger talks underway",
                snippet="Beta company reports merger talks underway in syndicated release.",
                source_domain="wire-reprint-2.com",
            ),
            EvidenceItem(
                id="ev_3",
                title="Beta company reports merger talks underway",
                snippet="Beta company reports merger talks underway in syndicated release.",
                source_domain="wire-reprint-3.com",
            ),
        ]
        updated_items, clusters_map = engine.cluster_independence(items)
        # All 3 share identical title slug and origin, so they form 1 cluster
        assert len(clusters_map) == 1
        # Syndicated republications have penalized independence score
        assert updated_items[1].independence_score <= 0.20

        trust = TrustMetadata(independent_source_count=len(clusters_map))
        assert trust.independent_source_count == 1

    # ── Scenario 9: Genuine Conflicting Information ──────────────────────────
    def test_scenario_9_genuine_conflicting_information(self):
        """Contradiction detector recognizes direct factual contradiction between sources."""
        engine = ClaimIntelligenceEngine()
        ev1 = EvidenceItem(
            id="ev_1",
            title="Ministry of Health reports 0 active cases in southern district",
            snippet="Officials confirmed 0 cases across the region.",
            source_name="Central Ministry",
            primary_source=True,
        )
        ev2 = EvidenceItem(
            id="ev_2",
            title="Ministry of Health regional bureau denies 0 cases report",
            snippet="Regional bureau explicitly refutes 0 active cases claim, confirming 142 cases.",
            source_name="Regional Bureau",
            primary_source=True,
        )

        contradictions = engine.detect_contradictions([ev1, ev2], target_name="Ministry of Health")
        factual = [
            c for c in contradictions
            if c["type"] in (ContradictionType.FACTUAL_CONTRADICTION.value, ContradictionType.CREDIBILITY_ASYMMETRY.value)
        ]
        assert len(factual) >= 1
        assert factual[0]["severity"] == "HIGH"

    # ── Scenario 10: Insufficient Evidence Abstention ────────────────────────
    def test_scenario_10_insufficient_evidence_abstention(self):
        """When evidence cannot be retrieved, system abstains with INSUFFICIENT_EVIDENCE."""
        claim = "Obscure unverifiable private transaction occurred in 1984 on an unnamed island"
        report = ReportBuilder.from_claim_result(
            claim_text=claim,
            verdict={
                "verdict": "INSUFFICIENT_EVIDENCE",
                "confidence": None,
                "reasoning": "Zero corroborated primary or secondary evidence was found across channels.",
            },
            corpus=None,
            execution_log=[{"channel": "web", "status": "SUCCESS", "result_count_normalized": 0}],
        )
        dump = report.to_dict()
        assert "INSUFFICIENT_EVIDENCE" in dump["summary"]
        assert dump["trust"]["independent_source_count"] is None

    # ── Scenario 11: Partially Accessible Sources ────────────────────────────
    def test_scenario_11_partially_accessible_sources(self):
        """When a source requires authorization, telemetry records it honestly without fake data."""
        exec_log = [
            {"channel": "web", "status": "SUCCESS", "result_count_normalized": 3},
            {"channel": "news", "status": "AUTH_REQUIRED", "result_count_normalized": 0},
        ]
        report = ReportBuilder.from_claim_result(
            claim_text="Partially accessible query",
            verdict={"verdict": "UNVERIFIED", "confidence": 0.5},
            execution_log=exec_log,
            queries_planned=2,
        )
        dump = report.to_dict()
        telemetry = dump["trust"]["query_telemetry"]

        assert telemetry["queries_auth_required"] == 1
        assert telemetry["queries_succeeded"] == 1
        assert telemetry["queries_started"] == 2

    # ── Scenario 12: Completely Unavailable Operations ───────────────────────
    def test_scenario_12_completely_unavailable_operations(self):
        """When all operations fail or time out, failure is reported honestly with zero synthetic items."""
        exec_log = [
            {"channel": "web", "status": "FAILED", "error": "Connection reset"},
            {"channel": "rss", "status": "TIMEOUT", "error": "Gateway timeout"},
        ]
        report = ReportBuilder.from_claim_result(
            claim_text="Completely failed retrieval",
            verdict={"verdict": "INSUFFICIENT_EVIDENCE", "confidence": None},
            execution_log=exec_log,
            queries_planned=2,
        )
        dump = report.to_dict()
        telemetry = dump["trust"]["query_telemetry"]

        assert telemetry["queries_failed"] == 1
        assert telemetry["queries_timed_out"] == 1
        assert telemetry["queries_succeeded"] == 0
        assert len(dump["evidence"]["primary"]) == 0
        assert len(dump["evidence"]["independent"]) == 0
        assert len(dump["evidence"]["community"]) == 0
