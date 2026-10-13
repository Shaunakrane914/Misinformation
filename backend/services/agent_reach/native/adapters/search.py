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
        # Discovery consumes real search fragments; the social URL extractor is
        # not itself a search client. The old keyword mismatch silently made
        # every typed discovery request empty.
        from backend.services.agent_reach.native.router import native_router
        queries = generate_discovery_queries(platform=platform, query=query, entity=entity) if platform in {"reddit", "twitter", "x"} else [query]
        fragments = []
        for discovery_query in queries:
            fragments.extend(native_router._execute_web_search(discovery_query, limit=limit))
        disc_results = discover_sources_from_search(
            fragments, platform, query=query, target_entity=entity, max_candidates=limit
        ) if platform in {"reddit", "twitter", "x"} else []
        if platform not in {"reddit", "twitter", "x"}:
            candidates = []
            seen = set()
            for fragment in fragments:
                url = resolve_bing_redirect(fragment.url)
                if not url or url in seen:
                    continue
                seen.add(url)
                host = (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")
                actual_platform = platform
                for domains, specialist in ((["reddit.com", "redd.it"], "reddit"), (["x.com", "twitter.com"], "twitter"),
                                            (["youtube.com", "youtu.be"], "youtube"), (["github.com"], "github")):
                    if any(host == domain or host.endswith("." + domain) for domain in domains):
                        actual_platform = specialist
                        break
                candidates.append(CandidateSource(
                    url=url, platform=actual_platform, title=fragment.title,
                    snippet=fragment.snippet, discovery_query=query,
                    search_rank=len(candidates) + 1,
                    metadata={"published_at": fragment.published},
                ))
            return candidates[:limit]

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

        title = data.get("title") or candidate.title or ""
        snippet = data.get("snippet") or candidate.snippet or ""
        if not title and not snippet:
            return []
        url = data.get("url") or candidate.canonical_url or document.url
        plat = candidate.platform or "web"
        content = "\n".join(part for part in (f"Title: {title}" if title else "",
                                                 f"Search Index Snippet: {snippet}" if snippet else "") if part)

        frag = EvidenceFragment(
            platform=plat,
            title=title,
            content=content,
            url=url,
            author="",
            published="",
            snippet=snippet,
            score=candidate.semantic_score or 0.0,
            retrieval_method="agent_reach",
            channel_name=plat,
            content_depth="SNIPPET" if snippet else "METADATA",
            query_id=request.request_id,
            query_class=request.task_type,
            query_text=request.query,
            retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
            native_backend_id=self.backend_id,
            is_authenticated=False,
            raw_metadata={"search_rank": candidate.search_rank,
                          "discovery_query": candidate.discovery_query,
                          "discovery_published_at": data.get("published_at") or candidate.metadata.get("published_at")},
        )
        return [frag]
