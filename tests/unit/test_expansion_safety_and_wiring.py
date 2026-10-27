"""Synthetic offline regressions; these do not establish live acquisition yield."""
import asyncio
import gzip
import threading
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from backend.infrastructure.acquisition.adapters import expansion_safety as safety
from backend.infrastructure.acquisition.adapters.expanded_catalog import (
    ExpandedSourceChannel, expanded_query, get_expanded_adapters, read_expanded_url,
)
from backend.services.agent_reach.channels import CandidateSource, FetchedDocument


@pytest.mark.parametrize("platform,variable", [
    ("reddit_deep", "REDDIT_APPROVED_ACCESS"), ("sec_edgar", "SEC_USER_AGENT"),
    ("sec_filings_full", "SEC_USER_AGENT"), ("factcheck", "GOOGLE_FACTCHECK_API_KEY"),
])
def test_missing_configuration_fails_before_transport(platform, variable, monkeypatch):
    monkeypatch.delenv(variable, raising=False)
    assert safety.policy_status(platform)


@pytest.mark.parametrize("url", [
    "https://substack.com.attacker.invalid/p/post", "https://attacker.invalid/substack.com",
    "https://user:password@substack.com/p/post", "file:///substack.com/post",
])
def test_host_identity_is_not_platform_label_or_substring(url):
    adapter = get_expanded_adapters()["substack"]
    assert not adapter.can_handle(CandidateSource(url=url, platform="substack"))


def test_reddit_direct_adapter_cannot_skip_access_gate(monkeypatch):
    from backend.infrastructure.acquisition.adapters.social.reddit_deep import RedditDeepAdapter
    from backend.services.agent_reach.channels import RetrievalRequest
    monkeypatch.delenv("REDDIT_APPROVED_ACCESS", raising=False)
    fetch = MagicMock(side_effect=AssertionError("No outbound call permitted"))
    monkeypatch.setattr(safety, "_fetch", fetch)
    result = RedditDeepAdapter().acquire(CandidateSource(url="https://www.reddit.com/r/test/comments/abc/post"), RetrievalRequest(task_type="READ"))
    assert result.status == "POLICY_BLOCKED"
    fetch.assert_not_called()


def test_tuple_false_is_rejected_before_fetch(monkeypatch):
    fetch = MagicMock()
    monkeypatch.setattr(safety, "validate_url_safe", lambda _: (False, "blocked"))
    monkeypatch.setattr(safety, "_fetch", fetch)
    with pytest.raises(PermissionError):
        safety.safe_fetch("https://substack.com/p/post")
    fetch.assert_not_called()


def test_compressed_entity_has_decoded_byte_limit():
    with pytest.raises(ValueError):
        safety.bounded_decode(gzip.compress(b"x" * 10001), 10000)
    assert safety.bounded_decode(gzip.compress(b"observed")) == b"observed"


@pytest.mark.parametrize("xml", ["<!DOCTYPE x><x/>", '<!ENTITY x "unsafe"><x/>'])
def test_xml_declarations_rejected(xml):
    with pytest.raises(ValueError):
        safety.parse_bounded_xml(xml)


def test_unrelated_substack_posts_do_not_fill_limit(monkeypatch):
    from backend.infrastructure.acquisition.adapters.news import substack
    monkeypatch.setattr(substack, "validate_url_safe", lambda _: (True, ""))
    response = MagicMock(status_code=200, body=b'[{"title":"Garden design","subtitle":"Flowers","slug":"garden"}]')
    monkeypatch.setattr(substack, "fetch_public_http", lambda *a, **k: response)
    assert substack.SubstackAdapter().discover("Elena Rivera", 3) == []


def test_observed_external_publisher_is_a_lead_not_owned_adapter_body(monkeypatch):
    from backend.infrastructure.acquisition.adapters.news import substack
    from backend.services.agent_reach.channels import RetrievalRequest
    monkeypatch.setattr(substack, "validate_url_safe", lambda _: (True, ""))
    monkeypatch.setattr(safety, "validate_url_safe", lambda _: (True, ""))
    response = MagicMock(status_code=200, body=b'[{"title":"Orion Research","canonical_url":"https://publisher.example/observed"}]')
    monkeypatch.setattr(substack, "fetch_public_http", lambda *a, **k: response)
    adapter = substack.SubstackAdapter()
    lead = adapter.discover("Orion Research", 1)[0]
    assert lead.url == "https://publisher.example/observed" and lead.metadata["discovery_only"]
    assert not adapter.can_handle(lead)
    assert adapter.acquire(lead, RetrievalRequest(task_type="READ")).status == "URL_POLICY_REJECTED"


