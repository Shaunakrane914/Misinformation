"""Controlled acquisition-boundary tests for recovered production operations."""

import sys
from types import SimpleNamespace

import pytest

from backend.services.agent_reach.native.operation_capabilities import (
    EXECUTABLE_CAPABILITIES,
    runtime_operation_capabilities,
)
from backend.services.agent_reach.native.router import NativeRouter


RESTORED_OPERATIONS = {
    "github": {"read", "issues", "prs", "commits", "releases"},
    "youtube": {"read", "transcript", "comments"},
    "v2ex": {"latest", "search", "topic", "replies"},
    "web": {"read"},
    "rss": {"read"},
    "xiaoyuzhou": {"podcast", "episodes"},
}


@pytest.fixture(autouse=True)
def _clear_runtime_observations():
    runtime_operation_capabilities.reset_observations()
    yield
    runtime_operation_capabilities.reset_observations()


def _transport(endpoint="https://example.com/api"):
    return {
        "endpoint": endpoint,
        "network_observed_this_attempt": True,
        "http_status": 200,
        "content_type": "application/json",
        "raw_body_bytes": 123,
        "network_latency_ms": 5,
        "cache_status": "MISS",
    }


@pytest.mark.parametrize("operation", ["read", "issues", "prs", "releases", "commits"])
def test_recovered_github_operations_reach_rest_executor(monkeypatch, operation):
    router = NativeRouter()
    if operation == "read":
        item = {
            "full_name": "owner/repo", "description": "Repository", "readme": "README body",
            "html_url": "https://github.com/owner/repo", "owner": {"login": "owner"},
        }
    elif operation in {"issues", "prs"}:
        item = {"title": "Tracked change", "body": "Substantive body", "html_url": "https://github.com/owner/repo/issues/1", "user": {"login": "author"}}
    elif operation == "releases":
        item = {"name": "v1", "body": "Release notes", "html_url": "https://github.com/owner/repo/releases/tag/v1"}
    else:
        item = {"commit": {"message": "Fix provenance", "author": {"name": "author"}}, "html_url": "https://github.com/owner/repo/commit/abc"}
    monkeypatch.setattr(
        router.executor,
        "execute_github_rest_operation",
        lambda repo, op, limit: {"repo": "owner/repo", "items": [item], "transport": _transport()},
    )
    fragments, telemetry = router.execute_channel_query(
        "github", "owner/repo", operation=operation, limit=1
    )
    assert len(fragments) == 1
    assert telemetry["operation"] == f"github.{operation}"
    assert telemetry["network_observed"] is True
    assert fragments[0].requested_channel == "github"
    assert fragments[0].actual_retrieval_channel == "github"
    assert fragments[0].native_backend_id == "GitHub REST API"
    assert fragments[0].raw_metadata["operation"] == operation
    assert fragments[0].raw_metadata["transport"]["endpoint"]


@pytest.mark.parametrize("operation", ["read", "transcript", "comments"])
def test_recovered_youtube_operations_preserve_depth(monkeypatch, operation):
    router = NativeRouter()
    url = "https://www.youtube.com/watch?v=fixture123"
    if operation == "read":
        monkeypatch.setattr(router, "execute_channel_read", lambda *_args, **_kwargs: {
            "status": "success", "title": "Fixture video", "content": "Metadata description",
            "backend": "yt-dlp", "transport": _transport(url),
        })
    elif operation == "transcript":
        monkeypatch.setattr(router.executor, "execute_youtube_transcript", lambda *_args, **_kwargs: {
            "status": "SUCCESS", "content": "Transcript evidence " * 20, "transport": _transport(url),
        })
    else:
        monkeypatch.setattr(router.executor, "execute_youtube_comments", lambda *_args, **_kwargs: {
            "status": "SUCCESS", "items": [{"id": "c1", "author": "viewer", "text": "Useful comment", "like_count": 2}],
            "transport": _transport(url),
        })
    fragments, telemetry = router.execute_channel_query(
        "youtube", url, operation=operation, limit=1
    )
    assert fragments
    expected = {"read": "DIRECT_METADATA", "transcript": "DIRECT_CONTENT", "comments": "DIRECT_CONTENT"}
    assert telemetry["outcome"] == expected[operation]
    assert fragments[0].requested_channel == "youtube"
    assert fragments[0].actual_retrieval_channel == "youtube"
    assert fragments[0].raw_metadata["transport"]["endpoint"] == url


def test_youtube_read_failure_cannot_fall_through_to_generic_html(monkeypatch):
    router = NativeRouter()
    monkeypatch.setattr(
        "backend.infrastructure.acquisition.routing.router.is_safe_url",
        lambda _url: (True, "public fixture"),
    )

    class FailingYoutubeDL:
        def __init__(self, _options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, *_args, **_kwargs):
            raise RuntimeError("video unavailable")

    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FailingYoutubeDL))
    monkeypatch.setattr(
        "backend.infrastructure.acquisition.routing.router.execute_web_read",
        lambda *_args, **_kwargs: pytest.fail("generic reader must not receive a YouTube URL"),
    )
    result = router.execute_channel_read("https://www.youtube.com/watch?v=missing123")
    assert result["status"] == "failed"
    assert result["backend"] == "yt-dlp"
    assert result["transport"]["network_observed_this_attempt"] is True


