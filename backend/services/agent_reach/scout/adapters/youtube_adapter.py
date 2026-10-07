"""
Aegis Protocol — Scout YouTube Adapter
======================================
Acquires video metadata, descriptions, and transcripts via yt-dlp specialist backend.
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


class YouTubeAdapter(ScoutSourceAdapter):
    """
    Acquires YouTube video metadata, analyst breakdowns, and transcripts.
    """

    def can_handle(self, candidate: CandidateSource) -> bool:
        return candidate.platform == "youtube" or "youtube.com" in candidate.canonical_url or "youtu.be" in candidate.canonical_url

    def acquire(self, candidate: CandidateSource, request: ScoutSourceRequest) -> RawSource:
        target_url = candidate.canonical_url or candidate.url
        content_raw = ""
        method = "yt_dlp"
        status = 200
        lat = 100
        err = None

        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                content_raw = json.dumps(info or {})
        except Exception as e:
            logger.debug(f"[YouTubeAdapter] yt-dlp notice: {e}, falling back to HTTP")
            status, content_raw, _, lat, err = scout_transport.get(target_url, timeout=8.0)
            method = "direct_http"

        return RawSource(
            candidate=candidate,
            content_raw=content_raw,
            content_type="application/json" if method == "yt_dlp" else "text/html",
            status_code=status,
            acquisition_method=method,
            latency_ms=lat,
            bytes_retrieved=len(content_raw.encode("utf-8")),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            is_authenticated=False,
            error=err
        )

    def extract(self, raw: RawSource, request: ScoutSourceRequest) -> Optional[ScoutEvidence]:
        if not raw.content_raw:
            return None

        title = raw.candidate.title or "YouTube Video Analysis"
        description = raw.candidate.snippet or ""
        author = "YouTube Channel"
        pub_iso = datetime.now(timezone.utc).isoformat()

        try:
            data = json.loads(raw.content_raw)
            if isinstance(data, dict):
                title = data.get("title") or title
                description = data.get("description") or description
                author = data.get("uploader") or data.get("channel") or author
                upload_date = data.get("upload_date")
                if upload_date and len(upload_date) == 8:
                    pub_iso = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}T00:00:00Z"
        except Exception:
            description = raw.content_raw[:1000]

        facts = financial_number_extractor.extract_facts(f"{title}\n{description}")
        events = corporate_event_extractor.extract_events(f"{title}\n{description}", company_name=request.target_entity)

        hash_id = hashlib.sha256(raw.candidate.canonical_url.encode()).hexdigest()[:10]
        evidence_id = f"ev_yt_{hash_id}"

        return ScoutEvidence(
            evidence_id=evidence_id,
            url=raw.candidate.url,
            canonical_url=raw.candidate.canonical_url,
            platform="youtube",
            source_type="video",
            source_tier=SourceTier.TIER_4_COMMUNITY.value,
            external_id=raw.candidate.canonical_url,
            title=f"[Video] {title}",
            author=author,
            body=f"{title}\n\n{description}",
            snippet=description[:240],
            published_at=pub_iso,
            event_at=None,
            retrieved_at=raw.retrieved_at,
            financial_facts=facts,
            events=events,
            entities=[request.target_entity] if request.target_entity else [],
            tickers=request.tickers,
            score=raw.candidate.candidate_score,
            retrieval_mode=raw.acquisition_method,
            adapter="YouTubeAdapter",
            search_engine=raw.candidate.discovery_engine,
            is_authenticated=False,
            is_primary=False,
            provenance={
                "channel": author,
                "acquisition_method": raw.acquisition_method,
                "latency_ms": raw.latency_ms
            }
        )
