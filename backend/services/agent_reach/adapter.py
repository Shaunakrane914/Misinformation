"""Legacy import compatibility for the canonical acquisition service.

The implementation is owned by :mod:`backend.infrastructure.acquisition.service`.
Re-exporting the exact class and singleton instances preserves existing callers and
monkeypatch targets while Phase 3.5 callers migrate deliberately.
"""

from backend.infrastructure.acquisition.service import (
    AgentReachService,
    agent_reach_service,
    reach_adapter,
)

__all__ = ["AgentReachService", "agent_reach_service", "reach_adapter"]
