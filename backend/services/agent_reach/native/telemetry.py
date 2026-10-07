"""
Aegis Protocol — Shared Acquisition Telemetry
=============================================
Records structured telemetry for every retrieval request and route decision
across the unified acquisition fabric. Answers:
  - "Why did Aegis choose this source?"
  - "Why did Aegis fall back?"
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class RouteDecisionRecord:
    """Record explaining why a specific route/adapter was selected or bypassed."""
    channel: str
    selected_route: str                      # "specialist_mirror" | "scrapling_http" | "playwright_rescue" | "native_api" | "search_fallback"
    route_class: str                         # Route class A/B/C/D/E
    primary_backend: str
    fallback_backend: Optional[str] = None
    reason: str = ""                         # Rationale for selection (e.g. "Policy D zero-auth specialist mirror")
    skipped_routes: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "selected_route": self.selected_route,
            "route_class": self.route_class,
            "primary_backend": self.primary_backend,
            "fallback_backend": self.fallback_backend,
            "reason": self.reason,
            "skipped_routes": self.skipped_routes,
        }


@dataclass
class AcquisitionTelemetryRecord:
    """Detailed telemetry record for a single acquisition request."""
    request_id: str
    query_id: str = ""
    agent: str = "generic"
    platform: str = ""
    backend: str = ""
    route_selected: str = ""
    route_attempts: int = 1
    latency_ms: int = 0
    result_count: int = 0
    failures: List[str] = field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    cache_hit: bool = False
    candidate_count: int = 0
    candidates_selected_deep_read: int = 0
    final_retrieval_mode: str = ""
    source_selection_rationale: str = ""
    recorded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "query_id": self.query_id,
            "agent": self.agent,
            "platform": self.platform,
            "backend": self.backend,
            "route_selected": self.route_selected,
            "route_attempts": self.route_attempts,
            "latency_ms": self.latency_ms,
            "result_count": self.result_count,
            "failures": self.failures,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "cache_hit": self.cache_hit,
            "candidate_count": self.candidate_count,
            "candidates_selected_deep_read": self.candidates_selected_deep_read,
            "final_retrieval_mode": self.final_retrieval_mode,
            "source_selection_rationale": self.source_selection_rationale,
            "recorded_at": self.recorded_at,
        }


class AcquisitionTelemetryCollector:
    """In-memory telemetry sink and aggregator for retrieval requests."""

    def __init__(self):
        self._records: List[AcquisitionTelemetryRecord] = []
        self._route_decisions: List[RouteDecisionRecord] = []

    def record_attempt(self, record: AcquisitionTelemetryRecord) -> None:
        self._records.append(record)
        if len(self._records) > 2000:
            self._records = self._records[-1500:]

    def record_decision(self, decision: RouteDecisionRecord) -> None:
        self._route_decisions.append(decision)
        if len(self._route_decisions) > 1000:
            self._route_decisions = self._route_decisions[-800:]

    def get_records_for_request(self, request_id: str) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records if r.request_id == request_id]

    def summary(self) -> Dict[str, Any]:
        total = len(self._records)
        fallback_count = sum(1 for r in self._records if r.fallback_used)
        cache_hits = sum(1 for r in self._records if r.cache_hit)
        avg_lat = sum(r.latency_ms for r in self._records) / total if total > 0 else 0
        return {
            "total_requests": total,
            "fallback_rate": (fallback_count / total) if total > 0 else 0.0,
            "cache_hit_rate": (cache_hits / total) if total > 0 else 0.0,
            "avg_latency_ms": round(avg_lat, 1),
        }


acquisition_telemetry = AcquisitionTelemetryCollector()
