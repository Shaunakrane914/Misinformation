"""
Aegis Protocol — Integration Tests: Scout 2.0 Full Workflow
============================================================
Validates:
- End-to-end execution of POST /api/scout/analyze
- Schema conformance of Scout 2.0 response (stock, retrieval, sources, news, social, catalysts, narratives, timeline, misinformation)
- Backward-compatibility with existing consumers (short_attack_correlation, stock, news)
- Verification that source links and provenance are properly propagated
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_scout_analyze_api_full_workflow(test_client: TestClient):
    resp = test_client.post("/api/scout/analyze", json={"ticker": "TATAMOTORS.NS"})
    assert resp.status_code == 200
    data = resp.json()

    # Core metadata
    assert data["ticker"] == "TATAMOTORS.NS"
    assert "company_name" in data
    assert "analyzed_at" in data

    # 1. Market Telemetry Snapshot
    assert "stock" in data
    stock = data["stock"]
    assert "current_price" in stock
    assert "z_score" in stock
    assert "drop_percent" in stock
    assert "data_source" in stock

    # 2. Retrieval Scope
    assert "retrieval" in data
    retrieval = data["retrieval"]
    assert "total_sources" in retrieval
    assert "unique_sources" in retrieval
    assert "channels" in retrieval
    assert "latency_ms" in retrieval

    # 3. Sources & clickable URLs
    assert "sources" in data
    assert isinstance(data["sources"], list)
    for s in data["sources"]:
        assert "evidence_id" in s
        assert "source_role" in s
        assert "source_tier" in s
        assert "url" in s
        assert "has_url" in s
        assert "independence_group" in s

    # 4. Multi-channel Social
    assert "social" in data
    social = data["social"]
    assert "reddit" in social
    assert "twitter" in social
    assert "youtube" in social

    # 5. Catalysts & Narratives
    assert "catalysts" in data
    assert "positive" in data["catalysts"]
    assert "negative" in data["catalysts"]
    assert "unresolved" in data["catalysts"]

    assert "narratives" in data
    assert isinstance(data["narratives"], list)

    # 6. Contradictions & Misinformation Risk
    assert "contradictions" in data
    assert "for" in data["contradictions"]
    assert "against" in data["contradictions"]

    assert "misinformation" in data
    assert "status" in data["misinformation"]
    assert "manipulation_risk" in data["misinformation"]

    # 7. Backward Compatibility
    assert "short_attack_correlation" in data
    sac = data["short_attack_correlation"]
    assert "risk_level" in sac
    assert "correlation_score" in sac
    assert "social_catalyst_volume" in sac

    assert "news" in data
    assert "company" in data["news"]


@pytest.mark.integration
def test_scout_analyze_us_ticker(test_client: TestClient):
    resp = test_client.post("/api/scout/analyze", json={"ticker": "NVDA"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "NVDA"
    assert "Nvidia" in data["company_name"]
    assert "sources" in data
    assert "stock" in data
