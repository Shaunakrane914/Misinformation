"""Bounded, redirect-safe HTTP transport for public acquisition adapters.

This module owns transport safety, not provider semantics.  Callers still
normalize provider payloads and decide whether a successful response contains
useful evidence.
"""

from __future__ import annotations

import email.utils
import http.client
import io
import math
import random
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Optional

from backend.infrastructure.acquisition.security.url_validator import is_safe_url, resolve_public_addresses
from backend.infrastructure.acquisition.network.budget import remaining_timeout


RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
NON_RETRYABLE_STATUS_CODES = frozenset({400, 401, 403, 404, 405, 410, 422})
DEFAULT_MAX_RESPONSE_BYTES = 1_000_000


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
        rate_limit_remaining: Optional[int] = None,
        rate_limit_reset_at: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.endpoint = endpoint
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        self.network_observed = network_observed
        self.attempts = attempts
        self.rate_limit_remaining = rate_limit_remaining
        self.rate_limit_reset_at = rate_limit_reset_at


class ResponseTooLargeError(ProviderHTTPError):
    """Raised when a response exceeds a wire or decoded byte bound."""


@dataclass(frozen=True)
class BoundedHTTPResponse:
    body: bytes
    endpoint: str
    status_code: Optional[int]
    content_type: Optional[str]
    headers: Mapping[str, str]
    latency_ms: int
    attempts: int
    # The first entry is the requested URL and subsequent entries are redirect
    # targets observed by the validating redirect handler.  This remains empty
    # for constructed fixture responses and older callers.
    redirect_chain: tuple[str, ...] = ()


def decode_bounded_http_body(
    response: BoundedHTTPResponse, *, max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> bytes:
    """Decode an HTTP entity only when both wire and expanded bytes are bounded.

    ``response.body`` remains the original wire entity for provenance hashes.
    A server can send compressed data despite ``Accept-Encoding: identity``;
    callers must never interpret those bytes as page text or provider JSON.
    """
    if max_bytes <= 0:
        raise ValueError("HTTP bounds must be positive")
    wire = response.body
    if len(wire) > max_bytes:
        raise ResponseTooLargeError(
            f"Response exceeds {max_bytes} byte limit", endpoint=response.endpoint,
            status_code=response.status_code, network_observed=True,
            attempts=response.attempts,
        )
    encoding = next(
        (value for name, value in response.headers.items()
         if name.lower() == "content-encoding"),
        "identity",
    ).strip().lower()
    if encoding in ("", "identity"):
        if wire.startswith(b"\x1f\x8b"):
            raise ProviderHTTPError(
                "Undeclared compressed HTTP response", endpoint=response.endpoint,
                status_code=response.status_code, network_observed=True,
                attempts=response.attempts,
            )
        return wire
    if encoding not in ("gzip", "x-gzip", "deflate"):
        raise ProviderHTTPError(
            "Unsupported HTTP content encoding", endpoint=response.endpoint,
            status_code=response.status_code, network_observed=True,
            attempts=response.attempts,
        )
    try:
        decoder = zlib.decompressobj(
            16 + zlib.MAX_WBITS if encoding in ("gzip", "x-gzip") else zlib.MAX_WBITS
        )
        expanded = decoder.decompress(wire, max_bytes + 1)
        if len(expanded) > max_bytes:
            raise ResponseTooLargeError(
                f"Decoded response exceeds {max_bytes} byte limit",
                endpoint=response.endpoint, status_code=response.status_code,
                network_observed=True, attempts=response.attempts,
            )
        expanded += decoder.flush(max_bytes + 1 - len(expanded))
        if len(expanded) > max_bytes:
            raise ResponseTooLargeError(
                f"Decoded response exceeds {max_bytes} byte limit",
                endpoint=response.endpoint, status_code=response.status_code,
                network_observed=True, attempts=response.attempts,
            )
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("Incomplete or concatenated compressed response")
        return expanded
    except (zlib.error, ValueError) as error:
        raise ProviderHTTPError(
            "Invalid compressed HTTP response", endpoint=response.endpoint,
            status_code=response.status_code, network_observed=True,
            attempts=response.attempts,
        ) from error


def parse_retry_after(value: Optional[str], *, now: Optional[datetime] = None) -> Optional[float]:
    """Parse Retry-After seconds or HTTP-date into a non-negative delay."""
    if not value:
        return None
    clean = str(value).strip()
    try:
        delay = float(clean)
        return max(0.0, delay) if math.isfinite(delay) else None
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


def _connect_public_socket(address, timeout=5.0, source_address=None):
    """Connect only to fresh validated numeric IPs; retain HTTP Host/TLS SNI."""
    host, port = address
    timeout = 5.0 if timeout is socket._GLOBAL_DEFAULT_TIMEOUT or timeout is None else float(timeout)
    timeout = remaining_timeout(timeout)
    deadline = time.monotonic() + timeout
    try:
        addresses = resolve_public_addresses(host, port, timeout=min(2.5, timeout))
    except ValueError as error:
        raise ProviderHTTPError("Connection blocked by SSRF policy", endpoint=f"{host}:{port}") from error
    last_error = None
    for family, socktype, protocol, _, sockaddr in addresses:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Public HTTP connection deadline expired")
        connection = socket.socket(family, socktype, protocol)
        try:
            connection.settimeout(remaining)
            if source_address:
                connection.bind(source_address)
            # Numeric sockaddr came from the validated DNS answer. No re-lookup.
            connection.connect(sockaddr)
            return connection
        except OSError as error:
            last_error = error
            connection.close()
    raise last_error or OSError("No public address could be connected")


class _DeadlineStream(io.RawIOBase):
    """Keep header/body trickles within the connection's wall-clock budget."""

    def __init__(self, raw, connection, deadline):
        super().__init__()
        self.raw = raw
        self.connection = connection
        self.deadline = deadline

    def readable(self):
        return True

    def readinto(self, buffer):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Public HTTP response deadline expired")
        self.connection.settimeout(remaining)
        return self.raw.readinto(buffer)

    def close(self):
        try:
            self.raw.close()
        finally:
            super().close()


class _ResponseSocket:
    def __init__(self, connection, deadline):
        self.connection = connection
        self.deadline = deadline

    def makefile(self, mode):
        raw = self.connection.makefile(mode, buffering=0)
        return io.BufferedReader(_DeadlineStream(raw, self.connection, self.deadline))


def _install_response_deadline(connection):
    timeout = connection.timeout
    if timeout is None or timeout is socket._GLOBAL_DEFAULT_TIMEOUT:
        timeout = 5.0
    deadline = time.monotonic() + remaining_timeout(float(timeout))

    def response(sock, *args, **kwargs):
        return http.client.HTTPResponse(_ResponseSocket(sock, deadline), *args, **kwargs)

    connection.response_class = response


class _PublicHTTPConnection(http.client.HTTPConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _connect_public_socket
        _install_response_deadline(self)


class _PublicHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _connect_public_socket
        _install_response_deadline(self)


class _PublicHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, request):
        return self.do_open(_PublicHTTPConnection, request)


class _PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, request):
        return self.do_open(_PublicHTTPSConnection, request, context=self._context)


