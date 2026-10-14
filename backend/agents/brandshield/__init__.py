"""
Aegis Protocol — BrandShield Domain Agent Package
=================================================
Autonomous brand protection, counterfeit detection, and threat intelligence.
Owns domain entity resolution, threat-specific query planning, domain evidence
extraction, review-pattern screening, threat synthesis, and dossier construction.
"""

from backend.agents.brandshield.agent import BrandShieldAgent, brandshield_agent
from backend.agents.brandshield.assessment import (
    heuristic_threat_synthesis,
    screen_review_patterns,
    synthesize_brand_threats,
)
from backend.agents.brandshield.dossier import build_investigation_dossiers
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
from backend.agents.brandshield.planning import resolve_brand_entity
from backend.agents.brandshield.scanning import search_brand_evidence

__all__ = [
    "BrandShieldAgent",
    "brandshield_agent",
    "BrandShieldExtractionEngine",
    "brandshield_extractor",
    "BrandShieldExtractionResult",
    "BrandThreatRecord",
    "THREAT_TAXONOMY",
    "KNOWN_BRAND_CATALOG",
    "resolve_brand_entity",
    "search_brand_evidence",
    "screen_review_patterns",
    "synthesize_brand_threats",
    "heuristic_threat_synthesis",
    "build_investigation_dossiers",
]
