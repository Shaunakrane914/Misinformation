"""
Product Honesty and Anti-AI-Slop Integrity Test Suite
=====================================================
Validates that:
A. No fabricated homepage metrics or fake counters are served.
B. No fabricated progress percentages or timer-based progress bars exist.
C. Missing confidence renders as None / "Confidence unavailable".
D. Missing source URLs render as None, never "#" or synthetic domains.
E. Missing evidence never synthesizes placeholder evidence or post-hoc wire services.
F. Verdict does not invent Hawkes R0 (returns None / UNAVAILABLE when no event series).
G. Insufficient evidence != "no threat" / "no astroturfing" in BrandShield.
H. Channel health != query success; QueryExecutionRecord reflects actual attempts.
I. Primary escalation queries track genuine execution records and latency.
J. Doctor status never maps unprobed bootstrap states to AVAILABLE.
K. API deployment status endpoint reports real counts.
"""

import os
import pytest
import re
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.agent_reach.channels import ChannelStatus, QueryExecutionRecord
from backend.services.agent_reach.native.doctor import DoctorBridge
from backend.agents.brandshield_agent import BrandShieldAgent


class TestProductHonestyAndIntegrity:

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_a_deployment_status_endpoint_returns_real_counts(self, client):
        """Endpoint /api/system/deployment-status must report honest non-fabricated counts and distinct timestamps."""
        resp = client.get("/api/system/deployment-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "investigations_completed" in data
        assert isinstance(data["investigations_completed"], int)
        assert data["supported_channel_count"] >= 14

        # Behavioral agent count verification: registered count must equal specialized agent list length
        assert data["registered_agent_count"] == len(data["specialized_agents"])
        assert data["healthy_agent_count"] <= data["registered_agent_count"]

        # Active agent count must not be hardcoded to registered count on an on-demand architecture
        assert data["active_agent_count"] is None
        assert data["active_agent_count_status"] == "NOT_APPLICABLE_ON_DEMAND_EXECUTION"

        # Deployment ID must not be a fabricated static string when no deployment environment exists
        if not any(k in os.environ for k in ("DEPLOYMENT_ID", "RENDER_SERVICE_ID", "VERCEL_GIT_COMMIT_SHA")):
            assert data["deployment_id"] is None
            assert data["deployment_id_status"] == "UNAVAILABLE"

        # Timestamp semantics: response_generated_at must exist and not be confused with probe timestamp
        assert "response_generated_at" in data
        assert data["last_capability_probe_status"] in ("PROBED", "NOT_PROBED")
        assert data["last_successful_backend_sync_status"] == "UNAVAILABLE"

    def test_b_homepage_contains_no_fake_telemetry(self):
        """frontend/index.html must not contain the old hardcoded 142,800+, 16.2s, 99.4%, or 4 Swarms."""
        index_path = Path("frontend/index.html")
        assert index_path.exists()
        content = index_path.read_text(encoding="utf-8")

        assert "142,800+" not in content, "Found hardcoded 142,800+ in index.html"
        assert "99.4%" not in content, "Found hardcoded 99.4% in index.html"
        assert "4 Swarms" not in content, "Found inconsistent 4 Swarms claim in index.html"
        assert "16.2s" not in content or "16.2s" in content and "historical" in content.lower(), "Found hardcoded 16.2s telemetry"

    def test_c_nav_progress_contains_no_fake_timer_increments(self):
        """frontend/aegis-nav.js must not contain timer-simulated percentage increments."""
        nav_path = Path("frontend/aegis-nav.js")
        assert nav_path.exists()
        content = nav_path.read_text(encoding="utf-8")

        assert "currentPct += 4" not in content
        assert "autoStepInterval" not in content
        assert "currentPct = 100" not in content

    def test_d_missing_confidence_renders_unavailable(self, client):
        """When investigator returns confidence=None, claims API must preserve None."""
        mock_research = MagicMock()
        mock_research.gather_evidence_structured.return_value = {
            "research_corpus": {"findings": []},
            "evidence_chain": [],
            "research_trace": {},
            "contradictions": [],
        }

        mock_investigator = MagicMock()
        mock_investigator.process.return_value = {
            "verdict": "Unverified",
            "confidence": None,
            "reasoning": "No verifiable evidence retrieved.",
            "severity": "Low",
        }

        with patch("backend.api.claims.get_research_agent", return_value=mock_research), \
             patch("backend.api.claims.get_investigator_agent", return_value=mock_investigator):

            resp = client.post(
                "/api/claims/verify",
                json={"claim_text": "An obscure statement with zero web footprint"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["confidence"] is None or data.get("unified_report", {}).get("confidence") is None

    def test_e_missing_evidence_does_not_create_placeholder_urls_or_reuters(self, client):
        """Backend must never synthesize url='#' or fallback Reuters attribution."""
        mock_research = MagicMock()
        mock_research.gather_evidence_structured.return_value = {
            "research_corpus": None,
            "evidence_chain": [],
            "research_trace": {},
            "contradictions": [],
        }

        mock_investigator = MagicMock()
        mock_investigator.process.return_value = {
            "verdict": "Unverified",
            "confidence": None,
            "reasoning": "No sources retrieved.",
        }

        with patch("backend.api.claims.get_research_agent", return_value=mock_research), \
             patch("backend.api.claims.get_investigator_agent", return_value=mock_investigator):

            resp = client.post(
                "/api/claims/verify",
                json={"claim_text": "Test claim without sources"}
            )
            assert resp.status_code == 200
            data = resp.json()
            evidence_list = data.get("evidence", [])
            for ev in evidence_list:
                assert ev.get("url") != "#", "Found placeholder url='#' in evidence"
                assert "Verified Official Records" not in ev.get("source", ""), "Found synthesized 'Verified Official Records'"

    def test_f_verdict_does_not_generate_hawkes_r0(self, client):
        """A verdict must not synthesize Hawkes R0 (2.45 or 1.65)."""
        mock_research = MagicMock()
        mock_research.gather_evidence_structured.return_value = {
            "research_corpus": None,
            "evidence_chain": [],
            "research_trace": {},
            "contradictions": [],
        }

        mock_investigator = MagicMock()
        mock_investigator.process.return_value = {
            "verdict": "False",
            "confidence": 0.8,
            "reasoning": "Contradicted by known facts.",
        }

        with patch("backend.api.claims.get_research_agent", return_value=mock_research), \
             patch("backend.api.claims.get_investigator_agent", return_value=mock_investigator):

            resp = client.post(
                "/api/claims/verify",
                json={"claim_text": "False claim test"}
            )
            assert resp.status_code == 200
            data = resp.json()
            hawkes = data.get("hawkes_r0")
            assert hawkes is None or hawkes != 2.45, "Found verdict-dependent Hawkes R0 2.45"
            assert hawkes != 1.65, "Found verdict-dependent Hawkes R0 1.65"

    def test_g_brandshield_deterministic_review_pattern_screening(self):
        """BrandShield must use genuine text screening rather than keyword counting."""
        agent = BrandShieldAgent()

        # Case 1: Empty retrieval yields INSUFFICIENT_EVIDENCE
        brand_info = agent.resolve_brand_entity("Acme Corp")
        res_empty = agent._synthesize_brand_threats(brand_info, [])
        review_empty = res_empty.get("review_intel", {})
        assert review_empty.get("status") in ("INSUFFICIENT_EVIDENCE", "INSUFFICIENT_EVIDENCE_TO_ASSESS")
        assert review_empty.get("confidence") is None
        assert review_empty.get("review_manipulation_detected") is False
        assert review_empty.get("signals_analyzed") == 0

        # Case 2: Natural diverse reviews do not trigger duplicate clusters
        diverse_evidence = [
            {"evidence_id": "ev_1", "title": "Great customer service and fast shipping", "snippet": "I ordered this product last week and the customer support was very helpful.", "platform": "Web"},
            {"evidence_id": "ev_2", "title": "Disappointed with battery life rating", "snippet": "The device discharges after five hours of continuous heavy usage.", "platform": "Reddit"},
            {"evidence_id": "ev_3", "title": "Review of new firmware update release", "snippet": "The manufacturer fixed the bluetooth connectivity glitch in the latest patch.", "platform": "Web"},
        ]
        res_diverse = agent.screen_review_patterns(diverse_evidence)
        assert res_diverse["status"] == "SCREENED_NO_REPETITION_FOUND"
        assert res_diverse["review_manipulation_detected"] is False
        assert res_diverse["signals_analyzed"] == 3
        assert res_diverse["near_duplicate_clusters"] == 0

        # Case 3: Actual near-duplicate text triggers manipulation cluster
        templated_evidence = [
            {"evidence_id": "ev_1", "title": "Best purchase ever five star seller highly recommend", "snippet": "Amazing product best purchase ever five star seller highly recommend to everyone excellent quality.", "platform": "Web"},
            {"evidence_id": "ev_2", "title": "Best purchase ever five star seller highly recommend", "snippet": "Amazing item best purchase ever five star seller highly recommend to everyone excellent build.", "platform": "Web"},
        ]
        res_templated = agent.screen_review_patterns(templated_evidence)
        assert res_templated["status"] == "SUSPICIOUS_PATTERNS_DETECTED"
        assert res_templated["review_manipulation_detected"] is True
        assert res_templated["signals_analyzed"] == 2
        assert res_templated["near_duplicate_clusters"] >= 1
        assert len(res_templated["signals_found"]) >= 1

        # Case 4: Single review with keyword density cannot declare 'no manipulation'
        single_review = [
            {"evidence_id": "ev_1", "title": "Review rating five star seller feedback", "snippet": "Customer review rating five star feedback on order delivered.", "platform": "Web"}
        ]
        res_single = agent.screen_review_patterns(single_review)
        assert res_single["status"] == "INSUFFICIENT_EVIDENCE"
        assert res_single["review_manipulation_detected"] is False
        assert res_single["signals_analyzed"] == 1

        # Case 5: End-to-end synthesis links FAKE_REVIEW threat when manipulation is detected
        synth_res = agent._synthesize_brand_threats(brand_info, templated_evidence)
        assert synth_res["review_intel"]["review_manipulation_detected"] is True
        fake_threats = [t for t in synth_res.get("threats", []) if t.get("type") == "FAKE_REVIEW"]
        assert len(fake_threats) >= 1
        assert "ev_1" in fake_threats[0]["evidence_ids"]

    def test_h_doctor_status_marks_unprobed_baseline_as_unknown_not_available(self):
        """DoctorBridge fallback baseline must mark capabilities as not_probed / UNKNOWN, not available."""
        doc = DoctorBridge()
        baseline = doc._generate_fallback_baseline()
        for cap, details in baseline.items():
            assert details["status"] == "not_probed"
            assert details["active_backend"] is None
            code = doc.get_canonical_status_code(details)
            assert code == "UNKNOWN"

    def test_i_query_execution_record_preserves_genuine_telemetry(self):
        """QueryExecutionRecord must record real latency and channel without inventing SUCCESS."""
        record = QueryExecutionRecord(
            query_id="q-101",
            channel="web",
            query_text="test query",
            status="ERROR",
            latency_ms=124,
            result_count_raw=0,
            result_count_normalized=0,
            error="Network timeout"
        )
        data = record.to_dict()
        assert data["channel"] == "web"
        assert data["status"] == "ERROR"
        assert data["latency_ms"] == 124
        assert data["result_count_raw"] == 0
        assert data["error"] == "Network timeout"

    def test_j_api_root_information_contract(self, client):
        """Root /api/ must report authoritative version and honest deterministic architecture."""
        resp = client.get("/api/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "3.7.0"
        assert "Modular Multi-Agent Swarm with Zero-Cost Omni-Scraper Fabric" not in data.get("architecture", "")
        assert data["architecture"] == "Deterministic Evidence Pipeline with Selective Semantic AI"
        assert "registered_modules" in data

    def test_k_frontend_runtime_truth_and_integrity(self):
        """Frontend files must enforce honest initial states, valid 404 routing, and no synthetic fallbacks."""
        # 1. 404 page & redirects
        assert Path("frontend/404.html").exists(), "frontend/404.html missing"
        redirects = Path("frontend/_redirects").read_text(encoding="utf-8")
        assert "/* /index.html 200" not in redirects, "Catch-all 200 mask must be removed"

        # 2. Version 3.7.0 across shared nav
        nav = Path("frontend/aegis-nav.js").read_text(encoding="utf-8")
        assert "window.AEGIS_VERSION = '3.7.0'" in nav, "Nav missing authoritative version 3.7.0"

        # 3. submit.html: distinct AI_SYNTHESIS vs BACKEND_INVESTIGATION
        sub = Path("frontend/submit.html").read_text(encoding="utf-8")
        assert "AI_SYNTHESIS" in sub
        assert "reuters.com" not in sub

        # 4. investigator-agent.html: honest initial state
        inv = Path("frontend/investigator-agent.html").read_text(encoding="utf-8")
        assert "NO CASE LOADED" in inv
        assert "CASE-2026-A109" not in inv

        # 5. research-agent.html: honest initial state
        res = Path("frontend/research-agent.html").read_text(encoding="utf-8")
        assert "Awaiting Research Inquiry" in res
        assert "No findings yet" in res

        # 6. trending-agent.html: no synthetic fallback generator
        tr = Path("frontend/trending-agent.html").read_text(encoding="utf-8")
        assert "generateResilientTrendingFallback" not in tr
        assert "signals_retrieved: 18" not in tr

        # 7. dashboard: cached sample badge
        dash = Path("frontend/dashboard.html").read_text(encoding="utf-8")
        assert "CACHED SAMPLE DATA" in dash

        # 8. about.html: 4 clear tiers
        ab = Path("frontend/about.html").read_text(encoding="utf-8")
        assert "TIER 1 &bull; PRODUCTION IMPLEMENTATION" in ab
        assert "TIER 2 &bull; RESEARCH METHODOLOGY" in ab
        assert "TIER 3 &bull; SIMULATION INSTRUMENT" in ab
        assert "TIER 4 &bull; RESEARCH ROADMAP" in ab

        # 9. status.html: dynamic timeline states
        st = Path("frontend/status.html").read_text(encoding="utf-8")
        assert "tlBadge" in st
        assert "COMPLETE" in st and "RUNNING" in st and "FAILED" in st
