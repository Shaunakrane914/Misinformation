"""
Aegis Protocol — Research Budget & Execution Limits
===================================================
Defines strict bounded limits for candidate discovery, deep reading passes,
primary source escalations, and global research timeouts to ensure predictable performance.
"""

import os
from dataclasses import dataclass


@dataclass
class ResearchBudget:
    """Configurable execution budget governing research pipeline bounds."""
    max_candidates: int = 40
    max_deep_reads: int = 8
    max_primary_escalations: int = 3
    max_corroboration_queries: int = 3
    timeout_seconds: float = 15.0
    channel_timeout_seconds: float = 6.0
    deep_read_concurrency: int = 5

    @classmethod
    def from_env(cls) -> "ResearchBudget":
        """Factory: Read overrides from environment variables if present."""
        return cls(
            max_candidates=int(os.getenv("RESEARCH_MAX_CANDIDATES", "40")),
            max_deep_reads=int(os.getenv("RESEARCH_MAX_DEEP_READS", "8")),
            max_primary_escalations=int(os.getenv("RESEARCH_MAX_PRIMARY_ESCALATIONS", "3")),
            max_corroboration_queries=int(os.getenv("RESEARCH_MAX_CORROBORATION_QUERIES", "3")),
            timeout_seconds=float(os.getenv("RESEARCH_MAX_TOTAL_LATENCY_SECONDS", "15.0")),
            channel_timeout_seconds=float(os.getenv("RESEARCH_CHANNEL_TIMEOUT_SECONDS", "6.0")),
            deep_read_concurrency=int(os.getenv("RESEARCH_DEEP_READ_CONCURRENCY", "5")),
        )


default_budget = ResearchBudget.from_env()
