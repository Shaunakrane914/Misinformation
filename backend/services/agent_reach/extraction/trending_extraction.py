"""
Aegis Protocol — Trending Domain Extraction Engine (Shim)
=========================================================
Backward-compatibility shim. The canonical Trending extraction implementation
now lives in the agent-owned package: `backend.agents.trending.extraction`.
"""

from backend.agents.trending.extraction import (
    TrendingExtractionEngine,
    trending_extractor,
)
from backend.agents.trending.models import (
    NarrativeCluster,
    TrendingExtractionResult,
    TrendRecord,
    WIRE_SYNDICATION_DOMAINS,
)

__all__ = [
    "TrendingExtractionEngine",
    "TrendingExtractionResult",
    "TrendRecord",
    "NarrativeCluster",
    "WIRE_SYNDICATION_DOMAINS",
    "trending_extractor",
]
