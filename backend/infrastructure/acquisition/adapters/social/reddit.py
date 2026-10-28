"""
Aegis Protocol — Reddit Zero-Auth Specialist Adapter (Arctic Shift)
===================================================================
Acquires Reddit posts, comments, and subreddit feeds via the Arctic Shift
zero-auth public mirror (https://arctic-shift.photon-reddit.com/api).
Avoids doomed unauthenticated Reddit JSON / OAuth API failures.
Enforces caching via SocialCache and exponential backoff on retryable 422/429/503.
"""

import json
import hashlib
import copy
import html
import logging
import os
import re
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
from backend.infrastructure.acquisition.adapters.base import PlatformAdapter
from backend.services.agent_reach.native.cache import social_cache
from backend.services.agent_reach.native.normalizer import native_normalizer
from backend.services.agent_reach.native.source_discovery import extract_reddit_source
from backend.services.url_validator import validate_url_safe
from backend.infrastructure.acquisition.network.http import decode_bounded_http_body, fetch_public_http, ProviderHTTPError
from backend.infrastructure.acquisition.network.budget import remaining_timeout

logger = logging.getLogger(__name__)

DEFAULT_HTTP_TIMEOUT = float(os.getenv("AEGIS_HTTP_TIMEOUT", "25.0"))
ARCTIC_SHIFT_BASE = "https://arctic-shift.photon-reddit.com/api"


def fetch_arctic_shift_posts_batch(
    post_ids: List[str],
    query_id: str = "",
    query_class: str = "",
    query_text: str = "",
    cache_get: Optional[Any] = None,
    cache_set: Optional[Any] = None,
) -> List[EvidenceFragment]:
    """
    Batch Reddit submissions lookup via Arctic Shift REST API.
    Deduplicates post IDs, checks cache, and batches requests in chunks of up to 25.
    Applies exponential backoff on retryable 422/429/503 responses.
    """
    if not post_ids:
        return []

    clean_ids = list(dict.fromkeys([
        pid.replace("t3_", "").strip()
        for pid in post_ids
        if pid and pid.replace("t3_", "").strip()
    ]))

    results: List[EvidenceFragment] = []
    to_fetch: List[str] = []

    get_c = cache_get or social_cache.get
    set_c = cache_set or social_cache.set

    for pid in clean_ids:
        cached = get_c(f"reddit:post:{pid}")
        if cached:
            cached_copy = copy.deepcopy(cached)
            cached_copy.raw_metadata.setdefault("transport", {})["network_observed_this_attempt"] = False
            cached_copy.raw_metadata["transport"]["cache_status"] = "CACHE_HIT"
            results.append(cached_copy)
        else:
            to_fetch.append(pid)

    if not to_fetch:
        return results

    chunk_size = 25
    for i in range(0, len(to_fetch), chunk_size):
        chunk = to_fetch[i : i + chunk_size]
        url = f"{ARCTIC_SHIFT_BASE}/posts/ids?ids={','.join(chunk)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
                "Accept": "application/json",
            },
        )
        data = None
        transport = None
        for attempt in range(2):
            try:
                request_started = time.perf_counter()
                with urllib.request.urlopen(req, timeout=remaining_timeout(3.0)) as resp:
                    raw_body = resp.read()
                    data = json.loads(raw_body.decode("utf-8"))
                    transport = {
                        "network_observed_this_attempt": True,
                        "endpoint": url,
                        "http_status": getattr(resp, "status", None),
                        "content_type": resp.headers.get("Content-Type") if getattr(resp, "headers", None) else None,
                        "raw_body_bytes": len(raw_body),
                        "network_latency_ms": int((time.perf_counter() - request_started) * 1000),
                        "cache_status": "CACHE_MISS",
                        "rate_limit_remaining": resp.headers.get("X-Ratelimit-Remaining") if getattr(resp, "headers", None) else None,
                    }
                    break
            except urllib.error.HTTPError as e:
                if e.code in (422, 429, 503) and attempt == 0:
                    time.sleep(0.8)
                    continue
                logger.debug(f"[RedditAdapter] Arctic Shift batch lookup HTTP {e.code}: {e}")
                break
            except Exception as e:
                logger.debug(f"[RedditAdapter] Arctic Shift batch lookup error: {e}")
                break

        if data:
            posts = data.get("data", [])
            if posts:
                frags = native_normalizer.normalize_arctic_shift_posts(
                    posts, query_id=query_id, query_class=query_class, query_text=query_text
                )
                for f in frags:
                    if transport:
                        f.raw_metadata["transport"] = dict(transport)
                    pid = f.raw_metadata.get("post_id") or ""
                    if pid:
                        set_c(f"reddit:post:{pid}", f)
                results.extend(frags)

    return results


