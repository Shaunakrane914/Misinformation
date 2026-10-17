"""Compare saved native investigations without requests or acceptance inflation.

This is a diagnostic inventory, not an accuracy/recall evaluator. Outputs go to
a new file; retained words include metadata unless explicitly separated.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.schemas.evidence_inspection import METADATA_DEPTHS


def summarize_response(data):
    report = data.get("unified_report") or {}
    trace = data.get("deep_research_trace") or data.get("retrieval_trace") or {}
    corpus = data.get("research_corpus") or {}
    records = data.get("evidence") or data.get("sources") or []
    records = records if isinstance(records, list) else []
    depth_counts = {}
    for item in records:
        depth = item.get("content_depth") or (item.get("metadata") or {}).get("content_depth") or "UNKNOWN"
        depth_counts[depth] = depth_counts.get(depth, 0) + 1
    cards = [item for bucket in (report.get("evidence") or {}).values() if isinstance(bucket, list) for item in bucket]
    refs = [ref for finding in report.get("finding_details", []) for ref in finding.get("citation_observations", [])]
    attempts = trace.get("acquisition_attempts") or []
    return {
        "native_records": len(records), "native_depth_counts": depth_counts,
        "metadata_or_unknown_records": sum(v for k, v in depth_counts.items() if k in METADATA_DEPTHS),
        "retained_text_words": sum(len(str(item.get("content") or item.get("snippet") or "").split()) for item in records),
        "raw_candidates": len(corpus.get("raw_candidates") or []),
        "ranked_candidates": len(corpus.get("ranked_candidates") or []),
        "read_attempts": len(attempts),
        "read_outcomes": [{"url": a.get("url"), "status": a.get("status"), "error": a.get("error_message")} for a in attempts],
        "findings": len(report.get("findings") or []),
        "finding_states": [f.get("epistemic_state") for f in report.get("finding_details") or []],
        "citation_observations": {state: sum(r.get("availability") == state for r in refs)
                                  for state in ("SOURCE_RECORD", "DISCOVERY_ONLY", "UNAVAILABLE")},
        "render_contract_evidence_cards": len(cards),
        "inspection_chars": sum((card.get("extraction") or {}).get("captured_chars", 0) for card in cards),
        "stage_timings_ms": trace.get("stage_timings_ms") or {},
        "claim_accuracy": None, "research_acceptance": "REQUIRES_CONTENT_REVIEW",
    }


def summarize_directory(directory):
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    cases = []
    for row in summary["cases"]:
        data = json.loads((directory / (row["case_id"] + ".json")).read_text(encoding="utf-8"))
        cases.append({"case_id": row["case_id"], "input": row["input"], "agent": row["agent"],
                      "browser_seconds": row["elapsed_seconds"], **summarize_response(data)})
    return {"head": summary.get("head"), "application_sha256": summary.get("application_sha256"),
            "application_unchanged_during_run": summary.get("application_unchanged_during_run"), "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"scope": "Saved real observations, no new provider calls or inferred accuracy",
              "baseline": summarize_directory(args.baseline), "after": summarize_directory(args.after)}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
    print(str(args.output))


if __name__ == "__main__":
    main()
