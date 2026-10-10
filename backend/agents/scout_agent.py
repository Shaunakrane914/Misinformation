"""
Scout Agent: Predictive Financial Engine (Backward Compatibility Shim)
======================================================================
Canonical implementation relocated to `backend.agents.scout`.
Preserves historical import paths, class identities, and architectural contracts.
"""

from backend.services.agent_reach import agent_reach_service  # Architecture contract preservation
from backend.agents.scout import (
    ScoutAgent,
    process_scout_task,
    scout_agent,
)

__all__ = [
    "ScoutAgent",
    "scout_agent",
    "process_scout_task",
    "agent_reach_service",
]
