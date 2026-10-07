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
      - Are live health and offline fixture validation strictly separated?
      - Is the reported backend truthful to the actual production adapter exercised?
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

    # Truthful Backend & Production Adapter Verification (Section 3)
    declared_backend: str = ""
    actual_backend: str = ""
    adapter_name: str = ""
    probe_method: str = "production_adapter"  # "production_adapter" | "auxiliary_probe"
    production_path_verified: bool = True

    # Live vs. Offline Contract Separation (Section 8)
    probe_mode: str = "live"                  # "live" | "offline"
    live_transport_success: bool = False
    live_parse_success: bool = False
    live_field_completeness: float = 0.0
    live_latency_ms: int = 0
    fixture_contract_valid: bool = False
    fixture_field_completeness: float = 0.0
    fixture_schema_valid: bool = False

    # Policy D / Rescue Diagnostics (Section 4)
    browser_used: bool = False
    fallback_reason: Optional[str] = None

    # Network Telemetry (Section 15)
    http_requests: int = 0
    http_failures: int = 0
    status_codes: List[int] = field(default_factory=list)
    timeout_count: int = 0
    rate_limit_count: int = 0
    agent_contracts: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.declared_backend:
            self.declared_backend = self.backend
        if not self.actual_backend:
            self.actual_backend = self.backend
        if self.probe_mode == "live":
            self.live_transport_success = self.transport_success
            self.live_parse_success = self.parse_success
            self.live_field_completeness = self.field_completeness
            self.live_latency_ms = self.latency_ms

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
            "declared_backend": self.declared_backend,
            "actual_backend": self.actual_backend,
            "adapter_name": self.adapter_name,
            "probe_method": self.probe_method,
            "production_path_verified": self.production_path_verified,
            "probe_mode": self.probe_mode,
            "live_transport_success": self.live_transport_success,
            "live_parse_success": self.live_parse_success,
            "live_field_completeness": round(self.live_field_completeness, 2),
            "live_latency_ms": self.live_latency_ms,
            "fixture_contract_valid": self.fixture_contract_valid,
            "fixture_field_completeness": round(self.fixture_field_completeness, 2),
            "fixture_schema_valid": self.fixture_schema_valid,
            "browser_used": self.browser_used,
            "fallback_reason": self.fallback_reason,
            "http_requests": self.http_requests,
            "http_failures": self.http_failures,
            "status_codes": self.status_codes,
            "timeout_count": self.timeout_count,
            "rate_limit_count": self.rate_limit_count,
            "agent_contracts": self.agent_contracts,
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
    def run_canary(
        self,
        canary_fixture: Dict[str, Any],
        live_network: bool = True
    ) -> ScraperLabResult:
        """
        Execute canary test against the platform.
        When live_network is True, conducts actual HTTP network probe.
        When live_network is False, validates using offline fixture.
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
