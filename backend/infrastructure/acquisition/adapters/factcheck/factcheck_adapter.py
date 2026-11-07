"""Aegis Protocol — Fact-Checking Registry Adapters.

Structured adapters for accredited fact-checking registries and ClaimReview schemas:
- Google Fact Check Tools / ClaimReview
- Snopes, PolitiFact, FactCheck.org
- Alt News, BOOM Live, Full Fact, Lead Stories, Check Your Fact
- AFP Fact Check, BBC Verify, Reuters Fact Check, AP News Fact Check
- Health Feedback, Climate Feedback, The Quint WebQoof, Vishwas News
"""

from __future__ import annotations

import json
import logging
import os
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
        "leadstories.com": "leadstories",
        "checkyourfact.com": "checkyourfact",
        "factcheck.afp.com": "afp_factcheck",
        "afp.com": "afp_factcheck",
        "thequint.com": "thequint_webqoof",
        "vishwasnews.com": "vishwasnews",
        "indiatoday.in": "indiatoday_afwa",
        "pib.gov.in": "pib_factcheck",
        "healthfeedback.org": "healthfeedback",
        "climatefeedback.org": "climatefeedback",
        "sciencefeedback.co": "sciencefeedback",
        "poynter.org": "poynter_ifcn",
        "reuters.com": "reuters_factcheck",
        "apnews.com": "ap_factcheck",
        "bbc.com": "bbc_verify",
        "bbc.co.uk": "bbc_verify",
        "washingtonpost.com": "wapo_factchecker",
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
        """Discover fact-checking candidates via Google Fact Check API or live news feed fallback."""
        candidates: List[CandidateSource] = []
        clean_q = query.strip()
        if not clean_q:
            return candidates

        encoded_q = urllib.parse.quote_plus(clean_q)
        api_key = os.getenv("GOOGLE_FACTCHECK_API_KEY", "").strip()
        if api_key:
            key_param = f"&key={api_key}"
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
                                        "discovery_published_at": cr.get("reviewDate", ""),
                                        "discovery_author": pub,
                                    },
                                )
                            )
            except Exception as exc:
                logger.debug(f"[FactCheckAdapter] API discovery error: {type(exc).__name__}")

        if len(candidates) < limit:
            feed_candidates = self._discover_feed_fallback(clean_q, limit=limit - len(candidates))
            candidates.extend(feed_candidates)

        return candidates

    def _discover_feed_fallback(self, clean_q: str, limit: int = 5) -> List[CandidateSource]:
        """Zero-auth public news and accredited fact-checking RSS fallback discovery."""
        import feedparser
        results: List[CandidateSource] = []
        seen = set()

        queries = [
            f"{clean_q} fact check",
            f"{clean_q} site:snopes.com OR site:politifact.com OR site:factcheck.org OR site:boomlive.in OR site:altnews.in",
        ]
        for q_text in queries:
            if len(results) >= limit:
                break
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(q_text)}&hl=en-US&gl=US&ceid=US:en"
            try:
                resp = fetch_public_http(url, timeout=4.0, max_bytes=1_000_000)
                if resp.status_code == 200:
                    raw_body = getattr(resp, "body", b"")
                    feed = feedparser.parse(raw_body)
                    for entry in feed.get("entries", []):
                        link = entry.get("link", "")
                        title = entry.get("title", "")
                        if not link or link in seen:
                            continue
                        seen.add(link)
                        src = entry.get("source") or {}
                        pub = src.get("title", "Fact Check News Wire") if isinstance(src, dict) else "Fact Check"
                        pub_date = entry.get("published", "")
                        results.append(
                            CandidateSource(
                                url=link,
                                platform="factcheck",
                                title=title,
                                snippet=f"Publisher: {pub} | Date: {pub_date} | {title}",
                                search_engine="google_news_factcheck",
                                search_rank=len(results) + 1,
                                metadata={
                                    "publisher": pub,
                                    "published_at": pub_date,
                                    "is_fact_check": True,
                                    "attributed_assessment": True,
                                    "discovery_only": True,
                                    "discovery_published_at": pub_date,
                                    "discovery_author": pub,
                                },
                            )
                        )
                        if len(results) >= limit:
                            break
            except Exception as exc:
                logger.debug(f"[FactCheckAdapter] Feed fallback notice: {exc}")
        return results

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

        # 1. Parse structured ClaimReview if available from discovery
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
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("@type") == "ClaimReview":
                        review_rating = item.get("reviewRating", {})
                        verdict = review_rating.get("alternateName") or review_rating.get("ratingValue") or verdict
                        if item.get("claimReviewed"):
                            snippet = item["claimReviewed"]
                        break
            except Exception:
                continue

        # Simple heuristic if no ld+json
        if verdict == "Unknown":
            low_html = html.lower()[:4000]
            if "pants on fire" in low_html:
                verdict = "Pants on Fire"
            elif "mostly false" in low_html:
                verdict = "Mostly False"
            elif "false" in low_html:
                verdict = "False"
            elif "misleading" in low_html:
                verdict = "Misleading"
            elif "unproven" in low_html:
                verdict = "Unproven"
            elif "true" in low_html:
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
                author=candidate.metadata.get("publisher") or candidate.platform,
                snippet=snippet or text_content[:250],
                score=90.0,
                content_depth=ContentDepth.PARTIAL_CONTENT.value,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                native_backend_id=self.backend_id,
                channel_name="factcheck",
                raw_metadata={
                    "extracted_verdict": verdict,
                    "is_fact_check": True,
                    "publisher": candidate.metadata.get("publisher", ""),
                },
            )
        ]
