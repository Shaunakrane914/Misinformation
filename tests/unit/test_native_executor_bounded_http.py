"""Adapter contracts for the shared bounded HTTP transport."""

import json
import gzip
import socket
from types import SimpleNamespace

import pytest

from backend.infrastructure.acquisition.adapters.web import jina
from backend.infrastructure.acquisition.network.http import (
    BoundedHTTPResponse,
    ProviderHTTPError,
)
from backend.infrastructure.acquisition.routing.channel_dispatcher import (
    ChannelQueryDispatcher,
)
from backend.services.agent_reach.native.executor import NativeExecutor, _caption_segments


def _response(body, endpoint="https://example.com/final", content_type="application/json"):
    if isinstance(body, str):
        body = body.encode("utf-8")
    return BoundedHTTPResponse(
        body=body,
        endpoint=endpoint,
        status_code=200,
        content_type=content_type,
        headers={"Content-Type": content_type},
        latency_ms=4,
        attempts=1,
    )


@pytest.fixture
def executor():
    # None of these adapter methods uses the runtime profile.  Avoid probing the
    # host environment so the request-construction tests remain deterministic.
    return object.__new__(NativeExecutor)


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
    ])


def test_github_request_is_allowlisted_and_uses_shared_transport(monkeypatch, executor):
    calls = []

    def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))
        return _response("[]", url)

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    result = executor.execute_github_rest_operation("octocat/Hello-World", "issues", limit=7)

    assert calls[0][0] == "https://api.github.com/repos/octocat/Hello-World/issues?per_page=10"
    assert calls[0][1]["max_bytes"] > 0
    assert result["operation"] == "github.issues"
    assert result["transport"]["endpoint"] == calls[0][0]
    assert result["transport"]["raw_body_sha256"]


def test_github_read_uses_bounded_contents_api_readme_without_raw_host(monkeypatch, executor):
    import base64

    calls = []
    repository = {
        "full_name": "owner/repo", "description": "Repository",
        "html_url": "https://github.com/owner/repo", "stargazers_count": 7,
    }
    readme = {
        "encoding": "base64", "content": base64.b64encode(b"# Verified README\nActual content").decode(),
        "path": "README.md", "sha": "abc123",
        "html_url": "https://github.com/owner/repo/blob/main/README.md",
    }

    def fake_fetch(url, **_kwargs):
        calls.append(url)
        return _response(json.dumps(readme if url.endswith("/readme") else repository), url)

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    result = executor.execute_github_rest_operation("owner/repo", "read")
    assert calls == [
        "https://api.github.com/repos/owner/repo",
        "https://api.github.com/repos/owner/repo/readme",
    ]
    assert result["items"][0]["readme"] == "# Verified README\nActual content"
    assert result["items"][0]["readme_sha"] == "abc123"
    assert result["items"][0]["readme_transport"]["raw_body_sha256"]


def test_github_collection_pagination_is_bounded_and_observed(monkeypatch, executor):
    calls = []

    def fake_fetch(url, **_kwargs):
        calls.append(url)
        response = _response(json.dumps([{"number": 1, "title": "Issue"}]), url)
        response.headers["Link"] = '<https://api.github.com/repos/owner/repo/issues?page=3>; rel="next"'
        return response

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    result = executor.execute_github_rest_operation("owner/repo", "issues", limit=4, page=2)
    assert calls == ["https://api.github.com/repos/owner/repo/issues?per_page=10&page=2"]
    assert result["pagination"] == {
        "page": 2, "per_page": 10, "provider_items_on_page": 1,
        "filtered_pull_requests": 0,
        "has_next_page": True, "next_page_supported": True,
    }
    from backend.services.agent_reach.native.errors import NativeReachError
    with pytest.raises(NativeReachError):
        executor.execute_github_rest_operation("owner/repo", "issues", page=6)
    assert len(calls) == 1


