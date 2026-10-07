"""
Aegis Protocol — Multi-Engine Search Discovery & Fallback Adapter
==================================================================
First-class search discovery engine (Bing / Yahoo multi-engine discovery).
Discovers candidate URLs, resolves redirects, canonicalizes platform links,
and acts as fallback for walled-garden platforms (Instagram, Facebook, TikTok,
LinkedIn, Bilibili) where direct zero-auth scraping is impossible or forbidden.
"""

import json
import logging
import re
import time
import urllib.parse
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
from backend.services.agent_reach.native.source_discovery import (
    discover_sources_from_search,
    generate_discovery_queries,
    resolve_bing_redirect,
)
from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)


class SearchDiscoveryAdapter(PlatformAdapter):
    """
    Search-driven discovery and index acquisition adapter.
    """

    @property
    def platform(self) -> str:
        return "search"

    @property
    def backend_id(self) -> str:
        return "search_index_discovery"

    def can_handle(self, candidate: CandidateSource) -> bool:
        return True

    def discover_candidates(
        self,
        query: str,
        platform: str = "web",
        entity: str = "",
        limit: int = 10,
    ) -> List[CandidateSource]:
        """
        Execute multi-query search discovery and return ranked candidate sources.
        """
        queries = generate_discovery_queries(platform=platform, query=query, entity=entity)
        disc_results = discover_sources_from_search(queries=queries, platform=platform, limit=limit)

        candidates: List[CandidateSource] = []
        for idx, res in enumerate(disc_results, start=1):
            cand = CandidateSource(
                url=res.canonical_url,
                platform=res.platform,
                canonical_url=res.canonical_url,
                search_engine="bing_yahoo",
                search_rank=idx,
                discovery_query=res.discovery_query,
                title=res.raw_title,
                snippet=res.raw_snippet,
                passed_hard_gates=True,
                semantic_score=res.confidence * 100.0,
                metadata={
                    "external_id": res.external_id,
                    "handle": res.handle,
                    "subreddit": res.subreddit,
                    "source_type": res.source_type,
                },
            )
            candidates.append(cand)

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """
        When used as index acquisition fallback (e.g. for Instagram, TikTok, LinkedIn, FB).
        """
        target_url = candidate.canonical_url or candidate.url
        is_safe, reason = validate_url_safe(target_url)
        if not is_safe:
            return FetchedDocument(
                url=target_url,
                status="BLOCKED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                failure_reason=f"SSRF validation failed: {reason}",
            )

        # Snippet-based evidence from search index
        payload = {
            "title": candidate.title or "Search Discovery Record",
            "snippet": candidate.snippet or "",
            "url": target_url,
            "platform": candidate.platform,
            "search_rank": candidate.search_rank,
        }
        return FetchedDocument(
            url=target_url,
            status="SUCCESS",
            backend_id=self.backend_id,
            retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
            raw_content=json.dumps(payload),
            latency_ms=80,
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

        title = data.get("title") or candidate.title or "Search Result"
        snippet = data.get("snippet") or candidate.snippet or ""
        url = data.get("url") or candidate.canonical_url or document.url
        plat = candidate.platform or "web"

        frag = EvidenceFragment(
            platform=plat,
            title=title,
            content=f"Title: {title}\nPlatform: {plat}\n\nSearch Index Snippet:\n{snippet}",
            url=url,
            author=f"{plat}_index",
            published=datetime.now(timezone.utc).isoformat(),
            snippet=snippet,
            score=candidate.semantic_score or 1.0,
            retrieval_method="agent_reach",
            channel_name=plat,
            content_depth="SNIPPET",
            query_id=request.request_id,
            query_class=request.task_type,
            query_text=request.query,
            retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
            native_backend_id=self.backend_id,
            is_authenticated=False,
            raw_metadata={"search_rank": candidate.search_rank, "discovery_query": candidate.discovery_query},
        )
        return [frag]
