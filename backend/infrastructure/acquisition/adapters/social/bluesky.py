"""Aegis Protocol — Bluesky AT Protocol Public Social Adapter.

Queries the zero-auth public Bluesky endpoints (public.api.bsky.app)
for real-time memetic virality and narrative velocity tracking.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.adapters.expansion_safety import GuardedExpansionAdapter as PlatformAdapter
from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch as fetch_public_http
from backend.services.agent_reach.channels import (
    CandidateSource,
    ContentDepth,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)

BSKY_PUBLIC_API = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"


class BlueskyAdapter(PlatformAdapter):
    """Acquires posts and engagement from Bluesky using the public AT Protocol API."""

    @property
    def platform(self) -> str:
        return "bluesky"

    @property
    def backend_id(self) -> str:
        return "bsky_public_api"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        return candidate.platform.lower() in ("bluesky", "bsky") or "bsky.app" in url

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        candidates: List[CandidateSource] = []
        clean_q = query.strip()
        if not clean_q:
            return candidates

        params = urllib.parse.urlencode({"q": clean_q, "limit": min(limit, 25)})
        target_url = f"{BSKY_PUBLIC_API}?{params}"

        try:
            resp = fetch_public_http(target_url, timeout=4.0)
            if resp.status_code == 200:
                data = json.loads(resp.body.decode("utf-8", errors="replace"))
                posts = data.get("posts", [])
                for idx, post in enumerate(posts[:limit]):
                    author_info = post.get("author", {})
                    handle = author_info.get("handle", "unknown.bsky.social")
                    uri = post.get("uri", "")
                    rkey = uri.split("/")[-1] if uri else f"post_{idx}"
                    post_url = f"https://bsky.app/profile/{handle}/post/{rkey}"
                    record = post.get("record", {})
                    text = record.get("text", "")
                    title = f"@{handle}: {text[:80]}"

                    candidates.append(
                        CandidateSource(
                            url=post_url,
                            platform="bluesky",
                            title=title,
                            snippet=text[:300],
                            search_engine="bsky_public_search",
                            search_rank=idx + 1,
                            metadata={
                                "author_handle": handle,
                                "author_name": author_info.get("displayName", ""),
                                "post_text": text,
                                "created_at": record.get("createdAt", ""),
                                "like_count": post.get("likeCount", 0),
                                "repost_count": post.get("repostCount", 0),
                                "reply_count": post.get("replyCount", 0),
                            },
                        )
                    )
        except Exception as exc:
            logger.debug(f"[BlueskyAdapter] Discovery error for {query}: {type(exc).__name__}")

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        target_url = candidate.canonical_url or candidate.url
        is_safe, reason = validate_url_safe(target_url)
        if not is_safe:
            return FetchedDocument(
                url=target_url,
                status="BLOCKED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                failure_reason=f"SSRF policy blocked URL: {reason}",
            )

        if candidate.metadata.get("post_text"):
            return FetchedDocument(
                url=target_url,
                status="SUCCESS",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                raw_content=candidate.metadata["post_text"],
                raw_metadata=candidate.metadata,
                latency_ms=10,
            )

        return FetchedDocument(
            url=target_url,
            status="EMPTY_CONTENT",
            backend_id=self.backend_id,
            retrieval_mode=RetrievalMode.WEB_READER.value,
            raw_content="",
            raw_metadata=candidate.metadata,
            latency_ms=10,
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        if document.status != "SUCCESS":
            return []

        author = candidate.metadata.get("author_handle") or "bluesky_user"
        content = document.raw_content
        likes = candidate.metadata.get("like_count", 0)
        reposts = candidate.metadata.get("repost_count", 0)

        return [
            EvidenceFragment(
                platform="bluesky",
                title=candidate.title or f"Bluesky post by @{author}",
                content=content,
                url=document.url,
                author=f"@{author}",
                published=candidate.metadata.get("created_at", ""),
                snippet=candidate.snippet or content[:250],
                score=75.0,
                content_depth=ContentDepth.SOCIAL_POST.value,
                retrieval_mode=document.retrieval_mode or RetrievalMode.DIRECT_API.value,
                native_backend_id=self.backend_id,
                channel_name="bluesky",
                raw_metadata={
                    "like_count": likes,
                    "repost_count": reposts,
                    "engagement_total": likes + reposts,
                    "is_social_post": True,
                },
            )
        ]
