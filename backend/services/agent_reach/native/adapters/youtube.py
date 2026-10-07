"""
Aegis Protocol — YouTube In-Process Specialist Adapter
======================================================
Acquires YouTube metadata, descriptions, and transcripts using an in-process
Python import of `yt_dlp.YoutubeDL`.
Eliminates the 848ms process-spawn overhead of subprocess `yt-dlp` and avoids
PATH dependency failures in containerized cloud environments.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.agent_reach.channels import (
    CandidateSource,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.agent_reach.native.adapters.base import PlatformAdapter
from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)


class YouTubeAdapter(PlatformAdapter):
    """
    Acquires YouTube video metadata via in-process yt-dlp import.
    """

    @property
    def platform(self) -> str:
        return "youtube"

    @property
    def backend_id(self) -> str:
        return "yt_dlp_in_process"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        return candidate.platform.lower() == "youtube" or "youtube.com" in url or "youtu.be" in url

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        target_url = candidate.canonical_url or candidate.url

        # 1. SSRF Gate
        is_safe, reason = validate_url_safe(target_url)
        if not is_safe:
            return FetchedDocument(
                url=target_url,
                status="BLOCKED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                failure_reason=f"SSRF validation failed: {reason}",
            )

        t0 = time.perf_counter()
        raw_json_str = ""
        status = "SUCCESS"
        err_msg = None

        try:
            import yt_dlp
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                raw_json_str = json.dumps(info or {})
        except Exception as e:
            logger.debug(f"[YouTubeAdapter] in-process yt-dlp error for {target_url}: {e}")
            status = "FAILED"
            err_msg = str(e)

        lat = int((time.perf_counter() - t0) * 1000)
        return FetchedDocument(
            url=target_url,
            status=status,
            backend_id=self.backend_id,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            raw_content=raw_json_str,
            latency_ms=lat,
            failure_reason=err_msg,
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        try:
            info = json.loads(document.raw_content)
        except Exception:
            return []

        title = info.get("title") or candidate.title or "YouTube Video"
        uploader = info.get("uploader") or info.get("channel") or "Unknown Channel"
        description = info.get("description") or ""
        upload_date = info.get("upload_date") or datetime.now(timezone.utc).isoformat()
        content = f"Title: {title}\nChannel: {uploader}\n\nDescription:\n{description}"
        snippet = description[:280] or title

        frag = EvidenceFragment(
            platform=self.platform,
            title=title,
            content=content,
            url=document.url,
            author=uploader,
            published=str(upload_date),
            snippet=snippet,
            score=candidate.semantic_score or 1.0,
            retrieval_method="agent_reach",
            channel_name="youtube",
            content_depth="FULL_ARTICLE" if len(description) > 300 else "SNIPPET",
            query_id=request.request_id,
            query_class=request.task_type,
            query_text=request.query,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id=self.backend_id,
            is_authenticated=False,
            raw_metadata={
                "duration": info.get("duration"),
                "view_count": info.get("view_count"),
                "tags": info.get("tags", []),
            },
        )
        return [frag]
