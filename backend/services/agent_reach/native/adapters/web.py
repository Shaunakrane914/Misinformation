"""
Aegis Protocol — Scrapling & Playwright Web Adapter
===================================================
Authoritative web acquisition adapter implementing Policy D:
  - Primary: Scrapling HTTP (curl_cffi / lightweight HTTP)
  - Secondary: Playwright rescue strictly when client-side JS rendering
    or an anti-bot challenge prevents lightweight acquisition.
  - SSRF-safe URL validation enforced before any outbound connection.
  - Public Jina Reader deprecated as primary path.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from backend.services.agent_reach.channels import (
    CandidateSource,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.agent_reach.native.adapters.base import PlatformAdapter
from backend.services.agent_reach.native.route_policy import RoutePolicyEngine
from backend.services.url_validator import validate_url_safe

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
        return "scrapling_http"

    def can_handle(self, candidate: CandidateSource) -> bool:
        p = candidate.platform.lower()
        url = (candidate.canonical_url or candidate.url).lower()
        # Web adapter handles general web pages not explicitly claimed by specialized platforms
        specialists = ("reddit.com", "redd.it", "x.com", "twitter.com", "youtube.com", "youtu.be", "github.com")
        return p in ("web", "news", "article") or not any(s in url for s in specialists)

    def _fetch_scrapling(self, target_url: str, timeout: float = 8.0) -> Tuple[int, str, Dict[str, str], int, Optional[str]]:
        t0 = time.perf_counter()
        try:
            from scrapling import Fetcher
            response = Fetcher.get(target_url, headers=DEFAULT_HEADERS, timeout=timeout)
            lat = int((time.perf_counter() - t0) * 1000)
            text = response.text if hasattr(response, "text") else str(response)
            status = getattr(response, "status", 200)
            headers = dict(getattr(response, "headers", {}))
            return status, text, headers, lat, None
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

        # 2. Primary: Scrapling HTTP
        status, text, headers, lat, err = self._fetch_scrapling(target_url)
        active_backend = self.backend_id

        # 3. Secondary: Playwright Rescue (only if justified)
        if RoutePolicyEngine.should_attempt_playwright_rescue(status, len(text), err):
            logger.debug(f"[WebAdapter] Engaging Playwright rescue for {target_url} (HTTP {status}, len={len(text)})")
            p_status, p_text, p_headers, p_lat, p_err = self._fetch_playwright_rescue(target_url)
            if p_status == 200 and len(p_text) > len(text):
                status, text, headers, lat, err = p_status, p_text, p_headers, p_lat, p_err
                active_backend = "playwright_rescue"

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
        title = title_match.group(1).strip() if title_match else candidate.title or "Discovered Article"
        
        # Clean tags
        clean_text = re.sub(r"<[^>]+>", " ", text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        body = clean_text[:4000]

        depth = "FULL_ARTICLE" if len(body) > 1000 else ("PARTIAL_CONTENT" if len(body) > 250 else "SNIPPET")

        frag = EvidenceFragment(
            platform=self.platform,
            title=title,
            content=body,
            url=document.url,
            author="Web Publisher",
            published=datetime.now(timezone.utc).isoformat(),
            snippet=body[:280],
            score=candidate.semantic_score or 1.0,
            retrieval_method="agent_reach",
            channel_name="web",
            content_depth=depth,
            query_id=request.request_id,
            query_class=request.task_type,
            query_text=request.query,
            retrieval_mode=RetrievalMode.WEB_READER.value,
            native_backend_id=document.backend_id,
            is_authenticated=False,
            raw_metadata={"source_rank": candidate.search_rank},
        )
        return [frag]
