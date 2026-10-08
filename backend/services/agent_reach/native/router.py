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
import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from backend.services.agent_reach.channels import (
    CandidateSource,
    ChannelStatus,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.agent_reach.native.adapters import (
    AdapterRegistry,
    adapter_registry,
    GitHubAdapter,
    RedditAdapter,
    SearchDiscoveryAdapter,
    TwitterAdapter,
    WebAdapter,
    YouTubeAdapter,
)
from backend.services.agent_reach.native.cache import social_cache
from backend.services.agent_reach.native.channel_capabilities import get_capability
from backend.services.agent_reach.native.doctor import native_doctor
from backend.services.agent_reach.native.errors import AuthRequiredError, NativeReachError
from backend.services.agent_reach.native.executor import native_executor
from backend.services.agent_reach.native.normalizer import native_normalizer
from backend.services.agent_reach.native.evidence_sufficiency import (
    evidence_sufficiency_evaluator,
)
from backend.services.agent_reach.native.route_policy import (
    RouteDecision,
    RoutePolicyEngine,
)
from backend.services.agent_reach.native.source_discovery import (
    TWITTER_RESERVED_PATHS,
    SourceDiscoveryResult,
    check_entity_semantic_match,
    discover_sources_from_search,
    evaluate_content_relevance,
    extract_reddit_source,
    extract_x_source,
    generate_discovery_queries,
    is_valid_content_source,
    resolve_bing_redirect,
)
from backend.services.agent_reach.native.telemetry import (
    AcquisitionTelemetryRecord,
    acquisition_telemetry,
)
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
        self._social_cache: Dict[str, Tuple[float, Any]] = {}
        self._social_cache_ttl = float(os.getenv("AEGIS_SOCIAL_CACHE_TTL", "600.0"))

        # Experimental feature flags (safe zero-auth defaults)
        self.use_arctic_shift = os.getenv("AEGIS_REDDIT_ARCTIC_SHIFT", "true").lower() in ("true", "1", "yes")
        self.use_fxtwitter = os.getenv("AEGIS_X_FXTWITTER", "true").lower() in ("true", "1", "yes")
        self.use_social_url_discovery = os.getenv("AEGIS_SOCIAL_URL_DISCOVERY", "true").lower() in ("true", "1", "yes")

        # Authoritative adapter registry for shared acquisition fabric
        self.adapter_registry = adapter_registry
        self.web_adapter = adapter_registry.web_adapter
        self.reddit_adapter = adapter_registry.reddit_adapter
        self.twitter_adapter = adapter_registry.twitter_adapter
        self.youtube_adapter = adapter_registry.youtube_adapter
        self.github_adapter = adapter_registry.github_adapter
        self.search_adapter = adapter_registry.search_adapter

    def _get_social_cache(self, key: str) -> Optional[Any]:
        """Fetch unexpired item from in-memory cache."""
        if key in self._social_cache:
            ts, val = self._social_cache[key]
            if time.time() - ts < self._social_cache_ttl:
                return val
            del self._social_cache[key]
        return None

    def _set_social_cache(self, key: str, val: Any) -> None:
        """Store item in in-memory cache with current timestamp."""
        if val is not None:
            self._social_cache[key] = (time.time(), val)

    def _fetch_arctic_shift_posts_batch(
        self,
        post_ids: List[str],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """
        Batch Reddit submissions lookup via Arctic Shift REST API.
        Deduplicates post IDs, checks cache, and batches requests in chunks of up to 25.
        Applies exponential backoff on retryable 422/429/503 responses.
        """
        if not self.use_arctic_shift or not post_ids:
            return []

        clean_ids = list(dict.fromkeys([
            pid.replace("t3_", "").strip()
            for pid in post_ids
            if pid and pid.replace("t3_", "").strip()
        ]))
        
        results: List[EvidenceFragment] = []
        to_fetch: List[str] = []

        for pid in clean_ids:
            cached = self._get_social_cache(f"reddit:post:{pid}")
            if cached:
                results.append(cached)
            else:
                to_fetch.append(pid)

        if not to_fetch:
            return results

        chunk_size = 25
        for i in range(0, len(to_fetch), chunk_size):
            chunk = to_fetch[i : i + chunk_size]
            url = f"https://arctic-shift.photon-reddit.com/api/posts/ids?ids={','.join(chunk)}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
                    "Accept": "application/json"
                }
            )
            data = None
            for attempt in range(2):
                try:
                    with urllib.request.urlopen(req, timeout=8.0) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        break
                except urllib.error.HTTPError as e:
                    if e.code in (422, 429, 503) and attempt == 0:
                        time.sleep(0.8)
                        continue
                    logger.debug(f"[NativeRouter] Arctic Shift batch lookup HTTP {e.code}: {e}")
                    break
                except Exception as e:
                    logger.debug(f"[NativeRouter] Arctic Shift batch lookup error: {e}")
                    break

            if data:
                posts = data.get("data", [])
                if posts:
                    frags = self.normalizer.normalize_arctic_shift_posts(
                        posts, query_id=query_id, query_class=query_class, query_text=query_text
                    )
                    for f in frags:
                        pid = f.raw_metadata.get("post_id") or ""
                        if pid:
                            self._set_social_cache(f"reddit:post:{pid}", f)
                    results.extend(frags)

        return results

    def _fetch_arctic_shift_post(self, post_id: str) -> Optional[EvidenceFragment]:
        """Direct Reddit submission lookup via Arctic Shift REST API."""
        if not self.use_arctic_shift:
            return None
        frags = self._fetch_arctic_shift_posts_batch([post_id])
        return frags[0] if frags else None

    def _fetch_arctic_shift_search(
        self,
        query: str = "",
        subreddit: str = "",
        author: str = "",
        limit: int = 5,
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Search Reddit submissions via Arctic Shift REST API."""
        cache_key = f"reddit:search:{subreddit}:{author}:{query}:{limit}"
        cached = self._get_social_cache(cache_key)
        if cached:
            return cached

        params = {"limit": str(min(limit, 25)), "sort": "desc"}
        if subreddit:
            params["subreddit"] = subreddit
        if author:
            params["author"] = author
        if query:
            params["query"] = query

        url = f"https://arctic-shift.photon-reddit.com/api/posts/search?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=7.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                posts = data.get("data", [])
                frags = self.normalizer.normalize_arctic_shift_posts(
                    posts, query_id=query_id, query_class=query_class, query_text=query_text or query
                )
                if frags:
                    self._set_social_cache(cache_key, frags)
                    return frags
        except Exception as e:
            logger.debug(f"[NativeRouter] Arctic Shift search failed for params {params}: {e}")
        return []

    def _fetch_arctic_shift_comments(
        self,
        post_id: str,
        limit: int = 10,
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Fetch comments for a known Reddit submission via Arctic Shift REST API."""
        clean_pid = post_id.replace("t3_", "").strip()
        link_id = f"t3_{clean_pid}"
        cache_key = f"reddit:comments:{clean_pid}:{limit}"
        cached = self._get_social_cache(cache_key)
        if cached:
            return cached

        url = f"https://arctic-shift.photon-reddit.com/api/comments/search?link_id={link_id}&limit={min(limit, 50)}&sort=desc"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=7.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                comments = data.get("data", [])
                frags = self.normalizer.normalize_arctic_shift_comments(
                    comments, query_id=query_id, query_class=query_class, query_text=query_text
                )
                if frags:
                    self._set_social_cache(cache_key, frags)
                    return frags
        except Exception as e:
            logger.debug(f"[NativeRouter] Arctic Shift comments fetch failed for {clean_pid}: {e}")
        return []

    def _fetch_fxtwitter_status(self, user: str, status_id: str) -> Optional[EvidenceFragment]:
        """Fetch public tweet status via FxTwitter API with retry on 429/503."""
        if not self.use_fxtwitter:
            return None
        clean_sid = status_id.strip()
        cache_key = f"twitter:status:{clean_sid}"
        cached = self._get_social_cache(cache_key)
        if cached:
            return cached

        handle = user if (user and user not in ("i", "status")) else "status"
        if handle == "status":
            url = f"https://api.fxtwitter.com/status/{clean_sid}"
        else:
            url = f"https://api.fxtwitter.com/{handle}/status/{clean_sid}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
                "Accept": "application/json"
            }
        )
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=6.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("code") == 200 and data.get("tweet"):
                        frag = self.normalizer.normalize_fxtwitter_tweet(data["tweet"])
                        if frag:
                            self._set_social_cache(cache_key, frag)
                            return frag
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 503) and attempt == 0:
                    time.sleep(0.5)
                    continue
                logger.debug(f"[NativeRouter] FxTwitter status fetch failed for {user}/{status_id}: {e}")
                break
            except Exception as e:
                logger.debug(f"[NativeRouter] FxTwitter status fetch error: {e}")
                break
        return None

    def _fetch_fxtwitter_profile(self, user: str) -> Optional[EvidenceFragment]:
        """Fetch public user profile via FxTwitter API."""
        if not self.use_fxtwitter:
            return None
        clean_user = user.replace("@", "").strip()
        cache_key = f"twitter:profile:{clean_user.lower()}"
        cached = self._get_social_cache(cache_key)
        if cached:
            return cached

        url = f"https://api.fxtwitter.com/{clean_user}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
                "Accept": "application/json"
            }
        )
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=6.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("code") == 200 and data.get("user"):
                        frag = self.normalizer.normalize_fxtwitter_profile(data["user"])
                        if frag:
                            self._set_social_cache(cache_key, frag)
                            return frag
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 503) and attempt == 0:
                    time.sleep(0.5)
                    continue
                logger.debug(f"[NativeRouter] FxTwitter profile fetch failed for {clean_user}: {e}")
                break
            except Exception as e:
                logger.debug(f"[NativeRouter] FxTwitter profile fetch error: {e}")
                break
        return None

    @staticmethod
    def _tag_fragments(
        frags: List[EvidenceFragment],
        requested_channel: str,
        actual_channel: str,
        mode: str,
        backend_id: str,
        fallback_reason: Optional[str] = None,
        is_authenticated: bool = False,
    ) -> List[EvidenceFragment]:
        for f in frags:
            f.requested_channel = requested_channel
            f.actual_retrieval_channel = actual_channel
            if not f.channel_name:
                f.channel_name = actual_channel
            f.retrieval_mode = mode
            f.native_backend_id = backend_id
            f.fallback_reason = fallback_reason
            f.is_authenticated = is_authenticated
            f.retrieval_lineage = [{
                "channel": actual_channel,
                "requested_channel": requested_channel,
                "query_id": getattr(f, "query_id", ""),
                "retrieval_mode": mode,
                "backend_id": backend_id,
                "fallback_reason": fallback_reason,
                "is_authenticated": is_authenticated,
                "retrieved_at": getattr(f, "retrieved_at", ""),
            }]
        return frags

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
                        self._tag_fragments(fragments, "github", "github", RetrievalMode.DIRECT_API.value, "gh-cli", None, True)
                        telemetry["status"] = "SUCCESS"
                    else:
                        raise NativeReachError("Native gh CLI returned no items, trying REST fallback")
                except Exception as e_gh:
                    logger.debug(f"[NativeRouter] GitHub native path notice: {e_gh}. Trying REST fallback.")
                    fragments = self._fallback_github_rest(query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                    self._tag_fragments(fragments, "github", "github", RetrievalMode.DIRECT_API.value, "GitHub REST API", "GH_CLI_UNAVAILABLE", False)
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "GitHub REST API"
                    telemetry["fallback_reason"] = "GH_CLI_UNAVAILABLE"
                    telemetry["retrieval_mode"] = RetrievalMode.DIRECT_API.value
                    telemetry["status"] = "SUCCESS" if fragments else "DEGRADED"

            # ── 2. YouTube (Primary: yt-dlp) ──
            elif platform == "youtube":
                try:
                    res = self.executor.execute_youtube_search(query, limit=limit)
                    fragments = self.normalizer.normalize_youtube_search(
                        res.get("items", []), query_id=query_id, query_class=query_class, query_text=q_text
                    )
                    if fragments:
                        self._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.DIRECT_API.value, "yt-dlp", None, False)
                        telemetry["status"] = "SUCCESS"
                    else:
                        raise NativeReachError("Native yt-dlp returned no items, trying legacy fallback")
                except Exception as e_yt:
                    logger.debug(f"[NativeRouter] YouTube native path notice: {e_yt}. Trying legacy fallback.")
                    fragments = self._fallback_youtube_scraper(query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                    self._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, "Legacy YouTube Scraper", "YT_DLP_UNAVAILABLE", False)
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "Legacy YouTube Scraper"
                    telemetry["fallback_reason"] = "YT_DLP_UNAVAILABLE"
                    telemetry["retrieval_mode"] = RetrievalMode.LEGACY_SCRAPER_FALLBACK.value
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
                self._tag_fragments(fragments, "v2ex", "v2ex", RetrievalMode.DIRECT_API.value, "v2ex-public-api", None, False)
                telemetry["status"] = "SUCCESS"

            # ── 4. Bilibili (Native Public Search API — Zero Config) ──
            elif platform == "bilibili":
                res = self.executor.execute_bilibili_search(query, limit=limit)
                fragments = self.normalizer.normalize_bilibili_videos(
                    res.get("items", []), query_id=query_id, query_class=query_class, query_text=q_text
                )
                self._tag_fragments(fragments, "bilibili", "bilibili", RetrievalMode.DIRECT_API.value, "bilibili-public-api", None, False)
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
                        self._tag_fragments(fragments, "rss", "rss", RetrievalMode.DIRECT_API.value, "feedparser-google-rss", None, False)
                        telemetry["status"] = "SUCCESS"
                    else:
                        raise NativeReachError("Native RSS returned no entries, trying legacy fallback")
                except Exception as e_rss:
                    logger.debug(f"[NativeRouter] RSS native path notice: {e_rss}. Trying legacy fallback.")
                    fragments = self._fallback_news_scraper(wire_query, limit=limit, channel_name="rss", query_id=query_id, query_class=query_class, query_text=wire_query)
                    self._tag_fragments(fragments, "rss", "rss", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, "Legacy News Scraper", "RSS_UNAVAILABLE", False)
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "Legacy News Scraper"
                    telemetry["fallback_reason"] = "RSS_UNAVAILABLE"
                    telemetry["retrieval_mode"] = RetrievalMode.LEGACY_SCRAPER_FALLBACK.value
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
                        self._tag_fragments(fragments, "news", "news", RetrievalMode.DIRECT_API.value, "feedparser-google-news", None, False)
                        telemetry["status"] = "SUCCESS"
                    else:
                        raise NativeReachError("News RSS returned no entries, trying legacy fallback")
                except Exception as e_news:
                    logger.debug(f"[NativeRouter] News native path notice: {e_news}. Trying legacy fallback.")
                    fragments = self._fallback_news_scraper(query, limit=limit, channel_name="news", query_id=query_id, query_class=query_class, query_text=q_text)
                    self._tag_fragments(fragments, "news", "news", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, "Legacy News Scraper", "NEWS_FEED_UNAVAILABLE", False)
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "Legacy News Scraper"
                    telemetry["fallback_reason"] = "NEWS_FEED_UNAVAILABLE"
                    telemetry["retrieval_mode"] = RetrievalMode.LEGACY_SCRAPER_FALLBACK.value
                    telemetry["status"] = "SUCCESS" if fragments else "DEGRADED"

            # ── 7. Web Channel (Direct Bing Search with redirect unpacking) ──
            elif platform == "web":
                try:
                    fragments = self._execute_web_search(query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                    if fragments:
                        self._tag_fragments(fragments, "web", "web", RetrievalMode.DIRECT_API.value, "bing-search-rss", None, False)
                        telemetry["status"] = "SUCCESS"
                    else:
                        raise NativeReachError("Web search returned no items, trying legacy fallback")
                except Exception as e_web:
                    logger.debug(f"[NativeRouter] Web search notice: {e_web}. Trying legacy fallback.")
                    fragments = self._fallback_web_scraper(query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                    self._tag_fragments(fragments, "web", "web", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, "Legacy Web Scraper", "BING_SEARCH_UNAVAILABLE", False)
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "Legacy Web Scraper"
                    telemetry["fallback_reason"] = "BING_SEARCH_UNAVAILABLE"
                    telemetry["retrieval_mode"] = RetrievalMode.LEGACY_SCRAPER_FALLBACK.value
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
                        retrieval_mode=RetrievalMode.WEB_READER.value,
                        native_backend_id="jina-reader",
                        channel_name="jina_reader",
                        requested_channel="jina_reader",
                        actual_retrieval_channel="jina_reader",
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
                    self._tag_fragments(fragments, "jina_reader", "jina_reader", RetrievalMode.WEB_READER.value, "jina-reader", None, False)
                    telemetry["status"] = "SUCCESS"
                else:
                    telemetry["status"] = "FAILED"
                    telemetry["error"] = read_res.get("error", "Failed to read content")

            # ── 9. Reddit Channel (Zero-Auth Public Mirror: Arctic Shift) ──
            elif platform == "reddit":
                q_clean = query.strip()
                
                # BRANCH 1: Check if query contains an EXACT Reddit URL or redd.it link
                reddit_src = extract_reddit_source(q_clean, query=q_clean)
                if reddit_src and self.use_arctic_shift:
                    if reddit_src.source_type == "comment" and reddit_src.parent_id:
                        # Comment URL: fetch parent post + comments
                        post_frag = self._fetch_arctic_shift_post(reddit_src.parent_id)
                        comm_frags = self._fetch_arctic_shift_comments(
                            reddit_src.parent_id, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text
                        )
                        all_frags = ([post_frag] if post_frag else []) + comm_frags
                        if all_frags:
                            self._tag_fragments(
                                all_frags, "reddit", "reddit", RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, "arctic_shift", None, False
                            )
                            for f in all_frags:
                                f.raw_metadata["discovered_from"] = "direct_input"
                                f.raw_metadata["external_id"] = reddit_src.external_id
                                f.raw_metadata["content_completeness"] = "full_submission_plus_comments"
                            fragments = all_frags
                            telemetry["status"] = "SUCCESS"
                            telemetry["backend"] = "arctic_shift"
                            telemetry["retrieval_mode"] = RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
                            telemetry["authenticated"] = False
                    elif reddit_src.source_type == "post" and reddit_src.external_id:
                        post_frag = self._fetch_arctic_shift_post(reddit_src.external_id)
                        if post_frag:
                            comm_frags = self._fetch_arctic_shift_comments(
                                reddit_src.external_id, limit=3, query_id=query_id, query_class=query_class, query_text=q_text
                            )
                            post_frag.raw_metadata["discovered_from"] = "direct_input"
                            post_frag.raw_metadata["external_id"] = reddit_src.external_id
                            post_frag.raw_metadata["content_completeness"] = "full_submission_plus_comments" if comm_frags else "full_submission"
                            fragments = [post_frag] + comm_frags
                            self._tag_fragments(
                                fragments, "reddit", "reddit", RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, "arctic_shift", None, False
                            )
                            telemetry["status"] = "SUCCESS"
                            telemetry["backend"] = "arctic_shift"
                            telemetry["retrieval_mode"] = RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
                            telemetry["authenticated"] = False
                    elif reddit_src.source_type == "subreddit" and reddit_src.subreddit:
                        fragments = self._fetch_arctic_shift_search(
                            query="", subreddit=reddit_src.subreddit, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text
                        )
                        if fragments:
                            self._tag_fragments(
                                fragments, "reddit", "reddit", RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, "arctic_shift", None, False
                            )
                            for f in fragments:
                                f.raw_metadata["discovered_from"] = "direct_input"
                                f.raw_metadata["content_completeness"] = "subreddit_feed"
                            telemetry["status"] = "SUCCESS"
                            telemetry["backend"] = "arctic_shift"
                            telemetry["retrieval_mode"] = RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
                            telemetry["authenticated"] = False

                # BRANCH 2: Comments requested by ID (e.g. "comments:z1c9z")
                if not fragments and self.use_arctic_shift:
                    post_comment_match = re.search(r"(?:comments(?:\s+for\s+|\s+in\s+|:\s*)|^post\s+)([a-z0-9]+)", q_clean, re.IGNORECASE)
                    if post_comment_match:
                        target_pid = post_comment_match.group(1)
                        is_explicit_post = q_clean.lower().startswith("post ")
                        if is_explicit_post:
                            post_frag = self._fetch_arctic_shift_post(target_pid)
                            comm_frags = self._fetch_arctic_shift_comments(
                                target_pid, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text
                            )
                            fragments = ([post_frag] if post_frag else []) + comm_frags
                        else:
                            fragments = self._fetch_arctic_shift_comments(
                                target_pid, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text
                            )
                        if fragments:
                            self._tag_fragments(
                                fragments, "reddit", "reddit", RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, "arctic_shift", None, False
                            )
                            for f in fragments:
                                f.raw_metadata["discovered_from"] = "direct_input"
                                f.raw_metadata["external_id"] = target_pid
                                f.raw_metadata["content_completeness"] = "comments" if not is_explicit_post else "full_submission_plus_comments"
                            telemetry["status"] = "SUCCESS"
                            telemetry["backend"] = "arctic_shift"
                            telemetry["retrieval_mode"] = RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
                            telemetry["authenticated"] = False

                # BRANCH 3: Subreddit query (e.g. "r/technology" or "r/science")
                if not fragments and self.use_arctic_shift:
                    sub_match = re.match(r"^r/([a-zA-Z0-9_]+)$", q_clean)
                    if sub_match:
                        sub_name = sub_match.group(1)
                        fragments = self._fetch_arctic_shift_search(
                            query="", subreddit=sub_name, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text
                        )
                        if fragments:
                            self._tag_fragments(
                                fragments, "reddit", "reddit", RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, "arctic_shift", None, False
                            )
                            for f in fragments:
                                f.raw_metadata["discovered_from"] = "direct_input"
                                f.raw_metadata["content_completeness"] = "subreddit_feed"
                            telemetry["status"] = "SUCCESS"
                            telemetry["backend"] = "arctic_shift"
                            telemetry["retrieval_mode"] = RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
                            telemetry["authenticated"] = False

                # BRANCH 4: UNANCHORED REDDIT QUERY (MULTI-QUERY SEARCH DISCOVERY -> ARCTIC SHIFT MIRROR)
                if not fragments and self.use_arctic_shift and self.use_social_url_discovery:
                    target_ent = kwargs.get("entity") or ""
                    target_top = kwargs.get("topic") or ""
                    target_clm = kwargs.get("claim") or ""
                    task_t = kwargs.get("task_type") or "SEARCH"

                    discovery_queries = generate_discovery_queries("reddit", q_clean, entity=target_ent, task_type=task_t)
                    candidate_urls_all: List[str] = []
                    discovered_posts: List[SourceDiscoveryResult] = []
                    queries_attempted_count = 0

                    for dq in discovery_queries:
                        queries_attempted_count += 1
                        try:
                            search_frags = self._execute_web_search(
                                dq, limit=8, query_id=query_id, query_class=query_class, query_text=q_text
                            )
                        except (StopIteration, Exception):
                            search_frags = []
                        if search_frags:
                            for sf in search_frags:
                                if sf.url not in candidate_urls_all:
                                    candidate_urls_all.append(sf.url)
                            cands = discover_sources_from_search(
                                search_frags, platform="reddit", query=dq,
                                target_entity=target_ent, target_topic=target_top, target_claim=target_clm,
                                task_type=task_t, max_candidates=5
                            )
                            for c in cands:
                                if c.source_type in ("post", "comment") and c.external_id:
                                    if not any(x.external_id == c.external_id for x in discovered_posts):
                                        discovered_posts.append(c)
                        if len(discovered_posts) >= 2:
                            break

                    telemetry["discovery_attempted"] = True
                    telemetry["discovery_engine"] = "bing_search"
                    telemetry["queries_attempted"] = queries_attempted_count
                    telemetry["candidate_urls_count"] = len(candidate_urls_all)
                    telemetry["social_candidate_count"] = len(discovered_posts)
                    telemetry["reddit_url_count"] = len(discovered_posts)

                    cand_pids = [c.external_id for c in discovered_posts if c.source_type == "post" and c.external_id]
                    if cand_pids:
                        telemetry["selected_source_url"] = discovered_posts[0].canonical_url
                        telemetry["selected_external_id"] = cand_pids[0]
                        telemetry["mirror_attempted"] = True
                        telemetry["mirror_provider"] = "arctic_shift"

                        mirror_frags = self._fetch_arctic_shift_posts_batch(
                            cand_pids, query_id=query_id, query_class=query_class, query_text=q_text
                        )
                        if mirror_frags:
                            top_pid = mirror_frags[0].raw_metadata.get("post_id") or cand_pids[0]
                            comms = self._fetch_arctic_shift_comments(
                                top_pid, limit=3, query_id=query_id, query_class=query_class, query_text=q_text
                            )
                            fragments = mirror_frags + comms
                            self._tag_fragments(
                                fragments, "reddit", "reddit", RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, "arctic_shift", None, False
                            )
                            for f in fragments:
                                f.raw_metadata["discovered_from"] = "search_url_discovery"
                                f.raw_metadata["content_completeness"] = "full_submission_plus_comments" if comms else "full_submission"
                            telemetry["status"] = "SUCCESS"
                            telemetry["backend"] = "arctic_shift"
                            telemetry["retrieval_mode"] = RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
                            telemetry["authenticated"] = False
                            telemetry["discovered_from"] = "search_url_discovery"
                            telemetry["mirror_result"] = "SUCCESS"
                        else:
                            telemetry["mirror_result"] = "FALLBACK"
                    else:
                        telemetry["mirror_attempted"] = False
                        telemetry["mirror_result"] = "NO_VALID_URLS"

                # BRANCH 5: FALLBACK (Only after mirror retrieval fails or no valid source ID discovered)
                if not fragments:
                    logger.debug(f"[NativeRouter] Arctic Shift yielded no results for '{query}'. Trying search index fallback.")
                    site_query = f"site:reddit.com {query}"
                    fragments = self._execute_web_search(
                        site_query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text
                    )
                    if fragments:
                        self._tag_fragments(
                            fragments,
                            requested_channel="reddit",
                            actual_channel="web_search",
                            mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                            backend_id="bing-search-index",
                            fallback_reason="ARCTIC_SHIFT_UNAVAILABLE",
                            is_authenticated=False
                        )
                        for f in fragments:
                            f.platform = "Reddit (Web Index Fallback)"
                            f.retrieval_method = "reddit_web_index"
                            f.raw_metadata["source_tier"] = "TIER_3_AGGREGATE"
                            f.raw_metadata["honest_disclosure"] = "Direct Reddit mirror returned no items; retrieved via public search index"
                        telemetry["status"] = "SUCCESS"
                        telemetry["fallback_used"] = True
                        telemetry["fallback_backend"] = "Bing Search Index"
                        telemetry["fallback_reason"] = "ARCTIC_SHIFT_UNAVAILABLE"
                        telemetry["retrieval_mode"] = RetrievalMode.WEB_SEARCH_INDEX.value
                    else:
                        telemetry["status"] = "DEGRADED"
                        telemetry["fallback_used"] = True
                        telemetry["fallback_backend"] = "Bing Search Index"
                        telemetry["fallback_reason"] = "ARCTIC_SHIFT_UNAVAILABLE"

            # ── 10. Twitter / X Channel (Zero-Auth Public Mirror: FxTwitter) ──
            elif platform in ("twitter", "x"):
                q_clean = query.strip()
                
                # BRANCH 1: EXACT STATUS URL or ID
                x_src = extract_x_source(q_clean, query=q_clean)
                if x_src and self.use_fxtwitter:
                    if x_src.source_type == "status" and x_src.external_id:
                        frag = self._fetch_fxtwitter_status(x_src.handle or "status", x_src.external_id)
                        if frag:
                            frag.raw_metadata["discovered_from"] = "direct_input"
                            frag.raw_metadata["external_id"] = x_src.external_id
                            frag.raw_metadata["content_completeness"] = "full_status"
                            fragments = [frag]
                            self._tag_fragments(
                                fragments, "twitter", "twitter", RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, "fxtwitter", None, False
                            )
                            telemetry["status"] = "SUCCESS"
                            telemetry["backend"] = "fxtwitter"
                            telemetry["retrieval_mode"] = RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
                            telemetry["authenticated"] = False
                    elif x_src.source_type == "profile" and x_src.handle:
                        frag = self._fetch_fxtwitter_profile(x_src.handle)
                        if frag:
                            frag.raw_metadata["discovered_from"] = "direct_input"
                            frag.raw_metadata["external_id"] = x_src.handle
                            frag.raw_metadata["content_completeness"] = "profile"
                            fragments = [frag]
                            self._tag_fragments(
                                fragments, "twitter", "twitter", RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, "fxtwitter", None, False
                            )
                            telemetry["status"] = "SUCCESS"
                            telemetry["backend"] = "fxtwitter"
                            telemetry["retrieval_mode"] = RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
                            telemetry["authenticated"] = False

                # BRANCH 2: Profile / Handle lookup (e.g. "@NASA" or alphanumeric handle)
                # NEVER default to NASA or another hardcoded account
                if not fragments and self.use_fxtwitter:
                    handle_match = re.match(r"^@?([a-zA-Z0-9_]{1,15})$", q_clean)
                    if handle_match and not q_clean.startswith("site:"):
                        handle = handle_match.group(1)
                        if handle.lower() not in TWITTER_RESERVED_PATHS:
                            frag = self._fetch_fxtwitter_profile(handle)
                            if frag:
                                frag.raw_metadata["discovered_from"] = "direct_input"
                                frag.raw_metadata["external_id"] = handle
                                frag.raw_metadata["content_completeness"] = "profile"
                                fragments = [frag]
                                self._tag_fragments(
                                    fragments, "twitter", "twitter", RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, "fxtwitter", None, False
                                )
                                telemetry["status"] = "SUCCESS"
                                telemetry["backend"] = "fxtwitter"
                                telemetry["retrieval_mode"] = RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
                                telemetry["authenticated"] = False

                # BRANCH 3 & 4: SEARCH / DISCOVERY QUERY & BROAD X QUERY
                # Search for actual x.com/twitter.com status URLs, extract IDs, fetch via FxTwitter
                if not fragments and self.use_fxtwitter and self.use_social_url_discovery:
                    target_ent = kwargs.get("entity") or ""
                    target_top = kwargs.get("topic") or ""
                    target_clm = kwargs.get("claim") or ""
                    task_t = kwargs.get("task_type") or "SEARCH"

                    discovery_queries = generate_discovery_queries("twitter", q_clean, entity=target_ent, task_type=task_t)
                    candidate_urls_all: List[str] = []
                    discovered_statuses: List[SourceDiscoveryResult] = []
                    queries_attempted_count = 0

                    for dq in discovery_queries:
                        queries_attempted_count += 1
                        try:
                            search_frags = self._execute_web_search(
                                dq, limit=8, query_id=query_id, query_class=query_class, query_text=q_text
                            )
                        except (StopIteration, Exception):
                            search_frags = []
                        if search_frags:
                            for sf in search_frags:
                                if sf.url not in candidate_urls_all:
                                    candidate_urls_all.append(sf.url)
                            cands = discover_sources_from_search(
                                search_frags, platform="twitter", query=dq,
                                target_entity=target_ent, target_topic=target_top, target_claim=target_clm,
                                task_type=task_t, max_candidates=5
                            )
                            for c in cands:
                                if (c.source_type in ("status", "profile")) and c.external_id:
                                    if not any(x.external_id == c.external_id for x in discovered_statuses):
                                        discovered_statuses.append(c)
                        if len(discovered_statuses) >= 2:
                            break

                    telemetry["discovery_attempted"] = True
                    telemetry["discovery_engine"] = "bing_search"
                    telemetry["queries_attempted"] = queries_attempted_count
                    telemetry["candidate_urls_count"] = len(candidate_urls_all)
                    telemetry["social_candidate_count"] = len(discovered_statuses)
                    telemetry["valid_status_urls_count"] = len(discovered_statuses)
                    telemetry["x_status_url_count"] = len(discovered_statuses)

                    fetched_tweets: List[EvidenceFragment] = []
                    if discovered_statuses:
                        telemetry["selected_source_url"] = discovered_statuses[0].canonical_url
                        telemetry["selected_external_id"] = discovered_statuses[0].external_id
                        telemetry["mirror_attempted"] = True
                        telemetry["mirror_provider"] = "fxtwitter"

                        for cand in discovered_statuses:
                            if cand.source_type == "profile":
                                t_frag = self._fetch_fxtwitter_profile(cand.handle or cand.external_id)
                                if t_frag and t_frag.content:
                                    t_frag.raw_metadata["discovered_from"] = "search_url_discovery"
                                    t_frag.raw_metadata["external_id"] = cand.external_id
                                    t_frag.raw_metadata["content_completeness"] = "profile"
                                    fetched_tweets.append(t_frag)
                                    if len(fetched_tweets) >= limit:
                                        break
                            else:
                                t_frag = self._fetch_fxtwitter_status(cand.handle or "status", cand.external_id)
                                if t_frag and t_frag.content:
                                    t_frag.raw_metadata["discovered_from"] = "search_url_discovery"
                                    t_frag.raw_metadata["external_id"] = cand.external_id
                                    t_frag.raw_metadata["content_completeness"] = "full_status"
                                    fetched_tweets.append(t_frag)
                                    if len(fetched_tweets) >= limit:
                                        break

                        if fetched_tweets:
                            fragments = fetched_tweets[:limit]
                            self._tag_fragments(
                                fragments, "twitter", "twitter", RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, "fxtwitter", None, False
                            )
                            telemetry["status"] = "SUCCESS"
                            telemetry["backend"] = "fxtwitter"
                            telemetry["retrieval_mode"] = RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
                            telemetry["authenticated"] = False
                            telemetry["discovered_from"] = "search_url_discovery"
                            telemetry["mirror_result"] = "SUCCESS"
                        else:
                            telemetry["mirror_result"] = "FALLBACK"
                    else:
                        telemetry["mirror_attempted"] = False
                        telemetry["mirror_result"] = "NO_VALID_URLS"

                # BRANCH 5: FALLBACK (If no valid status discovered or FxTwitter failed)
                if not fragments:
                    site_query = f"site:twitter.com OR site:x.com {query}"
                    fragments = self._execute_web_search(
                        site_query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text
                    )
                    if fragments:
                        self._tag_fragments(
                            fragments,
                            requested_channel="twitter",
                            actual_channel="web_search",
                            mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                            backend_id="bing-search-index",
                            fallback_reason="FXTWITTER_SEARCH_INDEX_FALLBACK",
                            is_authenticated=False
                        )
                        for f in fragments:
                            f.platform = "Twitter (Web Index Fallback)"
                            f.retrieval_method = "twitter_web_index"
                            f.raw_metadata["source_tier"] = "TIER_3_AGGREGATE"
                            f.raw_metadata["honest_disclosure"] = "Broad X claim search routed via public search index (zero-auth)"
                        telemetry["status"] = "SUCCESS"
                        telemetry["fallback_used"] = True
                        telemetry["fallback_backend"] = "Bing Search Index"
                        telemetry["fallback_reason"] = "FXTWITTER_SEARCH_INDEX_FALLBACK"
                        telemetry["retrieval_mode"] = RetrievalMode.WEB_SEARCH_INDEX.value
                    else:
                        telemetry["status"] = "DEGRADED"
                        telemetry["fallback_used"] = True
                        telemetry["fallback_backend"] = "Bing Search Index"
                        telemetry["fallback_reason"] = "FXTWITTER_SEARCH_INDEX_FALLBACK"

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
                self._tag_fragments(fragments, platform, platform, RetrievalMode.DIRECT_API.value, active_backend or "generic-search", None, False)
                telemetry["status"] = "SUCCESS" if fragments else "DEGRADED"

        except AuthRequiredError as auth_err:
            telemetry["status"] = "AUTH_REQUIRED"
            telemetry["error"] = str(auth_err)
        except Exception as e:
            logger.warning(f"[NativeRouter] Query execution failed for '{platform}': {e}")
            telemetry["status"] = "FAILED"
            telemetry["error"] = str(e)

        telemetry["latency_ms"] = int((time.perf_counter() - t0) * 1000)

        # Defensive check to ensure provenance attributes are populated
        for f in fragments:
            if not getattr(f, "requested_channel", None):
                f.requested_channel = platform
            if not getattr(f, "actual_retrieval_channel", None):
                f.actual_retrieval_channel = getattr(f, "channel_name", None) or platform

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

        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        path = parsed.path.strip("/")

        # 1. Specialized Zero-Auth Social: Twitter / X
        if "twitter.com" in netloc or "x.com" in netloc:
            x_src = extract_x_source(url)
            if x_src and self.use_fxtwitter:
                if x_src.source_type == "status" and x_src.external_id:
                    frag = self._fetch_fxtwitter_status(x_src.handle or "status", x_src.external_id)
                    if frag and frag.content:
                        return {
                            "status": "success",
                            "title": frag.title,
                            "content": frag.content[:max_chars],
                            "markdown": f"### {frag.title}\n\n{frag.content}\n\n*Metrics: {frag.raw_metadata}*",
                            "url": url,
                            "char_count": len(frag.content),
                            "backend": "fxtwitter",
                            "fallback_used": False,
                        }
                elif x_src.source_type == "profile" and x_src.handle:
                    frag = self._fetch_fxtwitter_profile(x_src.handle)
                    if frag and frag.content:
                        return {
                            "status": "success",
                            "title": frag.title,
                            "content": frag.content[:max_chars],
                            "markdown": f"### {frag.title}\n\n{frag.content}",
                            "url": url,
                            "char_count": len(frag.content),
                            "backend": "fxtwitter",
                            "fallback_used": False,
                        }

        # 2. Specialized Zero-Auth Social: Reddit
        if "reddit.com" in netloc or "redd.it" in netloc:
            red_src = extract_reddit_source(url)
            if red_src and self.use_arctic_shift:
                target_pid = red_src.parent_id if red_src.source_type == "comment" else red_src.external_id
                if target_pid:
                    frag = self._fetch_arctic_shift_post(target_pid)
                    comments = self._fetch_arctic_shift_comments(target_pid, limit=5)
                    if frag and frag.content:
                        comm_md = ""
                        if comments:
                            comm_md = "\n\n### Top Comments\n" + "\n\n".join(
                                [f"**{c.author}** ({int(c.score)} pts):\n{c.content}" for c in comments[:3]]
                            )
                        full_body = frag.content + comm_md
                        return {
                            "status": "success",
                            "title": frag.title,
                            "content": full_body[:max_chars],
                            "markdown": f"### {frag.title}\n**Author**: {frag.author}\n\n{full_body[:max_chars]}\n\n*Source: {frag.url}*",
                            "url": url,
                            "char_count": len(full_body),
                            "backend": "arctic_shift",
                            "fallback_used": False,
                        }

        # 3. Specialized Video: YouTube via yt-dlp
        if "youtube.com" in netloc or "youtu.be" in netloc:
            try:
                import yt_dlp
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "extract_flat": True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                if info:
                    title = info.get("title") or "YouTube Video"
                    desc = info.get("description") or ""
                    uploader = info.get("uploader") or info.get("channel") or "YouTube Channel"
                    content = f"Title: {title}\nChannel: {uploader}\n\nDescription:\n{desc}"
                    if len(content.strip()) > 30:
                        return {
                            "status": "success",
                            "title": title,
                            "content": content[:max_chars],
                            "markdown": f"### {title}\n**Channel**: {uploader}\n\n{desc[:max_chars]}\n\n*Source: {url}*",
                            "url": url,
                            "char_count": len(content),
                            "backend": "yt-dlp",
                            "fallback_used": False,
                        }
            except Exception as e_yt:
                logger.debug(f"[NativeRouter] yt-dlp read notice for {url}: {e_yt}")

        # 4. Standard Web Document: Scrapling HTTP Primary -> Playwright Rescue
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
                    "backend": res.get("backend", "scrapling_http"),
                    "fallback_used": False,
                }
        except Exception as e_web:
            logger.debug(f"[NativeRouter] Native web read notice: {e_web}. Trying fallback scraper.")

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
            "Cookie": "SRCHHPGUSR=ADLT=OFF&NRSLT=20",
        }

        url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(clean_q)}&setlang=en&cc=US"
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
                dest_url = resolve_bing_redirect(raw_href) or raw_href

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
                    retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                    native_backend_id="bing-search-index",
                    channel_name="web",
                    query_id=query_id,
                    query_class=query_class,
                    query_text=query_text or query,
                    raw_metadata={
                        "backend": "Bing Search",
                        "raw_url": raw_href,
                    }
                ))

        # Complement with Yahoo search for social platform discovery
        if any(term in clean_q.lower() for term in ("reddit", "twitter", "x.com")):
            social_urls = [f.url for f in fragments if any(dom in f.url for dom in ("reddit.com", "x.com", "twitter.com"))]
            if len(social_urls) < 3:
                yahoo_frags = self._execute_yahoo_search(clean_q, limit=limit, query_id=query_id, query_class=query_class, query_text=query_text)
                for yf in yahoo_frags:
                    if not any(f.url == yf.url for f in fragments):
                        fragments.append(yf)
        return fragments

    def _execute_yahoo_search(self, query: str, limit: int = 6, query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Execute public zero-auth Yahoo search to uncover social URLs."""
        import requests
        from bs4 import BeautifulSoup

        clean_q = query.strip()
        fragments: List[EvidenceFragment] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        url = f"https://search.yahoo.com/search?p={urllib.parse.quote_plus(clean_q)}"
        try:
            resp = requests.get(url, headers=headers, timeout=6.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "/RU=" in href:
                        try:
                            raw_dest = href.split("/RU=")[1].split("/RK=")[0]
                            dest_url = urllib.parse.unquote(raw_dest)
                        except Exception:
                            continue

                        if not any(domain in dest_url for domain in ("reddit.com", "x.com", "twitter.com")):
                            continue
                        if any(f.url == dest_url for f in fragments):
                            continue

                        title = a.get_text(separator=" ", strip=True) or f"Result from {urllib.parse.urlparse(dest_url).netloc}"
                        fragments.append(EvidenceFragment(
                            platform="Web",
                            title=title,
                            content=title,
                            url=dest_url,
                            author=urllib.parse.urlparse(dest_url).netloc or "Web",
                            published="Recent",
                            snippet=title,
                            score=75.0,
                            retrieval_method="yahoo_search",
                            retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                            native_backend_id="yahoo-search-discovery",
                            channel_name="web",
                            query_id=query_id,
                            query_class=query_class,
                            query_text=query_text or query,
                            raw_metadata={
                                "backend": "Yahoo Search",
                                "raw_url": href,
                            }
                        ))
                        if len(fragments) >= limit:
                            break
        except Exception as e_y:
            logger.debug(f"[NativeRouter] Yahoo discovery query notice: {e_y}")
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
                    retrieval_mode=RetrievalMode.DIRECT_API.value,
                    native_backend_id="github-rest-api",
                    fallback_reason="GH_CLI_UNAVAILABLE",
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
        if hasattr(scraper, "search_web"):
            raw_items = scraper.search_web(query, limit=limit)
        elif hasattr(scraper, "search_news"):
            raw_items = scraper.search_news(query, limit=limit)
        else:
            raw_items = []
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

    def execute_retrieval_request(self, request: RetrievalRequest) -> List[EvidenceFragment]:
        """
        One shared authoritative retrieval pipeline (Policy D) used by all four domain agents.
        Enforces:
          - Discovery separated from Source Selection separated from Content Extraction
          - Hard source gates (scope, entity anti-cheat, url structure, doc type)
          - Knee: Top-5 semantic candidate selection by default
          - Escalation: Top-10 only when evidence is weak or conflicting
          - Specialist mirror / native / Scrapling HTTP acquisition
          - Normalization into EvidenceFragment with full provenance and evidence IDs
        """
        t0 = time.perf_counter()
        query_text = request.query or request.entity or request.intent
        if not query_text:
            return []

        # 1. Determine target channels with profile preferences
        channels = list(request.allowed_channels) if request.allowed_channels else ["web", "news"]
        if request.profile and request.profile.preferred_platforms:
            for pref in request.profile.preferred_platforms:
                if pref not in channels and not request.allowed_channels:
                    channels.append(pref)
            # Sort channels to prioritize agent's preferred platforms first
            pref_set = set(request.profile.preferred_platforms)
            channels.sort(key=lambda c: 0 if c in pref_set else 1)

        all_candidates: List[CandidateSource] = []

        # 2. Candidate Discovery via SearchDiscoveryAdapter
        for ch in channels:
            try:
                cands = self.search_adapter.discover_candidates(
                    query=query_text,
                    platform=ch,
                    entity=request.entity,
                    limit=max(request.candidate_budget * 2, 10),
                )
                all_candidates.extend(cands)
            except Exception as e_disc:
                logger.debug(f"[NativeRouter] Candidate discovery error for channel {ch}: {e_disc}")

        # 2b. Agent-Specific Strategy Candidate Discovery
        from backend.services.agent_reach.profile import get_agent_acquisition_strategy
        strat = get_agent_acquisition_strategy(request.agent)
        if strat:
            try:
                strat_cands = strat.discover(query=query_text, limit=min(request.candidate_budget, 5))
                all_candidates.extend(strat_cands)
            except Exception as e_sdisc:
                logger.debug(f"[NativeRouter] Strategy discovery error for {request.agent}: {e_sdisc}")

        # If no candidates from search discovery, create fallback candidate from direct query/URL
        if not all_candidates:
            if "http://" in query_text or "https://" in query_text:
                all_candidates.append(
                    CandidateSource(
                        url=query_text,
                        platform="web",
                        title=f"Direct URL: {query_text}",
                        passed_hard_gates=True,
                    )
                )

        # 3. Hard Source Gates & Semantic Scoring
        passed_candidates: List[CandidateSource] = []
        for cand in all_candidates:
            # Platform & structure validation
            url_lower = cand.canonical_url.lower()
            if not is_valid_content_source(
                SourceDiscoveryResult(
                    platform=cand.platform,
                    canonical_url=cand.canonical_url,
                    source_type=cand.metadata.get("source_type", "post"),
                    external_id=cand.metadata.get("external_id", "ext_1"),
                    handle=cand.metadata.get("handle"),
                    subreddit=cand.metadata.get("subreddit"),
                ),
                task_type=request.task_type
            ):
                cand.passed_hard_gates = False
                cand.gate_failure_reason = "URL structure or reserved path check failed"
                continue

            # Scope gate
            if request.scope:
                req_scope = request.scope.lower().strip()
                if req_scope.startswith("r/") and cand.metadata.get("subreddit"):
                    if cand.metadata.get("subreddit").lower() != req_scope[2:]:
                        cand.passed_hard_gates = False
                        cand.gate_failure_reason = f"Subreddit mismatch: expected {req_scope}"
                        continue
                elif req_scope.startswith("@") and cand.metadata.get("handle"):
                    if cand.metadata.get("handle").lower() != req_scope[1:]:
                        cand.passed_hard_gates = False
                        cand.gate_failure_reason = f"Handle mismatch: expected {req_scope}"
                        continue

            # Entity relevance & anti-token cheat gate
            eval_res = evaluate_content_relevance(
                content=f"{cand.title} {cand.snippet}",
                target_entity=request.entity,
                target_topic=request.intent,
                target_claim=request.intent,
                platform=cand.platform,
                candidate_metadata=cand.metadata,
                requested_scope=request.scope,
                task_type=request.task_type,
            )

            cand.semantic_score = eval_res["semantic_score"]
            if not eval_res["accepted"] and request.entity and len(request.entity.strip()) > 3:
                # If strict entity required and did not match
                if not eval_res.get("entity_match"):
                    cand.passed_hard_gates = False
                    cand.gate_failure_reason = "Failed entity anti-token-cheat gate"
                    continue
            # Profile-aware scoring adjustments
            if request.profile:
                if request.profile.need_primary_source and any(
                    p in cand.canonical_url.lower()
                    for p in ("sec.gov", "investor.", "ir.", "edgar.", "prnewswire.com", "businesswire.com")
                ):
                    cand.semantic_score = min(100.0, cand.semantic_score + 20.0)
                if request.profile.need_engagement and cand.platform in ("twitter", "x", "reddit", "youtube"):
                    cand.semantic_score = min(100.0, cand.semantic_score + 10.0)
                if cand.platform in request.profile.preferred_platforms:
                    cand.semantic_score = min(100.0, cand.semantic_score + 5.0)

            passed_candidates.append(cand)

        # 4. Semantic Ranking & Default Top-5 Selection
        passed_candidates.sort(key=lambda c: c.semantic_score, reverse=True)
        initial_budget = min(request.candidate_budget or 5, len(passed_candidates))
        selected_candidates = passed_candidates[:initial_budget]

        discovery_reqs = len(channels)
        acq_attempts = 0
        succ_acquisitions = 0
        fallback_attempts = 0
        search_reqs = len(channels)
        mirror_reqs = 0
        browser_reqs = 0

        def _acquire_candidate(cand: CandidateSource) -> List[EvidenceFragment]:
            nonlocal acq_attempts, succ_acquisitions, fallback_attempts, search_reqs, mirror_reqs, browser_reqs
            acq_attempts += 1
            # Authoritative route decision via RoutePolicyEngine
            decision = RoutePolicyEngine.decide_route(
                platform=cand.platform,
                request_id=request.request_id,
                task_type=request.task_type,
                is_url=bool(cand.url and cand.url.startswith("http"))
            )
            if decision.primary_backend in ("arctic_shift", "fxtwitter"):
                mirror_reqs += 1
            elif decision.primary_backend == "search_discovery":
                search_reqs += 1
            elif decision.primary_backend in ("playwright_rescue", "browser"):
                browser_reqs += 1

            # Authoritative adapter derived directly from RouteDecision via AdapterRegistry
            adapter = self.adapter_registry.get_adapter_for_decision(decision, cand)

            try:
                doc = adapter.acquire(cand, request)
                if doc.status == "SUCCESS":
                    succ_acquisitions += 1
                    frags = adapter.normalize(doc, cand, request)
                    # Domain-specific strategy normalization if agent strategy registered
                    from backend.services.agent_reach.profile import get_agent_acquisition_strategy
                    strat = get_agent_acquisition_strategy(request.agent)
                    if strat:
                        frags = strat.normalize(doc, cand, request)
                    elif request.profile:
                        for f in frags:
                            f.content_depth = request.profile.content_depth
                    return frags
                else:
                    # Fallback to index snippet
                    fallback_attempts += 1
                    search_reqs += 1
                    return self.search_adapter.normalize(
                        FetchedDocument(
                            url=cand.url,
                            status="SUCCESS",
                            backend_id="search_index_fallback",
                            retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                            raw_content=json.dumps({"title": cand.title, "snippet": cand.snippet, "url": cand.url}),
                        ),
                        cand,
                        request,
                    )
            except Exception as e_acq:
                fallback_attempts += 1
                logger.debug(f"[NativeRouter] Adapter {adapter.backend_id} acquisition error for {cand.url}: {e_acq}")
                return []

        # 5. Acquire Content: Initial Top-5 Batch
        final_fragments: List[EvidenceFragment] = []
        for cand in selected_candidates:
            final_fragments.extend(_acquire_candidate(cand))

        # 6. Evaluate Evidence Sufficiency & Evidence-Driven Escalation to Top-10
        remaining_candidates = passed_candidates[initial_budget:min(10, len(passed_candidates))]
        sufficiency_eval = evidence_sufficiency_evaluator.evaluate(
            final_fragments,
            request,
            remaining_candidates_count=len(remaining_candidates)
        )
        escalation_used = False
        if sufficiency_eval.should_escalate and remaining_candidates:
            escalation_used = True
            logger.info(f"[NativeRouter] Escalating candidate depth for {request.request_id}: {sufficiency_eval.reasons}")
            for cand in remaining_candidates:
                final_fragments.extend(_acquire_candidate(cand))

        # 6. Deduplicate & Record Telemetry
        seen_urls = set()
        deduped_fragments: List[EvidenceFragment] = []
        for f in final_fragments:
            if f.url and f.url in seen_urls:
                continue
            seen_urls.add(f.url)
            deduped_fragments.append(f)

        lat_ms = int((time.perf_counter() - t0) * 1000)
        acquisition_telemetry.record_attempt(
            AcquisitionTelemetryRecord(
                request_id=request.request_id,
                query_id=request.query,
                agent=request.agent,
                platform=",".join(channels),
                backend="shared_acquisition_fabric",
                route_selected="policy_d",
                route_attempts=len(channels),
                latency_ms=lat_ms,
                result_count=len(deduped_fragments),
                discovery_requests=discovery_reqs,
                candidate_count=len(all_candidates),
                acquisition_attempts=acq_attempts,
                successful_acquisitions=succ_acquisitions,
                fallback_attempts=fallback_attempts,
                search_requests=search_reqs,
                mirror_requests=mirror_reqs,
                browser_requests=browser_reqs,
                cache_hits=0,
                cache_misses=acq_attempts,
                final_fragments=len(deduped_fragments),
                candidates_selected_deep_read=len(selected_candidates),
                fallback_used=escalation_used,
                final_retrieval_mode=deduped_fragments[0].retrieval_mode if deduped_fragments else "none",
                source_selection_rationale=f"Selected {len(selected_candidates)} candidates via Policy D semantic rubric",
            )
        )

        return deduped_fragments


# Global singleton instance
native_router = NativeRouter()
