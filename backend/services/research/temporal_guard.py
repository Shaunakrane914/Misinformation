"""
Aegis Protocol — Trending Temporal Relevance & Freshness Guard
==============================================================
Enforces strict temporal eligibility, timestamp normalization, and freshness gating
specifically designed for real-time trend discovery and intelligence.

Guarantees & Invariants:
1. Canonical Timestamp Normalization:
   Normalizes ISO 8601 (with any timezone offset), RFC 2822, UNIX epochs,
   and relative time expressions into timezone-aware UTC datetimes.
2. Temporal Provenance Separation:
   Strictly distinguishes:
     - original publication time (published_at)
     - editorial update time (updated_at)
     - rediscovery time (discovered_at)
     - acquisition/fetch time (acquired_at / retrieved_at)
     - wire mirror time (mirror_at / syndicated_at)
   Discovery or acquisition times NEVER substitute for publication time.
3. Explicit Trending Freshness Window:
   Configurable (default: 48.0 hours). Items published outside the window
   are marked TEMPORAL_STALE and rejected from active trending rankings.
4. Transparent Missing & Future Timestamp Handling:
   - Missing/unparseable timestamps are rejected conservatively (TEMPORAL_MISSING_TIMESTAMP).
   - Future-dated timestamps (>1 hour ahead of reference time) are rejected
     (TEMPORAL_FUTURE_DATED) and cannot gain recency advantage.
5. Mirror Syndication & Update Policy:
   - Syndicated old stories with fresh mirror timestamps remain stale based on original date.
   - Recent updates to old articles follow an explicit update policy (default: rejected as
     active new trend, preserved as historical context).
6. Timezone Invariance:
   All comparisons occur in UTC epoch space. Local offsets (+08:00, -05:00) yield identical
   eligibility decisions.
7. Orthogonal to Semantic Scoring:
   Neural cross-encoders or high semantic overlap cannot override a failed temporal gate.
"""

import os
import re
import math
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
import email.utils

logger = logging.getLogger("TemporalGuard")

# Configurable defaults via environment
DEFAULT_TRENDING_WINDOW_HOURS = float(os.getenv("AEGIS_TRENDING_WINDOW_HOURS", "48.0"))
DEFAULT_RECENCY_HALF_LIFE_HOURS = float(os.getenv("AEGIS_RECENCY_HALF_LIFE_HOURS", "24.0"))
MAX_FUTURE_SKEW_TOLERANCE_HOURS = 1.0


@dataclass
class TemporalAssessment:
    """
    Forensic assessment of candidate temporal eligibility.
    """
    is_eligible: bool
    status: str  # FRESH | STALE | MISSING_TIMESTAMP | FUTURE_DATED | UPDATED_HISTORICAL_ACCEPTED | UPDATED_HISTORICAL_REJECTED | SYNDICATED_STALE
    published_at_utc: Optional[str] = None
    updated_at_utc: Optional[str] = None
    discovered_at_utc: Optional[str] = None
    age_hours: Optional[float] = None
    recency_score: float = 0.0
    context_only: bool = False
    rejection_reason: Optional[str] = None
    rejection_stage: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_eligible": self.is_eligible,
            "status": self.status,
            "published_at_utc": self.published_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "discovered_at_utc": self.discovered_at_utc,
            "age_hours": round(self.age_hours, 2) if self.age_hours is not None else None,
            "recency_score": round(self.recency_score, 4),
            "context_only": self.context_only,
            "rejection_reason": self.rejection_reason,
            "rejection_stage": self.rejection_stage,
            "details": self.details,
        }


