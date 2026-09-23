"""
Aegis Protocol — Shared Research Infrastructure Layer
=====================================================
Exports typed evidence models, quality scorers, syndication clustering,
deterministic rankers, deep readers, passage extractors, and the unified ResearchEngine.
"""

from backend.services.research.research_models import (
    AtomicClaim,
    ConfidenceLevel,
    ContentDepth,
    ContradictionType,
    EvidenceItem,
    Finding,
    FindingType,
    ResearchRequest,
    ResearchResult,
    SourceRole,
    SourceTier,
    TemporalStatus,
)
from backend.services.research.source_quality import SourceQualityEngine, source_quality_engine
from backend.services.research.source_independence import SourceIndependenceEngine, source_independence_engine
from backend.services.research.candidate_ranker import CandidateRanker, candidate_ranker
from backend.services.research.deep_reader import DeepReader, deep_reader
from backend.services.research.passage_extractor import PassageExtractor, passage_extractor
from backend.services.research.primary_source_escalator import PrimarySourceEscalator, primary_source_escalator
from backend.services.research.corroboration import CorroborationEngine, corroboration_engine
from backend.services.research.contradiction_detector import ContradictionDetector, contradiction_detector
from backend.services.research.evidence_graph import EvidenceGraphBuilder, evidence_graph_builder
from backend.services.research.research_budget import ResearchBudget, default_budget
from backend.services.research.research_engine import ResearchEngine, research_engine

__all__ = [
    "AtomicClaim",
    "CandidateRanker",
    "ConfidenceLevel",
    "ContentDepth",
    "ContradictionDetector",
    "ContradictionType",
    "CorroborationEngine",
    "DeepReader",
    "EvidenceGraphBuilder",
    "EvidenceItem",
    "Finding",
    "FindingType",
    "PassageExtractor",
    "PrimarySourceEscalator",
    "ResearchBudget",
    "ResearchEngine",
    "ResearchRequest",
    "ResearchResult",
    "SourceIndependenceEngine",
    "SourceQualityEngine",
    "SourceRole",
    "SourceTier",
    "TemporalStatus",
    "candidate_ranker",
    "contradiction_detector",
    "corroboration_engine",
    "deep_reader",
    "default_budget",
    "evidence_graph_builder",
    "passage_extractor",
    "primary_source_escalator",
    "research_engine",
    "source_independence_engine",
    "source_quality_engine",
]
