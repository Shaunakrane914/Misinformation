"""Missing provider fields must remain missing in evidence fragments."""

import json

from backend.services.agent_reach.native.normalizer import NativeNormalizer
from backend.services.agent_reach.native.adapters.github import GitHubAdapter
from backend.services.agent_reach.native.adapters.youtube import YouTubeAdapter
from backend.services.agent_reach.native.adapters.web import WebAdapter
from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
from backend.services.agent_reach.channels import CandidateSource, FetchedDocument, RetrievalRequest
from backend.infrastructure.acquisition.routing.channel_dispatcher import ChannelQueryDispatcher


def test_repository_discovery_does_not_make_owner_author_or_update_publication():
    fragment = NativeNormalizer.normalize_github_repos([{
        "nameWithOwner": "owner/repo", "url": "https://github.com/owner/repo",
        "updatedAt": "2026-10-10",
    }])[0]
    assert fragment.author == ""
    assert fragment.published == ""
    assert "No description provided" not in fragment.content
    assert "Stars: 0" not in fragment.content
    assert fragment.raw_metadata["stars"] is None
    assert fragment.raw_metadata["owner_login"] == "owner"
    assert fragment.raw_metadata["updated_at"] == "2026-10-10"


def test_direct_github_repository_adapter_preserves_missing_fields():
    candidate = CandidateSource(url="https://github.com/owner/repo", platform="github")
    payload = {
        "full_name": "owner/repo", "html_url": candidate.url,
        "owner": {"login": "owner"}, "pushed_at": "2026-10-10T12:00:00Z",
    }
    fragment = GitHubAdapter().normalize(
        FetchedDocument(url=candidate.url, raw_content=json.dumps(payload)),
        candidate, RetrievalRequest(),
    )[0]
    assert fragment.author == ""
    assert fragment.published == ""
    assert fragment.score == 0.0
    assert "Stars: 0" not in fragment.content
    assert "Language: Code" not in fragment.content
    assert "No description provided" not in fragment.content
    assert fragment.raw_metadata["stars"] is None
    assert fragment.raw_metadata["language"] is None
    assert fragment.raw_metadata["owner_login"] == "owner"
    assert fragment.raw_metadata["pushed_at"] == "2026-10-10T12:00:00Z"


def test_direct_youtube_adapter_does_not_invent_channel_title_or_engagement():
    candidate = CandidateSource(url="https://www.youtube.com/watch?v=test123", platform="youtube")
    fragment = YouTubeAdapter().normalize(
        FetchedDocument(url=candidate.url, raw_content=json.dumps({"id": "test123"})),
        candidate, RetrievalRequest(),
    )[0]
    assert fragment.title == fragment.author == fragment.published == ""
    assert fragment.content == "Video ID: test123"
    assert fragment.score == 0.0
    assert fragment.raw_metadata["view_count"] is None
    assert fragment.raw_metadata["tags"] is None


def test_direct_web_reader_does_not_promote_search_date_to_page_publication():
    candidate = CandidateSource(url="https://example.org/story", platform="web",
                                metadata={"published_at": "2026-10-10"})
    fragment = WebAdapter().normalize(
        FetchedDocument(url=candidate.url, raw_content="<title>Story</title><p>Observed page text</p>"),
        candidate, RetrievalRequest(),
    )[0]
    assert fragment.published == ""
    assert fragment.raw_metadata["discovery_published_at"] == "2026-10-10"
    assert fragment.score == 0.0


def test_search_discovery_adapter_does_not_invent_index_author_or_date():
    candidate = CandidateSource(url="https://example.org/story", platform="web",
                                metadata={"published_at": "2026-10-10"})
    fragment = SearchDiscoveryAdapter().normalize(
        FetchedDocument(url=candidate.url, raw_content=json.dumps({"title": "Observed result"})),
        candidate, RetrievalRequest(),
    )[0]
    assert fragment.title == "Observed result"
    assert fragment.author == fragment.published == ""
    assert fragment.content_depth == "METADATA"
    assert fragment.raw_metadata["discovery_published_at"] == "2026-10-10"
    assert fragment.score == 0.0


def test_video_metadata_does_not_invent_channel_or_view_count():
    fragment = NativeNormalizer.normalize_youtube_search([{
        "id": "fixture123", "title": "Observed title", "description": "",
    }])[0]
    assert fragment.author == ""
    assert fragment.published == ""
    assert fragment.snippet == "Observed title"
    assert "Views: 0" not in fragment.content
    assert "Uploader: YouTube" not in fragment.content
    assert fragment.raw_metadata["view_count"] is None


def test_comment_id_is_not_used_as_video_id_and_missing_likes_stay_unknown():
    fragment = NativeNormalizer.normalize_youtube_comments([{
        "id": "comment123", "text": "Observed comment",
    }])[0]
    assert fragment.url == ""
    assert fragment.author == ""
    assert fragment.title == ""
    assert fragment.content == "Observed comment"
    assert fragment.raw_metadata["likes"] is None


def test_v2ex_topic_body_is_partial_and_missing_date_is_not_string_none():
    fragment = NativeNormalizer.normalize_v2ex_topics([{
        "id": 42, "title": "Observed topic", "content": "Source body " * 80,
    }])[0]
    assert fragment.content_depth == "PARTIAL_CONTENT"
    assert fragment.published == ""
    assert fragment.raw_metadata["replies"] is None
    assert "Replies: Unknown" not in fragment.content


def test_feed_publisher_is_not_entry_author_and_title_only_is_metadata():
    fragment = NativeNormalizer.normalize_rss_entries([{
        "title": "Observed title", "link": "https://example.com/story",
        "feed_publisher": "Example News", "summary": "", "feed_content": "",
    }])[0]
    assert fragment.author == ""
    assert fragment.content_depth == "METADATA"
    assert fragment.raw_metadata["feed_publisher"] == "Example News"
    telemetry = {"status": "SUCCESS"}
    ChannelQueryDispatcher._finalize_outcome(telemetry, [fragment])
    assert telemetry["outcome"] == "DIRECT_METADATA"
    assert telemetry["content_class"] == "METADATA"


def test_podcast_without_episode_notes_has_metadata_depth_and_no_fake_identity():
    fragment = NativeNormalizer.normalize_xiaoyuzhou_episodes([{
        "item_type": "episode", "title": "Observed episode",
    }])[0]
    assert fragment.title == "Observed episode"
    assert fragment.author == ""
    assert fragment.url == ""
    assert fragment.published == ""
    assert fragment.content_depth == "METADATA"
    assert "Audio URL:" not in fragment.content
