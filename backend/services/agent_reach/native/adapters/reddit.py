"""
Aegis Protocol — Reddit Zero-Auth Specialist Adapter (Arctic Shift)
===================================================================
Acquires Reddit posts, comments, and subreddit feeds via the Arctic Shift
zero-auth public mirror.
Avoids doomed unauthenticated Reddit JSON / OAuth API failures.
Enforces caching via SocialCache and exponential backoff on retryable 422/429/503.
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.agent_reach.channels import (
    CandidateSource,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.agent_reach.native.adapters.base import PlatformAdapter
from backend.services.agent_reach.native.cache import social_cache
from backend.services.agent_reach.native.source_discovery import extract_reddit_source
from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)

ARCTIC_SHIFT_BASE = "https://arctic-shift.photon-reddit.com/api"


class RedditAdapter(PlatformAdapter):
    """
    Zero-auth Reddit acquisition adapter via Arctic Shift public mirror.
    """

    @property
    def platform(self) -> str:
        return "reddit"

    @property
    def backend_id(self) -> str:
        return "arctic_shift"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        return candidate.platform.lower() == "reddit" or "reddit.com" in url or "redd.it" in url

    def _fetch_from_mirror(self, endpoint: str, params: Dict[str, str], max_retries: int = 2) -> Optional[Dict[str, Any]]:
        query_str = urllib.parse.urlencode(params)
        url = f"{ARCTIC_SHIFT_BASE}/{endpoint}?{query_str}"
        cache_key = f"arctic_shift:{url}"

        cached = social_cache.get(cache_key)
        if cached:
            return cached

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
                "Accept": "application/json",
            },
        )

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=7.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    social_cache.set(cache_key, data)
                    return data
            except urllib.error.HTTPError as e:
                if e.code in (422, 429, 503) and attempt < max_retries - 1:
                    time.sleep(0.6 * (attempt + 1))
                    continue
                logger.debug(f"[RedditAdapter] Arctic Shift HTTP {e.code} for {endpoint}: {e}")
                break
            except Exception as e:
                logger.debug(f"[RedditAdapter] Arctic Shift error for {endpoint}: {e}")
                break

        return None

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        target_url = candidate.canonical_url or candidate.url

        # 1. SSRF Gate
        is_safe, reason = validate_url_safe(target_url)
        if not is_safe:
            return FetchedDocument(
                url=target_url,
                status="BLOCKED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
                failure_reason=f"SSRF validation failed: {reason}",
            )

        t0 = time.perf_counter()
        disc = extract_reddit_source(target_url)
        raw_json_str = ""
        status = "FAILED"
        err_msg = None

        if disc and disc.source_type == "post" and disc.external_id:
            clean_id = disc.external_id.replace("t3_", "").strip()
            data = self._fetch_from_mirror("posts/ids", {"ids": clean_id})
            if data and data.get("data"):
                raw_json_str = json.dumps(data.get("data", [])[0])
                status = "SUCCESS"
            else:
                err_msg = "Post not found or empty response from Arctic Shift"
        elif disc and disc.source_type == "subreddit" and disc.subreddit:
            data = self._fetch_from_mirror("posts/search", {"subreddit": disc.subreddit, "limit": "5"})
            if data and data.get("data"):
                raw_json_str = json.dumps(data.get("data", []))
                status = "SUCCESS"
            else:
                err_msg = f"Subreddit {disc.subreddit} not found or empty"
        else:
            # Fallback to query search via Arctic Shift
            q = request.query or request.entity or target_url
            data = self._fetch_from_mirror("posts/search", {"query": q, "limit": "5"})
            if data and data.get("data"):
                raw_json_str = json.dumps(data.get("data", []))
                status = "SUCCESS"
            else:
                err_msg = "Arctic Shift search returned no records"

        lat = int((time.perf_counter() - t0) * 1000)
        return FetchedDocument(
            url=target_url,
            status=status,
            backend_id=self.backend_id,
            retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
            raw_content=raw_json_str,
            latency_ms=lat,
            failure_reason=err_msg,
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        try:
            parsed = json.loads(document.raw_content)
        except Exception:
            return []

        posts = [parsed] if isinstance(parsed, dict) else parsed
        fragments: List[EvidenceFragment] = []

        for p in posts:
            if not isinstance(p, dict):
                continue
            title = p.get("title", "")
            selftext = p.get("selftext", "") or ""
            author = p.get("author", "unknown_redditor")
            sub = p.get("subreddit", "")
            pid = p.get("id", "")
            created_utc = p.get("created_utc")
            pub_date = datetime.fromtimestamp(created_utc, timezone.utc).isoformat() if created_utc else datetime.now(timezone.utc).isoformat()
            post_url = f"https://reddit.com/r/{sub}/comments/{pid}" if sub and pid else document.url

            content = f"Title: {title}\nSubreddit: r/{sub}\nAuthor: u/{author}\n\n{selftext}"
            snippet = selftext[:280] or title

            depth = "FULL_ARTICLE" if len(selftext) > 300 else ("PARTIAL_CONTENT" if len(selftext) > 50 else "SNIPPET")

            frag = EvidenceFragment(
                platform=self.platform,
                title=title,
                content=content,
                url=post_url,
                author=f"u/{author}",
                published=pub_date,
                snippet=snippet,
                score=candidate.semantic_score or 1.0,
                retrieval_method="agent_reach",
                channel_name="reddit",
                content_depth=depth,
                query_id=request.request_id,
                query_class=request.task_type,
                query_text=request.query,
                retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
                native_backend_id=self.backend_id,
                is_authenticated=False,
                raw_metadata={
                    "post_id": pid,
                    "subreddit": sub,
                    "score": p.get("score", 0),
                    "num_comments": p.get("num_comments", 0),
                },
            )
            fragments.append(frag)

        return fragments
