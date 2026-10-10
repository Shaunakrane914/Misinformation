"""
Aegis Protocol — Native Agent Reach Channel Capabilities Matrix
===============================================================
Defines the canonical metadata, supported operations, authentication requirements,
and runtime constraints across all 16 platforms supported by upstream Agent Reach.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass(frozen=True)
class PlatformCapability:
    """Formal capability description for an upstream platform."""
    platform: str
    display_name: str
    operations: Set[str]
    auth_mode: str  # "none" | "session_required" | "cookie_required" | "api_key" | "browser_cdp"
    tier: int       # 0: zero-config, 1: free key / user session, 2: complex setup
    cloud_safe: bool
    backends: List[str]
    doc_ref: str = ""
    fallback_chain: List[str] = field(default_factory=list)

    def is_operation_supported(self, op: str) -> bool:
        return op in self.operations


# Canonical 16-platform matrix derived from upstream Agent Reach (commit a19a171fa980a0785849596492e0af4db800c82f)
CAPABILITY_MATRIX: Dict[str, PlatformCapability] = {
    "web": PlatformCapability(
        platform="web",
        display_name="Web Page (Jina Reader)",
        operations={"read"},
        auth_mode="none",
        tier=0,
        cloud_safe=True,
        backends=["Jina Reader"],
        doc_ref="docs/README_en.md#supported-platforms",
        fallback_chain=[]
    ),
    "web_search": PlatformCapability(
        platform="web_search",
        display_name="Global Web Search",
        operations={"search"},
        auth_mode="none",
        tier=0,
        cloud_safe=True,
        backends=["Exa via mcporter", "Bing Search", "DuckDuckGo"],
        doc_ref="agent_reach/skill/references/search.md",
        fallback_chain=["Bing Search", "DuckDuckGo"]
    ),
    "github": PlatformCapability(
        platform="github",
        display_name="GitHub Repositories, Code & Releases",
        operations={"search", "read", "issues", "prs", "releases", "commits"},
        auth_mode="none",  # Public repos zero-auth; token optional for rate limits
        tier=0,
        cloud_safe=True,
        backends=["gh CLI", "GitHub REST"],
        doc_ref="agent_reach/skill/references/dev.md",
        fallback_chain=["GitHub REST"]
    ),
    "youtube": PlatformCapability(
        platform="youtube",
        display_name="YouTube Video, Metadata & Transcripts",
        operations={"search", "read", "transcript", "comments"},
        auth_mode="none",
        tier=0,
        cloud_safe=True,
        backends=["yt-dlp", "OpenCLI", "Whisper Transcribe"],
        doc_ref="agent_reach/skill/references/video.md",
        fallback_chain=["OpenCLI", "Whisper Transcribe"]
    ),
    "bilibili": PlatformCapability(
        platform="bilibili",
        display_name="Bilibili Video & Search",
        operations={"search", "read", "hot", "rank"},
        auth_mode="none",  # Search & metadata zero-auth; HD video needs session
        tier=1,
        cloud_safe=True,
        backends=["B站搜索 API", "bili-cli", "OpenCLI"],
        doc_ref="agent_reach/skill/references/video.md",
        fallback_chain=["bili-cli", "OpenCLI"]
    ),
    "v2ex": PlatformCapability(
        platform="v2ex",
        display_name="V2EX Tech Community",
        operations={"hot", "latest", "search", "topic", "replies"},
        auth_mode="none",
        tier=0,
        cloud_safe=True,
        backends=["V2EX API (public)"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=[]
    ),
    "rss": PlatformCapability(
        platform="rss",
        display_name="RSS / Official PR Wire Feeds",
        operations={"read"},
        auth_mode="none",
        tier=0,
        cloud_safe=True,
        backends=["feedparser"],
        doc_ref="agent_reach/skill/references/web.md",
        fallback_chain=[]
    ),
    "twitter": PlatformCapability(
        platform="twitter",
        display_name="Twitter / X Public Mirror & Status",
        operations={"search", "read", "status", "profile", "feed"},
        auth_mode="none",  # Zero-auth public retrieval via FxTwitter; auth not required for public retrieval
        tier=0,
        cloud_safe=True,
        backends=["FxTwitter", "Bing Search Index", "Google RSS"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=["Bing Search Index", "Google RSS"]
    ),
    "reddit": PlatformCapability(
        platform="reddit",
        display_name="Reddit Discussions & Comments (Arctic Shift)",
        operations={"search", "read", "comments"},
        auth_mode="none",  # Zero-auth public retrieval via Arctic Shift; auth not required for public retrieval
        tier=0,
        cloud_safe=True,
        backends=["Arctic Shift", "Reddit RSS", "Bing Search Index", "Google RSS"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=["Reddit RSS", "Bing Search Index", "Google RSS"]
    ),
    "xueqiu": PlatformCapability(
        platform="xueqiu",
        display_name="Xueqiu Financial Community & Quotes",
        operations={"search", "quotes", "hot_posts", "hot_stocks"},
        auth_mode="cookie_required",
        tier=1,
        cloud_safe=False,
        backends=["xueqiu-visitor-api", "OpenCLI", "Bing Search Index"],
        doc_ref="agent_reach/skill/references/finance.md",
        fallback_chain=["Bing Search Index"]
    ),
    "linkedin": PlatformCapability(
        platform="linkedin",
        display_name="LinkedIn Professional Profiles & Jobs",
        operations={"profile", "company", "jobs", "read"},
        auth_mode="session_required",
        tier=2,
        cloud_safe=False,
        backends=["linkedin-guest-jobs-api", "mcp-server-linkedin", "Bing Search Index"],
        doc_ref="agent_reach/skill/references/career.md",
        fallback_chain=["Bing Search Index"]
    ),
    "xiaohongshu": PlatformCapability(
        platform="xiaohongshu",
        display_name="XiaoHongShu Lifestyle & Product Notes",
        operations={"search", "read", "comments", "feed"},
        auth_mode="session_required",
        tier=1,
        cloud_safe=False,
        backends=["OpenCLI", "xiaohongshu-mcp", "Bing Search Index"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=["Bing Search Index"]
    ),
    "facebook": PlatformCapability(
        platform="facebook",
        display_name="Facebook Posts, Profiles & Groups",
        operations={"search", "profile", "feed", "groups", "oembed"},
        auth_mode="session_required",
        tier=1,
        cloud_safe=False,
        backends=["Meta oEmbed", "OpenCLI", "Bing Search Index"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=["Bing Search Index"]
    ),
    "instagram": PlatformCapability(
        platform="instagram",
        display_name="Instagram Profiles, Posts & Explore",
        operations={"search", "profile", "posts", "explore", "oembed"},
        auth_mode="session_required",
        tier=1,
        cloud_safe=False,
        backends=["Meta oEmbed", "OpenCLI", "Bing Search Index"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=["Bing Search Index"]
    ),
    "boss": PlatformCapability(
        platform="boss",
        display_name="Boss直聘 Jobs & Job Descriptions",
        operations={"search_jobs", "read_jd"},
        auth_mode="browser_cdp",
        tier=2,
        cloud_safe=False,
        backends=["boss-agent-cli (CDP)", "Bing Search Index"],
        doc_ref="agent_reach/skill/references/career.md",
        fallback_chain=["Bing Search Index"]
    ),
    "xiaoyuzhou": PlatformCapability(
        platform="xiaoyuzhou",
        display_name="Xiaoyuzhou Podcast Feeds & Audio",
        operations={"search", "episodes", "podcast", "transcribe"},
        auth_mode="api_key",
        tier=1,
        cloud_safe=False,
        backends=["podcast-rss-syndication", "groq-whisper", "Bing Search Index"],
        doc_ref="agent_reach/skill/references/video.md",
        fallback_chain=["Bing Search Index"]
    ),
}


def get_capability(platform: str) -> PlatformCapability:
    """Retrieve capability descriptor or a generic web fallback descriptor."""
    return CAPABILITY_MATRIX.get(
        platform,
        PlatformCapability(
            platform=platform,
            display_name=f"Generic Platform ({platform})",
            operations={"read"},
            auth_mode="none",
            tier=0,
            cloud_safe=True,
            backends=["Jina Reader"],
            fallback_chain=[]
        )
    )


# ── Structured Website Capability Registry ──────────────────────────────────

@dataclass
class WebsiteCapabilityRecord:
    """
    Structured website/platform capability definition according to Section 24.
    Used by both production planning and the scraper testing laboratory.
    """
    platform: str
    supported_operations: List[str]
    primary_backend: str
    fallback_backend: str
    auth_required: bool
    zero_auth_supported: bool
    discovery_supported: bool
    structured_metadata_supported: bool
    full_content_supported: bool
    comments_supported: bool
    transcript_supported: bool
    engagement_supported: bool
    current_schema_version: str = "v1.0"
    last_tested: str = ""
    health_status: str = "HEALTHY"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "supported_operations": self.supported_operations,
            "primary_backend": self.primary_backend,
            "fallback_backend": self.fallback_backend,
            "auth_required": self.auth_required,
            "zero_auth_supported": self.zero_auth_supported,
            "discovery_supported": self.discovery_supported,
            "structured_metadata_supported": self.structured_metadata_supported,
            "full_content_supported": self.full_content_supported,
            "comments_supported": self.comments_supported,
            "transcript_supported": self.transcript_supported,
            "engagement_supported": self.engagement_supported,
            "current_schema_version": self.current_schema_version,
            "last_tested": self.last_tested,
            "health_status": self.health_status,
        }


class WebsiteCapabilityRegistry:
    """
    Central registry of website capabilities and supported operations.
    """

    def __init__(self):
        self._registry: Dict[str, WebsiteCapabilityRecord] = {}
        self._init_defaults()

    def _init_defaults(self):
        records = [
            WebsiteCapabilityRecord(
                platform="reddit",
                supported_operations=["search", "read_post", "read_comments", "subreddit_posts"],
                primary_backend="arctic_shift",
                fallback_backend="web_search_index",
                auth_required=False,
                zero_auth_supported=True,
                discovery_supported=True,
                structured_metadata_supported=True,
                full_content_supported=True,
                comments_supported=True,
                transcript_supported=False,
                engagement_supported=True,
                current_schema_version="reddit_v2",
            ),
            WebsiteCapabilityRecord(
                platform="x",
                supported_operations=["read_status", "read_profile", "search"],
                primary_backend="fxtwitter",
                fallback_backend="web_search_index",
                auth_required=False,
                zero_auth_supported=True,
                discovery_supported=True,
                structured_metadata_supported=True,
                full_content_supported=True,
                comments_supported=False,
                transcript_supported=False,
                engagement_supported=True,
                current_schema_version="fxtwitter_v1",
            ),
            WebsiteCapabilityRecord(
                platform="youtube",
                supported_operations=["read_metadata", "read_transcript", "search"],
                primary_backend="yt_dlp_in_process",
                fallback_backend="web_search_index",
                auth_required=False,
                zero_auth_supported=True,
                discovery_supported=True,
                structured_metadata_supported=True,
                full_content_supported=True,
                comments_supported=True,
                transcript_supported=True,
                engagement_supported=True,
                current_schema_version="ytdlp_v1",
            ),
            WebsiteCapabilityRecord(
                platform="github",
                supported_operations=["read_repo", "read_issues", "read_prs", "read_releases", "search"],
                primary_backend="gh_api",
                fallback_backend="web_search_index",
                auth_required=False,
                zero_auth_supported=True,
                discovery_supported=True,
                structured_metadata_supported=True,
                full_content_supported=True,
                comments_supported=True,
                transcript_supported=False,
                engagement_supported=True,
                current_schema_version="gh_rest_v3",
            ),
            WebsiteCapabilityRecord(
                platform="web",
                supported_operations=["read_article", "search", "read_snippet"],
                primary_backend="scrapling_http",
                fallback_backend="playwright_rescue",
                auth_required=False,
                zero_auth_supported=True,
                discovery_supported=True,
                structured_metadata_supported=True,
                full_content_supported=True,
                comments_supported=False,
                transcript_supported=False,
                engagement_supported=False,
                current_schema_version="article_v1",
            ),
            WebsiteCapabilityRecord(
                platform="google_news",
                supported_operations=["search", "read_feed", "read_article"],
                primary_backend="rss_feed",
                fallback_backend="web_search_index",
                auth_required=False,
                zero_auth_supported=True,
                discovery_supported=True,
                structured_metadata_supported=True,
                full_content_supported=False,
                comments_supported=False,
                transcript_supported=False,
                engagement_supported=False,
                current_schema_version="rss_v2",
            ),
            WebsiteCapabilityRecord(
                platform="instagram",
                supported_operations=["search_discovery", "read_snippet"],
                primary_backend="search_discovery",
                fallback_backend="web_search_index",
                auth_required=True,
                zero_auth_supported=False,
                discovery_supported=True,
                structured_metadata_supported=False,
                full_content_supported=False,
                comments_supported=False,
                transcript_supported=False,
                engagement_supported=False,
                current_schema_version="walled_v1",
            ),
            WebsiteCapabilityRecord(
                platform="facebook",
                supported_operations=["search_discovery", "read_snippet"],
                primary_backend="search_discovery",
                fallback_backend="web_search_index",
                auth_required=True,
                zero_auth_supported=False,
                discovery_supported=True,
                structured_metadata_supported=False,
                full_content_supported=False,
                comments_supported=False,
                transcript_supported=False,
                engagement_supported=False,
                current_schema_version="walled_v1",
            ),
            WebsiteCapabilityRecord(
                platform="tiktok",
                supported_operations=["search_discovery", "read_snippet"],
                primary_backend="search_discovery",
                fallback_backend="web_search_index",
                auth_required=True,
                zero_auth_supported=False,
                discovery_supported=True,
                structured_metadata_supported=False,
                full_content_supported=False,
                comments_supported=False,
                transcript_supported=False,
                engagement_supported=False,
                current_schema_version="walled_v1",
            ),
            WebsiteCapabilityRecord(
                platform="linkedin",
                supported_operations=["search_discovery", "read_snippet"],
                primary_backend="search_discovery",
                fallback_backend="web_search_index",
                auth_required=True,
                zero_auth_supported=False,
                discovery_supported=True,
                structured_metadata_supported=False,
                full_content_supported=False,
                comments_supported=False,
                transcript_supported=False,
                engagement_supported=False,
                current_schema_version="walled_v1",
            ),
            WebsiteCapabilityRecord(
                platform="bilibili",
                supported_operations=["search_discovery", "read_snippet"],
                primary_backend="search_discovery",
                fallback_backend="web_search_index",
                auth_required=False,
                zero_auth_supported=True,
                discovery_supported=True,
                structured_metadata_supported=True,
                full_content_supported=False,
                comments_supported=False,
                transcript_supported=False,
                engagement_supported=False,
                current_schema_version="bilibili_v1",
            ),
        ]
        for r in records:
            self._registry[r.platform] = r

    def get(self, platform: str) -> Optional[WebsiteCapabilityRecord]:
        return self._registry.get((platform or "").lower().strip())

    def list_all(self) -> List[WebsiteCapabilityRecord]:
        return list(self._registry.values())


website_capability_registry = WebsiteCapabilityRegistry()
