"""
Aegis Protocol — Scout Domain Agent Package
============================================
Autonomous predictive financial engine, market intelligence acquisition,
and short-attack anomaly detector. Owns domain financial analysis,
evidence extraction, source-level financial event corroboration,
and research workspace reporting.
"""

from backend.agents.scout.agent import (
    ScoutAgent,
    process_scout_task,
    scout_agent,
)
from backend.agents.scout.assessment import (
    correlate_social_rumors,
    synthesize_financial_intelligence,
)
from backend.agents.scout.extraction import (
    ScoutExtractionEngine,
    scout_extractor,
)
from backend.agents.scout.financial import (
    analyze_volatility,
    check_stock_impact,
    extract_prices,
    fetch_stock_data,
    predict_impact,
    resolve_ticker_and_company,
)
from backend.agents.scout.models import (
    CandidateSource,
    ContradictionRecord,
    CorporateEvent,
    CorporateEventType,
    EpistemicStatus,
    FactDirection,
    FinancialContradiction,
    FinancialFact,
    FreshnessRequirement,
    MarketCatalyst,
    MarketSession,
    RawSource,
    ScoutEvidence,
    ScoutExtractionResult,
    ScoutFailureCode,
    ScoutResult,
    ScoutSourceRequest,
    SourceTier,
    StoryCluster,
)
from backend.agents.scout.sources import (
    ScoutSourceEngine,
    scout_source_engine,
)

__all__ = [
    # Agent
    "ScoutAgent",
    "scout_agent",
    "process_scout_task",
    # Domain extraction
    "ScoutExtractionEngine",
    "scout_extractor",
    # Financial analysis
    "resolve_ticker_and_company",
    "fetch_stock_data",
    "extract_prices",
    "analyze_volatility",
    "predict_impact",
    "check_stock_impact",
    # Assessment
    "correlate_social_rumors",
    "synthesize_financial_intelligence",
    # Domain models
    "FinancialFact",
    "CorporateEvent",
    "FinancialContradiction",
    "MarketCatalyst",
    "ScoutExtractionResult",
    # Source engine
    "ScoutSourceEngine",
    "scout_source_engine",
    "ScoutSourceRequest",
    "ScoutResult",
    "ScoutEvidence",
    "CandidateSource",
    "RawSource",
    "ContradictionRecord",
    "StoryCluster",
    "SourceTier",
    "EpistemicStatus",
    "ScoutFailureCode",
    "FactDirection",
    "CorporateEventType",
    "MarketSession",
    "FreshnessRequirement",
]