def _origin(url):
    parsed = urllib.parse.urlsplit(url)
    return (parsed.scheme.lower(), (parsed.hostname or "").lower(),
            parsed.port or (443 if parsed.scheme.lower() == "https" else 80))


class _ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate every redirect before urllib is allowed to transmit it."""

    def __init__(self, max_redirects: int) -> None:
        super().__init__()
        self.max_redirects = max_redirects
        self.redirect_count = 0
        self.redirect_targets: list[str] = []

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
        self.redirect_targets.append(target)
        if self.redirect_count > self.max_redirects:
            raise ProviderHTTPError(
                f"Redirect limit exceeded ({self.max_redirects})",
                endpoint=target,
                status_code=code,
                network_observed=True,
            )
        redirected = super().redirect_request(req, fp, code, msg, headers, target)
        if redirected is not None:
            if _origin(req.full_url) != _origin(target):
                sensitive = {"authorization", "cookie", "proxy-authorization", "x-goog-api-key", "x-api-key", "apikey"}
                for name, _value in list(redirected.header_items()):
                    if name.lower() in sensitive:
                        redirected.remove_header(name)
        return redirected


def fetch_public_http(
    url: str,
    *,
    headers: Optional[Mapping[str, str]] = None,
    timeout: float = 5.0,
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
    if max_bytes <= 0 or max_attempts <= 0 or max_redirects < 0 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("HTTP bounds must be positive")
    remaining_timeout(timeout)
    safe, reason = is_safe_url(url)
    if not safe:
        raise ProviderHTTPError(f"URL blocked by SSRF policy: {reason}", endpoint=url)

    request_headers = dict(headers or {})
    request_headers.setdefault("Accept-Encoding", "identity")
    started = time.perf_counter()
    last_error: Optional[ProviderHTTPError] = None

    for attempt in range(1, max_attempts + 1):
        attempt_timeout = remaining_timeout(timeout)
        redirect_handler = _ValidatingRedirectHandler(max_redirects=max_redirects)
        # Environment proxies must not bypass the destination-address boundary.
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), redirect_handler,
            _PublicHTTPHandler(), _PublicHTTPSHandler(),
        )
        request = urllib.request.Request(url, headers=request_headers, method="GET")
        try:
            with opener.open(request, timeout=attempt_timeout) as response:
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
                    redirect_chain=tuple([url, *redirect_handler.redirect_targets]),
                )
        except urllib.error.HTTPError as error:
            status = int(error.code)
            retry_after = parse_retry_after(error.headers.get("Retry-After"))
            remaining_header = error.headers.get("X-RateLimit-Remaining")
            try:
                rate_limit_remaining = int(remaining_header) if remaining_header is not None else None
            except ValueError:
                rate_limit_remaining = None
            reset_header = error.headers.get("X-RateLimit-Reset")
            rate_limit_reset_at = None
            if reset_header:
                try:
                    rate_limit_reset_at = datetime.fromtimestamp(
                        float(reset_header), tz=timezone.utc,
                    ).isoformat()
                except (ValueError, TypeError, OverflowError):
                    rate_limit_reset_at = str(reset_header)[:100]
            error.close()
            last_error = ProviderHTTPError(
                f"Provider HTTP {status}",
                endpoint=str(getattr(error, "url", url) or url),
                status_code=status,
                retry_after_seconds=retry_after,
                network_observed=True,
                attempts=attempt,
                rate_limit_remaining=rate_limit_remaining,
                rate_limit_reset_at=rate_limit_reset_at,
            )
            if status in NON_RETRYABLE_STATUS_CODES:
                raise last_error from error
            if status not in RETRYABLE_STATUS_CODES or attempt >= max_attempts:
                raise last_error from error
            delay = retry_after if retry_after is not None else retry_base_seconds * (2 ** (attempt - 1))
            if delay > max_retry_sleep_seconds:
                raise last_error from error
            delay = max(0.0, delay + jitter(0.0, min(0.1, delay * 0.1)))
            if delay >= remaining_timeout(timeout):
                raise last_error from error
            sleep(delay)
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
            delay += jitter(0.0, min(0.1, delay * 0.1))
            if delay >= remaining_timeout(timeout):
                raise last_error from error
            sleep(delay)

    raise last_error or ProviderHTTPError("Provider request failed", endpoint=url)
