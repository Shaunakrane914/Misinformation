"""
Aegis Protocol — Scout Primary Filing & Corporate IR Adapter
============================================================
Acquires official SEC EDGAR filings, exchange releases, and investor relations
disclosures. Tier 1 authority.
"""

import hashlib
import logging
import os
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
from backend.services.research.source_quality import registered_authority_url, canonical_hostname, hostname_matches, SourceQualityEngine, VERIFIED_CORPORATE_DOMAINS
from backend.services.research.research_models import EvidenceItem
from backend.agents.scout.sources.extraction import (
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
        return registered_authority_url(candidate.canonical_url)

    def acquire(self, candidate: CandidateSource, request: ScoutSourceRequest) -> RawSource:
        if not self.can_handle(candidate):
            raise ValueError("Unregistered authority origin")
        target_url = candidate.canonical_url or candidate.url
        headers = {}
        # SEC EDGAR requires compliant User-Agent format: Sample Company AdminContact@domain.com
        if hostname_matches(canonical_hostname(target_url), "sec.gov"):
            user_agent = os.environ.get("SEC_USER_AGENT", "").strip()
            if not user_agent:
                raise ValueError("SEC_USER_AGENT owner-approved contact is required")
            headers["User-Agent"] = user_agent

        status, text, resp_headers, lat, err = scout_transport.get(target_url, headers=headers, timeout=5.0)

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
        if raw.status_code != 200 or not raw.content_raw or not self.can_handle(raw.candidate):
            return None
        observed_url = raw.headers.get("X-Aegis-Observed-Endpoint", raw.candidate.canonical_url)
        if not registered_authority_url(observed_url):
            return None

        meta = structured_metadata_extractor.extract(raw.content_raw, base_url=raw.candidate.canonical_url)
        title = meta.get("title") or raw.candidate.title or "Official Disclosure / Filing"
        body = meta.get("body") or raw.content_raw[:3000]
        host = canonical_hostname(observed_url)
        target = next((name for name, domains in VERIFIED_CORPORATE_DOMAINS.items()
                       if any(hostname_matches(host, domain) for domain in domains)), "")
        classification = SourceQualityEngine().classify_and_score(EvidenceItem(
            id="authority", canonical_url=observed_url, title=title, content=body,
        ), target)

        pub_iso, event_iso = temporal_extractor.disambiguate(meta.get("published_at"), body)
        facts = financial_number_extractor.extract_facts(body)
        events = corporate_event_extractor.extract_events(body, company_name=request.target_entity)

        hash_id = hashlib.sha256(raw.candidate.canonical_url.encode()).hexdigest()[:10]
        evidence_id = f"ev_prim_{hash_id}"

        return ScoutEvidence(
            evidence_id=evidence_id,
            url=raw.candidate.url,
            canonical_url=observed_url,
            platform="primary_filing",
            source_type=raw.candidate.source_type or "filing",
            source_tier=SourceTier.TIER_1_PRIMARY.value if classification.primary_source else SourceTier.TIER_5_AGGREGATE.value,
            external_id=raw.candidate.canonical_url,
            title=title,
            author=meta.get("author") or meta.get("publisher") or "",
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
            is_primary=classification.primary_source,
            provenance={
                "source_tier": SourceTier.TIER_1_PRIMARY.value if classification.primary_source else SourceTier.TIER_5_AGGREGATE.value,
                "acquisition_method": raw.acquisition_method,
                "latency_ms": raw.latency_ms
            }
        )
