"""
Aegis Protocol — Scout Temporal Extractor (Shim)
================================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.extraction.temporal`.
"""

from backend.agents.scout.sources.extraction.temporal import (
    TemporalExtractor,
    temporal_extractor,
)

__all__ = [
    "TemporalExtractor",
    "temporal_extractor",
]
