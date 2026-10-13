"""
Aegis Protocol — Bounded Public Web Adapter
===================================================
Authoritative typed web acquisition uses the connection-validated public HTTP
transport. Compatibility helper names are retained, but browser rescue is not
automatically authorized because its subrequests cannot use that transport.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.services.agent_reach.channels import (
    CandidateSource,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.agent_reach.native.adapters.base import PlatformAdapter
from backend.services.url_validator import validate_url_safe
from backend.infrastructure.acquisition.network.http import decode_bounded_http_body, fetch_public_http

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 AegisProtocol/3.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class WebAdapter(PlatformAdapter):
    """
    Acquires general web content following Policy D.
    """

    @property
    def platform(self) -> str:
        return "web"

    @property
    def backend_id(self) -> str:
        return "bounded_urllib"

    def can_handle(self, candidate: CandidateSource) -> bool:
        p = candidate.platform.lower()
        url = (candidate.canonical_url or candidate.url).lower()
        # Web adapter handles general web pages not explicitly claimed by specialized platforms
        specialists = ("reddit.com", "redd.it", "x.com", "twitter.com", "youtube.com", "youtu.be", "github.com")
        return p in ("web", "news", "article") or not any(s in url for s in specialists)

    def _fetch_scrapling(self, target_url: str, timeout: float = 5.0) -> Tuple[int, str, Dict[str, str], int, Optional[str]]:
        """Compatibility method name for the connection-validated HTTP reader."""
        t0 = time.perf_counter()
        try:
            response = fetch_public_http(target_url, headers=DEFAULT_HEADERS,
                                         timeout=min(timeout, 5.0), max_bytes=1_000_000)
            media_type = (response.content_type or "").split(";", 1)[0].strip().lower()
            if media_type and not (
                media_type.startswith("text/")
                or media_type in ("application/xhtml+xml", "application/xml", "application/json")
            ):
                raise ValueError("HTTP response is not a text document")
            content = decode_bounded_http_body(response).decode("utf-8")
            if any(ord(character) < 32 and character not in "\t\r\n" for character in content):
                raise ValueError("HTTP response contains binary control characters")
            return response.status_code or 200, content, dict(response.headers), response.latency_ms, None
        except Exception as e:
            lat = int((time.perf_counter() - t0) * 1000)
            logger.debug(f"[WebAdapter] Scrapling fetch error for {target_url}: {e}")
            return 500, "", {}, lat, str(e)

    def _fetch_playwright_rescue(self, target_url: str, timeout: float = 12.0) -> Tuple[int, str, Dict[str, str], int, Optional[str]]:
        """
        Playwright rescue executed ONLY when lightweight HTTP fails with JS-rendering signs.
        """
        t0 = time.perf_counter()
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(int(timeout * 1000))
                resp = page.goto(target_url, wait_until="domcontentloaded")
                status = resp.status if resp else 200
                content = page.content()
                browser.close()
                lat = int((time.perf_counter() - t0) * 1000)
                return status, content, {"content-type": "text/html"}, lat, None
        except Exception as e:
            lat = int((time.perf_counter() - t0) * 1000)
            logger.debug(f"[WebAdapter] Playwright rescue failed for {target_url}: {e}")
            return 500, "", {}, lat, str(e)

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        target_url = candidate.canonical_url or candidate.url
        # 1. SSRF Gate
        is_safe, reason = validate_url_safe(target_url)
        if not is_safe:
            return FetchedDocument(
                url=target_url,
                status="BLOCKED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                failure_reason=f"SSRF validation failed: {reason}",
            )

        # 2. Primary: bounded, connection-validated public HTTP
        status, text, headers, lat, err = self._fetch_scrapling(target_url)
        active_backend = self.backend_id

        # Browser rescue is not automatic: browser subrequests cannot use the
        # connection-pinned public transport and must not bypass SSRF failures.

        doc_status = "SUCCESS" if (status == 200 and len(text) > 0) else "FAILED"
        return FetchedDocument(
            url=target_url,
            status=doc_status,
            backend_id=active_backend,
            retrieval_mode=RetrievalMode.WEB_READER.value,
            raw_content=text,
            raw_metadata={"headers": headers, "status_code": status},
            latency_ms=lat,
            failure_reason=err,
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        # Simple HTML to text extraction
        text = document.raw_content
        # Strip script, style, comments
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        # Extract title if present
        title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else candidate.title or ""
        
        # Clean tags
        clean_text = re.sub(r"<[^>]+>", " ", text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        body = clean_text[:4000]

        # A 4,000-character cap cannot establish that the entire article was read.
        depth = "PARTIAL_CONTENT" if len(body) > 250 else "SNIPPET"

        frag = EvidenceFragment(
            platform=self.platform,
            title=title,
            content=body,
            url=document.url,
            author="",
            published=document.raw_metadata.get("published_at") or "",
            snippet=body[:280],
            score=candidate.semantic_score or 0.0,
            retrieval_method="agent_reach",
            channel_name="web",
            content_depth=depth,
            query_id=request.request_id,
            query_class=request.task_type,
            query_text=request.query,
            retrieval_mode=RetrievalMode.WEB_READER.value,
            native_backend_id=document.backend_id,
            is_authenticated=False,
            raw_metadata={"source_rank": candidate.search_rank,
                          "discovery_published_at": candidate.metadata.get("published_at")},
        )
        return [frag]
