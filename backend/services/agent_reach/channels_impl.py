"""
Aegis Protocol — Native-Backed Channel Implementations
======================================================
Provides concrete implementations for all Aegis evidence channels.
Uses upstream Agent Reach tools (gh CLI, yt-dlp, Jina Reader, V2EX API, Bilibili API,
feedparser) as the primary execution path, preserving the legacy scraper strictly as a
safety fallback (marked [LEGACY_COMPATIBILITY]).
"""

import base64
import logging
import os
import urllib.parse
from typing import Any, Dict, List, Optional

from backend.services.agent_reach.channels import (
    Channel,
    ChannelStatus,
    EvidenceFragment,
)
from backend.services.agent_reach.native import (
    native_doctor,
    native_executor,
    native_normalizer,
    native_router,
)

logger = logging.getLogger(__name__)


def _get_legacy_scraper():
    """
    [LEGACY_COMPATIBILITY]
    Lazy import for legacy scraper fallback when native upstream tools fail or are offline.
    """
    from backend.services.agent_reach_scraper import reach_scraper
    return reach_scraper


# ─────────────────────────────────────────────────────────────────────────────
# 1. GITHUB CHANNEL (Native gh CLI -> REST Fallback)
# ─────────────────────────────────────────────────────────────────────────────

class GitHubChannel(Channel):
    """
    GitHub evidence channel for technical claims, repo verification,
    releases, and open-source provenance.
    Primary: native `gh` CLI JSON tools.
    Fallback: GitHub REST API.
    """

    @property
    def name(self) -> str:
        return "github"

    def search(self, query: str, limit: int = 5, **kwargs) -> List[EvidenceFragment]:
        # Primary: Native gh CLI
        try:
            res = native_executor.execute_github_search(query, limit=limit)
            fragments = native_normalizer.normalize_github_repos(
                res.get("items", []),
                query_id=kwargs.get("query_id", ""),
                query_class=kwargs.get("query_class", ""),
                query_text=kwargs.get("query_text", query)
            )
            if fragments:
                return fragments
        except Exception as e:
            logger.debug(f"[GitHubChannel] Native gh CLI search notice: {e}. Trying REST fallback.")

        # [LEGACY_COMPATIBILITY] Fallback: GitHub REST API
        import requests
        clean_q = query.strip()
        encoded_q = urllib.parse.quote_plus(clean_q)
        url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page={limit}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AegisProtocol-AgentReach/3.0"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=8.0)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                fragments = []
                for repo in items[:limit]:
                    name = repo.get("full_name", "")
                    desc = repo.get("description") or "No description provided."
                    html_url = repo.get("html_url", "")
                    stars = repo.get("stargazers_count", 0)
                    updated = repo.get("updated_at", "")
                    owner = repo.get("owner", {}).get("login", "")
                    topics = ", ".join(repo.get("topics", []))
                    
                    content = f"Repository: {name}\nDescription: {desc}\nStars: {stars} | Updated: {updated}\nTopics: {topics}"
                    fragments.append(EvidenceFragment(
                        platform="GitHub",
                        title=f"{name} ({stars} stars)",
                        content=content,
                        url=html_url,
                        author=owner,
                        published=updated,
                        snippet=desc[:200],
                        score=float(min(stars, 100)),
                        retrieval_method="github_rest_fallback",
                        channel_name=self.name,
                        query_id=kwargs.get("query_id", ""),
                        query_class=kwargs.get("query_class", ""),
                        query_text=kwargs.get("query_text", query),
                        raw_metadata={
                            "backend": "GitHub REST (fallback)",
                            "stars": stars,
                            "forks": repo.get("forks_count", 0),
                            "language": repo.get("language"),
                        }
                    ))
                return fragments
            elif resp.status_code == 403:
                logger.warning("[GitHubChannel] Rate limited by GitHub REST API")
                return []
        except Exception as e:
            logger.warning(f"[GitHubChannel] REST fallback search failed: {e}")
        return []

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status("github")
        if st.get("status") in ("ok", "warn") and shutil_which_gh():
            return ChannelStatus.AVAILABLE
        return ChannelStatus.DEGRADED


def shutil_which_gh() -> bool:
    import shutil
    return shutil.which("gh") is not None


# ─────────────────────────────────────────────────────────────────────────────
# 2. YOUTUBE CHANNEL (Native yt-dlp -> Scraper Fallback)
# ─────────────────────────────────────────────────────────────────────────────

