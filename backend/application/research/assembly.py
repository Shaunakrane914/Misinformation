"""Research corpus assembly, telemetry, and immutable dossier registration."""

from typing import Any, Dict, List
import logging
import time

from backend.application.research.contracts import (
    AdaptiveEvidence, Analysis, AssembledResearch, Discovery, EscalatedEvidence,
    QueryPlan, RankedEvidence, ReadEvidence,
)
from backend.services.agent_reach.channels import QueryExecutionRecord
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import (
    ContentDepth, EvidenceItem, ResearchCorpus, ResearchRequest, ResearchResult, SourceRole,
)

logger = logging.getLogger(__name__)


class CorpusAssemblyStage:
    def run(self, request: ResearchRequest, budget: ResearchBudget, plan: QueryPlan,
            discovery: Discovery, ranked: RankedEvidence, adaptive: AdaptiveEvidence,
            escalated: EscalatedEvidence, read: ReadEvidence, analysis: Analysis,
            start_ts: float) -> AssembledResearch:
        multi_queries = plan.channel_queries
        query_classes = plan.query_classes
        retrieval_res = discovery.retrieval
        channel_status = retrieval_res.channel_health
        trace_dict = retrieval_res.retrieval_trace or {}
        raw_candidates = discovery.raw_candidates
        accepted_candidates = ranked.accepted
        ranked_candidates = ranked.ranked
        clusters_map = ranked.clusters
        all_rejected_audit = ranked.rejected
        novelty_tracker = adaptive.novelty
        follow_up_telemetry = adaptive.telemetry
        adaptive_query_records = adaptive.query_records
        escalation_query_records = escalated.query_records
        esc_telemetry = escalated.telemetry
        investigated_items = read.investigated
        read_telemetry = read.telemetry
        contradictions = analysis.contradictions
        findings = analysis.findings
        integrity_report = analysis.integrity_report
        graph = analysis.graph
        lineage_graph = analysis.lineage_graph

        # Compile specialized source subsets (Requirement 19)
        primary_sources = [
            it for it in ranked_candidates
            if it.primary_source or it.source_role == SourceRole.PRIMARY.value
        ]
        social_sources = [
            it for it in ranked_candidates
            if it.channel in ("twitter", "reddit", "instagram", "facebook", "xiaohongshu")
            or it.content_depth == ContentDepth.SOCIAL_POST.value
        ]
        video_sources = [
            it for it in ranked_candidates
            if it.channel in ("youtube", "bilibili")
            or it.content_depth in (ContentDepth.VIDEO_METADATA.value, ContentDepth.VIDEO_TRANSCRIPT.value)
        ]
        transcript_sources = [
            it for it in ranked_candidates
            if it.content_depth == ContentDepth.VIDEO_TRANSCRIPT.value or "transcript" in it.metadata
        ]

        # Stage 13: Full Research Corpus Assembly (Requirement 19)
        initial_records = getattr(retrieval_res, "query_records", []) or []
        if not initial_records:
            for ch, q_list in multi_queries.items():
                for q in q_list:
                    initial_records.append(QueryExecutionRecord(
                        query_id=q.get("query_id", ""),
                        channel=ch,
                        query_text=q.get("query_text", ""),
                        query_class=q.get("query_class", "general"),
                        phase="initial",
                        status="UNRECORDED",
                        started_at=None,
                        completed_at=None,
                        latency_ms=None,
                        result_count_raw=0,
                        result_count_normalized=0,
                        error="Execution record not captured by upstream retrieval layer",
                        retrieval_mode="direct",
                        backend_id=ch,
                    ))

        all_query_records: List[QueryExecutionRecord] = list(initial_records) + adaptive_query_records + escalation_query_records

        queries_planned = len(all_query_records)
        queries_skipped = sum(1 for q in all_query_records if q.status == "SKIPPED")
        queries_submitted = queries_planned - queries_skipped
        queries_started = queries_submitted
        queries_succeeded = sum(1 for q in all_query_records if q.status == "SUCCESS")
        queries_failed = sum(1 for q in all_query_records if q.status == "FAILED")
        queries_timed_out = sum(1 for q in all_query_records if q.status == "TIMEOUT")
        queries_auth_required = sum(1 for q in all_query_records if q.status == "AUTH_REQUIRED")
        queries_executed = queries_succeeded + queries_failed + queries_timed_out + queries_auth_required

        all_executed_queries: List[Dict[str, Any]] = [
            q.to_dict() if hasattr(q, "to_dict") else q for q in all_query_records
        ]

        sat_summary = novelty_tracker.get_summary()
        halt_reason = (
            follow_up_telemetry.get("halt_reason") or
            ("SATURATION_THRESHOLD_REACHED" if sat_summary.get("is_saturated") else "BUDGET_CEILING")
        )

        funnel = {
            "queries_planned": queries_planned,
            "queries_submitted": queries_submitted,
            "queries_started": queries_started,
            "queries_succeeded": queries_succeeded,
            "queries_failed": queries_failed,
            "queries_timed_out": queries_timed_out,
            "queries_auth_required": queries_auth_required,
            "queries_skipped": queries_skipped,
            "queries_executed": queries_executed,
            "candidates_found": len(raw_candidates),
            "candidates_accepted": len(accepted_candidates),
            "candidates_rejected": len(all_rejected_audit),
            "unique_candidates": len(ranked_candidates),
            "deep_reads_count": read_telemetry.get("successful", read_telemetry.get("reads_succeeded", 0)),
            "primary_sources_count": len(primary_sources),
            "independent_groups_count": len(clusters_map),
            "contradictions_count": len(contradictions),
            "findings_count": len(findings),
            "saturation_score": sat_summary.get("cumulative_saturation", 0.0),
            "halt_reason": halt_reason,
            "adaptive_rounds": follow_up_telemetry.get("rounds_executed", 0),
        }

        selection_audit = read_telemetry.get("candidate_selection_audit", [])

        corpus = ResearchCorpus(
            funnel=funnel,
            queries=all_executed_queries,
            raw_candidates=[c.to_dict() for c in raw_candidates],
            ranked_candidates=[r.to_dict() for r in ranked_candidates],
            deep_read_sources=[i.to_dict() for i in investigated_items],
            candidate_selection_audit=selection_audit,
            primary_sources=[p.to_dict() for p in primary_sources],
            social_sources=[s.to_dict() for s in social_sources],
            video_sources=[v.to_dict() for v in video_sources],
            transcript_sources=[t.to_dict() for t in transcript_sources],
            contradictions=contradictions,
            corroboration_groups=[{"group_id": gid, "item_ids": ids} for gid, ids in clusters_map.items()],
            findings=[f.to_dict() for f in findings],
            evidence_graph=graph,
            source_lineage_graph=lineage_graph,
            channel_telemetry=channel_status,
        )

        total_latency_ms = int((time.time() - start_ts) * 1000)

        # Compile research telemetry
        telemetry = {
            **trace_dict,
            "scan_id": trace_dict.get("scan_id", f"res_{int(time.time())}"),
            "funnel": funnel,
            "queries_planned": queries_planned,
            "queries_submitted": queries_submitted,
            "queries_started": queries_started,
            "queries_succeeded": queries_succeeded,
            "queries_failed": queries_failed,
            "queries_timed_out": queries_timed_out,
            "queries_auth_required": queries_auth_required,
            "queries_skipped": queries_skipped,
            "queries_executed": queries_executed,
            "query_records": all_executed_queries,
            "query_classes_count": len(query_classes),
            "follow_ups_executed": follow_up_telemetry["attempted"],
            "candidates_found": len(raw_candidates),
            "candidates_accepted": len(accepted_candidates),
            "candidates_rejected": len(all_rejected_audit),
            "candidates_ranked": len(ranked_candidates),
            "deep_read_attempted": read_telemetry["attempted"],
            "deep_read_success": read_telemetry["successful"],
            "candidate_selection_audit": selection_audit,
            "acquisition_attempts": read_telemetry.get("acquisition_attempts", []),
            "total_chars_read": read_telemetry["total_chars_read"],
            "primary_sources_found": len(primary_sources),
            "escalations": esc_telemetry,
            "independent_source_groups": len(clusters_map),
            "contradictions_found": len(contradictions),
            "findings_count": len(findings),
            "integrity_report": integrity_report.to_dict(),
            "saturation": sat_summary,
            "source_lineage": lineage_graph.get("metrics", {}),
            "total_latency_ms": total_latency_ms,
            "source_plan": (
                plan.source_plan.to_dict()
                if getattr(plan.source_plan, "to_dict", None)
                else plan.source_plan
            ),
        }

        # Build human-readable executive summary
        summary = (
            f"Forensic investigation for '{request.target}' across {len(multi_queries)} channels yielded "
            f"{len(ranked_candidates)} deduplicated candidates, with {read_telemetry['successful']} deep-read "
            f"primary/investigative documents across {len(clusters_map)} independent source groups. "
            f"Identified {len(findings)} substantive evidence-backed findings, {len(contradictions)} conflicting signal(s), "
            f"and isolated {lineage_graph.get('metrics', {}).get('origin_count', 0)} verified origin sources from "
            f"{lineage_graph.get('metrics', {}).get('echo_count', 0)} syndicated echoes."
        )

        return AssembledResearch(corpus, telemetry, summary, primary_sources, total_latency_ms)


