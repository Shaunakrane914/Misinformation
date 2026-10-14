"""
Aegis Protocol — Scout Web Adapter (Shim)
=========================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.adapters.web_adapter`.
"""

from backend.agents.scout.sources.adapters.web_adapter import (
    GenericWebAdapter,
)

__all__ = [
    "GenericWebAdapter",
]
