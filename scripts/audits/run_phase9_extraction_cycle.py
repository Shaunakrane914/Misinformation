"""Repeat bounded production extraction probes; never silently optimize on labels.

Live traffic is explicit. Every run writes a new directory, retains aggregate
field/depth observations by default, and discloses dirty source. Public text
samples require --capture-samples and remain separately bounded research data.
Use --rounds/--interval-seconds for continuous sampling, not an unbounded crawler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.schemas.evidence_inspection import summarize_inspections
from backend.infrastructure.acquisition.routing.router import NativeRouter
from backend.services.agent_reach.native.operation_capabilities import EXECUTABLE_CAPABILITIES
from scripts.audits.run_phase8_live_acquisition_audit import PROBES, PROTECTED_OPERATIONS


def probe_specs(all_operations=False):
    seen = set()
    specs = []
    for spec in PROBES:
        if spec.operation not in seen:
            specs.append((spec.operation, spec.target))
            seen.add(spec.operation)
    specs += [
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
    if all_operations:
        # Fixed public samples, not credentials, guessed private endpoints or
        # held-out benchmark cases. Policy/credential decisions stay upstream.
        defaults = {
            "news": "OpenAI", "web": "OpenAI official announcements",
            "web_search": "OpenAI official announcements",
            "jina_reader": "https://www.python.org/about/",
            "rss": "OpenAI", "github": "openai/openai-python",
            "youtube": "Python programming", "v2ex": "python",
            "bilibili": "Python", "reddit": "Python",
            "twitter": "OpenAI", "linkedin": "Python developer",
            "xueqiu": "AAPL", "xiaohongshu": "technology",
            "instagram": "OpenAI", "facebook": "OpenAI", "boss": "Python",
            "xiaoyuzhou": "technology", "sec_edgar": "AAPL",
            "nist_cve": "Log4j", "arxiv": "attention transformer",
            "fact_check": "climate change", "hackernews": "Python",
            "stackexchange": "python generator",
            "expanded_sources": "yahoo_finance|Microsoft",
        }
        overrides = {
            "github.search": "misinformation verification", "v2ex.hot": "",
            "twitter.read": "https://x.com/jack/status/20",
            # oEmbed requires an explicit public object, not a search string.
            "instagram.oembed": "https://www.instagram.com/p/CxJgZZXu99M/",
            "facebook.oembed": "https://www.facebook.com/Meta/posts/10153231379946729",
        }
        present = {operation for operation, _ in specs}
        for channel, actions in sorted(EXECUTABLE_CAPABILITIES.items()):
            for action in sorted(actions):
                operation = f"{channel}.{action}"
                if operation not in present:
                    specs.append((operation, overrides.get(operation, defaults[channel])))
    return specs


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          encoding="utf-8", check=False).stdout.strip()


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


def run_round(router, specs, limit, deep, capture_directory=None):
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
            elif channel == "stackexchange":
                options.update(include_answers=True)
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
            if capture_directory is not None:
                from backend.schemas.evidence_inspection import inspect_evidence
                samples = []
                for fragment in fragments[:limit]:
                    content = fragment.content or fragment.snippet or ""
                    metadata = fragment.raw_metadata or {}
                    raw = metadata.get("raw_capture") or {}
                    samples.append({
                        "title": fragment.title, "content_depth": fragment.content_depth,
                        "url": fragment.url, "evidence_id": fragment.evidence_id,
                        "author": fragment.author, "published": fragment.published,
                        "retrieved_at": getattr(fragment, "retrieved_at", None),
                        "operation": operation,
                        "captured_text": content[:100_000],
                        "raw_text": str(raw.get("text", content))[:100_000],
                        "sample_truncated": len(content) > 100_000,
                        "inspection": inspect_evidence(fragment),
                    })
                target_id = hashlib.sha256(target.encode()).hexdigest()[:12]
                (capture_directory / f"{operation}_{target_id}.json").write_text(
                    json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
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
    parser.add_argument("--all-operations", action="store_true", help="Sample every executable operation, including blocked ones")
    parser.add_argument("--capture-samples", action="store_true", help="Retain bounded public source text in the new output tree; treat as research data")
    parser.add_argument("--extra-web-url", action="append", default=[], help="Up to five explicit supplemental public page reads; normal SSRF rules apply")
    parser.add_argument("--env-file", type=Path, help="Optional existing server config; import only source access settings, never write secrets")
    parser.add_argument("--operations", help="Comma-separated exact operations; unknown operations are rejected")
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_live:
        parser.error("Live probes require --allow-live; offline regression is pytest")
    if not 60 <= args.interval_seconds <= 3600:
        parser.error("Interval must be 60–3600 seconds to avoid rapid repeat requests")
    if args.env_file:
        from dotenv import dotenv_values
        from backend.services.agent_reach.native.operation_capabilities import CHANNEL_AUTH_ENVIRONMENT
        allowed = set(CHANNEL_AUTH_ENVIRONMENT.values()) | {"REDDIT_APPROVED_ACCESS", "SEC_USER_AGENT"}
        for key, value in dotenv_values(args.env_file).items():
            if key in allowed and value is not None:
                os.environ.setdefault(key, value)
    specs = probe_specs(args.all_operations)
    if args.operations:
        selected = set(args.operations.split(","))
        unknown = selected - {operation for operation, _ in specs}
        if unknown:
            parser.error("Unknown operation filter")
        specs = [spec for spec in specs if spec[0] in selected]
    if len(args.extra_web_url) > 5:
        parser.error("At most five supplemental public page URLs")
    specs.extend(("web.read", url) for url in args.extra_web_url)
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
        "supplemental_public_urls": args.extra_web_url,
        "policy": "Bounded public samples; no accuracy/completeness claim",
        "captures_public_text": args.capture_samples,
        "explicit_env_file_used": bool(args.env_file),
        "reddit_approved_access_flag": os.getenv("REDDIT_APPROVED_ACCESS", "false").lower() in {"1", "true", "yes"},
        "access_note": "Operator configuration observation only, not independent provider authorization",
    }, indent=2), encoding="utf-8")
    router = NativeRouter()
    all_rounds = []
    for index in range(args.rounds):
        if index:
            time.sleep(args.interval_seconds)
        capture_directory = directory / f"samples_{index + 1}" if args.capture_samples else None
        if capture_directory:
            capture_directory.mkdir()
        records = run_round(router, specs, args.limit, args.deep, capture_directory)
        all_rounds.append(records)
        (directory / f"round_{index + 1}.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    last = all_rounds[-1]
    successful = {record["operation"] for record in last if record["metrics"]["items"] > 0}
    unchanged = source_fingerprint() == json.loads((directory / "metadata.json").read_text(encoding="utf-8"))["source_tree_sha256"]
    summary = {
        "source_unchanged_during_run": unchanged,
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
    return 0 if unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
