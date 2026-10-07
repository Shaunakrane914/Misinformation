"""
Aegis Protocol — Adaptive Research Budget & Execution Bounds
============================================================
Defines separate bounded budgets for candidate discovery, follow-up queries,
primary source escalations, deep reading passes, transcripts, and contradiction
resolution to maximize evidence coverage per unit latency.
Supports environment overrides (LOCAL_RESEARCH_* and SERVER_RESEARCH_*).
"""

import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple


@dataclass
class ResearchBudget:
    """Configurable adaptive execution budget governing research pipeline bounds."""
    discovery_budget: int = 40
    follow_up_budget: int = 3
    primary_escalation_budget: int = 2
    deep_read_budget: int = 6
    transcript_budget: int = 2
    contradiction_resolution_budget: int = 2
    timeout_seconds: float = 20.0
    channel_timeout_seconds: float = 5.0
    deep_read_concurrency: int = 4

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

    # ── Staged Latency Budgets ─────────────────────────────────────────────
    @property
    def discovery_timeout_seconds(self) -> float:
        """Maximum time allowed for initial discovery and adaptive expansion."""
        return round(self.timeout_seconds * 0.45, 2)

    @property
    def deep_read_timeout_seconds(self) -> float:
        """Dedicated time reserved specifically for deep reading."""
        return round(self.timeout_seconds * 0.40, 2)

    @property
    def synthesis_timeout_seconds(self) -> float:
        """Time reserved for finding synthesis, passage extraction, and verdict."""
        return round(self.timeout_seconds * 0.15, 2)

    def check_stop_condition(
        self,
        elapsed_seconds: float,
        independent_group_count: int = 0,
        primary_source_count: int = 0,
        contradiction_count: int = 0,
        novel_evidence_added: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate research stop conditions."""
        if elapsed_seconds >= self.timeout_seconds:
            return True, "latency_ceiling_reached"

        if independent_group_count >= 3 and primary_source_count >= 1:
            return True, "sufficient_corroboration_and_primary_located"

        if not novel_evidence_added and elapsed_seconds > 4.0:
            return True, "no_novel_evidence_produced"

        return False, None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["discovery_timeout_seconds"] = self.discovery_timeout_seconds
        d["deep_read_timeout_seconds"] = self.deep_read_timeout_seconds
        d["synthesis_timeout_seconds"] = self.synthesis_timeout_seconds
        d["max_deep_reads"] = self.max_deep_reads
        d["max_candidates"] = self.max_candidates
        return d

    @classmethod
    def from_env(cls) -> "ResearchBudget":
        """Factory: Read overrides from environment variables if present."""
        is_server = os.getenv("RENDER") or os.getenv("PORT") or os.getenv("SERVER_MODE")
        prefix = "SERVER_RESEARCH_" if is_server else "LOCAL_RESEARCH_"

        disc_b = int(os.getenv(f"{prefix}MAX_QUERIES", os.getenv("RESEARCH_MAX_CANDIDATES", "40")))
        fu_b = int(os.getenv(f"{prefix}MAX_FOLLOW_UPS", os.getenv("RESEARCH_MAX_FOLLOW_UPS", "3")))
        prim_b = int(os.getenv(f"{prefix}MAX_PRIMARY_ESCALATIONS", os.getenv("RESEARCH_MAX_PRIMARY_ESCALATIONS", "2")))
        dr_b = int(os.getenv(f"{prefix}MAX_DEEP_READS", os.getenv("RESEARCH_MAX_DEEP_READS", "6")))
        tout = float(os.getenv(f"{prefix}TIMEOUT", os.getenv("RESEARCH_MAX_TOTAL_LATENCY_SECONDS", "25.0" if not is_server else "20.0")))
        ch_tout = float(os.getenv(f"{prefix}CHANNEL_TIMEOUT", os.getenv("RESEARCH_CHANNEL_TIMEOUT_SECONDS", "5.0")))

        return cls(
            discovery_budget=disc_b,
            follow_up_budget=fu_b,
            primary_escalation_budget=prim_b,
            deep_read_budget=dr_b,
            transcript_budget=int(os.getenv("RESEARCH_MAX_TRANSCRIPTS", "2")),
            contradiction_resolution_budget=int(os.getenv("RESEARCH_MAX_CORROBORATION_QUERIES", "2")),
            timeout_seconds=tout,
            channel_timeout_seconds=ch_tout,
            deep_read_concurrency=int(os.getenv("RESEARCH_DEEP_READ_CONCURRENCY", "4")),
        )


default_budget = ResearchBudget.from_env()
