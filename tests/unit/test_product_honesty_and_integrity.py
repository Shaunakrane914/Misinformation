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
        """Endpoint /api/system/deployment-status must report honest non-fabricated counts."""
        resp = client.get("/api/system/deployment-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "investigations_completed" in data
        assert isinstance(data["investigations_completed"], int)
        assert data["supported_channel_count"] >= 14
        assert data["active_agent_count"] == 7
        assert data["architecture_claims"]["swarms_claim"] == "7 Specialized Domain Engines"

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

    def test_g_brandshield_insufficient_evidence_is_not_no_threat(self):
        """BrandShield must return INSUFFICIENT_EVIDENCE_TO_ASSESS when fewer than 4 reviews exist."""
        agent = BrandShieldAgent()
        brand_info = agent.resolve_brand_entity("Acme Corp")
        res = agent._synthesize_brand_threats(brand_info, [])
        review_intel = res.get("review_intel", {})
        assert review_intel.get("status") == "INSUFFICIENT_EVIDENCE_TO_ASSESS"
        assert review_intel.get("confidence") is None
        assert review_intel.get("review_manipulation_detected") is False

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
