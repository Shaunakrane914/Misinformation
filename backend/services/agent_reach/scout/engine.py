"""
Aegis Protocol — Scout Source Orchestration Engine (Shim)
=========================================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.engine`.
"""

from backend.services.agent_reach.adapter import agent_reach_service  # Architecture contract preservation
from backend.agents.scout.sources.engine import ScoutSourceEngine, scout_source_engine

__all__ = ["ScoutSourceEngine", "scout_source_engine", "agent_reach_service"]
