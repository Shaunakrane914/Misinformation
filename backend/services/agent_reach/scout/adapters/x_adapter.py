"""
Aegis Protocol — Scout X Adapter (Shim)
=======================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.adapters.x_adapter`.
"""

from backend.agents.scout.sources.adapters.x_adapter import (
    XAdapter,
)

__all__ = [
    "XAdapter",
]
