"""Aegis Protocol — Consumer Reviews & Scam Complaints Adapter.

Provides brand defense, counterfeit tracking, and consumer smear intelligence for BrandShield:
- Public customer reviews from Trustpilot, ComplaintsBoard, and BBB
- Overall TrustScore, star rating breakdown, and verified review volume
- Unfiltered complaint narratives (counterfeiting, billing fraud, scam alerts, smear campaigns)
- Ingests up to 25,000 characters of authentic consumer sentiment
"""

from __future__ import annotations

import json
from backend.infrastructure.acquisition.adapters.expansion_safety import matches_host
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

DEFAULT_CONSUMER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class ConsumerReviewAdapter(PlatformAdapter):
    """Acquires consumer review narratives and brand complaint threads."""

    @property
    def platform(self) -> str:
        return "trustpilot"

    @property
    def backend_id(self) -> str:
        return "trustpilot_reader"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("trustpilot", "consumer_reviews", "complaints", "brand_reviews"):
            return True
        return any(domain in url for domain in ("trustpilot.com", "complaintsboard.com", "sitejabber.com", "bbb.org"))

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Discover consumer review profile or complaint threads for a brand."""
        candidates: List[CandidateSource] = []
        clean_q = query.strip()
        if not clean_q:
            return candidates

        # A name alone does not establish a real review-profile domain.
        if not matches_host(clean_q, ("trustpilot.com", "complaintsboard.com", "sitejabber.com", "bbb.org")):
            return []
        candidates.append(CandidateSource(url=clean_q, canonical_url=clean_q,
            platform="trustpilot", title="User-supplied consumer-review source",
            metadata={"acquisition_scope": "EXTERNALLY_SUPPLIED_SOURCE"}))
        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """Fetch and extract customer reviews and complaint narratives."""
        url = candidate.canonical_url or candidate.url
        if not validate_url_safe(url)[0]:
            return FetchedDocument(url=url, status="BLOCKED_SSRF", failure_reason="Review URL failed SSRF check", backend_id=self.backend_id)

        brand = candidate.metadata.get("brand") or "Target Brand"
        try:
            resp = fetch_public_http(url, headers=DEFAULT_CONSUMER_HEADERS, timeout=6.0, max_bytes=2_000_000)
            if resp.status_code != 200:
                return FetchedDocument(url=url, status="FAILED", failure_reason=f"HTTP {resp.status_code}", backend_id=self.backend_id)

            raw_html = resp.body.decode("utf-8", errors="replace")

            # Extract structured Next.js data or HTML reviews
            reviews_text = []
            trust_score = "N/A"
            review_count = "0"

            # Check for embedded json data
            next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([\s\S]*?)</script>', raw_html)
            if next_data_match:
                try:
                    data = json.loads(next_data_match.group(1))
                    business_entity = data.get("props", {}).get("pageProps", {}).get("businessUnit", {})
                    trust_score = str(business_entity.get("trustScore", "N/A"))
                    review_count = str(business_entity.get("numberOfReviews", "0"))
                    raw_reviews = data.get("props", {}).get("pageProps", {}).get("reviews", [])
                    for r in raw_reviews:
                        r_title = r.get("title", "")
                        r_text = r.get("text", "")
                        r_rating = r.get("rating", "")
                        r_date = r.get("dates", {}).get("publishedDate", "")
                        reviews_text.append(f"### Review ({r_rating}/5 stars) — {r_title}\n*Date: {r_date}*\n{r_text}")
                except Exception as exc:
                    logger.debug("[ConsumerReviewAdapter] Next.js data parse notice: %s", type(exc).__name__)

            # Fallback to HTML text parsing
            if not reviews_text:
                cleaned = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", raw_html, flags=re.IGNORECASE)
                cleaned = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"<(?:p|div|article|h[1-6]|li)[^>]*>", "\n\n", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"<[^>]+>", " ", cleaned)
                plain_body = re.sub(r"\s+", " ", cleaned).strip()
                reviews_text.append(plain_body[:20000])

            if not any(value.strip() for value in reviews_text):
                return FetchedDocument(url=url, status="EMPTY_CONTENT", backend_id=self.backend_id)
            content = f"# Consumer Review Capture: {brand}\n"
            content += f"**TrustScore**: {trust_score}/5.0 | **Provider-reported Review Count**: {review_count}\n"
            content += f"**Audit Source**: {url}\n\n"
            content += "## Customer Testimonials & Dispute Narratives\n\n"
            content += "\n\n".join(reviews_text)

            capped = content[:25000]

            return FetchedDocument(
                url=url,
                status="SUCCESS",
                raw_content=capped,
                backend_id=self.backend_id,
                raw_metadata={
                    "brand": brand,
                "source_html": locals().get("raw_html") or locals().get("body_html") or "",
                    "trust_score": trust_score,
                    "review_count": review_count,
                    "wordcount": len(capped.split()),
                },
            )
        except Exception as exc:
            logger.warning("[ConsumerReviewAdapter] Acquisition error for '%s': %s", url, type(exc).__name__)
            return FetchedDocument(url=url, status="FAILED", failure_reason=type(exc).__name__, backend_id=self.backend_id)

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """Normalize into consumer review EvidenceFragment."""
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        brand = document.raw_metadata.get("brand") or candidate.metadata.get("brand") or "Brand"
        content = document.raw_content

        fragment = EvidenceFragment(
            platform="trustpilot",
            channel_name="trustpilot",
            url=candidate.url,
            title=f"{brand} Consumer Reviews & Complaints",
            content=content,
            snippet=content[:400] + ("..." if len(content) > 400 else ""),
            author="Source-reported community reviews; reviewer identities unverified",
            content_depth=ContentDepth.FULL_ARTICLE.value,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id=self.backend_id,
            retrieval_lineage=[{
                "platform": "trustpilot",
                "backend": self.backend_id,
                "url": candidate.url,
                "brand": brand,
                "retrieval_mode": RetrievalMode.DIRECT_API.value,
            }],
            raw_metadata={
                "source_role": "secondary",
                "source_tier": "tier_3_community",
                "source_domain": "trustpilot.com",
                "source_independence_group": "trustpilot.com",
                "char_count": len(content),
                "word_count": len(content.split()),
                "trust_score": document.raw_metadata.get("trust_score"),
                "review_count": document.raw_metadata.get("review_count"),
                "brand": brand,
            },
        )
        return [fragment]
