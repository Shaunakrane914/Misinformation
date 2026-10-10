"""
Aegis Protocol — Scout Source Ranking Engine (Shim)
===================================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.ranking`.
"""

from backend.agents.scout.sources.ranking import (
    NON_SOCIAL_DOMAINS,
    TWITTER_RESERVED_PATHS,
    ScoutRankingEngine,
    check_entity_semantic_match,
    scout_ranking_engine,
)

__all__ = [
    "ScoutRankingEngine",
    "scout_ranking_engine",
    "NON_SOCIAL_DOMAINS",
    "TWITTER_RESERVED_PATHS",
    "check_entity_semantic_match",
]
