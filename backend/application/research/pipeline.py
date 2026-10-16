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
        start_ts = time.time()
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

        def run_stage(stage, *args):
            nonlocal completed
            label = labels[completed]
            report_progress(pipeline_pass=pass_id, pipeline_step=label,
                            pipeline_completed=completed, pipeline_total=len(labels))
            try:
                result = stage.run(*args)
            except Exception:
                report_progress(pipeline_pass=pass_id, pipeline_step=label,
                                pipeline_completed=completed, pipeline_total=len(labels), pipeline_failed=True)
                raise
            completed += 1
            report_progress(pipeline_pass=pass_id, pipeline_step=label,
                            pipeline_completed=completed, pipeline_total=len(labels))
            return result

        plan = run_stage(QueryPlanningStage(), request)
        retrieval = run_stage(BroadDiscoveryStage(), request, self.budget, effective_timeout, plan)
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
        read = run_stage(PassageAnalysisStage(), request, escalated.ranked, read)
        analysis = run_stage(GroundedSynthesisStage(), request, escalated.ranked, read)
        analysis = run_stage(EvidenceGraphStage(), escalated.ranked, analysis)
        assembled = run_stage(CorpusAssemblyStage(),
            request, self.budget, plan, discovery, escalated.ranked,
            adaptive, escalated, read, analysis, start_ts,
        )
        run_stage(DossierRegistrationStage(), request, escalated.ranked, analysis, assembled)
        return run_stage(ResultPublicationStage(),
            request, self.budget, discovery, escalated.ranked, read, analysis, assembled
        )
