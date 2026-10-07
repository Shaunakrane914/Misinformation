"""
Aegis Protocol — Scraper Laboratory Base Contracts & Classifications
=====================================================================
Defines the canonical ScraperLabResult, ErrorClass enum, and base
WebsiteScraperTest class for the offline/CI website testing laboratory.
This module is strictly part of the test & benchmarking laboratory.
Production agents MUST NOT depend on or import this module.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ScraperErrorClass(str, Enum):
    """
    Fine-grained taxonomy of scraper laboratory failures.
    Distinguishes network errors, rate limits, schema changes, and canary deletions.
    """
    NONE = "NONE"
    TRANSPORT_ERROR = "TRANSPORT_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    BLOCKED = "BLOCKED"
    NOT_FOUND = "NOT_FOUND"
    GONE = "GONE"
    CANARY_UNAVAILABLE = "CANARY_UNAVAILABLE"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    PARSE_ERROR = "PARSE_ERROR"
    FIELD_MISSING = "FIELD_MISSING"
    CONTENT_TOO_SHORT = "CONTENT_TOO_SHORT"
    WRONG_SOURCE = "WRONG_SOURCE"
    WRONG_PLATFORM = "WRONG_PLATFORM"
    SSRF_BLOCKED = "SSRF_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass
class SchemaDriftReport:
    """Detailed record of schema drift or field degradation."""
    detected: bool = False
    missing_required_fields: List[str] = field(default_factory=list)
    missing_optional_fields: List[str] = field(default_factory=list)
    type_mismatches: List[str] = field(default_factory=list)
    empty_fields: List[str] = field(default_factory=list)
    unexpected_keys: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected": self.detected,
            "missing_required_fields": self.missing_required_fields,
            "missing_optional_fields": self.missing_optional_fields,
            "type_mismatches": self.type_mismatches,
            "empty_fields": self.empty_fields,
            "unexpected_keys": self.unexpected_keys,
            "notes": self.notes,
        }


@dataclass
class ScraperLabResult:
    """
    Authoritative test contract returned by every website scraper in the laboratory.
    Answers:
      - Did transport and parsing succeed?
      - Are production-required fields present and valid?
      - Did schema drift occur?
      - Was fallback triggered?
      - What are the latency percentiles?
    """
    platform: str
    target_url_or_id: str
    transport_success: bool = False
    parse_success: bool = False
    required_fields_present: bool = False
    optional_fields_present: bool = False
    field_completeness: float = 0.0          # 0.0 to 100.0%
    content_depth: str = "SNIPPET"
    source_correctness: bool = False
    schema_valid: bool = False
    fallback_used: bool = False
    fallback_count: int = 0
    fallback_rate: float = 0.0               # percentage
    latency_ms: int = 0
    error_class: str = ScraperErrorClass.NONE.value
    error_message: str = ""
    backend: str = "unknown"
    retrieval_mode: str = "unknown"
    last_success: Optional[str] = None
    health_status: str = "HEALTHY"           # HEALTHY | DEGRADED | UNHEALTHY
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    schema_drift: SchemaDriftReport = field(default_factory=SchemaDriftReport)
    tested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "target_url_or_id": self.target_url_or_id,
            "transport_success": self.transport_success,
            "parse_success": self.parse_success,
            "required_fields_present": self.required_fields_present,
            "optional_fields_present": self.optional_fields_present,
            "field_completeness": round(self.field_completeness, 2),
            "content_depth": self.content_depth,
            "source_correctness": self.source_correctness,
            "schema_valid": self.schema_valid,
            "fallback_used": self.fallback_used,
            "fallback_count": self.fallback_count,
            "fallback_rate": round(self.fallback_rate, 2),
            "latency_ms": self.latency_ms,
            "error_class": self.error_class,
            "error_message": self.error_message,
            "backend": self.backend,
            "retrieval_mode": self.retrieval_mode,
            "last_success": self.last_success,
            "health_status": self.health_status,
            "extracted_fields": {k: str(v)[:100] for k, v in self.extracted_fields.items()},
            "schema_drift": self.schema_drift.to_dict(),
            "tested_at": self.tested_at,
        }


class WebsiteScraperTest(ABC):
    """
    Abstract base class for all website scraper laboratory tests.
    Each supported website provides an isolated implementation.
    """

    @property
    @abstractmethod
    def platform(self) -> str:
        """Canonical platform name (e.g. 'reddit', 'x', 'youtube')."""
        pass

    @property
    @abstractmethod
    def primary_backend(self) -> str:
        """Primary backend being validated (e.g. 'arctic_shift', 'fxtwitter')."""
        pass

    @property
    @abstractmethod
    def required_fields(self) -> List[str]:
        """Fields strictly required by production contracts."""
        pass

    @property
    def optional_fields(self) -> List[str]:
        """Useful optional fields for enhanced extraction."""
        return []

    @abstractmethod
    def run_canary(self, canary_fixture: Dict[str, Any]) -> ScraperLabResult:
        """
        Execute live or simulated canary test against the platform.
        Evaluates transport, parsing, field presence, schema drift, and latency.
        """
        pass

    def evaluate_schema_drift(
        self,
        extracted: Dict[str, Any],
        expected_types: Optional[Dict[str, type]] = None
    ) -> SchemaDriftReport:
        """
        Check whether extracted dictionary satisfies expected production schema.
        Detects missing fields, empty fields, and type mismatches.
        """
        report = SchemaDriftReport()
        for rf in self.required_fields:
            if rf not in extracted:
                report.missing_required_fields.append(rf)
            elif extracted[rf] is None or extracted[rf] == "":
                report.empty_fields.append(rf)

        for of in self.optional_fields:
            if of not in extracted:
                report.missing_optional_fields.append(of)

        if expected_types:
            for field_name, expected_type in expected_types.items():
                if field_name in extracted and extracted[field_name] is not None:
                    if not isinstance(extracted[field_name], expected_type):
                        report.type_mismatches.append(
                            f"{field_name}: expected {expected_type.__name__}, got {type(extracted[field_name]).__name__}"
                        )

        report.detected = bool(
            report.missing_required_fields or report.type_mismatches or len(report.empty_fields) > 1
        )
        if report.detected:
            report.notes = f"Schema drift detected: missing {report.missing_required_fields}, empty {report.empty_fields}"
        return report
