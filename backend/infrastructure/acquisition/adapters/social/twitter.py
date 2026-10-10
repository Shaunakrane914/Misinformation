"""
Aegis Protocol — X / Twitter Zero-Auth Specialist Adapter (FxTwitter)
=====================================================================
Acquires X/Twitter status updates and profile metadata via the FxTwitter
zero-auth public mirror (https://api.fxtwitter.com).
FxTwitter is NOT a general keyword search engine. For keyword queries, discovery
occurs via search index first to identify concrete status URLs, followed by
enrichment here.
"""

import json
import logging
import os
import time
import urllib.error
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
from backend.infrastructure.acquisition.adapters.base import PlatformAdapter
from backend.services.agent_reach.native.cache import social_cache
from backend.services.agent_reach.native.normalizer import native_normalizer
from backend.services.agent_reach.native.source_discovery import extract_x_source
from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)

DEFAULT_HTTP_TIMEOUT = float(os.getenv("AEGIS_HTTP_TIMEOUT", "25.0"))
FXTWITTER_BASE = "https://api.fxtwitter.com"


def fetch_fxtwitter_status(
    user: str,
    status_id: str,
    cache_get: Optional[Any] = None,
    cache_set: Optional[Any] = None,
) -> Optional[EvidenceFragment]:
    """Fetch public tweet status via FxTwitter API with retry on 429/503."""
    clean_sid = status_id.strip()
    cache_key = f"twitter:status:{clean_sid}"
    get_c = cache_get or social_cache.get
    set_c = cache_set or social_cache.set

    cached = get_c(cache_key)
    if cached:
        return cached

    handle = user if (user and user not in ("i", "status")) else "status"
    if handle == "status":
        url = f"{FXTWITTER_BASE}/status/{clean_sid}"
    else:
        url = f"{FXTWITTER_BASE}/{handle}/status/{clean_sid}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
            "Accept": "application/json",
        },
    )
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=DEFAULT_HTTP_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 200 and data.get("tweet"):
                    frag = native_normalizer.normalize_fxtwitter_tweet(data["tweet"])
                    if frag:
                        set_c(cache_key, frag)
                        return frag
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt == 0:
                time.sleep(0.5)
                continue
            logger.debug(f"[TwitterAdapter] FxTwitter status fetch failed for {user}/{status_id}: {e}")
            break
        except Exception as e:
            logger.debug(f"[TwitterAdapter] FxTwitter status fetch error: {e}")
            break
    return None


def fetch_fxtwitter_profile(
    user: str,
    cache_get: Optional[Any] = None,
    cache_set: Optional[Any] = None,
) -> Optional[EvidenceFragment]:
    """Fetch public user profile via FxTwitter API."""
    clean_user = user.replace("@", "").strip()
    cache_key = f"twitter:profile:{clean_user.lower()}"
    get_c = cache_get or social_cache.get
    set_c = cache_set or social_cache.set

    cached = get_c(cache_key)
    if cached:
        return cached

    url = f"{FXTWITTER_BASE}/{clean_user}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
            "Accept": "application/json",
        },
    )
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=DEFAULT_HTTP_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 200 and data.get("user"):
                    frag = native_normalizer.normalize_fxtwitter_profile(data["user"])
                    if frag:
                        set_c(cache_key, frag)
                        return frag
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt == 0:
                time.sleep(0.5)
                continue
            logger.debug(f"[TwitterAdapter] FxTwitter profile fetch failed for {clean_user}: {e}")
            break
        except Exception as e:
            logger.debug(f"[TwitterAdapter] FxTwitter profile fetch error: {e}")
            break
    return None


class TwitterAdapter(PlatformAdapter):
    """
    Zero-auth X / Twitter acquisition adapter via FxTwitter public mirror.
    """

    @property
    def platform(self) -> str:
        return "twitter"

    @property
    def backend_id(self) -> str:
        return "fxtwitter"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        return candidate.platform.lower() in ("twitter", "x") or "x.com" in url or "twitter.com" in url

    def _fetch_from_fxtwitter(self, path: str, max_retries: int = 2) -> Optional[Dict[str, Any]]:
        clean_path = path.lstrip("/")
        url = f"{FXTWITTER_BASE}/{clean_path}"
        cache_key = f"fxtwitter:{url}"

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
                if e.code in (429, 503) and attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                logger.debug(f"[TwitterAdapter] FxTwitter HTTP {e.code} for {clean_path}: {e}")
                break
            except Exception as e:
                logger.debug(f"[TwitterAdapter] FxTwitter error for {clean_path}: {e}")
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
        disc = extract_x_source(target_url)
        raw_json_str = ""
        status = "FAILED"
        err_msg = None

        if disc and disc.source_type == "status" and disc.external_id:
            user = disc.handle or "i"
            data = self._fetch_from_fxtwitter(f"{user}/status/{disc.external_id}")
            if data and (data.get("tweet") or data.get("code") == 200):
                raw_json_str = json.dumps(data)
                status = "SUCCESS"
            else:
                err_msg = f"Status {disc.external_id} not found on FxTwitter"
        elif disc and disc.source_type == "profile" and disc.handle:
            data = self._fetch_from_fxtwitter(disc.handle)
            if data and (data.get("user") or data.get("code") == 200):
                raw_json_str = json.dumps(data)
                status = "SUCCESS"
            else:
                err_msg = f"Profile @{disc.handle} not found on FxTwitter"
        else:
            err_msg = "X URL is not a concrete status or profile URL"

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
            data = json.loads(document.raw_content)
        except Exception:
            return []

        tweet = data.get("tweet") or {}
        user = tweet.get("author", {}) or data.get("user", {})

        author_name = user.get("name") or user.get("screen_name") or "X User"
        handle = user.get("screen_name") or "unknown"
        text = tweet.get("text", "") or user.get("description", "")
        title = f"Post by @{handle}: {text[:70]}..." if text else f"@{handle} on X"
        pub_date = tweet.get("created_at") or datetime.now(timezone.utc).isoformat()

        content = f"Author: {author_name} (@{handle})\n\n{text}"
        snippet = text[:280]

        frag = EvidenceFragment(
            platform=self.platform,
            title=title,
            content=content,
            url=tweet.get("url") or document.url,
            author=f"@{handle}",
            published=str(pub_date),
            snippet=snippet,
            score=candidate.semantic_score or 1.0,
            retrieval_method="agent_reach",
            channel_name="twitter",
            content_depth="SNIPPET" if len(text) < 150 else "PARTIAL_CONTENT",
            query_id=request.request_id,
            query_class=request.task_type,
            query_text=request.query,
            retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
            native_backend_id=self.backend_id,
            is_authenticated=False,
            raw_metadata={
                "likes": tweet.get("likes", 0),
                "retweets": tweet.get("retweets", 0),
                "replies": tweet.get("replies", 0),
            },
        )
        return [frag]
