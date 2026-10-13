"""Comprehensive tests for Phase 8B maximum extraction depth and structured contracts."""

import json
from types import SimpleNamespace
import pytest

from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse, ProviderHTTPError
from backend.services.agent_reach.native.errors import NativeReachError
from backend.services.agent_reach.native.executor import NativeExecutor
from backend.infrastructure.acquisition.routing.router import NativeRouter
from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_observed_page_details


def _response(body: str, endpoint: str = "https://example.com/api", status_code: int = 200, headers=None, content_type: str = "application/json"):
    raw = body.encode("utf-8")
    return BoundedHTTPResponse(
        body=raw,
        endpoint=endpoint,
        status_code=status_code,
        content_type=content_type,
        headers=headers or {"Content-Type": content_type},
        latency_ms=10,
        attempts=1,
    )


@pytest.fixture
def executor():
    return NativeExecutor()


@pytest.fixture
def router():
    return NativeRouter()


def test_github_pr_file_followup_preserves_file_diff_metadata(monkeypatch, executor):
    calls = []

    def fake_fetch(url, **_kwargs):
        calls.append(url)
        if "/files?" in url:
            return _response(json.dumps([
                {
                    "filename": "backend/core/security.py",
                    "status": "modified",
                    "additions": 15,
                    "deletions": 2,
                    "changes": 17,
                    "patch": "@@ -1,5 +1,18 @@\n+def verify_token(): ...",
                }
            ]), url)
        return _response(json.dumps([
            {"number": 42, "title": "Security patch", "body": "Tighten tokens", "state": "open"}
        ]), url)

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    result = executor.execute_github_rest_operation(
        "owner/repo", "prs", limit=1, include_files=True, file_limit=3
    )
    assert result["status"] == "SUCCESS"
    assert result["follow_up_requests"] == 1
    assert calls[-1] == "https://api.github.com/repos/owner/repo/pulls/42/files?per_page=3"
    pr_item = result["items"][0]
    assert pr_item["file_lookup_status"] == "SUCCESS"
    assert len(pr_item["sampled_files"]) == 1
    file_info = pr_item["sampled_files"][0]
    assert file_info["filename"] == "backend/core/security.py"
    assert file_info["status"] == "modified"
    assert file_info["additions"] == 15
    assert file_info["deletions"] == 2


def test_github_commit_file_followup_preserves_commit_stats_and_files(monkeypatch, executor):
    calls = []

    def fake_fetch(url, **_kwargs):
        calls.append(url)
        if url.endswith("/commits/a1b2c3d"):
            return _response(json.dumps({
                "sha": "a1b2c3d",
                "stats": {"total": 10, "additions": 8, "deletions": 2},
                "files": [
                    {"filename": "README.md", "status": "modified", "additions": 8, "deletions": 2, "patch": "diff"}
                ]
            }), url)
        return _response(json.dumps([
            {"sha": "a1b2c3d", "commit": {"message": "Update docs", "author": {"name": "Dev"}}}
        ]), url)

    monkeypatch.setattr("backend.services.agent_reach.native.executor.fetch_public_http", fake_fetch)
    result = executor.execute_github_rest_operation(
        "owner/repo", "commits", limit=1, include_files=True, file_limit=3
    )
    assert result["status"] == "SUCCESS"
    assert result["follow_up_requests"] == 1
    assert calls[-1] == "https://api.github.com/repos/owner/repo/commits/a1b2c3d"
    commit_item = result["items"][0]
    assert commit_item["file_lookup_status"] == "SUCCESS"
    assert commit_item["stats"] == {"total": 10, "additions": 8, "deletions": 2}
    assert len(commit_item["sampled_files"]) == 1
    assert commit_item["sampled_files"][0]["filename"] == "README.md"


def test_github_file_followup_validates_options(executor):
    with pytest.raises(NativeReachError):
        executor.execute_github_rest_operation("owner/repo", "prs", include_files="false")
    with pytest.raises(NativeReachError):
        executor.execute_github_rest_operation("owner/repo", "prs", include_files=True, file_limit=15)
    with pytest.raises(NativeReachError):
        executor.execute_github_rest_operation("owner/repo", "issues", include_files=True)


def test_github_pr_route_formats_files_in_fragments(monkeypatch, router):
    pr_item = {
        "number": 10, "title": "Add feature", "body": "Initial description",
        "html_url": "https://github.com/owner/repo/pull/10",
        "user": {"login": "coder"}, "created_at": "2026-10-12T00:00:00Z",
        "sampled_files": [
            {"filename": "main.py", "status": "added", "additions": 50, "deletions": 0}
        ],
        "file_lookup_status": "SUCCESS",
    }
    monkeypatch.setattr(
        router.executor, "execute_github_rest_operation",
        lambda repo, op, limit, **kwargs: {
            "repo": "owner/repo", "items": [pr_item], "status": "SUCCESS",
            "transport": {"endpoint": "https://api.github.com", "network_observed_this_attempt": True,
                          "http_status": 200, "content_type": "application/json", "raw_body_bytes": 100,
                          "network_latency_ms": 10, "cache_status": "MISS"},
        }
    )
    fragments, telemetry = router.execute_channel_query(
        "github", "owner/repo", operation="prs", limit=1, include_files=True
    )
    assert len(fragments) == 1
    frag = fragments[0]
    assert "Observed changed files" in frag.content
    assert "main.py (added, +50/-0)" in frag.content
    assert frag.content_depth == "PARTIAL_CONTENT"
    provider_fields = frag.raw_metadata["provider_fields"]
    assert provider_fields["file_lookup_status"] == "SUCCESS"
    assert len(provider_fields["file_samples"]) == 1


