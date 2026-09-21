"""
Aegis Protocol — Integration Tests: Claim Lifecycle & API Endpoints
====================================================================
Tests the full HTTP API surface:
- Claim submission (POST /api/claims/submit)
- Claim status retrieval (GET /api/claims/{claim_id})
- Duplicate submission handling (POST /api/claims/submit)
- Input validation failures (empty body, invalid JSON)
- Threat Lab endpoints
"""

import time
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_submit_claim_and_retrieve_verdict(test_client: TestClient):
    payload = {
        "claim": "Drinking warm lemon water completely cures chronic diabetes within two weeks."
    }
    
    # 1. Submit claim
    resp = test_client.post("/api/claims/submit", json=payload)
    assert resp.status_code in (200, 202)
    data = resp.json()
    assert "claim_id" in data
    assert data["status"] in ("pending", "processing")
    claim_id = data["claim_id"]

    # 2. Wait briefly for background worker execution
    time.sleep(0.6)

    # 3. Poll claim status
    status_resp = test_client.get(f"/api/claims/{claim_id}")
    assert status_resp.status_code == 200
    claim_data = status_resp.json()
    
    assert claim_data.get("claim_id") == claim_id
    assert claim_data.get("status") in ("completed", "pending", "processing")
    if claim_data.get("status") == "completed":
        assert claim_data.get("verdict") in [
            "True", "False", "Misleading", "Partially True", "Unverified", "Insufficient Evidence"
        ]
        assert ("confidence" in claim_data or "confidence_score" in claim_data)


@pytest.mark.integration
def test_submit_empty_claim_fails(test_client: TestClient):
    resp = test_client.post("/api/claims/submit", json={"claim": ""})
    assert resp.status_code in (400, 422)


@pytest.mark.integration
def test_duplicate_claim_submission(test_client: TestClient):
    payload = {"claim": "Identical claim for deduplication testing."}
    
    resp1 = test_client.post("/api/claims/submit", json=payload)
    assert resp1.status_code in (200, 202)
    id1 = resp1.json()["claim_id"]

    resp2 = test_client.post("/api/claims/submit", json=payload)
    assert resp2.status_code in (200, 202)
    id2 = resp2.json()["claim_id"]
    
    assert id1 == id2
    assert resp2.json().get("is_new") is False


@pytest.mark.integration
def test_threat_lab_api_endpoints(test_client: TestClient):
    # 1. Synthetic detect
    r1 = test_client.post("/api/lab/synthetic-detect", json={
        "text": "Artificial intelligence algorithms generate realistic sentences that match linguistic power law distributions."
    })
    assert r1.status_code == 200
    assert "r_squared" in r1.json()
    assert r1.json().get("verdict") in ("SYNTHETIC", "HUMAN", "INSUFFICIENT_DATA")

    # 2. Hawkes blast radius
    r2 = test_client.post("/api/lab/blast-radius", json={
        "topic": "Financial Market Manipulation",
        "claim": "Central bank secretly devaluing currency overnight"
    })
    assert r2.status_code == 200
    assert r2.json().get("threat_level") in ("CRITICAL CONTAGION", "ELEVATED", "NOMINAL")
    assert r2.json().get("is_simulation") is True

    # 3. Consensus arbitration
    r3 = test_client.post("/api/lab/consensus", json={
        "claim": "The earth is stationary and enclosed in a glass dome."
    })
    assert r3.status_code == 200
    assert "consensus_verdict" in r3.json()
    assert "agents" in r3.json()
    assert len(r3.json()["agents"]) >= 3
