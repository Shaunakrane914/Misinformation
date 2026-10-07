"""
Aegis Protocol — Trial Environment Native Router (Trial NativeRouter)
=====================================================================
Trial implementation of the proposed Zero-Auth Social Capability Routing.

Integrates:
  1. REDDIT: Arctic Shift REST API for post ID lookup and subreddit feeds,
     with graceful Search Index Fallback for unconstrained keyword queries.
  2. X / TWITTER: FxTwitter / FxEmbed API for tweet status URLs and user profiles,
     with graceful Search Index Fallback for keyword claim searches.
  3. FACEBOOK: Automated Public Search Index Fallback (site:facebook.com)
     replacing hard AuthRequiredError dead-ends.

Maintains 100% compatibility with EvidenceFragment schema and NativeRouter telemetry.
"""

import time
import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode
from backend.services.agent_reach.native.router import NativeRouter
from backend.services.agent_reach.native.errors import AuthRequiredError

logger = logging.getLogger(__name__)


class TrialNativeRouter(NativeRouter):
    """
    Candidate Router with zero-auth social media specialist adapters.
    Extends NativeRouter without modifying production core.
    """

    def __init__(self):
        super().__init__()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 1. SPECIALIST ADAPTER: Arctic Shift (Reddit)
    # ─────────────────────────────────────────────────────────────────────────
    def _fetch_arctic_shift_post(self, post_id: str, query_id: str = "") -> Optional[EvidenceFragment]:
        url = f"https://arctic-shift.photon-reddit.com/api/posts/ids?ids={post_id}"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=7.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                posts = data.get("data", [])
                if posts:
                    p = posts[0]
                    body = p.get("selftext") or p.get("title") or ""
                    title = p.get("title") or f"Reddit Submission {post_id}"
                    author = p.get("author") or "reddit_user"
                    subreddit = p.get("subreddit") or ""
                    created = p.get("created_utc")
                    score = p.get("score", 0)
                    num_comments = p.get("num_comments", 0)
                    permalink = f"https://reddit.com{p.get('permalink')}" if p.get("permalink") else url

                    frag = EvidenceFragment(
                        platform="reddit",
                        url=permalink,
                        content=body[:3000],
                        channel_name="reddit",
                        title=title,
                        author=f"u/{author}",
                        published=str(created) if created else "",
                        snippet=body[:200],
                        score=float(score),
                        content_depth="FULL_ARTICLE" if len(body) > 300 else "PARTIAL_CONTENT",
                        raw_metadata={
                            "score": score,
                            "num_comments": num_comments,
                            "subreddit": subreddit,
                            "post_id": post_id,
                            "source_tier": "SPECIALIST_MIRROR",
                            "mirror_backend": "arctic-shift"
                        }
                    )
                    return frag
        except Exception as e:
            logger.debug(f"[TrialRouter] Arctic Shift post fetch failed for {post_id}: {e}")
        return None

    def _fetch_arctic_shift_feed(self, subreddit: str, limit: int = 5) -> List[EvidenceFragment]:
        url = f"https://arctic-shift.photon-reddit.com/api/posts/search?subreddit={urllib.parse.quote_plus(subreddit)}&limit={limit}&sort=desc"
        req = urllib.request.Request(url, headers=self.headers)
        frags = []
        try:
            with urllib.request.urlopen(req, timeout=7.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                posts = data.get("data", [])
                for p in posts[:limit]:
                    body = p.get("selftext") or p.get("title") or ""
                    title = p.get("title") or "Reddit Post"
                    author = p.get("author") or "reddit_user"
                    created = p.get("created_utc")
                    permalink = f"https://reddit.com{p.get('permalink')}" if p.get("permalink") else ""
                    frag = EvidenceFragment(
                        platform="reddit",
                        url=permalink or f"https://reddit.com/r/{subreddit}",
                        content=body[:2000],
                        channel_name="reddit",
                        title=title,
                        author=f"u/{author}",
                        published=str(created) if created else "",
                        snippet=body[:200],
                        score=float(p.get("score", 0)),
                        content_depth="SNIPPET" if not p.get("selftext") else "PARTIAL_CONTENT",
                        raw_metadata={
                            "score": p.get("score", 0),
                            "num_comments": p.get("num_comments", 0),
                            "subreddit": subreddit,
                            "source_tier": "SPECIALIST_MIRROR",
                            "mirror_backend": "arctic-shift"
                        }
                    )
                    frags.append(frag)
        except Exception as e:
            logger.debug(f"[TrialRouter] Arctic Shift feed fetch failed for r/{subreddit}: {e}")
        return frags

    # ─────────────────────────────────────────────────────────────────────────
    # 2. SPECIALIST ADAPTER: FxTwitter (X / Twitter)
    # ─────────────────────────────────────────────────────────────────────────
    def _fetch_fxtwitter_status(self, user: str, status_id: str) -> Optional[EvidenceFragment]:
        url = f"https://api.fxtwitter.com/{user}/status/{status_id}"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 200 and data.get("tweet"):
                    tw = data["tweet"]
                    author_obj = tw.get("author", {})
                    author_handle = author_obj.get("screen_name") or user
                    author_name = author_obj.get("name") or author_handle
                    text = tw.get("text") or ""
                    created = tw.get("created_at") or tw.get("created_timestamp")
                    likes = tw.get("likes", 0)
                    rts = tw.get("retweets", 0)
                    replies = tw.get("replies", 0)

                    frag = EvidenceFragment(
                        platform="twitter",
                        url=tw.get("url") or f"https://x.com/{author_handle}/status/{status_id}",
                        content=text,
                        channel_name="twitter",
                        title=f"Post by {author_name} (@{author_handle})",
                        author=f"@{author_handle}",
                        published=str(created) if created else "",
                        snippet=text[:200],
                        content_depth="FULL_ARTICLE" if len(text) > 0 else "SNIPPET",
                        raw_metadata={
                            "likes": likes,
                            "retweets": rts,
                            "replies": replies,
                            "source_tier": "SPECIALIST_MIRROR",
                            "mirror_backend": "fxtwitter"
                        }
                    )
                    return frag
        except Exception as e:
            logger.debug(f"[TrialRouter] FxTwitter status fetch failed for {user}/{status_id}: {e}")
        return None

    def _fetch_fxtwitter_profile(self, user: str) -> Optional[EvidenceFragment]:
        url = f"https://api.fxtwitter.com/{user}"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 200 and data.get("user"):
                    u = data["user"]
                    screen_name = u.get("screen_name") or user
                    name = u.get("name") or screen_name
                    desc = u.get("description") or f"Public X profile of @{screen_name}"
                    followers = u.get("followers", 0)
                    tweets_count = u.get("tweets", 0)

                    frag = EvidenceFragment(
                        platform="twitter",
                        url=f"https://x.com/{screen_name}",
                        content=desc,
                        channel_name="twitter",
                        title=f"Profile: {name} (@{screen_name})",
                        author=f"@{screen_name}",
                        published=str(u.get("joined")) if u.get("joined") else "",
                        snippet=desc[:200],
                        content_depth="PARTIAL_CONTENT",
                        raw_metadata={
                            "followers": followers,
                            "tweets_count": tweets_count,
                            "source_tier": "SPECIALIST_MIRROR",
                            "mirror_backend": "fxtwitter"
                        }
                    )
                    return frag
        except Exception as e:
            logger.debug(f"[TrialRouter] FxTwitter profile fetch failed for {user}: {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # OVERRIDE: execute_channel_query with Zero-Auth Adapters
    # ─────────────────────────────────────────────────────────────────────────
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
        Trial channel query router handling Reddit, X/Twitter, and Facebook without auth.
        """
        # For non-social channels, route to parent NativeRouter
        if platform not in ("reddit", "twitter", "x", "facebook"):
            return super().execute_channel_query(
                platform=platform,
                query=query,
                limit=limit,
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                domain=domain,
                **kwargs
            )

        t0 = time.perf_counter()
        q_text = query_text or query
        fragments: List[EvidenceFragment] = []
        telemetry: Dict[str, Any] = {
            "platform": platform,
            "backend": "trial_noauth_router",
            "operation": f"{platform}.search",
            "status": "INITIATED",
            "fallback_used": False,
            "fallback_backend": None,
            "attempts": 1,
            "latency_ms": 0,
            "error": None,
        }

        # ── A. REDDIT TRIAL ROUTE ──
        if platform == "reddit":
            # 1. Subreddit query (e.g. "r/technology" or "technology")
            if query.startswith("r/") or (len(query.split()) == 1 and not query.startswith("site:")):
                sub_name = query.replace("r/", "").strip()
                frags = self._fetch_arctic_shift_feed(sub_name, limit=limit)
                if frags:
                    self._tag_fragments(frags, "reddit", "reddit", RetrievalMode.PUBLIC_MIRROR.value if hasattr(RetrievalMode, "PUBLIC_MIRROR") else RetrievalMode.DIRECT_API.value, "arctic-shift", None, False)
                    telemetry["status"] = "SUCCESS"
                    telemetry["backend"] = "arctic-shift-feed"
                    fragments = frags

            # 2. Keyword query fallback via Web Search Index (Bing)
            if not fragments:
                site_query = f"site:reddit.com {query}"
                try:
                    fragments = self._execute_web_search(site_query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                    if fragments:
                        self._tag_fragments(
                            fragments,
                            requested_channel="reddit",
                            actual_channel="web_search",
                            mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                            backend_id="bing-search-index",
                            fallback_reason="UNCONSTRAINED_QUERY_INDEX_FALLBACK",
                            is_authenticated=False
                        )
                        telemetry["status"] = "SUCCESS"
                        telemetry["fallback_used"] = True
                        telemetry["fallback_backend"] = "Bing Search Index"
                        telemetry["fallback_reason"] = "UNCONSTRAINED_QUERY_INDEX_FALLBACK"
                    else:
                        telemetry["status"] = "DEGRADED"
                except Exception as e_s:
                    telemetry["status"] = "FAILED"
                    telemetry["error"] = str(e_s)

        # ── B. X / TWITTER TRIAL ROUTE ──
        elif platform in ("twitter", "x"):
            # 1. Profile query (e.g. "@NASA" or "NASA")
            if query.startswith("@") or (len(query.split()) == 1 and not query.startswith("http")):
                user_clean = query.replace("@", "").strip()
                frag = self._fetch_fxtwitter_profile(user_clean)
                if frag:
                    fragments = [frag]
                    self._tag_fragments(fragments, "twitter", "twitter", RetrievalMode.DIRECT_API.value, "fxtwitter-profile", None, False)
                    telemetry["status"] = "SUCCESS"
                    telemetry["backend"] = "fxtwitter-profile"

            # 2. Keyword query fallback via Web Search Index (Bing)
            if not fragments:
                site_query = f"site:twitter.com OR site:x.com {query}"
                try:
                    fragments = self._execute_web_search(site_query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                    if fragments:
                        self._tag_fragments(
                            fragments,
                            requested_channel="twitter",
                            actual_channel="web_search",
                            mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                            backend_id="bing-search-index",
                            fallback_reason="SEARCH_INDEX_FALLBACK",
                            is_authenticated=False
                        )
                        telemetry["status"] = "SUCCESS"
                        telemetry["fallback_used"] = True
                        telemetry["fallback_backend"] = "Bing Search Index"
                        telemetry["fallback_reason"] = "SEARCH_INDEX_FALLBACK"
                    else:
                        telemetry["status"] = "DEGRADED"
                except Exception as e_s:
                    telemetry["status"] = "FAILED"
                    telemetry["error"] = str(e_s)

        # ── C. FACEBOOK TRIAL ROUTE ──
        elif platform == "facebook":
            # Direct guest HTTP is blocked by login wall; route to Search Index Fallback
            site_query = f"site:facebook.com {query}"
            try:
                fragments = self._execute_web_search(site_query, limit=limit, query_id=query_id, query_class=query_class, query_text=q_text)
                if fragments:
                    self._tag_fragments(
                        fragments,
                        requested_channel="facebook",
                        actual_channel="web_search",
                        mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                        backend_id="bing-search-index",
                        fallback_reason="PUBLIC_SEARCH_INDEX_ONLY",
                        is_authenticated=False
                    )
                    telemetry["status"] = "SUCCESS"
                    telemetry["fallback_used"] = True
                    telemetry["fallback_backend"] = "Bing Search Index"
                    telemetry["fallback_reason"] = "PUBLIC_SEARCH_INDEX_ONLY"
                else:
                    telemetry["status"] = "DEGRADED"
            except Exception as e_s:
                telemetry["status"] = "FAILED"
                telemetry["error"] = str(e_s)

        telemetry["latency_ms"] = int((time.perf_counter() - t0) * 1000)
        return fragments, telemetry

    # ─────────────────────────────────────────────────────────────────────────
    # OVERRIDE: execute_channel_read with Specialist URL Resolvers
    # ─────────────────────────────────────────────────────────────────────────
    def execute_channel_read(self, url: str, max_chars: int = 4000, **kwargs) -> Dict[str, Any]:
        """
        Trial channel document read routing X and Reddit URLs to public mirrors.
        """
        if not url:
            return {"status": "error", "error": "Empty URL provided", "url": ""}

        # 1. Check for Twitter / X Status URL
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        path = parsed.path.strip("/")

        if "twitter.com" in netloc or "x.com" in netloc:
            parts = path.split("/")
            if len(parts) >= 3 and parts[1] == "status":
                user, status_id = parts[0], parts[2]
                frag = self._fetch_fxtwitter_status(user, status_id)
                if frag and frag.content:
                    return {
                        "status": "success",
                        "title": frag.title,
                        "content": frag.content[:max_chars],
                        "markdown": f"### {frag.title}\n\n{frag.content}\n\n*Metrics: {frag.raw_metadata}*",
                        "url": url,
                        "char_count": len(frag.content),
                        "backend": "FxTwitter Mirror",
                        "fallback_used": False
                    }
            elif len(parts) == 1 and parts[0]:
                frag = self._fetch_fxtwitter_profile(parts[0])
                if frag and frag.content:
                    return {
                        "status": "success",
                        "title": frag.title,
                        "content": frag.content[:max_chars],
                        "markdown": f"### {frag.title}\n\n{frag.content}",
                        "url": url,
                        "char_count": len(frag.content),
                        "backend": "FxTwitter Profile Mirror",
                        "fallback_used": False
                    }

        # 2. Check for Reddit Post URL
        if "reddit.com" in netloc and "/comments/" in path:
            parts = path.split("/")
            # /r/subreddit/comments/post_id/slug
            try:
                comm_idx = parts.index("comments")
                if len(parts) > comm_idx + 1:
                    post_id = parts[comm_idx + 1]
                    frag = self._fetch_arctic_shift_post(post_id)
                    if frag and frag.content:
                        return {
                            "status": "success",
                            "title": frag.title,
                            "content": frag.content[:max_chars],
                            "markdown": f"### {frag.title}\n**Author**: {frag.author}\n\n{frag.content}",
                            "url": url,
                            "char_count": len(frag.content),
                            "backend": "Arctic Shift Mirror",
                            "fallback_used": False
                        }
            except Exception:
                pass

        # 3. Default back to parent NativeRouter read (Jina Reader / legacy scraper)
        return super().execute_channel_read(url=url, max_chars=max_chars, **kwargs)
