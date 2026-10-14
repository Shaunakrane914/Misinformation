"""
Aegis Protocol — Fact Check & ClaimReview Aggregator Acquisition Adapter
========================================================================
Acquires published fact-checks, claimant attributions, and ratings from public
fact-checking organizations (ClaimReview standard schema via Fact Check Tools API).
Enforces 15-point source contract, SSRF safety, and bounded payload limits.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.network.http import (
    decode_bounded_http_body,
    fetch_public_http,
    BoundedHTTPResponse,
)
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode

logger = logging.getLogger(__name__)


def fetch_fact_check_claims(
    query: str,
    limit: int = 5,
    api_key: Optional[str] = None,
    http_fetcher: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Acquire verified fact-checks for a query using public ClaimReview endpoints.
    Endpoint: https://factchecktools.googleapis.com/v1alpha1/claims:search
    """
    fetcher = http_fetcher if http_fetcher is not None else fetch_public_http
    clean_q = query.strip()
    encoded = urllib.parse.quote(clean_q)
    key = api_key or os.getenv("GOOGLE_FACTCHECK_API_KEY", "")

    url = f"https://factchecktools.googleapis.com/v1alpha1/claims:search?query={encoded}&pageSize={min(limit, 10)}"
    if not key:
        return {"status": "AUTH_REQUIRED", "items": [], "error": "GOOGLE_FACTCHECK_API_KEY is not configured", "transport": {"endpoint": url, "network_observed": False}}

    headers = {
        "X-Goog-Api-Key": key,
        "Accept": "application/json",
        "User-Agent": "AegisProtocol MisinfoResearch/1.0",
        "Accept-Encoding": "identity",
    }

    try:
        response: BoundedHTTPResponse = fetcher(
            url,
            headers=headers,
            timeout=5.0,
            max_bytes=1_000_000,
        )
        raw_bytes = decode_bounded_http_body(response, max_bytes=1_000_000)
        data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    except Exception as e:
        status_code = getattr(e, "status_code", None)
        outcome = "AUTH_REQUIRED" if status_code in {401, 403} else "RATE_LIMITED" if status_code == 429 else "FAILED"
        logger.warning("[FactCheck] Fetch failure: %s", outcome)
        return {
            "status": outcome,
            "error": f"Provider request failed ({type(e).__name__})",
            "items": [],
            "transport": {"endpoint": url, "status_code": status_code, "network_observed": getattr(e, "network_observed", False)}
        }

    raw_claims = data.get("claims", [])
    parsed_items: List[Dict[str, Any]] = []

    for c in raw_claims[:limit]:
        claim_text = c.get("text", "")
        claimant = c.get("claimant", "")
        claim_date = c.get("claimDate", "")

        reviews = c.get("claimReview", [])
        for r in reviews:
            pub = r.get("publisher", {})
            pub_name = pub.get("name", "Fact Checker")
            pub_site = pub.get("site", "")
            rev_url = r.get("url", "")
            rev_title = r.get("title", "")
            rev_date = r.get("reviewDate", "")
            rating = r.get("textRating", "Unrated")

            parsed_items.append({
                "claim_text": claim_text,
                "claimant": claimant,
                "claim_date": claim_date,
                "publisher_name": pub_name,
                "publisher_site": pub_site,
                "review_url": rev_url,
                "review_title": rev_title,
                "review_date": rev_date,
                "text_rating": rating,
            })
            if len(parsed_items) >= limit:
                break
        if len(parsed_items) >= limit:
            break

    return {
        "status": "SUCCESS",
        "items": parsed_items,
        "transport": {
            "endpoint": url,
            "status_code": response.status_code,
            "latency_ms": response.latency_ms,
        }
    }


def normalize_fact_check_items(
    items: List[Dict[str, Any]],
    query_id: str = "",
    query_class: str = "",
    query_text: str = ""
) -> List[EvidenceFragment]:
    """Normalize ClaimReview fact-check items into typed EvidenceFragments."""
    fragments: List[EvidenceFragment] = []
    for item in items:
        rating = item["text_rating"]
        pub = item["publisher_name"]
        title = f"{pub} Fact Check: {rating} — {item['claim_text'][:80]}"
        snippet = (
            f"Fact Check by {pub}: Rating: '{rating}'. "
            f"Claim evaluated: \"{item['claim_text']}\" (Claimed by {item['claimant']}). "
            f"Review title: {item['review_title']}. Date: {item['review_date']}."
        )
        frag = EvidenceFragment(
            platform="fact_check",
            title=title,
            content=snippet,
            snippet=snippet,
            url=item["review_url"],
            author=pub,
            published=item["review_date"],
            score=92.0,
            retrieval_method="claimreview_api",
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id="factcheck-tools-api",
            channel_name="fact_check",
            requested_channel="fact_check",
            actual_retrieval_channel="fact_check",
            content_depth="DIRECT_METADATA",
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            raw_metadata={
                "claim_text": item["claim_text"],
                "claimant": item["claimant"],
                "text_rating": rating,
                "publisher_name": pub,
                "review_date": item["review_date"],
                "claim_date": item.get("claim_date", ""),
                "rating_attribution": "publisher_reported_not_aegis_verdict",
                "review_body_acquired": False,
                "source_role": "SECONDARY",
                "source_tier": "TIER_2_INVESTIGATIVE",
                "source_authority": "INDEPENDENT_FACT_CHECKER",
                "primary_source": False,
                "reliability_score": 0.92,
                "canonical_url": item["review_url"],
            }
        )
        fragments.append(frag)
    return fragments
