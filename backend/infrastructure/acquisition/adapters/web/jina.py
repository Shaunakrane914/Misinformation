"""
Aegis Protocol — Jina Web Reader & Content Extraction Adapter
==============================================================
Provides safe web document extraction into clean markdown via:
1. Native Scrapling HTTP / Playwright rescue executor (Primary)
2. Legacy reach scraper fallback (Secondary)
3. Native Jina Reader HTTP API (https://r.jina.ai/{url}) (Tertiary)
Enforces strict SSRF defense before network transmission.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
import time
from typing import Any, Dict, Optional

from backend.services.url_validator import is_safe_url

logger = logging.getLogger(__name__)

JINA_READER_BASE = "https://r.jina.ai"


def read_article_via_jina(url: str, timeout: float = 8.0) -> Optional[Dict[str, Any]]:
    """
    Fetch markdown document from Jina Reader endpoint with SSRF check.
    """
    safe, reason = is_safe_url(url)
    if not safe:
        return {"status": "blocked_ssrf", "error": f"SSRF blocked: {reason}", "url": url}

    jina_target = f"{JINA_READER_BASE}/{url.strip()}"
    req = urllib.request.Request(
        jina_target,
        headers={
            "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
            "Accept": "text/markdown, application/json, text/plain",
        },
    )
    try:
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_body = resp.read()
            content = raw_body.decode("utf-8", errors="replace")
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if content and len(content.strip()) > 30:
                netloc = urllib.parse.urlparse(url).netloc
                return {
                    "status": "success",
                    "title": f"Article from {netloc}",
                    "content": content,
                    "markdown": content,
                    "url": url,
                    "char_count": len(content),
                    "backend": "jina-reader",
                    "fallback_used": True,
                    "fallback_backend": "jina-reader",
                    "transport": {
                        "endpoint": getattr(resp, "url", jina_target),
                        "network_observed_this_attempt": True,
                        "http_status": getattr(resp, "status", None),
                        "content_type": resp.headers.get("Content-Type"),
                        "raw_body_bytes": len(raw_body),
                        "network_latency_ms": latency_ms,
                        "cache_status": "UNKNOWN",
                    },
                }
    except Exception as e:
        logger.debug(f"[JinaWebReader] Jina reader HTTP fetch failed for {url}: {e}")

    return None


def execute_web_read(
    url: str,
    max_chars: int = 4000,
    executor: Any = None,
    legacy_scraper: Any = None,
) -> Dict[str, Any]:
    """
    Safely fetch and extract document content into clean markdown.
    Enforces SSRF defense before network transmission.
    Primary: Native executor (Scrapling HTTP / Playwright rescue).
    Fallback: Legacy reader scraper.
    Tertiary: Jina reader direct endpoint.
    """
    if not url:
        return {"status": "error", "error": "Empty URL provided", "url": ""}

    safe, reason = is_safe_url(url)
    if not safe:
        logger.warning(f"[JinaWebReader] SSRF defense blocked URL: {url} ({reason})")
        return {
            "status": "blocked_ssrf",
            "error": f"URL blocked by SSRF defense: {reason}",
            "url": url,
        }

    # 1. Primary: Native executor web read
    if executor is not None and hasattr(executor, "execute_web_read"):
        try:
            res = executor.execute_web_read(url)
            content = res.get("content", "")
            if content and len(content.strip()) > 50:
                netloc = urllib.parse.urlparse(url).netloc
                return {
                    "status": "success",
                    "title": f"Article from {netloc}",
                    "content": content[:max_chars],
                    "markdown": content[:max_chars],
                    "url": url,
                    "char_count": len(content),
                    "backend": res.get("backend", "scrapling_http"),
                    "fallback_used": False,
                    "transport": res.get("transport"),
                }
        except Exception as e_web:
            logger.debug(f"[JinaWebReader] Native web read notice: {e_web}. Trying fallback.")

    # 2. Fallback: Legacy reach scraper
    if legacy_scraper is not None and hasattr(legacy_scraper, "read_article_markdown"):
        try:
            res = legacy_scraper.read_article_markdown(url, max_chars=max_chars)
            content = res.get("content", "") or res.get("markdown", "")
            if content:
                netloc = urllib.parse.urlparse(url).netloc
                return {
                    "status": "success",
                    "title": res.get("title") or f"Article from {netloc}",
                    "content": content[:max_chars],
                    "markdown": content[:max_chars],
                    "url": url,
                    "char_count": len(content),
                    "backend": "Legacy Reach Scraper",
                    "fallback_used": True,
                    "fallback_backend": "Legacy Reach Scraper",
                }
        except Exception as e_sc:
            logger.warning(f"[JinaWebReader] Fallback read failed for {url}: {e_sc}")

    # 3. Tertiary: Jina reader direct fetch
    jina_res = read_article_via_jina(url, timeout=7.0)
    if jina_res and jina_res.get("status") == "success":
        c = jina_res.get("content", "")
        return {
            "status": "success",
            "title": jina_res.get("title", ""),
            "content": c[:max_chars],
            "markdown": c[:max_chars],
            "url": url,
            "char_count": len(c),
            "backend": "jina-reader",
            "fallback_used": True,
            "fallback_backend": "jina-reader",
            "transport": jina_res.get("transport"),
        }

    return {"status": "error", "error": "Failed to read content", "url": url}


class JinaWebReaderAdapter:
    """
    Adapter encapsulating Jina Reader & Web reading operations.
    """

    @property
    def platform(self) -> str:
        return "jina_reader"

    @property
    def backend_id(self) -> str:
        return "jina-reader"

    def read(self, url: str, max_chars: int = 4000) -> Dict[str, Any]:
        return execute_web_read(url, max_chars=max_chars)
