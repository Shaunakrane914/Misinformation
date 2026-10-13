"""Missing provider fields must remain missing in evidence fragments."""

from backend.services.agent_reach.native.normalizer import NativeNormalizer
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
