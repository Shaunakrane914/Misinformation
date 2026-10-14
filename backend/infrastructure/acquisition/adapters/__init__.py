"""
Aegis Protocol — Acquisition Platform Adapters
================================================
Platform-specific adapters for evidence acquisition across Web, Social, and Knowledge platforms.
"""

def __getattr__(name: str):
    if name == "PlatformAdapter":
        from backend.services.agent_reach.native.adapters.base import PlatformAdapter
        return PlatformAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["PlatformAdapter"]
