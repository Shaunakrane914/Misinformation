"""
Aegis Protocol — Jina Web Reader & Content Extraction Adapter
==============================================================
Provides safe web document extraction into clean markdown via:
1. Native bounded, DNS-pinned HTTP executor (Primary)
2. Native Jina Reader HTTP API (https://r.jina.ai/{url}) (Fallback)
Enforces strict SSRF defense before network transmission.
"""

import hashlib
import logging
import urllib.parse
from typing import Any, Dict, Optional

from backend.infrastructure.acquisition.network.http import (
    DEFAULT_MAX_RESPONSE_BYTES,
    ProviderHTTPError,
    decode_bounded_http_body,
    fetch_public_http,
)
from backend.services.url_validator import is_safe_url
from backend.services.agent_reach.native.errors import SecurityPolicyViolation

logger = logging.getLogger(__name__)

JINA_READER_BASE = "https://r.jina.ai"


def read_article_via_jina(url: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """
    Fetch markdown document from Jina Reader endpoint with SSRF check.
    """
    safe, reason = is_safe_url(url)
    if not safe:
        return {"status": "blocked_ssrf", "error": f"SSRF blocked: {reason}", "url": url}

    jina_target = f"{JINA_READER_BASE}/{url.strip()}"
    headers = {
        "User-Agent": "AegisAgentReach/3.0 (Zero-Auth Public Evidence Mirror)",
        "Accept": "text/markdown, application/json, text/plain",
    }
    try:
        response = fetch_public_http(
            jina_target,
            headers=headers,
            timeout=timeout,
            max_bytes=DEFAULT_MAX_RESPONSE_BYTES,
        )
        raw_body = response.body
        content = decode_bounded_http_body(response).decode("utf-8")
        if any(ord(character) < 32 and character not in "\t\r\n" for character in content):
            raise ValueError("Reader response contains binary control characters")
        if content and len(content.strip()) > 30:
            netloc = urllib.parse.urlparse(url).netloc
            return {
                "status": "success",
                "title": f"Page from {netloc}",
                "content": content,
                "markdown": content,
                "url": url,
                "char_count": len(content),
                "backend": "jina-reader",
                "fallback_used": True,
                "fallback_backend": "jina-reader",
                "transport": {
                    "endpoint": response.endpoint,
                    "requested_endpoint": response.redirect_chain[0] if response.redirect_chain else jina_target,
                    "redirect_chain": list(response.redirect_chain),
                    "network_observed_this_attempt": True,
                    "http_status": response.status_code,
                    "content_type": response.content_type,
                    "raw_body_bytes": len(raw_body),
                    "raw_body_sha256": hashlib.sha256(raw_body).hexdigest(),
                    "network_latency_ms": response.latency_ms,
                    "cache_status": "UNKNOWN",
                    "attempts": response.attempts,
                },
            }
    except ProviderHTTPError as error:
        logger.debug("[JinaWebReader] Bounded fetch failed for %s: %s", url, error)
    except Exception as error:
        logger.debug("[JinaWebReader] Jina response parsing failed for %s: %s", url, error)

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
    Primary: Native bounded HTTP executor. Fallback: bounded Jina reader.
    The legacy_scraper argument remains for import/call compatibility, but its
    unpinned network implementation must not bypass this security boundary.
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
                page_metadata = res.get("page_metadata") or {}
                return {
                    "status": "success",
                    "title": page_metadata.get("title") or f"Page from {netloc}",
                    "author": page_metadata.get("author") or "",
                    "published": page_metadata.get("published") or "",
                    "page_metadata": page_metadata,
                    "content": content[:max_chars],
                    "markdown": content[:max_chars],
                    "url": url,
                    "char_count": len(content),
                    "backend": res.get("backend", "scrapling_http"),
                    "fallback_used": res.get("backend") == "jina_reader_fallback",
                    "transport": res.get("transport"),
                }
        except SecurityPolicyViolation as error:
            return {"status": "blocked_ssrf", "error": str(error), "url": url}
        except ProviderHTTPError as error:
            return {
                "status": "failed", "error": str(error), "url": url,
                "transport": {"endpoint": error.endpoint, "http_status": error.status_code,
                              "retry_after_seconds": error.retry_after_seconds,
                              "network_observed_this_attempt": error.network_observed},
            }
        except Exception as e_web:
            logger.debug(f"[JinaWebReader] Native web read notice: {e_web}. Trying fallback.")

    # Only a bounded transport can serve as an automatic fallback.
    jina_res = read_article_via_jina(url, timeout=5.0)
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
