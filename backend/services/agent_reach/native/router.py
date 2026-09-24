"""
Aegis Protocol — Native Agent Reach Capability Router
======================================================
The single authoritative runtime dispatch layer for Agent Reach.
Routes channel queries and document reads to the active upstream backend
determined by live Doctor checks, coordinates allowlisted native execution,
applies explicit fallback chains when primary tools are offline or throttled,
and records comprehensive execution telemetry for every attempt.
"""

import base64
import logging
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from backend.services.agent_reach.channels import ChannelStatus, EvidenceFragment
from backend.services.agent_reach.native.channel_capabilities import get_capability
from backend.services.agent_reach.native.doctor import native_doctor
from backend.services.agent_reach.native.errors import AuthRequiredError, NativeReachError
from backend.services.agent_reach.native.executor import native_executor
from backend.services.agent_reach.native.normalizer import native_normalizer
from backend.services.url_validator import is_safe_url

logger = logging.getLogger(__name__)


def _get_legacy_scraper():
    """
    [LEGACY_COMPATIBILITY]
    Lazy import for legacy scraper fallback strictly when native upstream tools fail.
    """
    from backend.services.agent_reach_scraper import reach_scraper
    return reach_scraper


class NativeRouter:
    """
    Central capability-aware channel router coordinating native execution across platforms.
    Owns backend selection, auth verification, primary tool execution, fallback chains,
    and telemetry attribution.
    """

    def __init__(self):
        self.doctor = native_doctor
        self.executor = native_executor
        self.normalizer = native_normalizer

    def execute_channel_query(
        self,
        platform: str,
        query: str,
        limit: int = 5,
        query_id: str = "",
        query_class: str = "",
        query_text: str = "",
        domain: str = "general",
        **kwargs
    ) -> Tuple[List[EvidenceFragment], Dict[str, Any]]:
        """
        Execute a search or retrieval query for a specific platform using its active backend.

        Args:
            platform: Channel identifier (e.g. 'github', 'youtube', 'v2ex', 'bilibili', 'rss', 'news', 'web')
            query: The search term or target specification
            limit: Maximum items to return
            query_id: Traceable query identifier
            query_class: Semantic classification (e.g. 'official', 'refuting', 'forensic')
            query_text: Raw query text for provenance
            domain: Investigation domain ('financial', 'brand', 'fact_check', etc.)

        Returns:
            Tuple of (fragments: List[EvidenceFragment], telemetry: Dict[str, Any])
        """
        q_text = query_text or query
        cap = get_capability(platform)
        status_info = self.doctor.get_channel_status(platform)
        active_backend = status_info.get("active_backend") or (cap.backends[0] if cap.backends else "default")

        telemetry: Dict[str, Any] = {
            "platform": platform,
            "backend": active_backend,
            "operation": f"{platform}.search",
            "status": "INITIATED",
            "fallback_used": False,
            "fallback_backend": None,
            "attempts": 1,
            "latency_ms": 0,
            "error": None,
        }

        t0 = time.perf_counter()
        fragments: List[EvidenceFragment] = []

        try:
            # ── 1. GitHub (Primary: gh CLI) ──
            if platform == "github":
                try:
                    res = self.executor.execute_github_search(query, limit=limit)
                    fragments = self.normalizer.normalize_github_repos(
                        res.get("items", []), query_id=query_id, query_class=query_class, query_text=q_text
                    )
                    if fragments:
                        telemetry["status"] = "SUCCESS"
                    else:
                        raise NativeReachError("Native gh CLI returned no items, trying REST fallback")
                except Exception as e_gh:
                    logger.debug(f"[NativeRouter] GitHub native path notice: {e_gh}. Trying REST fallback.")
                    fragments = self._fallback_github_rest(query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "GitHub REST API"
                    telemetry["status"] = "SUCCESS" if fragments else "DEGRADED"

            # ── 2. YouTube (Primary: yt-dlp) ──
            elif platform == "youtube":
                try:
                    res = self.executor.execute_youtube_search(query, limit=limit)
                    fragments = self.normalizer.normalize_youtube_search(
                        res.get("items", []), query_id=query_id, query_class=query_class, query_text=q_text
                    )
                    if fragments:
                        telemetry["status"] = "SUCCESS"
                    else:
                        raise NativeReachError("Native yt-dlp returned no items, trying legacy fallback")
                except Exception as e_yt:
                    logger.debug(f"[NativeRouter] YouTube native path notice: {e_yt}. Trying legacy fallback.")
                    fragments = self._fallback_youtube_scraper(query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "Legacy YouTube Scraper"
                    telemetry["status"] = "SUCCESS" if fragments else "DEGRADED"

            # ── 3. V2EX (Native Public REST API — Zero Config) ──
            elif platform == "v2ex":
                res = self.executor.execute_v2ex_hot()
                raw_items = res.get("items", [])
                if query and query.strip():
                    q_low = query.lower()
                    filtered = [
                        t for t in raw_items
                        if q_low in t.get("title", "").lower() or q_low in (t.get("content") or "").lower()
                    ]
                    raw_items = filtered or raw_items[:limit]
                fragments = self.normalizer.normalize_v2ex_topics(
                    raw_items[:limit], query_id=query_id, query_class=query_class, query_text=q_text
                )
                telemetry["status"] = "SUCCESS"

            # ── 4. Bilibili (Native Public Search API — Zero Config) ──
            elif platform == "bilibili":
                res = self.executor.execute_bilibili_search(query, limit=limit)
                fragments = self.normalizer.normalize_bilibili_videos(
                    res.get("items", []), query_id=query_id, query_class=query_class, query_text=q_text
                )
                telemetry["status"] = "SUCCESS"

            # ── 5. RSS / PR Wires (Native feedparser) ──
            elif platform == "rss":
                wire_terms = ["press release", "filing", "statement", "announcement", "regulatory", "wire"]
                if not any(wt in query.lower() for wt in wire_terms):
                    wire_query = f"{query} (press release OR official statement OR filing OR wire)"
                else:
                    wire_query = query

                try:
                    feed_query = urllib.parse.quote_plus(wire_query.strip())
                    rss_url = f"https://news.google.com/rss/search?q={feed_query}&hl=en-US&gl=US&ceid=US:en"
                    res = self.executor.execute_rss_read(rss_url, limit=limit)
                    fragments = self.normalizer.normalize_rss_entries(
                        res.get("items", []), channel_name=platform, query_id=query_id, query_class=query_class, query_text=wire_query
                    )
                    if fragments:
                        telemetry["status"] = "SUCCESS"
                    else:
                        raise NativeReachError("Native RSS returned no entries, trying legacy fallback")
                except Exception as e_rss:
                    logger.debug(f"[NativeRouter] RSS native path notice: {e_rss}. Trying legacy fallback.")
                    fragments = self._fallback_news_scraper(wire_query, limit=limit, channel_name="rss", query_id=query_id, query_class=query_class, query_text=wire_query)
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "Legacy News Scraper"
                    telemetry["status"] = "SUCCESS" if fragments else "DEGRADED"

            # ── 6. News Channel (Native Google News RSS via feedparser) ──
            elif platform == "news":
                try:
                    feed_query = urllib.parse.quote_plus(query.strip())
                    rss_url = f"https://news.google.com/rss/search?q={feed_query}&hl=en-US&gl=US&ceid=US:en"
                    res = self.executor.execute_rss_read(rss_url, limit=limit)
                    fragments = self.normalizer.normalize_rss_entries(
                        res.get("items", []), channel_name="news", query_id=query_id, query_class=query_class, query_text=q_text
                    )
                    if fragments:
                        telemetry["status"] = "SUCCESS"
                    else:
                        raise NativeReachError("News RSS returned no entries, trying legacy fallback")
                except Exception as e_news:
                    logger.debug(f"[NativeRouter] News native path notice: {e_news}. Trying legacy fallback.")
                    fragments = self._fallback_news_scraper(query, limit=limit, channel_name="news", query_id=query_id, query_class=query_class, query_text=q_text)
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "Legacy News Scraper"
                    telemetry["status"] = "SUCCESS" if fragments else "DEGRADED"

            # ── 7. Web Channel (Direct Bing Search with redirect unpacking) ──
            elif platform == "web":
                try:
                    fragments = self._execute_web_search(query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                    if fragments:
                        telemetry["status"] = "SUCCESS"
                    else:
                        raise NativeReachError("Web search returned no items, trying legacy fallback")
                except Exception as e_web:
                    logger.debug(f"[NativeRouter] Web search notice: {e_web}. Trying legacy fallback.")
                    fragments = self._fallback_web_scraper(query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "Legacy Web Scraper"
                    telemetry["status"] = "SUCCESS" if fragments else "DEGRADED"

            # ── 8. Jina Reader Channel (Direct URL Fetch) ──
            elif platform == "jina_reader":
                target_url = kwargs.get("url") or query
                read_res = self.execute_channel_read(target_url, max_chars=kwargs.get("max_chars", 4000))
                if read_res.get("status") == "success":
                    content = read_res.get("markdown", "") or read_res.get("content", "")
                    frag = EvidenceFragment(
                        platform="Web",
                        title=read_res.get("title") or f"Article from {urllib.parse.urlparse(target_url).netloc}",
                        content=content,
                        url=target_url,
                        author=urllib.parse.urlparse(target_url).netloc or "Web",
                        published="Recent",
                        snippet=content[:300],
                        score=85.0,
                        retrieval_method="jina_reader",
                        channel_name="jina_reader",
                        content_depth="FULL_ARTICLE" if len(content) > 500 else "SNIPPET",
                        query_id=query_id,
                        query_class=query_class,
                        query_text=q_text,
                        raw_metadata={
                            "backend": read_res.get("backend", "Jina Reader"),
                            "char_count": len(content),
                        }
                    )
                    fragments = [frag]
                    telemetry["status"] = "SUCCESS"
                else:
                    telemetry["status"] = "FAILED"
                    telemetry["error"] = read_res.get("error", "Failed to read content")

            # ── 9. Authenticated Social Channels (Reddit, Twitter, etc.) ──
            elif platform in ("reddit", "twitter"):
                env_var = f"{platform.upper()}_COOKIE"
                try:
                    self.executor.guard_authenticated_channel(
                        platform=platform,
                        backend=active_backend,
                        env_var=env_var
                    )
                    telemetry["status"] = "SUCCESS"
                except AuthRequiredError as auth_err:
                    # Provide an honest authenticated fallback via web indexing if allowed
                    logger.info(f"[NativeRouter] Platform '{platform}' requires login ({auth_err.message}); falling back to Google RSS web syndication index")
                    site_query = f"site:{platform}.com {query}"
                    feed_query = urllib.parse.quote_plus(site_query.strip())
                    rss_url = f"https://news.google.com/rss/search?q={feed_query}&hl=en-US&gl=US&ceid=US:en"
                    try:
                        res = self.executor.execute_rss_read(rss_url, limit=limit)
                        fragments = self.normalizer.normalize_rss_entries(
                            res.get("items", []), channel_name=platform, query_id=query_id, query_class=query_class, query_text=q_text
                        )
                        for f in fragments:
                            f.platform = platform.capitalize()
                            f.retrieval_method = f"{platform}_web_index"
                        telemetry["status"] = "SUCCESS" if fragments else "AUTH_REQUIRED"
                        telemetry["fallback_used"] = True
                        telemetry["fallback_backend"] = "Google RSS (Unauthenticated Index)"
                    except Exception:
                        telemetry["status"] = "AUTH_REQUIRED"
                        telemetry["error"] = str(auth_err)

            # ── 10. Tier-1 Session Channels (LinkedIn, Xueqiu, RED, FB, IG, Boss) ──
            elif platform in ("linkedin", "xueqiu", "xiaohongshu", "instagram", "facebook", "boss"):
                env_var = "BOSS_CDP_PORT" if platform == "boss" else f"{platform.upper()}_COOKIE"
                try:
                    self.executor.guard_authenticated_channel(
                        platform=platform,
                        backend=active_backend,
                        env_var=env_var
                    )
                    telemetry["status"] = "SUCCESS"
                except AuthRequiredError as auth_err:
                    telemetry["status"] = "AUTH_REQUIRED"
                    telemetry["error"] = str(auth_err)
                    logger.debug(f"[NativeRouter] Channel '{platform}' requires authentication: {auth_err.message}")

            # ── 11. Generic Platform Dispatch ──
            else:
                fragments = self._execute_web_search(query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                telemetry["status"] = "SUCCESS" if fragments else "DEGRADED"

        except AuthRequiredError as auth_err:
            telemetry["status"] = "AUTH_REQUIRED"
            telemetry["error"] = str(auth_err)
        except Exception as e:
            logger.warning(f"[NativeRouter] Query execution failed for '{platform}': {e}")
            telemetry["status"] = "FAILED"
            telemetry["error"] = str(e)

        telemetry["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        return fragments, telemetry

    def execute_channel_read(self, url: str, max_chars: int = 4000, **kwargs) -> Dict[str, Any]:
        """
        Safely fetch and extract document content into clean markdown.
        Enforces SSRF defense before network transmission.
        Primary: native Jina Reader HTTP executor.
        Fallback: Trafilatura / legacy reader scraper.
        """
        if not url:
            return {"status": "error", "error": "Empty URL provided", "url": ""}

        safe, reason = is_safe_url(url)
        if not safe:
            logger.warning(f"[NativeRouter] SSRF defense blocked URL: {url} ({reason})")
            return {
                "status": "blocked_ssrf",
                "error": f"URL blocked by SSRF defense: {reason}",
                "url": url,
            }

        # 1. Primary: Native Jina Reader
        try:
            res = self.executor.execute_web_read(url)
            content = res.get("content", "")
            if content and len(content.strip()) > 50:
                netloc = urllib.parse.urlparse(url).netloc
                return {
                    "status": "success",
                    "title": f"Article from {netloc}",
                    "content": content[:max_chars],
                    "markdown": content[:max_chars],
                    "url": url,
                    "char_count": len(content),
                    "backend": "Jina Reader",
                    "fallback_used": False,
                }
        except Exception as e_jina:
            logger.debug(f"[NativeRouter] Native Jina read notice: {e_jina}. Trying fallback scraper.")

        # 2. Fallback: Legacy reach scraper
        try:
            scraper = _get_legacy_scraper()
            res = scraper.read_article_markdown(url, max_chars=max_chars)
            content = res.get("content", "") or res.get("markdown", "")
            if content:
                return {
                    "status": "success",
                    "title": res.get("title") or f"Article from {urllib.parse.urlparse(url).netloc}",
                    "content": content[:max_chars],
                    "markdown": content[:max_chars],
                    "url": url,
                    "char_count": len(content),
                    "backend": "Legacy Reach Scraper",
                    "fallback_used": True,
                    "fallback_backend": "Legacy Reach Scraper",
                }
        except Exception as e_sc:
            logger.warning(f"[NativeRouter] Fallback read failed for {url}: {e_sc}")

        return {"status": "error", "error": "Failed to read content", "url": url}

    # ── Internal Helper Methods ─────────────────────────────────────────────

    def _execute_web_search(self, query: str, limit: int = 6, query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Execute open-web search using Bing with redirect resolution."""
        import requests
        from bs4 import BeautifulSoup

        clean_q = query.strip()
        fragments: List[EvidenceFragment] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

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
                    content=snippet,
                    url=dest_url,
                    author=urllib.parse.urlparse(dest_url).netloc or "Web",
                    published="Recent",
                    snippet=snippet[:300],
                    score=75.0,
                    retrieval_method="bing_search",
                    channel_name="web",
                    query_id=query_id,
                    query_class=query_class,
                    query_text=query_text or query,
                    raw_metadata={
                        "backend": "Bing Search",
                        "raw_url": raw_href,
                    }
                ))
        return fragments

    def _fallback_github_rest(self, query: str, limit: int = 5, query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Fallback: GitHub REST API."""
        import requests
        clean_q = query.strip()
        encoded_q = urllib.parse.quote_plus(clean_q)
        url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page={limit}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AegisProtocol-AgentReach/3.0"
        }
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
                    channel_name="github",
                    query_id=query_id,
                    query_class=query_class,
                    query_text=query_text or query,
                    raw_metadata={
                        "backend": "GitHub REST (fallback)",
                        "stars": stars,
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language"),
                    }
                ))
            return fragments
        return []

    def _fallback_youtube_scraper(self, query: str, limit: int = 6, query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Fallback: Legacy YouTube scraper."""
        scraper = _get_legacy_scraper()
        raw_items = scraper.search_youtube(query, limit=limit)
        return [
            EvidenceFragment.from_scraper_dict(
                item,
                channel_name="youtube",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text or query,
            )
            for item in raw_items
        ]

    def _fallback_news_scraper(self, query: str, limit: int = 6, channel_name: str = "news", query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Fallback: Legacy news scraper."""
        scraper = _get_legacy_scraper()
        raw_items = scraper.search_news(query, limit=limit)
        return [
            EvidenceFragment.from_scraper_dict(
                item,
                channel_name=channel_name,
                query_id=query_id,
                query_class=query_class,
                query_text=query_text or query,
            )
            for item in raw_items
        ]

    def _fallback_web_scraper(self, query: str, limit: int = 6, query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Fallback: Legacy web scraper."""
        scraper = _get_legacy_scraper()
        raw_items = scraper.search_web(query, limit=limit)
        return [
            EvidenceFragment.from_scraper_dict(
                item,
                channel_name="web",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text or query,
            )
            for item in raw_items
        ]


# Global singleton instance
native_router = NativeRouter()
