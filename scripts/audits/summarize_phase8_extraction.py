"""Summarize observed Phase 8 acquisition richness without re-fetching sources.

Inputs are immutable Phase 8A/8B probe JSONL files. This measures normalized
evidence fields and, where retained, parsed adapter-item field names. Neither
is a complete raw provider schema. Output must be a new path.
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


# Minimum useful fields for the evidence type, not every theoretical provider
# field. Optional fields remain measured (and may legitimately be absent).
IMPORTANT_FIELDS = {
    "github.read": ("title", "canonical_url", "author", "content", "metadata.readme_sha"),
    "github.issues": ("title", "canonical_url", "author", "published", "provider.number", "provider.state"),
    "github.prs": ("title", "canonical_url", "author", "published", "provider.number", "provider.state"),
    "github.commits": ("title", "canonical_url", "author", "published", "provider.sha"),
    "github.releases": ("title", "canonical_url", "published", "provider.tag_name"),
    "youtube.read": ("title", "canonical_url", "video.video_id", "video.channel", "video.upload_date"),
    "youtube.transcript": ("canonical_url", "content", "metadata.segments", "metadata.caption_language"),
    "youtube.comments": ("canonical_url", "author", "content", "metadata.comment_id"),
    "v2ex.latest": ("title", "canonical_url", "author", "metadata.topic_id", "metadata.node"),
    "v2ex.search": ("title", "canonical_url", "author", "metadata.topic_id", "metadata.node"),
    "v2ex.topic": ("title", "canonical_url", "author", "metadata.topic_id", "content"),
    "v2ex.replies": ("canonical_url", "author", "content", "metadata.reply_id", "metadata.topic_id"),
    "web.read": (
        "title", "canonical_url", "content", "page.title", "page.headings",
        "page.observed_links", "page.tables", "page.quotations",
        "page.media_captions", "page.potential_corrections",
        "page.declared_structured_data",
    ),
    "rss.read": ("title", "canonical_url", "published", "metadata.guid", "metadata.feed_title"),
    "xiaoyuzhou.podcast": ("title", "canonical_url", "metadata.item_type", "metadata.episode_count"),
    "xiaoyuzhou.episodes": ("title", "canonical_url", "published", "content", "metadata.duration"),
}

NESTED_FIELD_LISTS = {
    "metadata": "populated_metadata_field_names",
    "provider": "populated_provider_field_names",
    "video": "populated_video_metadata_field_names",
    "page": "populated_page_metadata_field_names",
}


def _important_field_state(sample: dict, field: str) -> bool | None:
    """True/False when measured, None when an older probe lacks the field audit."""
    if field == "content":
        return sample.get("content_chars", 0) > 0 if "content_chars" in sample else None
    if "." not in field:
        return bool(sample[field]) if field in sample else None
    category, name = field.split(".", 1)
    audit_key = NESTED_FIELD_LISTS[category]
    if audit_key not in sample:
        return None
    return name in sample[audit_key]


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
        field_names = ("title", "canonical_url", "author", "published", "backend_id", "content_depth")
        observed_fields = {
            field: sum(field in sample for sample in samples)
            for field in field_names
        }
        populated = {
            field: sum(field in sample and bool(sample[field]) for sample in samples)
            for field in field_names
        }
        latencies = [
            probe["latency_ms"] for probe in probes
            if isinstance(probe.get("latency_ms"), (int, float))
        ]
        total_items = sum(probe.get("item_count") or 0 for probe in successful)
        important = {}
        for field in IMPORTANT_FIELDS[operation]:
            states = [_important_field_state(sample, field) for sample in samples]
            measured = [state for state in states if state is not None]
            important[field] = {
                "populated": sum(measured),
                "measured_samples": len(measured),
                "population_rate": round(sum(measured) / len(measured), 3) if measured else None,
            }
        operations[operation] = {
            "scenario_count": len(probes),
            "live_success_count": len(successful),
            "live_success_rate": round(len(successful) / len(probes), 3) if probes else None,
            "sampled_item_count": total_items,
            "normalized_sample_count": len(samples),
            "normalized_field_observation_count": observed_fields,
            "normalized_field_population": populated,
            "normalized_field_population_rate": {
                field: round(count / observed_fields[field], 3)
                if observed_fields[field] else None
                for field, count in populated.items()
            },
            "observed_populated_metadata_field_names": sorted({
                field for sample in samples
                for field in sample.get("populated_metadata_field_names", [])
            }),
            "observed_populated_video_metadata_field_names": sorted({
                field for sample in samples
                for field in sample.get("populated_video_metadata_field_names", [])
            }),
            "observed_adapter_item_field_names": sorted({
                field for probe in successful
                for field in probe.get("adapter_item_field_names", [])
            }),
            "important_field_population": important,
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
                "Parsed adapter-item keys are a bounded observed subset, not a raw "
                "provider schema. Whole-page completeness is not measurable here."
            ),
        }

    return {
        "schema_version": "phase8-extraction-summary-v1",
        "source_probe_files": [path.as_posix() for path in paths],
        "method": "Observed live probe records; latest matching operation/scenario wins.",
        "limitations": [
            "Normalized samples and bounded parsed adapter-item key names are scored; raw provider field completeness is unverified.",
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
