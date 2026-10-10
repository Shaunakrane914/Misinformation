"""
Aegis Protocol — Scout Source Engine Models (Shim)
==================================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.models`.
"""

from backend.agents.scout.sources.models import (
    CandidateSource,
    ContradictionRecord,
    CorporateEvent,
    CorporateEventType,
    EpistemicStatus,
    FactDirection,
    FinancialFact,
    FreshnessRequirement,
    MarketSession,
    RawSource,
    ScoutEvidence,
    ScoutFailureCode,
    ScoutResult,
    ScoutSourceRequest,
    SourceTier,
    StoryCluster,
)

__all__ = [
    "MarketSession",
    "FreshnessRequirement",
    "SourceTier",
    "FactDirection",
    "CorporateEventType",
    "EpistemicStatus",
    "ScoutFailureCode",
    "ScoutSourceRequest",
    "CandidateSource",
    "RawSource",
    "FinancialFact",
    "CorporateEvent",
    "ContradictionRecord",
    "StoryCluster",
    "ScoutEvidence",
    "ScoutResult",
]
