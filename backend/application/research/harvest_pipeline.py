"""Acquisition-first orchestration using the existing evidence/agent contracts.

Reading eligibility is deliberately not evidence eligibility. The raw pool is
populated before any semantic qualification, and remains available for replay.
"""
import time
import uuid
import os
from dataclasses import replace

from backend.application.research.contracts import (
    AdaptiveEvidence, Discovery, EscalatedEvidence, QueryPlan, RankedEvidence, ReadEvidence,
)
from backend.application.research.progress import report_progress
from backend.application.research.acquisition import IndependenceRankingStage
from backend.application.research.assembly import CorpusAssemblyStage, DossierRegistrationStage, ResultPublicationStage
from backend.application.research.synthesis import PassageAnalysisStage, GroundedSynthesisStage, EvidenceGraphStage
from backend.services.agent_reach.channels import RetrievalResult
from backend.services.research.evidence_saturation import EvidenceNoveltyTracker
from backend.services.research.passage_extractor import has_usable_passage
from backend.services.research.raw_pool import RawAcquisitionPool
from backend.services.research.relevance_gate import relevance_gate
from backend.services.research.source_quality import source_quality_engine


def run_harvest_pipeline(request, budget, profile_name):
    from backend.services.agent_reach import agent_reach_service
    from backend.services.research.harvesting import HarvestingEngine
    from backend.services.research.research_profiles import get_research_profile
    from backend.services.research.body_context import reconcile_captured_context
    from backend.infrastructure.llm.advisory_policy import observations
    from backend.infrastructure.acquisition.network.budget import PublicRequestBudget, public_request_budget

    started = time.monotonic()
    profile = get_research_profile(profile_name)
    timeout = min(profile.timeout_seconds, max(0.0, request.timeout_seconds
                  if request.timeout_seconds is not None else budget.timeout_seconds))
    # Explicit caller limits can lower, never silently enlarge, the selected mode.
    disabled = budget.max_deep_reads <= 0 or budget.max_candidates <= 0
    profile = replace(profile, max_reads=min(profile.max_reads, max(1, budget.max_deep_reads)),
                      max_candidates=min(profile.max_candidates, max(1, budget.max_candidates)))
    if disabled:
        timeout = 0.0
    run_id = uuid.uuid4().hex
    timings = {}
    labels = ("Query planning and raw harvesting", "Strict body qualification", "Source independence ranking",
              "Passage analysis", "Grounded synthesis", "Evidence graph", "Corpus assembly", "Dossier registration")
    completed = 0

    def stage(label, callback):
        nonlocal completed
        report_progress(pipeline_pass=run_id, pipeline_step=label, pipeline_completed=completed, pipeline_total=len(labels))
        before = time.monotonic()
        result = callback()
        timings[label] = round((time.monotonic() - before) * 1000, 2)
        completed += 1
        report_progress(pipeline_pass=run_id, pipeline_step=label, pipeline_completed=completed, pipeline_total=len(labels))
        return result

    http_cap = {"QUICK": 40, "STANDARD": 80, "DEEP": 120}[profile.name]
    http_cap = min(http_cap, max(1, int(os.getenv("AEGIS_HARVEST_HTTP_CAP", str(http_cap)))))
    http_budget = PublicRequestBudget(total=http_cap, per_host=24)
    # Preserve existing capability-aware specialist routes without replacing
    # publisher harvesting with a universal social-source sweep.
    from backend.services.agent_reach.source_planner import source_planning_engine
    source_plan = source_planning_engine.plan(request.extra_params.get("claim_text") or request.target,
        entity=request.target, domain=request.domain, agent=request.agent_name, use_llm=False,
        routing_hints={**request.extra_params, 'time_scope': request.time_scope},
        allowed_channels=request.extra_params.get('allowed_channels'))
    extra_queries = [{"channel": channel, **row} for channel, rows in source_plan.to_channel_queries().items()
                     if channel not in {"reddit", "twitter"} for row in rows]
    for row in extra_queries:
        row['source_plan_action_id'] = row['query_id']
    specialist_plan = None
    if request.domain in {"brand", "personal"}:
        from backend.services.research.specialist_planning import build_specialist_harvest_plan
        extra_queries, specialist_plan = build_specialist_harvest_plan(request, source_plan)
    # One explicit adapter discovery action competes inside the original two
    # optional slots; its returned leads still require normal budgeted reads.
    from backend.infrastructure.acquisition.adapters.expanded_catalog import expanded_query
    from backend.services.agent_reach.native.operation_capabilities import runtime_operation_capabilities
    expanded = expanded_query(request, research_context=getattr(source_plan, 'research_context', {}))
    allowed = request.extra_params.get("allowed_channels")
    expanded_allowed = allowed is None or "expanded_sources" in allowed
    if (expanded and expanded_allowed and not request.source_url
            and runtime_operation_capabilities.assess("expanded_sources", "search")["decision"] not in {"EXCLUDE", "DEFER_TEMPORARY"}):
        core = [row for row in extra_queries if row.get("channel") in {"web", "news", "rss"}]
        optional = [row for row in extra_queries if row.get("channel") not in {"web", "news", "rss"}]
        extra_queries = core + [expanded] + optional[:1]
    try:
        with public_request_budget(http_budget):
            harvest = stage(labels[0], lambda: HarvestingEngine(agent_reach_service).run(
                target=request.target, domain=request.domain, intent=request.intent, agent_name=request.agent_name,
                profile=profile, deadline=started + timeout * .90, request=request,
                source_url=request.source_url, query_plan=extra_queries,
                source_plan=source_plan,
                controller=os.getenv("AEGIS_ACQUISITION_CONTROLLER", "legacy"),
                specialist_tasks=(specialist_plan or {}).get("requested_tasks", []),
                specialist_task_explicit=bool((specialist_plan or {}).get("explicit_task")),
                progress=lambda counts: report_progress(phase="harvesting", **counts)))
    finally:
        http_budget.close()
    harvest.metrics.update(http_budget.snapshot())
    pool = RawAcquisitionPool(run_id)
    for candidate in harvest.candidates:
        pool.add_candidate(candidate)
    for capture in harvest.captures:
        # Classify the observed body before the pool fixes its structural type.
        # This also re-evaluates saved text without changing the captured bytes.
        capture.metadata["temporal_required"] = request.domain == "trending"
        reconcile_captured_context(capture)
        pool.add_capture(capture)
    by_id = {item.id: item for item in harvest.candidates}
    for attempt in harvest.read_telemetry.get("acquisition_attempts", []):
        if attempt.get("status") != "SUCCESS":
            pool.add_failure(by_id.get(attempt.get("candidate_id")) or attempt.get("url", ""),
                             attempt.get("failure_kind") or "READ_FAILED", http_status=attempt.get("http_status"))

    rejected = list(harvest.rejected)

    def qualify():
        accepted = []
        for item in harvest.captures:
            item.metadata["temporal_required"] = request.domain == "trending"
            reconcile_captured_context(item)
            # Final semantic decisions must concern captured body, not an old
            # search snippet or a provider's favorable headline.
            item.metadata["discovery_snippet"] = item.snippet
            item.relevant_excerpt = ""
            item.snippet = item.content[:12_000]
            source_quality_engine.classify_and_score(item, target_name=request.target)
            result = relevance_gate.evaluate_item(item, request.target, domain=request.domain, intent=request.intent)
            raw_record = pool.get(item.id) or {}
            structural_body = raw_record.get("source_type") in {"ARTICLE_BODY", "OFFICIAL_DOCUMENT", "COMMUNITY_POST", "STRUCTURED_PUBLIC_DATA"}
            from backend.services.research.source_registry import source_registry
            permission = source_registry.excerpt_decision(item.canonical_url, item.metadata.get('page_metadata'))
            item.metadata['source_use_permission'] = permission
            item.metadata["layer2_eligible"] = result.is_accepted and structural_body and permission['eligible']
            reason = result.rejection_reason or ("NO_STRUCTURAL_BODY" if not structural_body else
                     permission.get('reason') if not permission['eligible'] else None)
            item.metadata["post_read_qualification_reason"] = reason
            item.metadata["temporal_required"] = request.domain == "trending"
            item.metadata["temporal_eligible"] = result.is_accepted if request.domain == "trending" else True
            if item.metadata["layer2_eligible"]:
                accepted.append(item)
            else:
                rejected.append({**result.to_dict(), "is_accepted": False, "rejection_reason": reason or "BODY_NOT_RELEVANT",
                                 "rejection_stage": result.rejection_stage or "BODY_STRUCTURE"})
                pool.mark_qualification(item.id, "REJECTED", reasons=[reason or "BODY_NOT_RELEVANT"])
        return accepted

    accepted = stage(labels[1], qualify)
    queries = getattr(harvest, "channel_queries", {})
    if not queries:
        for record in harvest.query_records:
            queries.setdefault(record.channel, []).append({"query_id": record.query_id,
                "query_text": record.query_text, "query_class": record.query_class})
    plan = QueryPlan(None, queries, {item.query_class for item in harvest.candidates}, source_plan)
    retrieval = RetrievalResult(query=request.target, domain=request.domain,
        query_records=harvest.query_records, retrieval_trace={**getattr(harvest, "retrieval_trace", {}),
            "scan_id": run_id, "harvesting": harvest.metrics},
        channel_health=getattr(harvest, "channel_health", {}))
    discovery = Discovery(retrieval, harvest.candidates, accepted, rejected)
    ranked = stage(labels[2], lambda: IndependenceRankingStage().run(request, plan, accepted, rejected))
    novelty = EvidenceNoveltyTracker()
    adaptive = AdaptiveEvidence(ranked, novelty, {"attempted": 0, "rounds_executed": 0,
        "halt_reason": harvest.metrics.get("halt_reason", "HARVEST_COMPLETE"),
        "ai_search_advice": harvest.metrics.get("ai_search_advice", {"status": "DISABLED"})}, [])
    escalated = EscalatedEvidence(ranked, [], {"attempted": 0, "mode": "HARVESTED_WITH_SHARED_BUDGET"}, [])
    read = ReadEvidence(harvest.captures, harvest.read_telemetry)
    read = stage(labels[3], lambda: PassageAnalysisStage().run(request, ranked, read, 0.0))
    for item in read.investigated:
        if not item.metadata.get("layer2_eligible", False):
            item.relevant_excerpt = ""
            item.extraction_status = "LAYER2_REJECTED"
        useful = has_usable_passage(item)
        pool.mark_qualification(item.id, "QUALIFIED" if useful else "REJECTED",
            reasons=[] if useful else [item.metadata.get("post_read_qualification_reason") or item.extraction_status],
            useful_words=len(item.relevant_excerpt.split()) if useful else 0)
    for record in pool.export(include_text=False)["sources"]:
        if record["qualification_status"] == "PENDING":
            pool.mark_qualification(record["source_id"], "DUPLICATE" if record["duplicate_of"] else "REJECTED",
                reasons=["EXACT_CAPTURE_DUPLICATE" if record["duplicate_of"] else "NOT_ACQUIRED_OR_NOT_USABLE"])
    # Specialists must consume the qualified body set, not re-run keyword threat
    # classifiers on all harvested navigation/product text. Raw bytes and their
    # explicit rejection reasons remain inspectable in the pool below.
    read.investigated = [item for item in read.investigated if has_usable_passage(item)]
    analysis = stage(labels[4], lambda: GroundedSynthesisStage().run(request, ranked, read))
    analysis = stage(labels[5], lambda: EvidenceGraphStage().run(ranked, analysis))
    assembled = stage(labels[6], lambda: CorpusAssemblyStage().run(request, budget, plan, discovery, ranked,
        adaptive, escalated, read, analysis, started))
    # One traceable pool, not a second evidence list with regenerated identities.
    raw_export = pool.export(include_text=True)
    assembled.corpus.raw_acquisition_pool = raw_export
    assembled.telemetry.update(raw_acquisition_pool=pool.export(include_text=False), acquisition_metrics=pool.stats(),
        harvesting=harvest.metrics, research_profile=profile.name, stage_timings_ms=timings,
        ai_advisory_observations=observations(current_only=True))
    if specialist_plan is not None:
        assembled.telemetry["specialist_planning"] = {
            **specialist_plan,
            "harvest_admission": harvest.metrics.get("specialist_action_admission", {}),
            "selection_scope": "Promoted source-plan actions; profile admission and submission are separate observations",
        }
    assembled.telemetry["acquisition_metrics"]["findings"] = len(analysis.findings)
    assembled.telemetry["acquisition_metrics"]["publisher_independence_verified"] = False
    if request.domain == 'trending' and len(read.investigated) < 2:
        from backend.services.research.trending_background import historical_background
        assembled.telemetry['historical_background'] = historical_background(harvest.captures, request.target)
    measured = assembled.telemetry["acquisition_metrics"]
    funnel = assembled.telemetry["discovery_funnel"]
    from backend.services.research.discovery_funnel import summarize_qualification_decisions
    decisions = summarize_qualification_decisions(rejected)
    for legacy in (assembled.telemetry.get("funnel", {}), assembled.corpus.funnel):
        legacy.update(candidates_rejected=decisions["rejected_candidate_count"],
            candidates_accepted=harvest.metrics.get("candidates_accepted_for_read", 0),
            raw_capture_count=measured["successful_captures"], article_body_count=measured["article_bodies"],
            qualified_source_count=measured["qualified_source_count"],
            publisher_link_decision_count=decisions["publisher_link_decision_count"],
            candidate_count_scope="Read-eligible leads and post-read rejected source identities are different stages and may overlap")
    assembled.telemetry["candidates_rejected"] = decisions["rejected_candidate_count"]
    assembled.telemetry["candidates_accepted"] = harvest.metrics.get("candidates_accepted_for_read", 0)
    funnel.update(decisions)
    funnel.update(extracted_article_bodies=measured["article_bodies"],
                  successful_body_captures=measured["article_bodies"] + measured["by_type"].get("OFFICIAL_DOCUMENT", 0),
                  raw_capture_count=measured["successful_captures"],
                  qualified_evidence=measured["qualified_source_count"],
                  qualified_evidence_ids=[item.id for item in read.investigated],
                  accepted_candidates=harvest.metrics.get("candidates_accepted_for_read", 0))
    observed_boundary = funnel.get("first_observed_empty_boundary")
    if measured["qualified_source_count"]:
        funnel["first_observed_empty_boundary"] = None
    elif funnel["successful_body_captures"]:
        funnel["first_observed_empty_boundary"] = "BODY_OR_PASSAGE_QUALIFICATION"
    elif observed_boundary in {"PLANNING", "SEARCH_TRANSPORT", "SEARCH_RANKING", "DISCOVERY_NO_RESULTS",
                              "PUBLISHER_RESOLUTION", "READING_BUDGET"}:
        pass  # Retain the measured earlier loss, not a generic empty result.
    else:
        funnel["first_observed_empty_boundary"] = ("DISCOVERY" if not harvest.candidates else
            "READING" if not measured["successful_captures"] else "ARTICLE_EXTRACTION")
    if not read.investigated:
        acquisition_failed = not measured["successful_captures"] and (
            harvest.read_telemetry.get("attempted") or
            assembled.telemetry["acquisition"].get("status") == "ACQUISITION_FAILED")
        assembled.telemetry["acquisition"]["status"] = "ACQUISITION_FAILED" if acquisition_failed else "INSUFFICIENT_EVIDENCE"
        assembled.telemetry["acquisition"]["message"] = (
            "Unable to retrieve source bodies: the attempted reads failed; this is not proof that no public evidence exists."
            if assembled.telemetry["acquisition"]["status"] == "ACQUISITION_FAILED" else
            "Acquisition completed without usable task-relevant evidence. Inspect raw captures and per-source qualification reasons; no claim verdict is established.")
        assembled.summary = assembled.telemetry["acquisition"]["message"]
    # Optional audit persistence is explicit and only creates an owned temp tree.
    if request.extra_params.get("persist_raw_pool") or os.getenv("AEGIS_RAW_POOL_PERSIST", "false").lower() == "true":
        assembled.telemetry["raw_pool_snapshot"] = str(pool.save_temporary())
    report_progress(phase="qualification", acquisition_metrics=pool.stats())
    stage(labels[7], lambda: DossierRegistrationStage().run(request, ranked, analysis, assembled))
    return ResultPublicationStage().run(request, budget, discovery, ranked, read, analysis, assembled)
