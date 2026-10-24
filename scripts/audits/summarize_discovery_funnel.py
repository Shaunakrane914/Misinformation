"""Summarize saved local captures without importing the app or using network/AI.

Counters describe the capture's own code version, not current recomputation.
Writes only an explicitly new output file; never edits native evidence files.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def locator(url):
    try:
        parsed = urlsplit(url or "")
        return urlunsplit((parsed.scheme, parsed.hostname or "", parsed.path, "", ""))[:500]
    except ValueError:
        return "INVALID_URL"


def summarize(directory):
    manifest = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    cases = []
    for case in manifest["cases"]:
        path = directory / (case["case_id"] + ".json")
        data = json.loads(path.read_text(encoding="utf-8"))
        trace = data.get("retrieval_trace") or {}
        funnel = trace.get("discovery_funnel") or {}
        providers = funnel.get("provider_observations", [])
        cases.append({
            "case_id": case["case_id"], "agent": case["agent"], "input": case["input"],
            "seconds": case["seconds"], "native_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "investigation_status": data.get("investigation_status"),
            "initial_generated_queries": len(funnel.get("generated_queries", [])),
            "funnel": {key: value for key, value in funnel.items() if key not in {
                "generated_queries", "provider_observations", "qualification_rejections", "read_attempts", "publisher_link_audit"}},
            "provider_outcomes": dict(Counter(row.get("provider", "UNKNOWN") + ":" + row.get("status", "UNKNOWN") for row in providers)),
            "read_failures": [{"candidate_id": row.get("candidate_id"), "url": locator(row.get("url")),
                "failure_kind": row.get("failure_kind"), "http_status": row.get("http_status"),
                "resolver_query_statuses": [query.get("status") for query in (row.get("wrapper_resolution") or {}).get("query_records", [])]}
                for row in funnel.get("read_attempts", []) if row.get("status") != "SUCCESS"],
            "captures": [{"id": source.get("id"), "url": locator(source.get("canonical_url")),
                "title": source.get("title"), "words": len((source.get("content") or "").split()),
                "kb": round(len((source.get("content") or "").encode("utf-8")) / 1000, 3),
                "text_sha256": hashlib.sha256((source.get("content") or "").encode("utf-8")).hexdigest(),
                "extraction_status": source.get("extraction_status")}
                for source in (data.get("research_corpus") or {}).get("deep_read_sources", [])],
            "displayed_findings": len((data.get("unified_report") or {}).get("findings", [])),
            "remaining_research_seconds": (trace.get("budget_observations") or {}).get("remaining_after_processing_seconds"),
        })
    return {"mode": manifest["mode"], "application_sha256": manifest.get("application_sha256"),
        "stable_application": manifest.get("stable_application"), "live_ai_authorized": manifest.get("live_ai_authorized"),
        "bounds": manifest.get("requested_audit_bounds"), "cases": cases,
        "limitations": "Observed samples, not unique URL totals, complete HTTP accounting, calibrated entailment or independent accuracy; saved-mode attempts are historical observations."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.capture_dir)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    print(json.dumps({"mode": result["mode"], "cases": len(result["cases"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
