"""
Aegis Protocol — Scout Cache (Shim)
===================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.cache`.
"""

from backend.agents.scout.sources.cache import (
    ScoutCache,
    scout_cache,
)

__all__ = [
    "ScoutCache",
    "scout_cache",
]
