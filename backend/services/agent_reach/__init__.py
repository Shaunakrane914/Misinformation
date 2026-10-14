"""
Aegis Protocol — Agent Reach Capability Layer
==============================================
Unified internet evidence-acquisition layer with channel health tracking,
retrieval planning, and provenance-annotated evidence fragments.
"""

__version__ = "1.5.0"

from backend.services.agent_reach.channels import (
    AgentAcquisitionBase,
    Channel,
    ChannelStatus,
    ChannelTelemetry,
    EvidenceFragment,
    RetrievalProfile,
    RetrievalResult,
    RetrievalTrace,
)
from backend.services.agent_reach.profile import get_agent_profile
from backend.services.agent_reach.registry import CapabilityRegistry
from backend.services.agent_reach.planner import RetrievalPlan, RetrievalPlanner


def __getattr__(name: str):
    """Lazily expose legacy service names without reversing infrastructure imports."""
    if name in {"AgentReachService", "agent_reach_service", "reach_adapter"}:
        from backend.services.agent_reach.adapter import (
            AgentReachService,
            agent_reach_service,
            reach_adapter,
        )
        return {
            "AgentReachService": AgentReachService,
            "agent_reach_service": agent_reach_service,
            "reach_adapter": reach_adapter,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "AgentAcquisitionBase",
    "AgentReachService",
    "agent_reach_service",
    "reach_adapter",
    "CapabilityRegistry",
    "Channel",
    "ChannelStatus",
    "ChannelTelemetry",
    "EvidenceFragment",
    "RetrievalPlan",
    "RetrievalPlanner",
    "RetrievalProfile",
    "get_agent_profile",
    "RetrievalResult",
    "RetrievalTrace",
]

