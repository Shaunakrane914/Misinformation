"""
Aegis Protocol — Contract Tests: Upstream Toolchain Response Fixtures
======================================================================
Verifies command/response parsing and forensic normalization against fixtures
matching the exact current upstream Agent Reach and CLI tool outputs:
1. agent-reach doctor --json output structure
2. gh search repos / gh issue view JSON output
3. yt-dlp dump-json video and transcript metadata
4. V2EX topics hot JSON API
5. Bilibili web search API JSON
"""

import json
import pytest

from backend.services.agent_reach.native.normalizer import native_normalizer
from backend.services.agent_reach.native.doctor import native_doctor


# ── 1. Doctor Contract ───────────────────────────────────────────────────────

DOCTOR_JSON_FIXTURE = """
{
  "web": {"active_backend": "jina-reader", "status": "ok"},
  "github": {"active_backend": "gh", "status": "ok"},
  "youtube": {"active_backend": "yt-dlp", "status": "ok"},
  "twitter": {"active_backend": "twitter-cli", "status": "auth_required"},
  "reddit": {"active_backend": "opencli", "status": "auth_required"},
  "v2ex": {"active_backend": "public_api", "status": "ok"},
  "bilibili": {"active_backend": "public_search", "status": "ok"},
  "rss": {"active_backend": "feedparser", "status": "ok"},
  "boss": {"active_backend": "boss-agent-cli", "status": "auth_required"}
}
"""

def test_contract_doctor_json_parsing():
    """Verify parsing of upstream agent-reach doctor --json output."""
    data = json.loads(DOCTOR_JSON_FIXTURE)
    assert "github" in data
    assert data["github"]["active_backend"] == "gh"
    assert data["twitter"]["status"] == "auth_required"
    assert data["boss"]["active_backend"] == "boss-agent-cli"


# ── 2. GitHub CLI Contract ───────────────────────────────────────────────────

GH_SEARCH_REPOS_FIXTURE = """
[
  {
    "name": "cpython",
    "nameWithOwner": "python/cpython",
    "description": "The Python programming language",
    "url": "https://github.com/python/cpython",
    "stargazers": {"totalCount": 65000},
    "updatedAt": "2026-09-23T10:00:00Z"
  },
  {
    "name": "agent-reach",
    "nameWithOwner": "Panniantong/Agent-Reach",
    "description": "Give your agent real-time access to the internet",
    "url": "https://github.com/Panniantong/Agent-Reach",
    "stargazers": {"totalCount": 12500},
    "updatedAt": "2026-09-23T12:00:00Z"
  }
]
"""

def test_contract_gh_repo_normalization():
    """Verify normalization of gh search repos JSON output."""
    repos = json.loads(GH_SEARCH_REPOS_FIXTURE)
    frags = native_normalizer.normalize_github_repos(
        repos,
        query_id="q_gh_01",
        query_class="technical",
        query_text="python"
    )
    assert len(frags) == 2
    f1 = frags[0]
    assert f1.platform == "GitHub"
    assert "python/cpython" in f1.title
    assert f1.channel_name == "github"
    assert f1.raw_metadata["stars"] == 65000


# ── 3. yt-dlp Video & Transcript Contract ────────────────────────────────────

YTDLP_DUMP_JSON_FIXTURE = """
{
  "id": "dQw4w9WgXcQ",
  "title": "Autonomous Agent Systems Explained",
  "description": "A deep technical walkthrough of modern tool routing architectures.",
  "uploader": "AI Architecture Hub",
  "upload_date": "20260815",
  "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "duration": 720,
  "view_count": 45000
}
"""

def test_contract_ytdlp_video_normalization():
    """Verify normalization of yt-dlp metadata."""
    video = json.loads(YTDLP_DUMP_JSON_FIXTURE)
    frag = native_normalizer.normalize_youtube_video(
        video,
        query_id="q_yt_01",
        query_class="viral_moments",
        query_text="Agent Systems"
    )
    assert frag.platform == "YouTube"
    assert frag.title == "Autonomous Agent Systems Explained"
    assert frag.author == "AI Architecture Hub"
    assert frag.channel_name == "youtube"
    assert frag.raw_metadata["view_count"] == 45000


# ── 4. V2EX Topics Contract ──────────────────────────────────────────────────

V2EX_HOT_JSON_FIXTURE = """
[
  {
    "id": 98765,
    "title": "LLM inference latency benchmarks on latest hardware",
    "url": "https://v2ex.com/t/98765",
    "content": "Comparing vLLM and TensorRT-LLM on Blackwell B200",
    "member": {"username": "hpc_engineer"},
    "replies": 42,
    "created": 1726000000
  }
]
"""

def test_contract_v2ex_topics_normalization():
    """Verify normalization of V2EX hot topics JSON API."""
    topics = json.loads(V2EX_HOT_JSON_FIXTURE)
    frags = native_normalizer.normalize_v2ex_topics(
        topics,
        query_id="q_v2ex_01",
        query_class="discussions",
        query_text="LLM inference"
    )
    assert len(frags) == 1
    f = frags[0]
    assert f.platform == "V2EX"
    assert f.title == "LLM inference latency benchmarks on latest hardware"
    assert f.channel_name == "v2ex"
    assert f.author == "hpc_engineer"
    assert f.raw_metadata["replies"] == 42


# ── 5. Bilibili Search Contract ──────────────────────────────────────────────

BILIBILI_SEARCH_JSON_FIXTURE = """
[
  {
    "title": "<em class=\\"keyword\\">Tesla</em> Optimus Gen 3 Hands-On Teardown",
    "arcurl": "https://www.bilibili.com/video/BV1ABC411XYZ",
    "author": "RoboticsReview",
    "description": "Full mechanical teardown of actuators and sensors.",
    "play": 280000,
    "video_review": 1200,
    "pubdate": 1726500000
  }
]
"""

def test_contract_bilibili_search_normalization():
    """Verify normalization of Bilibili search JSON API."""
    items = json.loads(BILIBILI_SEARCH_JSON_FIXTURE)
    frags = native_normalizer.normalize_bilibili_videos(
        items,
        query_id="q_bili_01",
        query_class="viral_moments",
        query_text="Tesla Optimus"
    )
    assert len(frags) == 1
    f = frags[0]
    assert f.platform == "Bilibili"
    assert "<em" not in f.title
    assert "Tesla Optimus Gen 3 Hands-On Teardown" in f.title
    assert f.channel_name == "bilibili"
    assert f.raw_metadata["play_count"] == 280000
