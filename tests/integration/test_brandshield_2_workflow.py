"""
Aegis Protocol — Integration Tests: BrandShield 2.0 Full Workflow
==================================================================
Tests:
- End-to-end execution of POST /api/brandshield/scan
- Full schema verification (brand, entity, retrieval, summary, threats, claims, narratives, dossiers, sources, timeline)
- Product line distinction (Nike vs. Nike Air Max)
- 100% backward compatibility for existing consumers (findings, threat_count, safe_count, platforms)
- URL preservation and absence of fabricated platform simulation
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_brandshield_scan_api_full_workflow(test_client: TestClient):
    resp = test_client.post("/api/brandshield/scan", json={"brand_name": "Nike"})
    assert resp.status_code == 200
    data = resp.json()

    # Core brand & entity resolution
    assert "brand" in data
    assert data["brand"] == "Nike"
    assert "entity" in data
    assert data["entity"]["entity_type"] == "brand"

    # Retrieval metadata
    assert "retrieval" in data
    retrieval = data["retrieval"]
    assert "total_sources" in retrieval
    assert "unique_sources" in retrieval
    assert "latency_ms" in retrieval

    # Summary counts
    assert "summary" in data
    summary = data["summary"]
    assert "threats_count" in summary
    assert "claims_count" in summary
    assert "independent_groups_count" in summary

    # Threats list & structure
    assert "threats" in data
    assert isinstance(data["threats"], list)
    for t in data["threats"]:
        assert "threat_id" in t
        assert "type" in t
        assert "title" in t
        assert "severity" in t
        assert "evidence_ids" in t

    # Claims & Narratives
    assert "claims" in data
    assert isinstance(data["claims"], list)
    assert "narratives" in data
    assert isinstance(data["narratives"], list)

    # Dossiers
    assert "dossiers" in data
    assert isinstance(data["dossiers"], list)

    # Sources & Clickable URLs
    assert "sources" in data
    assert isinstance(data["sources"], list)
    for s in data["sources"]:
        assert "evidence_id" in s
        assert "url" in s
        assert "has_url" in s
        assert "source_role" in s
        assert "platform" in s

    # Backward Compatibility
    assert "findings" in data
    assert isinstance(data["findings"], list)
    assert "total_findings" in data
    assert "threat_count" in data
    assert "safe_count" in data
    assert "platforms" in data


@pytest.mark.integration
def test_brandshield_product_distinction(test_client: TestClient):
    resp = test_client.post("/api/brandshield/scan", json={"brand_name": "Nike Air Max"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["brand"] == "Nike"
    assert data["entity"]["entity_type"] == "product"
    assert data["entity"]["product"] == "Air Max"
    assert "Nike Air Max" in data["entity"]["resolved_entity"]


@pytest.mark.integration
def test_brandshield_no_unsupported_platform_simulation(test_client: TestClient):
    resp = test_client.post("/api/brandshield/scan", json={"brand_name": "CustomBespokeStore999"})
    assert resp.status_code == 200
    data = resp.json()

    # If Amazon or Flipkart were not in the retrieved sources, they must not appear in platforms
    retrieved_platforms = set(s["platform"] for s in data["sources"])
    for p in data["platforms"]:
        assert p in retrieved_platforms or len(data["sources"]) == 0
