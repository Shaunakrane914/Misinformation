"""Sanitized, read-only measurements of saved native source/report envelopes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def measure(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 80_000_000:
        raise ValueError("Use a bounded regular native response")
    encoded = path.read_bytes()
    payload = json.loads(encoded)
    from scripts.audits.requalify_raw_pool import locate_pool
    pool = locate_pool(payload)
    report = payload.get("unified_report") or {}
    trace = payload.get("deep_research_trace") or payload.get("retrieval_trace") or {}
    workbench = report.get("evidence_workbench") or {}
    sources = pool.get("sources", [])
    articles = [row for row in sources if row.get("source_type") in {"ARTICLE_BODY", "OFFICIAL_DOCUMENT"}
                and row.get("readable_text") and not row.get("duplicate_of")]
    qualified = [row for row in sources if row.get("qualification_status") == "QUALIFIED"]
    passages = workbench.get("passages") or []
    original_records = {row.get("source_id"): row for row in sources}
    exact = all(row.get("evidence_id") in original_records
        and original_records[row["evidence_id"]].get("readable_text", "")[row["start"]:row["end"]] == row["text"]
        for row in passages)
    acquisition = trace.get("acquisition_metrics") or {}
    harvesting = trace.get("harvesting") or {}
    return {"agent": report.get("_meta", {}).get("agent"), "input_sha256": hashlib.sha256(encoded).hexdigest(),
        "investigation_status": report.get("investigation_status"), "article_bodies": len(articles),
        "raw_article_words": sum(len(row["readable_text"].split()) for row in articles),
        "raw_article_utf8_kb": round(sum(len(row["readable_text"].encode("utf-8")) for row in articles) / 1000, 3),
        "qualified_sources": len(qualified), "selected_excerpt_words": sum(row.get("useful_words", 0) for row in qualified),
        "workbench": workbench.get("accounting"), "all_published_spans_match_retained_bodies": exact,
        "published_sources": [{"source_id": row["source_id"], "source_url": row.get("source_url"),
                               "body_sha256": row.get("raw_content_hash")} for row in qualified],
        "workbench_role_words": {role: sum(len(row["text"].split()) for row in passages if row["content_role"] == role)
                                 for role in sorted({row["content_role"] for row in passages})},
        "discovery": {key: harvesting.get(key) for key in ("queries_generated", "reads_attempted", "captures",
            "source_diversity", "failure_categories", "unread_by_reason", "native_http_admissions", "complete_network_accounting")},
        "funnel": {key: (trace.get("discovery_funnel") or {}).get(key) for key in (
            "generated_queries", "candidate_urls_discovered", "accepted_candidates", "reads_attempted",
            "successful_body_captures", "qualified_evidence", "first_observed_empty_boundary")},
        "acquisition_metrics": {key: acquisition.get(key) for key in ("article_bodies", "qualified_source_count", "relevant_words")},
        "scope": "Code-selected source assertions; no independent accuracy, completeness or 20x acceptance asserted"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, action="append", required=True)
    parser.add_argument("--mode", choices=("SAVED_SOURCE_REPLAY", "AUTHORIZED_LIVE_BATCH"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    protected = [ROOT / directory for directory in ("research", "artifacts", "backend/data/dossiers", "tests/retrieval_benchmark")]
    if output.exists() or any(output == path or output.is_relative_to(path) for path in protected):
        raise ValueError("Use a fresh measurement file outside protected data")
    rows = [measure(path) for path in args.result]
    summary = {"mode": args.mode, "target_multiplier": 20, "target_status": "NOT_DEMONSTRATED",
        "cases": rows, "limitations": ["Raw text is not useful evidence; selected words are not independently verified.",
        "A selected-excerpt to workbench ratio is not growth over all previously inspectable frontend text.",
        "Fresh live batches are not controlled before/after comparisons; source availability and dates may change."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"mode": args.mode, "cases": len(rows), "exact_span_checks": all(row["all_published_spans_match_retained_bodies"] for row in rows)}))
    return 0 if all(row["all_published_spans_match_retained_bodies"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
