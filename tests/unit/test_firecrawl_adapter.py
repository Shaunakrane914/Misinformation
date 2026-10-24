"""
Offline Unit Tests for Firecrawl Web Acquisition Adapter
=========================================================
Tests SSRF validation, honest provenance, transport failure classification,
bounded payloads, fallback execution, and PlatformAdapter contract compliance.
"""

import json
from unittest.mock import patch
import pytest
from backend.infrastructure.acquisition.adapters.web.firecrawl import FirecrawlAdapter
from backend.infrastructure.acquisition.adapters.web.jina import execute_web_read
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse, ProviderHTTPError
from backend.services.agent_reach.channels import CandidateSource, RetrievalMode, RetrievalRequest


def make_mock_response(status_code: int, body_dict: dict) -> BoundedHTTPResponse:
    raw_body = json.dumps(body_dict).encode("utf-8")
    return BoundedHTTPResponse(
        body=raw_body,
        endpoint="https://api.firecrawl.dev/v1/scrape",
        status_code=status_code,
        content_type="application/json",
        headers={"content-type": "application/json"},
        latency_ms=120,
        attempts=1,
        redirect_chain=(),
    )


def test_firecrawl_configuration_and_health():
    # Cloud without key: requires configuration
    cloud_adapter = FirecrawlAdapter(base_url="https://api.firecrawl.dev", api_key="")
    assert not cloud_adapter.is_configured()
    assert cloud_adapter.health()["status"] == "CONFIG_REQUIRED"

    # Cloud with key: available
    cloud_keyed = FirecrawlAdapter(base_url="https://api.firecrawl.dev", api_key="fc-test-key-12345")
    assert cloud_keyed.is_configured()
    assert cloud_keyed.health()["status"] == "CONFIGURED_UNVERIFIED"
    assert cloud_keyed.health()["has_api_key"] is True

    # A local/private endpoint is not silently exempt from public egress policy.
    local_adapter = FirecrawlAdapter(base_url="http://localhost:3002", api_key="")
    assert not local_adapter.is_configured()
    assert local_adapter.health()["status"] == "CONFIG_REQUIRED"


def test_firecrawl_ssrf_protection_blocks_private_targets():
    adapter = FirecrawlAdapter(base_url="https://api.firecrawl.dev", api_key="fc-key")

    # AWS metadata IP
    res1 = adapter.scrape_article("http://169.254.169.254/latest/meta-data/")
    assert res1["status"] in ("blocked_ssrf", "failed")
    assert res1["failure_kind"] == "SSRF_BLOCKED"

    # Localhost loopback
    res2 = adapter.scrape_article("http://127.0.0.1:8080/admin")
    assert res2["status"] in ("blocked_ssrf", "failed")
    assert res2["failure_kind"] == "SSRF_BLOCKED"


def test_firecrawl_successful_article_scraping_and_provenance(monkeypatch):
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.web.firecrawl.is_safe_url", lambda u: (True, "safe"))

    mock_payload = {
        "success": True,
        "data": {
            "markdown": "## Investigation into Counterfeit Semiconductor Supply\n\nIndependent forensic analysis confirmed altered date codes and sandblasted package markings on commercial lots delivered through unverified distributors.",
            "metadata": {
                "title": "Counterfeit Semiconductor Investigation Report",
                "description": "Analysis of fraudulent chip marking schemes.",
                "canonicalURL": "https://trusted-news.com/investigations/semiconductors-2026",
                "publishedTime": "2026-10-18T14:30:00Z",
                "language": "en",
                "statusCode": 200,
            },
        },
    }

    def mock_fetcher(endpoint, **kwargs):
        return make_mock_response(200, mock_payload)

    adapter = FirecrawlAdapter(
        base_url="https://api.firecrawl.dev",
        api_key="fc-key",
        http_fetcher=mock_fetcher,
    )

    result = adapter.scrape_article("https://trusted-news.com/investigations/semiconductors-2026")
    assert result["status"] == "success"
    assert "Counterfeit Semiconductor" in result["title"]
    assert "Independent forensic analysis" in result["content"]
    assert result["canonical_url"] == "https://trusted-news.com/investigations/semiconductors-2026"
    assert result["published"] == "2026-10-18T14:30:00Z"
    assert result["backend"] == "firecrawl-v1"
    assert result["raw_capture"]["source"] == "firecrawl_api"
    assert len(result["raw_capture"]["sha256"]) == 64


