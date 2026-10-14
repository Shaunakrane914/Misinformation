"""
Aegis Protocol — Scout Telemetry (Shim)
=======================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.telemetry`.
"""

from backend.agents.scout.sources.telemetry import (
    ScoutTelemetry,
)

__all__ = [
    "ScoutTelemetry",
]
