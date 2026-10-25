"""Measure saved normal agent outputs only; no extra adapter fetches or AI calls.

Raw body words are not useful evidence. No stopword heuristic or synthetic
throughput ratio is presented as research-quality or frontend acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path


def measure_response(payload):
    report = payload.get("unified_report") or {}
    records = payload.get("sources") or payload.get("evidence") or []
    records = records if isinstance(records, list) else []
    seen, raw_words, bodies = set(), 0, 0
    for row in records:
        if not isinstance(row, dict):
            continue
        body = row.get("content") or ""
        if not body or row.get("content_depth") in {"SNIPPET", "INDEX_SNIPPET", "PROFILE_METADATA", "DIRECT_METADATA"}:
            continue
        identity = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if identity in seen:
            continue
        seen.add(identity)
        raw_words += len(body.split())
        bodies += 1
    workbench = report.get("evidence_workbench") or {}
    accounting = workbench.get("accounting") or {}
    return {"agent": report.get("_meta", {}).get("agent"), "retained_unique_body_words": raw_words,
            "retained_body_records": bodies, "published_selected_passages": accounting.get("published_passages"),
            "published_selected_words": accounting.get("published_unique_words"),
            "usefulness_independently_reviewed": False, "twentyfold_acceptance": "NOT_EVALUATED",
            "scope": "Saved normal agent output; no separately fetched adapter text added"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if output.exists() or any(output.is_relative_to(root / name) for name in (
            "artifacts", "research", "backend/data/dossiers", "tests/retrieval_benchmark")):
        raise ValueError("Use a new output outside protected historical trees")
    cases = []
    for path in args.input:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 80_000_000:
            raise ValueError("Use a bounded regular saved response")
        cases.append(measure_response(json.loads(path.read_text(encoding="utf-8"))))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump({"mode": "OFFLINE_SAVED_AGENT_MEASUREMENT", "new_network_calls": 0, "model_calls": 0,
                   "cases": cases, "multiplier_claim": "NOT_DEMONSTRATED"}, stream, indent=2)
    print(json.dumps({"cases": len(cases), "mode": "OFFLINE_SAVED_AGENT_MEASUREMENT"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
