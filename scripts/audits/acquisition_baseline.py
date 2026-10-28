"""Reproducible offline evidence-yield baseline for saved native investigations.

One measurement code path serves both the saved baseline and any new run, so the
definitions of "qualified", "relevant passage words" and "publisher group" are
identical on both sides of a comparison. Nothing here touches the network, a model
or any input file, and every reported field carries its provenance:

* MEASURED      copied from telemetry the original run recorded
* DERIVED       recomputed offline from the saved bytes by deterministic code
* NOT_RECORDED  the original run did not capture it (never estimated silently)
* REVIEWED      a separate manual label file; absent unless supplied

Qualification here is relevance/structure/date eligibility of captured text. It is
not a verdict, not source independence, and not independent accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import statistics
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOMAINS = {"scout": "financial", "brandshield": "brand", "trending": "trending", "personal_watch": "personal"}
MULTIPART_SUFFIXES = {"co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "co.in", "co.jp", "co.nz", "com.br", "com.sg",
                      "com.hk", "com.cn", "co.za", "com.mx"}
LEGACY_VERBS = re.compile(r"\b(?:is|are|was|were|has|have|allows|contains|includes|limits|rated)\b", re.I)
MEASURED, DERIVED, NOT_RECORDED = "MEASURED", "DERIVED", "NOT_RECORDED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def publisher_group(host: str) -> str:
    """Registrable-domain approximation. An observed host group, not an owner."""
    labels = [part for part in (host or "").lower().strip(".").split(".") if part]
    if labels[:1] == ["www"]:
        labels = labels[1:]
    if len(labels) <= 2:
        return ".".join(labels)
    return ".".join(labels[-3:]) if ".".join(labels[-2:]) in MULTIPART_SUFFIXES else ".".join(labels[-2:])


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.casefold())).strip()


def deduplicate_passages(passages):
    """Exact duplicates and contained passages count once; the longer text is kept."""
    kept = []
    for passage in sorted(passages, key=lambda p: -len(p["normalized"])):
        if any(passage["normalized"] == other["normalized"] or passage["normalized"] in other["normalized"] for other in kept):
            continue
        kept.append(passage)
    return kept


def _find_first(obj, key, depth=0):
    if depth > 7:
        return None
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = _find_first(value, key, depth + 1)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj[:3]:
            found = _find_first(value, key, depth + 1)
            if found is not None:
                return found
    return None


def _trace(report, key):
    trace = report.get("deep_research_trace") or {}
    if key in trace:
        return trace[key]
    plan = ((report.get("retrieval") or {}).get("plan") or {}).get("trace") or {}
    return plan.get(key) or (report.get("retrieval_trace") or {}).get(key) or {}


def _quantiles(values):
    if not values:
        return None
    ordered = sorted(values)
    return {"n": len(ordered), "median": round(statistics.median(ordered), 3),
            "p95": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 3),
            "sum": round(sum(ordered), 3)}


def recorded_target_and_domain(report, agent):
    waves = _trace(report, "discovery_waves") or []
    first = waves[0] if isinstance(waves, list) and waves else {}
    return (first.get("query") or "").strip(), first.get("domain") or DOMAINS[agent]


def _measured_block(report, case_row):
    harvest, metrics = _trace(report, "harvesting"), _trace(report, "acquisition_metrics")
    timings = _trace(report, "stage_timings_ms") or {}
    attempts = _trace(report, "acquisition_attempts") or []
    queries = (report.get("research_corpus") or {}).get("queries") or []
    durations = [a["duration_ms"] / 1000 for a in attempts if isinstance(a.get("duration_ms"), (int, float)) and a["duration_ms"] > 0]
    outcomes = Counter("SUCCESS" if a.get("status") == "SUCCESS" else (a.get("failure_kind") or "FAILED") for a in attempts)
    native = _find_first(report, "native_http_admissions")
    by_phase = _find_first(report, "native_http_by_phase")
    total_ms = sum(v for v in timings.values() if isinstance(v, (int, float)))
    resource = (case_row or {}).get("resource_usage") or {}
    return {
        "queries_generated": harvest.get("queries_generated"),
        "queries_submitted": harvest.get("search_query_reservations"),
        "queries_succeeded": sum(1 for q in queries if q.get("status") == "SUCCESS"),
        "query_latency_seconds": _quantiles([q["latency_ms"] / 1000 for q in queries if isinstance(q.get("latency_ms"), (int, float))]),
        "results_per_query_mean": round(sum(q.get("result_count_normalized") or 0 for q in queries) / len(queries), 2) if queries else None,
        "candidates_discovered": harvest.get("candidate_urls_discovered"),
        "candidates_eligible": harvest.get("candidates_accepted_for_read"),
        "discarded_by_reason": harvest.get("discarded_by_reason") or {},
        "reads_selected": harvest.get("reads_attempted"),
        "eligible_unread": harvest.get("eligible_candidates_unread"),
        "unread_by_reason": harvest.get("unread_by_reason") or {},
        "read_successes": outcomes.get("SUCCESS", 0),
        "read_failures": sum(v for k, v in outcomes.items() if k != "SUCCESS"),
        "read_outcomes": dict(outcomes),
        "read_duration_seconds": _quantiles(durations),
        "run_recorded_workbench_passages": ((report.get("unified_report") or {}).get("evidence_workbench") or {}).get("accounting", {}).get("published_passages", NOT_RECORDED),
        "run_recorded_workbench_unique_words": ((report.get("unified_report") or {}).get("evidence_workbench") or {}).get("accounting", {}).get("published_unique_words", NOT_RECORDED),
        "captures": metrics.get("successful_captures"),
        "article_bodies": metrics.get("article_bodies"),
        "raw_article_words_NOT_EVIDENCE": metrics.get("raw_article_words"),
        "http_admissions": native if native is not None else NOT_RECORDED,
        "http_admissions_by_phase": by_phase if by_phase is not None else NOT_RECORDED,
        "pipeline_seconds": round(total_ms / 1000, 2) if total_ms else NOT_RECORDED,
        "harvest_seconds": round(timings.get("Query planning and raw harvesting", 0) / 1000, 2) if timings else NOT_RECORDED,
        "request_wall_seconds": (case_row or {}).get("seconds", NOT_RECORDED),
        "peak_rss_mb": resource.get("peak_rss_mb", NOT_RECORDED),
        "process_cpu_seconds": resource.get("process_cpu_seconds", NOT_RECORDED),
    }


def _isolate():
    """Network-blocked, credential-blind application imports (mirrors requalify_raw_pool)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from dotenv import dotenv_values
    from scripts.validation.isolated_runtime import block_live_network, isolated_environment
    block_live_network()
    directory = tempfile.mkdtemp(prefix="aegis-baseline-")
    environment = isolated_environment(Path(directory))
    for name in set(environment) | set(dotenv_values(ROOT / ".env")):
        if any(marker in name.upper() for marker in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "COOKIE")):
            environment[name] = ""
    environment.update(AEGIS_MOCK_LLM="false", AEGIS_SEARCH_ADVISOR_ENABLED="false", AEGIS_EVIDENCE_ADVISOR_ENABLED="false",
                       AEGIS_AI_POLICY_DB=str(Path(directory) / "ai-disabled.db"))
    os.environ.update(environment)


