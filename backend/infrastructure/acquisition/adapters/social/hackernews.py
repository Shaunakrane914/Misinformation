"""Aegis Protocol — Hacker News Public Discussion Adapter.

Queries the official Hacker News Algolia search API (hn.algolia.com/api/v1/search)
for tech, startup, and scientific narrative monitoring.
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

HN_SEARCH_API = "https://hn.algolia.com/api/v1/search"


class HackerNewsAdapter(PlatformAdapter):
    """Acquires stories and discussions from Hacker News."""

    @property
    def platform(self) -> str:
        return "hackernews"

    @property
    def backend_id(self) -> str:
        return "hn_algolia_api"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        return candidate.platform.lower() in ("hackernews", "hn") or "news.ycombinator.com" in url

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        candidates: List[CandidateSource] = []
        clean_q = query.strip()
        if not clean_q:
            return candidates

        params = urllib.parse.urlencode({
            "query": clean_q,
            "tags": "story",
            "hitsPerPage": min(limit, 20),
        })
        target_url = f"{HN_SEARCH_API}?{params}"

        try:
            resp = fetch_public_http(target_url, timeout=3.5)
            if resp.status_code == 200:
                data = json.loads(resp.body.decode("utf-8", errors="replace"))
                hits = data.get("hits", [])
                for idx, hit in enumerate(hits[:limit]):
                    object_id = hit.get("objectID", f"hn_{idx}")
                    hn_url = f"https://news.ycombinator.com/item?id={object_id}"
                    title = hit.get("title", "HN Story")
                    author = hit.get("author", "hn_user")
                    story_text = hit.get("story_text") or hit.get("url") or ""
                    points = hit.get("points", 0)
                    comments = hit.get("num_comments", 0)

                    candidates.append(
                        CandidateSource(
                            url=hn_url,
                            platform="hackernews",
                            title=f"[HN {points} pts] {title}",
                            snippet=f"{story_text[:200]} | By: {author} | Comments: {comments}",
                            search_engine="hn_algolia_search",
                            search_rank=idx + 1,
                            metadata={
                                "author": author,
                                "points": points,
                                "num_comments": comments,
                                "story_url": hit.get("url", ""),
                                "created_at": hit.get("created_at", ""),
                                "full_text": story_text,
                            },
                        )
                    )
        except Exception as exc:
            logger.debug(f"[HackerNewsAdapter] Discovery error for {query}: {type(exc).__name__}")

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

        content = candidate.metadata.get("full_text") or candidate.snippet or candidate.title
        return FetchedDocument(
            url=target_url,
            status="SUCCESS",
            backend_id=self.backend_id,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            raw_content=content,
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

        author = candidate.metadata.get("author") or "hn_author"
        points = candidate.metadata.get("points", 0)
        comments = candidate.metadata.get("num_comments", 0)
        content = f"{candidate.title}\nURL: {candidate.metadata.get('story_url', '')}\n\n{document.raw_content}"

        return [
            EvidenceFragment(
                platform="hackernews",
                title=candidate.title,
                content=content,
                url=document.url,
                author=author,
                published=candidate.metadata.get("created_at", ""),
                snippet=candidate.snippet,
                score=80.0,
                content_depth=ContentDepth.SOCIAL_POST.value,
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id=self.backend_id,
                channel_name="hackernews",
                raw_metadata={
                    "points": points,
                    "num_comments": comments,
                    "external_story_url": candidate.metadata.get("story_url", ""),
                },
            )
        ]
