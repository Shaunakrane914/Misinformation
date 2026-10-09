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

from backend.infrastructure.acquisition.adapters.social.reddit import (
    fetch_arctic_shift_comments,
    fetch_arctic_shift_post,
    fetch_arctic_shift_posts_batch,
    fetch_arctic_shift_search,
)
from backend.infrastructure.acquisition.adapters.social.twitter import (
    fetch_fxtwitter_profile,
    fetch_fxtwitter_status,
)
from backend.infrastructure.acquisition.adapters.web.jina import execute_web_read
from backend.infrastructure.acquisition.routing.channel_dispatcher import ChannelQueryDispatcher
from backend.services.agent_reach.channels import (
    CandidateSource,
    ChannelStatus,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.agent_reach.native.adapters import (
    adapter_registry,
)
from backend.services.agent_reach.native.doctor import native_doctor
from backend.services.agent_reach.native.executor import native_executor
from backend.services.agent_reach.native.normalizer import native_normalizer
from backend.services.agent_reach.native.evidence_sufficiency import (
    evidence_sufficiency_evaluator,
)
from backend.services.agent_reach.native.route_policy import (
    RoutePolicyEngine,
)
from backend.services.agent_reach.native.source_discovery import (
    SourceDiscoveryResult,
    evaluate_content_relevance,
    extract_reddit_source,
    extract_x_source,
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
    Capability-aware orchestrator for channel queries, reads, and Policy D retrieval.

    Query dispatch, platform execution, social discovery/fallback, and shared telemetry
    are delegated to focused routing components. This class retains the reusable read,
    search, normalization, security, and Policy D coordination primitives they compose.
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
        self.channel_dispatcher = ChannelQueryDispatcher(self)

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
        query_text: str = "",
    ) -> List[EvidenceFragment]:
        if not self.use_arctic_shift:
            return []
        return fetch_arctic_shift_posts_batch(
            post_ids,
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            cache_get=self._get_social_cache,
            cache_set=self._set_social_cache,
        )

    def _fetch_arctic_shift_post(self, post_id: str) -> Optional[EvidenceFragment]:
        if not self.use_arctic_shift:
            return None
        return fetch_arctic_shift_post(
            post_id,
            cache_get=self._get_social_cache,
            cache_set=self._set_social_cache,
        )

    def _fetch_arctic_shift_search(
        self,
        query: str = "",
        subreddit: str = "",
        author: str = "",
        limit: int = 5,
        query_id: str = "",
        query_class: str = "",
        query_text: str = "",
    ) -> List[EvidenceFragment]:
        return fetch_arctic_shift_search(
            query=query,
            subreddit=subreddit,
            author=author,
            limit=limit,
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            cache_get=self._get_social_cache,
            cache_set=self._set_social_cache,
        )

    def _fetch_arctic_shift_comments(
        self,
        post_id: str,
        limit: int = 10,
        query_id: str = "",
        query_class: str = "",
        query_text: str = "",
    ) -> List[EvidenceFragment]:
        return fetch_arctic_shift_comments(
            post_id=post_id,
            limit=limit,
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            cache_get=self._get_social_cache,
            cache_set=self._set_social_cache,
        )

    def _fetch_fxtwitter_status(self, user: str, status_id: str) -> Optional[EvidenceFragment]:
        if not self.use_fxtwitter:
            return None
        return fetch_fxtwitter_status(
            user,
            status_id,
            cache_get=self._get_social_cache,
            cache_set=self._set_social_cache,
        )

    def _fetch_fxtwitter_profile(self, user: str) -> Optional[EvidenceFragment]:
        if not self.use_fxtwitter:
            return None
        return fetch_fxtwitter_profile(
            user,
            cache_get=self._get_social_cache,
            cache_set=self._set_social_cache,
        )

    @staticmethod
    def _tag_fragments(
        fragments: List[EvidenceFragment],
        requested_channel: str,
        actual_channel: str,
        mode: str,
        backend_id: str,
        fallback_reason: Optional[str] = None,
        is_authenticated: bool = False,
    ) -> List[EvidenceFragment]:
        """Enrich fragments with forensic provenance metadata."""
        for f in fragments:
            f.requested_channel = requested_channel
            f.actual_retrieval_channel = actual_channel
            f.retrieval_mode = mode
            f.native_backend_id = backend_id
            f.fallback_reason = fallback_reason
            f.is_authenticated = is_authenticated
            if not hasattr(f, "raw_metadata") or f.raw_metadata is None:
                f.raw_metadata = {}
            f.raw_metadata["retrieval_lineage"] = [{
                "requested_channel": requested_channel,
                "actual_channel": actual_channel,
                "retrieval_mode": mode,
                "backend_id": backend_id,
                "fallback_reason": fallback_reason,
                "is_authenticated": is_authenticated,
                "retrieved_at": getattr(f, "retrieved_at", ""),
            }]
        return fragments

    def execute_channel_query(
        self,
        platform: str,
        query: str,
        limit: int = 5,
        query_id: str = "",
        query_class: str = "",
        query_text: str = "",
        domain: str = "general",
        **kwargs: Any,
    ) -> Tuple[List[EvidenceFragment], Dict[str, Any]]:
        """Dispatch a channel request through cohesive platform handlers."""
        return self.channel_dispatcher.execute(
            platform=platform,
            query=query,
            limit=limit,
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            domain=domain,
            **kwargs,
        )

    def execute_channel_read(self, url: str, max_chars: int = 4000, **kwargs) -> Dict[str, Any]:
        """
        Safely fetch and extract document content into clean markdown.
        Enforces SSRF defense before network transmission.
        Routes specialized social/video URLs to specialist mirrors, and standard web pages
        through modular web reading.
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

        # 4. Standard Web Document: Delegated to modular web reader
        legacy_scraper = None
        try:
            import backend.services.agent_reach.native.router as _shim
            scraper_factory = getattr(_shim, "_get_legacy_scraper", _get_legacy_scraper)
            legacy_scraper = scraper_factory()
        except Exception:
            legacy_scraper = _get_legacy_scraper()

        return execute_web_read(
            url,
            max_chars=max_chars,
            executor=self.executor,
            legacy_scraper=legacy_scraper,
        )

    def _execute_web_search(self, query: str, limit: int = 6, query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Execute open-web search using Bing with redirect resolution."""
        import requests
        from bs4 import BeautifulSoup

        clean_q = query.strip()
        fragments: List[EvidenceFragment] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(clean_q)}"
            resp = requests.get(url, headers=headers, timeout=6.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = soup.select("li.b_algo")
                for r in results:
                    title_elem = r.select_one("h2 a")
                    snippet_elem = r.select_one(".b_caption p, .b_snippet")
                    if title_elem:
                        raw_href = title_elem.get("href", "")
                        resolved_url = resolve_bing_redirect(raw_href)
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        if resolved_url and "bing.com" not in urllib.parse.urlparse(resolved_url).netloc:
                            fragments.append(EvidenceFragment(
                                platform="Web",
                                title=title,
                                snippet=snippet,
                                content=f"Title: {title}\nURL: {resolved_url}\n\nSnippet: {snippet}",
                                url=resolved_url,
                                author=urllib.parse.urlparse(resolved_url).netloc,
                                published="Recent",
                                channel_name="web",
                                query_id=query_id,
                                query_class=query_class,
                                query_text=query_text or clean_q,
                            ))
                            if len(fragments) >= limit:
                                break
        except Exception as e:
            logger.debug(f"[NativeRouter] Bing search attempt notice: {e}. Trying Yahoo fallback.")

        if not fragments:
            fragments = self._execute_yahoo_search(clean_q, limit=limit, query_id=query_id, query_class=query_class, query_text=query_text)

        return fragments

    def _execute_yahoo_search(self, query: str, limit: int = 6, query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Secondary public web search via Yahoo Search."""
        import requests
        from bs4 import BeautifulSoup

        clean_q = query.strip()
        fragments: List[EvidenceFragment] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            url = f"https://search.yahoo.com/search?p={urllib.parse.quote_plus(clean_q)}"
            resp = requests.get(url, headers=headers, timeout=6.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = soup.select("div.algo")
                for r in results:
                    title_elem = r.select_one("h3 a")
                    snippet_elem = r.select_one(".compText p, .compText")
                    if title_elem:
                        raw_href = title_elem.get("href", "")
                        actual_url = raw_href
                        if "/RU=" in raw_href:
                            try:
                                m = re.search(r"/RU=([^/]+)/", raw_href)
                                if m:
                                    actual_url = urllib.parse.unquote(m.group(1))
                            except Exception:
                                pass
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        if actual_url and "search.yahoo.com" not in actual_url:
                            fragments.append(EvidenceFragment(
                                platform="Web",
                                title=title,
                                snippet=snippet,
                                content=f"Title: {title}\nURL: {actual_url}\n\nSnippet: {snippet}",
                                url=actual_url,
                                author=urllib.parse.urlparse(actual_url).netloc,
                                published="Recent",
                                channel_name="web",
                                query_id=query_id,
                                query_class=query_class,
                                query_text=query_text or clean_q,
                            ))
                            if len(fragments) >= limit:
                                break
        except Exception as e_y:
            logger.debug(f"[NativeRouter] Yahoo fallback search error: {e_y}")

        return fragments

    def _fallback_github_rest(self, query: str, limit: int = 5, query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Zero-auth GitHub public search API fallback."""
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote_plus(query)}&per_page={limit}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AegisAgentReach/3.0",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_items = data.get("items", [])
                return self.normalizer.normalize_github_repos(
                    raw_items, query_id=query_id, query_class=query_class, query_text=query_text or query
                )
        except Exception as e:
            logger.debug(f"[NativeRouter] GitHub REST fallback failed: {e}")
            return []

    def _fallback_youtube_scraper(self, query: str, limit: int = 6, query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Legacy scraper fallback for YouTube search."""
        try:
            scraper = _get_legacy_scraper()
            raw_items = scraper.search_youtube(query, limit=limit)
            return self.normalizer.normalize_youtube_search(
                raw_items, query_id=query_id, query_class=query_class, query_text=query_text or query
            )
        except Exception as e:
            logger.debug(f"[NativeRouter] YouTube scraper fallback failed: {e}")
            return []

    def _fallback_news_scraper(self, query: str, limit: int = 6, channel_name: str = "news", query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Legacy scraper fallback for news/RSS entries."""
        try:
            scraper = _get_legacy_scraper()
            raw_items = scraper.search_news(query, limit=limit)
            return self.normalizer.normalize_rss_entries(
                raw_items, channel_name=channel_name, query_id=query_id, query_class=query_class, query_text=query_text or query
            )
        except Exception as e:
            logger.debug(f"[NativeRouter] News scraper fallback failed: {e}")
            return []

    def _fallback_web_scraper(self, query: str, limit: int = 6, query_id: str = "", query_class: str = "", query_text: str = "") -> List[EvidenceFragment]:
        """Legacy scraper fallback for open web search."""
        try:
            scraper = _get_legacy_scraper()
            raw_items = scraper.search_web(query, limit=limit)
        except Exception as e:
            logger.debug(f"[NativeRouter] Web scraper fallback failed: {e}")
            return []

        return [
            EvidenceFragment(
                platform="Web",
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                content=item.get("snippet", ""),
                url=item.get("link", ""),
                author=item.get("source", "Web"),
                published=item.get("date", "Recent"),
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
                if not eval_res.get("entity_match"):
                    cand.passed_hard_gates = False
                    cand.gate_failure_reason = "Failed entity anti-token-cheat gate"
                    continue

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

            adapter = self.adapter_registry.get_adapter_for_decision(decision, cand)

            try:
                doc = adapter.acquire(cand, request)
                if doc.status == "SUCCESS":
                    succ_acquisitions += 1
                    frags = adapter.normalize(doc, cand, request)
                    from backend.services.agent_reach.profile import get_agent_acquisition_strategy
                    strat = get_agent_acquisition_strategy(request.agent)
                    if strat:
                        frags = strat.normalize(doc, cand, request)
                    elif request.profile:
                        for f in frags:
                            f.content_depth = request.profile.content_depth
                    return frags
                else:
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

        # 7. Deduplicate & Record Telemetry
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
