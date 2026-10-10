"""Typed hand-offs between research pipeline stages.

The contracts retain the existing domain objects and ordering. They do not
serialize or copy evidence, since downstream stages annotate those same items.
"""

from dataclasses import dataclass, field
from typing import Any

from backend.services.agent_reach.channels import QueryExecutionRecord, RetrievalResult
from backend.services.research.evidence_saturation import EvidenceNoveltyTracker
from backend.services.research.research_models import EvidenceItem, Finding, ResearchCorpus


@dataclass
class QueryPlan:
    planner: Any
    channel_queries: dict[str, list[dict[str, Any]]]
    query_classes: Any
    source_plan: Any = None


@dataclass
class Discovery:
    retrieval: RetrievalResult
    raw_candidates: list[EvidenceItem]
    accepted: list[EvidenceItem]
    rejected: list[dict[str, Any]]


@dataclass
class RankedEvidence:
    accepted: list[EvidenceItem]
    ranked: list[EvidenceItem]
    clusters: dict[str, list[str]]
    rejected: list[dict[str, Any]]


@dataclass
class AdaptiveEvidence:
    ranked: RankedEvidence
    novelty: EvidenceNoveltyTracker
    telemetry: dict[str, Any]
    query_records: list[QueryExecutionRecord]


@dataclass
class EscalatedEvidence:
    ranked: RankedEvidence
    primaries: list[EvidenceItem]
    telemetry: dict[str, Any]
    query_records: list[QueryExecutionRecord]


@dataclass
class ReadEvidence:
    investigated: list[EvidenceItem]
    telemetry: dict[str, Any]


@dataclass
class Analysis:
    contradictions: list[dict[str, Any]]
    findings: list[Finding]
    integrity_report: Any
    graph: dict[str, Any]
    lineage_graph: dict[str, Any]


@dataclass
class AssembledResearch:
    corpus: ResearchCorpus
    telemetry: dict[str, Any]
    summary: str
    primary_sources: list[EvidenceItem]
    total_latency_ms: int
