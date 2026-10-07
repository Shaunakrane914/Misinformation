"""
Aegis Protocol — Scraper Laboratory Canary Fixtures
===================================================
Configurable canary targets for each supported website/platform.
Canaries are known public resources used to detect platform schema drift,
authentication walls, and format changes without testing with random queries.
"""

from typing import Any, Dict, List

CANARY_FIXTURES: Dict[str, Dict[str, Any]] = {
    "reddit": {
        "platform": "reddit",
        "canary_id": "reddit_known_post_1",
        "target_url": "https://www.reddit.com/r/technology/comments/1example/artificial_intelligence_breakthrough/",
        "post_id": "1example",
        "subreddit": "technology",
        "expected_author": "tech_reporter",
        "expected_fields": ["title", "author", "created_utc", "subreddit", "selftext"],
        "fallback_target": "https://arctic-shift.photon-reddit.com/api/posts/ids?ids=1example",
    },
    "x": {
        "platform": "x",
        "canary_id": "x_known_status_1",
        "target_url": "https://x.com/OpenAI/status/1880000000000000000",
        "status_id": "1880000000000000000",
        "handle": "OpenAI",
        "expected_fields": ["text", "author", "created_at", "id", "likes"],
        "mirror_target": "https://api.fxtwitter.com/OpenAI/status/1880000000000000000",
    },
    "youtube": {
        "platform": "youtube",
        "canary_id": "youtube_known_video_1",
        "target_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video_id": "dQw4w9WgXcQ",
        "expected_channel": "Rick Astley",
        "expected_fields": ["title", "channel", "upload_date", "duration", "description"],
    },
    "github": {
        "platform": "github",
        "canary_id": "github_known_repo_1",
        "target_url": "https://github.com/psf/requests",
        "repo_path": "psf/requests",
        "expected_owner": "psf",
        "expected_fields": ["full_name", "description", "stargazers_count", "html_url"],
    },
    "web": {
        "platform": "web",
        "canary_id": "web_known_article_1",
        "target_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "expected_title_fragment": "Artificial intelligence",
        "expected_fields": ["title", "content", "url"],
    },
    "google_news": {
        "platform": "google_news",
        "canary_id": "google_news_rss_1",
        "target_url": "https://news.google.com/rss/search?q=technology&hl=en-US",
        "expected_fields": ["title", "link", "published", "source"],
    },
    "instagram": {
        "platform": "instagram",
        "canary_id": "instagram_known_profile_1",
        "target_url": "https://www.instagram.com/microsoft/",
        "is_walled_garden": True,
        "discovery_query": "site:instagram.com microsoft",
        "expected_fields": ["title", "snippet", "url"],
    },
    "facebook": {
        "platform": "facebook",
        "canary_id": "facebook_known_page_1",
        "target_url": "https://www.facebook.com/Google/",
        "is_walled_garden": True,
        "discovery_query": "site:facebook.com Google",
        "expected_fields": ["title", "snippet", "url"],
    },
    "tiktok": {
        "platform": "tiktok",
        "canary_id": "tiktok_known_profile_1",
        "target_url": "https://www.tiktok.com/@tiktok",
        "is_walled_garden": True,
        "discovery_query": "site:tiktok.com @tiktok",
        "expected_fields": ["title", "snippet", "url"],
    },
    "linkedin": {
        "platform": "linkedin",
        "canary_id": "linkedin_known_company_1",
        "target_url": "https://www.linkedin.com/company/microsoft",
        "is_walled_garden": True,
        "discovery_query": "site:linkedin.com/company microsoft",
        "expected_fields": ["title", "snippet", "url"],
    },
    "bilibili": {
        "platform": "bilibili",
        "canary_id": "bilibili_known_video_1",
        "target_url": "https://www.bilibili.com/video/BV1xx411c7mD",
        "bvid": "BV1xx411c7mD",
        "expected_fields": ["title", "snippet", "url"],
    },
}


def get_canary_fixture(platform: str) -> Dict[str, Any]:
    """Retrieve canary fixture for platform, or a generic web fixture."""
    plat = (platform or "").lower().strip()
    return CANARY_FIXTURES.get(
        plat,
        {
            "platform": plat,
            "canary_id": f"{plat}_canary_default",
            "target_url": f"https://example.com/{plat}",
            "expected_fields": ["title", "url"],
        }
    )