def fetch_arctic_shift_post(
    post_id: str,
    cache_get: Optional[Any] = None,
    cache_set: Optional[Any] = None,
) -> Optional[EvidenceFragment]:
    """Direct Reddit submission lookup via Arctic Shift REST API."""
    frags = fetch_arctic_shift_posts_batch([post_id], cache_get=cache_get, cache_set=cache_set)
    return frags[0] if frags else None


def fetch_arctic_shift_search(
    query: str = "",
    subreddit: str = "",
    author: str = "",
    limit: int = 5,
    query_id: str = "",
    query_class: str = "",
    query_text: str = "",
    cache_get: Optional[Any] = None,
    cache_set: Optional[Any] = None,
) -> List[EvidenceFragment]:
    """Search Reddit submissions via Arctic Shift REST API."""
    cache_key = f"reddit:search:{subreddit}:{author}:{query}:{limit}"
    get_c = cache_get or social_cache.get
    set_c = cache_set or social_cache.set

    cached = get_c(cache_key)
    if cached:
        cached_copy = copy.deepcopy(cached)
        for fragment in cached_copy:
            fragment.raw_metadata.setdefault("transport", {})["network_observed_this_attempt"] = False
            fragment.raw_metadata["transport"]["cache_status"] = "CACHE_HIT"
        return cached_copy

    params = {"limit": str(min(limit, 25)), "sort": "desc"}
    if subreddit:
        params["subreddit"] = subreddit
    if author:
        params["author"] = author
    if query:
        params["query"] = query

    url = f"{ARCTIC_SHIFT_BASE}/posts/search?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
            "Accept": "application/json",
        },
    )
    try:
        request_started = time.perf_counter()
        with urllib.request.urlopen(req, timeout=remaining_timeout(3.0)) as resp:
            raw_body = resp.read()
            data = json.loads(raw_body.decode("utf-8"))
            posts = data.get("data", [])
            frags = native_normalizer.normalize_arctic_shift_posts(
                posts, query_id=query_id, query_class=query_class, query_text=query_text or query
            )
            if frags:
                transport = {
                    "network_observed_this_attempt": True,
                    "endpoint": url,
                    "http_status": getattr(resp, "status", None),
                    "content_type": resp.headers.get("Content-Type") if getattr(resp, "headers", None) else None,
                    "raw_body_bytes": len(raw_body),
                    "network_latency_ms": int((time.perf_counter() - request_started) * 1000),
                    "cache_status": "CACHE_MISS",
                    "rate_limit_remaining": resp.headers.get("X-Ratelimit-Remaining") if getattr(resp, "headers", None) else None,
                }
                for fragment in frags:
                    fragment.raw_metadata["transport"] = dict(transport)
                set_c(cache_key, frags)
                return frags
    except Exception as e:
        logger.debug(f"[RedditAdapter] Arctic Shift search failed for params {params}: {e}")
    return []


