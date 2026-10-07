"""
Aegis Protocol — Scraper Laboratory Canary Fixtures
===================================================
Configurable canary targets for each supported website/platform.
Canaries are known public resources used to detect platform schema drift,
authentication walls, and format changes without testing with random queries.
Supports environment variable overrides for live operational maintenance (Section 6, 9).
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CanaryCategory(str, Enum):
    """Classification of canary resource permanence and maintenance expectation."""
    STABLE_PUBLIC_RESOURCE = "stable_public_resource"   # e.g., Wikipedia AI article, Rick Astley video
    KNOWN_TEST_RESOURCE = "known_test_resource"         # e.g., psf/requests GitHub repository
    CONFIGURABLE_RESOURCE = "configurable_resource"     # e.g., specific Reddit post, X tweet status


@dataclass
class CanaryTarget:
    """Maintainable canary configuration model (Section 9)."""
    canary_id: str
    platform: str
    category: str
    target_url: str
    required_fields: List[str]
    expected_schema: Dict[str, str] = field(default_factory=dict)
    expiry_notes: str = ""
    env_var_override: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canary_id": self.canary_id,
            "platform": self.platform,
            "category": self.category,
            "target_url": self.target_url,
            "required_fields": self.required_fields,
            "expected_schema": self.expected_schema,
            "expiry_notes": self.expiry_notes,
            "env_var_override": self.env_var_override,
            "metadata": self.metadata,
        }


# Dynamic resolver respecting environment variable overrides
def _get_configured_canaries() -> Dict[str, Dict[str, Any]]:
    reddit_post_id = os.getenv("AEGIS_CANARY_REDDIT_POST_ID", "1example")
    x_status_id = os.getenv("AEGIS_CANARY_X_STATUS_ID", "1880000000000000000")
    youtube_video_id = os.getenv("AEGIS_CANARY_YOUTUBE_VIDEO_ID", "dQw4w9WgXcQ")
    github_repo = os.getenv("AEGIS_CANARY_GITHUB_REPO", "psf/requests")
    web_url = os.getenv("AEGIS_CANARY_WEB_URL", "https://en.wikipedia.org/wiki/Artificial_intelligence")
    google_news_url = os.getenv("AEGIS_CANARY_GOOGLE_NEWS_URL", "https://news.google.com/rss/search?q=technology&hl=en-US")

    return {
        "reddit": {
            "platform": "reddit",
            "canary_id": "reddit_arctic_shift_canary_1",
            "category": CanaryCategory.CONFIGURABLE_RESOURCE.value,
            "target_url": f"https://www.reddit.com/r/technology/comments/{reddit_post_id}/",
            "post_id": reddit_post_id,
            "subreddit": "technology",
            "expected_author": "tech_reporter",
            "expected_fields": ["title", "author", "created_utc", "subreddit", "selftext"],
            "fallback_target": f"https://arctic-shift.photon-reddit.com/api/posts/ids?ids={reddit_post_id}",
            "env_var_override": "AEGIS_CANARY_REDDIT_POST_ID",
            "expiry_notes": "Configurable post ID for Arctic Shift mirror verification",
        },
        "x": {
            "platform": "x",
            "canary_id": "x_fxtwitter_canary_1",
            "category": CanaryCategory.CONFIGURABLE_RESOURCE.value,
            "target_url": f"https://x.com/OpenAI/status/{x_status_id}",
            "status_id": x_status_id,
            "handle": "OpenAI",
            "expected_fields": ["text", "author", "created_at", "id", "likes"],
            "mirror_target": f"https://api.fxtwitter.com/OpenAI/status/{x_status_id}",
            "env_var_override": "AEGIS_CANARY_X_STATUS_ID",
            "expiry_notes": "Configurable status ID for FxTwitter mirror verification",
        },
        "youtube": {
            "platform": "youtube",
            "canary_id": "youtube_yt_dlp_canary_1",
            "category": CanaryCategory.STABLE_PUBLIC_RESOURCE.value,
            "target_url": f"https://www.youtube.com/watch?v={youtube_video_id}",
            "video_id": youtube_video_id,
            "expected_channel": "Rick Astley",
            "expected_fields": ["title", "channel", "upload_date", "duration"],
            "env_var_override": "AEGIS_CANARY_YOUTUBE_VIDEO_ID",
            "expiry_notes": "Permanent public video resource (Never Gonna Give You Up)",
        },
        "github": {
            "platform": "github",
            "canary_id": "github_native_canary_1",
            "category": CanaryCategory.KNOWN_TEST_RESOURCE.value,
            "target_url": f"https://github.com/{github_repo}",
            "repo_path": github_repo,
            "expected_owner": "psf",
            "expected_fields": ["full_name", "description", "stargazers_count", "html_url"],
            "env_var_override": "AEGIS_CANARY_GITHUB_REPO",
            "expiry_notes": "Stable public Python open-source repository",
        },
        "web": {
            "platform": "web",
            "canary_id": "web_scrapling_canary_1",
            "category": CanaryCategory.STABLE_PUBLIC_RESOURCE.value,
            "target_url": web_url,
            "expected_title_fragment": "Artificial intelligence",
            "expected_fields": ["title", "content", "url"],
            "env_var_override": "AEGIS_CANARY_WEB_URL",
            "expiry_notes": "Stable encyclopedia article for HTML parsing validation",
        },
        "google_news": {
            "platform": "google_news",
            "canary_id": "google_news_rss_canary_1",
            "category": CanaryCategory.STABLE_PUBLIC_RESOURCE.value,
            "target_url": google_news_url,
            "expected_fields": ["title", "link", "published", "source"],
            "env_var_override": "AEGIS_CANARY_GOOGLE_NEWS_URL",
            "expiry_notes": "Continuous public RSS syndication feed",
        },
        "instagram": {
            "platform": "instagram",
            "canary_id": "instagram_walled_canary_1",
            "category": CanaryCategory.STABLE_PUBLIC_RESOURCE.value,
            "target_url": "https://www.instagram.com/microsoft/",
            "is_walled_garden": True,
            "discovery_query": "site:instagram.com microsoft",
            "expected_fields": ["title", "snippet", "url"],
            "expiry_notes": "Walled garden verified profile requiring search discovery",
        },
        "facebook": {
            "platform": "facebook",
            "canary_id": "facebook_walled_canary_1",
            "category": CanaryCategory.STABLE_PUBLIC_RESOURCE.value,
            "target_url": "https://www.facebook.com/Google/",
            "is_walled_garden": True,
            "discovery_query": "site:facebook.com Google",
            "expected_fields": ["title", "snippet", "url"],
            "expiry_notes": "Walled garden verified page requiring search discovery",
        },
        "tiktok": {
            "platform": "tiktok",
            "canary_id": "tiktok_walled_canary_1",
            "category": CanaryCategory.STABLE_PUBLIC_RESOURCE.value,
            "target_url": "https://www.tiktok.com/@tiktok",
            "is_walled_garden": True,
            "discovery_query": "site:tiktok.com @tiktok",
            "expected_fields": ["title", "snippet", "url"],
            "expiry_notes": "Walled garden account requiring search discovery",
        },
        "linkedin": {
            "platform": "linkedin",
            "canary_id": "linkedin_walled_canary_1",
            "category": CanaryCategory.STABLE_PUBLIC_RESOURCE.value,
            "target_url": "https://www.linkedin.com/company/microsoft",
            "is_walled_garden": True,
            "discovery_query": "site:linkedin.com/company microsoft",
            "expected_fields": ["title", "snippet", "url"],
            "expiry_notes": "Walled garden corporate profile requiring search discovery",
        },
        "bilibili": {
            "platform": "bilibili",
            "canary_id": "bilibili_canary_1",
            "category": CanaryCategory.STABLE_PUBLIC_RESOURCE.value,
            "target_url": "https://www.bilibili.com/video/BV1xx411c7mD",
            "bvid": "BV1xx411c7mD",
            "expected_fields": ["title", "snippet", "url"],
            "expiry_notes": "Stable international video resource",
        },
    }


# Backward-compatible global fixture dictionary
CANARY_FIXTURES: Dict[str, Dict[str, Any]] = _get_configured_canaries()


def get_canary_fixture(platform: str) -> Dict[str, Any]:
    """Retrieve dynamically resolved canary fixture for platform, respecting env overrides."""
    fixtures = _get_configured_canaries()
    plat = (platform or "").lower().strip()
    return fixtures.get(
        plat,
        {
            "platform": plat,
            "canary_id": f"{plat}_canary_default",
            "target_url": f"https://example.com/{plat}",
            "expected_fields": ["title", "url"],
            "category": CanaryCategory.CONFIGURABLE_RESOURCE.value,
        }
    )
