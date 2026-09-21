"""
Aegis Protocol — Integration Tests: Modular Routers Coverage
============================================================
Validates that all domain routers in backend/api/ are mounted correctly
and respond across all specialized agent and telemetry endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_system_and_telemetry_router(test_client: TestClient):
    # 1. Healthz probe
    r1 = test_client.get("/api/healthz")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"
    assert r1.json()["active_agents"] == 7

    # 2. System API Index
    r2 = test_client.get("/api/")
    assert r2.status_code == 200
    assert "agents" in r2.json()
    assert len(r2.json()["agents"]) == 7

    # 3. All 7 Agents Telemetry
    r3 = test_client.get("/api/system/agents")
    assert r3.status_code == 200
    agents = r3.json()["agents"]
    assert "claim_ingestion" in agents
    assert "research" in agents
    assert "investigator" in agents
    assert "scout" in agents
    assert "brandshield" in agents
    assert "personal_watch" in agents
    assert "trending" in agents


@pytest.mark.integration
def test_claims_verify_sync_truth_dossier(test_client: TestClient):
    payload = {
        "claim": "Drinking boiling seawater cures advanced stage cancer within forty-eight hours."
    }
    resp = test_client.post("/api/claims/verify", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["verdict"] in ("FALSE", "MISLEADING", "TRUE", "UNVERIFIED")
    assert "social_radar" in data
    assert "forensic_risk" in data
    assert "action_package" in data
    assert "supporting_evidence" in data
    assert "refuting_evidence" in data


@pytest.mark.integration
def test_scout_agent_router(test_client: TestClient):
    resp = test_client.get("/api/stock?ticker=NVDA")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_price" in data
    assert "z_score" in data

    # Stock analysis
    res2 = test_client.post("/api/scout/analyze", json={"ticker": "AAPL"})
    assert res2.status_code == 200
    assert "short_attack_correlation" in res2.json()


@pytest.mark.integration
def test_brandshield_agent_router(test_client: TestClient):
    resp = test_client.post("/api/brandshield/scan", json={"brand_name": "TestCorp"})
    assert resp.status_code == 200
    data = resp.json()
    assert "brand" in data or "findings" in data or "threat_count" in data


@pytest.mark.integration
def test_personal_watch_agent_router(test_client: TestClient):
    resp = test_client.post("/api/personal/scan", json={"name": "Executive VIP"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_mentions" in data or "status" in data or "findings" in data


@pytest.mark.integration
def test_trending_agent_router(test_client: TestClient):
    resp = test_client.post("/api/trending/scan", json={"asset_name": "Tech Market"})
    assert resp.status_code == 200
    assert "asset_name" in resp.json() or "threats" in resp.json() or "narrative" in resp.json() or "velocity" in resp.json()
