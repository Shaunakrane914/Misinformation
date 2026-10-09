"""
Aegis Protocol — Acquisition Service Contract
==============================================
Authoritative polymorphic evidence acquisition service coordinating
channel capability discovery, multi-query planning, bounded concurrent retrieval,
and SSRF-hardened document reading.
"""

from backend.services.agent_reach.adapter import AgentReachService

# Canonical alias
AcquisitionService = AgentReachService

__all__ = [
    "AcquisitionService",
    "AgentReachService",
]
