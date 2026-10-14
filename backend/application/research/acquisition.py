"""Planning, broad discovery, qualification, and evidence ranking."""

from typing import Any

from backend.application.research.contracts import Discovery, QueryPlan, RankedEvidence
from backend.services.research.candidate_ranker import candidate_ranker
from backend.services.research.relevance_gate import relevance_gate
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import EvidenceItem, ResearchRequest
from backend.services.research.source_independence import source_independence_engine
from backend.services.research.source_quality import source_quality_engine


class QueryPlanningStage:
    def run(self, request: ResearchRequest) -> QueryPlan:
        from backend.services.agent_reach.planner import RetrievalPlanner
        from backend.services.agent_reach.source_planner import source_planning_engine

        planner = RetrievalPlanner()
        legacy_queries, query_classes = planner.build_multi_channel_queries(
            request.target, domain=request.domain
        )
        source_plan = source_planning_engine.plan(
            f"{request.target}. {request.intent}",
            entity=request.target,
            domain=request.domain,
            agent=request.agent_name,
        )
        planned_queries = source_plan.to_channel_queries()

        # Preserve useful domain query diversity, but only for channels selected
        # by the capability-aware plan. Planner actions take precedence and the
        # per-channel bound prevents indiscriminate fan-out.
        multi_queries: dict[str, list[dict[str, Any]]] = {}
        for channel in source_plan.channels:
            combined = list(planned_queries.get(channel, []))
            seen = {item.get("query_text", "").strip().lower() for item in combined}
            for item in legacy_queries.get(channel, []):
                query_text = item.get("query_text", "").strip()
                if query_text and query_text.lower() not in seen:
                    combined.append(item)
                    seen.add(query_text.lower())
                if len(combined) >= source_plan.budget.max_queries_per_channel:
                    break
            if combined:
                multi_queries[channel] = combined[:source_plan.budget.max_queries_per_channel]
        # The legacy planner also combined request.query_classes into a local
        # value, but never consumed it; retaining that no-op is unnecessary.
        return QueryPlan(planner, multi_queries, query_classes, source_plan)


class BroadDiscoveryStage:
    def run(self, request: ResearchRequest, budget: ResearchBudget,
            effective_timeout: float, plan: QueryPlan) -> Any:
        from backend.services.agent_reach import agent_reach_service

        channel_timeout = min(budget.channel_timeout_seconds, max(2.0, effective_timeout / 2))
        return agent_reach_service.retrieve_many(
            channel_queries=plan.channel_queries,
            domain=request.domain,
            agent_name=request.agent_name,
            target_name=request.target,
            source_url=request.source_url,
            budget={
                "max_queries_per_channel": 3,
                "max_results_per_query": 5,
                "max_total_evidence": request.max_candidates or budget.max_candidates,
                "max_deep_reads": 0,
            },
            perform_reads=False,
            timeout=channel_timeout * 2,
        )


class CandidateQualificationStage:
    def run(self, request: ResearchRequest, retrieval: Any) -> Discovery:
        raw_candidates: list[EvidenceItem] = []
        for idx, frag in enumerate(retrieval.fragments):
            item_id = getattr(frag, "candidate_id", None) or getattr(frag, "evidence_id", None) or f"ev_{idx + 1:03d}"
            ev_item = EvidenceItem.from_evidence_fragment(frag, item_id=item_id, target_name=request.target)
            source_quality_engine.classify_and_score(ev_item, target_name=request.target)
            raw_candidates.append(ev_item)

        accepted, rejected = relevance_gate.filter_candidates(
            raw_candidates,
            target_entity=request.target,
            domain=request.domain,
            intent=request.intent,
        )
        return Discovery(retrieval, raw_candidates, accepted, list(rejected))


class IndependenceRankingStage:
    def run(self, request: ResearchRequest, plan: QueryPlan,
            accepted: list[EvidenceItem], rejected: list[dict[str, Any]]) -> RankedEvidence:
        accepted, clusters = source_independence_engine.cluster_independence(accepted)
        ranked = candidate_ranker.rank_candidates(
            accepted,
            target_name=request.target,
            intent=request.intent,
            query_classes=plan.query_classes,
        )
        return RankedEvidence(accepted, ranked, clusters, rejected)


# Canonical 10-stage architectural aliases
PlanningStage = QueryPlanningStage
DiscoveryStage = BroadDiscoveryStage
GatingStage = CandidateQualificationStage
RankingStage = IndependenceRankingStage

