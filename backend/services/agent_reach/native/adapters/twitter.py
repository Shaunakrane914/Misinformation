"""
[LEGACY_COMPATIBILITY_SHIM]
Aegis Protocol — Twitter/X Zero-Auth Specialist Adapter Shim
=============================================================
Re-exports canonical Twitter adapter from:
backend.infrastructure.acquisition.adapters.social.twitter
"""

from backend.infrastructure.acquisition.adapters.social.twitter import (
    FXTWITTER_BASE,
    TwitterAdapter,
    fetch_fxtwitter_profile,
    fetch_fxtwitter_status,
)

__all__ = [
    "FXTWITTER_BASE",
    "TwitterAdapter",
    "fetch_fxtwitter_profile",
    "fetch_fxtwitter_status",
]
