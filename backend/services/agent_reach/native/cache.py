"""
Aegis Protocol — Social & Acquisition Cache
============================================
Thread-safe, TTL-bounded cache for public social mirror requests and document reads.
Prevents duplicate fetches, reduces burst pressure on mirrors (Arctic Shift / FxTwitter),
and mitigates rate-limit sensitivity.
"""

import os
import threading
import time
from typing import Any, Dict, Optional, Tuple


class SocialCache:
    """
    In-memory, TTL-backed cache for raw and normalized acquisition results.
    Configured via AEGIS_SOCIAL_CACHE_TTL (default: 600.0 seconds).
    """

    def __init__(self, ttl: Optional[float] = None):
        if ttl is not None:
            self.ttl = float(ttl)
        else:
            self.ttl = float(os.getenv("AEGIS_SOCIAL_CACHE_TTL", "600.0"))
        self._lock = threading.Lock()
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._hits: int = 0
        self._misses: int = 0

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item if present and not expired."""
        with self._lock:
            if key in self._store:
                ts, val = self._store[key]
                if time.time() - ts < self.ttl:
                    self._hits += 1
                    return val
                del self._store[key]
            self._misses += 1
            return None

    def set(self, key: str, val: Any) -> None:
        """Store item with current timestamp. Discards None values to prevent poison."""
        if val is None:
            return
        with self._lock:
            self._store[key] = (time.time(), val)

    def delete(self, key: str) -> None:
        """Remove a key from cache."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        """Return cache health and usage statistics."""
        with self._lock:
            return {
                "size": len(self._store),
                "ttl_seconds": self.ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": (self._hits / (self._hits + self._misses)) if (self._hits + self._misses) > 0 else 0.0,
            }


# Global singleton instance for shared acquisition fabric
social_cache = SocialCache()
