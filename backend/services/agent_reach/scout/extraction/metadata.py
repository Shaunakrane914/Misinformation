"""
Aegis Protocol — Scout Structured Metadata Extractor (Shim)
===========================================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.extraction.metadata`.
"""

from backend.agents.scout.sources.extraction.metadata import (
    StructuredMetadataExtractor,
    structured_metadata_extractor,
)

__all__ = [
    "StructuredMetadataExtractor",
    "structured_metadata_extractor",
]
