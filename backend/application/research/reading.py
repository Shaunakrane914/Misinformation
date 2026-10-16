"""Primary-source escalation and bounded deep reading."""

from datetime import datetime
import time
from typing import Any, List

from backend.application.research.contracts import EscalatedEvidence, RankedEvidence, ReadEvidence
from backend.services.agent_reach.channels import QueryExecutionRecord
from backend.services.research.deep_reader import deep_reader
from backend.services.research.primary_source_escalator import primary_source_escalator
from backend.services.research.relevance_gate import relevance_gate
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import ResearchRequest
from backend.services.research.source_quality import source_quality_engine


class PrimaryEscalationStage:
    def run(self, request: ResearchRequest, budget: ResearchBudget, ranked: RankedEvidence,
            start_ts: float, effective_timeout: float) -> EscalatedEvidence:
        # Stage 7: Adaptive Primary Source Escalation (Requirement 16)
        escalation_query_records: List[QueryExecutionRecord] = []
        # Escalation shares discovery's slice; it cannot consume the protected
        # deep-read and synthesis reservation after initial/adaptive discovery.
        escalation_time = min(budget.discovery_timeout_seconds, effective_timeout * 0.45) - (time.time() - start_ts)
        if escalation_time > 0:
            escalated_primaries, esc_telemetry = primary_source_escalator.escalate(
                ranked.ranked,
                target_name=request.target,
                domain=request.domain,
                max_escalations=budget.max_primary_escalations,
                timeout_seconds=escalation_time,
            )
            if escalated_primaries:
                for p in escalated_primaries:
                    source_quality_engine.classify_and_score(p, target_name=request.target)
                esc_acc, esc_rej = relevance_gate.filter_candidates(
                    escalated_primaries,
                    target_entity=request.target,
                    domain=request.domain
                )
                ranked.rejected.extend(esc_rej)
                ranked.ranked = esc_acc + ranked.ranked

            escalation_query_records = esc_telemetry.get("execution_records") or []
            if not escalation_query_records and esc_telemetry.get("queries"):
                for idx, eq_text in enumerate(esc_telemetry.get("queries", [])):
                    q_id = f"q_esc_{idx + 1:03d}"
                    prim_count = sum(1 for p in (escalated_primaries or []) if p.metadata.get("primary_query_id") == q_id or p.metadata.get("escalation_query") == eq_text)
                    escalation_query_records.append(QueryExecutionRecord(
                        query_id=q_id,
                        channel="web",
                        query_text=eq_text,
                        query_class="primary_escalation",
                        phase="escalation",
                        status="SUCCESS" if prim_count > 0 else "NO_RESULTS",
                        started_at=None,
                        completed_at=None,
                        latency_ms=None,
                        result_count_raw=prim_count,
                        result_count_normalized=prim_count,
                        error=None,
                        retrieval_mode="direct",
                        backend_id="web",
                    ))
        else:
            escalated_primaries, esc_telemetry = [], {"queries": [], "escalations": 0}

        return EscalatedEvidence(ranked, escalated_primaries, esc_telemetry, escalation_query_records)


class DeepReadingStage:
    def run(self, request: ResearchRequest, budget: ResearchBudget, ranked: RankedEvidence,
            start_ts: float, effective_timeout: float) -> ReadEvidence:
        # Stage 8: Diversity-Aware Deep Reading (Requirement 13 & 14)
        deep_read_budget = max(0, min(request.deep_read_budget, budget.max_deep_reads))
        # The bounded discovery transport already fetched explicit source URLs.
        # Preserve those bodies without requesting the same URL twice.
        carried = [item for item in ranked.ranked if item.metadata.get("acquired_during_discovery")
                   and item.acquired_id and item.acquisition_attempt_id]
        pending = [item for item in ranked.ranked if item not in carried
                   and item.canonical_url not in {source.canonical_url for source in carried}]
        time_left = max(0.0, effective_timeout * 0.85 - (time.time() - start_ts))
        if deep_read_budget > 0 and pending and time_left > 0:
            investigated_items, read_telemetry = deep_reader.deep_read(
                pending,
                max_reads=deep_read_budget,
                timeout_per_read=min(budget.channel_timeout_seconds, time_left)
            )
        else:
            investigated_items, read_telemetry = [], {
                "attempted": 0,
                "successful": 0,
                "failed": 0,
                "cached": 0,
                "total_chars_read": 0,
                "read_urls": [],
                "candidate_selection_audit": [],
            }

        read_telemetry["reused_acquired_count"] = len(carried)
        return ReadEvidence(carried + investigated_items, read_telemetry)
