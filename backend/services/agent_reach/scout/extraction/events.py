"""
Aegis Protocol — Scout Corporate Event Extractor (Shim)
=======================================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.extraction.events`.
"""

from backend.agents.scout.sources.extraction.events import (
    CorporateEvent,
    CorporateEventExtractor,
    CorporateEventType,
    FactDirection,
    corporate_event_extractor,
)

__all__ = [
    "CorporateEvent",
    "CorporateEventExtractor",
    "CorporateEventType",
    "FactDirection",
    "corporate_event_extractor",
]
