"""
Aegis Protocol — Integration Tests: Personal Watch 2.0 Workflow
===============================================================
Tests:
- Full end-to-end API scan via POST /api/personal/scan
- Verification of 2.0 response schema (dossiers, claims, channel_health, timeline)
- Change detection ("WHAT CHANGED?") across consecutive scans
- Backward compatibility with legacy response keys
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_personal_watch_full_api_workflow(test_client: TestClient):
    payload = {
        "name": "Sam Altman",
        "category": "executive",
        "official_handles": {"twitter": "@sama"},
        "aliases": ["Sama"]
    }

    resp = test_client.post("/api/personal/scan", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # 1. Subject & metadata verification
    assert data["vip_name"] == "Sam Altman"
    assert "subject" in data
    assert data["subject"]["canonical_name"] == "Sam Altman"
    assert data["subject"]["category"] == "executive"
    assert "scan_metadata" in data

    # 2. Channel health
    assert "channel_health" in data
    health = data["channel_health"]
    assert "news" in health
    assert "web" in health
    assert "twitter" in health
    assert "reddit" in health

    # 3. Evidence & source links
    assert "evidence" in data
    assert "summary" in data
    assert isinstance(data["evidence"], list)

    for ev in data["evidence"][:5]:
        assert "evidence_id" in ev
        assert "url" in ev
        assert ev["url"] != "#"
        assert "platform" in ev
        assert "source" in ev

    # 4. Threats, Claims & Dossiers
    assert "threats" in data
    assert "claims" in data
    assert "dossiers" in data
    assert "timeline" in data
    assert "spread_analysis" in data
    assert "changes" in data

    for d in data["dossiers"][:3]:
        assert "threat_id" in d
        assert "risk_level" in d
        assert "evidence_chain" in d
        assert "why_flagged" in d


@pytest.mark.integration
def test_personal_watch_change_detection_on_second_scan(test_client: TestClient):
    payload = {
        "name": "Elon Musk",
        "category": "executive",
        "official_handles": {"twitter": "@elonmusk"}
    }

    # First scan
    resp1 = test_client.post("/api/personal/scan", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "changes" in data1
    assert len(data1["changes"]) > 0

    # Second scan
    resp2 = test_client.post("/api/personal/scan", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "changes" in data2
    assert isinstance(data2["changes"], list)


@pytest.mark.integration
def test_personal_watch_backward_compatibility(test_client: TestClient):
    # Minimal legacy request payload
    legacy_payload = {
        "name": "Narendra Modi"
    }

    resp = test_client.post("/api/personal/scan", json=legacy_payload)
    assert resp.status_code == 200
    data = resp.json()

    # Verify all legacy keys exist with expected types
    assert "vip_name" in data
    assert "total_mentions" in data and isinstance(data["total_mentions"], int)
    assert "web_mentions" in data and isinstance(data["web_mentions"], int)
    assert "twitter_mentions" in data and isinstance(data["twitter_mentions"], int)
    assert "mentions" in data and isinstance(data["mentions"], list)
    assert "threats" in data and isinstance(data["threats"], list)
    assert "high_risk_count" in data and isinstance(data["high_risk_count"], int)
    assert "medium_risk_count" in data and isinstance(data["medium_risk_count"], int)
    assert "low_risk_count" in data and isinstance(data["low_risk_count"], int)
    assert "alerts_sent" in data and isinstance(data["alerts_sent"], int)
