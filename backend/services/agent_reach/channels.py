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
from typing import Any, Dict, List, Optional


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
    WEB_SEARCH_INDEX = "web_search_index"
    RSS_FEED = "rss_feed"
    WEB_READER = "web_reader"
    UNAUTHENTICATED_SYNDICATED_FALLBACK = "unauthenticated_syndicated_fallback"
    LEGACY_SCRAPER_FALLBACK = "legacy_scraper_fallback"
    CACHED = "cached"
    UNKNOWN = "unknown"


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
    retrieval_lineage: List[Dict[str, Any]] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
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
            }]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses and JSON storage."""
        return {
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
