"""
Aegis Protocol — Scout X / Twitter Adapter
==========================================
Acquires X/Twitter statuses and profiles via FxTwitter zero-auth public mirror
without user authentication, cookies, or API secrets.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from backend.agents.scout.sources.adapters.base import ScoutSourceAdapter
from backend.agents.scout.sources.models import (
    CandidateSource,
    RawSource,
    ScoutEvidence,
    ScoutSourceRequest,
    SourceTier,
)
from backend.agents.scout.sources.transport import scout_transport
from backend.agents.scout.sources.extraction import (
    financial_number_extractor,
    corporate_event_extractor,
)

logger = logging.getLogger(__name__)


class XAdapter(ScoutSourceAdapter):
    """
    Acquires public X/Twitter posts via FxTwitter mirror.
    Zero-auth default.
    """

    FXTWITTER_BASE = "https://api.fxtwitter.com"

    def can_handle(self, candidate: CandidateSource) -> bool:
        return candidate.platform == "twitter" or any(s in candidate.canonical_url for s in ("x.com", "twitter.com"))

    def acquire(self, candidate: CandidateSource, request: ScoutSourceRequest) -> RawSource:
        status_id = candidate.external_id
        handle = candidate.handle or "i"

        # Query FxTwitter status endpoint
        if status_id and status_id.isdigit():
            api_url = f"{self.FXTWITTER_BASE}/{handle}/status/{status_id}"
            status, text, headers, lat, err = scout_transport.get(api_url, timeout=7.0)
            method = "zero_auth_public_mirror"
        elif candidate.source_type == "profile" and handle:
            api_url = f"{self.FXTWITTER_BASE}/{handle}"
            status, text, headers, lat, err = scout_transport.get(api_url, timeout=7.0)
            method = "zero_auth_public_mirror"
        else:
            status, text, headers, lat, err = scout_transport.get(candidate.canonical_url, timeout=8.0)
            method = "direct_http"

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

        body = ""
        author = raw.candidate.handle or "@unknown"
        pub_iso = datetime.now(timezone.utc).isoformat()
        engagement = {}

        try:
            data = json.loads(raw.content_raw)
            tweet = data.get("tweet") or data
            if isinstance(tweet, dict):
                body = tweet.get("text") or ""
                author_info = tweet.get("author", {})
                author = f"@{author_info.get('screen_name', raw.candidate.handle or 'x_user')}"
                created_at = tweet.get("created_at")
                if created_at:
                    pub_iso = created_at
                engagement = {
                    "likes": tweet.get("likes", 0),
                    "retweets": tweet.get("retweets", 0),
                    "replies": tweet.get("replies", 0),
                }
        except Exception:
            body = raw.content_raw[:1000]

        title = f"{author} on X: \"{body[:90]}...\"" if len(body) > 90 else f"{author} on X: \"{body}\""
        facts = financial_number_extractor.extract_facts(body)
        events = corporate_event_extractor.extract_events(body, company_name=request.target_entity)

        hash_id = hashlib.sha256(raw.candidate.canonical_url.encode()).hexdigest()[:10]
        evidence_id = f"ev_x_{hash_id}"

        return ScoutEvidence(
            evidence_id=evidence_id,
            url=raw.candidate.url,
            canonical_url=raw.candidate.canonical_url,
            platform="twitter",
            source_type=raw.candidate.source_type or "status",
            source_tier=SourceTier.TIER_4_COMMUNITY.value,
            external_id=raw.candidate.external_id,
            title=title,
            author=author,
            body=body,
            snippet=body[:240],
            published_at=pub_iso,
            event_at=None,
            retrieved_at=raw.retrieved_at,
            financial_facts=facts,
            events=events,
            entities=[request.target_entity] if request.target_entity else [],
            tickers=request.tickers,
            score=raw.candidate.candidate_score,
            retrieval_mode=raw.acquisition_method,
            adapter="XAdapter",
            search_engine=raw.candidate.discovery_engine,
            is_authenticated=False,
            is_primary=False,
            provenance={
                "author": author,
                "engagement": engagement,
                "acquisition_method": raw.acquisition_method,
                "latency_ms": raw.latency_ms
            }
        )
