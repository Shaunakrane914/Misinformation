"""
Aegis Protocol — Scout Source Adapter Base (Shim)
=================================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.adapters.base`.
"""

from backend.agents.scout.sources.adapters.base import (
    ScoutSourceAdapter,
)

__all__ = [
    "ScoutSourceAdapter",
]
