"""
Aegis Protocol — Agent Reach Capability Layer
==============================================
Unified internet evidence-acquisition layer with channel health tracking,
retrieval planning, and provenance-annotated evidence fragments.
"""

from backend.services.agent_reach.channels import (
    Channel,
    ChannelStatus,
    ChannelTelemetry,
    EvidenceFragment,
    RetrievalResult,
    RetrievalTrace,
)
from backend.services.agent_reach.registry import CapabilityRegistry
from backend.services.agent_reach.adapter import (
    AgentReachService,
    agent_reach_service,
    reach_adapter,
)
from backend.services.agent_reach.planner import RetrievalPlan, RetrievalPlanner

__all__ = [
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
    "RetrievalResult",
    "RetrievalTrace",
]

