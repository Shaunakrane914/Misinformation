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
import re
import time
from typing import Any, Dict, Optional

from backend.infrastructure.acquisition.network.http import (
    DEFAULT_MAX_RESPONSE_BYTES,
    ProviderHTTPError,
    decode_bounded_http_body,
    fetch_public_http,
    transport_failure_kind,
)
from backend.services.url_validator import is_safe_url
from backend.infrastructure.acquisition.security.url_validator import validation_failure_kind
from backend.services.agent_reach.native.errors import SecurityPolicyViolation
from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_reader_markdown
from backend.infrastructure.acquisition.network.budget import acquisition_deadline, remaining_timeout

logger = logging.getLogger(__name__)

JINA_READER_BASE = "https://r.jina.ai"


_FAILURE_KINDS = frozenset({
    'TIMEOUT', 'DNS_ERROR', 'DNS_TIMEOUT', 'DNS_CAPACITY', 'CONNECTION_FAILURE',
    'HTTP_FAILURE', 'PROVIDER_FAILURE', 'EMPTY_EXTRACTION', 'CHALLENGE_PAGE',
    'SSRF_BLOCKED', 'BUDGET_EXHAUSTED', 'RATE_LIMITED', 'AUTH_REQUIRED',
    'ACCESS_DENIED', 'CONFIG_REQUIRED', 'PERMISSION_REQUIRED', 'UNVERIFIED',
    'BLOCKED', 'ROBOTS_DENIED', 'ROBOTS_UNVERIFIED', 'ROBOTS_CRAWL_DELAY_BUDGET_EXHAUSTED',
    'ROBOTS_CRAWL_DELAY_REVIEW_REQUIRED', 'PAYWALL', 'LOGIN_REQUIRED',
})


def _failure_observation(stage, result):
    """Copy only bounded typed observations, never raw exception text/headers."""
    transport = result.get('transport') if isinstance(result.get('transport'), dict) else {}
    kind = result.get('failure_kind')
    kind = kind if isinstance(kind, str) and kind in _FAILURE_KINDS else 'PROVIDER_FAILURE'
    status = transport.get('http_status', result.get('status_code'))
    status = status if type(status) is int and 100 <= status <= 599 else None
    observed = transport.get('network_observed_this_attempt', result.get('network_observed'))
    from backend.infrastructure.acquisition.adapters.web.response_diagnostics import safe_diagnostics
    diagnostic = safe_diagnostics(result.get('native_response_diagnostics'))
    return {'stage': stage, 'failure_kind': kind, 'http_status': status,
            'network_observed': observed if type(observed) is bool else None,
            **({'native_response_diagnostics': diagnostic} if diagnostic else {})}


def _with_failures(result, failures):
    diagnostic = next((row['native_response_diagnostics'] for row in failures
                       if row.get('native_response_diagnostics')), None)
    return {**result, **({'native_response_diagnostics': diagnostic} if diagnostic else {}),
            **({'provider_failures': failures[:3]} if failures else {})}


def _failed_read(url, failures):
    if not failures:
        return {"status": "error", "error": "Failed to read content", "url": url}
    first = failures[0]
    return _with_failures({'status': 'error', 'url': url,
        'error': 'No reader acquired content; see typed provider observations',
        'failure_kind': first['failure_kind'], 'network_observed': first['network_observed'],
        'transport': {'http_status': first['http_status'],
                      'network_observed_this_attempt': first['network_observed']}}, failures)


