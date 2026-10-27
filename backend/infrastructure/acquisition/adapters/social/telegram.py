"""Aegis Protocol — Telegram Public Web Channel Preview Adapter.

Acquires public channel messages and broadcast posts from Telegram's web preview
mirrors (https://t.me/s/<channel>) without requiring Telegram API authentication.
"""

from __future__ import annotations

import logging
import re
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


class TelegramPublicAdapter(PlatformAdapter):
    """Acquires posts from Telegram public channel web previews."""

    @property
    def platform(self) -> str:
        return "telegram"

    @property
    def backend_id(self) -> str:
        return "telegram_web_preview"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        return candidate.platform.lower() in ("telegram", "tg") or "t.me/" in url

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        target_url = candidate.canonical_url or candidate.url
        # Normalize to web preview URL /s/
        if "t.me/" in target_url and "/s/" not in target_url:
            target_url = target_url.replace("t.me/", "t.me/s/")

        is_safe, reason = validate_url_safe(target_url)
        if not is_safe:
            return FetchedDocument(
                url=target_url,
                status="BLOCKED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                failure_reason=f"SSRF policy blocked URL: {reason}",
            )

        try:
            resp = fetch_public_http(target_url, timeout=5.0, max_bytes=1_000_000)
            return FetchedDocument(
                url=target_url,
                status="SUCCESS" if resp.status_code == 200 else "FAILED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                raw_content=resp.body.decode("utf-8", errors="replace"),
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

        html = document.raw_content
        # Extract channel name
        channel_name_match = re.search(r'<div class="tgme_channel_info_title">([^<]+)</div>', html)
        channel_title = channel_name_match.group(1).strip() if channel_name_match else "Telegram Channel"

        # Extract message text blocks
        messages = re.findall(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            html,
            re.DOTALL,
        )

        fragments: List[EvidenceFragment] = []
        for idx, msg_html in enumerate(messages[:5]):
            clean_text = re.sub(r'<[^>]+>', ' ', msg_html)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            if not clean_text:
                continue

            fragments.append(
                EvidenceFragment(
                    platform="telegram",
                    title=f"[{channel_title}] Post #{idx + 1}",
                    content=clean_text,
                    url=document.url,
                    author=channel_title,
                    snippet=clean_text[:250],
                    score=72.0,
                    content_depth=ContentDepth.SOCIAL_POST.value,
                    retrieval_mode=RetrievalMode.WEB_READER.value,
                    native_backend_id=self.backend_id,
                    channel_name="telegram",
                    raw_metadata={
                        "channel_title": channel_title,
                        "is_telegram_channel": True,
                    },
                )
            )

        if not fragments:
            clean_all = re.sub(r'<[^>]+>', ' ', html)
            clean_all = re.sub(r'\s+', ' ', clean_all).strip()[:2000]
            fragments.append(
                EvidenceFragment(
                    platform="telegram",
                    title=channel_title,
                    content=clean_all,
                    url=document.url,
                    author=channel_title,
                    snippet=clean_all[:250],
                    score=65.0,
                    content_depth=ContentDepth.SOCIAL_POST.value,
                    retrieval_mode=RetrievalMode.WEB_READER.value,
                    native_backend_id=self.backend_id,
                    channel_name="telegram",
                )
            )

        return fragments
