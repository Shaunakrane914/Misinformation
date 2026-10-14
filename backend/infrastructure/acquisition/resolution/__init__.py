"""
Aegis Protocol — Phase 6.8 Entity-to-Social-Source Resolution Package
"""

from backend.infrastructure.acquisition.resolution.social_resolver import (
    EntitySocialResolutionResult,
    EntitySocialResolver,
    EntitySubredditResolver,
    REDDIT_DATA_API_SUNSET_DATE,
    REDDIT_LEGACY_API_DEADLINE,
    REDDIT_RSS_SUNSET_DATE,
    ResolvedXCandidate,
    SubredditCandidate,
    WikidataXResolver,
    entity_social_resolver,
)

__all__ = [
    "EntitySocialResolutionResult",
    "EntitySocialResolver",
    "EntitySubredditResolver",
    "REDDIT_DATA_API_SUNSET_DATE",
    "REDDIT_LEGACY_API_DEADLINE",
    "REDDIT_RSS_SUNSET_DATE",
    "ResolvedXCandidate",
    "SubredditCandidate",
    "WikidataXResolver",
    "entity_social_resolver",
]
