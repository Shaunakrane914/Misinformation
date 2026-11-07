"""Offline reproductions for acquired-body metadata and reader selection losses."""
import json

import pytest

from backend.infrastructure.acquisition.adapters import expanded_catalog, expansion_safety
from backend.infrastructure.acquisition.adapters.news import substack
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse, ProviderHTTPError
from backend.services.agent_reach.channels import CandidateSource, FetchedDocument, RetrievalRequest
from backend.services.research.deep_reader import DeepReader
from backend.services.research.research_models import EvidenceItem


def response(url, body, content_type="application/json"):
    return BoundedHTTPResponse(body=body, endpoint=url, status_code=200, content_type=content_type,
        headers={}, latency_ms=1, attempts=1)


@pytest.mark.parametrize("status", [401, 403, 429])
def test_post_api_denial_cannot_activate_direct_html_reader(monkeypatch, status):
    monkeypatch.setattr(substack, "validate_url_safe", lambda _: (True, ""))
    monkeypatch.setattr(expansion_safety, "validate_url_safe", lambda _: (True, ""))
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        if "/api/" in url:
            raise ProviderHTTPError("Denied", endpoint=url, status_code=status, network_observed=True, attempts=1)
        return response(url, b"<article><p>This response must never be requested after access denial.</p></article>", "text/html")

    monkeypatch.setattr(expansion_safety, "_fetch", fetch)
    candidate = CandidateSource(url="https://orion.substack.com/p/observed-report")
    with pytest.raises(ProviderHTTPError) as error:
        substack.SubstackAdapter().acquire(candidate, RetrievalRequest())
    assert error.value.status_code == status
    assert calls == ["https://orion.substack.com/api/v1/posts/observed-report"]


def test_expanded_html_retains_captured_date_and_observed_document_links(monkeypatch):
    adapter = expanded_catalog.get_expanded_adapters()["news_wires"]
    url = "https://www.bbc.com/news/observed-report"
    text = "Orion Devices announced a battery recycling facility with a processing capacity of forty thousand tonnes annually. "
    html = ('<html><head><title>Orion Devices battery recycling</title>'
        '<meta property="article:published_time" content="2026-10-30T12:00:00Z"></head>'
        '<body><article><h1>Orion Devices battery recycling</h1>' + '<p>' + text * 3 + '</p>' * 1
        + '<p>The company said construction will begin next year and remains subject to local approval.</p>'
        '<a href="/news/observed-followup">Orion Devices original announcement</a></article></body></html>')
    monkeypatch.setattr(adapter, "acquire", lambda *a: FetchedDocument(url=url, status="SUCCESS", raw_content=html))
    result = expanded_catalog.read_expanded_url(url)
    assert result["page_metadata"]["published"] == "2026-10-30T12:00:00Z"
    assert result["page_metadata"]["observed_links"][0]["url"] == "https://www.bbc.com/news/observed-followup"
    item = EvidenceItem(id="captured", canonical_url=url, title="Discovery title", content=result["content"],
        metadata={"read_success": True, "temporal_required": True, "page_metadata": result["page_metadata"]})
    from backend.services.research.body_context import reconcile_captured_context
    reconcile_captured_context(item)
    assert item.published_at == "2026-10-30T12:00:00Z"


def test_captured_post_api_date_is_not_discarded(monkeypatch):
    monkeypatch.setattr(substack, "validate_url_safe", lambda _: (True, ""))
    post = {"title": "Orion Devices statement", "post_date": "2026-10-30T11:00:00Z",
        "publishedBylines": [{"name": "Morgan Vale"}],
        "body_html": "<p>" + "Orion Devices announced a battery recycling facility and published its original production estimates. " * 6 + "</p>"}
    monkeypatch.setattr(substack, "fetch_public_http", lambda url, **kw: response(url, json.dumps(post).encode()))
    result = expanded_catalog.read_expanded_url("https://orion.substack.com/p/observed-report")
    assert result["page_metadata"]["published"] == post["post_date"]
    assert result["page_metadata"]["author"] == "Morgan Vale"


@pytest.mark.parametrize("path", ["instagram.com-impersonation", "facebook.com-warning", "threads.net-report", "bilibili.com-analysis"])
def test_platform_name_in_article_path_does_not_disable_reader(path):
    item = EvidenceItem(id="observed", canonical_url="https://publisher.example/" + path,
        title="Documented impersonation report", metadata={"candidate_score": .95})
    selected, _ = DeepReader()._select_read_candidates([item], max_reads=1)
    assert selected == [item]


@pytest.mark.parametrize("host", ["instagram.com", "www.facebook.com", "threads.net", "www.bilibili.com"])
def test_actual_restricted_platform_hosts_keep_existing_exclusion(host):
    item = EvidenceItem(id="observed", canonical_url="https://" + host + "/observed",
        title="Observed platform post", metadata={"candidate_score": .95})
    selected, _ = DeepReader()._select_read_candidates([item], max_reads=1)
    assert selected == []


def test_raw_pool_does_not_restore_rejected_feed_date_after_body_read():
    from backend.services.research.raw_pool import RawAcquisitionPool
    from backend.services.research.body_context import reconcile_captured_context
    item = EvidenceItem(id="observed", canonical_url="https://publisher.example/report",
        title="Orion Devices battery recycling", published_at="2026-10-30T12:00:00Z")
    pool = RawAcquisitionPool("date-provenance")
    pool.add_candidate(item)
    item.content = "Orion Devices announced a new battery recycling facility. " * 12
    item.acquired_id = "actual-read"
    item.content_depth = "PARTIAL_CONTENT"
    item.metadata.update(read_success=True, temporal_required=True, page_metadata={"body_kind": "ARTICLE_BODY"})
    reconcile_captured_context(item)
    assert not item.published_at
    pool.add_capture(item)
    source = pool.export(include_text=True)["sources"][0]
    assert source["published_at"] is None
    assert source["discovery_published_at"] == "2026-10-30T12:00:00Z"