def _derived_block(report, agent, target, domain, predicate):
    from scripts.audits.requalify_raw_pool import requalify_payload, locate_pool
    pool = locate_pool(report)
    reference = datetime.fromisoformat(pool["created_at"])
    module = importlib.import_module("backend.services.research.passage_extractor")
    original = module.has_finite_predicate
    if predicate == "legacy":
        module.has_finite_predicate = lambda text: bool(LEGACY_VERBS.search(text))
    rescue = False
    try:
        try:
            result = requalify_payload(report, target=target, domain=domain, reference_time=reference)
        except ValueError as error:
            if "Conflicting source alias" not in str(error):
                raise
            rescue = True       # the repo's documented explicit offline rescue
            result = requalify_payload(report, target=target, domain=domain, reference_time=reference, disambiguate_aliases=True)
    finally:
        module.has_finite_predicate = original
    decisions = result["requalification"]["decisions"]
    qualified = [d for d in decisions if d["qualification_status"] == "QUALIFIED"]
    passages = [{"url": d["source_url"], "words": d["passage"]["word_count"], "start": d["passage"]["start"],
                 "end": d["passage"]["end"], "normalized": _normalize(d["passage"]["text"]),
                 "text_sha256": hashlib.sha256(d["passage"]["text"].encode("utf-8")).hexdigest(),
                 "text": d["passage"]["text"]} for d in qualified]
    unique = deduplicate_passages(passages)
    multi = deduplicate_passages([{**{"url": d["source_url"], "words": q["word_count"], "text": q["text"]},
                                   "normalized": _normalize(q["text"])}
                                  for d in qualified for q in (d.get("workbench_passages") or [])])
    groups = Counter(publisher_group(re.sub(r"^https?://([^/]+).*$", r"\1", p["url"])) for p in unique)
    causes = Counter()
    for d in decisions:
        if d["qualification_status"] == "QUALIFIED":
            continue
        kind = "NOT_ACQUIRED_AS_BODY" if d["source_type"] not in {"ARTICLE_BODY", "OFFICIAL_DOCUMENT", "COMMUNITY_POST", "STRUCTURED_PUBLIC_DATA"} else \
            re.sub(r"[:(\[].*$", "", (d["reasons"] or ["UNSPECIFIED"])[0]).strip() or "UNSPECIFIED"
        causes[kind] += 1
    return {
        "requalified_with": "legacy verb condition" if predicate == "legacy" else "current clause predicate",
        "alias_rescue_used": rescue,
        "reference_time": pool["created_at"],
        "qualified_source_records": len(qualified),
        "qualified_passages": len(passages),
        "relevant_passage_words_before_dedup": sum(p["words"] for p in passages),
        "relevant_passage_words_unique": sum(p["words"] for p in unique),
        "duplicate_or_contained_passages_removed": len(passages) - len(unique),
        "all_passages_count_unique": len(multi),
        "all_passages_words_unique": sum(q["words"] for q in multi),
        "all_passages_scope": "Every bounded paragraph passing the same gates, one winner per source plus others; exact-text deduplicated",
        "distinct_publisher_groups": len(groups),
        "publisher_groups": dict(groups),
        "publisher_group_scope": "Observed registrable-domain groups; ownership and independence are NOT established",
        "rejection_causes": dict(causes),
        "passages": [{k: v for k, v in p.items() if k != "normalized"} for p in unique],
    }


