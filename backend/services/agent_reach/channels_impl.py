"""
Aegis Protocol — Native-Backed Channel Implementations
======================================================
Provides concrete implementations for all Aegis evidence channels.
Every channel delegates execution directly to NativeRouter, establishing a
single capability-aware dispatch and fallback bottleneck while maintaining
the object-oriented Channel interface.
"""

import logging
import shutil
from typing import Any, Dict, List, Optional

from backend.services.agent_reach.channels import (
    Channel,
    ChannelStatus,
    EvidenceFragment,
)
from backend.services.agent_reach.native import (
    native_doctor,
    native_router,
)

logger = logging.getLogger(__name__)


def _get_legacy_scraper():
    """
    [LEGACY_COMPATIBILITY]
    Lazy import for legacy scraper fallback when needed.
    """
    from backend.services.agent_reach_scraper import reach_scraper
    return reach_scraper


def shutil_which_gh() -> bool:
    """Helper to detect gh CLI availability on host."""
    return shutil.which("gh") is not None


def _dispatch_channel_query(channel_name: str, query: str, limit: int, default_domain: str = "general", **kwargs) -> List[EvidenceFragment]:
    kw = dict(kwargs)
    q_id = kw.pop("query_id", "")
    q_cls = kw.pop("query_class", "")
    q_txt = kw.pop("query_text", query)
    dom = kw.pop("domain", default_domain)
    fragments, _ = native_router.execute_channel_query(
        platform=channel_name,
        query=query,
        limit=limit,
        query_id=q_id,
        query_class=q_cls,
        query_text=q_txt,
        domain=dom,
        **kw
    )
    return fragments


# ─────────────────────────────────────────────────────────────────────────────
# 1. GITHUB CHANNEL
# ─────────────────────────────────────────────────────────────────────────────

class GitHubChannel(Channel):
    """
    GitHub evidence channel for technical claims, repo verification,
    releases, and open-source provenance.
    Routes via NativeRouter (gh CLI primary, REST fallback).
    """

    @property
    def name(self) -> str:
        return "github"

    def search(self, query: str, limit: int = 5, **kwargs) -> List[EvidenceFragment]:
        return _dispatch_channel_query(self.name, query, limit=limit, default_domain="tech", **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self.name)
        if st.get("status") in ("ok", "warn") and shutil_which_gh():
            return ChannelStatus.AVAILABLE
        return ChannelStatus.DEGRADED


# ─────────────────────────────────────────────────────────────────────────────
# 2. YOUTUBE CHANNEL
# ─────────────────────────────────────────────────────────────────────────────

class YouTubeChannel(Channel):
    """
    YouTube evidence channel for video discussions, commentary, and transcripts.
    Routes via NativeRouter (yt-dlp primary, scraper fallback).
    """

    @property
    def name(self) -> str:
        return "youtube"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        return _dispatch_channel_query(self.name, query, limit=limit, default_domain="video", **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self.name)
        if st.get("status") in ("ok", "warn"):
            return ChannelStatus.AVAILABLE
        return ChannelStatus.DEGRADED


# ─────────────────────────────────────────────────────────────────────────────
# 3. V2EX CHANNEL (Public REST API — Zero Config)
# ─────────────────────────────────────────────────────────────────────────────

class V2EXChannel(Channel):
    """
    V2EX tech community evidence channel.
    Routes via NativeRouter (public JSON API).
    """

    @property
    def name(self) -> str:
        return "v2ex"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        return _dispatch_channel_query(self.name, query, limit=limit, default_domain="general", **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self.name)
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.UNAVAILABLE


# ─────────────────────────────────────────────────────────────────────────────
# 4. BILIBILI CHANNEL (Public Search API — Zero Config)
# ─────────────────────────────────────────────────────────────────────────────

class BilibiliChannel(Channel):
    """
    Bilibili video and community evidence channel.
    Routes via NativeRouter (public search API).
    """

    @property
    def name(self) -> str:
        return "bilibili"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        return _dispatch_channel_query(self.name, query, limit=limit, default_domain="video", **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self.name)
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.DEGRADED


# ─────────────────────────────────────────────────────────────────────────────
# 5. RSS / PR WIRE CHANNEL
# ─────────────────────────────────────────────────────────────────────────────

