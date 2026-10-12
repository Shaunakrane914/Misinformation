"""Summarize observed Phase 8 acquisition richness without re-fetching sources.

Inputs are immutable Phase 8A/8B probe JSONL files. This measures normalized
evidence fields only; it cannot establish which raw provider fields were present
or whether an omitted field was available upstream. Output must be a new path.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

from run_phase8_live_acquisition_audit import (
    PROTECTED_OPERATIONS,
    SUCCESS_CLASSIFICATIONS,
)


def summarize(paths: list[Path]) -> dict:
    records: list[dict] = []
    for path in paths:
        with path.open(encoding="utf-8") as source:
            records.extend(json.loads(line) for line in source if line.strip())

    # The final provided probe set supersedes earlier observations only for
    # matching operation/scenario pairs. Keep all other scenarios.
    selected = {}
    for record in records:
        if record.get("operation") in PROTECTED_OPERATIONS:
            selected[(record["operation"], record["scenario"])] = record

    by_operation = defaultdict(list)
    for record in selected.values():
        by_operation[record["operation"]].append(record)

    operations = {}
    for operation in PROTECTED_OPERATIONS:
        probes = by_operation[operation]
        successful = [
            probe for probe in probes
            if probe.get("classification") in SUCCESS_CLASSIFICATIONS
            and probe.get("live_verified") is True
        ]
        samples = [
            sample for probe in successful
            for sample in probe.get("provenance", {}).get("normalized_evidence_samples", [])
        ]
        field_names = ("title", "canonical_url", "published", "backend_id", "content_depth")
        populated = {
            field: sum(bool(sample.get(field)) for sample in samples)
            for field in field_names
        }
        latencies = [
            probe["latency_ms"] for probe in probes
            if isinstance(probe.get("latency_ms"), (int, float))
        ]
        total_items = sum(probe.get("item_count") or 0 for probe in successful)
        operations[operation] = {
            "scenario_count": len(probes),
            "live_success_count": len(successful),
            "live_success_rate": round(len(successful) / len(probes), 3) if probes else None,
            "sampled_item_count": total_items,
            "normalized_sample_count": len(samples),
            "normalized_field_population": populated,
            "normalized_field_population_rate": {
                field: round(count / len(samples), 3) if samples else None
                for field, count in populated.items()
            },
            "mean_relevant_chars_per_successful_item": round(
                sum(probe.get("relevant_text_chars") or 0 for probe in successful) / total_items
            ) if total_items else None,
            "median_probe_latency_ms": round(median(latencies)) if latencies else None,
            "classification_counts": dict(Counter(probe.get("classification") for probe in probes)),
            "content_depth_counts": dict(Counter(
                depth for probe in successful for depth in probe.get("content_depths", [])
            )),
            "pagination_observations": sorted({
                probe.get("pagination_coverage") or "UNVERIFIED" for probe in probes
            }),
            "limits": (
                "Normalized samples only; source-response field availability and "
                "whole-page completeness are not measurable from these artifacts."
            ),
        }

    return {
        "schema_version": "phase8-extraction-summary-v1",
        "source_probe_files": [path.as_posix() for path in paths],
        "method": "Observed live probe records; latest matching operation/scenario wins.",
        "limitations": [
            "Only normalized sample fields are scored; raw provider field completeness is unverified.",
            "Sample size is small and source-dependent, not a continuous health guarantee.",
            "No request is made by this summarizer and no inferred data fills missing fields.",
        ],
        "operations": operations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-records", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output path already exists; preserve historical extraction evidence")
    summary = summarize(args.probe_records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as target:
        json.dump(summary, target, indent=2, ensure_ascii=False)
        target.write("\n")
    print(args.output)
    print(f"PROTECTED_OPERATIONS={len(summary['operations'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
