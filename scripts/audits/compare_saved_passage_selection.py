"""Compare saved genuine native responses; no network, AI or evidence rewriting.

--case label=before.json=after.json may repeat. Outputs hashes, selected exact
spans and role/financial labels, not complete captured bodies. Paths are omitted
from the durable output. Both inputs must already contain raw pools.
"""
import argparse
import hashlib
import json
from pathlib import Path


def inspect(payload):
    corpus = payload.get("research_corpus") or {}
    raw = corpus["raw_acquisition_pool"]
    deep = {row["id"]: row for row in corpus.get("deep_read_sources", [])}
    records = {}
    for source in raw["sources"]:
        if source["source_type"] not in {"ARTICLE_BODY", "OFFICIAL_DOCUMENT"}:
            continue
        row = deep.get(source["source_id"], {})
        body, excerpt = source["readable_text"], row.get("relevant_excerpt") or ""
        start, end = row.get("excerpt_start"), row.get("excerpt_end")
        if hashlib.sha256(body.encode()).hexdigest() != source["raw_content_hash"]:
            raise ValueError("Recorded body hash mismatch")
        exact = bool(excerpt and type(start) is int and type(end) is int and body[start:end] == excerpt)
        if excerpt and not exact:
            raise ValueError("Selected excerpt is not the recorded capture span")
        records[source["source_id"]] = {"source_id": source["source_id"], "url": source["source_url"],
            "published_at": source.get("published_at"), "body_sha256": source["raw_content_hash"],
            "body_words": len(body.split()), "selected_words": len(excerpt.split()),
            "selected_passage": excerpt, "start": start, "end": end, "exact_capture_span": exact,
            "qualification": source["qualification_status"], "reasons": source["qualification_reasons"],
            "source_context": (row.get("metadata") or {}).get("trend_source_context")}
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"mode": "GENUINE_SAVED_RESPONSE_COMPARISON_NOT_LIVE", "network_calls": 0, "model_calls": 0, "cases": []}
    for spec in args.case:
        label, before_path, after_path = spec.split("=", 2)
        before_bytes, after_bytes = Path(before_path).read_bytes(), Path(after_path).read_bytes()
        before, after = json.loads(before_bytes), json.loads(after_bytes)
        previous, current = inspect(before), inspect(after)
        if set(previous) != set(current) or any(previous[key]["body_sha256"] != current[key]["body_sha256"]
                or previous[key]["url"] != current[key]["url"] for key in previous):
            raise ValueError("Raw article inventory/identity/body changed")
        case = {"label": label, "before_response_sha256": hashlib.sha256(before_bytes).hexdigest(),
            "after_response_sha256": hashlib.sha256(after_bytes).hexdigest(),
            "raw_article_identity_body_preserved": True,
            "articles": [{"before": previous[key], "after": current[key]} for key in previous],
            "primary_topic_coverage": after.get("primary_topic_coverage"),
            "financial_context_summary": after.get("financial_context_summary"),
            "financial_observations": [{key: value for key, value in row.items() if key in {
                "evidence_id", "published_at", "observed_at", "publication_scope", "content_kind",
                "observed_period_labels", "title_period_labels", "observed_currencies", "result_scope",
                "issuer_alignment", "filing_comparison_status", "financial_assessment_eligible"}}
                for row in after.get("financial_observations", [])],
            "filing_comparison_status": (after.get("filing_comparison") or {}).get("status"),
            "investigation_status": after.get("investigation_status")}
        result["cases"].append(case)
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if output.exists() or any(output.is_relative_to(root / name) for name in
            ("research", "artifacts", "backend/data/dossiers", "tests/retrieval_benchmark")):
        raise ValueError("Output must be new and outside protected data")
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"cases": len(result["cases"]), "raw_identity_preserved": True,
        "mode": result["mode"], "network_calls": 0, "model_calls": 0}))


if __name__ == "__main__":
    main()