class RssChannel(Channel):
    """
    Syndicated RSS wire channel for official news, press releases,
    and verified wire dispatches. Routes via NativeRouter.
    """

    @property
    def name(self) -> str:
        return "rss"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        return _dispatch_channel_query(self.name, query, limit=limit, default_domain="news", **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self.name)
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.UNAVAILABLE


# ─────────────────────────────────────────────────────────────────────────────
# 6. NEWS CHANNEL (News Wire via RSS)
# ─────────────────────────────────────────────────────────────────────────────

class NewsChannel(Channel):
    """News wire evidence channel backed by Google News RSS. Routes via NativeRouter."""

    @property
    def name(self) -> str:
        return "news"

    def search(self, query: str, limit: int = 8, **kwargs) -> List[EvidenceFragment]:
        return _dispatch_channel_query(self.name, query, limit=limit, default_domain="news", **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self.name)
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.DEGRADED


# ─────────────────────────────────────────────────────────────────────────────
# 7. JINA READER CHANNEL (Content Extraction)
# ─────────────────────────────────────────────────────────────────────────────

class JinaReaderChannel(Channel):
    """
    Dedicated high-throughput content extraction channel.
    Routes document reads through NativeRouter with SSRF validation.
    """

    @property
    def name(self) -> str:
        return "jina_reader"

    def search(self, query: str, limit: int = 1, **kwargs) -> List[EvidenceFragment]:
        return _dispatch_channel_query(self.name, query, limit=limit, default_domain="general", url=query, **kwargs)

    def read(self, url: str, max_chars: int = 4000, **kwargs) -> Dict[str, Any]:
        return native_router.execute_channel_read(url, max_chars=max_chars, **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status("web")
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.DEGRADED


# ─────────────────────────────────────────────────────────────────────────────
# 8. WEB CHANNEL (Direct Open Web Search)
# ─────────────────────────────────────────────────────────────────────────────

class WebChannel(Channel):
    """
    Direct open-web search channel.
    Retrieves web pages, articles, blogs, and databases with real destination URLs.
    Routes via NativeRouter.
    """

    @property
    def name(self) -> str:
        return "web"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        return _dispatch_channel_query(self.name, query, limit=limit, default_domain="web", **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self.name)
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.DEGRADED


# ─────────────────────────────────────────────────────────────────────────────
# 9. REDDIT & TWITTER CHANNELS
# ─────────────────────────────────────────────────────────────────────────────

class RedditChannel(Channel):
    """Reddit discussion channel with auth checks and honest fallback."""

    @property
    def name(self) -> str:
        return "reddit"

    def search(self, query: str, limit: int = 6, subreddit: str = None, **kwargs) -> List[EvidenceFragment]:
        search_q = f"r/{subreddit} {query}" if subreddit else query
        return _dispatch_channel_query(self.name, search_q, limit=limit, default_domain="social", **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self.name)
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.AUTH_REQUIRED


class TwitterChannel(Channel):
    """Twitter / X discussion channel with auth checks and honest fallback."""

    @property
    def name(self) -> str:
        return "twitter"

    def search(self, query: str, limit: int = 6, vip_handle: str = None, **kwargs) -> List[EvidenceFragment]:
        search_q = f"from:{vip_handle} {query}" if vip_handle else query
        return _dispatch_channel_query(self.name, search_q, limit=limit, default_domain="social", **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self.name)
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.AUTH_REQUIRED


# ─────────────────────────────────────────────────────────────────────────────
# 10. AUTHENTICATED / DESKTOP-SESSION CHANNELS (OpenCLI / Cookies)
# ─────────────────────────────────────────────────────────────────────────────

class AuthenticatedOptionalChannel(Channel):
    """
    Channel base for platforms requiring user credentials, browser automation,
    or session cookies (LinkedIn, Xiaohongshu, Instagram, Facebook, Boss直聘, Xueqiu).
    Routes via NativeRouter which verifies active backend and reports AUTH_REQUIRED.
    """

    def __init__(self, channel_id: str, platform_name: str, auth_env_var: str = ""):
        self._name = channel_id
        self.platform_name = platform_name
        self.auth_env_var = auth_env_var

    @property
    def name(self) -> str:
        return self._name

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        return _dispatch_channel_query(self._name, query, limit=limit, default_domain="social", **kwargs)

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self._name)
        if st.get("status") == "ok" and st.get("active_backend"):
            return ChannelStatus.AVAILABLE
        return ChannelStatus.AUTH_REQUIRED

