"""
Aegis Protocol — Scout Source Engine Package
============================================
Proprietary source acquisition, structured extraction, financial entity parsing,
and corroboration engine powering Agent 1: Scout.
"""

from .models import (
    ScoutSourceRequest,
    ScoutResult,
    ScoutEvidence,
    CandidateSource,
    RawSource,
    FinancialFact,
    CorporateEvent,
    StoryCluster,
    ContradictionRecord,
    SourceTier,
    EpistemicStatus,
    ScoutFailureCode,
    FactDirection,
    CorporateEventType,
)
from .engine import scout_source_engine, ScoutSourceEngine
from .transport import scout_transport, ScoutTransport
from .discovery import scout_discovery, ScoutDiscoveryEngine
from .ranking import scout_ranking_engine, ScoutRankingEngine
from .deduplication import scout_deduplicator, ScoutDeduplicator
from .corroboration import scout_corroboration_engine, ScoutCorroborationEngine
from .cache import scout_cache, ScoutCache
from .telemetry import ScoutTelemetry

__all__ = [
    "scout_source_engine",
    "ScoutSourceEngine",
    "ScoutSourceRequest",
    "ScoutResult",
    "ScoutEvidence",
    "CandidateSource",
    "RawSource",
    "FinancialFact",
    "CorporateEvent",
    "StoryCluster",
    "ContradictionRecord",
    "SourceTier",
    "EpistemicStatus",
    "ScoutFailureCode",
    "FactDirection",
    "CorporateEventType",
    "scout_transport",
    "ScoutTransport",
    "scout_discovery",
    "ScoutDiscoveryEngine",
    "scout_ranking_engine",
    "ScoutRankingEngine",
    "scout_deduplicator",
    "ScoutDeduplicator",
    "scout_corroboration_engine",
    "ScoutCorroborationEngine",
    "scout_cache",
    "ScoutCache",
    "ScoutTelemetry",
]
