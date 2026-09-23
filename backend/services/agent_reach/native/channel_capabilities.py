"""
Aegis Protocol — Native Agent Reach Channel Capabilities Matrix
===============================================================
Defines the canonical metadata, supported operations, authentication requirements,
and runtime constraints across all 16 platforms supported by upstream Agent Reach.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set


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
        display_name="Twitter / X Feeds & Search",
        operations={"search", "read", "feed", "user_posts", "article"},
        auth_mode="cookie_required",
        tier=1,
        cloud_safe=False,
        backends=["twitter-cli", "OpenCLI", "bird CLI (legacy)"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=["OpenCLI"]
    ),
    "reddit": PlatformCapability(
        platform="reddit",
        display_name="Reddit Discussions & Comments",
        operations={"search", "read", "comments"},
        auth_mode="session_required",
        tier=1,
        cloud_safe=False,
        backends=["OpenCLI", "rdt-cli"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=["rdt-cli"]
    ),
    "xueqiu": PlatformCapability(
        platform="xueqiu",
        display_name="Xueqiu Financial Community & Quotes",
        operations={"search", "quotes", "hot_posts", "hot_stocks"},
        auth_mode="cookie_required",
        tier=1,
        cloud_safe=False,
        backends=["OpenCLI", "Xueqiu API"],
        doc_ref="agent_reach/skill/references/finance.md",
        fallback_chain=["Xueqiu API"]
    ),
    "linkedin": PlatformCapability(
        platform="linkedin",
        display_name="LinkedIn Professional Profiles & Jobs",
        operations={"profile", "company", "jobs", "read"},
        auth_mode="session_required",
        tier=2,
        cloud_safe=False,
        backends=["mcp-server-linkedin", "Jina Reader"],
        doc_ref="agent_reach/skill/references/career.md",
        fallback_chain=["Jina Reader"]
    ),
    "xiaohongshu": PlatformCapability(
        platform="xiaohongshu",
        display_name="XiaoHongShu Lifestyle & Product Notes",
        operations={"search", "read", "comments", "feed"},
        auth_mode="session_required",
        tier=1,
        cloud_safe=False,
        backends=["OpenCLI", "xiaohongshu-mcp", "xhs-cli"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=["xiaohongshu-mcp", "xhs-cli"]
    ),
    "facebook": PlatformCapability(
        platform="facebook",
        display_name="Facebook Posts, Profiles & Groups",
        operations={"search", "profile", "feed", "groups"},
        auth_mode="session_required",
        tier=1,
        cloud_safe=False,
        backends=["OpenCLI"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=[]
    ),
    "instagram": PlatformCapability(
        platform="instagram",
        display_name="Instagram Profiles, Posts & Explore",
        operations={"search", "profile", "posts", "explore"},
        auth_mode="session_required",
        tier=1,
        cloud_safe=False,
        backends=["OpenCLI"],
        doc_ref="agent_reach/skill/references/social.md",
        fallback_chain=[]
    ),
    "boss": PlatformCapability(
        platform="boss",
        display_name="Boss直聘 Jobs & Job Descriptions",
        operations={"search_jobs", "read_jd"},
        auth_mode="browser_cdp",
        tier=2,
        cloud_safe=False,
        backends=["boss-agent-cli (CDP)"],
        doc_ref="agent_reach/skill/references/career.md",
        fallback_chain=[]
    ),
    "xiaoyuzhou": PlatformCapability(
        platform="xiaoyuzhou",
        display_name="Xiaoyuzhou Podcast Transcripts",
        operations={"transcribe"},
        auth_mode="api_key",
        tier=1,
        cloud_safe=True,
        backends=["groq-whisper", "ffmpeg"],
        doc_ref="agent_reach/skill/references/video.md",
        fallback_chain=[]
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
