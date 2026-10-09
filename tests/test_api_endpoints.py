"""
Integration tests for unified report integration in API endpoints.
Tests /api/claims/verify, /api/scout/analyze, /api/trending/scan,
/api/brandshield/scan, /api/personal/scan.
"""

import warnings
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_claims_verify_returns_unified_report():
    """Verify endpoint should include unified_report in response."""
    payload = {
        "claim_text": "The moon is made of green cheese according to NASA.",
        "skip_cache": True
    }
    with patch("backend.api.claims.get_claim_ingestion_agent") as mock_ingest_getter, \
         patch("backend.api.claims.get_research_agent") as mock_research_getter, \
         patch("backend.api.claims.get_investigator_agent") as mock_invest_getter:
        
        mock_ingest = MagicMock()
        mock_ingest.ingest.return_value = {
            "claim_id": "test_claim_id_123",
            "normalized_text": payload["claim_text"]
        }
        mock_ingest.decompose_claim.return_value = [payload["claim_text"]]
        mock_ingest_getter.return_value = mock_ingest

        mock_research = MagicMock()
        mock_research.gather_evidence_structured.return_value = {
            "supporting_evidence": [],
            "refuting_evidence": [{"source": "NASA", "quote": "Moon rock analysis proves it is basalt and anorthosite"}],
            "overall_evidence_confidence": "High",
            "research_corpus": {
                "primary_sources": [{"title": "NASA Lunar Sample Lab", "canonical_url": "https://nasa.gov", "domain": "nasa.gov", "source_tier": "tier_1_verified_record"}]
            }
        }
        mock_research_getter.return_value = mock_research

        mock_invest = MagicMock()
        mock_invest.process.return_value = {
            "verdict": "False",
            "confidence": 0.95,
            "reasoning": "Empirical geology disproves the moon is cheese.",
            "severity": "Low"
        }
        mock_invest.extract_verdict.return_value = mock_invest.process.return_value
        mock_invest_getter.return_value = mock_invest

        response = client.post("/api/claims/verify", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "unified_report" in data
        assert data["unified_report"] is not None
        assert data["unified_report"]["_meta"]["agent"] == "claim_verifier"
        assert "summary" in data["unified_report"]
        assert "evidence" in data["unified_report"]
        assert "trust" in data["unified_report"]

def test_scout_analyze_returns_unified_report():
    """Scout analyze endpoint should include unified_report in response."""
    payload = {"ticker": "NVDA", "drop_percentage": 5.0}
    with patch("backend.api.agents.get_scout_agent") as mock_scout_getter:
        mock_scout = MagicMock()
        mock_scout.analyze_stock.return_value = {
            "status": "success",
            "ticker": "NVDA",
            "catalysts": [{"title": "Supply rumor", "confidence": 0.8}],
            "recommendation": "Monitor",
            "severity": "medium",
            "summary": "Potential short rumor detected",
            "stock": {"current_price": 120.0, "drop_percent": -5.2, "z_score": -2.3}
        }
        mock_scout_getter.return_value = mock_scout
        response = client.post("/api/scout/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "unified_report" in data
        assert data["unified_report"] is not None
        assert data["unified_report"]["_meta"]["agent"] == "scout"
        assert "summary" in data["unified_report"]
        assert "findings" in data["unified_report"]

def test_trending_scan_returns_unified_report():
    """Trending scan endpoint should include unified_report in response."""
    payload = {"query": "AI regulation rumors"}
    with patch("backend.api.agents.get_trending_agent") as mock_trend_getter:
        mock_trend = MagicMock()
        mock_trend.scan.return_value = {
            "status": "success",
            "narratives": [{"topic": "AI Ban", "velocity": 12.5}],
            "alerts": []
        }
        mock_trend_getter.return_value = mock_trend
        response = client.post("/api/trending/scan", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "unified_report" in data
        assert data["unified_report"] is not None
        assert data["unified_report"]["_meta"]["agent"] == "trending"
        assert "findings" in data["unified_report"]

def test_brandshield_scan_returns_unified_report():
    """BrandShield scan endpoint should include unified_report in response."""
    payload = {"brand_name": "Acme Corp"}
    with patch("backend.api.agents.get_brandshield_agent") as mock_bs_getter:
        mock_bs = MagicMock()
        mock_bs.scan.return_value = {
            "status": "success",
            "brand": "Acme Corp",
            "threats_detected": 1,
            "threat_level": "moderate",
            "threats": [{"type": "counterfeit", "source": "fake-store.com"}],
            "recommendations": ["Takedown notice"]
        }
        mock_bs_getter.return_value = mock_bs
        response = client.post("/api/brandshield/scan", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "unified_report" in data
        assert data["unified_report"] is not None
        assert data["unified_report"]["_meta"]["agent"] == "brandshield"
        assert "findings" in data["unified_report"]

def test_personal_scan_returns_unified_report():
    """Personal scan endpoint should include unified_report in response."""
    payload = {"name": "Jane Doe"}
    with patch("backend.agents.personal_agent.process_personal_watch") as mock_process:
        mock_process.return_value = {
            "status": "success",
            "target": "Jane Doe",
            "threats": [{"type": "impersonation", "platform": "Twitter"}],
            "severity": "low",
            "summary": "Impersonation account spotted"
        }
        response = client.post("/api/personal/scan", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "unified_report" in data
        assert data["unified_report"] is not None
        assert data["unified_report"]["_meta"]["agent"] in ("personal", "personal_watch")
        assert "findings" in data["unified_report"]


def test_claims_verify_zero_variance_tokens_regression():
    """
    Regression test: claims where all tokens have identical frequency (zero variance)
    must produce mandelbrot_r2=None and must NOT raise or emit any NumPy RuntimeWarning.
    """
    # 10 distinct words, each appearing exactly once (uniform frequencies, zero variance)
    claim_text = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    payload = {"claim_text": claim_text, "skip_cache": True}

    with patch("backend.api.claims.get_claim_ingestion_agent") as mock_ingest_getter, \
         patch("backend.api.claims.get_research_agent") as mock_research_getter, \
         patch("backend.api.claims.get_investigator_agent") as mock_invest_getter:

        mock_ingest = MagicMock()
        mock_ingest.ingest.return_value = {"claim_id": "reg_001", "normalized_text": claim_text}
        mock_ingest.decompose_claim.return_value = [claim_text]
        mock_ingest_getter.return_value = mock_ingest

        mock_research = MagicMock()
        mock_research.gather_evidence_structured.return_value = {
            "supporting_evidence": [],
            "refuting_evidence": [],
            "overall_evidence_confidence": "Low",
            "research_corpus": {"primary_sources": []}
        }
        mock_research_getter.return_value = mock_research

        mock_invest = MagicMock()
        mock_invest.process.return_value = {
            "verdict": "Unverified",
            "confidence": 0.5,
            "reasoning": "No corroborating signals.",
            "severity": "Low"
        }
        mock_invest.extract_verdict.return_value = mock_invest.process.return_value
        mock_invest_getter.return_value = mock_invest

        with warnings.catch_warnings(record=True) as captured_warnings:
            warnings.simplefilter("always")
            response = client.post("/api/claims/verify", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "forensic_risk" in data
        assert data["forensic_risk"]["mandelbrot_r2"] is None

        # Assert no RuntimeWarning from numpy or math was emitted
        runtime_warnings = [w for w in captured_warnings if issubclass(w.category, RuntimeWarning)]
        assert len(runtime_warnings) == 0, f"Expected 0 RuntimeWarnings, got: {[str(w.message) for w in runtime_warnings]}"


def test_claims_verify_nonconstant_frequencies_valid_r2():
    """
    Confirms that claims with varying token frequencies produce a valid numeric mandelbrot_r2
    without warnings.
    """
    # 10+ words with varying frequencies: 'signal' x4, 'threat' x3, 'report' x2, and singletons
    claim_text = (
        "signal signal signal signal threat threat threat report report "
        "investigation anomaly detection intelligence radar"
    )
    payload = {"claim_text": claim_text, "skip_cache": True}

    with patch("backend.api.claims.get_claim_ingestion_agent") as mock_ingest_getter, \
         patch("backend.api.claims.get_research_agent") as mock_research_getter, \
         patch("backend.api.claims.get_investigator_agent") as mock_invest_getter:

        mock_ingest = MagicMock()
        mock_ingest.ingest.return_value = {"claim_id": "reg_002", "normalized_text": claim_text}
        mock_ingest.decompose_claim.return_value = [claim_text]
        mock_ingest_getter.return_value = mock_ingest

        mock_research = MagicMock()
        mock_research.gather_evidence_structured.return_value = {
            "supporting_evidence": [],
            "refuting_evidence": [],
            "overall_evidence_confidence": "Medium",
            "research_corpus": {"primary_sources": []}
        }
        mock_research_getter.return_value = mock_research

        mock_invest = MagicMock()
        mock_invest.process.return_value = {
            "verdict": "Unverified",
            "confidence": 0.6,
            "reasoning": "Varying frequency test.",
            "severity": "Low"
        }
        mock_invest.extract_verdict.return_value = mock_invest.process.return_value
        mock_invest_getter.return_value = mock_invest

        with warnings.catch_warnings(record=True) as captured_warnings:
            warnings.simplefilter("always")
            response = client.post("/api/claims/verify", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "forensic_risk" in data
        r2 = data["forensic_risk"]["mandelbrot_r2"]
        assert r2 is not None
        assert isinstance(r2, float)
        assert 0.0 <= r2 <= 1.0

        runtime_warnings = [w for w in captured_warnings if issubclass(w.category, RuntimeWarning)]
        assert len(runtime_warnings) == 0
