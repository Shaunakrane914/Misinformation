"""Unit tests for expanded public social adapters: Bluesky, Hacker News, Telegram."""

import json
from unittest.mock import MagicMock, patch

from backend.infrastructure.acquisition.adapters.social.bluesky import BlueskyAdapter
from backend.infrastructure.acquisition.adapters.social.hackernews import HackerNewsAdapter
from backend.infrastructure.acquisition.adapters.social.telegram import TelegramPublicAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)


def test_bluesky_adapter_can_handle_and_normalize():
    adapter = BlueskyAdapter()
    cand = CandidateSource(url="https://bsky.app/profile/alice.bsky.social/post/3k123abc")
    assert adapter.can_handle(cand) is True

    cand.metadata = {
        "author_handle": "alice.bsky.social",
        "created_at": "2026-10-24T10:00:00Z",
        "like_count": 42,
        "repost_count": 12,
    }
    doc = FetchedDocument(
        url=cand.url,
        status="SUCCESS",
        raw_content="Viral claim debunked with official data.",
    )
    frags = adapter.normalize(doc, cand, RetrievalRequest())
    assert len(frags) == 1
    f = frags[0]
    assert f.platform == "bluesky"
    assert f.author == "@alice.bsky.social"
    assert f.raw_metadata["like_count"] == 42


def test_hackernews_adapter_can_handle_and_normalize():
    adapter = HackerNewsAdapter()
    cand = CandidateSource(
        url="https://news.ycombinator.com/item?id=40001234",
        title="Show HN: Fast Fact Checker",
        snippet="Snippet",
        metadata={
            "author": "tech_founder",
            "points": 350,
            "num_comments": 85,
            "story_url": "https://example.com/project",
        },
    )
    assert adapter.can_handle(cand) is True

    doc = FetchedDocument(
        url=cand.url,
        status="SUCCESS",
        raw_content="Discussion text regarding architecture.",
    )
    frags = adapter.normalize(doc, cand, RetrievalRequest())
    assert len(frags) == 1
    f = frags[0]
    assert f.platform == "hackernews"
    assert f.raw_metadata["points"] == 350
    assert f.author == "tech_founder"


def test_telegram_public_adapter_can_handle_and_normalize():
    adapter = TelegramPublicAdapter()
    cand = CandidateSource(url="https://t.me/news_channel")
    assert adapter.can_handle(cand) is True

    sample_html = """
    <html>
      <body>
        <div class="tgme_channel_info_title">Official Breaking News</div>
        <div class="tgme_widget_message_text">First alert regarding market movement.</div>
        <div class="tgme_widget_message_text">Second statement released by treasury.</div>
      </body>
    </html>
    """
    doc = FetchedDocument(
        url="https://t.me/s/news_channel",
        status="SUCCESS",
        raw_content=sample_html,
    )
    frags = adapter.normalize(doc, cand, RetrievalRequest())
    assert len(frags) == 2
    f1 = frags[0]
    assert f1.platform == "telegram"
    assert f1.author == "Official Breaking News"
    assert "First alert" in f1.content
