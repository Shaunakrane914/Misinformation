"""
Aegis Protocol — Social Platform Acquisition Adapters
======================================================
Zero-auth public mirror adapters for Reddit (Arctic Shift) and Twitter/X (FxTwitter).
"""

from backend.infrastructure.acquisition.adapters.social.reddit import (
    ARCTIC_SHIFT_BASE,
    RedditAdapter,
    fetch_arctic_shift_comments,
    fetch_arctic_shift_post,
    fetch_arctic_shift_posts_batch,
    fetch_arctic_shift_search,
)
from backend.infrastructure.acquisition.adapters.social.twitter import (
    FXTWITTER_BASE,
    TwitterAdapter,
    fetch_fxtwitter_profile,
    fetch_fxtwitter_status,
)

__all__ = [
    "ARCTIC_SHIFT_BASE",
    "RedditAdapter",
    "fetch_arctic_shift_comments",
    "fetch_arctic_shift_post",
    "fetch_arctic_shift_posts_batch",
    "fetch_arctic_shift_search",
    "FXTWITTER_BASE",
    "TwitterAdapter",
    "fetch_fxtwitter_profile",
    "fetch_fxtwitter_status",
]