def test_feed_summary_is_not_an_acquired_article(monkeypatch):
    from backend.infrastructure.acquisition.adapters.news import wires_adapter
    from backend.services.agent_reach.channels import RetrievalRequest
    monkeypatch.setattr(wires_adapter, "validate_url_safe", lambda _: (True, ""))
    fetch = MagicMock(side_effect=TimeoutError())
    monkeypatch.setattr(wires_adapter, "fetch_public_http", fetch)
    candidate = CandidateSource(url="https://www.bbc.com/news/observed",
                                metadata={"full_content": "A feed summary is not the article"})
    document = wires_adapter.NewswireAdapter().acquire(candidate, RetrievalRequest(task_type="READ"))
    assert document.status != "SUCCESS"
    fetch.assert_called_once()


def test_navigation_page_cannot_become_full_article():
    from backend.infrastructure.acquisition.adapters.news.wires_adapter import NewswireAdapter
    from backend.services.agent_reach.channels import RetrievalRequest
    url = "https://www.bbc.com/"
    document = FetchedDocument(url=url, status="SUCCESS", raw_content="<html><nav>" + "Home Products Contact " * 200 + "</nav></html>")
    fragments = NewswireAdapter().normalize(document, CandidateSource(url=url), RetrievalRequest())
    assert all(fragment.content_depth != "FULL_ARTICLE" for fragment in fragments)
    assert not fragments or all(fragment.content.strip() for fragment in fragments)


def test_feed_rejects_declarations_and_labels_summaries():
    from backend.infrastructure.acquisition.adapters.news.feed_discovery import UniversalFeedDiscovery
    assert UniversalFeedDiscovery.parse_feed_content('<!DOCTYPE x><x/>', "https://www.bbc.com/feed") == []
    result = UniversalFeedDiscovery.parse_feed_content('<rss version="2.0"><channel><title>BBC</title><item><title>Observed</title><link>https://www.bbc.com/news/story</link><description>Feed observation</description></item></channel></rss>', "https://www.bbc.com/feed")
    assert result[0].content_depth == "SYNDICATED_SUMMARY"
    assert result[0].raw_metadata["linked_article_retrieved"] is False


@pytest.mark.parametrize("domain,key", [
    ("financial", "yahoo_finance"), ("brand", "news_wires"),
    ("trending", "news_wires"), ("personal", "news_wires"),
])
def test_domain_discovery_leads_require_separate_native_body_read(domain, key, monkeypatch):
    from types import SimpleNamespace
    row = expanded_query(SimpleNamespace(domain=domain, target="Orion Research"))
    assert row["query_text"] == key + "|Orion Research"
    url = {"yahoo_finance": "https://finance.yahoo.com/news/orion-research.html",
           "news_wires": "https://www.bbc.com/news/orion-research",
           "bluesky": "https://bsky.app/profile/orion.test/post/abc",
           "substack": "https://orion.substack.com/p/research"}[key]
    adapter = get_expanded_adapters()[key]
    monkeypatch.setattr(adapter, "discover", lambda *a, **k: [CandidateSource(url=url, title="Orion Research", snippet="Discovery observation")])
    lead = ExpandedSourceChannel().search(row["query_text"])[0]
    assert lead.content == "" and lead.content_depth == "INDEX_SNIPPET"
    assert lead.raw_metadata["linked_article_retrieved"] is False
    # A recognized failed read remains a failure; its title/snippet is not a body.
    monkeypatch.setattr(adapter, "acquire", lambda *a: FetchedDocument(url=url, status="EMPTY_CONTENT"))
    if key == "bluesky":
        import backend.infrastructure.acquisition.adapters.expanded_catalog as catalog
        monkeypatch.setattr(catalog, "safe_fetch", lambda *a, **k: MagicMock(status_code=200, body=b'{}'))
    result = read_expanded_url(url)
    assert result["status"] == "failed" and result["content"] == ""


def test_observed_substack_body_reaches_shared_extraction(monkeypatch):
    from backend.services.agent_reach.channels import RetrievalRequest
    adapter = get_expanded_adapters()["substack"]
    url = "https://orion.substack.com/p/observed"
    paragraph = "Orion Research reported audited figures and described the underlying accounting methodology. " * 8
    html = "<article><h1>Orion Research</h1><p>" + paragraph + "</p></article>"
    document = FetchedDocument(url=url, status="SUCCESS", raw_content=paragraph,
        raw_metadata={"source_html": html, "source_html_basis": "CAPTURED_POST_BODY_HTML"})
    monkeypatch.setattr(adapter, "acquire", lambda *a: document)
    result = read_expanded_url(url, 5000)
    assert result["status"] == "success" and "accounting methodology" in result["content"]
    assert result["page_metadata"]["body_quality"]["body_kind"] == "ARTICLE_BODY"
    assert "source_html" not in result


