"""
Unit and integration tests for claims research endpoint and ResearchCorpus persistence.
Tests:
- GET /api/claims/{claim_id} includes research_funnel and research_url
- GET /api/claims/{claim_id}/research returns full ResearchCorpus
- GET /api/claims/{claim_id}/research returns 404 when no corpus is available
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.db import database as db

client = TestClient(app)


def test_claim_status_and_research_endpoint():
    inserted = db.insert_claim("hash_999", "Sample claim for testing research endpoint", "Sample claim for testing research endpoint")
    claim_id = inserted["id"]
    db.update_claim_status(claim_id, "completed")
    db.update_claim_final_result(claim_id, verdict="False", confidence=0.95, severity="High", reasoning="Refuted by official regulatory records.")

    # 1. Before research corpus is saved
    resp = client.get(f"/api/claims/{claim_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["claim_id"] == claim_id
    assert data["has_research_corpus"] is False
    assert data["research_url"] is None

    res_404 = client.get(f"/api/claims/{claim_id}/research")
    assert res_404.status_code == 404

    # 2. Save mock ResearchCorpus
    mock_corpus = {
        "funnel": {
            "queries_planned": 12,
            "queries_executed": 12,
            "candidates_found": 35,
            "candidates_ranked": 35,
            "deep_reads_count": 5,
            "primary_sources_count": 3,
            "independent_groups_count": 8,
            "contradictions_count": 1,
            "findings_count": 3
        },
        "grounded_findings": [
            {
                "finding_id": "f_1",
                "claim_statement": "Sample claim assertion is ungrounded",
                "summary": "SEC 10-K confirms statement is false",
                "confidence_score": 0.96,
                "sentiment_stance": "refuting",
                "supporting_evidence_ids": ["ev_01", "ev_02"]
            }
        ],
        "deep_read_sources": [
            {
                "id": "ev_01",
                "url": "https://sec.gov/edgar/sample-10k",
                "domain": "sec.gov",
                "authority_score": 1.0,
                "role": "primary_document",
                "title": "SEC Annual Report 2026",
                "content_preview": "Official financial statement proves no merger occurred.",
                "word_count": 1240,
                "provenance": "Escalated to primary source via SEC EDGAR directory"
            }
        ],
        "primary_sources": [
            {
                "url": "https://sec.gov/edgar/sample-10k",
                "domain": "sec.gov",
                "title": "SEC Annual Report 2026",
                "escalation_reason": "Government regulatory filing"
            }
        ],
        "corroboration_groups": [
            {
                "group_name": "SEC Regulatory Registry",
                "articles_count": 1,
                "parent_wire": None
            }
        ],
        "candidate_selection_audit": [
            {
                "candidate_id": "ev_01",
                "rank": 1,
                "score": 0.98,
                "eligible_for_read": True,
                "selected": True,
                "rejection_reason": None
            },
            {
                "candidate_id": "ev_02",
                "rank": 2,
                "score": 0.50,
                "eligible_for_read": False,
                "selected": False,
                "rejection_reason": "social_only"
            }
        ]
    }
    db.save_claim_research(claim_id, mock_corpus)

    # 3. Check /api/claims/{claim_id} now reports research_funnel and research_url
    resp2 = client.get(f"/api/claims/{claim_id}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["has_research_corpus"] is True
    assert data2["research_url"] == f"/api/claims/{claim_id}/research"
    assert data2["research_funnel"]["queries_planned"] == 12
    assert data2["research_funnel"]["deep_reads_count"] == 5

    # 4. Check /api/claims/{claim_id}/research returns full corpus
    res_corpus = client.get(f"/api/claims/{claim_id}/research")
    assert res_corpus.status_code == 200
    c_data = res_corpus.json()
    assert c_data["claim_id"] == claim_id
    assert c_data["funnel"]["deep_reads_count"] == 5
    assert len(c_data["corpus"]["grounded_findings"]) == 1
    assert len(c_data["corpus"]["deep_read_sources"]) == 1
    assert len(c_data["corpus"]["candidate_selection_audit"]) == 2
    assert c_data["corpus"]["candidate_selection_audit"][1]["rejection_reason"] == "social_only"
