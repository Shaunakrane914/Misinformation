"""
Aegis Protocol — Scout Reddit Adapter (Shim)
============================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.adapters.reddit_adapter`.
"""

from backend.agents.scout.sources.adapters.reddit_adapter import (
    RedditAdapter,
)

__all__ = [
    "RedditAdapter",
]
