"""Bounded per-domain admission pacing; provider quota compliance is not inferred."""

from __future__ import annotations

import asyncio
import threading
import math
import time
import urllib.parse
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class TokenBucket:
    """Token bucket state for a single target domain."""
    rate: float          # Tokens replenished per second
    capacity: float      # Maximum token burst capacity
    tokens: float        # Current token count
    last_update: float   # Timestamp of last replenishment


class DomainRateLimiter:
    """Loop-independent admission pacing, not a provider quota guarantee."""
    DEFAULT_DOMAIN_RATES = {"data.sec.gov": (1.0, 1.0), "www.sec.gov": (1.0, 1.0)}

    def __init__(self, default_rate=1.0, default_capacity=1.0):
        if not all(math.isfinite(v) and v > 0 for v in (default_rate, default_capacity)):
            raise ValueError("Positive finite limits required")
        self.default_rate, self.default_capacity = default_rate, default_capacity
        self._buckets, self._lock = {}, threading.Lock()

    def _extract_domain(self, target):
        return ((urllib.parse.urlsplit(target).hostname or "") if "://" in target else target.split("/")[0].split(":")[0]).lower()

    async def acquire(self, url_or_domain, tokens=1.0):
        domain = self._extract_domain(url_or_domain)
        if not domain or not math.isfinite(tokens) or tokens <= 0:
            raise ValueError("Valid hostname and positive finite tokens required")
        with self._lock:
            now = time.monotonic()
            bucket = self._buckets.get(domain)
            if bucket is None:
                if len(self._buckets) >= 1024:
                    raise RuntimeError("Domain limiter capacity exhausted")
                rate, capacity = self.DEFAULT_DOMAIN_RATES.get(domain, (self.default_rate, self.default_capacity))
                bucket = self._buckets[domain] = TokenBucket(rate, capacity, capacity, now)
            if tokens > bucket.capacity:
                raise ValueError("Tokens exceed burst capacity")
            elapsed = max(0.0, now - bucket.last_update)
            bucket.tokens = min(bucket.capacity, bucket.tokens + elapsed * bucket.rate)
            wait = max(0.0, bucket.last_update - now) + max(0.0, tokens - bucket.tokens) / bucket.rate
            bucket.tokens = max(0.0, bucket.tokens - tokens)
            bucket.last_update = now + wait
        # Cancellation consumes the reservation conservatively.
        if wait:
            await asyncio.sleep(wait)
        return wait

    def set_rate(self, domain, rate, capacity=None):
        capacity = capacity if capacity is not None else max(1.0, rate * 2.0)
        if not all(math.isfinite(v) and v > 0 for v in (rate, capacity)):
            raise ValueError("Positive finite limits required")
        with self._lock:
            prior = self._buckets.get(self._extract_domain(domain))
            self._buckets[self._extract_domain(domain)] = TokenBucket(rate, capacity,
                min(prior.tokens, capacity) if prior else capacity,
                max(time.monotonic(), prior.last_update) if prior else time.monotonic())


domain_rate_limiter = DomainRateLimiter()
