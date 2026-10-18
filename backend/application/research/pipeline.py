"""Application-level orchestration of the bounded research investigation."""

import logging
import time
import uuid

from backend.application.research.acquisition import (
    BroadDiscoveryStage, CandidateQualificationStage, IndependenceRankingStage,
    QueryPlanningStage,
)
from backend.application.research.adaptive import AdaptiveExpansionStage
from backend.application.research.assembly import (
    CorpusAssemblyStage, DossierRegistrationStage, ResultPublicationStage,
)
from backend.application.research.reading import DeepReadingStage, PrimaryEscalationStage
from backend.application.research.synthesis import (
    EvidenceGraphStage, GroundedSynthesisStage, PassageAnalysisStage,
)
from backend.services.research.research_budget import ResearchBudget
from backend.services.research.research_models import ResearchRequest, ResearchResult
from backend.application.research.progress import report_progress

logger = logging.getLogger(__name__)


class ResearchPipeline:
    """Coordinates stages without owning retrieval, scoring, or persistence logic."""

    def __init__(self, budget: ResearchBudget):
        self.budget = budget

    def run(self, request: ResearchRequest) -> ResearchResult:
        from backend.infrastructure.llm.advisory_policy import investigation_scope
        with investigation_scope():
            return self._run(request)

    def _run(self, request: ResearchRequest) -> ResearchResult:
        start_ts = time.monotonic()
        effective_timeout = (
            request.timeout_seconds if getattr(request, "timeout_seconds", None) is not None
            else self.budget.timeout_seconds
        )
        logger.info(
            "[ResearchEngine] Launching deep investigation for '%s' (domain=%s, timeout=%ss)",
            request.target, request.domain, effective_timeout,
        )

        labels = ("Query planning", "Multi-channel discovery", "Candidate qualification",
                  "Source independence ranking", "Adaptive expansion", "Primary source escalation",
                  "Deep reading", "Passage analysis", "Grounded synthesis", "Evidence graph",
                  "Corpus assembly", "Dossier registration", "Research result publication")
        pass_id, completed = str(uuid.uuid4()), 0
        stage_timings_ms = {}
        stage_budgets = {}

        def run_stage(stage, *args):
            nonlocal completed
            label = labels[completed]
            stage_start = time.monotonic()
            stage_budgets[label] = {"remaining_total_seconds": max(0.0, effective_timeout - (stage_start - start_ts)),
                                   "remaining_discovery_seconds": max(0.0, effective_timeout * 0.45 - (stage_start - start_ts)),
                                   "remaining_reading_seconds": max(0.0, effective_timeout * 0.85 - (stage_start - start_ts))}
            report_progress(pipeline_pass=pass_id, pipeline_step=label,
                            pipeline_completed=completed, pipeline_total=len(labels))
            try:
                result = stage.run(*args)
            except Exception:
                report_progress(pipeline_pass=pass_id, pipeline_step=label,
                                pipeline_completed=completed, pipeline_total=len(labels), pipeline_failed=True)
                raise
            finally:
                stage_timings_ms[label] = round((time.monotonic() - stage_start) * 1000, 2)
            completed += 1
            report_progress(pipeline_pass=pass_id, pipeline_step=label,
                            pipeline_completed=completed, pipeline_total=len(labels))
            return result

        plan = run_stage(QueryPlanningStage(), request)
        discovery_remaining = max(0.0, min(self.budget.discovery_timeout_seconds, effective_timeout * 0.45)
                                  - (time.monotonic() - start_ts))
        retrieval = run_stage(BroadDiscoveryStage(), request, self.budget, discovery_remaining / 0.45, plan)
        discovery = run_stage(CandidateQualificationStage(), request, retrieval)
        ranked = run_stage(IndependenceRankingStage(),
            request, plan, discovery.accepted, discovery.rejected
        )
        adaptive = run_stage(AdaptiveExpansionStage(),
            request, self.budget, plan, discovery, ranked, start_ts, effective_timeout
        )
        escalated = run_stage(PrimaryEscalationStage(),
            request, self.budget, adaptive.ranked, start_ts, effective_timeout
        )
        read = run_stage(DeepReadingStage(),
            request, self.budget, escalated.ranked, start_ts, effective_timeout
        )
        advisor_timeout = min(2.0, max(0.0, effective_timeout - (time.monotonic() - start_ts)))
        read = run_stage(PassageAnalysisStage(), request, escalated.ranked, read, advisor_timeout)
        analysis = run_stage(GroundedSynthesisStage(), request, escalated.ranked, read)
        analysis = run_stage(EvidenceGraphStage(), escalated.ranked, analysis)
        assembled = run_stage(CorpusAssemblyStage(),
            request, self.budget, plan, discovery, escalated.ranked,
            adaptive, escalated, read, analysis, start_ts,
        )
        # Store the completed acquisition/processing measurements before dossier
        # registration, so diagnostic evidence is preserved as well as exported.
        assembled.telemetry["stage_timings_ms"] = dict(stage_timings_ms)
        assembled.telemetry["pre_research_timings_ms"] = request.extra_params.get("pre_research_timings_ms", {})
        assembled.telemetry["budget_observations"] = {
            "clock": "monotonic", "discovery_remaining_at_submission_seconds": discovery_remaining,
            "reading_reservation_seconds": effective_timeout * 0.40,
            "remaining_after_processing_seconds": max(0.0, effective_timeout - (time.monotonic() - start_ts)),
            "stage_entry": stage_budgets,
        }
        run_stage(DossierRegistrationStage(), request, escalated.ranked, analysis, assembled)
        return run_stage(ResultPublicationStage(),
            request, self.budget, discovery, escalated.ranked, read, analysis, assembled
        )
