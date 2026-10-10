"""
Aegis Protocol — Scout GitHub Adapter (Shim)
============================================
Backward-compatibility shim. Canonical implementation relocated to
`backend.agents.scout.sources.adapters.github_adapter`.
"""

from backend.agents.scout.sources.adapters.github_adapter import (
    GitHubAdapter,
)

__all__ = [
    "GitHubAdapter",
]
