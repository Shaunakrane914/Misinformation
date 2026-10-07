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
        clean_url = url.strip()
        if not clean_url:
            return 400, "", {}, 0, "EMPTY_URL"

        # 1. SSRF Gate
        is_safe, reason = validate_url_safe(clean_url)
        if not is_safe:
            logger.warning(f"[ScoutTransport] SSRF check blocked {clean_url}: {reason}")
            return 403, "", {}, 0, f"BLOCKED_SSRF: {reason}"

        # 2. Domain Rate Limiting
        try:
            parsed = urllib.parse.urlparse(clean_url)
            domain = parsed.netloc or ""
            self.rate_limiter.wait_for_domain(domain)
        except Exception:
            pass

        req_timeout = timeout or self.default_timeout
        merged_headers = dict(self.session.headers)
        if headers:
            merged_headers.update(headers)

        # 3. Retries with exponential backoff on 429/503
        last_error = None
        for attempt in range(max_retries + 1):
            t0 = time.time()
            try:
                resp = self.session.get(
                    clean_url,
                    params=params,
                    headers=merged_headers,
                    timeout=req_timeout
                )
                latency_ms = int((time.time() - t0) * 1000)
                resp_headers = dict(resp.headers)

                if resp.status_code in (429, 503) and attempt < max_retries:
                    backoff = 0.5 * (2 ** attempt)
                    time.sleep(backoff)
                    continue

                return resp.status_code, resp.text, resp_headers, latency_ms, None

            except requests.Timeout as te:
                last_error = f"TIMEOUT: {te}"
            except requests.RequestException as re:
                last_error = f"REQUEST_ERROR: {re}"
            except Exception as e:
                last_error = f"UNEXPECTED_TRANSPORT_ERROR: {e}"

            if attempt < max_retries:
                time.sleep(0.4 * (2 ** attempt))

        latency_ms = int((time.time() - t0) * 1000) if 't0' in locals() else 0
        return 0, "", {}, latency_ms, last_error


# Global singleton transport for Scout
scout_transport = ScoutTransport()
