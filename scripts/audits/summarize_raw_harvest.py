"""Read-only measurements from an existing terminal harvest capture directory.

No application import, network, model call, source reprocessing or capture edits.
Writes only a new output file. Raw-pool article/qualification labels are recorded
as saved observations, not independently verified truth or source independence.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlsplit


_SENSITIVE = re.compile(r"token|api[_-]?key|secret|password|authorization|cookie|signature|credential", re.I)
_DOMAINS = {"scout": "financial", "brandshield": "brand", "trending": "trending", "personal_watch": "personal"}


def _load(path):
    if not path.is_file():
        return {}
    if path.stat().st_size > 50_000_000:
        raise ValueError("Capture exceeds 50 MB read limit: " + path.name)
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else {}


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _url(value):
    """Keep exact public locators; never silently redact into another resource."""
    if not isinstance(value, str) or not value:
        return None
    try:
        p = urlsplit(value)
        if (len(value) > 8192 or p.scheme not in {"http", "https"} or not p.hostname
                or p.username or p.password or any(_SENSITIVE.search(k) for k, _ in parse_qsl(p.query))):
            return "WITHHELD_INVALID_OR_SENSITIVE_LOCATOR"
        return value
    except ValueError:
        return "WITHHELD_INVALID_OR_SENSITIVE_LOCATOR"


def _host(value):
    try:
        return (urlsplit(value or "").hostname or "").lower()
    except ValueError:
        return ""


def _wrapper(value):
    try:
        p = urlsplit(value or "")
        return (p.hostname == "news.google.com" or (p.hostname or "").endswith("bing.com")
                and "/news/apiclick" in p.path)
    except ValueError:
        return False


def _rows(value):
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _transport(source, captures):
    ids = {source.get("source_id"), *source.get("aliases", [])} - {None, ""}
    matching = [row for row in captures if row.get("canonical_url") == source.get("source_url")]
    basis = "EXACT_SAVED_SOURCE_URL"
    if not matching:
        candidates = [row for row in captures if (row.get("id") or row.get("evidence_id")) in ids]
        matching = candidates if len(candidates) == 1 else []
        basis = "UNIQUE_SAVED_ID" if matching else "UNAVAILABLE_OR_AMBIGUOUS_ID"
    meta = (matching[0].get("metadata") or {}) if matching else {}
    transport = meta.get("transport") or {}
    return {"transport_join_basis": basis, "observed_endpoint": _url(transport.get("endpoint")),
            "observed_endpoint_host": _host(transport.get("endpoint")) or None,
            "http_status": transport.get("http_status"),
            "network_observed_this_attempt": transport.get("network_observed_this_attempt"),
            "redirect_chain": [_url(value) for value in transport.get("redirect_chain", [])[:10]],
            "source_body_hash": transport.get("raw_body_sha256"),
            "endpoint_is_search_wrapper": _wrapper(transport.get("endpoint"))}


def _source_metadata(source, captures):
    return {"source_id": source.get("source_id"), "source_url": _url(source.get("source_url")),
            "original_url_is_search_wrapper": _wrapper(source.get("source_url")),
            "saved_source_label": source.get("publisher"), "saved_publisher_host": source.get("publisher_host"),
            "title": source.get("title"), "published_at": source.get("published_at"),
            "publication_time_basis": source.get("publication_time_basis"),
            "source_type": source.get("source_type"), "qualification_status": source.get("qualification_status"),
            "qualification_reasons": source.get("qualification_reasons"),
            "acquisition_method": source.get("acquisition_method"), "content_depth": source.get("content_depth"),
            "retained_word_count": source.get("word_count"), "useful_words": source.get("useful_words"),
            "readable_text_sha256": source.get("raw_content_hash"), "duplicate_of": source.get("duplicate_of"),
            "provider_truncated": source.get("provider_truncated"), "transport": _transport(source, captures)}


def _dossier_summary(path, dossier):
    snapshots = dossier.get("candidate_snapshots") or {}
    words = sum(len(str(row.get("content") or "").split()) for row in snapshots.values() if isinstance(row, dict))
    return {"file": path.name, "sha256": _hash(path), "session_id": dossier.get("session_id"),
            "target": dossier.get("target"), "domain": dossier.get("domain"),
            "internal_status": dossier.get("status"), "latency_ms": dossier.get("latency_ms"),
            "acquisition": dossier.get("acquisition"), "stage_timings_ms": (dossier.get("timing") or {}).get("stage_timings_ms"),
            "snapshot_count": len(snapshots), "snapshot_text_words": words,
            "finding_provenance_count": len(dossier.get("findings_provenance") or []),
            "returned_to_user": False,
            "limitation": "Isolated internal dossier, not a completed returned API report. Snapshot text does not establish article type, qualification or accuracy."}


def summarize(run_dir):
    manifest = _load(run_dir / "summary.json")
    if not manifest:
        raise ValueError("A terminal summary.json is required")
    dossiers = [(path, _load(path)) for path in sorted((run_dir / "dossiers").glob("*.json"))]
    cases = []
    for case in _rows(manifest.get("cases")):
        case_id = str(case.get("case_id") or "")
        if not re.fullmatch(r"\d{2}-[a-z_]+", case_id):
            raise ValueError("Invalid case_id locator")
        native_path, pipeline_path = run_dir / (case_id + ".json"), run_dir / (case_id + "-pipeline.json")
        native, pipeline = _load(native_path), _load(pipeline_path)
        corpus = pipeline.get("research_corpus") or native.get("research_corpus") or {}
        trace = native.get("retrieval_trace") or native.get("deep_research_trace") or {}
        pool = corpus.get("raw_acquisition_pool") or trace.get("raw_acquisition_pool") or {}
        has_pool = bool(pool.get("schema_version") or "stats" in pool)
        sources = _rows(pool.get("sources"))
        captures = _rows(corpus.get("deep_read_sources"))
        queries = _rows(corpus.get("queries")) or _rows(trace.get("query_records"))
        attempts = _rows(trace.get("acquisition_attempts"))
        harvesting = trace.get("harvesting") or {}
        stats = pool.get("stats") or {}
        structured_findings = _rows(corpus.get("findings"))
        displayed_findings = (native.get("unified_report") or {}).get("findings") or []
        ids = {}
        for source in sources:
            for identity in [source.get("source_id"), *source.get("aliases", [])]:
                if identity:
                    records = ids.setdefault(identity, [])
                    if source.get("source_id") not in {row.get("source_id") for row in records}:
                        records.append(source)
        ambiguous_ids = {identity: [row.get("source_id") for row in records] for identity, records in ids.items() if len(records) > 1}
        references, repeated_citations = [], 0
        for finding in structured_findings:
            found = finding.get("supporting_evidence_ids") or finding.get("evidence_ids") or []
            repeated_citations += len(found) - len(set(found))
            for identity in found:
                targets = ids.get(identity, [])
                target = targets[0] if len(targets) == 1 else None
                references.append({"finding_id": finding.get("finding_id") or finding.get("id"),
                    "evidence_id": identity, "join_status": "AMBIGUOUS_SOURCE_ID" if len(targets) > 1 else "RAW_POOL_RECORD" if target else "UNAVAILABLE",
                    "source_type": target.get("source_type") if target else None,
                    "qualification_status": target.get("qualification_status") if target else None})
        metadata = [_source_metadata(source, captures) for source in sources if source.get("extraction_status") == "SUCCESS"]
        articles = [row for row in metadata if row["source_type"] == "ARTICLE_BODY" and not row["duplicate_of"]]
        qualified = [row for row in metadata if row["qualification_status"] == "QUALIFIED" and not row["duplicate_of"]]
        actual_hosts = sorted({row["transport"]["observed_endpoint_host"] for row in articles
                               if row["transport"]["observed_endpoint_host"] and not row["transport"]["endpoint_is_search_wrapper"]})
        qualified_actual_hosts = sorted({row["transport"]["observed_endpoint_host"] for row in qualified
                                         if row["transport"]["observed_endpoint_host"] and not row["transport"]["endpoint_is_search_wrapper"]})
        legacy = {key: case.get(key) for key in ("records", "words", "kb")}
        legacy.update(displayed_finding_strings=len(displayed_findings), structured_findings=len(structured_findings))
        discrepancies = []
        if legacy["records"] != stats.get("article_bodies"):
            discrepancies.append("Legacy source-record count is not the raw-pool article-body count.")
        if legacy["words"] != stats.get("raw_article_words"):
            discrepancies.append("Legacy retained words include nonarticle/homepage/index or metadata content.")
        if len(structured_findings) > stats.get("qualified_source_count", 0):
            discrepancies.append("Structured findings outnumber qualified sources; this is not independent claim verification.")
        if any(row["original_url_is_search_wrapper"] for row in articles):
            discrepancies.append("Saved source/publisher hosts include search wrappers; observed transport endpoints are reported separately, without assuming independence.")
        if ambiguous_ids:
            discrepancies.append("Native evidence IDs/aliases collide across distinct source URLs; citation joins and saved qualifications may be incomplete or ambiguous.")
        returned = bool(case.get("result_event"))
        isolated = []
        if not returned:
            for path, dossier in dossiers:
                if (str(dossier.get("target") or "").casefold() == str(case.get("input") or "").casefold()
                        and dossier.get("domain") == _DOMAINS.get(case.get("agent"))):
                    isolated.append(_dossier_summary(path, dossier))
        cases.append({"case_id": case_id, "agent": case.get("agent"), "input": case.get("input"),
            "returned_result_event": returned, "http_status": case.get("http_status"), "seconds": case.get("seconds"),
            "error_events": case.get("error_events"), "investigation_status": native.get("investigation_status"),
            "native_sha256": _hash(native_path), "pipeline_sha256": _hash(pipeline_path),
            "research_profile": trace.get("research_profile") or harvesting.get("profile"),
            "generated_queries": harvesting.get("queries_generated"), "query_record_count": len(queries) if returned or queries else None,
            "query_status_counts": dict(Counter(row.get("status", "UNKNOWN") for row in queries)) if returned or queries else None,
            "providers_contacted": dict(Counter(str(attempt.get("provider", "UNKNOWN")) for row in queries
                for attempt in _rows(row.get("search_attempts")) if attempt.get("provider_invoked"))),
            "harvesting_observations": harvesting, "raw_pool_stats": stats or None,
            "captured_source_types": dict(Counter(row["source_type"] for row in metadata)),
            "recomputed_raw_article_bodies": len(articles) if has_pool else None,
            "recomputed_raw_article_words": sum(row["retained_word_count"] or 0 for row in articles) if has_pool else None,
            "qualified_sources": len(qualified) if has_pool else None,
            "qualified_useful_words": sum(row["useful_words"] or 0 for row in qualified) if has_pool else None,
            "observed_article_endpoint_hosts": actual_hosts, "observed_qualified_endpoint_hosts": qualified_actual_hosts,
            "observed_unique_article_endpoints": len({row["transport"]["observed_endpoint"] for row in articles if row["transport"]["observed_endpoint"]}),
            "publisher_independence": "NOT_VERIFIED", "article_metadata": articles, "qualified_source_metadata": qualified,
            "read_attempt_count": len(attempts) if returned or attempts else None,
            "read_status_counts": dict(Counter(row.get("status", "UNKNOWN") for row in attempts)) if returned or attempts else None,
            "read_failure_categories": dict(Counter(row.get("failure_kind") or "UNKNOWN" for row in attempts if row.get("status") != "SUCCESS")),
            "legacy_projection": legacy, "projection_limitations": discrepancies,
            "citation_reference_count": len(references), "duplicate_citations_within_findings": repeated_citations,
            "ambiguous_native_source_ids": ambiguous_ids,
            "citation_joins": references, "citation_entailment": "NOT_VERIFIED",
            "ai_observations": trace.get("ai_advisory_observations") or [], "isolated_not_returned_dossiers": isolated})
    return {"schema": "raw-harvest-audit-summary-v1", "mode": "READ_ONLY_SAVED_OBSERVATIONS",
        "source_run_mode": manifest.get("mode"), "application_sha256": manifest.get("application_sha256"),
        "final_application_sha256": manifest.get("final_application_sha256"), "stable_application": manifest.get("stable_application"),
        "requested_audit_bounds": manifest.get("requested_audit_bounds"), "model_check": manifest.get("advisory_model_check"),
        "ai_calls_reserved": manifest.get("live_ai_calls_reserved"), "ai_observations": manifest.get("live_ai_observations"),
        "cases": cases, "limitations": ["No network or AI call; no source requalification or original capture edits.",
            "Raw-pool article and qualification decisions are the saved code's classifications, not independent accuracy acceptance.",
            "Different endpoint hosts do not establish independent reporting; publication declarations are not independently verified dates.",
            "No-result cases retain unknown article/qualification counts; internal dossiers are disclosed separately, not promoted to returned results.",
            "Body text, headers and credentials are excluded. Exact public source/transport URLs are retained unless credential-shaped."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = summarize(args.run_dir)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    print(json.dumps({"mode": result["mode"], "cases": len(result["cases"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
