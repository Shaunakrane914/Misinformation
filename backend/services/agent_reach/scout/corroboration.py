"""
Aegis Protocol — Scout Corroboration Engine (Shim)
==================================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.corroboration`.
"""

from backend.agents.scout.sources.corroboration import (
    ScoutCorroborationEngine,
    scout_corroboration_engine,
)

__all__ = [
    "ScoutCorroborationEngine",
    "scout_corroboration_engine",
]
