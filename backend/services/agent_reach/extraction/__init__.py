"""
Aegis Protocol — Domain-Specific Extraction Engines
===================================================
Each domain engine consumes normalized EvidenceFragment[] records produced by
the shared acquisition fabric and outputs typed, domain-specific intelligence
with traceability to source evidence IDs.
"""

from backend.services.agent_reach.extraction.brandshield_extraction import (
    BrandShieldExtractionEngine,
    BrandShieldExtractionResult,
    BrandThreatRecord,
    brandshield_extractor,
)
from backend.services.agent_reach.extraction.personal_extraction import (
    CareerEvent,
    PersonalWatchExtractionEngine,
    PersonalWatchExtractionResult,
    PublicStatement,
    personal_watch_extractor,
)
from backend.services.agent_reach.extraction.scout_extraction import (
    CorporateEvent,
    FinancialContradiction,
    FinancialFact,
    ScoutExtractionEngine,
    ScoutExtractionResult,
    scout_extractor,
)
from backend.services.agent_reach.extraction.trending_extraction import (
    NarrativeCluster,
    TrendingExtractionEngine,
    TrendingExtractionResult,
    TrendRecord,
    trending_extractor,
)

__all__ = [
    "BrandShieldExtractionEngine",
    "BrandShieldExtractionResult",
    "BrandThreatRecord",
    "brandshield_extractor",
    "PersonalWatchExtractionEngine",
    "PersonalWatchExtractionResult",
    "CareerEvent",
    "PublicStatement",
    "personal_watch_extractor",
    "ScoutExtractionEngine",
    "ScoutExtractionResult",
    "FinancialFact",
    "CorporateEvent",
    "FinancialContradiction",
    "scout_extractor",
    "TrendingExtractionEngine",
    "TrendingExtractionResult",
    "TrendRecord",
    "NarrativeCluster",
    "trending_extractor",
]
