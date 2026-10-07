"""
Aegis Protocol — Scout Primary Filing & Corporate IR Adapter
============================================================
Acquires official SEC EDGAR filings, exchange releases, and investor relations
disclosures. Tier 1 authority.
"""

import hashlib
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
    structured_metadata_extractor,
    financial_number_extractor,
    corporate_event_extractor,
    temporal_extractor,
)

logger = logging.getLogger(__name__)


class PrimaryFilingAdapter(ScoutSourceAdapter):
    """
    Acquires official SEC filings, company investor relations, and exchange notices.
    Assigns Tier 1 Primary authority.
    """

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = candidate.canonical_url.lower()
        return (
            candidate.platform == "primary_filing"
            or "sec.gov" in url
            or "investor." in url
            or "ir." in url
            or "/investors" in url
            or "bseindia.com" in url
            or "nseindia.com" in url
            or candidate.metadata.get("is_primary_lead", False)
        )

    def acquire(self, candidate: CandidateSource, request: ScoutSourceRequest) -> RawSource:
        target_url = candidate.canonical_url or candidate.url
        headers = {}
        # SEC EDGAR requires compliant User-Agent format: Sample Company AdminContact@domain.com
        if "sec.gov" in target_url:
            headers["User-Agent"] = "AegisProtocolResearch research@aegisprotocol.internal"

        status, text, resp_headers, lat, err = scout_transport.get(target_url, headers=headers, timeout=10.0)

        return RawSource(
            candidate=candidate,
            content_raw=text,
            content_type=resp_headers.get("content-type", "text/html"),
            status_code=status,
            acquisition_method="primary_official_retrieval",
            latency_ms=lat,
            bytes_retrieved=len(text.encode("utf-8")),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            headers=resp_headers,
            is_authenticated=False,
            error=err
        )

    def extract(self, raw: RawSource, request: ScoutSourceRequest) -> Optional[ScoutEvidence]:
        if raw.status_code != 200 or not raw.content_raw:
            return None

        meta = structured_metadata_extractor.extract(raw.content_raw, base_url=raw.candidate.canonical_url)
        title = meta.get("title") or raw.candidate.title or "Official Disclosure / Filing"
        body = meta.get("body") or raw.content_raw[:3000]

        pub_iso, event_iso = temporal_extractor.disambiguate(meta.get("published_at"), body)
        facts = financial_number_extractor.extract_facts(body)
        events = corporate_event_extractor.extract_events(body, company_name=request.target_entity)

        hash_id = hashlib.sha256(raw.candidate.canonical_url.encode()).hexdigest()[:10]
        evidence_id = f"ev_prim_{hash_id}"

        return ScoutEvidence(
            evidence_id=evidence_id,
            url=raw.candidate.url,
            canonical_url=raw.candidate.canonical_url,
            platform="primary_filing",
            source_type=raw.candidate.source_type or "filing",
            source_tier=SourceTier.TIER_1_PRIMARY.value,
            external_id=raw.candidate.canonical_url,
            title=f"[OFFICIAL PRIMARY] {title}",
            author=meta.get("author") or meta.get("publisher") or "Company Disclosures",
            body=body,
            snippet=body[:260],
            published_at=pub_iso,
            event_at=event_iso,
            retrieved_at=raw.retrieved_at,
            financial_facts=facts,
            events=events,
            entities=[request.target_entity] if request.target_entity else [],
            tickers=request.tickers,
            score=min(1.0, raw.candidate.candidate_score + 0.20),
            retrieval_mode=raw.acquisition_method,
            adapter="PrimaryFilingAdapter",
            search_engine=raw.candidate.discovery_engine,
            is_authenticated=False,
            is_primary=True,
            provenance={
                "source_tier": "TIER_1_PRIMARY",
                "acquisition_method": raw.acquisition_method,
                "latency_ms": raw.latency_ms
            }
        )
