"""Bounded public technical-discussion sources; not authoritative truth feeds.

HN discovery uses the disclosed Algolia index, then reads original items from
the official Firebase API. Stack Exchange uses body-inclusive public API reads.
No account access, scraping bypass, arbitrary endpoint or paid credential.
"""
from __future__ import annotations

import json
import re
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlsplit

from bs4 import BeautifulSoup

from backend.infrastructure.acquisition.network.http import decode_bounded_http_body, fetch_public_http
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode

_backoff_until = 0.0
_backoff_lock = threading.Lock()
_cache = OrderedDict()


def _plain(value):
    soup = BeautifulSoup(value if isinstance(value, str) else "", "html.parser")
    for node in soup(["script", "style"]):
        node.decompose()
    return soup.get_text(" ", strip=True)


def _date(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value, timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            pass
    return ""


def _json(url, observations, fetcher):
    cacheable = url.startswith("https://api.stackexchange.com/") and fetcher is fetch_public_http
    if cacheable:
        with _backoff_lock:
            cached = _cache.get(url)
            if cached and time.monotonic() - cached[0] < 60:
                observations.append({"endpoint": url, "network_observed_this_attempt": False,
                                     "cache_status": "HIT"})
                return cached[1]
    response = fetcher(url, timeout=5.0, max_bytes=1_000_000,
                       headers={"Accept": "application/json", "Accept-Encoding": "identity",
                                "User-Agent": "AegisProtocol Research/1.0"})
    observations.append({
        "endpoint": response.endpoint, "http_status": response.status_code,
        "network_observed_this_attempt": True, "cache_status": "MISS",
        "latency_ms": response.latency_ms,
    })
    payload = json.loads(decode_bounded_http_body(response).decode("utf-8"))
    if cacheable:
        with _backoff_lock:
            _cache[url] = (time.monotonic(), payload)
            _cache.move_to_end(url)
            while len(_cache) > 64:
                _cache.popitem(last=False)
    return payload


def acquire_community(platform, query, limit=3, *, operation="search", page=1, include_comments=False, http_fetcher=None):
    """Return fragments plus all observed requests; exceptions keep safe HTTP semantics."""
    global _backoff_until
    fetcher = http_fetcher or fetch_public_http
    limit = min(5, max(0, int(limit)))
    page = min(5, max(1, int(page)))
    telemetry = {"status": "EMPTY_RESULT", "transport_observations": [], "scope": "BOUNDED_SAMPLE"}
    if not limit:
        return [], telemetry
    if platform not in {"hackernews", "stackexchange"} or operation not in {"search", "read"}:
        return [], {**telemetry, "status": "UNSUPPORTED"}
    observations = telemetry["transport_observations"]
    fragments = []
    query = str(query).strip()[:2000]
    parsed = urlsplit(query)
    if platform == "hackernews":
        if operation == "read":
            if query.isdigit():
                ids = [query]
            elif parsed.scheme == "https" and parsed.hostname == "news.ycombinator.com" and parsed.path == "/item":
                ids = parse_qs(parsed.query).get("id", [])[:1]
            else:
                return [], {**telemetry, "status": "INVALID_TARGET"}
            ids = [value for value in ids if re.fullmatch(r"[0-9]{1,12}", value)]
            if not ids:
                return [], {**telemetry, "status": "INVALID_TARGET"}
        else:
            index = _json("https://hn.algolia.com/api/v1/search?" + urlencode({
                "query": query, "tags": "story", "hitsPerPage": limit, "page": page - 1,
            }), observations, fetcher)
            ids = [str(hit.get("objectID", "")) for hit in index.get("hits", [])[:limit]
                   if isinstance(hit, dict) and re.fullmatch(r"[0-9]{1,12}", str(hit.get("objectID", "")))]
            telemetry["discovery_backend"] = "Algolia HN search index"
        for item_id in ids:
            item = _json(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", observations, fetcher)
            if not isinstance(item, dict) or item.get("deleted") or item.get("dead"):
                continue
            # The requested ID, not a payload-controlled URL, identifies the observed item.
            if str(item.get("id")) != item_id:
                continue
            body = _plain(item.get("text"))
            fragments.append(EvidenceFragment(
                platform="Hacker News", channel_name="hackernews",
                title=_plain(item.get("title")), content=body[:12000], snippet=body[:350],
                url=f"https://news.ycombinator.com/item?id={item_id}",
                source_id=f"src_hn_{item_id}", evidence_id=f"ev_hn_{item_id}",
                author=item.get("by") if isinstance(item.get("by"), str) else "",
                published=_date(item.get("time")),
                content_depth="PARTIAL_CONTENT" if body else "METADATA",
                retrieval_mode=RetrievalMode.DIRECT_API.value, native_backend_id="hn-firebase-api",
                raw_metadata={"score": item.get("score"), "comment_count": item.get("descendants"),
                              "transport": dict(observations[-1]),
                              "sampled_reply_ids": item.get("kids", [])[:10],
                              "referenced_url": item.get("url"), "referenced_url_acquired": False,
                              "truncated": len(body) > 12000, "pagination_complete": None},
            ))
            if include_comments is True:
                for child in (item.get("kids") or [])[:2]:
                    if not isinstance(child, int) or isinstance(child, bool) or child <= 0:
                        continue
                    try:
                        reply = _json(f"https://hacker-news.firebaseio.com/v0/item/{child}.json", observations, fetcher)
                    except Exception as error:
                        telemetry.setdefault("followup_failures", []).append(type(error).__name__)
                        continue
                    if not isinstance(reply, dict) or reply.get("deleted") or reply.get("dead"):
                        continue
                    if reply.get("id") != child or reply.get("parent") != int(item_id):
                        continue
                    text = _plain(reply.get("text"))
                    if not text:
                        continue
                    fragments.append(EvidenceFragment(
                        platform="Hacker News", channel_name="hackernews", title=f"Observed reply to item {item_id}",
                        content=text[:12000], snippet=text[:350], url=f"https://news.ycombinator.com/item?id={child}",
                        source_id=f"src_hn_{child}", evidence_id=f"ev_hn_{child}",
                        author=reply.get("by") if isinstance(reply.get("by"), str) else "", published=_date(reply.get("time")),
                        content_depth="COMMENT", retrieval_mode=RetrievalMode.DIRECT_API.value,
                        native_backend_id="hn-firebase-api",
                        raw_metadata={"parent_id": int(item_id), "truncated": len(text) > 12000,
                                      "transport": dict(observations[-1]),
                                      "discussion_completeness": "BOUNDED_TWO_DIRECT_REPLIES"},
                    ))
    else:
        # This adapter's source is explicitly Stack Overflow, not all SE sites.
        with _backoff_lock:
            remaining = max(0, _backoff_until - time.monotonic())
        if remaining:
            return [], {**telemetry, "status": "RATE_LIMITED", "retry_after_seconds": remaining,
                        "error": "Stack Exchange rate limit backoff active", "attempts": 0}
        params = {"site": "stackoverflow", "filter": "withbody", "pagesize": limit, "page": page}
        if operation == "read":
            if query.isdigit():
                item_id = query
            elif parsed.scheme == "https" and parsed.hostname == "stackoverflow.com":
                match = re.match(r"/(?:questions|q)/(\d+)(?:/|$)", parsed.path)
                item_id = match.group(1) if match else ""
            else:
                item_id = ""
            if not re.fullmatch(r"[0-9]{1,12}", item_id):
                return [], {**telemetry, "status": "INVALID_TARGET"}
            path = f"questions/{item_id}"
        else:
            path = "search/advanced"
            params.update(q=query, order="desc", sort="relevance")
        data = _json("https://api.stackexchange.com/2.3/" + path + "?" + urlencode(params), observations, fetcher)
        backoff = data.get("backoff")
        if isinstance(backoff, (int, float)) and backoff > 0:
            with _backoff_lock:
                _backoff_until = max(_backoff_until, time.monotonic() + min(backoff, 86400))
            telemetry["retry_after_seconds"] = backoff
        telemetry.update(has_more=data.get("has_more"), quota_remaining=data.get("quota_remaining"))
        if data.get("error_id") or data.get("quota_remaining") == 0:
            return [], {**telemetry, "status": "RATE_LIMITED" if backoff or data.get("quota_remaining") == 0 else "FAILED",
                        "error": "Stack Exchange rate limit or provider error"}
        for item in data.get("items", [])[:limit]:
            if not isinstance(item, dict) or not isinstance(item.get("question_id"), int):
                continue
            body = _plain(item.get("body"))
            owner = item.get("owner") or {}
            fragments.append(EvidenceFragment(
                platform="Stack Overflow", channel_name="stackexchange", title=_plain(item.get("title")),
                content=body[:12000], snippet=body[:350],
                url=f"https://stackoverflow.com/questions/{item['question_id']}",
                author=_plain(owner.get("display_name")), published=_date(item.get("creation_date")),
                content_depth="PARTIAL_CONTENT" if body else "METADATA",
                retrieval_mode=RetrievalMode.DIRECT_API.value, native_backend_id="stackexchange-api",
                raw_metadata={"score": item.get("score"), "answer_count": item.get("answer_count"),
                              "transport": dict(observations[-1]),
                              "is_answered": item.get("is_answered"), "tags": item.get("tags", [])[:10],
                              "accepted_answer_id": item.get("accepted_answer_id"),
                              "content_license": item.get("content_license"),
                              "attribution_url": f"https://stackoverflow.com/questions/{item['question_id']}",
                              "answers_acquired": False, "has_more": data.get("has_more"), "page": page,
                              "truncated": len(body) > 12000, "pagination_complete": None},
            ))
    telemetry["status"] = "SUCCESS" if fragments else "EMPTY_RESULT"
    return fragments, telemetry
