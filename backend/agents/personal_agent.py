"""
Personal Watch Agent 2.0 (Backward Compatibility Shim)
======================================================
Canonical implementation relocated to `backend.agents.personal_watch`.
Preserves historical import paths, class identities, and architectural contracts.
"""

from backend.services.agent_reach import agent_reach_service  # Architecture contract preservation
from backend.agents.personal_watch import (
    PersonalWatchAgent,
    PersonalAgent,
    personal_watch_agent,
    process_personal_watch,
    THREAT_TAXONOMY,
    KNOWN_PUBLIC_PROFILES,
)

__all__ = [
    "PersonalWatchAgent",
    "PersonalAgent",
    "personal_watch_agent",
    "process_personal_watch",
    "THREAT_TAXONOMY",
    "KNOWN_PUBLIC_PROFILES",
    "agent_reach_service",
]
