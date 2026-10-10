"""
BrandShield Agent 2.0 (Backward Compatibility Shim)
===================================================
Canonical implementation relocated to `backend.agents.brandshield`.
Preserves historical import paths, class identities, and architectural contracts.
"""

from backend.services.agent_reach import agent_reach_service  # Architecture contract preservation
from backend.agents.brandshield import (
    BrandShieldAgent,
    brandshield_agent,
    THREAT_TAXONOMY,
    KNOWN_BRAND_CATALOG,
)

__all__ = [
    "BrandShieldAgent",
    "brandshield_agent",
    "THREAT_TAXONOMY",
    "KNOWN_BRAND_CATALOG",
    "agent_reach_service",
]
