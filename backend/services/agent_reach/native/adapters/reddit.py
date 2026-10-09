"""
[LEGACY_COMPATIBILITY_SHIM]
Aegis Protocol — Reddit Zero-Auth Specialist Adapter Shim
===========================================================
Re-exports canonical Reddit adapter from:
backend.infrastructure.acquisition.adapters.social.reddit
"""

from backend.infrastructure.acquisition.adapters.social.reddit import (
    ARCTIC_SHIFT_BASE,
    RedditAdapter,
    fetch_arctic_shift_comments,
    fetch_arctic_shift_post,
    fetch_arctic_shift_posts_batch,
    fetch_arctic_shift_search,
)

__all__ = [
    "ARCTIC_SHIFT_BASE",
    "RedditAdapter",
    "fetch_arctic_shift_comments",
    "fetch_arctic_shift_post",
    "fetch_arctic_shift_posts_batch",
    "fetch_arctic_shift_search",
]