class DossierRegistrationStage:
    def run(self, request: ResearchRequest, ranked: RankedEvidence,
            analysis: Analysis, assembled: AssembledResearch) -> None:
        ranked_candidates = ranked.ranked
        findings = analysis.findings
        telemetry = assembled.telemetry
        summary = assembled.summary
        lineage_graph = analysis.lineage_graph
        all_executed_queries = assembled.corpus.queries
        total_latency_ms = assembled.total_latency_ms
        primary_sources = assembled.primary_sources
        # Stage 14: Immutable Research Dossier Registration
        try:
            from backend.services.research.replay_ledger import replay_ledger
            dossier_id = replay_ledger.record_investigation(
                target=request.target,
                domain=request.domain,
                summary=summary,
                candidates=ranked_candidates,
                findings=findings,
                queries=all_executed_queries,
                telemetry=telemetry,
                lineage_graph=lineage_graph,
            )
            telemetry["dossier_id"] = dossier_id
        except Exception as e_dos:
            logger.debug(f"[ResearchEngine] Dossier recording notice: {e_dos}")
            telemetry["dossier_id"] = None

        logger.info(f"[ResearchEngine] Investigation finished in {total_latency_ms}ms (dossier={telemetry.get('dossier_id')}): {len(findings)} findings, {len(primary_sources)} primaries")



