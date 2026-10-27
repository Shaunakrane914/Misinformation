"""Unit tests for Async HTTP Transport, SSRF Pinning & Domain Rate Limiter."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.infrastructure.acquisition.network.async_http import (
    PinnedAsyncHTTPTransport,
    PinnedNetworkBackend,
    fetch_public_async_http,
)
from backend.infrastructure.acquisition.network.http import (
    BoundedHTTPResponse,
    ProviderHTTPError,
    ResponseTooLargeError,
)
from backend.infrastructure.acquisition.network.rate_limiter import (
    DomainRateLimiter,
    domain_rate_limiter,
)


def test_pinned_network_backend_blocks_private_ip():
    async def _test():
        backend = PinnedNetworkBackend()
        with pytest.raises(ProviderHTTPError) as exc_info:
            await backend.connect_tcp("127.0.0.1", 80)
        assert "SSRF policy" in str(exc_info.value)

    asyncio.run(_test())


def test_pinned_network_backend_blocks_cloud_metadata():
    async def _test():
        backend = PinnedNetworkBackend()
        with pytest.raises(ProviderHTTPError) as exc_info:
            await backend.connect_tcp("169.254.169.254", 80)
        assert "SSRF policy" in str(exc_info.value)

    asyncio.run(_test())


def test_fetch_public_async_http_rejects_unsafe_url():
    async def _test():
        with pytest.raises(ProviderHTTPError) as exc_info:
            await fetch_public_async_http("http://192.168.1.1/admin")
        assert "SSRF policy" in str(exc_info.value)

    asyncio.run(_test())


def test_fetch_public_async_http_response_too_large():
    async def _test():
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = httpx.Headers({"content-type": "text/plain"})

        async def mock_aiter_bytes():
            yield b"A" * 600
            yield b"B" * 600

        mock_response.aiter_raw = mock_aiter_bytes
        mock_response.aclose = AsyncMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        mock_client.build_request.return_value = MagicMock()
        mock_client.send = AsyncMock(return_value=mock_response)

        with patch("backend.infrastructure.acquisition.network.async_http.is_safe_url", return_value=(True, "")):
            with pytest.raises(ResponseTooLargeError) as exc_info:
                await fetch_public_async_http(
                    "https://public.example.com/huge.bin",
                    max_bytes=1000,
                    client=mock_client,
                )
            assert "exceeded maximum allowed 1000 bytes" in str(exc_info.value)

    asyncio.run(_test())


def test_fetch_public_async_http_strips_credentials_on_cross_origin_redirect():
    async def _test():
        redirect_response = MagicMock(spec=httpx.Response)
        redirect_response.status_code = 302
        redirect_response.headers = httpx.Headers({"location": "https://other-domain.example.com/target"})
        redirect_response.aclose = AsyncMock()

        final_response = MagicMock(spec=httpx.Response)
        final_response.status_code = 200
        final_response.headers = httpx.Headers({"content-type": "text/html"})

        async def mock_aiter_bytes():
            yield b"<html>Final Page</html>"

        final_response.aiter_raw = mock_aiter_bytes
        final_response.aclose = AsyncMock()

        mock_client = MagicMock(spec=httpx.AsyncClient)
        captured_headers = []

        def fake_build_request(method, url, headers=None, **kwargs):
            captured_headers.append((url, dict(headers or {})))
            req = MagicMock()
            req.url = url
            return req

        mock_client.build_request.side_effect = fake_build_request
        mock_client.send = AsyncMock(side_effect=[redirect_response, final_response])

        with patch("backend.infrastructure.acquisition.network.async_http.is_safe_url", return_value=(True, "")):
            res = await fetch_public_async_http(
                "https://first.example.com/start",
                headers={"Authorization": "Bearer secret-token", "Accept": "text/html"},
                client=mock_client,
            )

            assert res.status_code == 200
            assert len(captured_headers) == 2
            # First request had Authorization
            assert "Authorization" in captured_headers[0][1]
            # Cross-origin redirected request MUST NOT have Authorization
            assert "Authorization" not in captured_headers[1][1]
            assert "Accept" in captured_headers[1][1]
            assert len(res.redirect_chain) == 2

    asyncio.run(_test())


def test_domain_rate_limiter():
    async def _test():
        limiter = DomainRateLimiter(default_rate=10.0, default_capacity=5.0)

        # Initial tokens available, wait should be 0.0
        w1 = await limiter.acquire("https://news.example.com/article-1")
        assert w1 == 0.0

        # Override domain rate to be very low and consume all tokens
        limiter.set_rate("slow.example.com", rate=100.0, capacity=1.0)
        w_initial = await limiter.acquire("https://slow.example.com/page1", tokens=1.0)
        assert w_initial == 0.0

        # Immediate second request should wait slightly (around 0.01s for 100 req/s)
        t0 = asyncio.get_event_loop().time()
        w_second = await limiter.acquire("https://slow.example.com/page2", tokens=1.0)
        t_elapsed = asyncio.get_event_loop().time() - t0
        assert w_second > 0.0
        assert t_elapsed >= 0.005

    asyncio.run(_test())
