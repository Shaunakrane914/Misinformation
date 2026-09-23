"""
Aegis Protocol — Shared Research Object Models
===============================================
Defines strongly typed forensic evidence, finding, claim, request, and result models
used across all seven domain sentinels and intelligence engines.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import urllib.parse
import re


class ContentDepth(str, Enum):
    HEADLINE_ONLY = "HEADLINE_ONLY"
    SNIPPET = "SNIPPET"
    PARTIAL_CONTENT = "PARTIAL_CONTENT"
    FULL_ARTICLE = "FULL_ARTICLE"
    PRIMARY_DOCUMENT = "PRIMARY_DOCUMENT"
    SOCIAL_POST = "SOCIAL_POST"
    VIDEO_METADATA = "VIDEO_METADATA"
    VIDEO_TRANSCRIPT = "VIDEO_TRANSCRIPT"
    REGULATORY_FILING = "REGULATORY_FILING"
    OFFICIAL_STATEMENT = "OFFICIAL_STATEMENT"


class SourceRole(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    COMMUNITY = "COMMUNITY"
    COMMENTARY = "COMMENTARY"
    DISCOVERY = "DISCOVERY"
    AGGREGATOR = "AGGREGATOR"
    SEARCH_INDEX = "SEARCH_INDEX"


class SourceTier(str, Enum):
    TIER_1_OFFICIAL_FILING = "TIER_1_OFFICIAL_FILING"
    TIER_1_ORIGINAL_DOCUMENT = "TIER_1_ORIGINAL_DOCUMENT"
    TIER_2_FINANCIAL_PRESS = "TIER_2_FINANCIAL_PRESS"
    TIER_2_INVESTIGATIVE = "TIER_2_INVESTIGATIVE"
    TIER_2_VIDEO_ANALYSIS = "TIER_2_VIDEO_ANALYSIS"
    TIER_3_INVESTOR_COMMUNITY = "TIER_3_INVESTOR_COMMUNITY"
    TIER_3_SOCIAL_SIGNALS = "TIER_3_SOCIAL_SIGNALS"
    TIER_3_AGGREGATE = "TIER_3_AGGREGATE"


class FindingType(str, Enum):
    FACT = "FACT"
    EVENT = "EVENT"
    RISK = "RISK"
    CATALYST = "CATALYST"
    TREND = "TREND"
    CONTRADICTION = "CONTRADICTION"
    UNKNOWN = "UNKNOWN"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class ContradictionType(str, Enum):
    FACTUAL_CONTRADICTION = "FACTUAL_CONTRADICTION"
    ATTRIBUTION_DIFFERENCE = "ATTRIBUTION_DIFFERENCE"
    TIMELINE_DISAGREEMENT = "TIMELINE_DISAGREEMENT"
    INTERPRETATION_DIFFERENCE = "INTERPRETATION_DIFFERENCE"
    NO_CONTRADICTION = "NO_CONTRADICTION"


class TemporalStatus(str, Enum):
    NEW_EVENT = "NEW_EVENT"
    ONGOING_EVENT = "ONGOING_EVENT"
    OLD_EVENT_RESURFACED = "OLD_EVENT_RESURFACED"
    HISTORICAL_CONTEXT = "HISTORICAL_CONTEXT"
    UNKNOWN = "UNKNOWN"


@dataclass
class EvidenceItem:
    """
    Forensic, typed evidence item tracking full provenance, depth, quality,
    source family, independence, and relevant extracted passages.
    """
    id: str
    canonical_url: str = ""
    title: str = ""
    source_name: str = ""
    source_domain: str = ""
    channel: str = ""
    query_id: str = ""
    query_class: str = ""
    query_text: str = ""
    published_at: str = ""
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content_depth: str = ContentDepth.SNIPPET.value
    snippet: str = ""
    content: str = ""
    relevant_excerpt: str = ""
    excerpt_start: int = -1
    excerpt_end: int = -1
    source_role: str = SourceRole.DISCOVERY.value
    source_tier: str = SourceTier.TIER_3_AGGREGATE.value
    source_quality_score: float = 0.50
    relevance_score: float = 0.50
    recency_score: float = 0.50
    independence_score: float = 0.50
    source_family_id: str = ""
    independence_group: str = "independent"
    syndicated_from: Optional[str] = None
    primary_source: bool = False
    official_source: bool = False
    entities: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    retrieval_status: str = "SUCCESS"  # SUCCESS | DEGRADED | TIMEOUT | EMPTY
    read_status: str = "NOT_ATTEMPTED"  # NOT_ATTEMPTED | SUCCESS | FAILED | SKIPPED
    extraction_status: str = "NOT_ATTEMPTED"  # NOT_ATTEMPTED | SUCCESS | EMPTY
    contradiction_flag: bool = False
    corroboration_count: int = 1
    provenance: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Dict-like compatibility for legacy code ───────────────────────────
    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        # Check metadata or aliases
        if key == "url":
            return self.canonical_url
        if key == "source":
            return self.source_name
        if key == "platform":
            return self.channel
        if key in self.metadata:
            return self.metadata[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or key in ("url", "source", "platform") or key in self.metadata

    def keys(self):
        d = self.to_dict()
        return d.keys()

    def values(self):
        d = self.to_dict()
        return d.values()

    def items(self):
        d = self.to_dict()
        return d.items()

    @property
    def url(self) -> str:
        return self.canonical_url

    @property
    def source(self) -> str:
        return self.source_name

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to complete forensic dictionary."""
        return {
            "id": self.id,
            "evidence_id": self.id,
            "canonical_url": self.canonical_url,
            "url": self.canonical_url,
            "has_url": bool(self.canonical_url and self.canonical_url.startswith("http")),
            "title": self.title,
            "source_name": self.source_name,
            "source": self.source_name,
            "source_domain": self.source_domain,
            "channel": self.channel,
            "platform": self.channel,
            "author": self.source_name,
            "query_id": self.query_id,
            "query_class": self.query_class,
            "query_text": self.query_text,
            "published_at": self.published_at,
            "discovered_at": self.discovered_at,
            "retrieved_at": self.discovered_at,
            "content_depth": self.content_depth,
            "snippet": self.snippet,
            "content": self.content,
            "relevant_excerpt": self.relevant_excerpt,
            "excerpt_start": self.excerpt_start,
            "excerpt_end": self.excerpt_end,
            "source_role": self.source_role,
            "source_tier": self.source_tier,
            "source_quality_score": round(self.source_quality_score, 3),
            "relevance_score": round(self.relevance_score, 3),
            "recency_score": round(self.recency_score, 3),
            "independence_score": round(self.independence_score, 3),
            "source_family_id": self.source_family_id,
            "independence_group": self.independence_group,
            "syndicated_from": self.syndicated_from,
            "primary_source": self.primary_source,
            "is_primary": self.primary_source,
            "official_source": self.official_source,
            "entities": self.entities,
            "claims": self.claims,
            "topics": self.topics,
            "retrieval_status": self.retrieval_status,
            "read_status": self.read_status,
            "extraction_status": self.extraction_status,
            "contradiction_flag": self.contradiction_flag,
            "corroboration_count": self.corroboration_count,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }

    @classmethod
    def from_evidence_fragment(
        cls,
        fragment: Any,
        item_id: str,
        target_name: str = ""
    ) -> "EvidenceItem":
        """Factory: Convert an AgentReach EvidenceFragment into a typed EvidenceItem."""
        url = getattr(fragment, "url", "") or ""
        parsed_domain = urllib.parse.urlparse(url).netloc.lower() if url else ""
        source_name = getattr(fragment, "author", "") or getattr(fragment, "platform", "") or parsed_domain or "Web"
        
        # Metadata pass-through
        raw_meta = getattr(fragment, "raw_metadata", {}) or {}
        
        return cls(
            id=item_id,
            canonical_url=url,
            title=getattr(fragment, "title", "") or f"{target_name} Signal",
            source_name=source_name,
            source_domain=parsed_domain,
            channel=getattr(fragment, "channel_name", "") or getattr(fragment, "platform", ""),
            query_id=getattr(fragment, "query_id", ""),
            query_class=getattr(fragment, "query_class", "general"),
            query_text=getattr(fragment, "query_text", ""),
            published_at=getattr(fragment, "published", "") or "Recent",
            discovered_at=getattr(fragment, "retrieved_at", "") or datetime.now(timezone.utc).isoformat(),
            content_depth=getattr(fragment, "content_depth", ContentDepth.SNIPPET.value),
            snippet=getattr(fragment, "snippet", "") or getattr(fragment, "content", "")[:280],
            content=getattr(fragment, "content", ""),
            relevant_excerpt=getattr(fragment, "snippet", "")[:350],
            source_role=raw_meta.get("source_role", SourceRole.DISCOVERY.value),
            source_tier=raw_meta.get("source_tier", SourceTier.TIER_3_AGGREGATE.value),
            independence_group=raw_meta.get("source_independence_group", "independent"),
            primary_source=raw_meta.get("source_role") == SourceRole.PRIMARY.value,
            provenance={
                "retrieval_method": getattr(fragment, "retrieval_method", "agent_reach"),
                "score": getattr(fragment, "score", 0.0),
            },
            metadata=raw_meta
        )


