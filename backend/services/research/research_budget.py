"""
Aegis Protocol — Adaptive Research Budget & Execution Bounds
============================================================
Defines separate bounded budgets for candidate discovery, follow-up queries,
primary source escalations, deep reading passes, transcripts, and contradiction
resolution to maximize evidence coverage per unit latency.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class ResearchBudget:
    """Configurable adaptive execution budget governing research pipeline bounds (Requirement 12)."""
    discovery_budget: int = 40
    follow_up_budget: int = 4
    primary_escalation_budget: int = 3
    deep_read_budget: int = 8
    transcript_budget: int = 2
    contradiction_resolution_budget: int = 3
    timeout_seconds: float = 15.0
    channel_timeout_seconds: float = 6.0
    deep_read_concurrency: int = 5

    # ── Backward-compatible properties ────────────────────────────────────
    @property
    def max_candidates(self) -> int:
        return self.discovery_budget

    @property
    def max_deep_reads(self) -> int:
        return self.deep_read_budget

    @property
    def max_primary_escalations(self) -> int:
        return self.primary_escalation_budget

    @property
    def max_corroboration_queries(self) -> int:
        return self.contradiction_resolution_budget

    def check_stop_condition(
        self,
        elapsed_seconds: float,
        independent_group_count: int = 0,
        primary_source_count: int = 0,
        contradiction_count: int = 0,
        novel_evidence_added: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate research stop conditions (Requirement 12):
        1. Latency ceiling reached
        2. Sufficient independent corroboration + primary document located
        3. Contradictory evidence resolved & sufficient citations
        4. No novel evidence produced by follow-up queries
        """
        if elapsed_seconds >= self.timeout_seconds:
            return True, "latency_ceiling_reached"

        if independent_group_count >= 3 and primary_source_count >= 1:
            return True, "sufficient_corroboration_and_primary_located"

        if not novel_evidence_added and elapsed_seconds > 4.0:
            return True, "no_novel_evidence_produced"

        return False, None

    @classmethod
    def from_env(cls) -> "ResearchBudget":
        """Factory: Read overrides from environment variables if present."""
        return cls(
            discovery_budget=int(os.getenv("RESEARCH_MAX_CANDIDATES", "40")),
            follow_up_budget=int(os.getenv("RESEARCH_MAX_FOLLOW_UPS", "4")),
            primary_escalation_budget=int(os.getenv("RESEARCH_MAX_PRIMARY_ESCALATIONS", "3")),
            deep_read_budget=int(os.getenv("RESEARCH_MAX_DEEP_READS", "8")),
            transcript_budget=int(os.getenv("RESEARCH_MAX_TRANSCRIPTS", "2")),
            contradiction_resolution_budget=int(os.getenv("RESEARCH_MAX_CORROBORATION_QUERIES", "3")),
            timeout_seconds=float(os.getenv("RESEARCH_MAX_TOTAL_LATENCY_SECONDS", "15.0")),
            channel_timeout_seconds=float(os.getenv("RESEARCH_CHANNEL_TIMEOUT_SECONDS", "6.0")),
            deep_read_concurrency=int(os.getenv("RESEARCH_DEEP_READ_CONCURRENCY", "5")),
        )


default_budget = ResearchBudget.from_env()