def fetch_arctic_shift_comments(
    post_id: str,
    limit: int = 10,
    query_id: str = "",
    query_class: str = "",
    query_text: str = "",
    cache_get: Optional[Any] = None,
    cache_set: Optional[Any] = None,
) -> List[EvidenceFragment]:
    """Fetch comments for a known Reddit submission via Arctic Shift REST API."""
    clean_pid = post_id.replace("t3_", "").strip()
    if not re.fullmatch(r"[a-z0-9]{1,12}", clean_pid, re.I):
        return []
    limit = min(50, max(0, int(limit)))
    if not limit:
        return []
    link_id = f"t3_{clean_pid}"
    cache_key = f"reddit:comments:{clean_pid}:{limit}"
    get_c = cache_get or social_cache.get
    set_c = cache_set or social_cache.set

    cached = get_c(cache_key)
    if cached:
        cached_copy = copy.deepcopy(cached)
        for fragment in cached_copy:
            fragment.raw_metadata.setdefault("transport", {})["network_observed_this_attempt"] = False
            fragment.raw_metadata["transport"]["cache_status"] = "CACHE_HIT"
        return cached_copy

    url = f"{ARCTIC_SHIFT_BASE}/comments/search?link_id={link_id}&limit={min(limit, 50)}&sort=desc"
    try:
        response = fetch_public_http(url, timeout=3.0, max_bytes=1_000_000, headers={
            "User-Agent": "AegisAgentReach/3.0", "Accept": "application/json", "Accept-Encoding": "identity"})
        data = json.loads(decode_bounded_http_body(response).decode("utf-8"))
        comments = [comment for comment in data.get("data", [])[:limit]
                    if isinstance(comment, dict) and comment.get("link_id") == link_id]
        frags = native_normalizer.normalize_arctic_shift_comments(
            comments, query_id=query_id, query_class=query_class, query_text=query_text)
        if frags:
            transport = {"network_observed_this_attempt": True, "endpoint": response.endpoint,
                         "http_status": response.status_code, "content_type": response.content_type,
                         "raw_body_bytes": len(response.body),
                         "raw_body_sha256": hashlib.sha256(response.body).hexdigest(),
                         "network_latency_ms": response.latency_ms, "cache_status": "CACHE_MISS"}
            for fragment in frags:
                fragment.raw_metadata["transport"] = dict(transport)
            set_c(cache_key, frags)
            return frags
    except Exception as e:
        logger.debug(f"[RedditAdapter] Arctic Shift comments fetch failed for {clean_pid}: {e}")
    return []


