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
        # Direct publisher feeds observed in the IDE-checkout repair. The old
        # Reuters endpoint is gone and the PIB endpoint returns an HTML index.
        # Keep the original three-feed bound and existing reader/access policy.
        "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "bbc_technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    }
    FEED_SECTIONS = {'bbc_world': 'world', 'bbc_business': 'business', 'bbc_technology': 'technology'}
    CATEGORY_QUERIES = {
        'world': {'world', 'world news', 'international news'},
        'business': {'business', 'business news', 'finance', 'finance news'},
        'technology': {'technology', 'technology news', 'tech', 'tech news'},
    }
    MAX_FEEDS_PER_DISCOVER = 3

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
        seen = set()
        clean_q = ' '.join(re.findall(r'\w+', query.casefold()))
        if not clean_q or limit <= 0:
            return candidates
        section = next((name for name, labels in self.CATEGORY_QUERIES.items() if clean_q in labels), None)
        category_words = {word for labels in self.CATEGORY_QUERIES.values() for label in labels for word in label.split()}
        tokens = {word for word in clean_q.split() if len(word) > 2}
        meaningful = tokens - category_words - {'latest', 'updates', 'update', 'the', 'and', 'for', 'about'}
        feeds = sorted(self.OFFICIAL_FEEDS.items(),
                       key=lambda row: self.FEED_SECTIONS.get(row[0]) != section if section else False)

        for wire_name, feed_url in feeds[:self.MAX_FEEDS_PER_DISCOVER]:
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
                        identity = (f.url or '').split('#', 1)[0]
                        if not identity or identity in seen:
                            continue
                        text_to_match = set(re.findall(r'\w+', f"{f.title} {f.snippet}".casefold()))
                        topic_section = section and self.FEED_SECTIONS.get(wire_name) == section
                        # A technology section contains AI/device reports that
                        # need not repeat 'technology' in each headline. This
                        # permits reading leads only, never evidence acceptance.
                        # Names/other terms cannot pass on the section word alone.
                        token_match = (bool(meaningful) and meaningful <= text_to_match if not section
                                       else bool(tokens & text_to_match))
                        if topic_section or token_match:
                            seen.add(identity)
                            candidates.append(
                                CandidateSource(
                                    url=f.url,
                                    platform="news",
                                    title=f.title,
                                    snippet=f.snippet,
                                    search_engine=f"{wire_name}_wire",
                                    metadata={
                                        "wire": wire_name,
                                        "feed_url": feed_url,
                                        "publisher_section": self.FEED_SECTIONS.get(wire_name),
                                        "discovery_match_basis": 'PUBLISHER_TOPIC_SECTION' if topic_section else 'TITLE_OR_SNIPPET_TOKENS',
                                        "discovery_only": True,
                                        "linked_article_retrieved": False,
                                        "publication_time_basis": "PUBLISHER_FEED_DECLARATION",
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
