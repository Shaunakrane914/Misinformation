"""
Aegis Protocol — Unified Report Schema (v3.8.0)
================================================
Single source of truth for the JSON structure returned by ALL five agent
endpoints (Claim Verifier, Trending, Scout, BrandShield, Personal Watch).

Frontend templates bind directly to these field names.  Backend agents must
produce a ``UnifiedReport`` (or use ``ReportBuilder``) — no agent-specific
response shapes at the API boundary.

Key Design Rules
----------------
- ``None`` / ``null`` for fields where no genuine data exists.
- Empty ``list`` (``[]``) for array fields that are structurally required.
- NO hardcoded fallback numbers, fake URLs, or synthetic session IDs.
- ``quality_tensor`` is ``None`` when no real evidence corpus was analysed.
- ``query_telemetry`` counts are derived from ``execution_log`` entries only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


# ─────────────────────────────────────────────────────────────────────────────
# INNER TYPES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UnifiedQualityTensor:
    """
    Six-axis quality tensor for a piece of evidence or an entire report.
    All axes are in [0.0, 1.0].  ``contradiction`` is a *risk* score (higher =
    more contradiction signals detected).
    """
    relevance: Optional[float] = None
    source_quality: Optional[float] = None
    independence: Optional[float] = None
    primary_weight: Optional[float] = None
    freshness: Optional[float] = None
    contradiction: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relevance": self.relevance,
            "source_quality": self.source_quality,
            "independence": self.independence,
            "primary_weight": self.primary_weight,
            "freshness": self.freshness,
            "contradiction": self.contradiction,
        }

    @classmethod
    def from_research_model(cls, qt: Any) -> "UnifiedQualityTensor":
        """Convert a ``research_models.QualityTensor`` to the unified form."""
        if qt is None:
            return cls()
        def _flt(v: Any) -> Optional[float]:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
            return None
        return cls(
            relevance=_flt(getattr(qt, "relevance", None)),
            source_quality=_flt(getattr(qt, "source_quality", None)),
            independence=_flt(getattr(qt, "independence", None)),
            primary_weight=_flt(getattr(qt, "primary_weight", None)),
            freshness=_flt(getattr(qt, "freshness", None)),
            contradiction=_flt(getattr(qt, "contradiction_level", None) if hasattr(qt, "contradiction_level") else getattr(qt, "contradiction", None)),
        )


@dataclass
class RetrievalLineageEntry:
    """One retrieval hop that contributed to fetching an evidence item."""
    query_id: Optional[str] = None
    channel: Optional[str] = None
    retrieval_mode: Optional[str] = None
    backend_id: Optional[str] = None
    is_authenticated: bool = False
    fallback_reason: Optional[str] = None
    retrieved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "channel": self.channel,
            "retrieval_mode": self.retrieval_mode,
            "backend_id": self.backend_id,
            "is_authenticated": self.is_authenticated,
            "fallback_reason": self.fallback_reason,
            "retrieved_at": self.retrieved_at,
        }


@dataclass
class UnifiedEvidenceSource:
    name: Optional[str] = None
    type: Optional[str] = None   # "news" | "social" | "filing" | "video" | "other"
    domain: Optional[str] = None
    is_primary: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "domain": self.domain,
            "is_primary": self.is_primary,
        }


def _safe_str(val: Any) -> Optional[str]:
    """Return stripped string or None, discarding callables and unset mocks."""
    if val is None:
        return None
    if hasattr(val, "_mock_return_value") or hasattr(val, "_mock_name"):
        return None
    if callable(val):
        return None
    s = str(val).strip()
    return s if s else None


@dataclass
class UnifiedEvidenceItem:
    """A single piece of evidence in the unified schema."""
    title: Optional[str] = None
    snippet: Optional[str] = None
    url: Optional[str] = None            # None → UI shows "No source URL"
    timestamp: Optional[str] = None      # ISO publication timestamp
    source: UnifiedEvidenceSource = field(default_factory=UnifiedEvidenceSource)
    quality_tensor: Optional[UnifiedQualityTensor] = None
    retrieval_lineage: List[RetrievalLineageEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
            "timestamp": self.timestamp,
            "source": self.source.to_dict(),
            "quality_tensor": self.quality_tensor.to_dict() if self.quality_tensor else None,
            "retrieval_lineage": [r.to_dict() for r in self.retrieval_lineage],
        }

    @classmethod
    def from_evidence_item(cls, item: Any) -> "UnifiedEvidenceItem":
        """Convert a ``research_models.EvidenceItem`` dataclass or string item."""
        if item is None:
            return cls(title=None, snippet=None)

        if callable(item) and not (hasattr(item, "_mock_name") or hasattr(item, "_mock_return_value")):
            return cls(title=None, snippet=None)

        # If a raw string is passed as evidence (e.g., social handle or headline)
        if isinstance(item, (str, bytes)):
            text = str(item).strip()
            return cls(
                title=text if len(text) < 120 else None,
                snippet=text if len(text) >= 120 else None,
                url=None,
                source=UnifiedEvidenceSource(name="Platform Reference", type="social"),
            )

        raw_url = getattr(item, "canonical_url", None)
        url = _safe_str(raw_url)

        # Build source
        source_name = getattr(item, "source_name", None)
        source = UnifiedEvidenceSource(
            name=_safe_str(source_name),
            type=_infer_source_type(item),
            domain=_safe_str(getattr(item, "source_domain", None)),
            is_primary=bool(getattr(item, "primary_source", False)),
        )

        # Quality tensor
        qt_raw = getattr(item, "quality_tensor", None)
        qt = UnifiedQualityTensor.from_research_model(qt_raw) if (qt_raw is not None and not (callable(qt_raw) and not hasattr(qt_raw, "_mock_name"))) else None

        # Retrieval lineage
        lineage = []
        raw_lineage = getattr(item, "retrieval_lineage", None) or []
        if isinstance(raw_lineage, (list, tuple)):
            for entry in raw_lineage:
                if isinstance(entry, dict):
                    lineage.append(RetrievalLineageEntry(
                        query_id=_safe_str(entry.get("query_id")),
                        channel=_safe_str(entry.get("channel")),
                        retrieval_mode=_safe_str(entry.get("retrieval_mode")),
                        backend_id=_safe_str(entry.get("backend_id")),
                        is_authenticated=bool(entry.get("is_authenticated", False)),
                        fallback_reason=_safe_str(entry.get("fallback_reason")),
                        retrieved_at=_safe_str(entry.get("retrieved_at")),
                    ))

        # If no lineage in the item yet, build one from item fields if valid
        if not lineage:
            q_id = getattr(item, "query_id", None)
            ch = getattr(item, "channel", None)
            mode = getattr(item, "retrieval_mode", None)
            b_id = getattr(item, "native_backend_id", None)
            f_reason = getattr(item, "fallback_reason", None)
            d_at = getattr(item, "discovered_at", None)
            if any(_safe_str(x) is not None for x in [q_id, ch, mode, b_id, f_reason, d_at]):
                lineage.append(RetrievalLineageEntry(
                    query_id=_safe_str(q_id),
                    channel=_safe_str(ch),
                    retrieval_mode=_safe_str(mode),
                    backend_id=_safe_str(b_id),
                    is_authenticated=bool(getattr(item, "is_authenticated", False)),
                    fallback_reason=_safe_str(f_reason),
                    retrieved_at=_safe_str(d_at),
                ))

        return cls(
            title=_safe_str(getattr(item, "title", None)),
            snippet=_safe_str(getattr(item, "snippet", None) or getattr(item, "relevant_excerpt", None)),
            url=url,
            timestamp=_safe_str(getattr(item, "published_at", None)),
            source=source,
            quality_tensor=qt,
            retrieval_lineage=lineage,
        )


@dataclass
class UnifiedEvidenceSet:
    """Three-bucket evidence container (primary / independent / community)."""
    primary: List[UnifiedEvidenceItem] = field(default_factory=list)
    independent: List[UnifiedEvidenceItem] = field(default_factory=list)
    community: List[UnifiedEvidenceItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": [e.to_dict() for e in self.primary],
            "independent": [e.to_dict() for e in self.independent],
            "community": [e.to_dict() for e in self.community],
        }


@dataclass
class TimelineEvent:
    timestamp: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"timestamp": self.timestamp, "description": self.description}


@dataclass
class QueryTelemetry:
    """
    Execution-based query telemetry.
    All counts are derived from ``execution_log`` — never from channel status.
    """
    queries_planned: int = 0
    queries_submitted: int = 0
    queries_started: int = 0
    queries_succeeded: int = 0
    queries_failed: int = 0
    queries_timed_out: int = 0
    queries_auth_required: int = 0
    queries_skipped: int = 0
    execution_log: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_execution_log(
        cls,
        log: List[Any],
        queries_planned: int = 0,
    ) -> "QueryTelemetry":
        """Build telemetry by counting actual log record statuses."""
        submitted = 0
        started = 0
        succeeded = 0
        failed = 0
        timed_out = 0
        auth_required = 0
        skipped = 0
        serialized: List[Dict[str, Any]] = []

        for rec in log:
            if hasattr(rec, "to_dict"):
                d = rec.to_dict()
            elif isinstance(rec, dict):
                d = rec
            else:
                continue

            status = d.get("status", "")
            if status not in ("PLANNED",):
                submitted += 1
            if status in ("SUCCESS", "FAILED", "TIMEOUT", "AUTH_REQUIRED"):
                started += 1
            if status == "SUCCESS":
                succeeded += 1
            elif status == "FAILED":
                failed += 1
            elif status == "TIMEOUT":
                timed_out += 1
            elif status == "AUTH_REQUIRED":
                auth_required += 1
            elif status == "SKIPPED":
                skipped += 1
            serialized.append(d)

        return cls(
            queries_planned=queries_planned or len(log),
            queries_submitted=submitted,
            queries_started=started,
            queries_succeeded=succeeded,
            queries_failed=failed,
            queries_timed_out=timed_out,
            queries_auth_required=auth_required,
            queries_skipped=skipped,
            execution_log=serialized,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queries_planned": self.queries_planned,
            "queries_submitted": self.queries_submitted,
            "queries_started": self.queries_started,
            "queries_succeeded": self.queries_succeeded,
            "queries_failed": self.queries_failed,
            "queries_timed_out": self.queries_timed_out,
            "queries_auth_required": self.queries_auth_required,
            "queries_skipped": self.queries_skipped,
            "execution_log": self.execution_log,
        }


@dataclass
class TrustMetadata:
    quality_tensor: Optional[UnifiedQualityTensor] = None
    independent_source_count: Optional[int] = None
    query_telemetry: QueryTelemetry = field(default_factory=QueryTelemetry)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality_tensor": self.quality_tensor.to_dict() if self.quality_tensor else None,
            "independent_source_count": self.independent_source_count,
            "query_telemetry": self.query_telemetry.to_dict(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# TOP-LEVEL UNIFIED REPORT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UnifiedReport:
    """
    Root report object shared by all five Aegis agent endpoints.

    The ``to_dict()`` method produces the canonical JSON that the frontend
    reads.  Every field that could be ``None`` must be handled in the UI
    template using the mandatory placeholder strings defined in the spec:

        None numeric  → "—"  (em dash)
        None string   → "Unknown"
        Missing URL   → "No source URL"
        Missing ID    → "Not available"
    """
    # Core narrative
    summary: Optional[str] = None
    findings: List[str] = field(default_factory=list)

    # Evidence
    evidence: UnifiedEvidenceSet = field(default_factory=UnifiedEvidenceSet)

    # Contradictions and changes
    disagreements: List[str] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)

    # Chronology
    timeline: List[TimelineEvent] = field(default_factory=list)

    # Provenance / trust
    trust: TrustMetadata = field(default_factory=TrustMetadata)

    # Guidance
    next_steps: List[str] = field(default_factory=list)

    # Internal metadata (not rendered in report sections)
    agent: Optional[str] = None          # e.g. "claim_verifier"
    query: Optional[str] = None          # original user query
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "findings": self.findings,
            "evidence": self.evidence.to_dict(),
            "disagreements": self.disagreements,
            "changes": self.changes,
            "timeline": [t.to_dict() for t in self.timeline],
            "trust": self.trust.to_dict(),
            "next_steps": self.next_steps,
            "_meta": {
                "agent": self.agent,
                "query": self.query,
                "generated_at": self.generated_at,
                "schema_version": "3.8.0",
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _infer_source_type(item: Any) -> Optional[str]:
    """Infer a human-readable source type from an EvidenceItem."""
    channel = (getattr(item, "channel", "") or "").lower()
    tier = (getattr(item, "source_tier", "") or "").lower()
    if "filing" in tier or "official" in tier or "regulatory" in tier:
        return "filing"
    if channel in ("reddit", "twitter", "x", "instagram", "youtube", "social"):
        return "social"
    if channel in ("news", "rss", "web"):
        return "news"
    if "video" in channel:
        return "video"
    return "other"


def classify_evidence_items(
    items: List[Any],
) -> UnifiedEvidenceSet:
    """
    Sort a flat list of ``EvidenceItem`` objects into the three evidence buckets.

    Bucket rules (in order of precedence):
    1.  ``primary_source=True`` or ``source_role=PRIMARY``  → primary
    2.  ``source_role`` in (SECONDARY, DISCOVERY, COMMENTARY, AGGREGATOR)
        AND channel NOT in social platforms → independent
    3.  Everything else → community
    """
    from backend.services.research.research_models import SourceRole
    SOCIAL_CHANNELS = {"reddit", "twitter", "x", "instagram", "youtube", "tiktok"}

    evset = UnifiedEvidenceSet()
    for raw in items:
        unified = UnifiedEvidenceItem.from_evidence_item(raw)
        role = (getattr(raw, "source_role", "") or "").upper()
        channel = (getattr(raw, "channel", "") or "").lower()
        is_primary = getattr(raw, "primary_source", False) or role == SourceRole.PRIMARY.value

        if is_primary:
            evset.primary.append(unified)
        elif channel in SOCIAL_CHANNELS or role == SourceRole.COMMUNITY.value:
            evset.community.append(unified)
        else:
            evset.independent.append(unified)

    return evset


def build_trust_metadata(
    corpus: Any,
    execution_log: Optional[List[Any]] = None,
    queries_planned: int = 0,
) -> TrustMetadata:
    """
    Construct ``TrustMetadata`` from a ResearchCorpus and execution log.

    ``corpus`` may be ``None`` (when no research was performed); in that case
    ``quality_tensor`` and ``independent_source_count`` are left as ``None``.
    """
    qt: Optional[UnifiedQualityTensor] = None
    ind_count: Optional[int] = None

    if corpus is not None:
        raw_qt = getattr(corpus, "quality_tensor", None)
        if raw_qt is not None:
            qt = UnifiedQualityTensor.from_research_model(raw_qt)

        ind_groups = getattr(corpus, "independent_source_groups", None)
        if ind_groups is not None:
            ind_count = len(ind_groups) if hasattr(ind_groups, "__len__") else None

    telemetry = QueryTelemetry.from_execution_log(
        log=execution_log or [],
        queries_planned=queries_planned,
    )

    return TrustMetadata(
        quality_tensor=qt,
        independent_source_count=ind_count,
        query_telemetry=telemetry,
    )
