"""
Aegis Protocol — Personal Watch Domain Extraction Engine (Shim)
===============================================================
Backward-compatibility shim. The canonical Personal Watch extraction implementation
now lives in the agent-owned package: `backend.agents.personal_watch.extraction`.
"""

from backend.agents.personal_watch.extraction import (
    PersonalWatchExtractionEngine,
    personal_watch_extractor,
)
from backend.agents.personal_watch.models import (
    CareerEvent,
    PersonalWatchExtractionResult,
    PublicStatement,
    SENSITIVE_PII_KEYWORDS,
)

__all__ = [
    "PersonalWatchExtractionEngine",
    "PersonalWatchExtractionResult",
    "CareerEvent",
    "PublicStatement",
    "SENSITIVE_PII_KEYWORDS",
    "personal_watch_extractor",
]