class ResultPublicationStage:
    def run(self, request: ResearchRequest, budget: ResearchBudget, discovery: Discovery,
            ranked: RankedEvidence, read: ReadEvidence, analysis: Analysis,
            assembled: AssembledResearch) -> ResearchResult:
        raw_candidates = discovery.raw_candidates
        investigated_items = read.investigated
        findings = analysis.findings
        contradictions = analysis.contradictions
        graph = analysis.graph
        lineage_graph = analysis.lineage_graph
        primary_sources = assembled.primary_sources
        telemetry = assembled.telemetry
        channel_status = discovery.retrieval.channel_health
        trace_dict = discovery.retrieval.retrieval_trace or {}
        corpus = assembled.corpus
        all_rejected_audit = ranked.rejected
        integrity_report = analysis.integrity_report
        summary = assembled.summary
        return ResearchResult(
            agent=request.agent_name,
            target=request.target,
            domain=request.domain,
            summary=summary,
            candidates=raw_candidates,
            investigated_sources=investigated_items,
            evidence=investigated_items,
            findings=findings,
            contradictions=contradictions,
            source_graph=graph,
            source_lineage_graph=lineage_graph,
            primary_sources=primary_sources,
            telemetry=telemetry,
            channel_status=channel_status,
            retrieval_trace=trace_dict,
            research_corpus=corpus.to_dict(),
            accepted_evidence=investigated_items,
            rejected_evidence=all_rejected_audit,
            integrity_report=integrity_report.to_dict(),
            budget_telemetry=budget.to_dict(),
        )


# Canonical 10-stage architectural alias
LedgerPersistenceStage = DossierRegistrationStage

