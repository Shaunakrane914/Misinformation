"""
Trending Agent 2.0 (Backward Compatibility Shim)
================================================
Canonical implementation relocated to `backend.agents.trending`.
Preserves historical import paths, class identities, and architectural contracts.
"""

from backend.services.agent_reach import agent_reach_service  # Architecture contract preservation
from backend.agents.trending import (
    TrendingAgent,
    trending_agent,
    TrendEvidence,
    TrendNarrative,
    TrendClaim,
    Trend,
    KNOWN_ENTITY_CATALOG,
    WIRE_SIGNATURES,
    NarrativeCluster,
    TrendRecord,
    TrendingExtractionResult,
    fetch_news,
    fetch_targeted_news,
    fetch_paparazzi,
    fetch_box_office,
)

__all__ = [
    "TrendingAgent",
    "trending_agent",
    "TrendEvidence",
    "TrendNarrative",
    "TrendClaim",
    "Trend",
    "KNOWN_ENTITY_CATALOG",
    "WIRE_SIGNATURES",
    "NarrativeCluster",
    "TrendRecord",
    "TrendingExtractionResult",
    "fetch_news",
    "fetch_targeted_news",
    "fetch_paparazzi",
    "fetch_box_office",
    "agent_reach_service",
]
