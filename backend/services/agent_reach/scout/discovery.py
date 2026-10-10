"""
Aegis Protocol — Scout Discovery Engine (Shim)
==============================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.discovery`.
"""

from backend.agents.scout.sources.discovery import (
    BingDiscovery,
    DiscoveryStrategy,
    PrimaryFilingDiscovery,
    ScoutDiscoveryEngine,
    SocialDiscovery,
    YahooDiscovery,
    calculate_candidate_score,
    check_entity_semantic_match,
    clean_url,
    extract_reddit_source,
    extract_x_source,
    is_valid_content_source,
    resolve_bing_redirect,
    scout_discovery,
)

__all__ = [
    "ScoutDiscoveryEngine",
    "scout_discovery",
    "DiscoveryStrategy",
    "BingDiscovery",
    "PrimaryFilingDiscovery",
    "SocialDiscovery",
    "YahooDiscovery",
    "calculate_candidate_score",
    "check_entity_semantic_match",
    "clean_url",
    "extract_reddit_source",
    "extract_x_source",
    "is_valid_content_source",
    "resolve_bing_redirect",
]
