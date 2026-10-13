"""Run the Phase 8A live-acquisition acceptance audit.

The runner exercises the production ``NativeRouter`` with bounded public
targets.  It writes only to a new timestamped directory, retains no response
bodies, and never treats fixture, cache, or normalized output as live traffic.
Use ``--require-pass`` when an incomplete protected-operation gate should
produce a non-zero exit status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# A file-path invocation otherwise may import an editable-installed *other*
# checkout of ``backend`` (notably when this script runs in a Git worktree).
# Force this script's own repository to be the acquisition code under audit.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.infrastructure.acquisition.routing.router import NativeRouter
from backend.services.agent_reach.native.channel_capabilities import CAPABILITY_MATRIX
from backend.services.agent_reach.native.operation_capabilities import (
    EXECUTABLE_CAPABILITIES,
    required_auth_environment,
    runtime_operation_capabilities,
)


PROTECTED_OPERATIONS = (
    "github.read", "github.issues", "github.prs", "github.commits",
    "github.releases", "youtube.read", "youtube.transcript",
    "youtube.comments", "v2ex.latest", "v2ex.search", "v2ex.topic",
    "v2ex.replies", "web.read", "rss.read", "xiaoyuzhou.podcast",
    "xiaoyuzhou.episodes",
)

SUCCESS_CLASSIFICATIONS = {
    "DIRECT_FULL_CONTENT", "DIRECT_PARTIAL_CONTENT", "DIRECT_METADATA",
    "SEARCH_DISCOVERY_ONLY", "SYNDICATED_SUMMARY",
}


@dataclass(frozen=True)
class ProbeSpec:
    operation: str
    scenario: str
    target: str
    requested_url: str | None
    protected: bool = True
    missing_is_not_found: bool = False

    @property
    def channel(self) -> str:
        return self.operation.split(".", 1)[0]

    @property
    def action(self) -> str:
        return self.operation.split(".", 1)[1]


def _specs_for(operation: str, targets: Iterable[tuple[str, str, str | None, bool]]) -> list[ProbeSpec]:
    return [
        ProbeSpec(operation, scenario, target, url, operation in PROTECTED_OPERATIONS, missing)
        for scenario, target, url, missing in targets
    ]


PROBES: list[ProbeSpec] = []
for github_operation in ("read", "issues", "prs", "commits", "releases"):
    PROBES += _specs_for(f"github.{github_operation}", (
        ("common", "openai/openai-python", f"https://api.github.com/repos/openai/openai-python/{'' if github_operation == 'read' else {'issues': 'issues', 'prs': 'pulls', 'commits': 'commits', 'releases': 'releases'}[github_operation]}", False),
        ("high-content", "python/cpython", f"https://api.github.com/repos/python/cpython/{'' if github_operation == 'read' else {'issues': 'issues', 'prs': 'pulls', 'commits': 'commits', 'releases': 'releases'}[github_operation]}", False),
        ("inaccessible", "aegis-phase8/definitely-missing-repository", "https://api.github.com/repos/aegis-phase8/definitely-missing-repository", True),
    ))

for youtube_operation in ("read", "transcript", "comments"):
    PROBES += _specs_for(f"youtube.{youtube_operation}", (
        ("common", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", False),
        ("early-public-video", "https://www.youtube.com/watch?v=jNQXAC9IVRw", "https://www.youtube.com/watch?v=jNQXAC9IVRw", youtube_operation == "transcript"),
        ("not-found", "https://www.youtube.com/watch?v=aaaaaaaaaaa", "https://www.youtube.com/watch?v=aaaaaaaaaaa", True),
    ))

PROBES += _specs_for("v2ex.latest", (
    ("common", "", "https://www.v2ex.com/api/topics/latest.json", False),
    ("repeatability", "latest", "https://www.v2ex.com/api/topics/latest.json", False),
    ("bounded-edge", "ignored", "https://www.v2ex.com/api/topics/latest.json", False),
))
PROBES += _specs_for("v2ex.search", (
    ("common-node", "python", "https://www.v2ex.com/api/topics/show.json?node_name=python", False),
    ("active-node", "programmer", "https://www.v2ex.com/api/topics/show.json?node_name=programmer", False),
    ("missing-node", "aegis-phase8-no-such-node", "https://www.v2ex.com/api/topics/show.json?node_name=aegis-phase8-no-such-node", True),
))
for v2ex_operation in ("topic", "replies"):
    endpoint = "topics/show.json?id=" if v2ex_operation == "topic" else "replies/show.json?topic_id="
    PROBES += _specs_for(f"v2ex.{v2ex_operation}", (
        ("historical-topic", "1", f"https://www.v2ex.com/api/{endpoint}1", v2ex_operation == "replies"),
        ("public-topic", "1000000", f"https://www.v2ex.com/api/{endpoint}1000000", False),
        ("not-found", "999999999", f"https://www.v2ex.com/api/{endpoint}999999999", True),
    ))

PROBES += _specs_for("web.read", (
    ("common", "https://www.python.org/about/", "https://www.python.org/about/", False),
    ("high-content", "https://peps.python.org/pep-0008/", "https://peps.python.org/pep-0008/", False),
    ("not-found", "https://www.python.org/phase8-aegis-not-found", "https://www.python.org/phase8-aegis-not-found", True),
))
PROBES += _specs_for("rss.read", (
    ("common", "https://feeds.bbci.co.uk/news/rss.xml", "https://feeds.bbci.co.uk/news/rss.xml", False),
    ("official-feed", "https://www.nasa.gov/rss/dyn/breaking_news.rss", "https://www.nasa.gov/rss/dyn/breaking_news.rss", False),
    ("not-found", "https://www.python.org/phase8-aegis-not-found.xml", "https://www.python.org/phase8-aegis-not-found.xml", True),
))
for podcast_operation in ("podcast", "episodes"):
    PROBES += _specs_for(f"xiaoyuzhou.{podcast_operation}", (
        ("public-podcast", "https://www.xiaoyuzhoufm.com/podcast/64e6b4dc80c9ec4c5f1e0782", "https://www.xiaoyuzhoufm.com/podcast/64e6b4dc80c9ec4c5f1e0782", False),
        ("sparse-podcast", "https://www.xiaoyuzhoufm.com/podcast/65ccb318160fa5d60ae05161", "https://www.xiaoyuzhoufm.com/podcast/65ccb318160fa5d60ae05161", podcast_operation == "episodes"),
        ("not-found", "https://www.xiaoyuzhoufm.com/podcast/000000000000000000000000", "https://www.xiaoyuzhoufm.com/podcast/000000000000000000000000", True),
    ))

AUXILIARY_PROBES = (
    ProbeSpec("web.search", "discovery", "OpenAI official announcements", "https://www.bing.com/search", False),
    ProbeSpec("rss.search", "discovery", "OpenAI official announcement", "https://news.google.com/rss/search", False),
    ProbeSpec("github.search", "discovery", "misinformation verification", "gh search repos", False),
    ProbeSpec("youtube.search", "discovery", "misinformation verification", "ytsearch", False),
)

PAGINATION = {
    "github.issues": "BOUNDED_EXPLICIT_PAGE_1_TO_5",
    "github.prs": "BOUNDED_EXPLICIT_PAGE_1_TO_5",
    "github.commits": "BOUNDED_EXPLICIT_PAGE_1_TO_5",
    "github.releases": "BOUNDED_EXPLICIT_PAGE_1_TO_5",
    "rss.read": "FIRST_FEED_PAGE_BOUNDED",
    "xiaoyuzhou.podcast": "FIRST_SEARCH_PAGE_AND_FIRST_FEED_PAGE_BOUNDED",
    "xiaoyuzhou.episodes": "FIRST_SEARCH_PAGE_AND_FIRST_FEED_PAGE_BOUNDED",
    "youtube.comments": "TOP_COMMENTS_BOUNDED_NO_CONTINUATION",
}


def _git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False,
    )
    return result.stdout.strip()


def _redact(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    text = re.sub(r"(?i)(authorization|bearer|token|api[_-]?key|cookie)([=: ]+)[^\s,;]+", r"\1\2[REDACTED]", text)
    text = re.sub(r"([?&](?:key|token|access_token)=)[^&]+", r"\1[REDACTED]", text, flags=re.IGNORECASE)
    return text[:1000]


def _transport_records(
    fragments: Iterable[Any], telemetry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    raw_transports = list((telemetry or {}).get("transport_observations", []))
    raw_transports.extend(
        (getattr(fragment, "raw_metadata", {}) or {}).get("transport", {}) or {}
        for fragment in fragments
    )
    seen: set[str] = set()
    for transport in raw_transports:
        fingerprint = json.dumps(transport, sort_keys=True, default=str)
        if not transport or fingerprint in seen:
            continue
        seen.add(fingerprint)
        records.append({
            "requested_endpoint": _redact(transport.get("requested_endpoint")),
            "final_endpoint": _redact(transport.get("endpoint")),
            "redirect_chain": [_redact(item) for item in transport.get("redirect_chain", [])],
            "network_observed_this_attempt": transport.get("network_observed_this_attempt") is True,
            "http_status": transport.get("http_status"),
            "content_type": transport.get("content_type"),
            "raw_body_bytes": transport.get("raw_body_bytes"),
            "raw_body_sha256": transport.get("raw_body_sha256"),
            "network_latency_ms": transport.get("network_latency_ms"),
            "cache_status": transport.get("cache_status", "UNKNOWN"),
            "attempts": transport.get("attempts"),
        })
    return records


def classify_probe(
    *, telemetry: dict[str, Any], fragments: list[Any], missing_is_not_found: bool,
) -> str:
    """Map production telemetry to the mandatory Phase 8 outcome vocabulary."""
    status = str(telemetry.get("status") or "").upper()
    error = str(telemetry.get("error") or "").lower()
    statuses = {int(item) for item in telemetry.get("http_statuses", []) if item is not None}
    if status == "AUTH_REQUIRED" or 401 in statuses:
        return "AUTH_REQUIRED"
    if (
        429 in statuses
        or telemetry.get("rate_limit_remaining") == 0
        or "rate limit" in error
    ):
        return "RATE_LIMITED"
    if "policy_block" in error or "policy blocked" in error or 403 in statuses:
        return "POLICY_BLOCKED"
    if statuses & {404, 410}:
        return "NOT_FOUND"
    if missing_is_not_found and any(term in error for term in ("not found", "unavailable")):
        return "NOT_FOUND"
    if status in {"SKIPPED", "EXCLUDED"}:
        return "UNVERIFIED"
    if status == "FAILED":
        if any(term in error for term in ("parse", "decode", "invalid json", "extract")):
            return "PARSER_FAILURE"
        return "NETWORK_FAILURE"
    if not fragments:
        if str(telemetry.get("provider_status") or "").upper() == "EMPTY":
            return "NOT_FOUND"
        if missing_is_not_found:
            return "NOT_FOUND"
        return "PARSER_FAILURE" if telemetry.get("network_observed") else "UNVERIFIED"

    depths = {str(getattr(item, "content_depth", "") or "").upper() for item in fragments}
    modes = {str(getattr(item, "retrieval_mode", "") or "").lower() for item in fragments}
    if "INDEX_SNIPPET" in depths or "web_search_index" in modes:
        return "SEARCH_DISCOVERY_ONLY"
    if "FEED_ENTRY_SUMMARY" in depths or "rss_feed" in modes:
        return "SYNDICATED_SUMMARY"
    if depths and depths <= {"PROFILE_METADATA", "VIDEO_METADATA", "HEADLINE_ONLY", "METADATA"}:
        return "DIRECT_METADATA"
    if depths & {"SNIPPET", "PARTIAL_CONTENT"}:
        return "DIRECT_PARTIAL_CONTENT"
    if depths & {
        "FULL_ARTICLE", "FULL_CONTENT", "PRIMARY_DOCUMENT", "REGULATORY_FILING",
        "OFFICIAL_STATEMENT", "SOCIAL_POST", "TWEET_STATUS", "COMMENT", "COMMENTS",
        "VIDEO_TRANSCRIPT",
    }:
        return "DIRECT_FULL_CONTENT"
    return "DIRECT_PARTIAL_CONTENT"


def _probe(spec: ProbeSpec, sequence: int) -> dict[str, Any]:
    runtime_operation_capabilities.reset_observations()
    router = NativeRouter()
    started = time.perf_counter()
    fragments, telemetry = router.execute_channel_query(
        spec.channel,
        spec.target,
        operation=spec.action,
        limit=3,
        query_id=f"phase8_{sequence:03d}",
        query_class="phase8_bounded_live_probe",
        query_text=spec.target,
        public_mode=False,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    transport = _transport_records(fragments, telemetry)
    network_observed = bool(telemetry.get("network_observed")) or any(
        item["network_observed_this_attempt"] for item in transport
    )
    classification = classify_probe(
        telemetry=telemetry, fragments=fragments,
        missing_is_not_found=spec.missing_is_not_found,
    )
    samples = []
    for fragment in fragments[:3]:
        content = str(getattr(fragment, "content", "") or "")
        metadata = getattr(fragment, "raw_metadata", {}) or {}
        samples.append({
            "title": _redact(getattr(fragment, "title", "")),
            "canonical_url": _redact(getattr(fragment, "url", "")),
            "author": _redact(getattr(fragment, "author", "")),
            "content_chars": len(content),
            "content_sha256": hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest(),
            "bounded_excerpt": content[:400],
            "published": _redact(getattr(fragment, "published", "")),
            "requested_channel": getattr(fragment, "requested_channel", None),
            "actual_retrieval_channel": getattr(fragment, "actual_retrieval_channel", None),
            "backend_id": getattr(fragment, "native_backend_id", None),
            "content_depth": getattr(fragment, "content_depth", None),
            "retrieval_mode": getattr(fragment, "retrieval_mode", None),
            "populated_metadata_field_names": sorted(
                key for key, value in metadata.items()
                if key != "transport" and value is not None and value != ""
                and value != [] and value != {}
            ),
            "populated_video_metadata_field_names": sorted(
                key for key, value in (metadata.get("video_metadata") or {}).items()
                if value is not None and value != "" and value != [] and value != {}
            ),
            "populated_provider_field_names": sorted(
                key for key, value in (metadata.get("provider_fields") or {}).items()
                if value is not None and value != "" and value != [] and value != {}
            ),
            "populated_page_metadata_field_names": sorted(
                key for key, value in (metadata.get("page_metadata") or {}).items()
                if value is not None and value != "" and value != [] and value != {}
            ),
        })
    backends = sorted({
        str(getattr(fragment, "native_backend_id", "") or "") for fragment in fragments
        if getattr(fragment, "native_backend_id", None)
    })
    return {
        **asdict(spec),
        "probe_id": f"P8A-{sequence:03d}",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "classification": classification,
        "evidence_origin": "ACTUAL_LIVE_PROVIDER_TRAFFIC" if network_observed else "UNVERIFIED",
        "live_verified": network_observed and classification in SUCCESS_CLASSIFICATIONS,
        "provider_or_adapter": backends or [telemetry.get("backend")],
        "network_io_observed": network_observed,
        "http_statuses": sorted({
            int(item) for item in telemetry.get("http_statuses", []) if item is not None
        } | {
            int(item["http_status"]) for item in transport if item.get("http_status") is not None
        }),
        "response_content_types": sorted({
            str(item["content_type"]) for item in transport if item.get("content_type")
        }),
        "response_bytes": sum(int(item.get("raw_body_bytes") or 0) for item in transport),
        "item_count": len(fragments),
        "adapter_result_field_names": telemetry.get("adapter_result_field_names", []),
        "adapter_item_field_names": telemetry.get("adapter_item_field_names", []),
        "field_name_scope": "Parsed adapter result items; not a raw provider schema guarantee",
        "relevant_text_chars": sum(len(str(getattr(item, "content", "") or "")) for item in fragments),
        "content_depths": sorted({str(getattr(item, "content_depth", "") or "UNKNOWN") for item in fragments}),
        "retrieval_modes": sorted({str(getattr(item, "retrieval_mode", "") or "UNKNOWN") for item in fragments}),
        "pagination_coverage": PAGINATION.get(spec.operation, "NOT_IMPLEMENTED_OR_NOT_APPLICABLE"),
        "authentication_requirement": required_auth_environment(spec.channel, spec.action),
        "rate_limit_observed": classification == "RATE_LIMITED",
        "rate_limit_remaining": telemetry.get("rate_limit_remaining"),
        "rate_limit_reset_at": telemetry.get("rate_limit_reset_at"),
        "failure_reason": _redact(telemetry.get("error")),
        "latency_ms": elapsed_ms,
        "freshness_values": sorted({
            str(getattr(item, "published", "") or "") for item in fragments
            if getattr(item, "published", None)
        })[:10],
        "provenance": {
            "production_dispatcher": "NativeRouter.execute_channel_query",
            "transport": transport,
            "normalized_evidence_samples": samples,
            "raw_response_body_retained": False,
            "raw_response_proof": "bounded byte count and SHA-256 where the HTTP adapter exposed them",
        },
        "telemetry": {
            key: telemetry.get(key) for key in (
                "status", "outcome", "content_class", "attempts", "fallback_used",
                "fallback_backend", "retry_after_seconds", "runtime_decision",
                "rate_limit_remaining", "rate_limit_reset_at",
                "provider_status",
            )
        },
    }


def _failed_probe(spec: ProbeSpec, sequence: int, error: BaseException) -> dict[str, Any]:
    return {
        **asdict(spec), "probe_id": f"P8A-{sequence:03d}",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "classification": "NETWORK_FAILURE", "evidence_origin": "UNVERIFIED",
        "live_verified": False, "network_io_observed": False, "http_statuses": [],
        "item_count": 0, "relevant_text_chars": 0, "latency_ms": None,
        "failure_reason": _redact(f"{type(error).__name__}: {error}"),
        "provenance": {"raw_response_body_retained": False, "transport": []},
    }


def _aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["operation"]].append(record)
    operations = {}
    for operation, values in sorted(grouped.items()):
        verified = [item for item in values if item.get("live_verified")]
        operations[operation] = {
            "protected": operation in PROTECTED_OPERATIONS,
            "status": "LIVE_VERIFIED" if verified else "NOT_LIVE_VERIFIED",
            "verified_classifications": sorted({item["classification"] for item in verified}),
            "probe_count": len(values),
            "live_verified_probe_count": len(verified),
            "classifications": {name: sum(item["classification"] == name for item in values)
                                for name in sorted({item["classification"] for item in values})},
            "limitations": sorted({item.get("failure_reason") for item in values if item.get("failure_reason")}),
        }
    missing = sorted(set(PROTECTED_OPERATIONS) - set(operations))
    unverified = sorted(
        operation for operation in PROTECTED_OPERATIONS
        if operations.get(operation, {}).get("status") != "LIVE_VERIFIED"
    )
    return {
        "gate": "PASS" if not missing and not unverified else "PARTIAL",
        "protected_operation_count": len(PROTECTED_OPERATIONS),
        "live_verified_operation_count": len(PROTECTED_OPERATIONS) - len(unverified),
        "missing_operations": missing,
        "not_live_verified_operations": unverified,
        "operations": operations,
    }


def consolidate_run_records(run_directories: Iterable[Path]) -> list[dict[str, Any]]:
    """Select the newest complete probe set for each operation across runs.

    Later directories override an operation as a whole.  This prevents a fixed
    adapter from being mixed with stale probes for the same operation while
    allowing bounded retry runs after provider rate limits.
    """
    latest_by_operation: dict[str, list[dict[str, Any]]] = {}
    for directory in run_directories:
        path = directory / "probe_records.jsonl"
        if not path.is_file():
            raise FileNotFoundError(f"Missing probe record file: {path}")
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                record["evidence_run"] = directory.as_posix()
                grouped[record["operation"]].append(record)
        latest_by_operation.update(grouped)
    return [
        record
        for operation in sorted(latest_by_operation)
        for record in latest_by_operation[operation]
    ]


def _auxiliary_inventory() -> list[dict[str, Any]]:
    rows = []
    for channel in sorted(set(CAPABILITY_MATRIX) | set(EXECUTABLE_CAPABILITIES)):
        declared = set(CAPABILITY_MATRIX.get(channel).operations) if channel in CAPABILITY_MATRIX else set()
        for operation in sorted(declared | EXECUTABLE_CAPABILITIES.get(channel, set())):
            key = f"{channel}.{operation}"
            if key in PROTECTED_OPERATIONS:
                continue
            assessment = runtime_operation_capabilities.assess(channel, operation)
            rows.append({
                "operation": key,
                "declared": operation in declared,
                "handler_available": operation in EXECUTABLE_CAPABILITIES.get(channel, set()),
                "auth_environment": assessment["auth_environment"],
                "policy_eligible": assessment["policy_eligible"],
                "runtime_decision_before_live_probe": assessment["decision"],
                "note": "Static inventory; live evidence is recorded only when a matching probe exists.",
            })
    return rows


def _write_markdown(path: Path, aggregate: dict[str, Any], sha: str) -> None:
    lines = [
        "# Phase 8A real acquisition capability matrix", "",
        f"- Commit: `{sha}`", f"- Gate: **{aggregate['gate']}**",
        f"- Protected operations live-verified: {aggregate['live_verified_operation_count']} / {aggregate['protected_operation_count']}",
        "- A live verification requires adapter-level network observation and usable, honestly classified output.",
        "- Response bodies are not retained; bounded hashes/byte counts and normalized excerpts provide reproducible proof without storing whole copyrighted documents.",
        "", "| Operation | Status | Verified depth | Probes | Live probes |", "|---|---|---|---:|---:|",
    ]
    for operation in PROTECTED_OPERATIONS:
        row = aggregate["operations"].get(operation, {})
        depths = ", ".join(row.get("verified_classifications", [])) or "none"
        lines.append(
            f"| `{operation}` | {row.get('status', 'NOT_PROBED')} | {depths} | "
            f"{row.get('probe_count', 0)} | {row.get('live_verified_probe_count', 0)} |"
        )
    if aggregate["not_live_verified_operations"]:
        lines += ["", "## Gate limitations", ""] + [
            f"- `{operation}` was not independently live-verified."
            for operation in aggregate["not_live_verified_operations"]
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    router_source = Path(sys.modules[NativeRouter.__module__].__file__).resolve()
    if not router_source.is_relative_to(repository_root):
        raise RuntimeError("Audit would execute acquisition code from a different checkout")
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="artifacts/phase8_live_acquisition")
    parser.add_argument("--max-scenarios", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument("--operations", help="Comma-separated operation filter")
    parser.add_argument("--include-auxiliary", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument(
        "--consolidate-runs", nargs="+", type=Path,
        help="Create an acceptance artifact from existing runs; later runs override an operation.",
    )
    args = parser.parse_args()

    operation_filter = {
        item.strip() for item in (args.operations or "").split(",") if item.strip()
    }
    selected: list[ProbeSpec] = []
    seen_counts: dict[str, int] = defaultdict(int)
    for spec in [*PROBES, *(AUXILIARY_PROBES if args.include_auxiliary else ())]:
        if operation_filter and spec.operation not in operation_filter:
            continue
        if seen_counts[spec.operation] >= args.max_scenarios:
            continue
        selected.append(spec)
        seen_counts[spec.operation] += 1

    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%SZ")
    output_dir = Path(args.output_root) / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    if args.consolidate_runs:
        records = consolidate_run_records(args.consolidate_runs)
    else:
        records = []
        for sequence, spec in enumerate(selected, 1):
            print(f"[{sequence}/{len(selected)}] {spec.operation} {spec.scenario}", flush=True)
            try:
                record = _probe(spec, sequence)
            except Exception as error:  # keep the remainder of the acceptance run observable
                record = _failed_probe(spec, sequence, error)
            records.append(record)
            print(
                f"  -> {record['classification']} live={record.get('live_verified', False)} "
                f"items={record.get('item_count', 0)} latency_ms={record.get('latency_ms')}",
                flush=True,
            )

    aggregate = _aggregate(records)
    sha = _git_value("rev-parse", "HEAD")
    metadata = {
        "schema_version": "phase8-live-acquisition-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": sha,
        "branch": _git_value("branch", "--show-current"),
        "worktree_dirty": bool(_git_value("status", "--porcelain")),
        "router_source": router_source.relative_to(repository_root).as_posix(),
        "python": sys.version,
        "tools": {name: bool(shutil.which(name)) for name in ("gh", "yt-dlp")},
        "credential_presence": {
            name: bool(os.getenv(name)) for name in (
                "GITHUB_TOKEN", "YOUTUBE_API_KEY", "GROQ_API_KEY",
            )
        },
        "probe_budget": {"max_scenarios_per_operation": args.max_scenarios, "result_limit": 3},
        "evidence_policy": "No complete response bodies or secrets retained.",
        "consolidated_source_runs": [path.as_posix() for path in args.consolidate_runs or []],
    }
    (output_dir / "probe_records.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
        encoding="utf-8",
    )
    (output_dir / "acceptance.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    (output_dir / "auxiliary_operation_inventory.json").write_text(
        json.dumps(_auxiliary_inventory(), indent=2, ensure_ascii=False), encoding="utf-8",
    )
    _write_markdown(output_dir / "REAL_ACQUISITION_CAPABILITY_MATRIX.md", aggregate, sha)
    print(output_dir.as_posix(), flush=True)
    print(f"PHASE8A_GATE={aggregate['gate']}", flush=True)
    return 2 if args.require_pass and aggregate["gate"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
