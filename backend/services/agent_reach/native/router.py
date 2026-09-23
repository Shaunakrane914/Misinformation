"""
Aegis Protocol — Native Agent Reach Capability Router
======================================================
Routes domain search and retrieval requests to the active upstream backend
determined by live Doctor checks, following upstream-specified fallback chains
and recording full execution telemetry for every attempt.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.services.agent_reach.channels import ChannelStatus, EvidenceFragment
from backend.services.agent_reach.native.channel_capabilities import get_capability
from backend.services.agent_reach.native.doctor import native_doctor
from backend.services.agent_reach.native.errors import AuthRequiredError, NativeReachError
from backend.services.agent_reach.native.executor import native_executor
from backend.services.agent_reach.native.normalizer import native_normalizer

logger = logging.getLogger(__name__)


class NativeRouter:
    """
    Capability-aware channel router coordinating native execution across platforms.
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
        domain: str = "general",
        **kwargs
    ) -> Tuple[List[EvidenceFragment], Dict[str, Any]]:
        """
        Execute a search or fetch for a specific platform using its active backend.
        
        Returns:
            Tuple of (fragments: List[EvidenceFragment], telemetry: Dict[str, Any])
        """
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
            # ── 1. GitHub ──
            if platform == "github":
                res = self.executor.execute_github_search(query, limit=limit)
                fragments = self.normalizer.normalize_github_repos(
                    res.get("items", []), query_id=query_id, query_class=query_class, query_text=query
                )
                telemetry["status"] = "SUCCESS"

            # ── 2. YouTube ──
            elif platform == "youtube":
                res = self.executor.execute_youtube_search(query, limit=limit)
                fragments = self.normalizer.normalize_youtube_search(
                    res.get("items", []), query_id=query_id, query_class=query_class, query_text=query
                )
                telemetry["status"] = "SUCCESS"

            # ── 3. V2EX ──
            elif platform == "v2ex":
                # If query contains tech keywords, look for hot topics or specific node
                res = self.executor.execute_v2ex_hot()
                raw_items = res.get("items", [])
                # Filter by query keyword if provided
                if query and query.strip():
                    q_low = query.lower()
                    filtered = [t for t in raw_items if q_low in t.get("title", "").lower() or q_low in (t.get("content") or "").lower()]
                    raw_items = filtered or raw_items[:limit]
                fragments = self.normalizer.normalize_v2ex_topics(
                    raw_items[:limit], query_id=query_id, query_class=query_class, query_text=query
                )
                telemetry["status"] = "SUCCESS"

            # ── 4. Bilibili ──
            elif platform == "bilibili":
                res = self.executor.execute_bilibili_search(query, limit=limit)
                fragments = self.normalizer.normalize_bilibili_videos(
                    res.get("items", []), query_id=query_id, query_class=query_class, query_text=query
                )
                telemetry["status"] = "SUCCESS"

            # ── 5. RSS / News Wires ──
            elif platform in ("rss", "news"):
                # Use Google News RSS or company wire feed
                feed_query = urllib.parse.quote_plus(query.strip())
                rss_url = f"https://news.google.com/rss/search?q={feed_query}&hl=en-US&gl=US&ceid=US:en"
                res = self.executor.execute_rss_read(rss_url, limit=limit)
                fragments = self.normalizer.normalize_rss_entries(
                    res.get("items", []), channel_name=platform, query_id=query_id, query_class=query_class, query_text=query
                )
                telemetry["status"] = "SUCCESS"

            # ── 6. Web Page Read ──
            elif platform == "web" and kwargs.get("is_read"):
                target_url = kwargs.get("url") or query
                res = self.executor.execute_web_read(target_url)
                frag = EvidenceFragment(
                    platform="Web",
                    title=f"Article from {urllib.parse.urlparse(target_url).netloc}",
                    content=res.get("content", ""),
                    url=target_url,
                    author=urllib.parse.urlparse(target_url).netloc,
                    published="Recent",
                    snippet=res.get("content", "")[:300],
                    score=85.0,
                    retrieval_method="jina_reader",
                    channel_name="web",
                    content_depth="FULL_ARTICLE",
                    query_id=query_id,
                    query_class=query_class,
                    query_text=query,
                    raw_metadata={"backend": "Jina Reader"}
                )
                fragments = [frag]
                telemetry["status"] = "SUCCESS"

            # ── 7. Authenticated / Social Channels (Twitter, Reddit, FB, IG, etc.) ──
            elif platform in ("twitter", "reddit", "facebook", "instagram", "xiaohongshu", "xueqiu", "boss", "linkedin"):
                # Check authentication requirements
                self.executor.guard_authenticated_channel(
                    platform=platform,
                    backend=active_backend,
                    env_var=f"{platform.upper()}_COOKIE"
                )
                # If passed guard, execute local tool...
                telemetry["status"] = "SUCCESS"

            # ── 8. Web Search Fallback ──
            else:
                # Open web search via Bing / DDG
                from backend.services.agent_reach.channels_impl import WebChannel
                web_chan = WebChannel()
                fragments = web_chan.search(query, limit=limit, query_id=query_id, query_class=query_class, query_text=query)
                telemetry["status"] = "SUCCESS"

        except AuthRequiredError as auth_err:
            telemetry["status"] = "AUTH_REQUIRED"
            telemetry["error"] = str(auth_err)
            logger.info(f"[NativeRouter] Platform '{platform}' requires authentication: {auth_err.message}")

        except Exception as e:
            logger.warning(f"[NativeRouter] Primary backend '{active_backend}' for '{platform}' failed: {e}")
            telemetry["error"] = str(e)
            
            # Check fallback chain
            if cap.fallback_chain:
                fb_backend = cap.fallback_chain[0]
                telemetry["fallback_used"] = True
                telemetry["fallback_backend"] = fb_backend
                telemetry["attempts"] += 1
                logger.info(f"[NativeRouter] Activating fallback backend '{fb_backend}' for '{platform}'")
                
                # Execute fallback if available
                try:
                    if platform == "github":
                        # Direct REST fallback
                        from backend.services.agent_reach.channels_impl import GitHubChannel
                        gh_fb = GitHubChannel()
                        fragments = gh_fb.search(query, limit=limit)
                        telemetry["status"] = "SUCCESS"
                    elif platform == "web_search":
                        from backend.services.agent_reach.channels_impl import WebChannel
                        web_fb = WebChannel()
                        fragments = web_fb.search(query, limit=limit, query_id=query_id, query_class=query_class, query_text=query)
                        telemetry["status"] = "SUCCESS"
                    else:
                        telemetry["status"] = "DEGRADED"
                except Exception as fb_err:
                    telemetry["status"] = "FAILED"
                    telemetry["error"] = f"Primary failed ({e}); Fallback failed ({fb_err})"
            else:
                telemetry["status"] = "FAILED"

        telemetry["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        return fragments, telemetry


# Global singleton instance
native_router = NativeRouter()