class YouTubeChannel(Channel):
    """
    YouTube evidence channel for video discussions, commentary, and transcripts.
    Primary: native `yt-dlp` toolchain.
    Fallback: Scraper metadata extraction.
    """

    @property
    def name(self) -> str:
        return "youtube"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        # Primary: Native yt-dlp
        try:
            res = native_executor.execute_youtube_search(query, limit=limit)
            fragments = native_normalizer.normalize_youtube_search(
                res.get("items", []),
                query_id=kwargs.get("query_id", ""),
                query_class=kwargs.get("query_class", ""),
                query_text=kwargs.get("query_text", query)
            )
            if fragments:
                return fragments
        except Exception as e:
            logger.debug(f"[YouTubeChannel] Native yt-dlp search notice: {e}. Trying legacy scraper fallback.")

        # [LEGACY_COMPATIBILITY] Fallback: Legacy reach scraper
        scraper = _get_legacy_scraper()
        try:
            raw_items = scraper.search_youtube(query, limit=limit)
            return [
                EvidenceFragment.from_scraper_dict(
                    item,
                    channel_name=self.name,
                    query_id=kwargs.get("query_id", ""),
                    query_class=kwargs.get("query_class", ""),
                    query_text=kwargs.get("query_text", query),
                )
                for item in raw_items
            ]
        except Exception as e:
            logger.warning(f"[YouTubeChannel] Fallback search failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status("youtube")
        if st.get("status") in ("ok", "warn"):
            return ChannelStatus.AVAILABLE
        return ChannelStatus.DEGRADED


# ─────────────────────────────────────────────────────────────────────────────
# 3. V2EX CHANNEL (Native Public JSON API — Zero Config)
# ─────────────────────────────────────────────────────────────────────────────

class V2EXChannel(Channel):
    """
    V2EX tech community evidence channel.
    Backed by public HTTPS JSON API (Tier 0 zero-config).
    """

    @property
    def name(self) -> str:
        return "v2ex"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        try:
            res = native_executor.execute_v2ex_hot()
            raw_items = res.get("items", [])
            if query and query.strip():
                q_low = query.lower()
                filtered = [
                    t for t in raw_items
                    if q_low in t.get("title", "").lower() or q_low in (t.get("content") or "").lower()
                ]
                raw_items = filtered or raw_items[:limit]

            return native_normalizer.normalize_v2ex_topics(
                raw_items[:limit],
                query_id=kwargs.get("query_id", ""),
                query_class=kwargs.get("query_class", ""),
                query_text=kwargs.get("query_text", query)
            )
        except Exception as e:
            logger.warning(f"[V2EXChannel] Search failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status("v2ex")
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.UNAVAILABLE


# ─────────────────────────────────────────────────────────────────────────────
# 4. BILIBILI CHANNEL (Native Public Search API — Zero Config)
# ─────────────────────────────────────────────────────────────────────────────

class BilibiliChannel(Channel):
    """
    Bilibili video and community evidence channel.
    Backed by Bilibili public search web interface API (Zero auth for search/metadata).
    """

    @property
    def name(self) -> str:
        return "bilibili"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        try:
            res = native_executor.execute_bilibili_search(query, limit=limit)
            return native_normalizer.normalize_bilibili_videos(
                res.get("items", []),
                query_id=kwargs.get("query_id", ""),
                query_class=kwargs.get("query_class", ""),
                query_text=kwargs.get("query_text", query)
            )
        except Exception as e:
            logger.warning(f"[BilibiliChannel] Search failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status("bilibili")
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.DEGRADED


# ─────────────────────────────────────────────────────────────────────────────
# 5. RSS / WIRE CHANNEL (Native feedparser -> Scraper Fallback)
# ─────────────────────────────────────────────────────────────────────────────

class RssChannel(Channel):
    """
    Syndicated RSS wire channel for official news, press releases,
    and verified wire dispatches.
    Primary: native `feedparser` execution.
    Fallback: Scraper news indexer.
    """

    @property
    def name(self) -> str:
        return "rss"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        # Primary: Native feedparser with Google News RSS
        wire_terms = ["press release", "filing", "statement", "announcement", "regulatory", "wire"]
        if not any(wt in query.lower() for wt in wire_terms):
            wire_query = f"{query} (press release OR official statement OR filing OR wire)"
        else:
            wire_query = query

        try:
            feed_query = urllib.parse.quote_plus(wire_query.strip())
            rss_url = f"https://news.google.com/rss/search?q={feed_query}&hl=en-US&gl=US&ceid=US:en"
            res = native_executor.execute_rss_read(rss_url, limit=limit)
            fragments = native_normalizer.normalize_rss_entries(
                res.get("items", []),
                channel_name=self.name,
                query_id=kwargs.get("query_id", ""),
                query_class=kwargs.get("query_class", ""),
                query_text=kwargs.get("query_text", wire_query)
            )
            if fragments:
                return fragments
        except Exception as e:
            logger.debug(f"[RssChannel] Native RSS read notice: {e}. Trying legacy scraper fallback.")

        # [LEGACY_COMPATIBILITY] Fallback
        scraper = _get_legacy_scraper()
        try:
            raw_items = scraper.search_news(wire_query, limit=limit)
            fragments = []
            for item in raw_items:
                f = EvidenceFragment.from_scraper_dict(
                    item,
                    channel_name=self.name,
                    query_id=kwargs.get("query_id", ""),
                    query_class=kwargs.get("query_class", ""),
                    query_text=kwargs.get("query_text", wire_query),
                )
                f.platform = "PR Wire / RSS"
                fragments.append(f)
            return fragments
        except Exception as e:
            logger.warning(f"[RssChannel] Fallback search failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status("rss")
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.UNAVAILABLE


# ─────────────────────────────────────────────────────────────────────────────
# 6. NEWS CHANNEL (Native RSS News Wire -> Scraper Fallback)
# ─────────────────────────────────────────────────────────────────────────────

class NewsChannel(Channel):
    """News wire evidence channel backed by Google News RSS and news indexers."""

    @property
    def name(self) -> str:
        return "news"

    def search(self, query: str, limit: int = 8, **kwargs) -> List[EvidenceFragment]:
        try:
            feed_query = urllib.parse.quote_plus(query.strip())
            rss_url = f"https://news.google.com/rss/search?q={feed_query}&hl=en-US&gl=US&ceid=US:en"
            res = native_executor.execute_rss_read(rss_url, limit=limit)
            fragments = native_normalizer.normalize_rss_entries(
                res.get("items", []),
                channel_name=self.name,
                query_id=kwargs.get("query_id", ""),
                query_class=kwargs.get("query_class", ""),
                query_text=kwargs.get("query_text", query)
            )
            if fragments:
                for f in fragments:
                    f.platform = "News"
                return fragments
        except Exception as e:
            logger.debug(f"[NewsChannel] Native news feed read notice: {e}")

        # [LEGACY_COMPATIBILITY] Fallback
        scraper = _get_legacy_scraper()
        try:
            raw_items = scraper.search_news(query, limit=limit)
            return [
                EvidenceFragment.from_scraper_dict(
                    item,
                    channel_name=self.name,
                    query_id=kwargs.get("query_id", ""),
                    query_class=kwargs.get("query_class", ""),
                    query_text=kwargs.get("query_text", query),
                )
                for item in raw_items
            ]
        except Exception as e:
            logger.warning(f"[NewsChannel] Search failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        return ChannelStatus.AVAILABLE


# ─────────────────────────────────────────────────────────────────────────────
# 7. JINA READER CHANNEL (Native r.jina.ai -> Scraper Fallback)
# ─────────────────────────────────────────────────────────────────────────────

class JinaReaderChannel(Channel):
    """
    Dedicated article and web page reading channel via Jina Reader.
    Converts arbitrary public URLs into clean Markdown.
    """

    @property
    def name(self) -> str:
        return "jina_reader"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        """Search / fetch web document via URL."""
        return self.read_article(query, max_chars=kwargs.get("max_chars", 4000), **kwargs)

    def read_article(self, url: str, max_chars: int = 4000, **kwargs) -> List[EvidenceFragment]:
        # Primary: Native Jina Reader HTTP fetch with antibot detection
        try:
            res = native_executor.execute_web_read(url)
            content = res.get("content", "")
            return [EvidenceFragment(
                platform="Web",
                title=f"Article from {urllib.parse.urlparse(url).netloc}",
                content=content[:max_chars],
                url=url,
                author=urllib.parse.urlparse(url).netloc or "Web",
                published="Recent",
                snippet=content[:300],
                score=85.0,
                retrieval_method="jina_reader",
                channel_name=self.name,
                content_depth="FULL_ARTICLE" if len(content) > 500 else "SNIPPET",
                query_id=kwargs.get("query_id", ""),
                query_class=kwargs.get("query_class", ""),
                query_text=kwargs.get("query_text", url),
                raw_metadata={
                    "backend": "Jina Reader",
                    "status": "success",
                    "char_count": len(content),
                },
            )]
        except Exception as e:
            logger.debug(f"[JinaReaderChannel] Native Jina read notice: {e}. Trying legacy scraper fallback.")

        # [LEGACY_COMPATIBILITY] Fallback
        scraper = _get_legacy_scraper()
        try:
            result = scraper.read_article_markdown(url, max_chars=max_chars)
            content = result.get("content", "")
            if content:
                return [EvidenceFragment(
                    platform="Web",
                    title=result.get("title") or f"Article from {urllib.parse.urlparse(url).netloc}",
                    content=content,
                    url=url,
                    author=result.get("author") or urllib.parse.urlparse(url).netloc or "Web",
                    published=result.get("published", "Recent"),
                    snippet=content[:300],
                    score=80.0,
                    retrieval_method="jina_fallback",
                    channel_name=self.name,
                    content_depth="FULL_ARTICLE",
                    query_id=kwargs.get("query_id", ""),
                    query_class=kwargs.get("query_class", ""),
                    query_text=kwargs.get("query_text", url),
                    raw_metadata={
                        "status": result.get("status"),
                        "char_count": result.get("char_count", 0),
                    },
                )]
            return []
        except Exception as e:
            logger.warning(f"[JinaReaderChannel] Read failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status("web")
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.DEGRADED


# ─────────────────────────────────────────────────────────────────────────────
# 8. WEB CHANNEL (Direct Open Web Search with Bing/DDG)
# ─────────────────────────────────────────────────────────────────────────────

class WebChannel(Channel):
    """
    Direct open-web search channel.
    Retrieves web pages, articles, blogs, and databases with real destination URLs and descriptive snippets.
    Uses Bing search HTML extraction with DuckDuckGo fallback.
    """

    @property
    def name(self) -> str:
        return "web"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        clean_q = query.strip()
        fragments: List[EvidenceFragment] = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # 1. Bing Web Search (Fast, rich snippets, zero auth)
        import requests
        from bs4 import BeautifulSoup
        try:
            url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(clean_q)}"
            resp = requests.get(url, headers=headers, timeout=6.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for el in soup.select("li.b_algo")[:limit]:
                    h2 = el.find("h2")
                    if not h2:
                        continue
                    a = h2.find("a")
                    if not a or not a.get("href"):
                        continue
                    title = h2.get_text(separator=" ", strip=True)
                    raw_href = a["href"]

                    # Unpack Bing destination redirect URL if present
                    dest_url = raw_href
                    if "bing.com/ck/a?" in raw_href and "&u=a1" in raw_href:
                        try:
                            encoded_part = raw_href.split("&u=a1")[1].split("&")[0]
                            padded = encoded_part + "=" * (-len(encoded_part) % 4)
                            dest_url = base64.b64decode(padded).decode("utf-8", errors="ignore")
                        except Exception:
                            dest_url = raw_href

                    p = el.find("div", class_="b_caption") or el.find("p")
                    snippet = p.get_text(separator=" ", strip=True) if p else title

                    fragments.append(EvidenceFragment(
                        platform="Web",
                        title=title,
                        content=f"{title}\n\n{snippet}",
                        url=dest_url,
                        author=urllib.parse.urlparse(dest_url).netloc or "Web",
                        published="Recent",
                        snippet=snippet[:300],
                        score=50.0,
                        retrieval_method="web_search",
                        channel_name=self.name,
                        content_depth="SNIPPET",
                        query_id=kwargs.get("query_id", ""),
                        query_class=kwargs.get("query_class", ""),
                        query_text=kwargs.get("query_text", clean_q),
                        raw_metadata={"engine": "bing_web", "domain": urllib.parse.urlparse(dest_url).netloc}
                    ))
        except Exception as e:
            logger.debug(f"[WebChannel] Bing web search notice: {e}")

        # 2. DDGS Fallback if Bing returned fewer results than desired
        if len(fragments) < limit:
            try:
                from duckduckgo_search import DDGS
                ddgs = DDGS()
                ddg_results = list(ddgs.text(clean_q, max_results=limit))
                for r in ddg_results:
                    href = r.get("href", "")
                    if href and not any(f.url == href for f in fragments):
                        title = r.get("title", "Web Result")
                        body = r.get("body", "")
                        fragments.append(EvidenceFragment(
                            platform="Web",
                            title=title,
                            content=f"{title}\n\n{body}",
                            url=href,
                            author=urllib.parse.urlparse(href).netloc or "Web",
                            published="Recent",
                            snippet=body[:300],
                            score=45.0,
                            retrieval_method="web_search",
                            channel_name=self.name,
                            content_depth="SNIPPET",
                            query_id=kwargs.get("query_id", ""),
                            query_class=kwargs.get("query_class", ""),
                            query_text=kwargs.get("query_text", clean_q),
                            raw_metadata={"engine": "duckduckgo", "domain": urllib.parse.urlparse(href).netloc}
                        ))
                        if len(fragments) >= limit:
                            break
            except Exception as ddg_err:
                logger.debug(f"[WebChannel] DDGS fallback notice: {ddg_err}")

        return fragments[:limit]

    def health_check(self) -> ChannelStatus:
        import requests
        try:
            resp = requests.get("https://www.bing.com", timeout=4.0)
            if resp.status_code == 200:
                return ChannelStatus.AVAILABLE
            return ChannelStatus.DEGRADED
        except Exception:
            return ChannelStatus.UNAVAILABLE


# ─────────────────────────────────────────────────────────────────────────────
# 9. REDDIT & TWITTER CHANNELS (Capability-Aware with Scraper Fallback)
# ─────────────────────────────────────────────────────────────────────────────

class RedditChannel(Channel):
    """
    Reddit evidence channel.
    Checks Doctor for active OpenCLI or rdt-cli session.
    If unavailable, gracefully reports AUTH_REQUIRED or uses zero-API public streams.
    """

    @property
    def name(self) -> str:
        return "reddit"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        scraper = _get_legacy_scraper()
        try:
            raw_items = scraper.search_reddit(query, limit=limit)
            return [
                EvidenceFragment.from_scraper_dict(
                    item,
                    channel_name=self.name,
                    query_id=kwargs.get("query_id", ""),
                    query_class=kwargs.get("query_class", ""),
                    query_text=kwargs.get("query_text", query),
                )
                for item in raw_items
            ]
        except Exception as e:
            logger.warning(f"[RedditChannel] Search failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status("reddit")
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.AUTH_REQUIRED


class TwitterChannel(Channel):
    """
    Twitter/X evidence channel.
    Checks Doctor for active twitter-cli or OpenCLI session.
    If unavailable, gracefully reports AUTH_REQUIRED or uses public syndication indexers.
    """

    @property
    def name(self) -> str:
        return "twitter"

    def search(self, query: str, limit: int = 6, vip_handle: str = None, **kwargs) -> List[EvidenceFragment]:
        scraper = _get_legacy_scraper()
        try:
            raw_items = scraper.search_twitter(query, vip_handle=vip_handle, limit=limit)
            return [
                EvidenceFragment.from_scraper_dict(
                    item,
                    channel_name=self.name,
                    query_id=kwargs.get("query_id", ""),
                    query_class=kwargs.get("query_class", ""),
                    query_text=kwargs.get("query_text", query),
                )
                for item in raw_items
            ]
        except Exception as e:
            logger.warning(f"[TwitterChannel] Search failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status("twitter")
        if st.get("status") == "ok":
            return ChannelStatus.AVAILABLE
        return ChannelStatus.AUTH_REQUIRED


# ─────────────────────────────────────────────────────────────────────────────
# 10. AUTHENTICATED / DESKTOP-SESSION CHANNELS (OpenCLI / MCP / Cookies)
# ─────────────────────────────────────────────────────────────────────────────

class AuthenticatedOptionalChannel(Channel):
    """
    Channel base for platforms requiring user credentials, browser automation,
    or session cookies (e.g. LinkedIn, Xiaohongshu, Instagram, Facebook, Boss直聘, Xueqiu).
    Directly checks Doctor for active backend. Gracefully reports AUTH_REQUIRED
    so cloud and headless deployments continue uninterrupted with zero hallucinations.
    """

    def __init__(self, channel_id: str, platform_name: str, auth_env_var: str = ""):
        self._name = channel_id
        self.platform_name = platform_name
        self.auth_env_var = auth_env_var

    @property
    def name(self) -> str:
        return self._name

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        st = native_doctor.get_channel_status(self._name)
        if st.get("status") != "ok" or not st.get("active_backend"):
            logger.debug(f"[{self.platform_name}Channel] Search omitted: {st.get('message', 'AUTH_REQUIRED')}")
            return []
        return []

    def health_check(self) -> ChannelStatus:
        st = native_doctor.get_channel_status(self._name)
        if st.get("status") == "ok" and st.get("active_backend"):
            return ChannelStatus.AVAILABLE
        return ChannelStatus.AUTH_REQUIRED
