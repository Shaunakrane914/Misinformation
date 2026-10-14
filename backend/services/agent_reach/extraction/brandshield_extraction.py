"""
Aegis Protocol — BrandShield Domain Extraction Engine (Shim)
============================================================
Backward-compatibility shim. The canonical BrandShield extraction implementation
now lives in the agent-owned package: `backend.agents.brandshield.extraction`.
"""

from backend.agents.brandshield.extraction import (
    BrandShieldExtractionEngine,
    brandshield_extractor,
)
from backend.agents.brandshield.models import (
    KNOWN_BRAND_CATALOG,
    THREAT_TAXONOMY,
    BrandShieldExtractionResult,
    BrandThreatRecord,
)

__all__ = [
    "BrandShieldExtractionEngine",
    "BrandShieldExtractionResult",
    "BrandThreatRecord",
    "THREAT_TAXONOMY",
    "KNOWN_BRAND_CATALOG",
    "brandshield_extractor",
]
