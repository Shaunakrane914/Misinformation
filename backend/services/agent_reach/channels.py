"""
Aegis Protocol — Channel Abstraction & Evidence Fragment
========================================================
Defines the Channel protocol, ChannelStatus enum, and EvidenceFragment
dataclass used across the entire Agent Reach capability layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional
import uuid


class ChannelStatus(str, Enum):
    """Health status of an internet evidence channel."""
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"
    NOT_PROBED = "NOT_PROBED"


@dataclass
class QueryExecutionRecord:
    """Canonical execution record for an attempted retrieval query."""
    query_id: str
    channel: str
    query_text: str
    query_class: Optional[str] = None
    phase: str = "initial"  # "initial" | "adaptive" | "primary_escalation"
    status: str = "PLANNED"  # "PLANNED" | "SUBMITTED" | "SUCCESS" | "FAILED" | "TIMEOUT" | "AUTH_REQUIRED" | "SKIPPED"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    latency_ms: Optional[int] = None
    result_count_raw: Optional[int] = None
    result_count_normalized: Optional[int] = None
    error: Optional[str] = None
    retrieval_mode: Optional[str] = None
    backend_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "channel": self.channel,
            "query_text": self.query_text,
            "query_class": self.query_class,
            "phase": self.phase,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "latency_ms": self.latency_ms,
            "result_count_raw": self.result_count_raw,
            "result_count_normalized": self.result_count_normalized,
            "error": self.error,
            "retrieval_mode": self.retrieval_mode,
            "backend_id": self.backend_id,
        }


class RetrievalMode(str, Enum):
    """Accurate classification of the retrieval backend mechanism used."""
    UPSTREAM_AGENT_REACH = "upstream_agent_reach"
    NATIVE_TOOL_CLI = "native_tool_cli"
    DIRECT_API = "direct_api"
    ZERO_AUTH_PUBLIC_MIRROR = "zero_auth_public_mirror"
    WEB_SEARCH_INDEX = "web_search_index"
    RSS_FEED = "rss_feed"
    WEB_READER = "web_reader"
    UNAUTHENTICATED_SYNDICATED_FALLBACK = "unauthenticated_syndicated_fallback"
    LEGACY_SCRAPER_FALLBACK = "legacy_scraper_fallback"
    CACHED = "cached"
    UNKNOWN = "unknown"


@dataclass
class RetrievalProfile:
    """
    Domain-specific retrieval configuration defining an agent's evidence expectations,
    required fields, preferred platforms, content depth, and extraction requirements.
    """
    agent: str
    required_fields: List[str] = field(default_factory=list)
    preferred_platforms: List[str] = field(default_factory=list)
    content_depth: str = "SNIPPET"
    max_candidates: int = 5
    max_deep_reads: int = 3
    need_comments: bool = False
    need_transcript: bool = False
    need_engagement: bool = False
    need_structured_metadata: bool = False
    need_primary_source: bool = False
    extraction_hints: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "required_fields": self.required_fields,
            "preferred_platforms": self.preferred_platforms,
            "content_depth": self.content_depth,
            "max_candidates": self.max_candidates,
            "max_deep_reads": self.max_deep_reads,
            "need_comments": self.need_comments,
            "need_transcript": self.need_transcript,
            "need_engagement": self.need_engagement,
            "need_structured_metadata": self.need_structured_metadata,
            "need_primary_source": self.need_primary_source,
            "extraction_hints": self.extraction_hints,
        }


@dataclass
class RetrievalRequest:
    """
    Canonical request sent by any domain agent to the shared retrieval fabric.
    Encapsulates identity, task parameters, channel boundaries, candidate budget,
    and agent-specific retrieval profile.
    """
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:10]}")
    agent: str = "generic"                    # "brandshield" | "trending" | "scout" | "personal"
    entity: str = ""                         # Primary target entity or organization
    intent: str = ""                         # High-level goal (e.g. "counterfeit_check", "guidance_cut")
    task_type: str = "SEARCH"                # "SEARCH" | "STATUS" | "PROFILE" | "READ" | "FEED"
    scope: str = ""                          # Domain/subreddit/handle boundary
    time_window: str = ""                    # e.g. "24h", "7d", "30d"
    allowed_channels: List[str] = field(default_factory=list)
    candidate_budget: int = 5                # Default Top-5 semantic candidate knee
    query: str = ""                          # Optional pre-formulated query string
    query_constraints: Dict[str, Any] = field(default_factory=dict)
    profile: Optional[RetrievalProfile] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "agent": self.agent,
            "entity": self.entity,
            "intent": self.intent,
            "task_type": self.task_type,
            "scope": self.scope,
            "time_window": self.time_window,
            "allowed_channels": self.allowed_channels,
            "candidate_budget": self.candidate_budget,
            "query": self.query,
            "query_constraints": self.query_constraints,
            "profile": self.profile.to_dict() if self.profile else None,
            "metadata": self.metadata,
        }


class AgentAcquisitionBase(ABC):
    """
    Standard interface for all agent-specific acquisition implementations.
    Enforces that custom acquisition logic respects common contracts,
    returns normalized EvidenceFragment records, and exposes capability metadata.
    """

    @abstractmethod
    def get_profile(self) -> RetrievalProfile:
        """Return the agent's configured retrieval profile."""
        pass

    @abstractmethod
    def discover(self, query: str, limit: int = 5) -> List[Any]:
        """Stage 1: Cheap metadata and search candidate discovery."""
        pass

    @abstractmethod
    def acquire(self, candidate: Any, request: RetrievalRequest) -> Any:
        """Stage 2: Targeted candidate retrieval respecting required fields."""
        pass

    @abstractmethod
    def normalize(
        self,
        doc: Any,
        candidate: Any,
        request: RetrievalRequest,
    ) -> List[Any]:
        """Convert fetched document into canonical EvidenceFragment records."""
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Machine-readable health and status check."""
        pass

    @abstractmethod
    def capabilities(self) -> Dict[str, Any]:
        """Machine-readable capability and constraint descriptor."""
        pass


@dataclass
class RetrievalPlan:
    """
    Orchestrated multi-channel retrieval plan generated by RetrievalPlanner.
    Defines queries, channel assignments, routing policy, and escalation rules.
    """
    plan_id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:10]}")
    request_id: str = ""
    generated_queries: List[Dict[str, Any]] = field(default_factory=list)
    selected_channels: List[str] = field(default_factory=list)
    route_policy: str = "policy_d"           # Frozen Policy D (Specialist -> Scrapling -> Playwright -> Search)
    candidate_budget: int = 5
    fallback_policy: str = "graceful_fallback"
    escalation_policy: str = "weak_evidence_escalation"  # Escalate to Top-10 only when needed
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "request_id": self.request_id,
            "generated_queries": self.generated_queries,
            "selected_channels": self.selected_channels,
            "route_policy": self.route_policy,
            "candidate_budget": self.candidate_budget,
            "fallback_policy": self.fallback_policy,
            "escalation_policy": self.escalation_policy,
            "metadata": self.metadata,
        }


@dataclass
class CandidateSource:
    """
    Discovered candidate source reference prior to deep acquisition.
    Subjected to hard source gates before ranking.
    """
    candidate_id: str = field(default_factory=lambda: f"cand_{uuid.uuid4().hex[:10]}")
    url: str = ""
    platform: str = ""
    canonical_url: str = ""
    search_engine: str = ""
    search_rank: int = 0
    discovery_query: str = ""
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    title: str = ""
    snippet: str = ""
    passed_hard_gates: bool = True
    gate_failure_reason: Optional[str] = None
    semantic_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.canonical_url:
            self.canonical_url = self.url

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "url": self.url,
            "canonical_url": self.canonical_url,
            "platform": self.platform,
            "search_engine": self.search_engine,
            "search_rank": self.search_rank,
            "discovery_query": self.discovery_query,
            "discovered_at": self.discovered_at,
            "title": self.title,
            "snippet": self.snippet,
            "passed_hard_gates": self.passed_hard_gates,
            "gate_failure_reason": self.gate_failure_reason,
            "semantic_score": self.semantic_score,
            "metadata": self.metadata,
        }


@dataclass
class FetchedDocument:
    """
    Raw document payload acquired by a platform adapter.
    """
    url: str
    status: str = "SUCCESS"                   # "SUCCESS" | "FAILED" | "TIMEOUT" | "BLOCKED"
    backend_id: str = ""
    retrieval_mode: str = ""
    raw_content: str = ""
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0
    failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "status": self.status,
            "backend_id": self.backend_id,
            "retrieval_mode": self.retrieval_mode,
            "raw_content": self.raw_content,
            "raw_metadata": self.raw_metadata,
            "latency_ms": self.latency_ms,
            "failure_reason": self.failure_reason,
        }


class ContentDepth(str, Enum):
    """Accurate classification of the level of evidence detail acquired."""
    HEADLINE_ONLY = "HEADLINE_ONLY"
    SNIPPET = "SNIPPET"
    PARTIAL_CONTENT = "PARTIAL_CONTENT"
    FULL_ARTICLE = "FULL_ARTICLE"
    STRUCTURED_METADATA = "STRUCTURED_METADATA"
    TRANSCRIPT = "TRANSCRIPT"
    SOCIAL_POST = "SOCIAL_POST"
    COMMENT = "COMMENT"
    PROFILE = "PROFILE"


@dataclass
class SourceRecord:
    """
    Immutable identity of an external source (invariant across observations).
    """
    source_id: str
    platform: str
    canonical_url: str
    external_id: str = ""
    author: str = ""
    publisher: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "platform": self.platform,
            "canonical_url": self.canonical_url,
            "external_id": self.external_id,
            "author": self.author,
            "publisher": self.publisher,
        }


@dataclass
class EvidenceObservation:
    """
    Time-varying observation record of an external source at a specific point in time.
    Preserves historical changes, engagement growth, and content revisions.
    """
    observation_id: str
    source_id: str
    content_hash: str
    retrieved_at: str
    retrieval_mode: str
    backend_id: str
    content_depth: str
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "source_id": self.source_id,
            "content_hash": self.content_hash,
            "retrieved_at": self.retrieved_at,
            "retrieval_mode": self.retrieval_mode,
            "backend_id": self.backend_id,
            "content_depth": self.content_depth,
            "provenance": self.provenance,
        }


class FallbackReasonCode(str, Enum):
    """Authoritative machine-readable fallback reason taxonomy."""
    NATIVE_NO_RESULTS = "NATIVE_NO_RESULTS"
    NATIVE_EMPTY_CONTENT = "NATIVE_EMPTY_CONTENT"
    NATIVE_CONTENT_TOO_SHORT = "NATIVE_CONTENT_TOO_SHORT"
    NATIVE_EXCEPTION = "NATIVE_EXCEPTION"
    HTTP_403 = "HTTP_403"
    HTTP_404 = "HTTP_404"
    HTTP_429 = "HTTP_429"
    HTTP_5XX = "HTTP_5XX"
    DNS_FAILURE = "DNS_FAILURE"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    READ_TIMEOUT = "READ_TIMEOUT"
    PARSER_FAILURE = "PARSER_FAILURE"
    JS_REQUIRED = "JS_REQUIRED"
    BOT_CHALLENGE = "BOT_CHALLENGE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    INVALID_URL = "INVALID_URL"
    SSRF_BLOCK = "SSRF_BLOCK"
    MIRROR_UNAVAILABLE = "MIRROR_UNAVAILABLE"
    SEARCH_INDEX_EMPTY = "SEARCH_INDEX_EMPTY"
    NORMALIZATION_FAILURE = "NORMALIZATION_FAILURE"
    RELEVANCE_REJECTION = "RELEVANCE_REJECTION"
    OTHER = "OTHER"


@dataclass
class AcquisitionAttempt:
    """
    Forensic record of a discrete retrieval attempt against an external backend.
    Preserves multi-phase attempts, latency, HTTP codes, and fallback triggers.
    """
    attempt_id: str = field(default_factory=lambda: f"att_{uuid.uuid4().hex[:10]}")
    agent: str = "generic"
    query_id: str = ""
    candidate_id: str = ""
    source_id: str = ""
    url: str = ""
    requested_channel: str = ""
    actual_channel: str = ""
    backend: str = ""
    retrieval_mode: str = ""
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str = ""
    latency_ms: int = 0
    status: str = "INITIATED"           # SUCCESS | FAILED | TIMEOUT | BLOCKED
    fallback_used: bool = False
    fallback_backend: Optional[str] = None
    fallback_reason: Optional[str] = None
    http_status: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "agent": self.agent,
            "query_id": self.query_id,
            "candidate_id": self.candidate_id,
            "source_id": self.source_id,
            "url": self.url,
            "requested_channel": self.requested_channel,
            "actual_channel": self.actual_channel,
            "backend": self.backend,
            "retrieval_mode": self.retrieval_mode,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "fallback_used": self.fallback_used,
            "fallback_backend": self.fallback_backend,
            "fallback_reason": self.fallback_reason,
            "http_status": self.http_status,
            "error": self.error,
        }


@dataclass
class EvidenceFragment:
    """
    Normalized retrieval output from any channel.
    Every piece of internet evidence goes through this representation
    before being consumed by Aegis agents.
    """
    platform: str
    title: str = ""
    content: str = ""
    url: str = ""
    author: str = ""
    published: str = ""
    snippet: str = ""
    score: float = 0.0
    retrieval_method: str = "agent_reach"
    retrieved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    channel_name: str = ""
    content_depth: str = "SNIPPET"  # HEADLINE_ONLY | SNIPPET | PARTIAL_CONTENT | FULL_ARTICLE
    query_id: str = ""
    query_class: str = ""
    query_text: str = ""
    retrieval_mode: str = RetrievalMode.UNKNOWN.value
    native_backend_id: Optional[str] = None
    fallback_reason: Optional[str] = None
    is_authenticated: bool = False
    requested_channel: str = ""
    actual_retrieval_channel: str = ""
    evidence_id: str = ""
    source_id: str = ""
    observation_id: str = ""
    retrieval_lineage: List[Dict[str, Any]] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 1. Compute stable immutable source_id (Invariant across repeated retrievals)
        clean_url = (self.url or "").split("#")[0].strip()
        # Keep query parameters only for video identifiers
        if "youtube.com" not in clean_url and "youtu.be" not in clean_url:
            clean_url = clean_url.split("?")[0].rstrip("/").lower()
        base_source_str = f"{self.platform.lower().strip()}:{clean_url}:{self.author.lower().strip()}"
        if not self.source_id:
            self.source_id = f"src_{hashlib.sha256(base_source_str.encode('utf-8', errors='ignore')).hexdigest()[:12]}"
        
        # 2. Stable evidence_id maps to stable source identity
        if not self.evidence_id:
            self.evidence_id = f"ev_{hashlib.sha256(base_source_str.encode('utf-8', errors='ignore')).hexdigest()[:12]}"

        # 3. Time-varying observation_id tracks this specific retrieval observation
        content_fingerprint = hashlib.sha256((self.content or self.snippet or self.title or "").encode("utf-8", errors="ignore")).hexdigest()[:12]
        obs_key = f"{self.source_id}:{content_fingerprint}:{self.retrieved_at}"
        if not self.observation_id:
            self.observation_id = f"obs_{hashlib.sha256(obs_key.encode('utf-8', errors='ignore')).hexdigest()[:12]}"

        if not self.requested_channel:
            self.requested_channel = self.channel_name or self.platform
        if not self.actual_retrieval_channel:
            self.actual_retrieval_channel = self.channel_name or self.platform
        if not self.retrieval_lineage:
            self.retrieval_lineage = [{
                "channel": self.actual_retrieval_channel or self.channel_name or self.platform,
                "requested_channel": self.requested_channel or self.channel_name or self.platform,
                "query_id": self.query_id,
                "retrieval_mode": self.retrieval_mode,
                "backend_id": self.native_backend_id,
                "fallback_reason": self.fallback_reason,
                "is_authenticated": self.is_authenticated,
                "retrieved_at": self.retrieved_at,
                "source_id": self.source_id,
                "observation_id": self.observation_id,
            }]

    @property
    def metadata(self) -> Dict[str, Any]:
        """Convenience alias for raw_metadata."""
        return self.raw_metadata

    @metadata.setter
    def metadata(self, val: Dict[str, Any]) -> None:
        self.raw_metadata = val

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses and JSON storage."""
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "observation_id": self.observation_id,
            "platform": self.platform,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "author": self.author,
            "published": self.published,
            "snippet": self.snippet,
            "score": self.score,
            "retrieval_method": self.retrieval_method,
            "retrieval_mode": self.retrieval_mode,
            "native_backend_id": self.native_backend_id,
            "fallback_reason": self.fallback_reason,
            "is_authenticated": self.is_authenticated,
            "retrieved_at": self.retrieved_at,
            "channel_name": self.channel_name,
            "content_depth": self.content_depth,
            "query_id": self.query_id,
            "query_class": self.query_class,
            "query_text": self.query_text,
            "requested_channel": self.requested_channel,
            "actual_retrieval_channel": self.actual_retrieval_channel,
            "retrieval_lineage": self.retrieval_lineage,
            "raw_metadata": self.raw_metadata,
        }

    # ── Dict-like compatibility ───────────────────────────────────────────
    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        if key in self.raw_metadata:
            return self.raw_metadata[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or (hasattr(self, "raw_metadata") and key in self.raw_metadata)

    @classmethod
    def from_scraper_dict(
        cls,
        data: Dict[str, Any],
        channel_name: str,
        query_id: str = "",
        query_class: str = "",
        query_text: str = "",
        content_depth: str = "SNIPPET"
    ) -> "EvidenceFragment":
        """
        Factory: convert a raw scraper result dict into an EvidenceFragment.
        Handles varied field names across Reddit/Twitter/YouTube/News scrapers.
        """
        title = data.get("title", "")
        content = data.get("content", "")
        snippet = data.get("snippet", title)

        # Detect content depth heuristically if not explicitly provided
        depth = content_depth
        if depth == "SNIPPET":
            if len(content) > 1000 or data.get("is_full_article"):
                depth = "FULL_ARTICLE"
            elif len(content) > 250:
                depth = "PARTIAL_CONTENT"
            elif len(snippet) <= len(title) + 5 and len(snippet) < 120:
                depth = "HEADLINE_ONLY"

        return cls(
            platform=data.get("platform", channel_name),
            title=title,
            content=content,
            url=data.get("url", ""),
            author=data.get("author", ""),
            published=data.get("published", ""),
            snippet=snippet,
            score=float(data.get("score", 0)),
            retrieval_method=data.get("retrieval_method", "agent_reach"),
            retrieval_mode=data.get("retrieval_mode", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value),
            native_backend_id=data.get("backend", "legacy_scraper"),
            fallback_reason="NATIVE_TOOL_UNAVAILABLE",
            channel_name=channel_name,
            content_depth=depth,
            query_id=query_id or data.get("query_id", ""),
            query_class=query_class or data.get("query_class", ""),
            query_text=query_text or data.get("query_text", ""),
            evidence_id=data.get("evidence_id", ""),
            raw_metadata={
                k: v for k, v in data.items()
                if k not in ("platform", "title", "content", "url", "author",
                             "published", "snippet", "score", "retrieval_method",
                             "content_depth", "query_id", "query_class", "query_text",
                             "retrieval_mode", "backend")
            },
        )


@dataclass
class ChannelTelemetry:
    """Operational telemetry per channel."""
    channel: str
    queries_attempted: List[str] = field(default_factory=list)
    requests_attempted: int = 0
    successful_requests: int = 0
    raw_results: int = 0
    normalized_results: int = 0
    duplicates_removed: int = 0
    final_results: int = 0
    latency_ms: int = 0
    status: str = "AVAILABLE"
    active_backend: str = ""
    fallback_used: bool = False
    fallback_backend: Optional[str] = None
    failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "queries_attempted": self.queries_attempted,
            "requests_attempted": self.requests_attempted,
            "successful_requests": self.successful_requests,
            "raw_results": self.raw_results,
            "normalized_results": self.normalized_results,
            "duplicates_removed": self.duplicates_removed,
            "final_results": self.final_results,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "active_backend": self.active_backend,
            "fallback_used": self.fallback_used,
            "fallback_backend": self.fallback_backend,
            "failure_reason": self.failure_reason,
        }


