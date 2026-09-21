"""
Integration tests for Trending Agent 2.0 workflow & API endpoints.
Validates end-to-end execution of /api/trending/scan in Entity Mode & Discovery Mode,
historical snapshot tracking, /api/trending-news, and backward compatibility.
"""

import pytest
from starlette.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_trending_scan_entity_mode_api(client: TestClient, monkeypatch):
    """Test POST /api/trending/scan in Entity Mode with mocked or live retrieval."""
    from backend.agents.trending_agent import TrendingAgent, TrendEvidence

    # Mock fetch_news to be fast and deterministic
    def mock_fetch_news(self, keyword, limit=8):
        return [
            {
                "title": f"{keyword} announces new film project with global studio",
                "link": "https://reuters.com/entertainment/announcement-1",
                "published": "2026-09-21T10:00:00Z",
                "source": "Reuters",
                "summary": "Official announcement confirmed by studio heads."
            },
            {
                "title": f"Fans react to {keyword} new project announcement",
                "link": "https://variety.com/reactions-1",
                "published": "2026-09-21T10:30:00Z",
                "source": "Variety",
                "summary": "Social media reception to the announcement."
            }
        ]

    monkeypatch.setattr(TrendingAgent, "fetch_news", mock_fetch_news)

    resp = client.post("/api/trending/scan", json={
        "asset_name": "Deepika Padukone",
        "mode": "entity",
        "category": "entertainment"
    })

    assert resp.status_code == 200
    data = resp.json()

    # Verify 2.0 schema elements
    assert data["mode"] == "entity"
    assert data["entity_resolution"]["resolved_entity"] == "Deepika Padukone"
    assert "retrieval" in data
    assert "channels" in data["retrieval"]
    assert "trends" in data
    assert len(data["trends"]) >= 1

    t = data["trends"][0]
    assert "topic" in t
    assert "velocity" in t
    assert "origin" in t
    assert "misinformation_risk" in t

    # Verify evidence records and clickable URLs
    assert "evidence" in data
    assert len(data["evidence"]) >= 2
    assert all(e["url"].startswith("http") for e in data["evidence"] if e["url"] != "Source URL unavailable")

    # Verify backward compatibility fields
    assert "asset_name" in data
    assert "threats" in data
    assert "sources" in data
    assert "counts" in data


def test_trending_scan_discovery_mode_api(client: TestClient, monkeypatch):
    """Test POST /api/trending/scan in Discovery Mode."""
    from backend.agents.trending_agent import TrendingAgent

    def mock_fetch_news(self, keyword, limit=8):
        return [
            {
                "title": "Top cultural festival begins in Mumbai",
                "link": "https://thehindu.com/festival",
                "published": "2026-09-21T08:00:00Z",
                "source": "The Hindu",
                "summary": "Festival launches today with wide public turnout."
            }
        ]

    monkeypatch.setattr(TrendingAgent, "fetch_news", mock_fetch_news)

    resp = client.post("/api/trending/scan", json={
        "query": "What's trending in India?",
        "mode": "discovery"
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "discovery"
    assert "India" in data["entity_resolution"]["resolved_entity"]
    assert len(data["trends"]) >= 1


def test_trending_repeat_scan_velocity_snapshot(client: TestClient, monkeypatch):
    """Test that two consecutive scans update historical time-series."""
    from backend.agents.trending_agent import TrendingAgent

    def mock_fetch_news(self, keyword, limit=8):
        return [
            {
                "title": "Tech company unveils open frontier AI architecture",
                "link": "https://techcrunch.com/ai-launch",
                "published": "2026-09-21T07:00:00Z",
                "source": "TechCrunch",
                "summary": "New model architecture released open weights."
            }
        ]

    monkeypatch.setattr(TrendingAgent, "fetch_news", mock_fetch_news)

    # Scan 1
    resp1 = client.post("/api/trending/scan", json={"asset_name": "OpenAI"})
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Scan 2
    resp2 = client.post("/api/trending/scan", json={"asset_name": "OpenAI"})
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Chart history should record consecutive observation points
    assert len(data2["chart_history"]) >= 2
    assert "signals_per_hour" in data2["trends"][0]["velocity"]


def test_trending_news_endpoint(client: TestClient, monkeypatch):
    """Test GET /api/trending-news endpoint."""
    from backend.agents.trending_agent import TrendingAgent

    def mock_fetch_targeted_news(self, query, window_mins=1440):
        return [
            {
                "title": f"Market rally impacts {query}",
                "link": "https://bloomberg.com/market-rally",
                "published": "2026-09-21T11:00:00Z",
                "age_minutes": 10,
                "source": "Market News"
            }
        ]

    monkeypatch.setattr(TrendingAgent, "fetch_targeted_news", mock_fetch_targeted_news)

    resp = client.get("/api/trending-news")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "count" in data
    assert data["count"] > 0
    assert data["items"][0]["link"].startswith("http")