def test_firecrawl_empty_extraction_fails_gracefully(monkeypatch):
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.web.firecrawl.is_safe_url", lambda u: (True, "safe"))

    mock_payload = {
        "success": True,
        "data": {
            "markdown": "Short",
            "metadata": {"title": "Empty Page"},
        },
    }

    def mock_fetcher(endpoint, **kwargs):
        return make_mock_response(200, mock_payload)

    adapter = FirecrawlAdapter(
        base_url="https://api.firecrawl.dev",
        api_key="fc-key",
        http_fetcher=mock_fetcher,
    )

    result = adapter.scrape_article("https://example.com/empty")
    assert result["status"] == "failed"
    assert result["failure_kind"] == "EMPTY_EXTRACTION"


def test_firecrawl_provider_error_classification(monkeypatch):
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.web.firecrawl.is_safe_url", lambda u: (True, "safe"))

    def mock_fetcher_403(endpoint, **kwargs):
        raise ProviderHTTPError(
            "HTTP 403 Forbidden: Cloudflare challenge",
            endpoint="https://api.firecrawl.dev/v1/scrape",
            status_code=403,
            failure_kind="ACCESS_DENIED",
        )

    adapter = FirecrawlAdapter(
        base_url="https://api.firecrawl.dev",
        api_key="fc-key",
        http_fetcher=mock_fetcher_403,
    )

    result = adapter.scrape_article("https://protected-site.com/article")
    assert result["status"] == "failed"
    assert result["failure_kind"] == "ACCESS_DENIED"


def test_firecrawl_platform_adapter_contract(monkeypatch):
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.web.firecrawl.is_safe_url", lambda u: (True, "safe"))

    mock_payload = {
        "success": True,
        "data": {
            "markdown": "# Quarterly Security Audit\n\nZero unauthorized key access incidents recorded during Q3 2026. The report describes the bounded observation period and does not independently establish that every system is safe.",
            "metadata": {"title": "Security Audit Report", "publishedTime": "2026-09-30"},
        },
    }

    adapter = FirecrawlAdapter(
        base_url="https://api.firecrawl.dev",
        api_key="fc-key",
        http_fetcher=lambda ep, **kw: make_mock_response(200, mock_payload),
    )

    candidate = CandidateSource(
        candidate_id="cand_fc_01",
        url="https://example.com/security-audit",
        title="Security Audit",
    )
    request = RetrievalRequest(query="security audit key access")

    # Acquire
    doc = adapter.acquire(candidate, request)
    assert doc.status == "SUCCESS"
    assert "Zero unauthorized key access incidents" in doc.raw_content
    assert doc.backend_id == "firecrawl-v1"

    # Normalize
    frags = adapter.normalize(doc, candidate, request)
    assert len(frags) == 1
    assert frags[0].content_depth == "SNIPPET"
    assert frags[0].raw_metadata["source_role"] == "UNVERIFIED_SOURCE"
    assert frags[0].actual_retrieval_channel == "firecrawl"
    assert frags[0].native_backend_id == "firecrawl-v1"


def test_execute_web_read_integrates_firecrawl_fallback(monkeypatch):
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.web.jina.is_safe_url", lambda u: (True, "safe"))
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.web.firecrawl.is_safe_url", lambda u: (True, "safe"))

    mock_payload = {
        "success": True,
        "data": {
            "markdown": "# Recovered Article Via Firecrawl\n\nJournalistic reporting acquired through a mocked reader response for an offline transport regression. This is not live acquisition proof.",
            "metadata": {"title": "Recovered Story", "publishedTime": "2026-10-21"},
        },
    }

    mock_fc = FirecrawlAdapter(
        base_url="https://api.firecrawl.dev",
        api_key="fc-key",
        http_fetcher=lambda ep, **kw: make_mock_response(200, mock_payload),
    )

    # Class simulating a failed native executor
    class FailingExecutor:
        def execute_web_read(self, url):
            raise RuntimeError("Native connection reset by peer")

    res = execute_web_read(
        "https://example.com/article-js-rendered",
        executor=FailingExecutor(),
        firecrawl_adapter=mock_fc,
    )

    assert res["status"] == "success"
    assert res["backend"] == "firecrawl-v1"
    assert res["fallback_used"] is True
    assert "Recovered Article Via Firecrawl" in res["markdown"]