def measure_report(report, *, agent, label, case_row=None, predicate="current", source_file=None):
    target, domain = recorded_target_and_domain(report, agent)
    row = {"id": label, "agent": agent, "input": (case_row or {}).get("input"), "research_target": target, "domain": domain,
           "source_file": str(source_file) if source_file else None,
           "source_file_sha256": sha256_file(Path(source_file)) if source_file else None,
           "MEASURED": _measured_block(report, case_row)}
    row["DERIVED"] = _derived_block(report, agent, target, domain, predicate)
    admissions = row["MEASURED"]["http_admissions"]
    unique = row["DERIVED"]["relevant_passage_words_unique"]
    row["DERIVED"]["evidence_words_per_100_admissions"] = (round(100 * unique / admissions, 1)
                                                            if isinstance(admissions, (int, float)) and admissions else NOT_RECORDED)
    row["DERIVED"]["qualified_sources_per_100_admissions"] = (round(100 * row["DERIVED"]["qualified_source_records"] / admissions, 2)
                                                              if isinstance(admissions, (int, float)) and admissions else NOT_RECORDED)
    return row


def apply_reviews(rows, reviews):
    """Manual labels live in their own file and never alter the derived numbers."""
    for row in rows:
        counts, words = Counter(), Counter()
        for passage in row["DERIVED"]["passages"]:
            label = (reviews.get(passage["text_sha256"]) or {}).get("label")
            if label:
                counts[label] += 1
                words[label] += passage["words"]
        row["REVIEWED"] = {"labelled_passages": sum(counts.values()), "of_passages": len(row["DERIVED"]["passages"]),
                           "by_label": dict(counts), "words_by_label": dict(words),
                           "reviewer_note": "Labels come from the supplied review file; they are judgments, not measurements"}


