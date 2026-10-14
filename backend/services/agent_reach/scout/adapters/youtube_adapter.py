"""
Aegis Protocol — Scout YouTube Adapter (Shim)
=============================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.adapters.youtube_adapter`.
"""

from backend.agents.scout.sources.adapters.youtube_adapter import (
    YouTubeAdapter,
)

__all__ = [
    "YouTubeAdapter",
]
