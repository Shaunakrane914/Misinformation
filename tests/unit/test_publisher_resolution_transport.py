"""Offline provider fallback controls, never a live article-recall claim."""
import pytest

from backend.infrastructure.acquisition.adapters.web.search_observations import result_fit


@pytest.mark.parametrize("url", ["https://news.google.com/rss/articles/opaque",
    "https://www.bing.com/news/apiclick.aspx?opaque=1", "https://bing.com/ck/a?opaque=1"])
def test_matching_wrapper_is_not_a_resolved_publisher(url):
    title = "Elena Rivera discusses documented research findings"
    score, reason = result_fit(title, title, "", url, "publisher_url_resolution")
    assert reason == "UNRESOLVED_SEARCH_WRAPPER"


def test_wrapper_is_still_an_inspectable_ordinary_discovery_lead():
    title = "Elena Rivera discusses documented research findings"
    assert result_fit(title, title, "", "https://news.google.com/rss/articles/opaque", "harvest_statement")[1] is None


def test_direct_publisher_still_requires_original_title_fit():
    title = "Elena Rivera discusses documented research findings"
    assert result_fit(title, title, "", "https://publisher.example/story", "publisher_url_resolution")[1] is None
    assert result_fit(title, "Unrelated sporting match", "", "https://publisher.example/story", "publisher_url_resolution")[1] == "HEADLINE_MISMATCH"


def test_matching_wrapper_does_not_stop_existing_yahoo_fallback(monkeypatch):
    from backend.services.agent_reach.native.router import NativeRouter
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    title = "Elena Rivera discusses documented research findings"
    observed = "https://publisher.example/observed-research-story"
    feed = ("<rss><channel><item><title>" + title + "</title>"
            "<link>https://news.google.com/rss/articles/opaque</link></item></channel></rss>")
    page = ('<div class="algo"><h3><a href="' + observed + '">' + title + '</a></h3>'
            '<div class="compText"><p>Observed research findings.</p></div></div>')
    calls = []
    def fetch(url, **kwargs):
        calls.append(url)
        body = page if "yahoo" in url else feed
        return BoundedHTTPResponse(body=body.encode(), endpoint=url, status_code=200,
            content_type="text/html" if "yahoo" in url else "application/rss+xml",
            headers={}, latency_ms=1, attempts=1)
    monkeypatch.setattr("backend.infrastructure.acquisition.routing.router.fetch_public_http", fetch)
    router = object.__new__(NativeRouter)
    results = router._execute_web_search(title, limit=3, query_class="publisher_url_resolution")
    assert any("yahoo" in url for url in calls)
    assert [fragment.url for fragment in results] == [observed]
