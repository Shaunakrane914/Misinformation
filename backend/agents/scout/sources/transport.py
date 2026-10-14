"""
Aegis Protocol — Scout Transport & Session Manager
==================================================
Handles HTTP connections, connection reuse, bounded concurrency, token-bucket
rate limiting per domain, SSRF security validation, and retry backoff.
"""

import logging
import threading
import time
import urllib.parse
from typing import Any, Dict, Optional, Tuple
import requests

from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 AegisScout/1.0"
)


class DomainRateLimiter:
    """
    Token-bucket / delay rate limiter per target domain.
    Prevents triggering bot detection on Bing, Yahoo, Arctic Shift, and FxTwitter.
    """

    def __init__(self, default_min_interval: float = 0.5):
        self._lock = threading.Lock()
        self._last_request_time: Dict[str, float] = {}
        self._domain_intervals: Dict[str, float] = {
            "bing.com": 0.65,
            "yahoo.com": 0.60,
            "arctic-shift.photon-reddit.com": 0.40,
            "api.fxtwitter.com": 0.35,
            "sec.gov": 0.70,
        }
        self._default_interval = default_min_interval

    def wait_for_domain(self, domain: str) -> None:
        """Enforce domain-specific pacing."""
        d = domain.lower()
        # Find matching interval
        min_interval = self._default_interval
        for key, val in self._domain_intervals.items():
            if key in d:
                min_interval = val
                break

        with self._lock:
            now = time.time()
            last = self._last_request_time.get(d, 0.0)
            elapsed = now - last
            wait_time = min_interval - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
            self._last_request_time[d] = time.time()


class ScoutTransport:
    """
    Centralized, connection-pooled transport client for ScoutSourceEngine.
    Enforces SSRF boundaries and connection reuse.
    """

    def __init__(self, default_timeout: float = 10.0):
        self.default_timeout = default_timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.rate_limiter = DomainRateLimiter()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: int = 2
    ) -> Tuple[int, str, Dict[str, str], int, Optional[str]]:
        """
        Execute an SSRF-safe, rate-paced GET request.

        Returns:
            (status_code, content_text, response_headers, latency_ms, error_message)
        """
        from backend.infrastructure.acquisition.network.http import fetch_public_http, decode_bounded_http_body
        clean_url = (url or "").strip()
        if not clean_url:
            return 400, "", {}, 0, "EMPTY_URL"
        if params:
            parsed = urllib.parse.urlsplit(clean_url)
            query = urllib.parse.urlencode(params, doseq=True)
            clean_url = urllib.parse.urlunsplit(parsed._replace(query="&".join(filter(None, [parsed.query, query]))))
        merged_headers = dict(self.session.headers)
        merged_headers.update(headers or {})
        started = time.monotonic()
        try:
            self.rate_limiter.wait_for_domain(urllib.parse.urlsplit(clean_url).hostname or "")
            response = fetch_public_http(
                clean_url, headers=merged_headers,
                timeout=min(5.0, float(timeout or self.default_timeout)),
                max_bytes=1_000_000, max_attempts=max(1, min(3, max_retries + 1)),
            )
            body = decode_bounded_http_body(response, max_bytes=1_000_000)
            response_headers = dict(response.headers)
            response_headers["X-Aegis-Observed-Endpoint"] = response.endpoint
            return response.status_code or 200, body.decode("utf-8", errors="replace"), response_headers, int((time.monotonic() - started) * 1000), None
        except Exception as exc:
            return getattr(exc, "status_code", None) or 0, "", {}, int((time.monotonic() - started) * 1000), type(exc).__name__



# Global singleton transport for Scout
scout_transport = ScoutTransport()
