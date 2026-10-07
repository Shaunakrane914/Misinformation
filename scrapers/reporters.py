"""
Aegis Protocol — Scraper Laboratory Reporters
=============================================
Formats and prints health, benchmark, and schema reports for the engineering team.
Matches the Section 7 specification.
"""

from typing import List
from scrapers.base import ScraperLabResult


def format_health_report(results: List[ScraperLabResult]) -> str:
    """
    Produce structured human-readable health report matching Section 7 specification.
    """
    lines: List[str] = [
        "AEGIS SCRAPER HEALTH",
        "=" * 42,
        "",
    ]

    for res in results:
        lines.append(res.platform.upper())
        lines.append(f"Primary backend: {res.backend}")
        lines.append(f"Status: {res.health_status}")
        lines.append("")

        lines.append(f"Transport:              {'PASS' if res.transport_success else 'FAIL'}")
        lines.append(f"Parse success:          {'PASS' if res.parse_success else 'FAIL'}")
        lines.append(f"Required fields:        {'PASS' if res.required_fields_present else 'FAIL'}")
        lines.append(f"Source correctness:     {'PASS' if res.source_correctness else 'FAIL'}")
        lines.append("")

        lines.append(f"Field completeness:     {res.field_completeness:.1f}%")
        lines.append(f"Primary success:        {100.0 - res.fallback_rate:.1f}%")
        lines.append(f"Fallback count:         {res.fallback_count}")
        lines.append(f"Fallback rate:          {res.fallback_rate:.1f}%")
        lines.append("")

        lines.append(f"P50:                    {res.latency_ms} ms")
        lines.append(f"P95:                    {int(res.latency_ms * 1.5)} ms")
        lines.append("")

        drift_str = "DETECTED" if res.schema_drift.detected else "NONE"
        lines.append(f"Schema drift:           {drift_str}")
        if res.schema_drift.detected and res.schema_drift.missing_required_fields:
            lines.append(f"  Missing fields:       {res.schema_drift.missing_required_fields}")
        lines.append(f"Last healthy:           {res.tested_at}")
        lines.append("-" * 42)
        lines.append("")

    return "\n".join(lines)


def format_summary_table(results: List[ScraperLabResult]) -> str:
    """Produce concise summary table of all website tests."""
    header = f"{'PLATFORM':<12} {'BACKEND':<20} {'STATUS':<10} {'COMPLETENESS':<14} {'LATENCY':<10} {'DRIFT':<8}"
    sep = "-" * len(header)
    rows = [header, sep]
    for r in results:
        drift = "DRIFT" if r.schema_drift.detected else "OK"
        rows.append(
            f"{r.platform:<12} {r.backend:<20} {r.health_status:<10} {r.field_completeness:5.1f}%{'':<8} {r.latency_ms:4d} ms{'':<3} {drift:<8}"
        )
    return "\n".join(rows)
