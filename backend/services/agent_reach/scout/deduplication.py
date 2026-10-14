"""
Aegis Protocol — Scout Deduplicator (Shim)
==========================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.deduplication`.
"""

from backend.agents.scout.sources.deduplication import (
    WIRE_SIGNATURES,
    ScoutDeduplicator,
    scout_deduplicator,
)

__all__ = [
    "ScoutDeduplicator",
    "scout_deduplicator",
    "WIRE_SIGNATURES",
]
