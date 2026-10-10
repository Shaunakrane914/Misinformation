"""
Aegis Protocol — Trending Domain Agent Package
===============================================
Autonomous trend discovery, narrative extraction, velocity tracking, and trend intelligence.
Owns domain entity resolution, multi-channel discovery, trend clustering, syndication detection,
velocity and temporal tracking, and trend intelligence reporting.
"""

from backend.agents.trending.agent import TrendingAgent, trending_agent
from backend.agents.trending.assessment import (
    compute_cluster_sentiment,
    evaluate_misinformation_risk,
)
from backend.agents.trending.clustering import (
    cluster_trends,
    detect_syndication_group,
    extract_claims_from_cluster,
    extract_narratives_from_cluster,
)
from backend.agents.trending.discovery import (
    fetch_box_office,
    fetch_news,
    fetch_paparazzi,
    fetch_targeted_news,
    resolve_entity,
)
from backend.agents.trending.extraction import (
    TrendingExtractionEngine,
    trending_extractor,
)
from backend.agents.trending.models import (
    KNOWN_ENTITY_CATALOG,
    WIRE_SIGNATURES,
    WIRE_SYNDICATION_DOMAINS,
    NarrativeCluster,
    Trend,
    TrendClaim,
    TrendEvidence,
    TrendNarrative,
    TrendRecord,
    TrendingExtractionResult,
)
from backend.agents.trending.temporal import (
    calculate_velocity,
    parse_timestamp_epoch,
)

__all__ = [
    "TrendingAgent",
    "trending_agent",
    "TrendEvidence",
    "TrendNarrative",
    "TrendClaim",
    "Trend",
    "NarrativeCluster",
    "TrendRecord",
    "TrendingExtractionResult",
    "KNOWN_ENTITY_CATALOG",
    "WIRE_SIGNATURES",
    "WIRE_SYNDICATION_DOMAINS",
    "TrendingExtractionEngine",
    "trending_extractor",
    "resolve_entity",
    "fetch_news",
    "fetch_targeted_news",
    "fetch_paparazzi",
    "fetch_box_office",
    "detect_syndication_group",
    "cluster_trends",
    "extract_narratives_from_cluster",
    "extract_claims_from_cluster",
    "calculate_velocity",
    "parse_timestamp_epoch",
    "compute_cluster_sentiment",
    "evaluate_misinformation_risk",
]