def fetch_reddit_subreddit_rss(
    subreddit: str,
    limit: int = 25,
    query_id: str = "",
    query_class: str = "",
    query_text: str = "",
    cache_get: Optional[Any] = None,
    cache_set: Optional[Any] = None,
) -> List[EvidenceFragment]:
    """
    Acquire live Reddit submissions directly from public Subreddit RSS/Atom feed.
    Public Atom syndication when enabled; access denials are terminal.
    Governed by AEGIS_REDDIT_RSS_ENABLED feature flag and records sunset deprecation.
    """
    # 1. Feature Flag & Shutdown Governance Check
    is_rss_enabled = os.getenv("AEGIS_REDDIT_RSS_ENABLED", "true").strip().lower() in ("true", "1", "yes")
    if not is_rss_enabled:
        logger.info(f"[RedditAdapter] Subreddit RSS disabled via feature flag AEGIS_REDDIT_RSS_ENABLED=false")
        return []

    clean_sub = re.sub(r"^/?r/", "", subreddit.strip().rstrip("/"))
    if not re.fullmatch(r"[A-Za-z0-9_]{3,21}", clean_sub) or limit <= 0:
        return []
    limit = min(100, limit)

    cache_key = f"reddit:rss:{clean_sub.lower()}:{limit}"
    get_c = cache_get or social_cache.get
    set_c = cache_set or social_cache.set

    cached = get_c(cache_key)
    if isinstance(cached, dict) and cached.get('failure_status') in {401, 403, 429}:
        if cached.get('expires_at', 0) > time.time():
            raise ProviderHTTPError('Cached Reddit RSS access failure', endpoint='',
                status_code=cached['failure_status'], network_observed=False, attempts=0,
                retry_after_seconds=cached.get('retry_after_seconds'))
        cached = None
    if cached is not None:
        if not cached:
            return []
        cached_copy = copy.deepcopy(cached)
        for fragment in cached_copy:
            fragment.raw_metadata.setdefault("transport", {})["network_observed_this_attempt"] = False
            fragment.raw_metadata["transport"]["cache_status"] = "CACHE_HIT"
        return cached_copy

    url = f"https://www.reddit.com/r/{clean_sub}/.rss"
    timeout = DEFAULT_HTTP_TIMEOUT
    headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
        }
    fragments: List[EvidenceFragment] = []
    try:
        import feedparser
        request_started = time.perf_counter()
        response = fetch_public_http(url, headers=headers, timeout=remaining_timeout(min(5.0, timeout)),
                                     max_bytes=1_000_000, max_attempts=1, max_redirects=0)
        if response.status_code == 200:
            raw_xml = decode_bounded_http_body(response, max_bytes=1_000_000)
            opening = raw_xml[:1000]
            if (not re.search(br'<(?:rss|feed)(?:\s|>)', opening, re.I)
                    and re.search(br'401 unauthorized|403 forbidden|access denied|too many requests|verify you are human', opening, re.I)):
                raise ProviderHTTPError('Reddit RSS returned an explicit access denial', endpoint=url,
                    status_code=429 if b'too many requests' in opening.lower() else 403, network_observed=True)
            transport = {
                "network_observed_this_attempt": True,
                "endpoint": url,
                "http_status": response.status_code,
                "content_type": response.content_type,
                "raw_body_bytes": len(raw_xml),
                "network_latency_ms": int((time.perf_counter() - request_started) * 1000),
                "cache_status": "CACHE_MISS",
                "rate_limit_remaining": response.headers.get("X-Ratelimit-Remaining"),
            }
            feed = feedparser.parse(raw_xml)
            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                link = entry.get("link", f"https://www.reddit.com/r/{clean_sub}")
                author = entry.get("author", f"/r/{clean_sub}")
                published = entry.get("published", "")
                summary = entry.get("summary", "") or title

                clean_text = html.unescape(re.sub(r"<[^>]+>", " ", summary))
                clean_text = re.sub(
                    r"\bsubmitted\s+by\s+\S+(?:\s+to\s+\S+)?\s*",
                    " ", clean_text, flags=re.IGNORECASE,
                )
                clean_text = re.sub(r"\[(?:link|comments)\]", " ", clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r"\s+", " ", clean_text).strip(" -|")
                content = f"Subreddit: r/{clean_sub}\nTitle: {title}\nAuthor: {author}\nLink: {link}\n\nContent:\n{clean_text}"

                frag = EvidenceFragment(
                    platform="reddit",
                    title=f"[r/{clean_sub}] {title}",
                    content=content,
                    url=link,
                    author=author,
                    published=published or "",
                    snippet=clean_text[:300] if clean_text else title,
                    score=65.0,
                    retrieval_method="reddit_subreddit_rss",
                    retrieval_mode=RetrievalMode.DIRECT_API.value,
                    native_backend_id="reddit-rss",
                    channel_name="reddit",
                    content_depth="FEED_ENTRY_SUMMARY",
                    query_id=query_id,
                    query_class=query_class,
                    query_text=query_text or f"r/{clean_sub}",
                    requested_channel="reddit",
                    actual_retrieval_channel="reddit",
                    is_authenticated=False,
                    raw_metadata={
                        "backend": "reddit-rss",
                        "subreddit": clean_sub,
                        "source_tier": "SPECIALIST_API",
                        "content_type": "rss_feed_entry",
                        "rss_sunset_announced": "2026-11-13",
                        "deprecation_status": "OPERATIONAL",
                        "transport": dict(transport),
                        "usable_body_chars": len(clean_text),
                    }
                )
                fragments.append(frag)
            set_c(cache_key, fragments)
            return fragments
    except ProviderHTTPError as error:
        if error.status_code in {401, 403, 429}:
            set_c(cache_key, {'failure_status': error.status_code,
                'retry_after_seconds': error.retry_after_seconds,
                'expires_at': time.time() + min(300.0, max(1.0, error.retry_after_seconds or 30.0))})
        raise  # Never turn an access/validation failure into an empty successful feed.
    except Exception as e:
        from backend.services.research.source_registry import SourcePermissionError
        if isinstance(e, SourcePermissionError):
            raise
        logger.debug(f"[RedditAdapter] Subreddit RSS fetch failed for r/{clean_sub}: {e}")
    return fragments


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
                with urllib.request.urlopen(req, timeout=remaining_timeout(5.0)) as resp:
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
                author=f"u/{author}" if not author.startswith("u/") else author,
                published=pub_date,
                snippet=snippet,
                score=float(p.get("score") or 50.0),
                retrieval_method="arctic_shift_mirror",
                retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
                native_backend_id=self.backend_id,
                channel_name="reddit",
                content_depth=depth,
                is_authenticated=False,
                query_id=request.request_id,
                query_text=request.query or request.entity,
                raw_metadata={
                    "source_tier": "TIER_2_OFFICIAL_SOCIAL",
                    "honest_disclosure": "Public community discussion acquired via Arctic Shift zero-auth mirror",
                    "num_comments": p.get("num_comments", 0),
                    "subreddit": sub,
                    "external_id": pid,
                    "score": p.get("score", 0),
                },
            )
            fragments.append(frag)

        return fragments
