"""
Aegis Protocol — Scout Financial Number Extractor (Shim)
========================================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.extraction.financial`.
"""

from backend.agents.scout.sources.extraction.financial import (
    FactDirection,
    FinancialFact,
    FinancialNumberExtractor,
    financial_number_extractor,
)

__all__ = [
    "FactDirection",
    "FinancialFact",
    "FinancialNumberExtractor",
    "financial_number_extractor",
]
