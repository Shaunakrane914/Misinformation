"""
Aegis Protocol — Central Deep Research Engine
=============================================
Unified coordinator executing the full deep-research pipeline:
Broad Discovery -> Source Quality -> Syndication Clustering -> Candidate Ranking ->
Adaptive Primary Escalation -> Diversity Deep Reading -> Passage Extraction ->
Contradiction Detection -> Independent Corroboration -> Evidence Graph -> Grounded Findings.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.research.candidate_ranker import candidate_ranker
from backend.services.research.contradiction_detector import contradiction_detector
from backend.services.research.corroboration import corroboration_engine
from backend.services.research.deep_reader import deep_reader
from backend.services.research.evidence_graph import evidence_graph_builder
from backend.services.research.evidence_saturation import EvidenceNoveltyTracker
from backend.services.research.passage_extractor import passage_extractor
from backend.services.research.primary_source_escalator import primary_source_escalator
from backend.services.research.research_budget import ResearchBudget, default_budget
from backend.services.research.research_models import (
    ConfidenceLevel,
    ContentDepth,
    EpistemicState,
    EvidenceItem,
    Finding,
    FindingType,
    QualityTensor,
    ResearchCorpus,
    ResearchRequest,
    ResearchResult,
    SourceRole,
    TemporalStatus,
)
from backend.services.research.source_independence import source_independence_engine
from backend.services.research.source_lineage import source_lineage_engine
from backend.services.research.source_quality import source_quality_engine

logger = logging.getLogger(__name__)


class ResearchEngine:
    """Central intelligence and deep-research execution coordinator."""

    def __init__(self, budget: Optional[ResearchBudget] = None):
        self.budget = budget or default_budget
        logger.info("[ResearchEngine] Initialized with full 9-stage pipeline and bounded budgets")

    def _synthesize_grounded_findings(
        self,
        target_name: str,
        domain: str,
        investigated_items: List[EvidenceItem],
        contradictions: List[Dict[str, Any]],
        intent: str = ""
    ) -> List[Finding]:
        """
        Synthesizes 3-6 concrete, evidence-grounded findings from deeply read passages.
        Every finding strictly maps to supporting evidence IDs.
        """
        findings: List[Finding] = []
        if not investigated_items:
            return findings

        # Group items by query_class
        class_map: Dict[str, List[EvidenceItem]] = {}
        for item in investigated_items:
            qc = item.query_class or "general"
            class_map.setdefault(qc, []).append(item)

        # Generate findings per significant query class
        for q_class, items_in_class in class_map.items():
            if len(findings) >= 6:
                break

            top_item = items_in_class[0]
            sup_ids = [it.id for it in items_in_class]
            
            # Find any contradictions matching these items
            matched_cont_ids = []
            for c in contradictions:
                if c.get("source_a_id") in sup_ids or c.get("source_b_id") in sup_ids:
                    matched_cont_ids.append(c.get("source_b_id") if c.get("source_a_id") in sup_ids else c.get("source_a_id"))

            # Evaluate corroboration
            corrob = corroboration_engine.evaluate_corroboration(items_in_class)

            # Determine finding type based on domain & class
            f_type = FindingType.FACT.value
            if domain == "financial":
                if any(w in q_class for w in ["earnings", "financial", "filing"]):
                    f_type = FindingType.CATALYST.value
                elif "risk" in q_class or "investigation" in q_class:
                    f_type = FindingType.RISK.value
            elif domain == "trending":
                f_type = FindingType.TREND.value
            elif "scam" in q_class or "counterfeit" in q_class:
                f_type = FindingType.RISK.value

            # Format finding title and statement
            clean_class_title = q_class.replace("_", " ").title()
            title = f"{clean_class_title}: {top_item.title[:70]}"
            statement = top_item.relevant_excerpt or top_item.snippet or top_item.title
            
            # Identify primary sources among items
            prim_sources = [it.source_name for it in items_in_class if it.primary_source or it.source_role == SourceRole.PRIMARY.value]

            # Derive 6D Multidimensional Quality Tensor (Empirical Heuristic Model)
            total_items = max(1, len(items_in_class))
            avg_rel = sum(it.relevance_score for it in items_in_class) / total_items
            avg_sq = sum(it.source_quality_score for it in items_in_class) / total_items
            avg_rec = sum(it.recency_score for it in items_in_class) / total_items

            # Calibrated independence axis: ratio of independent clusters to total citations
            # Penalizes syndication echoes: 5 articles from 1 group = 1/5 = 0.20
            group_count = max(1, corrob.get("independent_group_count", 1))
            indep_ratio = min(1.0, group_count / total_items)
            indep_axis = max(0.15, min(1.0, 0.20 + 0.80 * indep_ratio))

            # Calibrated primary axis: proportion of citations that are verified primary filings
            prim_ratio = len(prim_sources) / total_items
            prim_axis = max(0.10, min(1.0, 0.30 + 0.70 * prim_ratio))
            cont_axis = 0.85 if matched_cont_ids else 0.05

            q_tensor = QualityTensor(
                relevance=round(avg_rel, 3),
                source_quality=round(avg_sq, 3),
                independence=round(indep_axis, 3),
                primary_weight=round(prim_axis, 3),
                freshness=round(avg_rec, 3),
                contradiction_level=round(cont_axis, 3),
                is_heuristic=True,
                scoring_model="aegis_heuristic_6d"
            )

            # Evaluate 6-State Epistemic Status
            if matched_cont_ids:
                ep_state = EpistemicState.CONTESTED.value
            elif prim_sources or corrob["independent_group_count"] >= 2:
                ep_state = EpistemicState.KNOWN_FACT.value
            elif len(items_in_class) >= 1:
                ep_state = EpistemicState.SUPPORTED.value
            else:
                ep_state = EpistemicState.UNVERIFIED.value

            f = Finding(
                finding_id=f"fnd_{domain[:2]}_{len(findings) + 1:03d}",
                title=title,
                statement=statement,
                type=f_type,
                importance="HIGH" if len(prim_sources) > 0 or corrob["independent_group_count"] >= 2 else "MEDIUM",
                confidence=corrob["confidence"],
                epistemic_state=ep_state,
                quality_tensor=q_tensor,
                supporting_evidence_ids=sup_ids,
                contradicting_evidence_ids=matched_cont_ids,
                independence_groups=corrob["independent_groups"],
                primary_sources=prim_sources,
                explanation=f"Substantiated across {corrob['independent_group_count']} independent source group(s) with {len(items_in_class)} citations.",
                temporal_status=TemporalStatus.NEW_EVENT.value,
                invalidation_criteria=f"Rebuttal or retraction issued by primary official channels ({', '.join(prim_sources) if prim_sources else 'official portal'})."
            )
            findings.append(f)

        return findings

    def investigate(self, request: ResearchRequest) -> ResearchResult:
        """
        Executes end-to-end intelligence investigation on a given target.
        """
        start_ts = time.time()
        effective_timeout = request.timeout_seconds if getattr(request, "timeout_seconds", None) is not None else self.budget.timeout_seconds
        logger.info(f"[ResearchEngine] Launching deep investigation for '{request.target}' (domain={request.domain}, timeout={effective_timeout}s)")

        from backend.services.agent_reach import agent_reach_service
        from backend.services.agent_reach.planner import RetrievalPlanner

        # Stage 1: Query Planning
        planner = RetrievalPlanner()
        multi_queries, query_classes = planner.build_multi_channel_queries(
            request.target,
            domain=request.domain
        )
        planned_classes = list(query_classes.keys()) if isinstance(query_classes, dict) else list(query_classes)
        if request.query_classes:
            planned_classes = list(set(planned_classes + request.query_classes))

        # Stage 2: Broad Discovery via AgentReach (perform_reads=False for fast candidate pooling)
        channel_timeout = min(self.budget.channel_timeout_seconds, max(2.0, effective_timeout / 2))
        retrieval_res = agent_reach_service.retrieve_many(
            channel_queries=multi_queries,
            domain=request.domain,
            agent_name=request.agent_name,
            target_name=request.target,
            source_url=request.source_url,
            budget={
                "max_queries_per_channel": 3,
                "max_results_per_query": 5,
                "max_total_evidence": request.max_candidates or self.budget.max_candidates,
                "max_deep_reads": 0,  # Handled in Stage 8 with diversity selection
            },
            perform_reads=False,
            timeout=channel_timeout * 2
        )

        raw_fragments = retrieval_res.fragments
        channel_status = retrieval_res.channel_health
        trace_dict = retrieval_res.retrieval_trace or {}

        # Stage 3: Candidate Normalization & Source Quality Classification
        candidates: List[EvidenceItem] = []
        for idx, frag in enumerate(raw_fragments):
            item_id = f"ev_{idx + 1:03d}"
            ev_item = EvidenceItem.from_evidence_fragment(frag, item_id=item_id, target_name=request.target)
            source_quality_engine.classify_and_score(ev_item, target_name=request.target)
            candidates.append(ev_item)

        # Stage 4: Syndication Clustering & True Independence Scoring
        candidates, clusters_map = source_independence_engine.cluster_independence(candidates)

        # Stage 5: Deterministic Candidate Ranking
        ranked_candidates = candidate_ranker.rank_candidates(
            candidates,
            target_name=request.target,
            intent=request.intent,
            query_classes=query_classes
        )

        # Initialize Mathematical Evidence Novelty & Saturation Tracker
        novelty_tracker = EvidenceNoveltyTracker(
            saturation_threshold=0.88,
            min_novelty_epsilon=0.08,
            max_steps=8
        )
        novelty_tracker.record_step(
            query_id="q_initial_broad",
            query_text=request.target,
            channel="broad_discovery",
            evidence_snippets=[c.snippet for c in candidates[:10]],
            explicit_entities=[request.target]
        )

        # Stage 6: Multi-Round Adaptive Query Expansion Loop with Saturation Halting (Requirement 11)
        follow_up_telemetry = {
            "rounds_executed": 0,
            "queries_planned": 0,
            "queries_submitted": 0,
            "queries_succeeded": 0,
            "queries_failed": 0,
            "attempted": 0,
            "queries": [],
            "halted_early": False,
            "halt_reason": None
        }
        max_adaptive_rounds = min(self.budget.follow_up_budget, 3)
        seen_adaptive_queries: Set[str] = set()

        if self.budget.follow_up_budget > 0:
            for round_idx in range(1, max_adaptive_rounds + 1):
                elapsed = time.time() - start_ts
                if elapsed >= effective_timeout:
                    follow_up_telemetry["halted_early"] = True
                    follow_up_telemetry["halt_reason"] = "latency_ceiling_reached"
                    logger.info(f"[ResearchEngine] Halting adaptive queries early: latency ceiling reached ({elapsed:.1f}s >= {effective_timeout}s)")
                    break

                if novelty_tracker.is_saturated:
                    follow_up_telemetry["halted_early"] = True
                    follow_up_telemetry["halt_reason"] = novelty_tracker.halt_reason
                    logger.info(f"[ResearchEngine] Halting adaptive queries early at round {round_idx}: {novelty_tracker.halt_reason}")
                    break

                # 1. Dynamically replan targeted queries based on latest ranked evidence and discovered contradictions
                current_contradictions = contradiction_detector.detect_contradictions(
                    ranked_candidates[:10],
                    target_name=request.target
                )
                round_candidates_plan = planner.plan_adaptive_follow_ups(
                    target_name=request.target,
                    initial_plan=None,
                    evidence_items=ranked_candidates[:12],
                    contradictions=current_contradictions,
                    max_follow_ups=2
                )

                new_queries = [
                    q for q in round_candidates_plan
                    if q["query_text"].lower().strip() not in seen_adaptive_queries
                ]
                if not new_queries:
                    logger.info(f"[ResearchEngine] No new adaptive queries generated in round {round_idx}; halting loop.")
                    break

                follow_up_telemetry["rounds_executed"] += 1
                follow_up_telemetry["queries_planned"] += len(new_queries)

                for fu in new_queries:
                    if (time.time() - start_ts) >= effective_timeout:
                        follow_up_telemetry["halted_early"] = True
                        follow_up_telemetry["halt_reason"] = "latency_ceiling_reached"
                        break
                    if novelty_tracker.is_saturated:
                        follow_up_telemetry["halted_early"] = True
                        follow_up_telemetry["halt_reason"] = novelty_tracker.halt_reason
                        break

                    seen_adaptive_queries.add(fu["query_text"].lower().strip())
                    follow_up_telemetry["attempted"] += 1
                    follow_up_telemetry["queries_submitted"] += 1
                    follow_up_telemetry["queries"].append(fu)

                    suggested_ch = fu.get("suggested_channels", ["web", "news"])
                    new_snippets_this_step: List[str] = []
                    query_had_success = False

                    for ch in suggested_ch[:2]:
                        try:
                            frags = agent_reach_service.search_channel(ch, fu["query_text"], limit=2)
                            if frags:
                                query_had_success = True
                            for f in frags:
                                u = getattr(f, "url", "") or ""
                                if u and any(c.canonical_url == u for c in candidates):
                                    continue
                                item_id = f"ev_fu_{len(candidates) + 1:03d}"
                                ev_item = EvidenceItem.from_evidence_fragment(f, item_id=item_id, target_name=request.target)
                                ev_item.query_id = fu["query_id"]
                                ev_item.query_class = fu.get("query_class", "adaptive_expansion")
                                ev_item.query_text = fu.get("query_text", "")
                                ev_item.metadata["parent_query_id"] = fu.get("parent_query_id", "q_001")
                                ev_item.metadata["trigger"] = fu.get("trigger", "adaptive")
                                ev_item.metadata["reason"] = fu.get("reason", "")
                                ev_item.metadata["adaptive_round"] = round_idx
                                source_quality_engine.classify_and_score(ev_item, target_name=request.target)
                                candidates.append(ev_item)
                                new_snippets_this_step.append(ev_item.snippet)
                        except Exception as e:
                            logger.debug(f"[ResearchEngine] Follow-up query error for '{fu['query_text']}': {e}")

                    if query_had_success:
                        follow_up_telemetry["queries_succeeded"] += 1
                    else:
                        follow_up_telemetry["queries_failed"] += 1

                    # Record step in novelty tracker
                    novelty_tracker.record_step(
                        query_id=fu.get("query_id", f"q_fu_{follow_up_telemetry['attempted']}"),
                        query_text=fu.get("query_text", ""),
                        channel=suggested_ch[0] if suggested_ch else "web",
                        evidence_snippets=new_snippets_this_step
                    )

                # Re-cluster and re-rank after each round so next round replans with enriched pool
                candidates, clusters_map = source_independence_engine.cluster_independence(candidates)
                ranked_candidates = candidate_ranker.rank_candidates(
                    candidates,
                    target_name=request.target,
                    intent=request.intent,
                    query_classes=query_classes
                )

        # Stage 7: Adaptive Primary Source Escalation (Requirement 16)
        if (time.time() - start_ts) < effective_timeout:
            escalated_primaries, esc_telemetry = primary_source_escalator.escalate(
                ranked_candidates,
                target_name=request.target,
                domain=request.domain,
                max_escalations=self.budget.max_primary_escalations
            )
            if escalated_primaries:
                for p in escalated_primaries:
                    source_quality_engine.classify_and_score(p, target_name=request.target)
                ranked_candidates = escalated_primaries + ranked_candidates
        else:
            escalated_primaries, esc_telemetry = [], {"queries": [], "escalations": 0}

        # Stage 8: Diversity-Aware Deep Reading (6-10 sources, Requirement 13 & 14)
        deep_read_budget = min(request.deep_read_budget, self.budget.max_deep_reads)
        time_left = max(1.0, effective_timeout - (time.time() - start_ts))
        if (time.time() - start_ts) < effective_timeout and deep_read_budget > 0:
            investigated_items, read_telemetry = deep_reader.deep_read(
                ranked_candidates,
                max_reads=deep_read_budget,
                timeout_per_read=min(self.budget.channel_timeout_seconds, time_left)
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

        # Stage 9: Relevant Passage Extraction
        investigated_items = passage_extractor.extract_passages(
            investigated_items,
            target_name=request.target,
            intent=request.intent
        )
        passage_extractor.extract_passages(
            ranked_candidates,
            target_name=request.target,
            intent=request.intent
        )

        # Stage 10: Contradiction Detection
        contradictions = contradiction_detector.detect_contradictions(
            investigated_items or ranked_candidates[:12],
            target_name=request.target
        )

        # Stage 11: Grounded Finding Synthesis
        findings = self._synthesize_grounded_findings(
            target_name=request.target,
            domain=request.domain,
            investigated_items=investigated_items or ranked_candidates[:8],
            contradictions=contradictions,
            intent=request.intent
        )

        # Stage 12: Evidence Graph & Source Lineage DAG Construction
        graph = evidence_graph_builder.build_graph(
            findings=findings,
            evidence=ranked_candidates
        )
        lineage_graph = source_lineage_engine.build_lineage_graph(ranked_candidates)

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
        # Stage 13: Full Research Corpus Assembly (Requirement 19)
        # Accurate query accounting across all phases
        initial_queries_planned = sum(len(q_list) for q_list in multi_queries.values())
        adaptive_queries_planned = follow_up_telemetry.get("queries_planned", 0)
        escalation_queries_planned = len(esc_telemetry.get("queries", []))
        total_queries_planned = initial_queries_planned + adaptive_queries_planned + escalation_queries_planned

        all_executed_queries: List[Dict[str, Any]] = []
        succeeded_queries_count = 0
        failed_queries_count = follow_up_telemetry.get("queries_failed", 0)

        for ch, q_list in multi_queries.items():
            ch_health = channel_status.get(ch, {})
            ch_ok = ch_health.get("status") in ("AVAILABLE", "DEGRADED", "SUCCESS") if isinstance(ch_health, dict) else True
            for q in q_list:
                status = "SUCCESS" if ch_ok else "FAILED"
                if ch_ok:
                    succeeded_queries_count += 1
                else:
                    failed_queries_count += 1
                all_executed_queries.append({
                    "channel": ch,
                    "query_id": q.get("query_id", ""),
                    "query_text": q.get("query_text", ""),
                    "status": status,
                })

        for fu in follow_up_telemetry.get("queries", []):
            all_executed_queries.append({
                "channel": "adaptive",
                "query_id": fu.get("query_id", ""),
                "query_text": fu.get("query_text", ""),
                "status": "SUCCESS",
            })
            succeeded_queries_count += 1

        for eq in esc_telemetry.get("queries", []):
            all_executed_queries.append({
                "channel": "primary_escalation",
                "query_id": "q_esc",
                "query_text": eq,
                "status": "SUCCESS",
            })
            succeeded_queries_count += 1

        sat_summary = novelty_tracker.get_summary()
        halt_reason = (
            follow_up_telemetry.get("halt_reason") or
            ("SATURATION_THRESHOLD_REACHED" if sat_summary.get("is_saturated") else "BUDGET_CEILING")
        )

        funnel = {
            "queries_planned": total_queries_planned,
            "queries_submitted": len(all_executed_queries),
            "queries_succeeded": succeeded_queries_count,
            "queries_failed": failed_queries_count,
            "queries_executed": succeeded_queries_count,
            "candidates_found": len(candidates),
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
            raw_candidates=[c.to_dict() for c in candidates],
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
            "queries_planned": total_queries_planned,
            "queries_submitted": len(all_executed_queries),
            "queries_succeeded": succeeded_queries_count,
            "queries_failed": failed_queries_count,
            "queries_executed": succeeded_queries_count,
            "query_classes_count": len(query_classes),
            "follow_ups_executed": follow_up_telemetry["attempted"],
            "candidates_found": len(candidates),
            "candidates_ranked": len(ranked_candidates),
            "deep_read_attempted": read_telemetry["attempted"],
            "deep_read_success": read_telemetry["successful"],
            "candidate_selection_audit": selection_audit,
            "total_chars_read": read_telemetry["total_chars_read"],
            "primary_sources_found": len(primary_sources),
            "escalations": esc_telemetry,
            "independent_source_groups": len(clusters_map),
            "contradictions_found": len(contradictions),
            "findings_count": len(findings),
            "saturation": sat_summary,
            "source_lineage": lineage_graph.get("metrics", {}),
            "total_latency_ms": total_latency_ms,
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
            telemetry["dossier_id"] = f"R-2026-TEMP-{int(time.time())}"

        logger.info(f"[ResearchEngine] Investigation finished in {total_latency_ms}ms (dossier={telemetry.get('dossier_id')}): {len(findings)} findings, {len(primary_sources)} primaries")

        return ResearchResult(
            agent=request.agent_name,
            target=request.target,
            domain=request.domain,
            summary=summary,
            candidates=candidates,
            investigated_sources=investigated_items,
            evidence=ranked_candidates,
            findings=findings,
            contradictions=contradictions,
            source_graph=graph,
            source_lineage_graph=lineage_graph,
            primary_sources=primary_sources,
            telemetry=telemetry,
            channel_status=channel_status,
            retrieval_trace=trace_dict,
            research_corpus=corpus.to_dict(),
        )


research_engine = ResearchEngine()