@dataclass
class ExecutionGraphStep:
    """Detailed capability-aware execution graph step for a single retrieval action."""
    step_id: int
    platform: str
    backend: str
    operation: str
    fallback_chain: List[str] = field(default_factory=list)
    fallback_used: bool = False
    result_count: int = 0
    read_depth: str = "SNIPPET"
    failure_reason: Optional[str] = None
    latency_ms: int = 0
    status: str = "SUCCESS"  # SUCCESS | DEGRADED | TIMEOUT | FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "platform": self.platform,
            "backend": self.backend,
            "operation": self.operation,
            "fallback_chain": self.fallback_chain,
            "fallback_used": self.fallback_used,
            "result_count": self.result_count,
            "read_depth": self.read_depth,
            "failure_reason": self.failure_reason,
            "latency_ms": self.latency_ms,
            "status": self.status,
        }


@dataclass
class RetrievalTrace:
    """Complete internal retrieval telemetry trace across all stages."""
    scan_id: str
    agent: str
    query: str
    domain: str
    planned_query_classes: int = 0
    planned_queries_count: int = 0
    executed_queries_count: int = 0
    channel_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    execution_graph: List[Dict[str, Any]] = field(default_factory=list)
    capability_summary: Dict[str, Any] = field(default_factory=dict)
    total_raw: int = 0
    total_normalized: int = 0
    total_duplicates: int = 0
    total_final: int = 0
    unique_domains: int = 0
    independent_groups: int = 0
    readable_sources: int = 0
    total_latency_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "agent": self.agent,
            "query": self.query,
            "domain": self.domain,
            "planning": {
                "query_classes_created": self.planned_query_classes,
                "queries_generated": self.planned_queries_count,
                "queries_executed": self.executed_queries_count,
            },
            "channels": self.channel_stats,
            "execution_graph": self.execution_graph,
            "capability_summary": self.capability_summary,
            "total": {
                "raw_results": self.total_raw,
                "normalized_results": self.total_normalized,
                "duplicates_removed": self.total_duplicates,
                "final_evidence": self.total_final,
                "unique_domains": self.unique_domains,
                "independent_groups": self.independent_groups,
                "readable_sources": self.readable_sources,
                "latency_ms": self.total_latency_ms,
            }
        }

    def to_ascii_table(self) -> str:
        lines = [
            f"SCAN: {self.query} (domain={self.domain}, id={self.scan_id}, agent={self.agent})",
            "-" * 70,
            f"Planned Query Classes: {self.planned_query_classes} | Planned Queries: {self.planned_queries_count} | Executed: {self.executed_queries_count}",
            "",
            f"{'CHANNEL':<12} {'ATTEMPTED':<10} {'RAW':<6} {'DUPES':<7} {'FINAL':<7} {'STATUS':<12} {'LATENCY':<8}",
            "-" * 70,
        ]
        for ch, s in self.channel_stats.items():
            lines.append(
                f"{ch:<12} {s.get('requests_attempted', 0):<10} {s.get('raw_results', 0):<6} "
                f"{s.get('duplicates_removed', 0):<7} {s.get('final_results', 0):<7} "
                f"{s.get('status', 'UNKNOWN'):<12} {s.get('latency_ms', 0)}ms"
            )
        lines.extend([
            "-" * 70,
            f"TOTALS: Raw: {self.total_raw} | Duplicates: {self.total_duplicates} | Final Evidence: {self.total_final}",
            f"Unique Domains: {self.unique_domains} | Independent Groups: {self.independent_groups} | Readable Sources: {self.readable_sources}",
            f"Total Latency: {self.total_latency_ms}ms",
            "-" * 70,
        ])
        return "\n".join(lines)


