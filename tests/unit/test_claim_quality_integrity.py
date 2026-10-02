"""
Unit Tests for Claim Analysis Quality Tensor Integrity
=======================================================
Verifies:
1. When no genuine research corpus is available:
   - quality_tensor is None.
   - quality_status is 'UNAVAILABLE_NO_CORPUS'.
   - No hardcoded synthetic defaults (0.95, 0.90, etc.) are returned.
2. When genuine research corpus or quality tensor is present:
   - Genuine quality_tensor is preserved and returned.
   - quality_status is 'VERIFIED_CORPUS'.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app


class TestClaimQualityIntegrity:
    """Verifies honest quality status reporting in /api/claims/analyze."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_claim_analysis_returns_unavailable_when_no_corpus(self, client):
        mock_research = MagicMock()
        mock_research.gather_evidence_structured.return_value = {
            "research_corpus": None,  # No genuine corpus
            "quality_tensor": None,
            "evidence_chain": [],
            "research_trace": {},
            "contradictions": [],
        }

        mock_investigator = MagicMock()
        mock_investigator.process.return_value = {
            "verdict": "False",
            "confidence": 0.5,
            "reasoning": "No definitive corroboration found.",
            "severity": "Low",
        }

        with patch("backend.api.claims.get_research_agent", return_value=mock_research), \
             patch("backend.api.claims.get_investigator_agent", return_value=mock_investigator):

            resp = client.post(
                "/api/claims/verify",
                json={"claim_text": "Unverified rumor circulating on social media"}
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["quality_tensor"] is None, "Quality tensor must be None when no genuine corpus exists"
            assert data["quality_status"] == "UNAVAILABLE_NO_CORPUS"

    def test_claim_analysis_returns_verified_corpus_when_genuine_tensor_exists(self, client):
        mock_tensor = {
            "source_credibility": 0.92,
            "factual_consistency": 0.88,
            "recency_decay": 0.95,
            "corroboration_depth": 0.84,
            "cross_platform_diversity": 0.70,
            "primary_source_proximity": 0.90,
            "composite_quality": 0.87,
        }

        mock_research = MagicMock()
        mock_research.gather_evidence_structured.return_value = {
            "research_corpus": {
                "findings": [
                    {
                        "title": "Official Announcement",
                        "quality_tensor": mock_tensor
                    }
                ]
            },
            "evidence_chain": [],
            "research_trace": {},
            "contradictions": [],
        }

        mock_investigator = MagicMock()
        mock_investigator.process.return_value = {
            "verdict": "True",
            "confidence": 0.95,
            "reasoning": "Verified with official press release.",
            "severity": "Low",
        }

        with patch("backend.api.claims.get_research_agent", return_value=mock_research), \
             patch("backend.api.claims.get_investigator_agent", return_value=mock_investigator):

            resp = client.post(
                "/api/claims/verify",
                json={"claim_text": "Official company quarterly report released"}
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["quality_tensor"] == mock_tensor
            assert data["quality_status"] == "VERIFIED_CORPUS"
