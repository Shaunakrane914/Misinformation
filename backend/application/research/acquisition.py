"""Planning, broad discovery, qualification, and evidence ranking."""

from typing import Any
import hashlib
import re

from backend.application.research.contracts import Discovery, QueryPlan, RankedEvidence
from backend.services.research.candidate_ranker import candidate_ranker
from backend.services.research.relevance_gate import relevance_gate
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import EvidenceItem, ResearchRequest
from backend.services.research.source_independence import source_independence_engine
from backend.services.research.source_quality import source_quality_engine


def _observed_issuer_documents(parent: EvidenceItem, *, html_only: bool = False) -> list[EvidenceItem]:
    """Bounded leads from a fetched issuer index, never invented body evidence."""
    from backend.services.research.source_quality import canonical_hostname, hostname_matches
    from backend.infrastructure.acquisition.adapters.web.page_extraction import document_link_priority
    from urllib.parse import urlsplit
    if (parent.query_class not in {"issuer_documents", "observed_issuer_document"}
            or not parent.metadata.get("read_success") or parent.metadata.get("document_hop", 0) >= 3):
        return []
    origin = canonical_hostname(parent.metadata.get("observed_final_endpoint") or parent.canonical_url)
    links = (parent.metadata.get("page_metadata") or {}).get("observed_links") or []
    documents = []
    seen = {parent.canonical_url}
    for link in sorted(links, key=document_link_priority):
        url, title = str(link.get("url") or ""), str(link.get("text") or "")
        if html_only and not urlsplit(url).path.lower().endswith((".html", ".htm")):
            continue
        if (url in seen or not hostname_matches(canonical_hostname(url), origin)
                or not re.search(r"quarter|results|filing|earnings|annual.report", title + " " + url, re.I)):
            continue
        seen.add(url)
        item_id = "ev_link_" + hashlib.sha256(url.encode()).hexdigest()[:12]
        documents.append(EvidenceItem(
            id=item_id, canonical_url=url, channel="web", title=title,
            snippet=title, content="", content_depth="INDEX_SNIPPET",
            query_class="observed_issuer_document", query_text=parent.query_text,
            metadata={"discovered_on_url": parent.canonical_url,
                      "discovered_on_candidate_id": parent.id, "link_text": title,
                      "document_hop": parent.metadata.get("document_hop", 0) + 1,
                      "linked_article_retrieved": False},
        ))
        if len(documents) >= 4:
            break
    return documents


class QueryPlanningStage:
    def run(self, request: ResearchRequest) -> QueryPlan:
        from backend.services.agent_reach.planner import RetrievalPlanner
        from backend.services.agent_reach.source_planner import source_planning_engine

        planner = RetrievalPlanner()
        legacy_queries, query_classes = planner.build_multi_channel_queries(
            request.target, domain=request.domain
        )
        # Purpose boilerplate is not a factual claim or useful provider query.
        # Preserve a caller's exact claim separately from the resolved entity.
        planning_text = request.extra_params.get("claim_text") or request.target
        source_plan = source_planning_engine.plan(
            planning_text,
            entity=request.target,
            domain=request.domain,
            agent=request.agent_name,
            use_llm=False,
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
            timeout=min(channel_timeout * 2, budget.discovery_timeout_seconds, effective_timeout * 0.45),
        )


class CandidateQualificationStage:
    def run(self, request: ResearchRequest, retrieval: Any) -> Discovery:
        raw_candidates: list[EvidenceItem] = []
        source_doc = getattr(retrieval, "source_article", None)
        if isinstance(source_doc, dict) and source_doc.get("status") in {"success", "fallback_soup"}:
            text = source_doc.get("markdown") or source_doc.get("content") or ""
            url = source_doc.get("url") or request.source_url or ""
            if url and len(text.strip()) >= 30:
                item_id = "ev_source_" + hashlib.sha256(url.encode()).hexdigest()[:12]
                transport = source_doc.get("transport") or {}
                item = EvidenceItem(
                    id=item_id, canonical_url=url, channel="web", content=text,
                    snippet=text[:280], title=source_doc.get("title") or "User-supplied source",
                    published_at=source_doc.get("published") or "", source_name=source_doc.get("author") or "Web source",
                    content_depth=source_doc.get("content_depth") or "PARTIAL_CONTENT",
                    query_class="user_supplied_source", query_text=request.extra_params.get("claim_text") or request.target,
                    read_status="SUCCESS", acquisition_attempt_id=f"attempt_source_{item_id}", acquired_id=f"cand_acq_{item_id}",
                    metadata={"read_success": True, "acquired_during_discovery": True,
                              "raw_capture": source_doc.get("raw_capture") or {},
                              "page_metadata": source_doc.get("page_metadata") or {},
                              "truncated": source_doc.get("truncated"),
                              "observed_final_endpoint": transport.get("endpoint"), "transport": transport},
                )
                source_quality_engine.classify_and_score(item, target_name=request.target)
                raw_candidates.append(item)
        for idx, frag in enumerate(retrieval.fragments):
            item_id = getattr(frag, "candidate_id", None) or getattr(frag, "evidence_id", None) or f"ev_{idx + 1:03d}"
            ev_item = EvidenceItem.from_evidence_fragment(frag, item_id=item_id, target_name=request.target)
            # A native body is already acquired evidence, not a search snippet
            # needing another generic page read. Keep its canonical ID and
            # provenance; qualification and passage-support gates still apply.
            body_depths = {"PARTIAL_CONTENT", "FULL_ARTICLE", "DIRECT_CONTENT", "DIRECT_ABSTRACT",
                           "COMMENT", "SOCIAL_POST", "TWEET_STATUS", "VIDEO_TRANSCRIPT", "FEED_ENTRY_CONTENT"}
            if ev_item.content_depth in body_depths and ev_item.content.strip() and ev_item.canonical_url:
                ev_item.read_status = "SUCCESS"
                ev_item.acquisition_attempt_id = f"attempt_native_{item_id}"
                ev_item.acquired_id = f"cand_acq_{item_id}"
                ev_item.metadata.update(read_success=True, acquired_during_discovery=True,
                                        acquisition_origin="NATIVE_SOURCE_BODY")
            source_quality_engine.classify_and_score(ev_item, target_name=request.target)
            raw_candidates.append(ev_item)
            for child in _observed_issuer_documents(ev_item):
                source_quality_engine.classify_and_score(child, target_name=request.target)
                raw_candidates.append(child)

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

