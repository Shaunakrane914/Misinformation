"""Adapter contracts for the shared bounded HTTP transport."""

import json
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
from backend.services.agent_reach.native.executor import NativeExecutor


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

    assert calls[0][0] == "https://api.github.com/repos/octocat/Hello-World/issues?per_page=7"
    assert calls[0][1]["max_bytes"] > 0
    assert result["operation"] == "github.issues"
    assert result["transport"]["endpoint"] == calls[0][0]


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


def test_rss_and_podcast_feeds_use_bounded_transport(monkeypatch, executor, public_dns):
    calls = []
    rss = """<?xml version="1.0"?><rss version="2.0"><channel><title>Fixture</title>
    <item><title>Episode</title><link>https://example.com/episode</link>
    <description>Evidence notes</description></item></channel></rss>"""

    def fake_fetch(url, **_kwargs):
        calls.append(url)
        if "itunes.apple.com" in url:
            return _response(
                json.dumps({"results": [{"collectionName": "Fixture", "feedUrl": "https://example.com/show.xml"}]}),
                url,
            )
        return _response(rss, url, "application/rss+xml")

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    rss_result = executor.execute_rss_read("https://example.com/show.xml")
    podcast_result = executor.execute_xiaoyuzhou_podcast("Fixture")

    assert rss_result["count"] == 1
    assert podcast_result["count"] == 1
    assert calls == [
        "https://example.com/show.xml",
        "https://itunes.apple.com/search?term=Fixture&entity=podcast&limit=3",
        "https://example.com/show.xml",
    ]
    assert podcast_result["transport"]["endpoint"] == "https://example.com/show.xml"


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
            network_observed=True,
            attempts=2,
        )

    dispatcher.standard.execute = fail
    fragments, telemetry = dispatcher.execute("github", "fixture", operation="issues")
    assert fragments == []
    assert telemetry["status"] == "FAILED"
    assert telemetry["http_statuses"] == [429]
    assert telemetry["retry_after_seconds"] == 120
    assert observations[0][1]["operation"] == "github.issues"
