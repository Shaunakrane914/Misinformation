"""
Aegis Protocol — Scout Source Adapters (Shim)
=============================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.adapters`.
"""

from backend.agents.scout.sources.adapters import (
    ALL_SCOUT_ADAPTERS,
    GenericWebAdapter,
    GitHubAdapter,
    PrimaryFilingAdapter,
    RedditAdapter,
    ScoutSourceAdapter,
    XAdapter,
    YouTubeAdapter,
)

__all__ = [
    "ScoutSourceAdapter",
    "PrimaryFilingAdapter",
    "GenericWebAdapter",
    "RedditAdapter",
    "XAdapter",
    "GitHubAdapter",
    "YouTubeAdapter",
    "ALL_SCOUT_ADAPTERS",
]