def test_web_page_extraction_captures_opengraph_and_table_markdown():
    from bs4 import BeautifulSoup
    html = """<!doctype html>
    <html>
      <head>
        <title>Earnings Report</title>
        <meta property="og:description" content="Company posts Q3 record revenue" />
        <meta property="og:site_name" content="Financial Wire" />
        <meta name="twitter:creator" content="@analyst" />
      </head>
      <body>
        <main>
          <h1>Q3 Financial Results</h1>
          <p>The company announced quarterly metrics.</p>
          <table>
            <tr><th>Metric</th><th>Q3 2026</th><th>Q3 2025</th></tr>
            <tr><td>Revenue</td><td>$35.1B</td><td>$18.1B</td></tr>
            <tr><td>Net Income</td><td>$19.3B</td><td>$9.2B</td></tr>
          </table>
        </main>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    details = extract_observed_page_details(soup, "https://example.com/earnings")
    og = details.get("declared_open_graph", {})
    assert og.get("og_description") == "Company posts Q3 record revenue"
    assert og.get("site_name") == "Financial Wire"
    assert og.get("twitter_creator") == "@analyst"
    assert len(details.get("tables", [])) == 1
    table_rows = details["tables"][0]
    assert table_rows[0] == ["Metric", "Q3 2026", "Q3 2025"]
    assert table_rows[1] == ["Revenue", "$35.1B", "$18.1B"]


def test_youtube_description_links_extracted(monkeypatch, router):
    fake_info = {
        "id": "vid123",
        "title": "Investigative Report",
        "description": "Full details at https://reuters.com/article/123 and source: https://sec.gov/edgar/456",
        "uploader": "NewsDesk",
        "channel_id": "chan1",
    }
    class FakeYDL:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def extract_info(self, url, download=False): return fake_info

    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)
    monkeypatch.setattr("backend.infrastructure.acquisition.routing.router.is_safe_url", lambda _u: (True, None))
    res = router.execute_channel_read("https://youtube.com/watch?v=vid123")
    assert res["status"] == "success"
    meta = res["video_metadata"]
    links = meta.get("description_links", [])
    assert len(links) == 2
    assert links[0]["url"] == "https://reuters.com/article/123"
    assert links[1]["url"] == "https://sec.gov/edgar/456"
    assert links[0]["verification"] == "UNVERIFIED_REFERENCED_LINK"


def test_v2ex_topic_and_reply_link_extraction(router):
    raw_topics = [{
        "id": 999, "title": "Discussion",
        "content": "Check out this document: https://example.com/doc.pdf for evidence",
        "member": {"username": "user1"},
        "node": {"title": "Tech", "name": "tech"},
    }]
    fragments = router.normalizer.normalize_v2ex_topics(raw_topics)
    assert len(fragments) == 1
    meta = fragments[0].raw_metadata
    assert len(meta.get("observed_links", [])) == 1
    assert meta["observed_links"][0]["url"] == "https://example.com/doc.pdf"
    assert meta["observed_links"][0]["verification"] == "UNVERIFIED_TOPIC_LINK"


def test_xiaoyuzhou_shownotes_link_extraction(router):
    raw_episodes = [{
        "podcast": "TechTalk", "title": "Episode 10",
        "summary": "Show notes reference: https://arxiv.org/abs/2401.12345 and website https://project.org",
        "audio_url": "https://media.xyz.com/ep10.mp3",
    }]
    fragments = router.normalizer.normalize_xiaoyuzhou_episodes(raw_episodes)
    assert len(fragments) == 1
    meta = fragments[0].raw_metadata
    links = meta.get("observed_links", [])
    assert len(links) == 2
    assert links[0]["url"] == "https://arxiv.org/abs/2401.12345"
    assert links[1]["url"] == "https://project.org"
    assert links[0]["verification"] == "UNVERIFIED_SHOW_NOTES_LINK"


def test_rss_linked_article_followup(monkeypatch, router):
    feed_items = [{
        "title": "Breaking News",
        "link": "https://news.example.com/breaking",
        "summary": "Brief summary",
        "published": "2026-10-13T10:00:00Z",
    }]
    monkeypatch.setattr(
        router.executor, "execute_rss_read",
        lambda url, limit: {"items": feed_items, "transport": {
            "endpoint": url, "network_observed_this_attempt": True, "http_status": 200,
            "content_type": "application/xml", "raw_body_bytes": 100, "network_latency_ms": 5, "cache_status": "MISS"
        }}
    )
    monkeypatch.setattr(
        router, "execute_channel_read",
        lambda url, max_chars=3000: {
            "status": "success",
            "title": "Breaking News Full Story",
            "content": "This is the full comprehensive investigative report with deep evidence.",
            "url": url,
        }
    )
    fragments, telemetry = router.execute_channel_query(
        "rss", "https://news.example.com/feed.xml", operation="read", limit=1, follow_linked_article=True
    )
    assert len(fragments) == 1
    frag = fragments[0]
    assert frag.content_depth == "FEED_ENTRY_WITH_LINKED_ARTICLE"
    assert "Observed linked article (https://news.example.com/breaking):" in frag.content
    assert "This is the full comprehensive investigative report" in frag.content
    assert frag.raw_metadata["linked_article"]["status"] == "SUCCESS"
    assert telemetry["follow_up_requests"] == 1

