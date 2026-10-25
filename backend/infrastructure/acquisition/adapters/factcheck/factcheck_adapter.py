"""Aegis Protocol — Fact-Checking Registry Adapters.

Structured adapters for accredited fact-checking registries and ClaimReview schemas:
- Google Fact Check Tools / ClaimReview
- Snopes
- PolitiFact
- AltNews & Regional verification
"""

import json
import logging
import re
import urllib.parse
from datetime import datetime
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


class FactCheckAdapter(PlatformAdapter):
    """Acquires and normalizes accredited fact-checking verdicts and ClaimReview records."""

    FACT_CHECK_DOMAINS = {
        "snopes.com": "snopes",
        "politifact.com": "politifact",
        "factcheck.org": "factcheck_org",
        "altnews.in": "altnews",
        "boomlive.in": "boomlive",
        "fullfact.org": "fullfact",
    }

    @property
    def platform(self) -> str:
        return "factcheck"

    @property
    def backend_id(self) -> str:
        return "claim_review_engine"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("factcheck", "fact_check", "claimreview"):
            return True
        return any(domain in url for domain in self.FACT_CHECK_DOMAINS)

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Discover fact-checking candidates via Google Fact Check API or structured query."""
        candidates: List[CandidateSource] = []
        clean_q = query.strip()
        if not clean_q:
            return candidates

        encoded_q = urllib.parse.quote_plus(clean_q)
        import os
        api_key = os.getenv("GOOGLE_FACTCHECK_API_KEY", "").strip()
        key_param = f"&key={api_key}" if api_key else ""
        api_url = f"https://factchecktools.googleapis.com/v1alpha1/claims:search?query={encoded_q}&pageSize={limit}{key_param}"

        try:
            resp = fetch_public_http(api_url, timeout=4.0)
            if resp.status_code == 200:
                data = json.loads(resp.body.decode("utf-8", errors="replace"))
                claims = data.get("claims", [])
                for idx, item in enumerate(claims[:limit]):
                    text = item.get("text", "")
                    claimant = item.get("claimant", "")
                    claim_reviews = item.get("claimReview", [])
                    if claim_reviews:
                        cr = claim_reviews[0]
                        pub = cr.get("publisher", {}).get("name", "FactCheck")
                        site_url = cr.get("url", "")
                        rating = cr.get("textualRating", "")
                        title = f"[{pub} - {rating}] {text[:80]}"
                        candidates.append(
                            CandidateSource(
                                url=site_url or f"https://factchecktools.googleapis.com/claim/{idx}",
                                platform="factcheck",
                                title=title,
                                snippet=f"Claimant: {claimant} | Verdict: {rating} | Review: {cr.get('title', text)}",
                                search_engine="google_factcheck",
                                search_rank=idx + 1,
                                metadata={
                                    "claimant": claimant,
                                    "textual_rating": rating,
                                    "publisher": pub,
                                    "raw_claim": item,
                                    "attributed_assessment": True,
                                    "claim_review": True,
                                    "independent_proof": False,
                                    "discovery_only": True,
                                },
                            )
                        )
        except Exception as exc:
            logger.debug(f"[FactCheckAdapter] API discovery error: {type(exc).__name__}")

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

        # If candidate already contains structured metadata from discovery
        if candidate.metadata.get("raw_claim"):
            raw_json = json.dumps(candidate.metadata["raw_claim"])
            return FetchedDocument(
                url=target_url,
                status="SUCCESS",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                raw_content=raw_json,
                raw_metadata=candidate.metadata,
                latency_ms=10,
            )

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

        # 1. Parse structured ClaimReview if available
        if candidate.metadata.get("textual_rating"):
            rating = candidate.metadata.get("textual_rating", "")
            publisher = candidate.metadata.get("publisher", "FactCheck")
            claimant = candidate.metadata.get("claimant", "")
            content = (
                f"Fact-Check Assessment by {publisher}:\n"
                f"Claimant: {claimant}\n"
                f"Rating: {rating}\n"
                f"Details: {candidate.snippet}"
            )
            return [
                EvidenceFragment(
                    platform="factcheck",
                    title=candidate.title,
                    content=content,
                    url=document.url,
                    author=publisher,
                    snippet=candidate.snippet,
                    score=95.0,
                    content_depth=ContentDepth.STRUCTURED_METADATA.value,
                    retrieval_mode=RetrievalMode.DIRECT_API.value,
                    native_backend_id=self.backend_id,
                    channel_name="factcheck",
                    raw_metadata={
                        "claim_rating": rating,
                        "publisher": publisher,
                        "claimant": claimant,
                        "is_fact_check": True,
                    },
                )
            ]

        # 2. Extract ClaimReview or HTML metadata from fetched HTML
        html = document.raw_content
        verdict = "Unknown"
        title = candidate.title or "Fact-Check Report"
        snippet = candidate.snippet or ""

        # Schema.org ClaimReview JSON-LD detection
        claim_review_matches = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        for block in claim_review_matches:
            try:
                data = json.loads(block.strip())
                if isinstance(data, list):
                    items = data
                else:
                    items = [data]
                for item in items:
                    if item.get("@type") == "ClaimReview":
                        review_rating = item.get("reviewRating", {})
                        verdict = review_rating.get("alternateName") or review_rating.get("ratingValue") or verdict
                        if item.get("claimReviewed"):
                            snippet = item["claimReviewed"]
                        break
            except Exception:
                continue

        # Simple heuristic if no ld+json
        if verdict == "Unknown":
            if "pants on fire" in html.lower():
                verdict = "Pants on Fire"
            elif "false" in html.lower()[:3000]:
                verdict = "False"
            elif "mostly false" in html.lower()[:3000]:
                verdict = "Mostly False"
            elif "true" in html.lower()[:3000]:
                verdict = "True"

        # Extract main text excerpt
        text_content = re.sub(r'<[^>]+>', ' ', html)
        text_content = re.sub(r'\s+', ' ', text_content).strip()[:4000]

        return [
            EvidenceFragment(
                platform="factcheck",
                title=title,
                content=f"Verdict: {verdict}\n\n{text_content}",
                url=document.url,
                author=candidate.platform,
                snippet=snippet or text_content[:250],
                score=90.0,
                content_depth=ContentDepth.PARTIAL_CONTENT.value,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                native_backend_id=self.backend_id,
                channel_name="factcheck",
                raw_metadata={
                    "extracted_verdict": verdict,
                    "is_fact_check": True,
                },
            )
        ]
