"""Aegis Protocol — Global & Regional Newswire Platform Adapter.

High-throughput specialized adapter for tier-1 news organizations:
- Reuters
- Associated Press (AP)
- BBC News
- Press Information Bureau (PIB India)
- ANI / The Hindu
"""

import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.adapters.expansion_safety import GuardedExpansionAdapter as PlatformAdapter
from backend.infrastructure.acquisition.adapters.news.feed_discovery import UniversalFeedDiscovery
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


class NewswireAdapter(PlatformAdapter):
    """Acquires and normalizes newswire dispatches and official press releases."""

    NEWSWIRE_DOMAINS = {
        "reuters.com": "reuters",
        "apnews.com": "associated_press",
        "bbc.com": "bbc",
        "bbc.co.uk": "bbc",
        "pib.gov.in": "pib_india",
        "aninews.in": "ani",
        "thehindu.com": "the_hindu",
    }

    OFFICIAL_FEEDS = {
        "reuters": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
        "bbc": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "pib_india": "https://pib.gov.in/RssMain.aspx",
    }

    @property
    def platform(self) -> str:
        return "news"

    @property
    def backend_id(self) -> str:
        return "newswire_wire_engine"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("news", "newswire", "pib", "reuters", "ap"):
            return True
        return any(d in url for d in self.NEWSWIRE_DOMAINS)

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Discover live newswire stories matching the query via official feeds."""
        candidates: List[CandidateSource] = []
        clean_q = query.lower().strip()
        tokens = set(clean_q.split())

        for wire_name, feed_url in self.OFFICIAL_FEEDS.items():
            if len(candidates) >= limit:
                break
            try:
                resp = fetch_public_http(feed_url, timeout=3.5)
                if resp.status_code == 200:
                    frags = UniversalFeedDiscovery.parse_feed_content(
                        resp.body.decode("utf-8", errors="replace"),
                        feed_url,
                        limit=20,
                    )
                    for f in frags:
                        text_to_match = f"{f.title} {f.snippet}".lower()
                        # If query tokens match or query is generic
                        if not tokens or any(tok in text_to_match for tok in tokens if len(tok) > 2):
                            candidates.append(
                                CandidateSource(
                                    url=f.url,
                                    platform="news",
                                    title=f.title,
                                    snippet=f.snippet,
                                    search_engine=f"{wire_name}_wire",
                                    metadata={
                                        "wire": wire_name,
                                        "published": f.published,
                                        "author": f.author,
                                        "full_content": f.content,
                                    },
                                )
                            )
                            if len(candidates) >= limit:
                                break
            except Exception as exc:
                logger.debug(f"[NewswireAdapter] Discovery error for {wire_name}: {type(exc).__name__}")

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        target_url = candidate.canonical_url or candidate.url
        is_safe, reason = validate_url_safe(target_url)
        if not is_safe:
            return FetchedDocument(
                url=target_url,
                status="BLOCKED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                failure_reason=f"SSRF policy blocked URL: {reason}",
            )

        # Feed text is discovery context. Acquire the actual linked document.
        try:
            resp = fetch_public_http(target_url, timeout=5.0, max_bytes=1_000_000)
            body_str = resp.body.decode("utf-8", errors="replace")
            return FetchedDocument(
                url=target_url,
                status="SUCCESS" if resp.status_code == 200 else "FAILED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                raw_content=body_str,
                latency_ms=resp.latency_ms,
            )
        except Exception as exc:
            return FetchedDocument(
                url=target_url,
                status="FAILED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                failure_reason=type(exc).__name__,
            )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        if document.status != "SUCCESS":
            return []

        raw = document.raw_content
        # Extract title and body text
        title = candidate.title or "Newswire Dispatch"
        title_match = re.search(r'<title[^>]*>(.*?)</title>', raw, re.IGNORECASE)
        if title_match and title == "Newswire Dispatch":
            title = re.sub(r'\s+', ' ', title_match.group(1)).strip()

        # Clean HTML tags
        clean_text = re.sub(r'<[^>]+>', ' ', raw)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()[:4000]
        snippet = candidate.snippet or clean_text[:250]

        wire_name = candidate.metadata.get("wire") or "newswire"
        is_official = "pib" in document.url or "reuters" in document.url or "apnews" in document.url

        return [
            EvidenceFragment(
                platform="news",
                title=title,
                content=clean_text,
                url=document.url,
                author=candidate.metadata.get("author") or wire_name.upper(),
                published=candidate.metadata.get("published", ""),
                snippet=snippet,
                score=88.0 if is_official else 80.0,
                content_depth=ContentDepth.FULL_ARTICLE.value if len(clean_text) > 800 else ContentDepth.PARTIAL_CONTENT.value,
                retrieval_mode=document.retrieval_mode or RetrievalMode.WEB_READER.value,
                native_backend_id=self.backend_id,
                channel_name="news",
                raw_metadata={
                    "wire": wire_name,
                    "is_official_wire": is_official,
                },
            )
        ]