def load_batch(label, directory):
    directory = Path(directory)
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    for case in summary["cases"]:
        path = directory / (case["case_id"] + ".json")
        if path.is_file():
            yield label, case, path


def render_markdown(rows):
    header = ("| Investigation | Disc | Elig | Read | Unread | Read ok/fail | Qualified | Relevant words (unique) | Publisher groups | "
              "HTTP adm | Words/100 adm | Pipeline s |\n| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |\n")
    lines = []
    for r in rows:
        m, d = r["MEASURED"], r["DERIVED"]
        lines.append(f"| {r['id']} ({r['input']}) | {m['candidates_discovered']} | {m['candidates_eligible']} | {m['reads_selected']} | "
                     f"{m['eligible_unread']} | {m['read_successes']}/{m['read_failures']} | {d['qualified_source_records']} | "
                     f"{d['relevant_passage_words_unique']} | {d['distinct_publisher_groups']} | {m['http_admissions']} | "
                     f"{d['evidence_words_per_100_admissions']} | {m['pipeline_seconds']} |")
    legend = ("\n\nProvenance: counts in Disc..Read ok/fail, HTTP adm and Pipeline s are MEASURED from the original run; "
              "Qualified, Relevant words, Publisher groups and Words/100 adm are DERIVED by one deterministic offline code path "
              "(same definitions for every run). Publisher groups are observed host groups, not independent sources.\n")
    return header + "\n".join(lines) + legend


def _safe_output(path: Path) -> Path:
    resolved = path.resolve()
    protected = [ROOT / "backend" / "data" / "dossiers", ROOT / "artifacts", ROOT / "research", ROOT / "tests" / "retrieval_benchmark"]
    if any(resolved == p or p in resolved.parents for p in protected):
        raise ValueError("Output must not target protected historical or benchmark trees")
    if resolved.exists():
        raise FileExistsError("Output exists; choose a fresh filename")
    return resolved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", action="append", required=True, metavar="LABEL=DIR",
                        help="Directory with summary.json and NN-agent.json native reports; repeatable")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--predicate", choices=("current", "legacy"), default="current")
    parser.add_argument("--reviews", type=Path, help="Optional {text_sha256: {label, note}} manual review file")
    args = parser.parse_args(argv)
    output = _safe_output(args.output)
    markdown = _safe_output(args.markdown) if args.markdown else None
    _isolate()
    rows, before = [], {}
    for spec in args.batch:
        label, _, directory = spec.partition("=")
        for batch, case, path in load_batch(label, directory):
            before[str(path)] = sha256_file(path)
            report = json.loads(path.read_text(encoding="utf-8"))
            agent = case["agent"]
            rows.append(measure_report(report, agent=agent, label=f"{batch}/{agent}", case_row=case, predicate=args.predicate, source_file=path))
    if args.reviews:
        apply_reviews(rows, json.loads(args.reviews.read_text(encoding="utf-8")))
    unchanged = all(sha256_file(Path(p)) == digest for p, digest in before.items())
    payload = {"mode": "OFFLINE_EVIDENCE_YIELD_BASELINE", "network_calls": 0, "model_calls": 0,
               "inputs_unchanged": unchanged, "predicate": args.predicate, "investigations": rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    if markdown:
        markdown.write_text(render_markdown(rows), encoding="utf-8")
    print(json.dumps({"investigations": len(rows), "inputs_unchanged": unchanged, "output": str(output)}))
    return 0 if unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
