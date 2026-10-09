"""
[LEGACY_COMPATIBILITY_SHIM]
Aegis Protocol — Native Agent Reach Router Shim
=================================================
Re-exports canonical capability router from:
backend.infrastructure.acquisition.routing.router
"""

from backend.infrastructure.acquisition.routing.router import (
    NativeRouter,
    native_router,
    _get_legacy_scraper as _orig_get_legacy_scraper,
)


def _get_legacy_scraper():
    return _orig_get_legacy_scraper()


__all__ = [
    "NativeRouter",
    "native_router",
    "_get_legacy_scraper",
]