@dataclass
class RetrievalResult:
    """Complete result from a retrieval operation across multiple channels."""
    query: str
    domain: str
    fragments: List[EvidenceFragment] = field(default_factory=list)
    channel_health: Dict[str, str] = field(default_factory=dict)
    total_signals: int = 0
    retrieval_plan: Optional[Dict[str, Any]] = None
    source_article: Optional[Dict[str, Any]] = None
    retrieval_trace: Optional[Dict[str, Any]] = None
    trace_obj: Optional["RetrievalTrace"] = None
    query_records: List[QueryExecutionRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API responses."""
        return {
            "query": self.query,
            "domain": self.domain,
            "fragments": [f.to_dict() for f in self.fragments],
            "channel_health": self.channel_health,
            "total_signals": self.total_signals,
            "retrieval_plan": self.retrieval_plan,
            "source_article": self.source_article,
            "retrieval_trace": self.retrieval_trace,
            "query_records": [q.to_dict() if hasattr(q, "to_dict") else q for q in self.query_records],
        }

    # ── Backward-compatible accessors ─────────────────────────────────────
    # These let existing code that expects the old omni_scan dict shape
    # continue to work without changes.

    @property
    def items(self) -> List[Dict[str, Any]]:
        """Legacy accessor: return fragments as dicts (matches omni_scan output)."""
        return [f.to_dict() for f in self.fragments]

    @property
    def channels(self) -> Dict[str, List[Dict[str, Any]]]:
        """Legacy accessor: return fragments grouped by channel name."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for frag in self.fragments:
            key = frag.channel_name or frag.platform.lower().replace("/", "_").replace(" ", "_")
            grouped.setdefault(key, []).append(frag.to_dict())
        return grouped


class Channel(ABC):
    """
    Abstract base for an internet evidence channel.

    Each channel encapsulates one retrieval backend (Reddit, Twitter, etc.)
    and exposes a uniform search + health-check interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique channel identifier (e.g. 'reddit', 'twitter')."""

    @abstractmethod
    def search(self, query: str, limit: int = 6) -> List[EvidenceFragment]:
        """
        Search this channel for evidence matching the query.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of normalized EvidenceFragment objects
        """

    @abstractmethod
    def health_check(self) -> ChannelStatus:
        """
        Probe this channel's availability.

        Returns:
            Current ChannelStatus
        """

    def __repr__(self) -> str:
        return f"<Channel:{self.name}>"