class TemporalGuard:
    """
    Production temporal relevance and freshness guard.
    """

    def __init__(
        self,
        default_window_hours: float = DEFAULT_TRENDING_WINDOW_HOURS,
        half_life_hours: float = DEFAULT_RECENCY_HALF_LIFE_HOURS,
    ):
        self.default_window_hours = default_window_hours
        self.half_life_hours = half_life_hours

    def normalize_timestamp(
        self,
        val: Any,
        reference_time: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Normalize arbitrary timestamp inputs to a timezone-aware datetime in UTC.

        Supports:
        - datetime objects (timezone-aware or naive; naive treated as UTC)
        - ISO 8601 strings (with Z, offsets like +08:00, or naive)
        - RFC 2822 / HTTP date strings (e.g. 'Wed, 21 Apr 2021 08:30:00 GMT')
        - UNIX epoch numbers (int, float, or numeric string in seconds or ms)
        - Relative human strings ('X hours ago', 'yesterday', 'X days ago', 'X mins ago')
        """
        if val is None:
            return None

        # 1. Datetime object
        if isinstance(val, datetime):
            if val.tzinfo is None:
                return val.replace(tzinfo=timezone.utc)
            return val.astimezone(timezone.utc)

        # 2. Numeric epoch
        if isinstance(val, (int, float)):
            try:
                # Milliseconds detection (> year 3000 in seconds is > 3.2e10)
                sec = val / 1000.0 if val > 1e11 else float(val)
                return datetime.fromtimestamp(sec, tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                return None

        val_str = str(val).strip()
        if not val_str:
            return None

        # Numeric string epoch
        if re.match(r'^\d+(\.\d+)?$', val_str):
            try:
                numeric_val = float(val_str)
                sec = numeric_val / 1000.0 if numeric_val > 1e11 else numeric_val
                return datetime.fromtimestamp(sec, tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                pass

        # 3. Relative human time expressions
        ref = reference_time or datetime.now(timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)

        lower_str = val_str.lower()
        if any(tok in lower_str for tok in ["ago", "yesterday", "today", "just now"]):
            if "just now" in lower_str or "today" in lower_str:
                return ref
            if "yesterday" in lower_str:
                return ref - timedelta(days=1)

            m_hours = re.search(r'(\d+)\s*(?:hour|hr)s?\s*ago', lower_str)
            if m_hours:
                return ref - timedelta(hours=float(m_hours.group(1)))

            m_mins = re.search(r'(\d+)\s*(?:minute|min)s?\s*ago', lower_str)
            if m_mins:
                return ref - timedelta(minutes=float(m_mins.group(1)))

            m_days = re.search(r'(\d+)\s*days?\s*ago', lower_str)
            if m_days:
                return ref - timedelta(days=float(m_days.group(1)))

            m_weeks = re.search(r'(\d+)\s*weeks?\s*ago', lower_str)
            if m_weeks:
                return ref - timedelta(days=float(m_weeks.group(1)) * 7)

            m_months = re.search(r'(\d+)\s*months?\s*ago', lower_str)
            if m_months:
                return ref - timedelta(days=float(m_months.group(1)) * 30)

            m_years = re.search(r'(\d+)\s*years?\s*ago', lower_str)
            if m_years:
                return ref - timedelta(days=float(m_years.group(1)) * 365)

        # 4. Standard ISO 8601 parsing via fromisoformat
        try:
            # Handle trailing 'Z'
            iso_cand = val_str
            if iso_cand.endswith('Z') or iso_cand.endswith('z'):
                iso_cand = iso_cand[:-1] + "+00:00"
            dt = datetime.fromisoformat(iso_cand)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass

        # 5. RFC 2822 / HTTP format (e.g. RSS/Atom dates)
        try:
            dt = email.utils.parsedate_to_datetime(val_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError):
            pass

        # 6. Common legacy formats
        legacy_patterns = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%b %d, %Y",
            "%B %d, %Y",
            "%Y%m%d%H%M%S",
        ]
        for pat in legacy_patterns:
            try:
                dt = datetime.strptime(val_str, pat)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        logger.debug("Failed to parse timestamp string: '%s'", val_str)
        return None

    def extract_timestamps(self, item: Any) -> Dict[str, Optional[datetime]]:
        """
        Extract and distinguish all relevant timestamps from an item:
        - original publication time
        - update time
        - rediscovery time
        - acquisition / retrieval time
        - mirror / syndication time
        """
        def _get(field_names: List[str]) -> Any:
            for fn in field_names:
                # Check attribute
                if hasattr(item, fn):
                    val = getattr(item, fn)
                    if val:
                        return val
                # Check dict
                if isinstance(item, dict) and fn in item and item[fn]:
                    return item[fn]
                # Check nested metadata
                meta = getattr(item, "metadata", None) or (item.get("metadata") if isinstance(item, dict) else None)
                if isinstance(meta, dict) and fn in meta and meta[fn]:
                    return meta[fn]
                # Check raw_metadata
                raw_meta = getattr(item, "raw_metadata", None) or (item.get("raw_metadata") if isinstance(item, dict) else None)
                if isinstance(raw_meta, dict) and fn in raw_meta and raw_meta[fn]:
                    return raw_meta[fn]
            return None

        # Original publication fields
        pub_raw = _get([
            "original_published_at", "original_publication_date", "original_date",
            "published_at", "published", "pubdate", "date_published", "created_at"
        ])

        # Editorial update fields
        upd_raw = _get([
            "updated_at", "updated", "modified_at", "last_modified", "last_updated", "date_modified"
        ])

        # Rediscovery fields
        disc_raw = _get(["discovered_at", "discovery_time"])

        # Acquisition / fetch fields
        acq_raw = _get(["acquired_at", "retrieved_at", "fetch_time", "fetched_at"])

        # Mirror / syndication fields
        mirror_raw = _get(["mirror_timestamp", "syndicated_at", "mirror_at", "wire_date"])

        pub_dt = self.normalize_timestamp(pub_raw)
        upd_dt = self.normalize_timestamp(upd_raw)
        disc_dt = self.normalize_timestamp(disc_raw)
        acq_dt = self.normalize_timestamp(acq_raw)
        mirror_dt = self.normalize_timestamp(mirror_raw)

        # Detect syndicated mirrors of historical articles from title/snippet
        title_text = _get(["title", "headline"]) or ""
        snippet_text = _get(["snippet", "content", "relevant_excerpt"]) or ""
        combined_text = f"{title_text} {snippet_text}"

        is_explicit_mirror = bool(re.search(r'\b(syndicated mirror|wire mirror|mirror copy|republished|syndicated wire copy)\b', combined_text, re.IGNORECASE))
        archived_year_match = re.search(r'\b(?:archived|originally published(?:\s+in)?|dating from|from)\s+(\d{4})\b', combined_text, re.IGNORECASE)

        if (is_explicit_mirror or archived_year_match) and pub_dt:
            if archived_year_match:
                extracted_year = int(archived_year_match.group(1))
                if extracted_year <= 2024 and pub_dt.year > extracted_year:
                    # Treat the older year as the true original publication date
                    orig_dt = datetime(extracted_year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
                    mirror_dt = pub_dt
                    pub_dt = orig_dt

        return {
            "published_dt": pub_dt,
            "updated_dt": upd_dt,
            "discovered_dt": disc_dt,
            "acquired_dt": acq_dt,
            "mirror_dt": mirror_dt,
        }

    def compute_recency_score(
        self,
        age_hours: Optional[float],
        half_life_hours: Optional[float] = None
    ) -> float:
        """
        Compute continuous exponential decay recency score:
        S = exp(-ln(2) / half_life * age_hours)
        """
        if age_hours is None:
            return 0.05

        if age_hours < 0:
            # Future-dated penalty
            return 0.0

        hl = half_life_hours or self.half_life_hours
        decay_constant = math.log(2) / max(1.0, hl)
        score = math.exp(-decay_constant * age_hours)
        return round(max(0.0, min(1.0, score)), 4)

    def evaluate(
        self,
        candidate: Any,
        reference_time: Optional[datetime] = None,
        window_hours: Optional[float] = None,
        allow_updated: bool = False,
    ) -> TemporalAssessment:
        """
        Evaluate candidate for Trending temporal eligibility.

        Args:
            candidate: EvidenceItem, EvidenceFragment, CandidateSource, or dict.
            reference_time: Explicit baseline time (defaults to datetime.now(timezone.utc)).
            window_hours: Max allowed age for active trending (default: 48h).
            allow_updated: If True, recent updates can qualify a historical article.
                           If False (default for Trending), old articles remain ineligible.

        Returns:
            TemporalAssessment with eligibility boolean, structured reasons, and telemetry.
        """
        win_hrs = window_hours if window_hours is not None else self.default_window_hours
        ref_dt = reference_time or datetime.now(timezone.utc)
        if ref_dt.tzinfo is None:
            ref_dt = ref_dt.replace(tzinfo=timezone.utc)

        ts = self.extract_timestamps(candidate)
        pub_dt = ts["published_dt"]
        upd_dt = ts["updated_dt"]
        disc_dt = ts["discovered_dt"]
        acq_dt = ts["acquired_dt"]
        mirror_dt = ts["mirror_dt"]

        pub_iso = pub_dt.isoformat() if pub_dt else None
        upd_iso = upd_dt.isoformat() if upd_dt else None
        disc_iso = disc_dt.isoformat() if disc_dt else None

        # Check for syndicated mirror: if candidate has an original publication date and
        # a fresh mirror date, the original publication date MUST govern.
        is_wire_mirror = False
        if mirror_dt and pub_dt:
            # If mirror is significantly newer than original publication
            if (mirror_dt - pub_dt).total_seconds() > 3600.0 * 24.0:
                is_wire_mirror = True

        # Rule 1: Missing or unparseable publication timestamp
        if pub_dt is None:
            return TemporalAssessment(
                is_eligible=False,
                status="MISSING_TIMESTAMP",
                published_at_utc=None,
                updated_at_utc=upd_iso,
                discovered_at_utc=disc_iso,
                age_hours=None,
                recency_score=0.05,
                context_only=True,
                rejection_reason="TEMPORAL_MISSING_TIMESTAMP: Candidate lacks a verifiable publication timestamp",
                rejection_stage="TEMPORAL_GATE_ERROR",
                details={"window_hours": win_hrs, "discovered_at": disc_iso},
            )

        # Calculate age relative to reference time
        age_seconds = (ref_dt - pub_dt).total_seconds()
        age_hours = age_seconds / 3600.0

        # Rule 2: Future-dated timestamp (> MAX_FUTURE_SKEW_TOLERANCE_HOURS)
        if age_seconds < -3600.0 * MAX_FUTURE_SKEW_TOLERANCE_HOURS:
            hours_future = abs(age_seconds) / 3600.0
            return TemporalAssessment(
                is_eligible=False,
                status="FUTURE_DATED",
                published_at_utc=pub_iso,
                updated_at_utc=upd_iso,
                discovered_at_utc=disc_iso,
                age_hours=age_hours,
                recency_score=0.0,
                context_only=False,
                rejection_reason=f"TEMPORAL_FUTURE_DATED: Timestamp '{pub_iso}' is {hours_future:.1f}h in the future",
                rejection_stage="TEMPORAL_GATE_ERROR",
                details={"window_hours": win_hrs, "future_hours": round(hours_future, 2)},
            )

        # Clamp minor negative skew (e.g. < 1 hr ahead due to host clock differences)
        effective_age_hours = max(0.0, age_hours)
        rec_score = self.compute_recency_score(effective_age_hours)

        # Rule 3: Syndicated old story with fresh mirror timestamp
        if is_wire_mirror and effective_age_hours > win_hrs:
            return TemporalAssessment(
                is_eligible=False,
                status="SYNDICATED_STALE",
                published_at_utc=pub_iso,
                updated_at_utc=upd_iso,
                discovered_at_utc=disc_iso,
                age_hours=effective_age_hours,
                recency_score=rec_score,
                context_only=True,
                rejection_reason=(
                    f"TEMPORAL_SYNDICATED_STALE: Original story published {effective_age_hours:.1f}h ago "
                    f"exceeds Trending window ({win_hrs}h); fresh syndication mirror does not confer freshness"
                ),
                rejection_stage="TEMPORAL_GATE_ERROR",
                details={"window_hours": win_hrs, "mirror_at": mirror_dt.isoformat() if mirror_dt else None},
            )

        # Rule 4: Editorial update to an old story
        if effective_age_hours > win_hrs and upd_dt is not None:
            update_age_seconds = (ref_dt - upd_dt).total_seconds()
            update_age_hours = max(0.0, update_age_seconds / 3600.0)

            if update_age_hours <= win_hrs:
                if allow_updated:
                    return TemporalAssessment(
                        is_eligible=True,
                        status="UPDATED_HISTORICAL_ACCEPTED",
                        published_at_utc=pub_iso,
                        updated_at_utc=upd_iso,
                        discovered_at_utc=disc_iso,
                        age_hours=effective_age_hours,
                        recency_score=self.compute_recency_score(update_age_hours),
                        context_only=False,
                        rejection_reason=None,
                        details={
                            "window_hours": win_hrs,
                            "is_update": True,
                            "original_age_hours": round(effective_age_hours, 1),
                            "update_age_hours": round(update_age_hours, 1),
                        },
                    )
                else:
                    return TemporalAssessment(
                        is_eligible=False,
                        status="UPDATED_HISTORICAL_REJECTED",
                        published_at_utc=pub_iso,
                        updated_at_utc=upd_iso,
                        discovered_at_utc=disc_iso,
                        age_hours=effective_age_hours,
                        recency_score=rec_score,
                        context_only=True,
                        rejection_reason=(
                            f"TEMPORAL_STALE_HISTORICAL_UPDATE: Original article published {effective_age_hours:.1f}h ago "
                            f"exceeds Trending window ({win_hrs}h). Updates to historical events do not qualify as new active trends."
                        ),
                        rejection_stage="TEMPORAL_GATE_ERROR",
                        details={
                            "window_hours": win_hrs,
                            "original_age_hours": round(effective_age_hours, 1),
                            "update_age_hours": round(update_age_hours, 1),
                        },
                    )

        # Rule 5: Stale article exceeding the Trending window
        if effective_age_hours > win_hrs:
            return TemporalAssessment(
                is_eligible=False,
                status="STALE",
                published_at_utc=pub_iso,
                updated_at_utc=upd_iso,
                discovered_at_utc=disc_iso,
                age_hours=effective_age_hours,
                recency_score=rec_score,
                context_only=True,
                rejection_reason=(
                    f"TEMPORAL_STALE: Published {effective_age_hours:.1f}h ago exceeds Trending "
                    f"freshness window ({win_hrs}h)"
                ),
                rejection_stage="TEMPORAL_GATE_ERROR",
                details={"window_hours": win_hrs},
            )

        # Rule 6: Fresh article within window
        return TemporalAssessment(
            is_eligible=True,
            status="FRESH",
            published_at_utc=pub_iso,
            updated_at_utc=upd_iso,
            discovered_at_utc=disc_iso,
            age_hours=effective_age_hours,
            recency_score=rec_score,
            context_only=False,
            rejection_reason=None,
            details={"window_hours": win_hrs},
        )


# Global singleton
temporal_guard = TemporalGuard()
