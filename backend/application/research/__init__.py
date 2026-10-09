"""
Aegis Protocol — Application Research Pipeline
==============================================
Provides decoupled, composable stages for multi-channel investigative research:

Stage 1: PlanningStage (QueryPlanningStage)
Stage 2: DiscoveryStage (BroadDiscoveryStage)
Stage 3: GatingStage (CandidateQualificationStage)
Stage 4: PrimaryEscalationStage
Stage 5: RankingStage (IndependenceRankingStage)
Subcomponent: AdaptiveDiscoveryCoordinator (AdaptiveExpansionStage)
Stage 6: DeepReadingStage
Stage 7: PassageExtractionStage (PassageAnalysisStage)
Stage 8: GraphConstructionStage (EvidenceGraphStage)
Stage 9: SynthesisStage (GroundedSynthesisStage)
Stage 10: LedgerPersistenceStage (DossierRegistrationStage)

Orchestrator: ResearchPipeline
Typed Contracts: QueryPlan, Discovery, RankedEvidence, AdaptiveEvidence,
                 EscalatedEvidence, ReadEvidence, Analysis, AssembledResearch
"""

from backend.application.research.acquisition import (
    BroadDiscoveryStage,
    CandidateQualificationStage,
    DiscoveryStage,
    GatingStage,
    IndependenceRankingStage,
    PlanningStage,
    QueryPlanningStage,
    RankingStage,
)
from backend.application.research.adaptive import (
    AdaptiveDiscoveryCoordinator,
    AdaptiveExpansionStage,
)
from backend.application.research.assembly import (
    CorpusAssemblyStage,
    DossierRegistrationStage,
    LedgerPersistenceStage,
    ResultPublicationStage,
)
from backend.application.research.contracts import (
    AdaptiveEvidence,
    Analysis,
    AssembledResearch,
    Discovery,
    EscalatedEvidence,
    QueryPlan,
    RankedEvidence,
    ReadEvidence,
)
from backend.application.research.pipeline import ResearchPipeline
from backend.application.research.reading import (
    DeepReadingStage,
    PrimaryEscalationStage,
)
from backend.application.research.synthesis import (
    EvidenceGraphStage,
    GraphConstructionStage,
    GroundedSynthesisStage,
    PassageAnalysisStage,
    PassageExtractionStage,
    SynthesisStage,
    synthesize_grounded_findings,
)

__all__ = [
    # Pipeline Orchestrator
    "ResearchPipeline",
    # 10 Canonical Logical Stages
    "PlanningStage",
    "DiscoveryStage",
    "GatingStage",
    "PrimaryEscalationStage",
    "RankingStage",
    "AdaptiveDiscoveryCoordinator",
    "DeepReadingStage",
    "PassageExtractionStage",
    "GraphConstructionStage",
    "SynthesisStage",
    "LedgerPersistenceStage",
    # Descriptive Stage Implementations
    "QueryPlanningStage",
    "BroadDiscoveryStage",
    "CandidateQualificationStage",
    "IndependenceRankingStage",
    "AdaptiveExpansionStage",
    "PassageAnalysisStage",
    "GroundedSynthesisStage",
    "EvidenceGraphStage",
    "CorpusAssemblyStage",
    "DossierRegistrationStage",
    "ResultPublicationStage",
    # Domain Synthesis Helper
    "synthesize_grounded_findings",
    # Typed Contracts
    "QueryPlan",
    "Discovery",
    "RankedEvidence",
    "AdaptiveEvidence",
    "EscalatedEvidence",
    "ReadEvidence",
    "Analysis",
    "AssembledResearch",
]
