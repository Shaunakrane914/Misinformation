"""
Aegis Protocol — Scraper Laboratory Reporters
=============================================
Formats and prints health, benchmark, schema, and operational reports.
Renders truthful backend attributions, explicit live/offline separation,
and delta diagnostics (Section 3, 7, 8, 16).
"""

from typing import List, Optional
from scrapers.base import ScraperLabResult


def format_health_report(results: List[ScraperLabResult]) -> str:
    """
    Produce structured human-readable health report with strict live/offline separation.
    """
    lines: List[str] = [
        "AEGIS SCRAPER HEALTH & TRUTHFULNESS AUDIT",
        "=" * 48,
        "",
    ]

    for res in results:
        lines.append(res.platform.upper())
        lines.append(f"Adapter:                {res.adapter_name or 'PlatformAdapter'}")
        lines.append(f"Declared backend:       {res.declared_backend}")
        lines.append(f"Actual backend:         {res.actual_backend}")
        lines.append(f"Probe method:           {res.probe_method}")
        lines.append(f"Production path:        {'VERIFIED' if res.production_path_verified else 'AUXILIARY'}")
        lines.append(f"Probe mode:             {res.probe_mode.upper()}")
        lines.append(f"Overall status:         {res.health_status}")
        lines.append("")

        if res.probe_mode == "live":
            lines.append("LIVE PROBE:")
            lines.append(f"  Transport:            {'PASS' if res.live_transport_success else 'FAIL'}")
            lines.append(f"  Parse success:        {'PASS' if res.live_parse_success else 'FAIL'}")
            lines.append(f"  Latency:              {res.live_latency_ms} ms")
            lines.append(f"  Field completeness:   {res.live_field_completeness:.1f}%")
            if res.fallback_used:
                lines.append(f"  Fallback triggered:   YES ({res.fallback_reason or 'mirror_degraded'})")
            if res.error_class != "NONE":
                lines.append(f"  Error class:          {res.error_class}")
                if res.error_message:
                    lines.append(f"  Error message:        {res.error_message}")
            lines.append("")

        lines.append("OFFLINE CONTRACT VALIDATION:")
        lines.append(f"  Schema valid:         {'PASS' if res.fixture_schema_valid or res.schema_valid else 'FAIL'}")
        lines.append(f"  Contract valid:       {'PASS' if res.fixture_contract_valid or not res.schema_drift.detected else 'FAIL'}")
        lines.append(f"  Completeness:         {res.fixture_field_completeness or res.field_completeness:.1f}%")
        lines.append("")

        drift_str = "DETECTED" if res.schema_drift.detected else "NONE"
        lines.append(f"Schema drift:           {drift_str}")
        if res.schema_drift.detected and res.schema_drift.missing_required_fields:
            lines.append(f"  Missing fields:       {res.schema_drift.missing_required_fields}")
        lines.append(f"Tested at:              {res.tested_at}")
        lines.append("-" * 48)
        lines.append("")

    return "\n".join(lines)


def format_summary_table(results: List[ScraperLabResult]) -> str:
    """Produce concise summary table of all website tests."""
    header = f"{'PLATFORM':<12} {'BACKEND':<18} {'ACTUAL':<18} {'STATUS':<10} {'COMPLETENESS':<13} {'LATENCY':<9} {'DRIFT':<6}"
    sep = "-" * len(header)
    rows = [header, sep]
    for r in results:
        drift = "DRIFT" if r.schema_drift.detected else "OK"
        rows.append(
            f"{r.platform:<12} {r.declared_backend:<18} {r.actual_backend:<18} {r.health_status:<10} {r.field_completeness:5.1f}%{'':<7} {r.latency_ms:4d} ms{'':<2} {drift:<6}"
        )
    return "\n".join(rows)
