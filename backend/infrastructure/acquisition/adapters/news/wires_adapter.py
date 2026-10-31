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

    # Zero-auth tier-1 publisher feeds that return REAL article URLs (not wrapper links),
    # ordered from most general to most specialist. Each was verified live 2026-10-26.
    # Removed: reutersagency.com (404, decommissioned), pib.gov.in/RssMain.aspx (serves HTML),
    # and Google News RSS search (its /rss/articles/ links are opaque, unresolvable wrappers).
    OFFICIAL_FEEDS = {
        "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "guardian_business": "https://www.theguardian.com/business/rss",
        "guardian_world": "https://www.theguardian.com/world/rss",
        "aljazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "bbc_technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "guardian_technology": "https://www.theguardian.com/technology/rss",
        "arstechnica": "https://feeds.arstechnica.com/arstechnica/index",
        "theverge": "https://www.theverge.com/rss/index.xml",
        "npr_business": "https://feeds.npr.org/1006/rss.xml",
    }
    # How many feeds to scan at most per discovery call, to bound latency.
    MAX_FEEDS_PER_DISCOVER = 6

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

    def _emit(self, frag, wire_name, candidates, seen):
        key = (frag.url or "").split("?")[0].rstrip("/").lower()
        if not frag.url or key in seen or frag.url.lower().startswith("https://news.google.com"):
            return  # Google News wrapper links are not readable; never emit them as leads.
        seen.add(key)
        candidates.append(CandidateSource(
            url=frag.url, platform="news", title=frag.title, snippet=frag.snippet,
            search_engine=f"{wire_name}_wire",
            metadata={"wire": wire_name, "published": frag.published, "author": frag.author,
                      "observed_publisher": wire_name, "full_content": frag.content,
                      "discovery_only": True, "linked_article_retrieved": False}))

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Discover live newswire stories for the query from direct tier-1 publisher feeds.

        Items are keyword-filtered to the query and carry real publisher article URLs, read
        later by the ordinary SSRF-safe budgeted reader. Nothing here is accepted as evidence;
        a niche query legitimately returns few or no leads rather than fabricated ones.
        """
        candidates: List[CandidateSource] = []
        seen: set = set()
        tokens = [t for t in query.lower().split() if len(t) > 2]
        feeds_to_scan = list(self.OFFICIAL_FEEDS.items())[:self.MAX_FEEDS_PER_DISCOVER]

        def _fetch_single_feed(item):
            w_name, f_url = item
            try:
                resp = fetch_public_http(f_url, timeout=3.0, max_bytes=2_000_000)
                if resp.status_code == 200:
                    return w_name, f_url, resp.body.decode("utf-8", errors="replace")
            except Exception as exc:
                logger.debug(f"[NewswireAdapter] Discovery error for {w_name}: {type(exc).__name__}")
            return w_name, f_url, None

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(feeds_to_scan), 6)) as pool:
            for wire_name, feed_url, body_str in pool.map(_fetch_single_feed, feeds_to_scan):
                if not body_str or len(candidates) >= limit:
                    continue
                try:
                    for f in UniversalFeedDiscovery.parse_feed_content(body_str, feed_url, limit=40):
                        if len(candidates) >= limit:
                            break
                        text_to_match = f"{f.title} {f.snippet}".lower()
                        if not tokens or any(tok in text_to_match for tok in tokens):
                            self._emit(f, wire_name, candidates, seen)
                except Exception:
                    pass

        return candidates[:limit]

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


class TrendingPulseAdapter(NewswireAdapter):
    """Fresh-pulse discovery for the Trending agent.

    Entertainment + breaking-news feeds that publish many items per day, so leads can
    satisfy the strict 48h virality window. All were verified live (2026-10-27) to return
    recent, directly-readable publisher article URLs (no Google News wrappers). Inherits the
    "news" platform (so its leads pass the shared external-lead rule) and NewswireAdapter's
    discover/acquire/normalize unchanged; only the feed set and scan breadth differ.
    """

    OFFICIAL_FEEDS = {
        "deadline": "https://deadline.com/feed/",
        "variety": "https://variety.com/feed/",
        "hollywood_reporter": "https://www.hollywoodreporter.com/feed/",
        "bollywood_hungama": "https://www.bollywoodhungama.com/rss/news.xml",
        "pinkvilla": "https://www.pinkvilla.com/rss.xml",
        "ndtv_entertainment": "https://feeds.feedburner.com/ndtvmovies-latest",
        "bbc_entertainment": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "guardian_culture": "https://www.theguardian.com/culture/rss",
        "aljazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    }
    MAX_FEEDS_PER_DISCOVER = 8

    @property
    def backend_id(self) -> str:
        return "trending_pulse_engine"
