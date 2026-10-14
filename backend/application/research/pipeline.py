"""Application-level orchestration of the bounded research investigation."""

import logging
import time

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

        plan = QueryPlanningStage().run(request)
        retrieval = BroadDiscoveryStage().run(request, self.budget, effective_timeout, plan)
        discovery = CandidateQualificationStage().run(request, retrieval)
        ranked = IndependenceRankingStage().run(
            request, plan, discovery.accepted, discovery.rejected
        )
        adaptive = AdaptiveExpansionStage().run(
            request, self.budget, plan, discovery, ranked, start_ts, effective_timeout
        )
        escalated = PrimaryEscalationStage().run(
            request, self.budget, adaptive.ranked, start_ts, effective_timeout
        )
        read = DeepReadingStage().run(
            request, self.budget, escalated.ranked, start_ts, effective_timeout
        )
        read = PassageAnalysisStage().run(request, escalated.ranked, read)
        analysis = GroundedSynthesisStage().run(request, escalated.ranked, read)
        analysis = EvidenceGraphStage().run(escalated.ranked, analysis)
        assembled = CorpusAssemblyStage().run(
            request, self.budget, plan, discovery, escalated.ranked,
            adaptive, escalated, read, analysis, start_ts,
        )
        DossierRegistrationStage().run(request, escalated.ranked, analysis, assembled)
        return ResultPublicationStage().run(
            request, self.budget, discovery, escalated.ranked, read, analysis, assembled
        )