@dataclass
class Finding:
    """
    A concrete intelligence finding or factual catalyst substantiated
    by specific evidence IDs, primary sources, and corroboration groups.
    """
    finding_id: str
    title: str
    statement: str
    type: str = FindingType.FACT.value
    importance: str = "HIGH"  # HIGH | MEDIUM | LOW
    confidence: str = ConfidenceLevel.HIGH.value  # HIGH | MEDIUM | LOW | INSUFFICIENT
    supporting_evidence_ids: List[str] = field(default_factory=list)
    contradicting_evidence_ids: List[str] = field(default_factory=list)
    independence_groups: List[str] = field(default_factory=list)
    primary_sources: List[str] = field(default_factory=list)
    explanation: str = ""
    temporal_status: str = TemporalStatus.NEW_EVENT.value
    catalyst_direction: Optional[str] = None  # POSITIVE | NEGATIVE | NEUTRAL | UNCERTAIN
    invalidation_criteria: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "id": self.finding_id,
            "title": self.title,
            "statement": self.statement,
            "type": self.type,
            "importance": self.importance,
            "confidence": self.confidence,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "contradicting_evidence_ids": self.contradicting_evidence_ids,
            "independence_groups": self.independence_groups,
            "primary_sources": self.primary_sources,
            "explanation": self.explanation,
            "temporal_status": self.temporal_status,
            "catalyst_direction": self.catalyst_direction,
            "invalidation_criteria": self.invalidation_criteria,
            "evidence_count": len(self.supporting_evidence_ids),
            "contradiction_count": len(self.contradicting_evidence_ids),
            "metadata": self.metadata,
        }


