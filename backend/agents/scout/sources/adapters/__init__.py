"""
Aegis Protocol — Scout Adapters Registry
"""

from typing import List
from .base import ScoutSourceAdapter
from .web_adapter import GenericWebAdapter
from .reddit_adapter import RedditAdapter
from .x_adapter import XAdapter
from .primary_adapter import PrimaryFilingAdapter
from .youtube_adapter import YouTubeAdapter
from .github_adapter import GitHubAdapter

ALL_SCOUT_ADAPTERS: List[ScoutSourceAdapter] = [
    PrimaryFilingAdapter(),
    RedditAdapter(),
    XAdapter(),
    YouTubeAdapter(),
    GitHubAdapter(),
    GenericWebAdapter(),  # Fallback for general web & news
]

__all__ = [
    "ScoutSourceAdapter",
    "GenericWebAdapter",
    "RedditAdapter",
    "XAdapter",
    "PrimaryFilingAdapter",
    "YouTubeAdapter",
    "GitHubAdapter",
    "ALL_SCOUT_ADAPTERS",
]
