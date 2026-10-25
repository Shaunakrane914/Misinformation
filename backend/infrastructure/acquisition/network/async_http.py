"""Bounded, connection-pinned, redirect-safe optional async HTTP transport.

Throughput improvements require independent measurement.
Enforces non-blocking DNS pre-resolution, SSRF verification, numeric socket pinning,
1 MB streaming response bounds, redirect origin credential stripping, and
per-domain rate limiting compatibility.
"""

from __future__ import annotations

import asyncio
import email.utils
import hashlib
import logging
import math
import weakref
import threading
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Mapping, Optional, Set, Tuple

import httpcore
import httpx

from backend.infrastructure.acquisition.network.http import (
    DEFAULT_MAX_RESPONSE_BYTES,
    NON_RETRYABLE_STATUS_CODES,
    RETRYABLE_STATUS_CODES,
    BoundedHTTPResponse,
    ProviderHTTPError,
    ResponseTooLargeError,
    parse_retry_after,
)
from backend.infrastructure.acquisition.security.url_validator import (
    is_safe_url,
    resolve_public_addresses,
)

logger = logging.getLogger(__name__)


def _origin(url: str) -> Tuple[str, str, int]:
    """Extract (scheme, hostname, port) from URL for origin comparison."""
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    port = parsed.port or (443 if scheme == "https" else 80)
    return (scheme, (parsed.hostname or "").lower(), port)


class PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Async network backend that connects exclusively to pre-validated numeric IPs.

    Resolves DNS using resolve_public_addresses, ensures zero private/reserved IPs
    exist in the resolution set, and connects directly to the numeric sockaddr while
    preserving the original hostname for HTTP Host and TLS SNI verification.
    """

    def __init__(self, default_backend: Optional[httpcore.AsyncNetworkBackend] = None) -> None:
        self._default = default_backend or httpcore._backends.auto.AutoBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options: Any = None,
    ) -> httpcore.AsyncNetworkStream:
        try:
            addrs = await asyncio.wait_for(asyncio.to_thread(
                resolve_public_addresses, host, port, timeout=min(2.5, timeout or 5.0)),
                timeout=min(2.5, timeout or 5.0))
        except ValueError as err:
            raise ProviderHTTPError(
                f"Connection blocked by SSRF policy: {err}",
                endpoint=f"{host}:{port}",
                network_observed=False,
            ) from err

        last_error = None
        for family, socktype, proto, _, sockaddr in addrs:
            numeric_ip = sockaddr[0]
            try:
                return await self._default.connect_tcp(
                    numeric_ip,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except OSError as error:
                last_error = error

        raise last_error or OSError(f"No public address could be connected for {host}:{port}")

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class PinnedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """HTTPX Async Transport with connection-level DNS pinning and connection pooling."""

    def __init__(
        self,
        max_connections: int = 16,
        max_keepalive_connections: int = 8,
        keepalive_expiry: float = 30.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
                keepalive_expiry=keepalive_expiry,
            ),
            **kwargs,
        )
        self._pool = httpcore.AsyncConnectionPool(
            network_backend=PinnedNetworkBackend(),
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            http1=True,
            http2=False,
        )


_ASYNC_CLIENTS = weakref.WeakKeyDictionary()
_CLIENT_LOCK = threading.Lock()


async def get_shared_async_client() -> httpx.AsyncClient:
    """One client per running loop; never reuse loop-bound pools in other loops."""
    loop = asyncio.get_running_loop()
    with _CLIENT_LOCK:
        client = _ASYNC_CLIENTS.get(loop)
        if client is None or client.is_closed:
            client = httpx.AsyncClient(transport=PinnedAsyncHTTPTransport(
                max_connections=16, max_keepalive_connections=8),
                follow_redirects=False, trust_env=False, timeout=httpx.Timeout(5.0))
            _ASYNC_CLIENTS[loop] = client
        return client


async def close_shared_async_client() -> None:
    with _CLIENT_LOCK:
        client = _ASYNC_CLIENTS.pop(asyncio.get_running_loop(), None)
    if client is not None and not client.is_closed:
        await client.aclose()


async def fetch_public_async_http(url: str, *, headers=None, timeout=5.0,
                                  max_bytes=DEFAULT_MAX_RESPONSE_BYTES,
                                  max_redirects=4, max_retries=0, client=None, now=None):
    """Bound the entire operation, including DNS, limiter wait and body streaming."""
    if not math.isfinite(float(timeout)) or timeout <= 0:
        raise TimeoutError("Public async HTTP deadline expired")
    if not 0 < max_bytes <= DEFAULT_MAX_RESPONSE_BYTES or not 0 <= max_redirects <= 4 or not 0 <= max_retries <= 1:
        raise ValueError("Public async HTTP limits exceeded")
    timeout = min(float(timeout), 5.0)
    try:
        from backend.infrastructure.acquisition.network.budget import remaining_timeout
        timeout = remaining_timeout(timeout)
    except ImportError:
        pass  # Older checkout has no request-budget module; local bound remains.
    async with asyncio.timeout(timeout):
        return await _fetch_public_async_http(url, headers=headers, timeout=timeout,
            max_bytes=max_bytes, max_redirects=max_redirects, max_retries=max_retries,
            client=client, now=now)


async def _fetch_public_async_http(
    url: str,
    *,
    headers: Optional[Mapping[str, str]] = None,
    timeout: float = 5.0,
    max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    max_redirects: int = 4,
    max_retries: int = 1,
    client: Optional[httpx.AsyncClient] = None,
    now: Optional[datetime] = None,
) -> BoundedHTTPResponse:
    """Execute high-speed async HTTP request with DNS pinning, SSRF checks, and size bounds."""
    t0 = time.perf_counter()
    safe, reason = await asyncio.to_thread(is_safe_url, url)
    if not safe:
        raise ProviderHTTPError(
            f"Connection blocked by SSRF policy: {reason}",
            endpoint=url,
            network_observed=False,
        )

    current_headers = dict(headers or {})
    current_headers.setdefault("Accept-Encoding", "identity")
    current_url = url
    redirect_chain: List[str] = [url]
    active_client = client or await get_shared_async_client()
    deadline = time.monotonic() + timeout

    attempts = 0
    while True:
        attempts += 1
        remaining_timeout = deadline - time.monotonic()
        if remaining_timeout <= 0:
            raise TimeoutError("Public async HTTP connection deadline expired")

        try:
            from backend.infrastructure.acquisition.network.rate_limiter import domain_rate_limiter
            await domain_rate_limiter.acquire(current_url)
            try:
                from backend.infrastructure.acquisition.network.budget import reserve_public_request
                reserve_public_request(current_url)
            except ImportError:
                pass
            remaining_timeout = deadline - time.monotonic()
            if remaining_timeout <= 0:
                raise TimeoutError("Public async HTTP deadline expired")
            req = active_client.build_request(
                "GET",
                current_url,
                headers=current_headers,
                timeout=remaining_timeout,
            )
            if len(redirect_chain) > 1:
                # HTTP header names are case-insensitive, including client defaults.
                allowed = {"accept", "accept-language", "accept-encoding", "user-agent", "cache-control"}
                if _origin(current_url) != _origin(url):
                    for name in list(req.headers):
                        if name.casefold() not in allowed | {"host"}:
                            del req.headers[name]
                    req.headers["host"] = urllib.parse.urlsplit(current_url).netloc
            # Disable implicit client auth flows: they can inject credentials
            # after request-header scrubbing on a redirected public fetch.
            response = await active_client.send(req, stream=True, follow_redirects=False, auth=None)

            # Check rate limit headers
            rate_remaining = None
            rate_reset = None
            if "x-ratelimit-remaining" in response.headers:
                try:
                    rate_remaining = int(response.headers["x-ratelimit-remaining"])
                except (ValueError, TypeError):
                    pass
            if "x-ratelimit-reset" in response.headers:
                rate_reset = response.headers["x-ratelimit-reset"]

            # Handle Redirects (3xx)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                await response.aclose()
                if not location:
                    raise ProviderHTTPError(
                        "Redirect response missing Location header",
                        endpoint=current_url,
                        status_code=response.status_code,
                        network_observed=True,
                    )
                target_url = urllib.parse.urljoin(current_url, location)
                safe_target, target_reason = await asyncio.to_thread(is_safe_url, target_url)
                if not safe_target or (_origin(current_url)[0] == "https" and _origin(target_url)[0] != "https"):
                    raise ProviderHTTPError(
                        f"Redirect blocked by SSRF policy: {target_reason}",
                        endpoint=target_url,
                        status_code=response.status_code,
                        network_observed=True,
                    )

                if len(redirect_chain) > max_redirects:
                    raise ProviderHTTPError(
                        f"Redirect limit exceeded ({max_redirects})",
                        endpoint=target_url,
                        status_code=response.status_code,
                        network_observed=True,
                    )

                # Strip credentials if origin changes
                if _origin(current_url) != _origin(target_url):
                    allowed = {"accept", "accept-language", "accept-encoding", "user-agent", "cache-control"}
                    current_headers = {key: value for key, value in current_headers.items() if key.casefold() in allowed}

                current_url = target_url
                redirect_chain.append(target_url)
                continue

            # Check retryable status codes
            if response.status_code in RETRYABLE_STATUS_CODES and attempts <= max_retries:
                retry_after_hdr = response.headers.get("retry-after")
                retry_sec = parse_retry_after(retry_after_hdr, now=now)
                await response.aclose()
                if retry_sec is not None and retry_sec > remaining_timeout:
                    raise ProviderHTTPError(
                        f"Provider requested retry-after ({retry_sec}s) exceeds available deadline",
                        endpoint=current_url,
                        status_code=response.status_code,
                        retry_after_seconds=retry_sec,
                        network_observed=True,
                        rate_limit_remaining=rate_remaining,
                        rate_limit_reset_at=rate_reset,
                    )
                sleep_duration = min(retry_sec or 0.2 * (2 ** (attempts - 1)), remaining_timeout)
                await asyncio.sleep(sleep_duration)
                continue

            # Stream body within max_bytes bound
            body_chunks = []
            total_bytes = 0
            try:
                async for chunk in response.aiter_raw():
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        await response.aclose()
                        raise ResponseTooLargeError(
                            f"Response exceeded maximum allowed {max_bytes} bytes",
                            endpoint=current_url,
                            status_code=response.status_code,
                            network_observed=True,
                            attempts=attempts,
                        )
                    body_chunks.append(chunk)
            finally:
                await response.aclose()

            full_body = b"".join(body_chunks)
            encoding = response.headers.get("content-encoding", "identity").lower()
            if encoding == "gzip":
                from backend.infrastructure.acquisition.adapters.expansion_safety import bounded_decode
                full_body = bounded_decode(full_body, max_bytes)
            elif encoding not in {"", "identity"}:
                raise ProviderHTTPError("Unsupported response encoding", endpoint=current_url,
                                        network_observed=True, attempts=attempts)
            lat = int((time.perf_counter() - t0) * 1000)

            return BoundedHTTPResponse(
                body=full_body,
                endpoint=current_url,
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
                headers={key: value for key, value in response.headers.items() if key.casefold() not in {"content-encoding", "content-length", "set-cookie"}},
                latency_ms=lat,
                attempts=attempts,
                redirect_chain=tuple(redirect_chain),
            )

        except (ResponseTooLargeError, ProviderHTTPError):
            raise
        except Exception as exc:
            if attempts <= max_retries and (time.monotonic() < deadline):
                await asyncio.sleep(0.1 * attempts)
                continue
            raise ProviderHTTPError(
                "Async HTTP transport failed",
                endpoint=current_url,
                network_observed=True,
                attempts=attempts,
            ) from exc
