"""Run a bounded, truth-preserving pre-Phase-7 acquisition audit.

This runner writes only to a new timestamped directory.  It never rewrites the
frozen benchmark datasets and never infers HTTP facts from normalized evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

os.environ.setdefault("AEGIS_HTTP_TIMEOUT", "6")
os.environ.setdefault("AEGIS_DISCOVERY_MAX_CANDIDATES", "5")

from backend.infrastructure.acquisition.routing.router import native_router
from backend.infrastructure.acquisition.service import agent_reach_service
from backend.services.agent_reach.native.channel_capabilities import CAPABILITY_MATRIX
from backend.services.agent_reach.source_planner import EXECUTABLE_CAPABILITIES
from backend.services.agent_reach.native.operation_capabilities import (
    runtime_operation_capabilities,
)


PROBES = [
    ("web", "search", "Nvidia RTX 5090 discontinuation rumor", True, None),
    ("web_search", "search", "Nvidia RTX 5090 discontinuation rumor", True, None),
    ("web", "read", "https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/", True, None),
    ("news", "search", "Nvidia RTX 5090 discontinuation rumor", True, None),
    ("rss", "search", "Nvidia official product announcement RTX 5090", True, None),
    ("jina_reader", "read", "https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/", True, None),
    ("github", "search", "misinformation research retrieval", True, None),
    ("github", "read", "pallets/flask", True, None),
    ("github", "issues", "pallets/flask", True, None),
    ("github", "releases", "pallets/flask", True, None),
    ("youtube", "search", "Nvidia RTX 5090 technical analysis", True, None),
    ("youtube", "read", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", True, None),
    ("youtube", "transcript", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", True, None),
    ("youtube", "comments", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", True, None),
    ("v2ex", "hot", "AI", True, None),
    ("v2ex", "latest", "", True, None),
    ("v2ex", "topic", "1", True, None),
    ("v2ex", "replies", "1", True, None),
    ("bilibili", "search", "Nvidia RTX 5090", True, None),
    ("twitter", "profile", "@OpenAI", True, None),
    ("twitter", "status", "https://x.com/Safety/status/1775942160509989256", True, None),
    (
        "reddit", "search", "Nvidia RTX 5090 r/hardware", False,
        "POLICY_RESTRICTED: no approved Reddit Data API access configured",
    ),
    (
        "reddit", "comments", "https://www.reddit.com/r/technology/comments/1x2e3ar/", False,
        "POLICY_RESTRICTED: direct Reddit content collection was not authorized",
    ),
    ("linkedin", "jobs", "AI research engineer", True, None),
    ("xueqiu", "search", "NVDA", True, None),
    ("xiaohongshu", "search", "Nvidia", True, None),
    ("instagram", "search", "Nvidia", True, None),
    ("facebook", "search", "Nvidia", True, None),
    ("boss", "search_jobs", "AI engineer", True, None),
    ("xiaoyuzhou", "podcast", "artificial intelligence", True, None),
]


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _depth_class(depths: Iterable[str], modes: Iterable[str]) -> str:
    depth_set = {str(item).upper() for item in depths}
    mode_set = {str(item).lower() for item in modes}
    if not depth_set:
        return "EMPTY"
    if "INDEX_SNIPPET" in depth_set or "web_search_index" in mode_set:
        return "SEARCH_INDEX_DISCOVERY"
    if "FEED_ENTRY_SUMMARY" in depth_set or "rss_feed" in mode_set:
        return "SYNDICATED_SUMMARY"
    if depth_set <= {"PROFILE_METADATA", "VIDEO_METADATA", "HEADLINE_ONLY", "METADATA"}:
        return "DIRECT_METADATA"
    if depth_set & {
        "FULL_ARTICLE", "PARTIAL_CONTENT", "TWEET_STATUS", "SOCIAL_POST",
        "COMMENTS", "COMMENT", "VIDEO_TRANSCRIPT", "PRIMARY_DOCUMENT",
    }:
        return "DIRECT_CONTENT"
    return "PARTIAL_OR_UNCLASSIFIED"


def _transport_records(fragments: Iterable[Any]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for fragment in fragments:
        transport = (getattr(fragment, "raw_metadata", {}) or {}).get("transport", {})
        records.append({
            "canonical_source_url": getattr(fragment, "url", None),
            "endpoint": transport.get("endpoint"),
            "network_observed_this_attempt": transport.get("network_observed_this_attempt"),
            "http_status": transport.get("http_status"),
            "content_type": transport.get("content_type"),
            "raw_body_bytes": transport.get("raw_body_bytes"),
            "network_latency_ms": transport.get("network_latency_ms"),
            "cache_status": transport.get("cache_status", "UNKNOWN"),
            "normalized_chars": len(getattr(fragment, "content", "") or ""),
            "usable_body_chars": (getattr(fragment, "raw_metadata", {}) or {}).get("usable_body_chars"),
        })
    return records


def _probe(channel: str, operation: str, query: str, permitted: bool, skip_reason: str | None) -> Dict[str, Any]:
    started = time.perf_counter()
    if not permitted:
        return {
            "channel": channel,
            "operation": operation,
            "query": query,
            "outcome": "BLOCKED",
            "health": "BLOCKED",
            "error_category": skip_reason,
            "network_io_observed": False,
            "fragments": [],
            "transport": [],
            "latency_ms": 0,
        }
    fragments, telemetry = native_router.execute_channel_query(
        channel,
        query,
        limit=3,
        query_id=f"audit_{channel}_{operation}",
        query_class="pre_phase7_audit",
        query_text=query,
        operation=operation,
        public_mode=False,
    )
    transport = _transport_records(fragments)
    depths = [getattr(fragment, "content_depth", "UNKNOWN") for fragment in fragments]
    modes = [getattr(fragment, "retrieval_mode", "unknown") for fragment in fragments]
    outcome = telemetry.get("outcome") or _depth_class(depths, modes)
    health = {
        "DIRECT_CONTENT": "HEALTHY",
        "DIRECT_METADATA": "LIMITED",
        "SYNDICATED_SUMMARY": "LIMITED",
        "SEARCH_INDEX_DISCOVERY": "DEGRADED",
        "AUTH_REQUIRED": "BLOCKED",
        "EMPTY": "DEGRADED",
        "UNAVAILABLE_NOT_IMPLEMENTED": "UNSUPPORTED",
    }.get(outcome, "UNAVAILABLE" if telemetry.get("status") == "FAILED" else "DEGRADED")
    return {
        "channel": channel,
        "operation": operation,
        "query": query,
        "backend": telemetry.get("backend"),
        "outcome": outcome,
        "legacy_status": telemetry.get("status"),
        "health": health,
        "content_depths": sorted(set(depths)),
        "retrieval_modes": sorted(set(modes)),
        "evidence_item_count": len(fragments),
        "usable_text_chars": telemetry.get("usable_text_chars", 0),
        "network_io_observed": any(item.get("network_observed_this_attempt") is True for item in transport),
        "http_statuses_observed": sorted({item["http_status"] for item in transport if item.get("http_status") is not None}),
        "transport": transport,
        "canonical_urls": [getattr(fragment, "url", "") for fragment in fragments],
        "titles": [getattr(fragment, "title", "")[:180] for fragment in fragments],
        "fallback_used": telemetry.get("fallback_used", False),
        "fallback_backend": telemetry.get("fallback_backend"),
        "error_category": telemetry.get("error") or telemetry.get("fallback_reason"),
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_markdown(path: Path, records: List[Dict[str, Any]], sha: str) -> None:
    lines = [
        "# Pre-Phase 7 verified capability matrix",
        "",
        f"- Commit: `{sha}`",
        f"- Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "- HTTP fields are populated only from adapter-level transport observations.",
        "- `network_io_observed=false` means transport facts remain unknown, even when normalized fragments exist.",
        "",
        "| Channel | Operation | Outcome | Health | Items | Network observed | HTTP |",
        "|---|---|---|---|---:|---|---|",
    ]
    for record in records:
        statuses = ", ".join(map(str, record.get("http_statuses_observed", []))) or "unknown"
        lines.append(
            f"| {record['channel']} | {record['operation']} | {record['outcome']} | "
            f"{record['health']} | {record.get('evidence_item_count', 0)} | "
            f"{str(record.get('network_io_observed', False)).lower()} | {statuses} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="artifacts/pre_phase7_audit")
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%SZ")
    output_dir = Path(args.output_root) / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    sha = _git_sha()
    records: List[Dict[str, Any]] = []
    for probe in PROBES:
        try:
            records.append(_probe(*probe))
        except Exception as exc:
            records.append({
                "channel": probe[0], "operation": probe[1], "query": probe[2],
                "outcome": "FAILED", "health": "UNAVAILABLE",
                "error_category": f"{type(exc).__name__}: {exc}",
                "network_io_observed": False, "http_statuses_observed": [],
                "evidence_item_count": 0, "transport": [], "latency_ms": None,
            })

    probed_keys = {(item["channel"], item["operation"]) for item in records}
    operation_records = list(records)
    declared_channels = set(CAPABILITY_MATRIX) | set(EXECUTABLE_CAPABILITIES)
    for channel in sorted(declared_channels):
        declared = set(CAPABILITY_MATRIX.get(channel).operations) if channel in CAPABILITY_MATRIX else set()
        executable = set(EXECUTABLE_CAPABILITIES.get(channel, set()))
        for operation in sorted(declared | executable):
            if (channel, operation) in probed_keys:
                continue
            assessment = runtime_operation_capabilities.assess(channel, operation)
            if operation not in executable:
                outcome, health = "UNAVAILABLE_NOT_IMPLEMENTED", "UNSUPPORTED"
                reason = "Declared upstream but no production execution path"
            elif assessment["runtime_health"] in {"AUTH_REQUIRED", "BLOCKED"}:
                outcome, health = assessment["runtime_health"], "BLOCKED"
                reason = assessment["reason"]
            else:
                outcome, health = "UNVERIFIED", "UNVERIFIED"
                reason = "Not exercised in bounded live audit"
            operation_records.append({
                "channel": channel,
                "operation": operation,
                "outcome": outcome,
                "health": health,
                "network_io_observed": False,
                "http_statuses_observed": [],
                "evidence_item_count": 0,
                "transport": [],
                "error_category": reason,
            })

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in operation_records:
        grouped[record["channel"]].append(record)
    channel_results = {
        channel: {
            "operations": values,
            "best_verified_health": next(
                (level for level in ("HEALTHY", "LIMITED", "DEGRADED", "BLOCKED", "UNSUPPORTED", "UNVERIFIED")
                 if any(item["health"] == level for item in values)),
                "UNVERIFIED",
            ),
        }
        for channel, values in sorted(grouped.items())
    }

    _write_json(output_dir / "channel_results.json", channel_results)
    with (output_dir / "operation_results.jsonl").open("w", encoding="utf-8") as handle:
        for record in operation_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    _write_json(output_dir / "agent_results.json", {
        "scope": "live network agent runs were not performed",
        "deterministic_test": "tests/integration/test_source_planner_agent_execution.py",
        "status": "VERIFY_WITH_PYTEST_OUTPUT",
    })
    _write_json(output_dir / "run_metadata.json", {
        "commit": sha,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": os.sys.version,
        "reddit_direct_probe_policy": "skipped_without_approved_access",
        "credentials_present": {
            name: bool(os.getenv(name)) for name in (
                "LINKEDIN_COOKIE", "XUEQIU_COOKIE", "XIAOHONGSHU_COOKIE",
                "INSTAGRAM_COOKIE", "FACEBOOK_COOKIE", "BOSS_CDP_PORT",
                "GROQ_API_KEY", "GITHUB_TOKEN",
            )
        },
    })
    _write_markdown(output_dir / "capability_matrix_verified.md", records, sha)

    failures = [item for item in records if item["health"] in {"BLOCKED", "UNAVAILABLE", "UNSUPPORTED"}]
    (output_dir / "failure_analysis.md").write_text(
        "# Failure analysis\n\n" + "\n".join(
            f"- **{item['channel']}.{item['operation']}** — {item['outcome']}: "
            f"{item.get('error_category') or 'no usable evidence'}"
            for item in failures
        ) + "\n",
        encoding="utf-8",
    )
    (output_dir / "executive_summary.md").write_text(
        "# Executive summary\n\n"
        f"This bounded run evaluated {len(records)} representative production operations at `{sha}`. "
        f"It observed {sum(1 for item in records if item.get('network_io_observed'))} operations with "
        "adapter-level network facts. Normalized output without an adapter observation was not assigned "
        "an HTTP status. Reddit direct-content probes were intentionally policy-blocked because approved "
        "Data API access was not configured. See `operation_results.jsonl` for every pass, limitation, and failure.\n",
        encoding="utf-8",
    )
    print(output_dir.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