def _terminal_failure(result):
    if not isinstance(result, dict):
        return False
    transport = result.get("transport") if isinstance(result.get("transport"), dict) else {}
    page = result.get("page_metadata") if isinstance(result.get("page_metadata"), dict) else {}
    status = str(transport.get("http_status") or result.get("http_status") or page.get("status_code") or "")
    return (status in {"401", "403", "429"}
            or str(result.get("failure_kind", "")).upper() in {"ACCESS_DENIED", "AUTH_REQUIRED", "FORBIDDEN", "CHALLENGE_PAGE",
                                             "SSRF_BLOCKED", "RATE_LIMITED", "BUDGET_EXHAUSTED", "ROBOTS_DENIED",
                                             "PAYWALL", "LOGIN_REQUIRED", "PERMISSION_REQUIRED", "UNVERIFIED", "BLOCKED",
                                             "ROBOTS_UNVERIFIED", "ROBOTS_CRAWL_DELAY_REVIEW_REQUIRED",
                                             "ROBOTS_CRAWL_DELAY_BUDGET_EXHAUSTED"}
            or str(result.get("status", "")).lower() in {"blocked_ssrf", "forbidden", "access_denied", "rate_limited"})


def read_article_via_jina(url: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """
    Fetch markdown document from Jina Reader endpoint with SSRF check.
    """
    safe, reason = is_safe_url(url)
    if not safe:
        kind = validation_failure_kind(reason)
        return {"status": "blocked_ssrf" if kind == "SSRF_BLOCKED" else "failed",
                "failure_kind": kind, "error": reason, "url": url}

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
        # Reader mirrors sometimes return HTTP 200 containing an explicit
        # upstream denial. It is not acquired article content.
        opening = re.sub(r"\s+", " ", content[:300]).strip().lower()
        warning = re.search(r"(?im)^\s*(?:warning:\s*)?target url returned error (401|403|429)\b", content[:1500])
        challenge = re.match(r"^(?:#{1,3}\s*)?(?:just a moment|verify (?:that )?you are human|attention required|access denied|403 forbidden|checking your browser)\b", opening)
        if warning or challenge:
            status = int(warning.group(1)) if warning else 403
            return {"status": "failed", "url": url, "failure_kind": "RATE_LIMITED" if status == 429 else "ACCESS_DENIED",
                    "error": "Reader reported an upstream access restriction", "transport": {
                        "http_status": status, "network_observed_this_attempt": True}}
        if any(ord(character) < 32 and character not in "\t\r\n" for character in content):
            raise ValueError("Reader response contains binary control characters")
        if content and len(content.strip()) > 30:
            extracted = extract_reader_markdown(content)
            readable = extracted["text"]
            page = extracted["page_metadata"]
            return {
                "status": "success",
                "title": page.get("title", ""),
                "published": page.get("published", ""),
                "page_metadata": page,
                "raw_capture": extracted["raw_capture"],
                "content": readable,
                "markdown": readable,
                "url": url,
                "char_count": len(readable),
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
        logger.debug("[JinaWebReader] Bounded fetch failed (%s)", error.failure_kind)
        return {"status": "failed", "url": url, "failure_kind": error.failure_kind,
                "error": "Reader provider request failed", "transport": {
                    "http_status": error.status_code, "retry_after_seconds": error.retry_after_seconds,
                    "network_observed_this_attempt": error.network_observed}}
    except Exception as error:
        from backend.services.research.source_registry import SourcePermissionError
        if isinstance(error, SourcePermissionError):
            raise
        logger.debug("[JinaWebReader] Reader response could not be processed")
        return {"status": "failed", "url": url, "failure_kind": transport_failure_kind(error),
                "error": "Reader response could not be processed"}

    return None


def execute_web_read(
    url: str,
    max_chars: int = 4000,
    executor: Any = None,
    legacy_scraper: Any = None,
    firecrawl_adapter: Any = None,
) -> Dict[str, Any]:
    # One deadline across native and alternate readers; never reset a parent's
    # clock. Each individual transmission keeps its existing five-second cap.
    try:
        with acquisition_deadline(time.monotonic() + remaining_timeout(15.0)):
            return _execute_web_read(url, max_chars, executor, legacy_scraper, firecrawl_adapter)
    except TimeoutError:
        return {"status": "failed", "url": url, "failure_kind": "BUDGET_EXHAUSTED",
                "error": "Acquisition deadline exhausted"}


def _execute_web_read(url, max_chars, executor, legacy_scraper, firecrawl_adapter):
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
        kind = validation_failure_kind(reason)
        logger.warning("[JinaWebReader] URL validation failed (%s): %s", kind, reason)
        return {
            "status": "blocked_ssrf" if kind == "SSRF_BLOCKED" else "failed",
            "error": reason, "failure_kind": kind,
            "url": url,
        }

    failures = []
    jina_attempted = False

    # 1. Primary: Native executor web read
    if executor is not None and hasattr(executor, "execute_web_read"):
        try:
            res = executor.execute_web_read(url)
            jina_attempted = res.get("reader_fallback_attempted") is True
            if _terminal_failure(res):
                failures.append(_failure_observation('NATIVE_READER', res))
                return _with_failures(res, failures)
            content = res.get("content", "")
            if content and len(content.strip()) > 50:
                page_metadata = res.get("page_metadata") or {}
                from backend.infrastructure.acquisition.adapters.web.response_diagnostics import safe_diagnostics
                diagnostic = safe_diagnostics(res.get('native_response_diagnostics'))
                if diagnostic:
                    page_metadata = {**page_metadata, 'native_response_diagnostics': diagnostic}
                return {
                    "status": "success",
                    "title": page_metadata.get("title") or "",
                    "author": page_metadata.get("author") or "",
                    "published": page_metadata.get("published") or "",
                    "page_metadata": page_metadata,
                    "raw_capture": res.get("raw_capture") or {},
                    "truncated": bool(res.get("truncated")) or len(content) > max_chars,
                    "content_depth": res.get("content_depth"),
                    "content": content[:max_chars],
                    "markdown": content[:max_chars],
                    "url": url,
                    "char_count": len(content),
                    "backend": res.get("backend", "scrapling_http"),
                    "fallback_used": res.get("backend") == "jina_reader_fallback",
                    "transport": res.get("transport"),
                }
            failures.append(_failure_observation('NATIVE_READER', {
                **res, 'failure_kind': res.get('failure_kind') or 'EMPTY_EXTRACTION'}))

        except SecurityPolicyViolation:
            return {"status": "blocked_ssrf", "failure_kind": "SSRF_BLOCKED", "error": "URL failed security validation", "url": url}
        except ProviderHTTPError as error:
            jina_attempted = error.reader_fallback_attempted
            kind = "CHALLENGE_PAGE" if "challenge page" in str(error).lower() else error.failure_kind
            # Access denials and publisher challenges never trigger alternate scrapers
            failure = {
                "status": "failed", "error": ("Native reader provider request failed" +
                    (f" (HTTP {error.status_code})" if type(error.status_code) is int and 100 <= error.status_code <= 599 else "")),
                "url": url,
                "failure_kind": kind or ("ACCESS_DENIED" if error.status_code in (401, 403) else "FAILED"),
                "native_response_diagnostics": error.response_diagnostics,
                "transport": {"http_status": error.status_code,
                              "retry_after_seconds": error.retry_after_seconds,
                              "network_observed_this_attempt": error.network_observed},
            }
            failures.append(_failure_observation('JINA_READER' if jina_attempted else 'NATIVE_READER', failure))
            if _terminal_failure(failure):
                return _with_failures(failure, failures)
        except Exception as error:
            from backend.services.research.source_registry import SourcePermissionError
            if isinstance(error, SourcePermissionError):
                raise
            failures.append(_failure_observation('NATIVE_READER', {'failure_kind': transport_failure_kind(error)}))
            logger.debug("[JinaWebReader] Native web read failed; trying bounded fallback")

    # 2. Secondary Fallback: Firecrawl (if configured and permitted)
    fc_adapter = firecrawl_adapter
    if fc_adapter is None:
        try:
            from backend.infrastructure.acquisition.adapters.web.firecrawl import FirecrawlAdapter
            fc_adapter = FirecrawlAdapter()
        except Exception:
            fc_adapter = None

    if fc_adapter and hasattr(fc_adapter, "is_configured") and fc_adapter.is_configured():
        try:
            fc_res = fc_adapter.scrape_article(url, timeout=remaining_timeout(5.0))
            if fc_res and _terminal_failure(fc_res):
                failures.append(_failure_observation('FIRECRAWL', fc_res))
                return _with_failures(fc_res, failures)
            if fc_res and fc_res.get("status") == "success":
                c = fc_res.get("content", "")
                if c and len(c.strip()) > 30:
                    return {
                        "status": "success",
                        "title": fc_res.get("title", ""),
                        "published": fc_res.get("published", ""),
                        "page_metadata": fc_res.get("page_metadata") or {},
                        "raw_capture": fc_res.get("raw_capture") or {},
                        "content": c[:max_chars],
                        "markdown": c[:max_chars],
                        "url": url,
                        "canonical_url": fc_res.get("canonical_url") or url,
                        "char_count": len(c),
                        "truncated": len(c) > max_chars,
                        "backend": "firecrawl-v1",
                        "fallback_used": True,
                        "fallback_backend": "firecrawl-v1",
                        "transport": fc_res.get("transport"),
                        **({'provider_failures': failures[:3]} if failures else {}),
                    }
            if fc_res:
                failures.append(_failure_observation('FIRECRAWL', fc_res))
        except TimeoutError as error:
            failures.append(_failure_observation('FIRECRAWL', {'failure_kind': transport_failure_kind(error)}))
            return _failed_read(url, failures)
        except Exception as error:
            from backend.services.research.source_registry import SourcePermissionError
            if isinstance(error, SourcePermissionError):
                error.provider_failures = [*failures, _failure_observation('FIRECRAWL', {
                    'failure_kind': error.failure_kind, 'network_observed': False})][:3]
                raise
            failures.append(_failure_observation('FIRECRAWL', {'failure_kind': transport_failure_kind(error)}))
            logger.debug("[JinaWebReader] Firecrawl fallback failed; proceeding to bounded reader")

    # The native executor may already have used this same bounded endpoint.
    # Trying it again spends admissions/time without adding a source path.
    if jina_attempted:
        return _failed_read(url, failures)

    # 3. Tertiary Fallback: Jina Reader (bounded public endpoint)
    try:
        jina_res = read_article_via_jina(url, timeout=remaining_timeout(5.0))
    except Exception as error:
        from backend.services.research.source_registry import SourcePermissionError
        if isinstance(error, TimeoutError):
            failures.append(_failure_observation('JINA_READER', {'failure_kind': transport_failure_kind(error)}))
            return _failed_read(url, failures)
        if isinstance(error, SourcePermissionError):
            error.provider_failures = [*failures, _failure_observation('JINA_READER', {
                'failure_kind': error.failure_kind, 'network_observed': False})][:3]
        raise
    if jina_res and _terminal_failure(jina_res):
        failures.append(_failure_observation('JINA_READER', jina_res))
        return _with_failures(jina_res, failures)
    if jina_res and jina_res.get("status") == "success":
        c = jina_res.get("content", "")
        return {
            "status": "success",
            "title": jina_res.get("title", ""),
            "published": jina_res.get("published", ""),
            "page_metadata": jina_res.get("page_metadata") or {},
            "raw_capture": jina_res.get("raw_capture") or {},
            "content": c[:max_chars],
            "markdown": c[:max_chars],
            "url": url,
            "char_count": len(c),
            "truncated": len(c) > max_chars,
            "backend": "jina-reader",
            "fallback_used": True,
            "fallback_backend": "jina-reader",
            "transport": jina_res.get("transport"),
            **({'provider_failures': failures[:3]} if failures else {}),
        }

    if jina_res:
        failures.append(_failure_observation('JINA_READER', jina_res))
    return _failed_read(url, failures)


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
