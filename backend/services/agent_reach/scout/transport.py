"""
Aegis Protocol — Scout Transport (Shim)
=======================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.transport`.
"""

from backend.agents.scout.sources.transport import (
    DEFAULT_USER_AGENT,
    DomainRateLimiter,
    ScoutTransport,
    scout_transport,
    validate_url_safe,
)

__all__ = [
    "ScoutTransport",
    "scout_transport",
    "DomainRateLimiter",
    "DEFAULT_USER_AGENT",
    "validate_url_safe",
]