def test_empty_provider_result_retains_transport_observation(monkeypatch):
    router = NativeRouter()
    url = "https://www.youtube.com/watch?v=fixture123"
    monkeypatch.setattr(router.executor, "execute_youtube_comments", lambda *_args, **_kwargs: {
        "status": "EMPTY", "items": [], "transport": _transport(url),
    })
    fragments, telemetry = router.execute_channel_query(
        "youtube", url, operation="comments", limit=1,
    )
    assert fragments == []
    assert telemetry["outcome"] == "EMPTY"
    assert telemetry["network_observed"] is True
    assert telemetry["http_statuses"] == [200]


@pytest.mark.parametrize("operation", ["hot", "latest", "search", "topic", "replies"])
def test_all_advertised_v2ex_operations_are_dispatched(monkeypatch, operation):
    router = NativeRouter()
    result = {
        "items": [{"id": 1, "title": "Fixture topic", "content": "Relevant discussion", "member": {"username": "tester"}, "url": "https://www.v2ex.com/t/1"}],
        "transport": _transport("https://www.v2ex.com/api/fixture"),
    }
    monkeypatch.setattr(router.executor, "execute_v2ex_hot", lambda: result)
    monkeypatch.setattr(router.executor, "execute_v2ex_search", lambda _query: result)
    monkeypatch.setattr(router.executor, "execute_v2ex_operation", lambda _op, _query: result)
    fragments, telemetry = router.execute_channel_query(
        "v2ex", "1" if operation in {"topic", "replies"} else "python",
        operation=operation, limit=1,
    )
    assert fragments
    assert telemetry["operation"] == f"v2ex.{operation}"
    assert fragments[0].requested_channel == "v2ex"
    assert fragments[0].actual_retrieval_channel == "v2ex"
    assert fragments[0].native_backend_id == "v2ex-public-api"
    assert fragments[0].raw_metadata["transport"]["endpoint"]


def test_web_search_is_a_real_alias_and_direct_web_read_is_recovered(monkeypatch):
    router = NativeRouter()
    monkeypatch.setattr(router, "_execute_web_search", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(router, "_fallback_web_scraper", lambda *_args, **_kwargs: [])
    _, alias_telemetry = router.execute_channel_query("web_search", "fixture")
    assert alias_telemetry["operation"] == "web_search.search"
    monkeypatch.setattr(router, "execute_channel_read", lambda *_args, **_kwargs: {
        "status": "success", "title": "Article", "content": "Direct article body " * 40,
        "backend": "reader", "transport": _transport("https://example.com/article"),
    })
    fragments, read_telemetry = router.execute_channel_query(
        "web", "https://example.com/article", operation="read"
    )
    assert fragments[0].content_depth == "FULL_ARTICLE"
    assert read_telemetry["outcome"] == "DIRECT_CONTENT"
    assert fragments[0].requested_channel == "web"
    assert fragments[0].actual_retrieval_channel == "jina_reader"
    assert fragments[0].raw_metadata["transport"]["endpoint"] == "https://example.com/article"


def test_rss_read_preserves_syndicated_depth_and_provenance(monkeypatch):
    router = NativeRouter()
    monkeypatch.setattr(router.executor, "execute_rss_read", lambda *_args, **_kwargs: {
        "items": [{"title": "Release", "link": "https://example.com/release", "summary": "Official summary", "published": "today"}],
        "transport": _transport("https://example.com/feed.xml"),
    })
    rss, _ = router.execute_channel_query(
        "rss", "https://example.com/feed.xml", operation="read", limit=1
    )
    assert rss and rss[0].content_depth == "FEED_ENTRY_SUMMARY"
    assert rss[0].requested_channel == "rss"
    assert rss[0].actual_retrieval_channel == "rss"
    assert rss[0].raw_metadata["transport"]["endpoint"] == "https://example.com/feed.xml"


@pytest.mark.parametrize("operation", ["podcast", "episodes"])
def test_public_podcast_operations_are_not_lost_behind_auth_guard(monkeypatch, operation):
    router = NativeRouter()
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(router.executor, "execute_xiaoyuzhou_podcast", lambda *_args, **_kwargs: {
        "items": [{"podcast": "Fixture", "title": "Episode", "summary": "Show notes", "link": "https://www.xiaoyuzhoufm.com/episode/1", "audio_url": "https://example.com/audio.mp3"}],
        "transport": _transport("https://itunes.apple.com/search"),
    })
    podcast, telemetry = router.execute_channel_query(
        "xiaoyuzhou", "Fixture", operation=operation, limit=1
    )
    assert podcast
    assert telemetry["status"] == "SUCCESS"
    assert telemetry["operation"] == f"xiaoyuzhou.{operation}"
    assert podcast[0].requested_channel == "xiaoyuzhou"
    assert podcast[0].actual_retrieval_channel == "xiaoyuzhou"
    assert podcast[0].native_backend_id == "xiaoyuzhou-public-web"
    assert podcast[0].raw_metadata["transport"]["endpoint"] == "https://itunes.apple.com/search"


def test_declared_recovered_contract_matches_runtime_dispatch_surface():
    assert EXECUTABLE_CAPABILITIES["web_search"] == {"search"}
    assert {"read", "issues", "prs", "releases", "commits"} <= EXECUTABLE_CAPABILITIES["github"]
    assert {"read", "transcript", "comments"} <= EXECUTABLE_CAPABILITIES["youtube"]
    assert {"latest", "search", "topic", "replies"} <= EXECUTABLE_CAPABILITIES["v2ex"]
    assert {"search", "podcast", "episodes"} <= EXECUTABLE_CAPABILITIES["xiaoyuzhou"]
    assert sum(len(operations) for operations in RESTORED_OPERATIONS.values()) == 16
    for channel, operations in RESTORED_OPERATIONS.items():
        assert operations <= EXECUTABLE_CAPABILITIES[channel]
