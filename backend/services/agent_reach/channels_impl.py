"""
Aegis Protocol — Concrete Channel Implementations
===================================================
Wraps the existing AgentReachScraper methods into the Channel protocol.
Zero duplication — each implementation delegates to the proven scraper logic.
"""

import logging
from typing import Any, Dict, List

from backend.services.agent_reach.channels import (
    Channel,
    ChannelStatus,
    EvidenceFragment,
)

logger = logging.getLogger(__name__)


def _get_scraper():
    """Lazy import to avoid circular dependency at module load time."""
    from backend.services.agent_reach_scraper import reach_scraper
    return reach_scraper


class RedditChannel(Channel):
    """Reddit evidence channel backed by the existing zero-API scraper."""

    @property
    def name(self) -> str:
        return "reddit"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        scraper = _get_scraper()
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
        scraper = _get_scraper()
        try:
            results = scraper.search_reddit("technology", limit=2)
            if results:
                return ChannelStatus.AVAILABLE
            return ChannelStatus.DEGRADED
        except Exception:
            return ChannelStatus.UNAVAILABLE


class TwitterChannel(Channel):
    """Twitter/X evidence channel backed by the existing zero-API scraper."""

    @property
    def name(self) -> str:
        return "twitter"

    def search(self, query: str, limit: int = 6, vip_handle: str = None, **kwargs) -> List[EvidenceFragment]:
        scraper = _get_scraper()
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
        scraper = _get_scraper()
        try:
            results = scraper.search_twitter("technology", limit=2)
            if results:
                return ChannelStatus.AVAILABLE
            return ChannelStatus.DEGRADED
        except Exception:
            return ChannelStatus.UNAVAILABLE