def test_shared_service_and_native_dispatch_consume_expansion(monkeypatch):
    from backend.services.agent_reach import agent_reach_service
    from backend.infrastructure.acquisition.routing.router import native_router
    url = "https://orion.substack.com/p/observed"
    adapter = get_expanded_adapters()["substack"]
    monkeypatch.setattr(adapter, "discover", lambda *a, **k: [CandidateSource(url=url, title="Orion Research")])
    result = agent_reach_service.retrieve_many({"expanded_sources": ["substack|Orion"]},
        perform_reads=False, timeout=2, budget={"max_queries_per_channel": 1, "max_results_per_query": 1})
    assert len(result.fragments) == 1 and result.fragments[0].content == ""
    fragments, telemetry = native_router.execute_channel_query("expanded_sources", "substack|Orion", limit=1)
    assert len(fragments) == 1 and telemetry["outcome"] == "SEARCH_INDEX_DISCOVERY"


def test_all_adapter_transport_failures_are_not_empty_success(monkeypatch):
    from backend.infrastructure.acquisition.adapters.news import substack
    from backend.infrastructure.acquisition.network.http import ProviderHTTPError
    monkeypatch.setattr(substack, "validate_url_safe", lambda _: (True, ""))
    monkeypatch.setattr(safety, "validate_url_safe", lambda _: (True, ""))
    monkeypatch.setattr(safety, "_fetch", MagicMock(side_effect=TimeoutError()))
    with pytest.raises(ProviderHTTPError, match="discovery providers failed"):
        ExpandedSourceChannel().search("substack|Orion Research")


def test_saved_measurement_does_not_mix_snippets_or_duplicate_bodies():
    from scripts.evaluation.test_4_agents_word_extraction import measure_response
    body = {"content": "Actual captured paragraph", "content_depth": "FULL_ARTICLE"}
    result = measure_response({"evidence": [body, body,
        {"content": "Search card is not an acquired body", "content_depth": "INDEX_SNIPPET"}]})
    assert result["retained_body_records"] == 1
    assert result["retained_unique_body_words"] == 3
    assert result["usefulness_independently_reviewed"] is False
    assert result["twentyfold_acceptance"] == "NOT_EVALUATED"


def test_numeric_socket_backend_runs_resolver_off_loop(monkeypatch):
    import backend.infrastructure.acquisition.network.async_http as transport
    loop_thread = threading.get_ident()
    observed = []
    def resolve(*args, **kwargs):
        observed.append(threading.get_ident())
        return [(2, 1, 6, "", ("93.184.216.34", 443))]
    delegate = MagicMock()
    delegate.connect_tcp = AsyncMock(return_value=object())
    monkeypatch.setattr(transport, "resolve_public_addresses", resolve)
    asyncio.run(transport.PinnedNetworkBackend(delegate).connect_tcp("publisher.test", 443, 1))
    assert observed and observed[0] != loop_thread
    assert delegate.connect_tcp.call_args.args[0] == "93.184.216.34"
    assert type(transport.PinnedNetworkBackend()._default).__name__ == "AutoBackend"


def test_cross_origin_strips_mixed_case_and_client_defaults(monkeypatch):
    import backend.infrastructure.acquisition.network.async_http as transport
    import backend.infrastructure.acquisition.network.rate_limiter as pacing
    monkeypatch.setattr(transport, "is_safe_url", lambda _: (True, ""))
    monkeypatch.setattr(pacing.domain_rate_limiter, "acquire", AsyncMock(return_value=0))
    sent = []
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"captured body"
    async def handler(request):
        sent.append(request)
        if len(sent) == 1:
            return httpx.Response(302, headers={"location": "https://other.test/article"}, stream=Stream())
        return httpx.Response(200, stream=Stream())
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), auth=("private", "private"),
            headers={"COOKIE": "private", "X-Api-Key": "private"}) as client:
            return await transport.fetch_public_async_http("https://first.test/article",
                headers={"AUTHORIZATION": "private"}, client=client)
    result = asyncio.run(run())
    assert result.body == b"captured body"
    assert "authorization" in sent[0].headers
    assert not {"authorization", "cookie", "x-api-key"} & set(sent[1].headers)


def test_total_deadline_covers_slow_body(monkeypatch):
    import backend.infrastructure.acquisition.network.async_http as transport
    import backend.infrastructure.acquisition.network.rate_limiter as pacing
    monkeypatch.setattr(transport, "is_safe_url", lambda _: (True, ""))
    monkeypatch.setattr(pacing.domain_rate_limiter, "acquire", AsyncMock(return_value=0))
    closed = []
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            await asyncio.sleep(1)
            yield b"too late"
        async def aclose(self):
            closed.append(True)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, stream=Stream()))) as client:
            with pytest.raises(TimeoutError):
                await transport.fetch_public_async_http("https://first.test/article", timeout=.05, client=client)
    asyncio.run(run())
    assert closed
