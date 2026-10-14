"""
Aegis Protocol — Scout Primary Filing Adapter (Shim)
====================================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.adapters.primary_adapter`.
"""

from backend.agents.scout.sources.adapters.primary_adapter import (
    PrimaryFilingAdapter,
)

__all__ = [
    "PrimaryFilingAdapter",
]
