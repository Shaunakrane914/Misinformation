"""Bounded adaptive query expansion with novelty/saturation halting."""

from datetime import datetime
import logging
import time
from typing import Any, Dict, List, Optional, Set

from backend.application.research.contracts import AdaptiveEvidence, Discovery, QueryPlan, RankedEvidence
from backend.services.agent_reach.channels import QueryExecutionRecord
from backend.services.research.candidate_ranker import candidate_ranker
from backend.services.research.contradiction_detector import contradiction_detector
from backend.services.research.evidence_saturation import EvidenceNoveltyTracker
from backend.services.research.relevance_gate import relevance_gate
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import EvidenceItem, ResearchRequest
from backend.services.research.source_independence import source_independence_engine
from backend.services.research.source_quality import source_quality_engine

logger = logging.getLogger(__name__)


class AdaptiveExpansionStage:
    def run(self, request: ResearchRequest, budget: ResearchBudget, plan: QueryPlan,
            discovery: Discovery, ranked: RankedEvidence, start_ts: float,
            effective_timeout: float) -> AdaptiveEvidence:
        from backend.services.agent_reach import agent_reach_service

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
            evidence_snippets=[c.snippet for c in ranked.accepted[:10]],
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
            "halt_reason": None,
            "source_replan": {
                "triggered": False,
                "gaps": [],
                "new_actions": [],
                "accepted_evidence": 0,
            },
        }
        max_adaptive_rounds = min(budget.follow_up_budget, 3)
        seen_adaptive_queries: Set[str] = set()
        adaptive_query_records: List[QueryExecutionRecord] = []

        # Bound discovery and adaptive search by discovery timeout to prevent deep read starvation
        discovery_ceiling = min(effective_timeout * 0.45, budget.discovery_timeout_seconds)

        # Connect the shared SourcePlanningEngine's single bounded replan to
        # real evidence gaps.  The legacy RetrievalPlanner continues to own
        # query wording for later novelty rounds during compatibility migration.
        source_plan = getattr(plan, "source_plan", None)
        if budget.follow_up_budget > 0 and source_plan is not None:
            gaps: List[str] = []
            if not ranked.accepted:
                gaps.append("no relevant results")
            if not any(getattr(item, "primary_source", False) for item in ranked.accepted):
                gaps.append("missing primary evidence")
            independent_groups = {
                getattr(item, "independence_group", "")
                for item in ranked.accepted if getattr(item, "independence_group", "")
            }
            if len(independent_groups) < 2:
                gaps.append("insufficient independent corroboration")
            full_depths = {
                "FULL_ARTICLE", "PRIMARY_DOCUMENT", "REGULATORY_FILING",
                "OFFICIAL_STATEMENT", "SOCIAL_POST", "VIDEO_TRANSCRIPT",
            }
            if ranked.accepted and not any(
                str(getattr(item, "content_depth", "")).upper() in full_depths
                for item in ranked.accepted
            ):
                gaps.append("metadata-only results when full evidence is required")

            if gaps:
                before_ids = {action.action_id for action in source_plan.actions}
                replanned = source_plan
                try:
                    from backend.services.agent_reach.source_planner import source_planning_engine
                    replanned = source_planning_engine.replan(source_plan, gaps)
                except Exception as error:
                    logger.debug("[ResearchEngine] Source replan failed closed: %s", error)
                new_actions = [
                    action for action in replanned.actions if action.action_id not in before_ids
                ]
                follow_up_telemetry["source_replan"].update(
                    triggered=bool(new_actions),
                    gaps=gaps,
                    new_actions=[action.to_dict() for action in new_actions],
                )
                if new_actions and (time.time() - start_ts) < discovery_ceiling:
                    replan_queries: Dict[str, List[Dict[str, str]]] = {}
                    for action in new_actions:
                        replan_queries.setdefault(action.channel, []).append({
                            "query_id": action.action_id,
                            "query_class": action.source_category,
                            "query_text": action.query,
                            "operation": action.operation,
                        })
                    replan_result = agent_reach_service.retrieve_many(
                        channel_queries=replan_queries,
                        domain=request.domain,
                        agent_name=request.agent_name,
                        target_name=request.target,
                        budget={
                            "max_queries_per_channel": 1,
                            "max_results_per_query": 3,
                            "max_total_evidence": 6,
                            "max_deep_reads": 0,
                        },
                        perform_reads=False,
                        timeout=min(6.0, max(2.0, discovery_ceiling - (time.time() - start_ts))),
                    )
                    replan_candidates: List[EvidenceItem] = []
                    for idx, fragment in enumerate(replan_result.fragments):
                        item_id = getattr(fragment, "evidence_id", None) or f"ev_replan_{idx + 1:03d}"
                        item = EvidenceItem.from_evidence_fragment(
                            fragment, item_id=item_id, target_name=request.target
                        )
                        source_quality_engine.classify_and_score(item, target_name=request.target)
                        replan_candidates.append(item)
                    accepted_replan, rejected_replan = relevance_gate.filter_candidates(
                        replan_candidates,
                        target_entity=request.target,
                        domain=request.domain,
                        intent=request.intent,
                    )
                    existing_urls = {item.canonical_url for item in ranked.accepted}
                    for item in accepted_replan:
                        if item.canonical_url not in existing_urls:
                            ranked.accepted.append(item)
                            existing_urls.add(item.canonical_url)
                    ranked.rejected.extend(rejected_replan)
                    adaptive_query_records.extend(replan_result.query_records)
                    follow_up_telemetry["source_replan"]["accepted_evidence"] = len(accepted_replan)
                    ranked.accepted, ranked.clusters = source_independence_engine.cluster_independence(ranked.accepted)
                    ranked.ranked = candidate_ranker.rank_candidates(
                        ranked.accepted,
                        target_name=request.target,
                        intent=request.intent,
                        query_classes=plan.query_classes,
                    )

        if budget.follow_up_budget > 0:
            for round_idx in range(1, max_adaptive_rounds + 1):
                elapsed = time.time() - start_ts
                if elapsed >= discovery_ceiling:
                    follow_up_telemetry["halted_early"] = True
                    follow_up_telemetry["halt_reason"] = "discovery_timeout_reached"
                    logger.info(f"[ResearchEngine] Halting adaptive queries early: discovery timeout reached ({elapsed:.1f}s >= {discovery_ceiling}s)")
                    break

                if novelty_tracker.is_saturated:
                    follow_up_telemetry["halted_early"] = True
                    follow_up_telemetry["halt_reason"] = novelty_tracker.halt_reason
                    logger.info(f"[ResearchEngine] Halting adaptive queries early at round {round_idx}: {novelty_tracker.halt_reason}")
                    break

                # 1. Dynamically replan targeted queries based on latest ranked evidence and discovered contradictions
                current_contradictions = contradiction_detector.detect_contradictions(
                    ranked.ranked[:10],
                    target_name=request.target
                )
                round_candidates_plan = plan.planner.plan_adaptive_follow_ups(
                    target_name=request.target,
                    initial_plan=None,
                    evidence_items=ranked.ranked[:12],
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

                for fu_idx, fu in enumerate(new_queries):
                    if (time.time() - start_ts) >= discovery_ceiling or novelty_tracker.is_saturated:
                        reason = "discovery_timeout_reached" if (time.time() - start_ts) >= discovery_ceiling else novelty_tracker.halt_reason
                        follow_up_telemetry["halted_early"] = True
                        follow_up_telemetry["halt_reason"] = reason
                        # Record remaining planned queries as SKIPPED
                        for remaining_fu in new_queries[fu_idx:]:
                            if remaining_fu["query_text"].lower().strip() not in seen_adaptive_queries:
                                seen_adaptive_queries.add(remaining_fu["query_text"].lower().strip())
                                rem_ch = remaining_fu.get("suggested_channels", ["web"])[0] if remaining_fu.get("suggested_channels") else "web"
                                adaptive_query_records.append(QueryExecutionRecord(
                                    query_id=remaining_fu["query_id"],
                                    channel=rem_ch,
                                    query_text=remaining_fu["query_text"],
                                    query_class=remaining_fu.get("query_class", "adaptive_expansion"),
                                    phase="adaptive",
                                    status="SKIPPED",
                                    started_at=datetime.utcnow().isoformat(),
                                    completed_at=datetime.utcnow().isoformat(),
                                    latency_ms=0,
                                    result_count_raw=0,
                                    result_count_normalized=0,
                                    error=reason,
                                    retrieval_mode="skipped",
                                    backend_id=rem_ch,
                                ))
                        break

                    seen_adaptive_queries.add(fu["query_text"].lower().strip())
                    follow_up_telemetry["attempted"] += 1
                    follow_up_telemetry["queries_submitted"] += 1
                    follow_up_telemetry["queries"].append(fu)

                    suggested_ch = fu.get("suggested_channels", ["web", "news"])
                    new_snippets_this_step: List[str] = []
                    query_had_success = False
                    q_start_time = time.time()
                    q_started_at = datetime.utcnow().isoformat()
                    fu_error: Optional[str] = None
                    raw_fu_count = 0

                    fu_candidates: List[EvidenceItem] = []
                    for ch in suggested_ch[:2]:
                        try:
                            frags = agent_reach_service.search_channel(ch, fu["query_text"], limit=2)
                            if frags:
                                query_had_success = True
                                raw_fu_count += len(frags)
                            for f in frags:
                                u = getattr(f, "url", "") or ""
                                if u and any(c.canonical_url == u for c in (ranked.accepted + discovery.raw_candidates)):
                                    continue
                                item_id = getattr(f, "candidate_id", None) or getattr(f, "evidence_id", None) or f"ev_fu_{len(ranked.accepted) + len(ranked.rejected) + 1:03d}"
                                ev_item = EvidenceItem.from_evidence_fragment(f, item_id=item_id, target_name=request.target)
                                ev_item.query_id = fu["query_id"]
                                ev_item.query_class = fu.get("query_class", "adaptive_expansion")
                                ev_item.query_text = fu.get("query_text", "")
                                ev_item.metadata["parent_query_id"] = fu.get("parent_query_id", "q_001")
                                ev_item.metadata["trigger"] = fu.get("trigger", "adaptive")
                                ev_item.metadata["reason"] = fu.get("reason", "")
                                ev_item.metadata["adaptive_round"] = round_idx
                                source_quality_engine.classify_and_score(ev_item, target_name=request.target)
                                fu_candidates.append(ev_item)
                        except Exception as e:
                            fu_error = str(e)
                            logger.debug(f"[ResearchEngine] Follow-up query error for '{fu['query_text']}': {e}")

                    # Hard filter follow-up items through relevance gate
                    fu_accepted, fu_rejected = relevance_gate.filter_candidates(
                        fu_candidates,
                        target_entity=request.target,
                        domain=request.domain,
                        intent=request.intent
                    )
                    ranked.rejected.extend(fu_rejected)
                    for acc_item in fu_accepted:
                        ranked.accepted.append(acc_item)
                        new_snippets_this_step.append(acc_item.snippet)

                    q_lat = int((time.time() - q_start_time) * 1000)
                    q_completed_at = datetime.utcnow().isoformat()

                    if query_had_success:
                        fu_status = "SUCCESS"
                        follow_up_telemetry["queries_succeeded"] += 1
                    elif fu_error:
                        fu_status = "TIMEOUT" if "timeout" in fu_error.lower() else "FAILED"
                        follow_up_telemetry["queries_failed"] += 1
                    else:
                        fu_status = "SUCCESS" if raw_fu_count > 0 else "FAILED"
                        if fu_status == "SUCCESS":
                            follow_up_telemetry["queries_succeeded"] += 1
                        else:
                            follow_up_telemetry["queries_failed"] += 1

                    primary_ch = suggested_ch[0] if suggested_ch else "web"
                    adaptive_query_records.append(QueryExecutionRecord(
                        query_id=fu["query_id"],
                        channel=primary_ch,
                        query_text=fu["query_text"],
                        query_class=fu.get("query_class", "adaptive_expansion"),
                        phase="adaptive",
                        status=fu_status,
                        started_at=q_started_at,
                        completed_at=q_completed_at,
                        latency_ms=q_lat,
                        result_count_raw=raw_fu_count,
                        result_count_normalized=len(new_snippets_this_step),
                        error=fu_error,
                        retrieval_mode="direct",
                        backend_id=primary_ch,
                    ))

                    # Record step in novelty tracker
                    novelty_tracker.record_step(
                        query_id=fu.get("query_id", f"q_fu_{follow_up_telemetry['attempted']}"),
                        query_text=fu.get("query_text", ""),
                        channel=suggested_ch[0] if suggested_ch else "web",
                        evidence_snippets=new_snippets_this_step
                    )

                # Re-cluster and re-rank after each round so next round replans with enriched pool
                ranked.accepted, ranked.clusters = source_independence_engine.cluster_independence(ranked.accepted)
                ranked.ranked = candidate_ranker.rank_candidates(
                    ranked.accepted,
                    target_name=request.target,
                    intent=request.intent,
                    query_classes=plan.query_classes
                )

        return AdaptiveEvidence(ranked, novelty_tracker, follow_up_telemetry, adaptive_query_records)


# Canonical architectural alias
AdaptiveDiscoveryCoordinator = AdaptiveExpansionStage

