"""
Aegis Protocol — Scout Generic Web & News Adapter
==================================================
Acquires articles and reports via persistent connection-pooled HTTP,
falling back to Jina Reader when JS execution is strictly required.
Extracts structured JSON-LD, OpenGraph, financial facts, and events.
"""

import hashlib
import logging
import re
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
    structured_metadata_extractor,
    financial_number_extractor,
    corporate_event_extractor,
    temporal_extractor,
)

logger = logging.getLogger(__name__)


class GenericWebAdapter(ScoutSourceAdapter):
    """
    Standard adapter for general web, news, and technical reports.
    """

    def can_handle(self, candidate: CandidateSource) -> bool:
        p = candidate.platform.lower()
        return p in ("web", "news", "article") or not any(s in candidate.canonical_url for s in ("reddit.com", "x.com", "twitter.com", "youtube.com", "github.com", "sec.gov"))

    def acquire(self, candidate: CandidateSource, request: ScoutSourceRequest) -> RawSource:
        target_url = candidate.canonical_url or candidate.url
        # 1. Direct HTTP GET with browser session
        status, text, headers, latency_ms, err = scout_transport.get(target_url, timeout=9.0)

        method = "scrapling_http"
        # 2. Scrapling / Playwright rescue if page is too short or blocked
        if (status != 200 or len(text) < 200) and request.allow_fallback:
            try:
                from scrapling import Fetcher
                s_resp = Fetcher.get(target_url, timeout=9.0)
                s_text = s_resp.text if hasattr(s_resp, "text") else str(s_resp)
                if len(s_text) > 200:
                    status, text, method = 200, s_text, "scrapling_http"
                    err = None
            except Exception as e_sc:
                logger.debug(f"[GenericWebAdapter] Scrapling fallback notice: {e_sc}")

            if len(text) < 200:
                try:
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page()
                        page.set_default_timeout(10000)
                        page.goto(target_url, wait_until="domcontentloaded")
                        pw_text = page.content()
                        browser.close()
                        if len(pw_text) > 200:
                            status, text, method = 200, pw_text, "playwright_rescue"
                            err = None
                except Exception as e_pw:
                    logger.debug(f"[GenericWebAdapter] Playwright rescue notice: {e_pw}")

        from datetime import datetime, timezone
        return RawSource(
            candidate=candidate,
            content_raw=text,
            content_type=headers.get("content-type", "text/html"),
            status_code=status,
            acquisition_method=method,
            latency_ms=latency_ms,
            bytes_retrieved=len(text.encode("utf-8")),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            headers=headers,
            is_authenticated=False,
            error=err
        )

    def extract(self, raw: RawSource, request: ScoutSourceRequest) -> Optional[ScoutEvidence]:
        if raw.status_code != 200 or not raw.content_raw:
            return None

        meta = structured_metadata_extractor.extract(raw.content_raw, base_url=raw.candidate.canonical_url)
        title = meta.get("title") or raw.candidate.title or "Untitled Discovered Article"
        body = meta.get("body") or raw.content_raw[:2000]
        author = meta.get("author") or meta.get("publisher") or "Web Publisher"

        pub_iso, event_iso = temporal_extractor.disambiguate(meta.get("published_at"), body)
        facts = financial_number_extractor.extract_facts(body)
        events = corporate_event_extractor.extract_events(body, company_name=request.target_entity)

        # Hash for unique evidence ID
        hash_id = hashlib.sha256(raw.candidate.canonical_url.encode()).hexdigest()[:10]
        evidence_id = f"ev_web_{hash_id}"

        tier = SourceTier.TIER_2_PRESS.value if any(k in raw.candidate.canonical_url for k in ("reuters.com", "bloomberg.com", "wsj.com", "ft.com", "cnbc.com", "marketwatch.com")) else SourceTier.TIER_3_SPECIALIST.value

        return ScoutEvidence(
            evidence_id=evidence_id,
            url=raw.candidate.url,
            canonical_url=raw.candidate.canonical_url,
            platform=raw.candidate.platform or "web",
            source_type="article",
            source_tier=tier,
            external_id=raw.candidate.canonical_url,
            title=title,
            author=author,
            body=body,
            snippet=meta.get("description") or body[:250],
            published_at=pub_iso,
            event_at=event_iso,
            retrieved_at=raw.retrieved_at,
            financial_facts=facts,
            events=events,
            entities=[request.target_entity] if request.target_entity else [],
            tickers=request.tickers,
            score=raw.candidate.candidate_score,
            retrieval_mode=raw.acquisition_method,
            adapter="GenericWebAdapter",
            search_engine=raw.candidate.discovery_engine,
            is_authenticated=False,
            is_primary=False,
            provenance={
                "status_code": raw.status_code,
                "latency_ms": raw.latency_ms,
                "bytes": raw.bytes_retrieved,
                "acquisition_method": raw.acquisition_method
            }
        )
