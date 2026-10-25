"""Aegis Protocol — Yahoo Finance Market & Earnings Intelligence Adapter.

Provides corporate market news, earnings releases, and guidance intelligence for Scout:
- Public market ticker symbol resolution and quote summaries
- Corporate press releases and earnings commentary
- Executive leadership roster and company business summary
- Ingests up to 25,000 characters per market intelligence document
"""

from __future__ import annotations

import json
import logging
import re
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

YFINANCE_SEARCH_BASE = "https://query2.finance.yahoo.com/v1/finance/search"
DEFAULT_YFINANCE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


class YahooFinanceAdapter(PlatformAdapter):
    """Acquires market disclosures and corporate earnings news from Yahoo Finance."""

    @property
    def platform(self) -> str:
        return "yahoo_finance"

    @property
    def backend_id(self) -> str:
        return "yahoo_finance_api"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("yahoo_finance", "yfinance", "finance_news"):
            return True
        return "finance.yahoo.com" in url

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Search Yahoo Finance for company quotes, news, and releases."""
        candidates: List[CandidateSource] = []
        clean_q = query.strip()
        if not clean_q:
            return candidates

        params = {
            "q": clean_q,
            "quotesCount": "5",
            "newsCount": str(min(limit, 10)),
            "enableFuzzyQuery": "false",
        }
        api_url = f"{YFINANCE_SEARCH_BASE}?{urllib.parse.urlencode(params)}"
        if not validate_url_safe(api_url)[0]:
            return candidates

        try:
            resp = fetch_public_http(api_url, headers=DEFAULT_YFINANCE_HEADERS, timeout=5.0)
            if resp.status_code != 200:
                logger.warning("[YahooFinanceAdapter] Search HTTP %d for query '%s'", resp.status_code, clean_q)
                return candidates

            data = json.loads(resp.body.decode("utf-8", errors="replace"))
            quotes = data.get("quotes", [])
            news_items = data.get("news", [])

            # Add quote profile overview if company quote found
            for q in quotes[:2]:
                symbol = q.get("symbol")
                shortname = q.get("shortname") or q.get("longname") or symbol
                if symbol and q.get("quoteType") == "EQUITY":
                    quote_url = f"https://finance.yahoo.com/quote/{symbol}"
                    candidates.append(
                        CandidateSource(
                            url=quote_url,
                            canonical_url=quote_url,
                            platform="yahoo_finance",
                            title=f"[{symbol}] {shortname} Corporate Profile & Market Summary",
                            snippet=f"{shortname} ({symbol}). Source-reported exchange: {q.get('exchange') or 'unavailable'}. Industry: {q.get('industry') or 'unavailable'}. Sector: {q.get('sector') or 'unavailable'}.",
                            metadata={
                                "symbol": symbol,
                                "exchange": q.get("exchange"),
                                "shortname": shortname,
                                "type": "quote",
                                "primary_source": False,
                                "official_source": False,
                            },
                        )
                    )

            # Add corporate news / press releases
            for item in news_items:
                if len(candidates) >= limit:
                    break
                title = item.get("title", "")
                link = item.get("link", "")
                publisher = item.get("publisher", "Yahoo Finance")
                uuid_val = item.get("uuid", "")
                pub_time = item.get("providerPublishTime")

                if title and link:
                    candidates.append(
                        CandidateSource(
                            url=link,
                            canonical_url=link,
                            platform="yahoo_finance",
                            title=f"{title} — {publisher}",
                            snippet=f"Market disclosure via {publisher}. Published {pub_time}.",
                            metadata={
                                "uuid": uuid_val,
                                "publisher": publisher,
                                "publish_time": pub_time,
                                "related_symbols": item.get("relatedTickers", []),
                                "type": "news",
                                "primary_source": False,
                                "official_source": False,
                            },
                        )
                    )
        except Exception as exc:
            logger.warning("[YahooFinanceAdapter] Discovery error for '%s': %s", clean_q, type(exc).__name__)

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """Fetch and extract full financial report or news article."""
        url = candidate.canonical_url or candidate.url
        if not validate_url_safe(url)[0]:
            return FetchedDocument(url=url, status="BLOCKED_SSRF", failure_reason="Yahoo Finance URL failed SSRF check", backend_id=self.backend_id)

        try:
            resp = fetch_public_http(url, headers=DEFAULT_YFINANCE_HEADERS, timeout=6.0, max_bytes=2_000_000)
            if resp.status_code != 200:
                return FetchedDocument(url=url, status="FAILED", failure_reason=f"HTTP {resp.status_code}", backend_id=self.backend_id)

            raw_html = resp.body.decode("utf-8", errors="replace")
            cleaned = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", raw_html, flags=re.IGNORECASE)
            cleaned = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"<(?:p|div|h[1-6]|li|article)[^>]*>", "\n\n", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"<[^>]+>", " ", cleaned)
            body_text = re.sub(r"[ \t]+", " ", cleaned).strip()

            if not body_text.strip():
                return FetchedDocument(url=url, status="EMPTY_CONTENT", backend_id=self.backend_id)
            title = candidate.title or "Yahoo Finance Market Report"
            symbol = candidate.metadata.get("symbol", "")
            publisher = candidate.metadata.get("publisher", "Yahoo Finance")

            content = f"# {title}\n"
            if symbol:
                content += f"**Ticker**: {symbol} | **Market Source**: {url}\n\n"
            else:
                content += f"**Publisher**: {publisher} | **Source**: {url}\n\n"
            content += body_text

            capped = content[:25000]

            return FetchedDocument(
                url=url,
                status="SUCCESS",
                raw_content=capped,
                backend_id=self.backend_id,
                raw_metadata={
                    "title": title,
                "source_html": locals().get("raw_html") or locals().get("body_html") or "",
                    "symbol": symbol,
                    "publisher": publisher,
                    "wordcount": len(capped.split()),
                },
            )
        except Exception as exc:
            logger.warning("[YahooFinanceAdapter] Acquisition error for '%s': %s", url, type(exc).__name__)
            return FetchedDocument(url=url, status="FAILED", failure_reason=type(exc).__name__, backend_id=self.backend_id)

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """Normalize into financial EvidenceFragment."""
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        title = document.raw_metadata.get("title") or candidate.title
        content = document.raw_content
        publisher = document.raw_metadata.get("publisher") or "Yahoo Finance"

        fragment = EvidenceFragment(
            platform="yahoo_finance",
            channel_name="yahoo_finance",
            url=candidate.url,
            title=f"{title} (Financial Intelligence)",
            content=content,
            snippet=content[:400] + ("..." if len(content) > 400 else ""),
            author=publisher,
            content_depth=ContentDepth.FULL_ARTICLE.value,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id=self.backend_id,
            retrieval_lineage=[{
                "platform": "yahoo_finance",
                "backend": self.backend_id,
                "url": candidate.url,
                "symbol": document.raw_metadata.get("symbol"),
                "retrieval_mode": RetrievalMode.DIRECT_API.value,
            }],
            raw_metadata={
                "source_role": "secondary",
                "source_tier": "tier_2_established",
                "source_domain": "finance.yahoo.com",
                "source_independence_group": "yahoo.com",
                "char_count": len(content),
                "word_count": len(content.split()),
                "symbol": document.raw_metadata.get("symbol"),
                "publisher": publisher,
            },
        )
        return [fragment]
