"""
Aegis Protocol — Scout Source Engine Cache
==========================================
Bounded TTL cache for raw content, immutable source IDs, and canonical URLs.
Supports force refresh and stale-while-revalidate policies.
"""

import threading
import time
from typing import Any, Dict, Optional, Tuple


class ScoutCache:
    """
    Thread-safe, bounded in-memory cache for Scout acquisitions.
    """

    def __init__(self, default_ttl_sec: float = 600.0, max_items: int = 1000):
        self.default_ttl = default_ttl_sec
        self.max_items = max_items
        self._lock = threading.Lock()
        self._store: Dict[str, Tuple[float, Any, float]] = {}  # key -> (timestamp, data, ttl)

    def get(self, key: str, max_age_sec: Optional[float] = None) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            ts, val, ttl = self._store[key]
            effective_ttl = max_age_sec if max_age_sec is not None else ttl
            if time.time() - ts < effective_ttl:
                return val
            # Expired
            del self._store[key]
            return None

    def set(self, key: str, val: Any, ttl_sec: Optional[float] = None) -> None:
        with self._lock:
            # Enforce max bounds
            if len(self._store) >= self.max_items:
                # Evict oldest 20%
                sorted_keys = sorted(self._store.keys(), key=lambda k: self._store[k][0])
                for old_k in sorted_keys[:int(self.max_items * 0.2)]:
                    del self._store[old_k]

            self._store[key] = (time.time(), val, ttl_sec or self.default_ttl)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


scout_cache = ScoutCache()