@dataclass
class AtomicClaim:
    """An individual atomic claim decomposed from an ingested text passage."""
    claim_id: str
    claim_text: str
    entity: str = ""
    event: str = ""
    time: str = ""
    location: str = ""
    claim_type: str = "FACTUAL"  # FACTUAL | CAUSAL | PREDICTIVE | ATTRIBUTIVE
    verifiable_dimensions: List[str] = field(default_factory=list)
    supporting_evidence_ids: List[str] = field(default_factory=list)
    contradicting_evidence_ids: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    verdict: str = "Unverified"
    confidence: float = 0.50
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "entity": self.entity,
            "event": self.event,
            "time": self.time,
            "location": self.location,
            "claim_type": self.claim_type,
            "verifiable_dimensions": self.verifiable_dimensions,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "contradicting_evidence_ids": self.contradicting_evidence_ids,
            "missing_evidence": self.missing_evidence,
            "verdict": self.verdict,
            "confidence": round(self.confidence, 3),
            "rationale": self.rationale,
        }


@dataclass
class ResearchRequest:
    """Structured request submitted to the shared ResearchEngine."""
    target: str
    domain: str = "general"  # financial | brand | personal | trending | fact_check | general
    intent: str = "general intelligence acquisition"
    query_classes: Optional[List[str]] = None
    required_source_roles: Optional[List[str]] = None
    deep_read_budget: int = 8
    corroboration_budget: int = 5
    max_candidates: int = 40
    time_scope: str = "recent"
    source_url: Optional[str] = None
    agent_name: str = "research_engine"
    timeout_seconds: float = 15.0
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchResult:
    """Comprehensive forensic result produced by the shared ResearchEngine."""
    agent: str
    target: str
    domain: str
    summary: str = ""
    candidates: List[EvidenceItem] = field(default_factory=list)
    investigated_sources: List[EvidenceItem] = field(default_factory=list)
    evidence: List[EvidenceItem] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    source_graph: Dict[str, Any] = field(default_factory=dict)
    primary_sources: List[EvidenceItem] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)
    channel_status: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    retrieval_trace: Dict[str, Any] = field(default_factory=dict)

    # ── Backward-compatible properties ────────────────────────────────────
    @property
    def items(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.evidence]

    @property
    def fragments(self) -> List[EvidenceItem]:
        return self.evidence

    @property
    def total_signals(self) -> int:
        return len(self.evidence)

    @property
    def channel_health(self) -> Dict[str, str]:
        return self.channel_status

    @property
    def retrieval_plan(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "target": self.target,
            "candidates_count": len(self.candidates),
            "investigated_count": len(self.investigated_sources),
            "evidence_count": len(self.evidence),
            "findings_count": len(self.findings),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "target": self.target,
            "domain": self.domain,
            "summary": self.summary,
            "candidates_count": len(self.candidates),
            "investigated_count": len(self.investigated_sources),
            "evidence": [e.to_dict() for e in self.evidence],
            "items": [e.to_dict() for e in self.evidence],
            "findings": [f.to_dict() for f in self.findings],
            "contradictions": self.contradictions,
            "source_graph": self.source_graph,
            "primary_sources": [p.to_dict() for p in self.primary_sources],
            "timeline": self.timeline,
            "telemetry": self.telemetry,
            "channel_status": self.channel_status,
            "channel_health": self.channel_status,
            "warnings": self.warnings,
            "retrieval_trace": self.retrieval_trace,
        }