def test_github_issue_page_of_only_prs_is_empty_not_a_missing_repository(monkeypatch, executor):
    def fake_fetch(url, **_kwargs):
        response = _response(json.dumps([
            {"number": 1, "pull_request": {"url": "https://api.github.com/prs/1"}},
            {"number": 2, "pull_request": {"url": "https://api.github.com/prs/2"}},
        ]), url)
        response.headers["Link"] = '<https://api.github.com/repos/owner/repo/issues?page=2>; rel="next"'
        return response

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    result = executor.execute_github_rest_operation("owner/repo", "issues", limit=3)
    assert result["status"] == "EMPTY"
    assert result["items"] == []
    assert result["pagination"]["filtered_pull_requests"] == 2
    assert result["pagination"]["has_next_page"] is True


def test_github_issue_comment_followup_is_explicit_bounded_and_attributed(monkeypatch, executor):
    calls = []
    issues = [
        {"number": 4, "title": "Observed issue", "comments": 2},
        {"number": 5, "title": "Another discussed issue", "comments": 3},
        {"number": 6, "title": "Quiet issue", "comments": 0},
        {"number": 7, "title": "Outside lookup budget", "comments": 3},
    ]
    comments = [{
        "id": 9, "body": "Observed reply", "html_url": "https://github.com/owner/repo/issues/4#issuecomment-9",
        "user": {"login": "reply-author"}, "created_at": "2026-10-13T00:00:00Z",
    }]

    def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))
        response = _response(json.dumps(comments if "/comments?" in url else issues), url)
        if "/comments?" in url:
            response.headers["Link"] = '<https://api.github.com/next>; rel="next"'
        return response

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    result = executor.execute_github_rest_operation(
        "owner/repo", "issues", limit=4, include_comments=True, comment_limit=1,
    )
    assert [url for url, _kwargs in calls] == [
        "https://api.github.com/repos/owner/repo/issues?per_page=10",
        "https://api.github.com/repos/owner/repo/issues/4/comments?per_page=1",
        "https://api.github.com/repos/owner/repo/issues/5/comments?per_page=1",
    ]
    assert all(kwargs["timeout"] <= 5.0 and kwargs["max_bytes"] == 1_000_000
               for _url, kwargs in calls)
    assert result["follow_up_requests"] == 2
    assert result["items"][0]["comment_lookup_status"] == "SUCCESS"
    assert result["items"][0]["sampled_comments"][0]["author"] == "reply-author"
    assert result["items"][0]["comment_has_next_page"] is True
    assert result["items"][1]["comment_lookup_status"] == "SUCCESS"
    assert result["items"][2]["comment_lookup_status"] == "NOT_APPLICABLE_ZERO_COUNT"
    assert result["items"][3]["comment_lookup_status"] == "NOT_REQUESTED_BUDGET"


def test_github_zero_comment_issues_do_not_consume_followup_budget(monkeypatch, executor):
    calls = []

    def fake_fetch(url, **_kwargs):
        calls.append(url)
        if "/comments?" in url:
            return _response(json.dumps([{"id": 8, "body": "Observed reply"}]), url)
        return _response(json.dumps([
            {"number": 1, "comments": 0}, {"number": 2, "comments": 0},
            {"number": 3, "comments": 1},
        ]), url)

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    result = executor.execute_github_rest_operation("owner/repo", "issues", limit=3,
                                                     include_comments=True)
    assert result["follow_up_requests"] == 1
    assert calls[-1] == "https://api.github.com/repos/owner/repo/issues/3/comments?per_page=3"
    assert result["items"][2]["comment_lookup_status"] == "SUCCESS"


def test_github_comment_followup_rejects_unbounded_or_ambiguous_options(executor):
    from backend.services.agent_reach.native.errors import NativeReachError

    with pytest.raises(NativeReachError):
        executor.execute_github_rest_operation("owner/repo", "issues", include_comments="false")
    with pytest.raises(NativeReachError):
        executor.execute_github_rest_operation("owner/repo", "issues", include_comments=True,
                                               comment_limit=6)
    with pytest.raises(NativeReachError):
        executor.execute_github_rest_operation("owner/repo", "prs", include_comments=True)


