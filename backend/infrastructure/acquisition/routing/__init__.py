"""
Aegis Protocol — Acquisition Routing Module
============================================
Orchestrator for capability-aware channel queries, document reads, and Policy D retrieval.
"""

from backend.infrastructure.acquisition.routing.router import (
    NativeRouter,
    native_router,
)

__all__ = [
    "NativeRouter",
    "native_router",
]
