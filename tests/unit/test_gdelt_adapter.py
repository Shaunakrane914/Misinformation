"""Unit tests for GDELT DOC API discovery adapter."""
import json
from unittest.mock import MagicMock, patch

from backend.infrastructure.acquisition.adapters.news.gdelt import GdeltDocAdapter, parse_gdelt_timestamp
from backend.infrastructure.acquisition.adapters.expanded_catalog import get_expanded_adapters, DOMAIN_DISCOVERY, expanded_query
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import CandidateSource, RetrievalRequest
from backend.services.research.research_models import ResearchRequest


def test_parse_gdelt_timestamp():
    assert parse_gdelt_timestamp("20261025T123000Z") == "2026-10-25T12:30:00+00:00"
    assert parse_gdelt_timestamp("20261025123000") == "2026-10-25T12:30:00+00:00"
    assert parse_gdelt_timestamp("20261025") == "2026-10-25T00:00:00+00:00"
    assert parse_gdelt_timestamp(None) is None
    assert parse_gdelt_timestamp("invalid") is None


def test_gdelt_adapter_discovery_only_and_acquire_unsupported():
    adapter = GdeltDocAdapter()
    cand_foreign = CandidateSource(url="https://reuters.com/article/battery-recycling-facility")
    assert adapter.can_handle(cand_foreign) is False
    doc_foreign = adapter.acquire(cand_foreign, RetrievalRequest())
    assert doc_foreign.status == "URL_POLICY_REJECTED"

    cand_owned = CandidateSource(url="https://api.gdeltproject.org/api/v2/doc/doc?query=test")
    doc_owned = adapter.acquire(cand_owned, RetrievalRequest())
    assert doc_owned.status == "UNSUPPORTED_DIRECT_ACQUISITION"
    assert "discovery-only" in doc_owned.failure_reason


def test_gdelt_adapter_discover_success():
    adapter = GdeltDocAdapter()
    sample_response = {
        "articles": [
            {
                "url": "https://reuters.com/business/battery-recycling-growth-2026",
                "title": "Battery Recycling Facilities Expand Globally",
                "seendate": "20261025T140000Z",
                "domain": "reuters.com",
                "language": "English",
                "sourcecountry": "United States",
            },
            {
                "url": "https://127.0.0.1/internal-status",  # SSRF candidate - must be excluded
                "title": "Internal Status",
                "seendate": "20261025T140000Z",
                "domain": "internal",
            },
            {
                "url": "https://techcrunch.com/2026/10/25/circular-battery-economy",
                "title": "New Circular Economy Startups in Battery Recycling",
                "seendate": "20261024T180000Z",
                "domain": "techcrunch.com",
                "language": "English",
                "sourcecountry": "United States",
            },
        ]
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_response).encode("utf-8"),
        endpoint="https://api.gdeltproject.org/api/v2/doc/doc",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=120,
        attempts=1,
    )
    def mock_validate(url):
        if "127.0.0.1" in url or "localhost" in url:
            return (False, "SSRF_LOOPBACK")
        return (True, "")

    with patch("backend.infrastructure.acquisition.adapters.news.gdelt.fetch_public_http", return_value=mock_resp), \
         patch("backend.infrastructure.acquisition.adapters.news.gdelt.validate_url_safe", side_effect=mock_validate), \
         patch("backend.infrastructure.acquisition.adapters.expansion_safety.validate_url_safe", side_effect=mock_validate):
        candidates = adapter.discover("battery recycling", limit=5)
        # SSRF localhost was excluded, so 2 remain
        assert len(candidates) == 2
        assert candidates[0].url == "https://reuters.com/business/battery-recycling-growth-2026"
        assert candidates[0].platform == "gdelt"
        assert candidates[0].metadata["discovery_only"] is True
        assert candidates[0].metadata["virality_measured"] is False
        assert candidates[0].metadata["published"] == "2026-10-25T14:00:00+00:00"
        assert candidates[1].url == "https://techcrunch.com/2026/10/25/circular-battery-economy"


def test_gdelt_adapter_handles_throttling_and_non_200():
    adapter = GdeltDocAdapter()
    mock_resp = BoundedHTTPResponse(
        body=b"Please limit requests to one every 5 seconds",
        endpoint="https://api.gdeltproject.org/api/v2/doc/doc",
        status_code=429,
        content_type="text/plain",
        headers={},
        latency_ms=80,
        attempts=1,
    )
    with patch("backend.infrastructure.acquisition.adapters.news.gdelt.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("battery recycling", limit=3)
        assert candidates == []


def test_gdelt_catalog_wiring():
    assert "gdelt" in get_expanded_adapters()
    assert DOMAIN_DISCOVERY["trending"] == "gdelt"
    req = ResearchRequest(target="battery recycling", domain="trending", agent_name="trending")
    q = expanded_query(req)
    assert q is not None
    assert q["channel"] == "expanded_sources"
    assert q["query_text"] == "gdelt|battery recycling"