def test_github_issue_comment_failure_preserves_issue_body(monkeypatch, executor):
    issue = {"number": 4, "title": "Observed issue", "body": "Issue evidence", "comments": 1}

    def fake_fetch(url, **_kwargs):
        if "/comments?" in url:
            raise ProviderHTTPError("not available", endpoint=url, status_code=403)
        return _response(json.dumps([issue]), url)

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    result = executor.execute_github_rest_operation("owner/repo", "issues", include_comments=True)
    assert result["status"] == "SUCCESS"
    assert result["items"][0]["body"] == "Issue evidence"
    assert result["items"][0]["comment_lookup_status"] == "FAILED"
    assert result["items"][0]["comment_http_status"] == 403
    assert "sampled_comments" not in result["items"][0]


def test_caption_segments_preserve_observed_timing_and_do_not_infer_audio():
    cues = """WEBVTT

00:01.000 --> 00:03.500
First factual claim

2
00:00:04,000 --> 00:00:06,200
Correction follows
"""
    assert _caption_segments(cues) == [
        {"start": "00:00:01.000", "end": "00:00:03.500", "text": "First factual claim"},
        {"start": "00:00:04.000", "end": "00:00:06.200", "text": "Correction follows"},
    ]


def test_transcript_file_carries_language_and_bounded_cues(monkeypatch, executor):
    from pathlib import Path

    monkeypatch.setattr("backend.services.agent_reach.native.executor.shutil.which", lambda _name: "yt-dlp")

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("-o") + 1].replace("%(id)s", "fixture.en"))
        output.with_suffix(".en.vtt").write_text(
            "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nObserved words\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("backend.services.agent_reach.native.executor.subprocess.run", fake_run)
    result = executor.execute_youtube_transcript("https://www.youtube.com/watch?v=fixture")
    assert result["status"] == "SUCCESS"
    assert result["caption_language"] == "en"
    assert result["caption_origin"] == "UNVERIFIED"
    assert result["segments"][0]["text"] == "Observed words"


def test_rss_preserves_feed_fields_without_claiming_linked_article(monkeypatch, executor, public_dns):
    from backend.services.agent_reach.native.normalizer import NativeNormalizer

    feed_xml = """<?xml version="1.0"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel><title>Official updates</title><item><title>Statement</title>
    <link>https://example.com/statement</link><guid>statement-1</guid>
    <author>Editorial team</author><category>Corrections</category>
    <pubDate>Sun, 11 Oct 2026 10:00:00 GMT</pubDate>
    <description>Short abstract</description><content:encoded><![CDATA[<p>Full syndicated statement text</p>]]></content:encoded>
    <enclosure url="https://example.com/audio.mp3" type="audio/mpeg" length="10"/>
    </item></channel></rss>"""
    monkeypatch.setattr(
        "backend.services.agent_reach.native.executor.fetch_public_http",
        lambda url, **_kwargs: _response(feed_xml, url, "application/rss+xml"),
    )
    result = executor.execute_rss_read("https://example.com/feed.xml")
    entry = result["items"][0]
    assert entry["guid"] == "statement-1"
    assert entry["author"] == "Editorial team"
    assert entry["categories"] == ["Corrections"]
    assert entry["enclosures"][0]["type"] == "audio/mpeg"
    assert entry["feed_content"]
    fragment = NativeNormalizer.normalize_rss_entries([entry])[0]
    assert fragment.content_depth == "FEED_ENTRY_CONTENT"
    assert "Full syndicated statement text" in fragment.content
    assert fragment.raw_metadata["linked_article_retrieved"] is False


def test_transport_proof_preserves_observed_redirect_chain(executor):
    response = BoundedHTTPResponse(
        body=b"evidence",
        endpoint="https://example.com/final",
        status_code=200,
        content_type="text/plain",
        headers={"Content-Type": "text/plain"},
        latency_ms=4,
        attempts=1,
        redirect_chain=("https://example.com/start", "https://example.com/final"),
    )
    transport = executor._bounded_http_transport(response)
    assert transport["requested_endpoint"] == "https://example.com/start"
    assert transport["redirect_chain"] == [
        "https://example.com/start", "https://example.com/final",
    ]
    assert len(transport["raw_body_sha256"]) == 64


@pytest.mark.parametrize(
    ("operation", "value", "expected"),
    [
        ("latest", "", "https://www.v2ex.com/api/topics/latest.json"),
        ("topic", "https://www.v2ex.com/t/123", "https://www.v2ex.com/api/topics/show.json?id=123"),
        ("replies", "123", "https://www.v2ex.com/api/replies/show.json?topic_id=123"),
    ],
)
def test_v2ex_operation_constructs_documented_endpoint(
    monkeypatch, executor, operation, value, expected
):
    calls = []
    monkeypatch.setattr(
        "backend.services.agent_reach.native.executor.fetch_public_http",
        lambda url, **_kwargs: calls.append(url) or _response("[]", url),
    )
    result = executor.execute_v2ex_operation(operation, value)
    assert calls == [expected]
    assert result["operation"] == f"v2ex.{operation}"


def test_v2ex_node_query_is_url_encoded(monkeypatch, executor):
    calls = []
    monkeypatch.setattr(
        "backend.services.agent_reach.native.executor.fetch_public_http",
        lambda url, **_kwargs: calls.append(url) or _response("[]", url),
    )
    executor.execute_v2ex_search("python & security")
    assert calls == [
        "https://www.v2ex.com/api/topics/show.json?node_name=python%20%26%20security"
    ]


def test_rss_and_xiaoyuzhou_public_pages_use_bounded_transport(monkeypatch, executor, public_dns):
    calls = []
    rss = """<?xml version="1.0"?><rss version="2.0"><channel><title>Fixture</title>
    <item><title>Episode</title><link>https://example.com/episode</link>
    <description>Evidence notes</description></item></channel></rss>"""

    xiaoyuzhou_document = json.dumps({
        "props": {"pageProps": {"podcast": {
            "pid": "64e6b4dc80c9ec4c5f1e0782",
            "title": "Fixture podcast",
            "description": "Official public description",
            "latestEpisodePubDate": "2026-01-01T00:00:00Z",
            "episodes": [{
                "eid": "6790c1c7181b314a5c314312",
                "title": "Episode",
                "description": "Evidence notes",
                "pubDate": "2026-01-01T00:00:00Z",
                "duration": 120,
            }],
        }}},
    })
    xiaoyuzhou_html = f'<script id="__NEXT_DATA__" type="application/json">{xiaoyuzhou_document}</script>'

    def fake_fetch(url, **_kwargs):
        calls.append(url)
        if "xiaoyuzhoufm.com" in url:
            return _response(xiaoyuzhou_html, url, "text/html")
        return _response(rss, url, "application/rss+xml")

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    rss_result = executor.execute_rss_read("https://example.com/show.xml")
    podcast_url = "https://www.xiaoyuzhoufm.com/podcast/64e6b4dc80c9ec4c5f1e0782"
    podcast_result = executor.execute_xiaoyuzhou_podcast(podcast_url, operation="podcast")
    episodes_result = executor.execute_xiaoyuzhou_podcast(podcast_url, operation="episodes")

    assert rss_result["count"] == 1
    assert podcast_result["count"] == 1
    assert episodes_result["count"] == 1
    assert calls == [
        "https://example.com/show.xml",
        podcast_url,
        podcast_url,
    ]
    assert podcast_result["transport"]["endpoint"] == podcast_url


def test_xiaoyuzhou_text_query_is_not_mislabeled_as_direct_platform_data(executor):
    with pytest.raises(Exception, match="official public podcast URL"):
        executor.execute_xiaoyuzhou_podcast("generic podcast search")


def test_web_reader_uses_bounded_transport_and_rejects_empty_success(monkeypatch, executor, public_dns):
    content = "<html><body>" + ("evidence " * 30) + "</body></html>"
    calls = []
    monkeypatch.setattr(
        "backend.services.agent_reach.native.executor.fetch_public_http",
        lambda url, **_kwargs: calls.append(url) or _response(content, url, "text/html"),
    )
    result = executor.execute_web_read("https://example.com/article")
    assert result["status"] == "SUCCESS"
    assert result["backend"] == "native_http_reader"
    assert calls == ["https://example.com/article"]

    monkeypatch.setattr(jina, "read_article_via_jina", lambda *_args, **_kwargs: None)
    empty_executor = SimpleNamespace(execute_web_read=lambda _url: {"content": ""})
    assert jina.execute_web_read("https://example.com/empty", executor=empty_executor)["status"] == "error"


def test_web_reader_decodes_gzip_before_extracting_page_text(monkeypatch, executor, public_dns):
    html = ("<html><head><title>Observed page</title></head>"
            "<body><h1>Actual heading</h1><p>Evidence text repeated many times. "
            "Evidence text repeated many times. Evidence text repeated many times.</p></body></html>")
    compressed = gzip.compress(html.encode("utf-8"))
    response = BoundedHTTPResponse(
        body=compressed, endpoint="https://example.com/article", status_code=200,
        content_type="text/html", headers={"Content-Encoding": "gzip"},
        latency_ms=1, attempts=1,
    )
    monkeypatch.setattr(
        "backend.services.agent_reach.native.executor.fetch_public_http",
        lambda *_args, **_kwargs: response,
    )
    result = executor.execute_web_read("https://example.com/article")
    assert result["page_metadata"]["title"] == "Observed page"
    assert result["page_metadata"]["headings"] == ["Actual heading"]
    assert "Evidence text" in result["content"]
    assert result["transport"]["raw_body_bytes"] == len(compressed)
    assert result["transport"]["decoded_body_bytes"] == len(html.encode("utf-8"))


def test_web_reader_rejects_binary_primary_and_fallback(monkeypatch, executor, public_dns):
    binary = BoundedHTTPResponse(
        body=b"\x00" + b"A" * 150, endpoint="https://example.com/article",
        status_code=200, content_type="application/octet-stream",
        headers={"Content-Type": "application/octet-stream"}, latency_ms=1, attempts=1,
    )
    monkeypatch.setattr(
        "backend.services.agent_reach.native.executor.fetch_public_http",
        lambda *_args, **_kwargs: binary,
    )
    with pytest.raises(Exception, match="Failed to retrieve content"):
        executor.execute_web_read("https://example.com/article")


def test_web_reader_preserves_declared_metadata_as_unverified(monkeypatch, executor, public_dns):
    html = """<html><head><title>Observed title</title>
    <meta name="author" content="Editorial desk">
    <meta property="article:published_time" content="2026-10-10T12:00:00Z">
    <link rel="canonical" href="https://example.com/canonical"></head>
    <body><h1>Major correction</h1><article>Evidence body repeated many times.
    Evidence body repeated many times. Evidence body repeated many times.</article></body></html>"""
    monkeypatch.setattr(
        "backend.services.agent_reach.native.executor.fetch_public_http",
        lambda url, **_kwargs: _response(html, url, "text/html"),
    )
    raw = executor.execute_web_read("https://example.com/article")
    assert raw["page_metadata"]["title"] == "Observed title"
    assert raw["page_metadata"]["published"] == "2026-10-10T12:00:00Z"
    assert raw["page_metadata"]["headings"] == ["Major correction"]
    assert raw["page_metadata"]["declared_canonical_verified"] is False
    assert raw["page_metadata"]["content_scope"] == "article"
    assert raw["page_metadata"]["observed_links"] == []
    view = jina.execute_web_read("https://example.com/article", executor=executor)
    assert view["title"] == "Observed title"
    assert view["author"] == "Editorial desk"
    assert view["published"] == "2026-10-10T12:00:00Z"
    assert view["backend"] == "native_http_reader"


def test_web_reader_does_not_invent_title_or_declared_canonical(monkeypatch, executor, public_dns):
    html = "<html><body><main>" + ("Observed body text. " * 12) + "</main></body></html>"
    monkeypatch.setattr(
        "backend.services.agent_reach.native.executor.fetch_public_http",
        lambda url, **_kwargs: _response(html, url, "text/html"),
    )
    raw = executor.execute_web_read("https://example.com/article")
    assert raw["page_metadata"]["title"] == ""
    assert "declared_canonical_verified" not in raw["page_metadata"]
    view = jina.execute_web_read("https://example.com/article", executor=executor)
    assert view["title"] == ""


def test_web_reader_discards_challenge_page_metadata_on_reader_fallback(monkeypatch, executor, public_dns):
    def fake_fetch(url, **_kwargs):
        if url.startswith("https://r.jina.ai/"):
            return _response("# Actual page\n" + ("Evidence text " * 20), url, "text/plain")
        return _response(
            "<html><head><title>Challenge title</title></head>"
            "<body>Verify you are human</body></html>", url, "text/html",
        )

    monkeypatch.setattr(
        "backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch,
    )
    result = executor.execute_web_read("https://example.com/article")
    assert result["backend"] == "jina_reader_fallback"
    assert result["page_metadata"] == {}


def test_web_reader_does_not_bypass_provider_rate_limit(monkeypatch, executor, public_dns):
    def rate_limited(*_args, **_kwargs):
        raise ProviderHTTPError(
            "Provider HTTP 429",
            endpoint="https://example.com/article",
            status_code=429,
            retry_after_seconds=45,
            network_observed=True,
        )

    monkeypatch.setattr(
        "backend.services.agent_reach.native.executor.fetch_public_http", rate_limited
    )
    with pytest.raises(ProviderHTTPError) as exc_info:
        executor.execute_web_read("https://example.com/article")
    assert exc_info.value.retry_after_seconds == 45


def test_jina_adapter_uses_shared_bounded_transport(monkeypatch, public_dns):
    calls = []
    monkeypatch.setattr(
        jina,
        "fetch_public_http",
        lambda url, **kwargs: calls.append((url, kwargs))
        or _response("# Article\n" + ("evidence " * 10), url, "text/markdown"),
    )
    result = jina.read_article_via_jina("https://example.com/article")
    assert result["status"] == "success"
    assert calls[0][0] == "https://r.jina.ai/https://example.com/article"
    assert calls[0][1]["max_bytes"] > 0


def test_jina_adapter_does_not_promote_compressed_wire_bytes(monkeypatch, public_dns):
    markdown = "# Actual page\n" + ("Relevant source text. " * 8)
    response = BoundedHTTPResponse(
        body=gzip.compress(markdown.encode("utf-8")),
        endpoint="https://r.jina.ai/https://example.com/article", status_code=200,
        content_type="text/plain", headers={"Content-Encoding": "gzip"},
        latency_ms=1, attempts=1,
    )
    monkeypatch.setattr(jina, "fetch_public_http", lambda *_args, **_kwargs: response)
    result = jina.read_article_via_jina("https://example.com/article")
    assert result["content"] == markdown
    assert result["transport"]["raw_body_bytes"] == len(response.body)


def test_provider_retry_after_reaches_dispatch_telemetry():
    observations = []
    doctor = SimpleNamespace(
        get_channel_status=lambda _platform: {"active_backend": "fixture"},
        record_observation=lambda platform, telemetry, fragments: observations.append(
            (platform, dict(telemetry), list(fragments))
        ),
    )
    dispatcher = ChannelQueryDispatcher(SimpleNamespace(doctor=doctor))

    def fail(*_args, **_kwargs):
        raise ProviderHTTPError(
            "Provider HTTP 429",
            endpoint="https://api.example.com/data",
            status_code=429,
            retry_after_seconds=120,
            rate_limit_remaining=0,
            rate_limit_reset_at="2030-01-01T00:00:00+00:00",
            network_observed=True,
            attempts=2,
        )

    dispatcher.standard.execute = fail
    fragments, telemetry = dispatcher.execute("github", "fixture", operation="issues")
    assert fragments == []
    assert telemetry["status"] == "FAILED"
    assert telemetry["http_statuses"] == [429]
    assert telemetry["retry_after_seconds"] == 120
    assert telemetry["rate_limit_remaining"] == 0
    assert telemetry["rate_limit_reset_at"] == "2030-01-01T00:00:00+00:00"
    assert observations[0][1]["operation"] == "github.issues"
