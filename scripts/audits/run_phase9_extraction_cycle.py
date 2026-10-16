"""Repeat bounded production extraction probes; never silently optimize on labels.

Live traffic is explicit. Every run writes a new directory, retains aggregate
field/depth observations rather than raw bodies, and discloses dirty source.
Use --rounds/--interval-seconds for continuous sampling, not an unbounded crawler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.schemas.evidence_inspection import summarize_inspections
from backend.infrastructure.acquisition.routing.router import NativeRouter
from scripts.audits.run_phase8_live_acquisition_audit import PROBES, PROTECTED_OPERATIONS


def probe_specs():
    seen = set()
    specs = []
    for spec in PROBES:
        if spec.operation not in seen:
            specs.append((spec.operation, spec.target))
            seen.add(spec.operation)
    return specs + [
        ("reddit.read", "https://www.reddit.com/r/IAmA/comments/z1c9z/i_am_barack_obama/"),
        ("reddit.comments", "https://www.reddit.com/r/IAmA/comments/z1c9z/i_am_barack_obama/"),
        ("twitter.status", "https://x.com/jack/status/20"),
        ("twitter.profile", "@OpenAI"),
        ("hackernews.read", "https://news.ycombinator.com/item?id=8863"),
        ("hackernews.search", "Python"),
        ("stackexchange.read", "https://stackoverflow.com/questions/231767/what-does-the-yield-keyword-do-in-python"),
        ("stackexchange.search", "python generator"),
        ("sec_edgar.read", "AAPL"),
        ("nist_cve.read", "CVE-2021-44228"),
        ("arxiv.read", "1706.03762"),
        ("fact_check.search", "climate change"),
    ]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip()


def source_fingerprint():
    # Include untracked implementation files, unlike `git diff HEAD` alone.
    paths = git("ls-files", "--cached", "--others", "--exclude-standard", "--", "backend", "scripts", "frontend")
    digest = hashlib.sha256()
    for name in sorted(set(paths.splitlines())):
        path = ROOT / name
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"}:
            digest.update(name.encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def run_round(router, specs, limit, deep):
    records = []
    for operation, target in specs:
        channel, action = operation.split(".", 1)
        options = {}
        if deep:
            if operation == "github.issues":
                options.update(include_comments=True, comment_limit=3)
            elif operation in {"github.prs", "github.commits"}:
                options.update(include_files=True, file_limit=3)
            elif operation == "rss.read":
                options.update(follow_linked_article=True)
            elif operation == "web.read":
                options.update(max_chars=12000)
            elif channel == "hackernews":
                options.update(include_comments=True)
        started = time.monotonic()
        try:
            fragments, telemetry = router.execute_channel_query(
                platform=channel, operation=action, query=target, limit=limit, **options,
            )
            record = {"operation": operation, "status": telemetry.get("status"),
                      "reason": (telemetry.get("runtime_decision") or {}).get("reason"),
                      "outcome": telemetry.get("outcome"), "network_observed": telemetry.get("network_observed", False),
                      "http_statuses": telemetry.get("http_statuses", []),
                      "metrics": summarize_inspections(fragments)}
        except Exception as error:
            # Do not persist arbitrary exception messages or provider payloads.
            record = {"operation": operation, "status": "FAILED", "error_type": type(error).__name__,
                      "metrics": summarize_inspections([]), "network_observed": False}
        record.update(latency_ms=round((time.monotonic() - started) * 1000),
                      target_sha256=hashlib.sha256(target.encode()).hexdigest())
        records.append(record)
        print(f"{operation}: {record['status']} items={record['metrics']['items']} "
              f"chars={record['metrics']['captured_chars']} live={record['network_observed']}", flush=True)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--rounds", type=int, choices=range(1, 11), default=1)
    parser.add_argument("--interval-seconds", type=float, default=60.0)
    parser.add_argument("--limit", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--operations", help="Comma-separated exact operations; unknown operations are rejected")
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_live:
        parser.error("Live probes require --allow-live; offline regression is pytest")
    if not 60 <= args.interval_seconds <= 3600:
        parser.error("Interval must be 60–3600 seconds to avoid rapid repeat requests")
    specs = probe_specs()
    if args.operations:
        selected = set(args.operations.split(","))
        unknown = selected - {operation for operation, _ in specs}
        if unknown:
            parser.error("Unknown operation filter")
        specs = [spec for spec in specs if spec[0] in selected]
    source = Path(sys.modules[NativeRouter.__module__].__file__).resolve()
    if not source.is_relative_to(ROOT):
        raise RuntimeError("Refusing to audit an editable-installed different checkout")
    directory = args.output_root / datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S_%fZ")
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "metadata.json").write_text(json.dumps({
        "schema_version": "phase9-extraction-cycle-v1", "head": git("rev-parse", "HEAD"),
        "worktree_dirty": bool(git("status", "--porcelain")),
        "source_diff_sha256": hashlib.sha256(git("diff", "HEAD", "--", "backend", "scripts").encode()).hexdigest(),
        "source_tree_sha256": source_fingerprint(),
        "rounds": args.rounds, "interval_seconds": args.interval_seconds,
        "limit": args.limit, "deep": args.deep,
        "operations": [operation for operation, _ in specs],
        "policy": "Bounded public samples; no raw bodies retained; no accuracy/completeness claim",
    }, indent=2), encoding="utf-8")
    router = NativeRouter()
    all_rounds = []
    for index in range(args.rounds):
        if index:
            time.sleep(args.interval_seconds)
        records = run_round(router, specs, args.limit, args.deep)
        all_rounds.append(records)
        (directory / f"round_{index + 1}.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    last = all_rounds[-1]
    successful = {record["operation"] for record in last if record["metrics"]["items"] > 0}
    summary = {
        "sample_gate": "PASS" if set(PROTECTED_OPERATIONS) <= successful else "PARTIAL",
        "sample_gate_scope": "16 protected operations only, bounded examples",
        "all_requested_sources_gate": "PASS" if len(successful) == len(specs) else "PARTIAL",
        "requested_operations_without_records": [record["operation"] for record in last if not record["metrics"]["items"]],
        "protected_operations_missing": sorted(set(PROTECTED_OPERATIONS) - successful),
        "operations_sampled": len(specs), "rounds_completed": len(all_rounds),
        "observed_items": sum(record["metrics"]["items"] for record in last),
        "claim_accuracy": None, "source_completeness": "UNKNOWN", "release_acceptance": "NOT_ESTABLISHED",
    }
    (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(directory.as_posix(), flush=True)
    print(json.dumps(summary), flush=True)
    # A completed sampling loop is distinct from a passing acquisition gate.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
