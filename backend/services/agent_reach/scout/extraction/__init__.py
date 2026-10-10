"""
Aegis Protocol — Scout Source Extraction (Shim)
===============================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.extraction`.
"""

from backend.agents.scout.sources.extraction import (
    CorporateEventExtractor,
    FinancialNumberExtractor,
    StructuredMetadataExtractor,
    TemporalExtractor,
    corporate_event_extractor,
    financial_number_extractor,
    structured_metadata_extractor,
    temporal_extractor,
)

__all__ = [
    "TemporalExtractor",
    "temporal_extractor",
    "FinancialNumberExtractor",
    "financial_number_extractor",
    "CorporateEventExtractor",
    "corporate_event_extractor",
    "StructuredMetadataExtractor",
    "structured_metadata_extractor",
]
