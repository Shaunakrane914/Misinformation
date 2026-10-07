"""
Aegis Protocol — Scout Reddit Adapter
=====================================
Acquires Reddit submissions and comments via Arctic Shift zero-auth public mirror
without user authentication, cookies, or API keys.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from backend.services.agent_reach.scout.adapters.base import ScoutSourceAdapter
from backend.services.agent_reach.scout.models import (
    CandidateSource,
    RawSource,
    ScoutEvidence,
    ScoutSourceRequest,
    SourceTier,
)
from backend.services.agent_reach.scout.transport import scout_transport
from backend.services.agent_reach.scout.extraction import (
    financial_number_extractor,
    corporate_event_extractor,
)

logger = logging.getLogger(__name__)


class RedditAdapter(ScoutSourceAdapter):
    """
    Acquires public Reddit discussions via Arctic Shift REST API.
    Zero-auth default.
    """

    ARCTIC_SHIFT_BASE = "https://arctic-shift.photon-reddit.com/api"

    def can_handle(self, candidate: CandidateSource) -> bool:
        return candidate.platform == "reddit" or "reddit.com" in candidate.canonical_url

    def acquire(self, candidate: CandidateSource, request: ScoutSourceRequest) -> RawSource:
        post_id = candidate.external_id
        # Fallback to direct HTTP if external_id missing
        if not post_id or not post_id.isalnum():
            status, text, headers, lat, err = scout_transport.get(candidate.canonical_url, timeout=8.0)
            return RawSource(
                candidate=candidate,
                content_raw=text,
                content_type="text/html",
                status_code=status,
                acquisition_method="direct_http",
                latency_ms=lat,
                bytes_retrieved=len(text.encode("utf-8")),
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                is_authenticated=False,
                error=err
            )

        # Query Arctic Shift mirror for submission
        api_url = f"{self.ARCTIC_SHIFT_BASE}/posts/ids?ids={post_id}"
        status, text, headers, lat, err = scout_transport.get(api_url, timeout=7.0)

        method = "zero_auth_public_mirror"
        if status != 200 or not text:
            # Fallback to direct HTTP with .json endpoint
            json_url = f"{candidate.canonical_url.rstrip('/')}.json"
            status, text, headers, lat, err = scout_transport.get(json_url, timeout=7.0)
            method = "reddit_json_stream"

        return RawSource(
            candidate=candidate,
            content_raw=text,
            content_type="application/json",
            status_code=status,
            acquisition_method=method,
            latency_ms=lat,
            bytes_retrieved=len(text.encode("utf-8")),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            headers=headers,
            is_authenticated=False,
            error=err
        )

    def extract(self, raw: RawSource, request: ScoutSourceRequest) -> Optional[ScoutEvidence]:
        if raw.status_code != 200 or not raw.content_raw:
            return None

        title = raw.candidate.title or "Reddit Discussion"
        body = ""
        author = raw.candidate.author or "u/community"
        pub_iso = datetime.now(timezone.utc).isoformat()
        subreddit = raw.candidate.subreddit or "stocks"

        try:
            data = json.loads(raw.content_raw)
            # 1. Arctic Shift schema
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], list) and data["data"]:
                item = data["data"][0]
                title = item.get("title") or title
                body = item.get("selftext") or ""
                author = f"u/{item.get('author', 'community')}"
                subreddit = item.get("subreddit") or subreddit
                created_utc = item.get("created_utc")
                if created_utc:
                    pub_iso = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
            # 2. Reddit native JSON schema
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {})
                title = post_data.get("title") or title
                body = post_data.get("selftext") or ""
                author = f"u/{post_data.get('author', 'community')}"
                subreddit = post_data.get("subreddit") or subreddit
                created_utc = post_data.get("created_utc")
                if created_utc:
                    pub_iso = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
        except Exception:
            body = raw.content_raw[:1500]

        facts = financial_number_extractor.extract_facts(f"{title}\n{body}")
        events = corporate_event_extractor.extract_events(f"{title}\n{body}", company_name=request.target_entity)

        hash_id = hashlib.sha256(raw.candidate.canonical_url.encode()).hexdigest()[:10]
        evidence_id = f"ev_rd_{hash_id}"

        return ScoutEvidence(
            evidence_id=evidence_id,
            url=raw.candidate.url,
            canonical_url=raw.candidate.canonical_url,
            platform="reddit",
            source_type=raw.candidate.source_type or "post",
            source_tier=SourceTier.TIER_4_COMMUNITY.value,
            external_id=raw.candidate.external_id,
            title=f"[r/{subreddit}] {title}",
            author=author,
            body=f"{title}\n\n{body}" if body else title,
            snippet=body[:240] if body else title,
            published_at=pub_iso,
            event_at=None,
            retrieved_at=raw.retrieved_at,
            financial_facts=facts,
            events=events,
            entities=[request.target_entity] if request.target_entity else [],
            tickers=request.tickers,
            score=raw.candidate.candidate_score,
            retrieval_mode=raw.acquisition_method,
            adapter="RedditAdapter",
            search_engine=raw.candidate.discovery_engine,
            is_authenticated=False,
            is_primary=False,
            provenance={
                "subreddit": subreddit,
                "acquisition_method": raw.acquisition_method,
                "latency_ms": raw.latency_ms
            }
        )