class YouTubeChannel(Channel):
    """YouTube evidence channel backed by the existing zero-API scraper."""

    @property
    def name(self) -> str:
        return "youtube"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        scraper = _get_scraper()
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
            logger.warning(f"[YouTubeChannel] Search failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        scraper = _get_scraper()
        try:
            results = scraper.search_youtube("AI technology", limit=2)
            if results:
                return ChannelStatus.AVAILABLE
            return ChannelStatus.DEGRADED
        except Exception:
            return ChannelStatus.UNAVAILABLE


class NewsChannel(Channel):
    """News wire evidence channel backed by the existing zero-API scraper."""

    @property
    def name(self) -> str:
        return "news"

    def search(self, query: str, limit: int = 8, **kwargs) -> List[EvidenceFragment]:
        scraper = _get_scraper()
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
        scraper = _get_scraper()
        try:
            results = scraper.search_news("technology", limit=2)
            if results:
                return ChannelStatus.AVAILABLE
            return ChannelStatus.DEGRADED
        except Exception:
            return ChannelStatus.UNAVAILABLE


class JinaReaderChannel(Channel):
    """
    Jina Reader channel for converting web pages to clean markdown.

    Unlike other channels, this is a URL-targeted reader rather than
    a search channel. The search() method is a pass-through that
    reads the query as a URL.
    """

    @property
    def name(self) -> str:
        return "jina_reader"

    def search(self, query: str, limit: int = 1) -> List[EvidenceFragment]:
        """
        Read a URL and return its markdown content as a single EvidenceFragment.
        The 'query' parameter is treated as a URL for this channel.
        """
        scraper = _get_scraper()
        try:
            result = scraper.read_article_markdown(query, max_chars=4000)
            if result.get("status") in ("success", "fallback_soup"):
                return [EvidenceFragment(
                    platform="Web Article",
                    title=result.get("title", "Web Document"),
                    content=result.get("markdown", ""),
                    url=result.get("url", query),
                    snippet=result.get("markdown", "")[:200],
                    retrieval_method="jina_reader",
                    channel_name=self.name,
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
        scraper = _get_scraper()
        try:
            result = scraper.read_article_markdown("https://example.com", max_chars=200)
            status = result.get("status", "error")
            if status in ("success", "fallback_soup"):
                return ChannelStatus.AVAILABLE
            return ChannelStatus.DEGRADED
        except Exception:
            return ChannelStatus.UNAVAILABLE


class GitHubChannel(Channel):
    """
    GitHub evidence channel for technical claims, repo verification,
    releases, and open-source provenance.
    """

    @property
    def name(self) -> str:
        return "github"

    def search(self, query: str, limit: int = 5) -> List[EvidenceFragment]:
        import requests
        import urllib.parse
        clean_q = query.strip()
        encoded_q = urllib.parse.quote_plus(clean_q)
        url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page={limit}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AegisProtocol-AgentReach/1.0"
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
                        retrieval_method="github_api",
                        channel_name=self.name,
                        raw_metadata={
                            "stars": stars,
                            "forks": repo.get("forks_count", 0),
                            "language": repo.get("language"),
                            "license": repo.get("license", {}).get("spdx_id") if repo.get("license") else None,
                        }
                    ))
                return fragments
            elif resp.status_code == 403:
                logger.warning("[GitHubChannel] Rate limited by GitHub API")
                return []
            return []
        except Exception as e:
            logger.warning(f"[GitHubChannel] Search failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        import requests
        try:
            resp = requests.get(
                "https://api.github.com/zen",
                headers={"User-Agent": "AegisProtocol/1.0"},
                timeout=5.0
            )
            if resp.status_code == 200:
                return ChannelStatus.AVAILABLE
            elif resp.status_code == 403:
                return ChannelStatus.DEGRADED
            return ChannelStatus.UNAVAILABLE
        except Exception:
            return ChannelStatus.UNAVAILABLE


class RssChannel(Channel):
    """
    Syndicated RSS wire channel for official news, press releases,
    and verified wire dispatches. Differentiates from general news by focusing
    on official corporate wires, regulatory filings, and press releases.
    """

    @property
    def name(self) -> str:
        return "rss"

    def search(self, query: str, limit: int = 6, **kwargs) -> List[EvidenceFragment]:
        scraper = _get_scraper()
        # Differentiate from news: steer query towards press releases & official statements
        wire_terms = ["press release", "filing", "statement", "announcement", "regulatory", "wire"]
        if not any(wt in query.lower() for wt in wire_terms):
            wire_query = f"{query} (press release OR official statement OR filing OR wire)"
        else:
            wire_query = query

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
                # If from official portal or regulatory filing, mark as PRIMARY
                text_low = (f.title + " " + f.url).lower()
                if any(k in text_low for k in ["filing", "sec.gov", "bseindia", "nseindia", "investor", "statement"]):
                    f.raw_metadata["source_role"] = "PRIMARY"
                    f.raw_metadata["source_tier"] = "TIER_1_OFFICIAL_FILING"
                else:
                    f.raw_metadata["source_role"] = "SECONDARY"
                    f.raw_metadata["source_tier"] = "TIER_2_FINANCIAL_PRESS"
                fragments.append(f)
            return fragments
        except Exception as e:
            logger.warning(f"[RssChannel] Search failed: {e}")
            return []

    def health_check(self) -> ChannelStatus:
        scraper = _get_scraper()
        try:
            results = scraper.search_news("press release official", limit=2)
            if results:
                return ChannelStatus.AVAILABLE
            return ChannelStatus.DEGRADED
        except Exception:
            return ChannelStatus.UNAVAILABLE


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
        import base64
        import requests
        import urllib.parse
        from bs4 import BeautifulSoup

        clean_q = query.strip()
        fragments: List[EvidenceFragment] = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # 1. Bing Web Search (Fast, rich snippets, zero auth)
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


class AuthenticatedOptionalChannel(Channel):
    """
    Channel base for platforms requiring user credentials, browser automation,
    or session cookies (e.g. LinkedIn, Xiaohongshu, Instagram, Facebook).
    These gracefully report AUTH_REQUIRED so cloud deployments continue uninterrupted.
    """

    def __init__(self, channel_id: str, platform_name: str, auth_env_var: str = ""):
        self._name = channel_id
        self.platform_name = platform_name
        self.auth_env_var = auth_env_var

    @property
    def name(self) -> str:
        return self._name

    def search(self, query: str, limit: int = 6) -> List[EvidenceFragment]:
        import os
        if not self.auth_env_var or not os.getenv(self.auth_env_var):
            logger.debug(f"[{self.platform_name}Channel] Search skipped: {self.auth_env_var} not configured")
            return []
        return []

    def health_check(self) -> ChannelStatus:
        import os
        if self.auth_env_var and os.getenv(self.auth_env_var):
            return ChannelStatus.AVAILABLE
        return ChannelStatus.AUTH_REQUIRED

