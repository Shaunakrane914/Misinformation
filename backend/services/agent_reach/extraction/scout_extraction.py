"""
Aegis Protocol — Scout Domain Extraction Engine (Shim)
======================================================
Backward-compatibility shim. The canonical Scout extraction implementation
now lives in the agent-owned package: `backend.agents.scout.extraction`.
"""

from backend.agents.scout.extraction import (
    ScoutExtractionEngine,
    scout_extractor,
)
from backend.agents.scout.models import (
    CorporateEvent,
    FinancialContradiction,
    FinancialFact,
    MarketCatalyst,
    ScoutExtractionResult,
)

__all__ = [
    "ScoutExtractionEngine",
    "ScoutExtractionResult",
    "FinancialFact",
    "CorporateEvent",
    "FinancialContradiction",
    "MarketCatalyst",
    "scout_extractor",
]
