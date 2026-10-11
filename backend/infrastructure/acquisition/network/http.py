"""Bounded, redirect-safe HTTP transport for public acquisition adapters.

This module owns transport safety, not provider semantics.  Callers still
normalize provider payloads and decide whether a successful response contains
useful evidence.
"""

from __future__ import annotations

import email.utils
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Optional

from backend.infrastructure.acquisition.security.url_validator import is_safe_url


RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
NON_RETRYABLE_STATUS_CODES = frozenset({400, 401, 403, 404, 405, 410, 422})
DEFAULT_MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class ProviderHTTPError(RuntimeError):
    """Transport failure with safe, structured provider observations."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str,
        status_code: Optional[int] = None,
        retry_after_seconds: Optional[float] = None,
        network_observed: bool = False,
        attempts: int = 1,
    ) -> None:
        super().__init__(message)
        self.endpoint = endpoint
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        self.network_observed = network_observed
        self.attempts = attempts


class ResponseTooLargeError(ProviderHTTPError):
    """Raised when a response exceeds the configured compressed-byte bound."""


@dataclass(frozen=True)
class BoundedHTTPResponse:
    body: bytes
    endpoint: str
    status_code: Optional[int]
    content_type: Optional[str]
    headers: Mapping[str, str]
    latency_ms: int
    attempts: int


def parse_retry_after(value: Optional[str], *, now: Optional[datetime] = None) -> Optional[float]:
    """Parse Retry-After seconds or HTTP-date into a non-negative delay."""
    if not value:
        return None
    clean = str(value).strip()
    try:
        return max(0.0, float(clean))
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(clean)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        reference = now or datetime.now(timezone.utc)
        return max(0.0, (parsed - reference).total_seconds())
    except (TypeError, ValueError, OverflowError):
        return None


class _ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate every redirect before urllib is allowed to transmit it."""

    def __init__(self, max_redirects: int) -> None:
        super().__init__()
        self.max_redirects = max_redirects
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        target = urllib.parse.urljoin(req.full_url, newurl)
        safe, reason = is_safe_url(target)
        if not safe:
            raise ProviderHTTPError(
                f"Redirect blocked by SSRF policy: {reason}",
                endpoint=target,
                status_code=code,
                network_observed=True,
            )
        self.redirect_count += 1
        if self.redirect_count > self.max_redirects:
            raise ProviderHTTPError(
                f"Redirect limit exceeded ({self.max_redirects})",
                endpoint=target,
                status_code=code,
                network_observed=True,
            )
        redirected = super().redirect_request(req, fp, code, msg, headers, target)
        if redirected is not None:
            source_host = (urllib.parse.urlsplit(req.full_url).hostname or "").lower()
            target_host = (urllib.parse.urlsplit(target).hostname or "").lower()
            if source_host != target_host:
                redirected.remove_header("Authorization")
        return redirected


def fetch_public_http(
    url: str,
    *,
    headers: Optional[Mapping[str, str]] = None,
    timeout: float = 10.0,
    max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    max_redirects: int = 4,
    max_attempts: int = 2,
    retry_base_seconds: float = 0.2,
    max_retry_sleep_seconds: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[float, float], float] = random.uniform,
) -> BoundedHTTPResponse:
    """Fetch a public HTTP(S) URL with bounded retries and response size.

    Only idempotent GET requests are supported.  A provider-supplied
    ``Retry-After`` delay is respected when it fits the local retry budget; a
    longer delay is surfaced to runtime health without blocking the worker.
    """
    safe, reason = is_safe_url(url)
    if not safe:
        raise ProviderHTTPError(f"URL blocked by SSRF policy: {reason}", endpoint=url)
    if max_bytes <= 0 or max_attempts <= 0 or max_redirects < 0:
        raise ValueError("HTTP bounds must be positive")

    request_headers = dict(headers or {})
    request_headers.setdefault("Accept-Encoding", "identity")
    started = time.perf_counter()
    last_error: Optional[ProviderHTTPError] = None

    for attempt in range(1, max_attempts + 1):
        redirect_handler = _ValidatingRedirectHandler(max_redirects=max_redirects)
        opener = urllib.request.build_opener(redirect_handler)
        request = urllib.request.Request(url, headers=request_headers, method="GET")
        try:
            with opener.open(request, timeout=timeout) as response:
                endpoint = str(getattr(response, "url", url) or url)
                final_safe, final_reason = is_safe_url(endpoint)
                if not final_safe:
                    raise ProviderHTTPError(
                        f"Final endpoint blocked by SSRF policy: {final_reason}",
                        endpoint=endpoint,
                        status_code=getattr(response, "status", None),
                        network_observed=True,
                        attempts=attempt,
                    )
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        if int(content_length) > max_bytes:
                            raise ResponseTooLargeError(
                                f"Response exceeds {max_bytes} byte limit",
                                endpoint=endpoint,
                                status_code=getattr(response, "status", None),
                                network_observed=True,
                                attempts=attempt,
                            )
                    except ValueError:
                        pass
                body = response.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise ResponseTooLargeError(
                        f"Response exceeds {max_bytes} byte limit",
                        endpoint=endpoint,
                        status_code=getattr(response, "status", None),
                        network_observed=True,
                        attempts=attempt,
                    )
                latency_ms = int((time.perf_counter() - started) * 1000)
                return BoundedHTTPResponse(
                    body=body,
                    endpoint=endpoint,
                    status_code=getattr(response, "status", None),
                    content_type=response.headers.get("Content-Type"),
                    headers=dict(response.headers.items()),
                    latency_ms=latency_ms,
                    attempts=attempt,
                )
        except urllib.error.HTTPError as error:
            status = int(error.code)
            retry_after = parse_retry_after(error.headers.get("Retry-After"))
            last_error = ProviderHTTPError(
                f"Provider HTTP {status}",
                endpoint=str(getattr(error, "url", url) or url),
                status_code=status,
                retry_after_seconds=retry_after,
                network_observed=True,
                attempts=attempt,
            )
            if status in NON_RETRYABLE_STATUS_CODES:
                raise last_error from error
            if status not in RETRYABLE_STATUS_CODES or attempt >= max_attempts:
                raise last_error from error
            delay = retry_after if retry_after is not None else retry_base_seconds * (2 ** (attempt - 1))
            if delay > max_retry_sleep_seconds:
                raise last_error from error
            sleep(max(0.0, delay + jitter(0.0, min(0.1, delay * 0.1))))
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = ProviderHTTPError(
                f"Provider network failure: {type(error).__name__}",
                endpoint=url,
                network_observed=False,
                attempts=attempt,
            )
            if attempt >= max_attempts:
                raise last_error from error
            delay = retry_base_seconds * (2 ** (attempt - 1))
            sleep(delay + jitter(0.0, min(0.1, delay * 0.1)))

    raise last_error or ProviderHTTPError("Provider request failed", endpoint=url)
