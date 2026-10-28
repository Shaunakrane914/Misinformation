"""Aegis Protocol — GDELT Project DOC API Platform Adapter.

Capability-aware discovery adapter for global news and narrative tracking:
- Topic searches and exact subject phrase queries
- Publication window filtering (timespan parameter)
- Article URLs and GDELT's first-seen index time (``gdelt_seen_at``; never a publication time)
- Graceful provider throttling, failures, and timeout boundaries
- Discovery-only candidate emission for standard secured reading

Invariants:
- Never fabricates articles from search snippets or metadata
- Does not interpret raw article counts alone as measured virality
- All candidate article URLs pass through validate_url_safe and Layer 2 qualification
"""

import json
import logging
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.adapters.expansion_safety import GuardedExpansionAdapter as PlatformAdapter
from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch as fetch_public_http
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)
from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)

GDELT_SEEN_AT_BASIS = "GDELT_INDEX_OBSERVATION_NOT_PUBLICATION"
PUBLICATION_TIME_UNKNOWN = "UNKNOWN_UNTIL_PUBLISHER_CONTENT"


def parse_gdelt_timestamp(val: Optional[str]) -> Optional[str]:
    """Parse GDELT ``seendate`` (e.g. 20261025T120000Z) to an ISO 8601 UTC string.

    The result is an index-observation time (``gdelt_seen_at``), never a publication time.
    """
    if not val or not isinstance(val, str):
        return None
    val = val.strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S", "%Y%m%d"):
        try:
            dt = datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return None


class GdeltDocAdapter(PlatformAdapter):
    """Acquires fresh candidate article leads from GDELT DOC API v2."""

    GDELT_HOST = "api.gdeltproject.org"

    @property
    def platform(self) -> str:
        return "gdelt"

    @property
    def backend_id(self) -> str:
        return "gdelt_doc_api"

    def can_handle(self, candidate: CandidateSource) -> bool:
        # GDELT DOC API is discovery-only; candidate article URLs are read by the web reader
        return False

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        return FetchedDocument(
            url=candidate.url,
            status="UNSUPPORTED_DIRECT_ACQUISITION",
            failure_reason="GDELT DOC API is discovery-only; candidate URLs pass through standard secure reader",
            backend_id=self.backend_id,
        )

    def discover(self, query: str, limit: int = 5, timespan: str = "48h") -> List[CandidateSource]:
        """Discover live news leads matching topic or phrase within timespan."""
        clean_q = query.strip()
        if not clean_q or limit <= 0:
            return []

        # Exact subject phrase handling if multi-word without existing quotes or operators
        if " " in clean_q and not clean_q.startswith('"') and not any(op in clean_q for op in (" AND ", " OR ", " NOT ")):
            query_str = f'"{clean_q}"'
        else:
            query_str = clean_q

        if "sourcelang:" not in query_str:
            query_str = f"{query_str} sourcelang:eng"

        max_records = min(30, max(5, int(limit) * 2))
        params = {
            "query": query_str,
            "mode": "ArtList",
            "maxrecords": str(max_records),
            "format": "json",
            "sort": "DateDesc",
            "timespan": timespan,
        }
        api_url = f"https://api.gdeltproject.org/api/v2/doc/doc?{urllib.parse.urlencode(params)}"

        candidates: List[CandidateSource] = []
        seen_urls = set()

        try:
            resp = fetch_public_http(api_url, timeout=4.5)
            if resp.status_code != 200:
                logger.debug(f"[GdeltDocAdapter] API returned status {resp.status_code}")
                return []
            data = json.loads(resp.body.decode("utf-8", errors="replace"))
        except Exception as exc:
            logger.debug(f"[GdeltDocAdapter] Discovery failed: {type(exc).__name__}")
            return []

        articles = data.get("articles", [])
        if not isinstance(articles, list):
            return []

        for idx, item in enumerate(articles):
            if len(candidates) >= limit:
                break
            if not isinstance(item, dict):
                continue
            article_url = (item.get("url") or "").strip()
            if not article_url:
                continue

            # SSRF check on article lead
            safe, _ = validate_url_safe(article_url)
            if not safe:
                continue

            norm_key = article_url.lower().rstrip("/")
            if norm_key in seen_urls:
                continue
            seen_urls.add(norm_key)

            title = (item.get("title") or "").strip()[:500]
            seendate_raw = item.get("seendate")
            seen_at = parse_gdelt_timestamp(seendate_raw)
            domain = item.get("domain", "")

            # GDELT's ``seendate`` is when GDELT's crawler first indexed the URL, not
            # when the publisher published it; an old article can be indexed today.
            # It is kept only as an index observation. No ``published``/``published_at``
            # is emitted, so publication time stays unknown until the captured
            # publisher page itself establishes it.
            candidates.append(
                CandidateSource(
                    url=article_url,
                    canonical_url=article_url,
                    platform="gdelt",
                    title=title,
                    snippet=(f"Indexed by GDELT (source domain: {domain or 'unknown'}; "
                             f"first seen by GDELT: {seen_at or seendate_raw or 'not reported'})"),
                    search_engine="gdelt_doc_api",
                    search_rank=idx + 1,
                    metadata={
                        "discovery_only": True,
                        "gdelt_seen_at": seen_at,
                        "gdelt_seen_at_raw": seendate_raw if isinstance(seendate_raw, str) else None,
                        "gdelt_seen_at_basis": GDELT_SEEN_AT_BASIS,
                        "publication_time_basis": PUBLICATION_TIME_UNKNOWN,
                        "gdelt_domain": domain,
                        "gdelt_language": item.get("language", ""),
                        "gdelt_country": item.get("sourcecountry", ""),
                        "virality_measured": False,
                    },
                )
            )

        return candidates[:limit]

    def normalize(self, document: FetchedDocument, candidate: CandidateSource, request: RetrievalRequest) -> List[Any]:
        return []
