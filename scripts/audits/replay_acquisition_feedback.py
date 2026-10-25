"""Evaluate opt-in routing feedback on genuine saved captures, without discovery.

This does not recreate provider ranking, request costs, controller recall or a
live investigation. Original source bytes/dates remain unchanged.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--domain", choices=("financial", "brand", "trending", "personal"), required=True)
    parser.add_argument("--intent", default="")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.input.is_symlink() or not args.input.is_file() or args.input.stat().st_size > 80_000_000:
        raise ValueError("Use a bounded regular saved native response")
    output = args.output_dir.resolve()
    if output.exists() or any(output.is_relative_to(ROOT / name) for name in (
            "research", "artifacts", "backend/data/dossiers", "tests/retrieval_benchmark")):
        raise ValueError("Use a fresh directory outside protected evidence")
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT))
    from scripts.validation.isolated_runtime import block_live_network, isolated_environment
    block_live_network()
    os.environ.update(isolated_environment(output / "runtime"))
    from scripts.audits.requalify_raw_pool import locate_pool
    from backend.services.research.raw_pool import RawAcquisitionPool
    from backend.services.research.adaptive_acquisition import inspect_capture
    encoded = args.input.read_bytes()
    original = locate_pool(json.loads(encoded))
    reference = datetime.fromisoformat(original["created_at"].replace("Z", "+00:00"))
    if reference.tzinfo is None:
        raise ValueError("Original capture observation time must be timezone-aware")
    pool = RawAcquisitionPool.from_export(original)
    rows = [inspect_capture(item, args.target, args.domain, args.intent, reference)
            for item in pool.to_evidence_items()]
    original_by_id = {row["source_id"]: row for row in original["sources"]}
    for row in rows:
        stored = original_by_id[row["source_id"]]
        row["original_qualification"] = stored["qualification_status"]
        row["duplicate_capture"] = bool(stored.get("duplicate_of"))
        row["captured_body_unchanged"] = row["body_sha256"] == hashlib.sha256(stored["readable_text"].encode()).hexdigest()
    result = {"mode": "OFFLINE_GENUINE_CAPTURE_FEEDBACK_NOT_DISCOVERY", "new_network_calls": 0, "model_calls": 0,
        "input_sha256": hashlib.sha256(encoded).hexdigest(), "domain": args.domain,
        "original_observation_clock": reference.isoformat(), "captures_checked": len(rows),
        "usable_routing_passages": sum(row["usable_passage"] and not row["duplicate_capture"] for row in rows), "rows": rows,
        "limitations": ["Routing feedback, not final source or claim acceptance.",
            "No search replay, native HTTP efficiency measurement or live autonomous discovery proof."]}
    with (output / "measurements.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({key: result[key] for key in ("mode", "captures_checked", "usable_routing_passages")}))
    return 0 if all(row["captured_body_unchanged"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
