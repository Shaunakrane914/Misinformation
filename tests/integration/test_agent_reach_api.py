"""
Aegis Protocol — Integration Tests: Agent Reach API Surface
============================================================
Validates:
- GET /api/agent-reach/capabilities: Channel inventory, supported domains
- GET /api/agent-reach/health: Channel probe health report
- GET /api/agent-reach/doctor: Legacy diagnostics endpoint
- POST /api/agent-reach/omni-scan: Domain-directed multi-channel retrieval
- POST /api/agent-reach/read: SSRF defense blocking internal URLs
- POST /api/agent-reach/scan: Unified cross-platform scan
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalResult

client = TestClient(app)


def test_api_agent_reach_capabilities():
    response = client.get("/api/agent-reach/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "AgentReachService"
    assert data["total_channels"] == 14
    assert "reddit" in data["channels"]
    assert "github" in data["channels"]
    assert "rss" in data["channels"]
    assert "linkedin" in data["channels"]
    assert "technical" in data["supported_domains"]


def test_api_agent_reach_health_and_doctor():
    # Health endpoint
    resp_health = client.get("/api/agent-reach/health")
    assert resp_health.status_code == 200
    data_health = resp_health.json()
    assert "status" in data_health
    assert "summary" in data_health
    assert "channels" in data_health

    # Legacy doctor endpoint
    resp_doc = client.get("/api/agent-reach/doctor")
    assert resp_doc.status_code == 200
    data_doc = resp_doc.json()
    assert "channels" in data_doc


def test_api_agent_reach_omni_scan():
    with patch("backend.services.agent_reach.adapter.AgentReachService.retrieve") as mock_retrieve:
        mock_retrieve.return_value = RetrievalResult(
            query="TSLA earnings crash",
            domain="financial",
            fragments=[
                EvidenceFragment(
                    platform="Twitter",
                    title="$TSLA volume spike",
                    content="Unusual options activity detected",
                    channel_name="twitter"
                )
            ],
            channel_health={"twitter": "AVAILABLE"},
            total_signals=1,
            retrieval_plan={"domain": "financial", "channels_to_query": ["twitter", "news"]}
        )

        response = client.post(
            "/api/agent-reach/omni-scan",
            json={"query": "TSLA earnings crash", "domain": "financial", "limit": 3}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "financial"
        assert "channels" in data
        assert "items" in data
        assert "twitter" in data["channels"]
        assert len(data["items"]) == 1
        assert "retrieval_plan" in data


def test_api_agent_reach_read_ssrf_blocked():
    # Attacking internal loopback
    response = client.post(
        "/api/agent-reach/read",
        json={"url": "http://127.0.0.1:8000/api/claims"}
    )
    assert response.status_code == 400
    assert "SSRF" in response.json()["detail"]


def test_api_agent_reach_scan():
    with patch("backend.services.agent_reach.adapter.AgentReachService.unified_scan") as mock_scan:
        mock_scan.return_value = {
            "query": "cryptocurrency exploit",
            "channels": {"news": [{"title": "Exploit patched"}]},
            "items": [{"title": "Exploit patched"}]
        }

        response = client.post(
            "/api/agent-reach/scan",
            json={"query": "cryptocurrency exploit", "limit": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert "channels" in data
        assert "items" in data
