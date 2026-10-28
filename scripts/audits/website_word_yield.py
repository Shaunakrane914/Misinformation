"""Offline website accounting from complete native captures, never snippets.

Word means whitespace-delimited word occurrences, not vocabulary size. Full
qualified-body volume is separate from exact selected/offset-validated passages.
Unknown observations remain null. This module performs no provider/model calls.
"""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


def host(url):
    return (urlsplit(url or "").hostname or "").lower()


def word_count(text):
    return len((text or "").split())


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def passage_accounting(passages, sources, scope="CURRENT_OR_TASK_EVIDENCE"):
    """Exact body/hash/offset identity, with cross-source text deduplication."""
    by_id = {}
    for source in sources:
        for identity in [source["source_id"], *source.get("aliases", [])]:
            by_id[identity] = source
    seen_text, covered, counts, checks = set(), defaultdict(set), Counter(), []
    for passage in passages:
        identity = passage.get("evidence_id") or passage.get("source_id")
        source = by_id.get(identity)
        text, start, end = passage.get("text", ""), passage.get("start"), passage.get("end")
        body = source.get("readable_text", "") if source else ""
        digest = sha(body) if body else None
        valid = bool(source and source.get("source_type") in {"ARTICLE_BODY", "OFFICIAL_DOCUMENT", "STRUCTURED_PUBLIC_DATA", "COMMUNITY_POST"}
                     and text and type(start) is int and type(end) is int
                     and 0 <= start < end <= len(body) and body[start:end] == text
                     and passage.get("captured_text_sha256") == digest
                     and source.get("raw_content_hash") == digest)
        check = {"passage_id": passage.get("passage_id"), "source_id": identity,
                 "valid_body_hash_and_offsets": valid, "words": word_count(text), "unique_words": 0,
                 "publication_scope": scope}
        if valid:
            normalized = " ".join(text.split())
            tokens = {i for i, token in enumerate(re.finditer(r"\S+", body))
                      if token.start() >= start and token.end() <= end}
            check.update(body_sha256=digest, text_sha256=sha(normalized),
                         body_word_start=min(tokens) if tokens else 0,
                         body_word_end=max(tokens) + 1 if tokens else 0)
            if normalized not in seen_text:
                unique = tokens - covered[digest]
                check["unique_words"] = len(unique)
                counts[source["source_id"]] += len(unique)
                covered[digest].update(tokens)
                seen_text.add(normalized)
        checks.append(check)
    return counts, checks


def measure_case(native, *, prompt_id, agent, observer=None, seconds=None, mode="LIVE"):
    corpus, trace = native.get("research_corpus", {}), native.get("retrieval_trace", {})
    pool = corpus.get("raw_acquisition_pool") or {}
    sources = pool.get("sources", [])
    report = native.get("unified_report") or {}
    native_records = {}
    for key in ("raw_candidates", "ranked_candidates", "deep_read_sources"):
        for record in corpus.get(key, []):
            native_records[record.get("id") or record.get("evidence_id")] = record
    workbench = report.get("evidence_workbench") or {}
    published, checks = passage_accounting(workbench.get("passages", []), sources)
    selected_passages = []
    for record in corpus.get("deep_read_sources", []):
        selected_passages.extend((record.get("metadata") or {}).get("evidence_passages", []))
    selected, selected_checks = passage_accounting(selected_passages, sources)
    background = (report.get("agent_intelligence") or {}).get("historical_background") or {}
    background_passages = background.get("passages", [])
    # Background schema stores source groups, each with exact captured passages.
    if not background_passages:
        for group in background.get("sources", []):
            if group.get("passages"):
                background_passages.extend(group["passages"])
                continue
            source = next((s for s in sources if group.get("evidence_id") in
                           [s["source_id"], *s.get("aliases", [])]), None)
            body = source.get("readable_text", "") if source else ""
            for text in group.get("passage", "").split("\n\n"):
                if not text:
                    continue
                start = body.find(text)
                background_passages.append({"evidence_id": group.get("evidence_id"), "text": text,
                    "start": start, "end": start + len(text),
                    "captured_text_sha256": group.get("source_body_sha256"),
                    "offset_basis": "OFFLINE_EXACT_SUBSTRING_OF_CAPTURE_NOT_ORIGINAL_OFFSET_EVENT"})
    older, older_checks = passage_accounting(background_passages, sources, "OLDER_BACKGROUND")
    reference_words, reference_checks = {}, []
    reference = (report.get('agent_intelligence') or {}).get('reference_background') or {}
    for group in reference.get('sources', []):
        source = next((row for row in sources if row['source_id'] == group.get('evidence_id')), None)
        body = source.get('readable_text', '') if source else ''
        text, start, end = group.get('passage', ''), group.get('start'), group.get('end')
        valid = bool(source and source.get('source_type') == 'BACKGROUND_REFERENCE'
            and type(start) is int and type(end) is int and 0 <= start < end <= len(body)
            and body[start:end] == text and sha(body) == group.get('source_body_sha256'))
        reference_checks.append({'source_id': group.get('evidence_id'), 'valid': valid,
                                 'scope': 'GENERAL_BACKGROUND_ONLY'})
        if valid:
            reference_words[group['evidence_id']] = word_count(text)
    queries = {q.get("query_id"): q for q in corpus.get("queries", [])}
    attempts = trace.get("acquisition_attempts", [])
    by_source, by_url = defaultdict(list), defaultdict(list)
    for attempt in attempts:
        by_source[attempt.get("candidate_id")].append(attempt)
        by_url[attempt.get("url")].append(attempt)
    admissions = (observer or {}).get("admissions", [])
    http_operations = (observer or {}).get("http_operations", [])
    assigned_http, rows, seen_bodies = set(), [], set()
    for source in sources:
        identity, body = source["source_id"], source.get("readable_text", "")
        native_record = native_records.get(identity) or {}
        metadata = native_record.get("metadata") or {}
        transport = source.get("transport") or {}
        urls = {source.get("source_url"), source.get("canonical_url"), *source.get("source_urls", []),
                source.get("actual_final_url"), transport.get("requested_endpoint"), transport.get("endpoint")}
        urls.discard(None)
        aliases = {identity, *source.get("aliases", [])}
        reads = {a.get("attempt_id"): a for i in aliases for a in by_source[i]}
        reads.update({a.get("attempt_id"): a for u in urls for a in by_url[u]})
        related_http = [i for i, operation in enumerate(http_operations)
                        if operation["requested_url"] in urls or operation.get("final_url") in urls]
        # Every HTTP operation is assigned once, including its actual redirects.
        related_http = [i for i in related_http if i not in assigned_http]
        assigned_http.update(related_http)
        operation_ids = {http_operations[i]["operation_id"] for i in related_http}
        matching_admissions = [a for a in admissions if a.get("http_operation_id") in operation_ids]
        article = source.get("source_type") == "ARTICLE_BODY" and bool(body)
        digest = sha(body) if body else None
        unique_body = article and digest not in seen_bodies
        if article:
            seen_bodies.add(digest)
        qrows = [queries[q] for q in source.get("query_ids", []) if q in queries]
        providers = sorted({a.get("provider", "UNKNOWN") for q in qrows for a in q.get("search_attempts", [])})
        reasons = list(source.get("qualification_reasons", [])) + [e.get("type", "UNKNOWN") for e in source.get("errors", [])]
        permission = (metadata.get("source_use_permission") or metadata.get("source_body_admission")
                      or source.get("source_permission") or source.get("source_body_admission") or {})
        row = {"agent": agent, "prompt_id": prompt_id, "mode": mode, "row_type": "SOURCE",
               "source_id": identity, "source_family": source.get("source_family") or metadata.get("source_family") or permission.get("source_family"),
               "website": host(source.get("canonical_url")), "original_discovered_url": metadata.get("discovery_url") or (source.get("source_urls", [None])[0] if source.get("source_urls") else source.get("source_url")),
               "canonical_article_url": source.get("canonical_url"), "final_acquired_url": source.get("actual_final_url"),
               "title": source.get("title"), "observed_publisher": source.get("publisher") or None,
               "discovery_providers": providers, "reader_backend": sorted({a.get("backend") for a in reads.values() if a.get("backend")}),
               "published_at": source.get("published_at"), "acquired_at": source.get("acquired_at"),
               "permission_status": permission or ("REJECTED_BY_PERMISSION" if any("PERMISSION" in r or "RIGHTS" in r for r in reasons) else "NOT_RETAINED_IN_CAPTURE"),
               "http_status": source.get("http_status"), "extraction_outcome": source.get("extraction_status"),
               "source_type": source.get("source_type"), "content_depth": source.get("content_depth"),
               "acquisition_method": source.get("acquisition_method"),
               "provider_truncated": source.get("provider_truncated"), "adapter_truncated": metadata.get("truncated"),
               "reads_attempted": len(reads), "read_duration_ms": round(sum(a.get("duration_ms", 0) for a in reads.values()), 3),
               "native_http_admissions": sum(a["admitted"] for a in matching_admissions) if observer is not None else None,
               "native_http_admission_hosts": dict(Counter(a["host"] for a in matching_admissions if a["admitted"])),
               "http_attribution_scope": "EXACT_RETAINED_LOCATOR_ONLY_LOOKUPS_REMAIN_TRANSPORT_ROWS",
               "http_operation_observations": [http_operations[i] for i in related_http],
               "bodies_acquired": int(article), "raw_article_words": word_count(body) if article else 0,
               "official_document_words": word_count(body) if source.get("source_type") == "OFFICIAL_DOCUMENT" else 0,
               "deduplicated_article_words": word_count(body) if unique_body else 0,
               "structurally_qualified_body_words": word_count(body) if unique_body else 0,
               "qualified_body_words": word_count(body) if unique_body and source.get("qualification_status") == "QUALIFIED" else 0,
               "topic_temporal_attribution_words": selected[identity] if selected_passages else None,
               "selected_unique_passage_words": selected[identity] if selected_passages else None,
               "published_unique_evidence_words": published[identity],
               "historical_background_words": older[identity],
               "reference_background_words": reference_words.get(identity, 0),
               "reference_citation_validity": [c for c in reference_checks if c['source_id'] == identity],
               "community_body_words": word_count(body) if source.get('source_type') == 'COMMUNITY_POST' else 0,
               "structured_data_words": word_count(body) if source.get('source_type') == 'STRUCTURED_PUBLIC_DATA' else 0,
               "video_transcript_words": word_count(body) if 'TRANSCRIPT' in str(source.get('content_depth', '')).upper() else 0,
               "reference_body_words": word_count(body) if source.get('source_type') == 'BACKGROUND_REFERENCE' else 0,
               "platform_channel": native_record.get('channel') or source.get('channel'),
               "qualification_status": source.get("qualification_status"), "reasons": sorted(set(reasons)),
               "body_sha256": digest, "stored_body_hash_valid": digest == source.get("raw_content_hash") if body else None,
               "passage_offset_validity": [c for c in checks + older_checks if c["source_id"] in aliases]}
        rows.append(row)
    retained_urls = {u for source in sources for u in
                     [source.get("source_url"), source.get("canonical_url"), *source.get("source_urls", [])] if u}
    discarded_leads = {}
    for query in queries.values():
        for response in query.get("search_attempts", []):
            for decision in response.get("decisions", []):
                url = decision.get("url")
                if not url or url in retained_urls or not decision.get("discard_reason"):
                    continue
                lead = discarded_leads.setdefault(url, {"agent": agent, "prompt_id": prompt_id, "mode": mode,
                    "row_type": "REJECTED_SEARCH_LEAD", "website": host(url), "original_discovered_url": url,
                    "title": decision.get("title"), "discovery_providers": [], "reasons": [],
                    "extraction_outcome": "DISCOVERY_ONLY_NO_RETAINED_BODY", "native_http_admissions": 0})
                if response.get("provider") not in lead["discovery_providers"]:
                    lead["discovery_providers"].append(response.get("provider"))
                if decision["discard_reason"] not in lead["reasons"]:
                    lead["reasons"].append(decision["discard_reason"])
    rows.extend(discarded_leads.values())
    for index, operation in enumerate(http_operations):
        if index in assigned_http:
            continue
        rows.append({"agent": agent, "prompt_id": prompt_id, "mode": mode, "row_type": "TRANSPORT",
                     "website": host(operation.get("final_url") or operation["requested_url"]),
                     "original_discovered_url": operation["requested_url"], "final_acquired_url": operation.get("final_url"),
                     "http_status": operation.get("http_status"), "extraction_outcome": "NOT_AN_ARTICLE_CAPTURE",
                     "native_http_admissions": sum(a["admitted"] for a in admissions if a.get("http_operation_id") == operation["operation_id"]),
                     "reasons": [operation["failure_kind"]] if operation.get("failure_kind") else [],
                     "transport_duration_ms": operation["duration_ms"], "http_operation_id": operation["operation_id"]})
    assigned_operations = {op["operation_id"] for op in http_operations}
    for admission in admissions:
        if admission.get("http_operation_id") not in assigned_operations:
            rows.append({"agent": agent, "prompt_id": prompt_id, "mode": mode, "row_type": "ADMISSION_ONLY",
                         "website": admission["host"], "original_discovered_url": admission["url"],
                         "native_http_admissions": int(admission["admitted"]), "reasons": ["NO_SHARED_HTTP_OPERATION_OBSERVED"]})
    harvest = trace.get("harvesting") or {}
    summary = {"prompt_id": prompt_id, "agent": agent, "mode": mode, "seconds": seconds,
               "source_records": len(sources), "article_bodies": sum(r.get("bodies_acquired", 0) for r in rows),
               "raw_article_words": sum(r.get("raw_article_words", 0) for r in rows),
               "deduplicated_article_words": sum(r.get("deduplicated_article_words", 0) for r in rows),
               "qualified_sources": sum(s.get("qualification_status") == "QUALIFIED" for s in sources),
               "qualified_publishers": sorted({r["website"] for r in rows if r.get("published_unique_evidence_words", 0)}),
               "qualified_unique_passage_words": sum(published.values()), "published_unique_evidence_words": sum(published.values()),
               "selected_pre_workbench_passage_words": sum(selected.values()) if selected_passages else None,
               "invalid_pre_workbench_passages": sum(not c["valid_body_hash_and_offsets"] for c in selected_checks),
               "historical_background_words": sum(older.values()), "valid_citations": sum(c["valid_body_hash_and_offsets"] for c in checks),
               "invalid_citations": sum(not c["valid_body_hash_and_offsets"] for c in checks),
               "background_invalid_citations": sum(not c["valid_body_hash_and_offsets"] for c in older_checks),
               "reads_attempted": trace.get("deep_read_attempted"),
               "native_http_admissions": harvest.get("native_http_admissions"),
               "observed_native_http_admissions": (observer or {}).get("native_http_admissions"),
               "ledger_native_http_admissions": sum(r.get("native_http_admissions") or 0 for r in rows) if observer is not None else None,
               "effective_profile": trace.get("research_profile"), "effective_http_cap": harvest.get("native_http_cap"),
               "effective_trending_window_hours": trace.get("trending_window_hours", 48 if agent == "trending" else None),
               "status": native.get("investigation_status") or report.get("investigation_status"),
               "workbench_accounting": workbench.get("accounting", {}),
               "failures": dict(Counter(reason for r in rows for reason in r.get("reasons", [])))}
    if not corpus.get("raw_acquisition_pool"):
        # An exception can discard output after real reads. It is not zero reads
        # or zero acquired bodies; HTTP success alone cannot reconstruct them.
        for key in ("article_bodies", "raw_article_words", "deduplicated_article_words", "qualified_sources",
                    "qualified_unique_passage_words", "reads_attempted"):
            summary[key] = None
        summary["capture_accounting_status"] = "NATIVE_POOL_UNAVAILABLE"
    else:
        summary["capture_accounting_status"] = "COMPLETE_NATIVE_POOL"
    return rows, summary


def write_ledger(rows, path):
    path = Path(path)
    path.with_suffix(".json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = sorted(set().union(*(r.keys() for r in rows)))
    with path.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fields)
        writer.writeheader()
        writer.writerows({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                         for key, value in row.items()} for row in rows)


def aggregate_websites(rows, per_case=True):
    groups = {}
    for row in rows:
        key = (row["agent"], row["prompt_id"] if per_case else "ALL_AUTHORIZED_CASES", row.get("website") or "UNKNOWN")
        result = groups.setdefault(key, {"agent": key[0], "prompt_id": key[1], "website": key[2],
            "source_records": 0, "reads_attempted": 0, "bodies_acquired": 0, "raw_article_words": 0,
            "deduplicated_article_words": 0, "qualified_body_words": 0, "published_unique_evidence_words": 0,
            "historical_background_words": 0, "native_http_admissions": 0, "discovery_only_records": 0,
            "rejected_search_leads": 0,
            "permission_rejected_records": 0, "observed_reasons": Counter(), "publication_accounting_unknown": False})
        for field in ("reads_attempted", "bodies_acquired", "raw_article_words", "deduplicated_article_words",
                      "qualified_body_words", "published_unique_evidence_words", "historical_background_words", "native_http_admissions"):
            result[field] += row.get(field) or 0
        if row["row_type"] == "SOURCE":
            result["source_records"] += 1
            result["discovery_only_records"] += row.get("source_type") in {"SOURCE_INDEX", "PUBLISHER_HOMEPAGE", "FEED_ENTRY", "DISCOVERY_LEAD", "BACKGROUND_REFERENCE"}
            permission = row.get("permission_status")
            result["permission_rejected_records"] += isinstance(permission, dict) and permission.get("eligible") is False
            if row.get("published_unique_evidence_words") is None:
                result["publication_accounting_unknown"] = True
            if row.get("reads_attempted") is None:
                result["read_attempt_accounting_unknown"] = True
        if row["row_type"] == "REJECTED_SEARCH_LEAD":
            result["rejected_search_leads"] += 1
        result["observed_reasons"].update(row.get("reasons", []))
    result = list(groups.values())
    for group in result:
        group["observed_reasons"] = dict(group["observed_reasons"])
        if group["publication_accounting_unknown"]:
            group["published_unique_evidence_words"] = None
            group["historical_background_words"] = None
        if group.get("read_attempt_accounting_unknown"):
            group["reads_attempted"] = None
        group["published_words_per_native_admission"] = (
            round(group["published_unique_evidence_words"] / group["native_http_admissions"], 3)
            if group["native_http_admissions"] and group["published_unique_evidence_words"] is not None else None)
        group["diagnostic_role"] = "ACQUIRED_ARTICLE_HOST" if group["bodies_acquired"] else "DISCOVERY_TRANSPORT_OR_FAILED_SOURCE"
        if not per_case:
            group["cross_case_unique"] = cross_case_unique([r for r in rows
                if r["agent"] == group["agent"] and (r.get("website") or "UNKNOWN") == group["website"]])
            group["case_sum_published_passage_words"] = group["published_unique_evidence_words"]
            if not group["publication_accounting_unknown"]:
                group["published_unique_evidence_words"] = group["cross_case_unique"]["known_unique_published_passage_words"]
                group["historical_background_words"] = group["cross_case_unique"]["known_unique_historical_passage_words"]
            group["deduplicated_article_words"] = group["cross_case_unique"]["known_unique_raw_article_words"]
            if not group["publication_accounting_unknown"] and group["native_http_admissions"]:
                group["published_words_per_native_admission"] = round(
                    group["cross_case_unique"]["known_unique_published_passage_words"] / group["native_http_admissions"], 3)
    return result


def cross_case_unique(rows):
    """Do not sum repeated bodies/passages from different prompts as new words."""
    bodies, passages, covered, older, all_covered = {}, set(), defaultdict(set), defaultdict(set), defaultdict(set)
    for row in rows:
        if row.get("bodies_acquired") and row.get("body_sha256"):
            bodies.setdefault(row["body_sha256"], row["raw_article_words"])
        for passage in row.get("passage_offset_validity", []):
            key = (passage.get("publication_scope"), passage.get("text_sha256"))
            if not passage.get("valid_body_hash_and_offsets") or key in passages:
                continue
            passages.add(key)
            destination = older if passage.get("publication_scope") == "OLDER_BACKGROUND" else covered
            tokens = range(passage["body_word_start"], passage["body_word_end"])
            destination[passage["body_sha256"]].update(tokens)
            all_covered[passage["body_sha256"]].update(tokens)
    return {"known_unique_article_bodies": len(bodies), "known_unique_raw_article_words": sum(bodies.values()),
            "known_unique_published_passage_words": sum(len(tokens) for tokens in covered.values()),
            "known_unique_historical_passage_words": sum(len(tokens) for tokens in older.values()),
            "known_unique_evidence_and_background_words": sum(len(tokens) for tokens in all_covered.values()),
            "scope": "EXACT_BODY_AND_NORMALIZED_PASSAGE_HASHES_AND_SAME_BODY_TOKEN_SPAN_UNION; UNKNOWN_CASES_EXCLUDED"}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True, help="List of id, agent, native_path, optional http_path/seconds")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    rows, summaries = [], []
    for case in json.loads(args.index.read_text(encoding="utf-8")):
        if case.get("raw_pool_path"):
            pools = json.loads(Path(case["raw_pool_path"]).read_text(encoding="utf-8"))
            native = {"research_corpus": {"raw_acquisition_pool": pools[-1]}}
        else:
            native = json.loads(Path(case["native_path"]).read_text(encoding="utf-8"))
        observer = json.loads(Path(case["http_path"]).read_text(encoding="utf-8")) if case.get("http_path") else None
        records, summary = measure_case(native, prompt_id=case["id"], agent=case["agent"], observer=observer,
                                        seconds=case.get("seconds"), mode=case.get("mode", "LIVE"))
        summary.update(input=case.get("input"), requested_prompt=case.get("query"),
                       application_sha256=case.get("application_sha256"),
                       native_file_sha256=hashlib.sha256(Path(case.get("native_path") or case["raw_pool_path"]).read_bytes()).hexdigest())
        if case.get("raw_pool_path"):
            summary.update(capture_accounting_status="RAW_POOL_RECOVERED_ORIGINAL_NATIVE_PROJECTION_UNAVAILABLE",
                           reads_attempted=case.get("dossier_verified_read_attempts"),
                           qualified_unique_passage_words=None, published_unique_evidence_words=None,
                           historical_background_words=None, valid_citations=None, invalid_citations=None)
            for row in records:
                if row["row_type"] == "SOURCE":
                    for key in ("topic_temporal_attribution_words", "selected_unique_passage_words",
                                "published_unique_evidence_words", "historical_background_words"):
                        row[key] = None
                    row["reads_attempted"] = None
                    row["read_duration_ms"] = None
                    row["reader_backend"] = None
                    row["read_attempt_observation_basis"] = "ORIGINAL_PER_URL_READ_TRACE_NOT_SAVED"
        if case.get("projection_native_path"):
            projection = json.loads(Path(case["projection_native_path"]).read_text(encoding="utf-8"))
            projected_rows, projected_summary = measure_case(projection, prompt_id=case["id"], agent=case["agent"], mode="OFFLINE_REPLAY")
            original_signatures = {s["source_id"]: (s.get("raw_content_hash"), s.get("canonical_url"))
                                   for s in native["research_corpus"]["raw_acquisition_pool"]["sources"]}
            projected_signatures = {s["source_id"]: (s.get("raw_content_hash"), s.get("canonical_url"))
                                    for s in projection["research_corpus"]["raw_acquisition_pool"]["sources"]}
            if original_signatures != projected_signatures:
                raise ValueError("Projection changed the original source identities or captured body hashes")
            projected_by_id = {r["source_id"]: r for r in projected_rows if r["row_type"] == "SOURCE"}
            for row in records:
                if row["row_type"] == "SOURCE":
                    updated = projected_by_id.get(row["source_id"], {})
                    row["offline_projection_published_words"] = updated.get("published_unique_evidence_words")
                    row["offline_projection_qualification_status"] = updated.get("qualification_status")
            summary["offline_projection"] = {"scope": "EXACT_SAVED_CAPTURE_REPROCESSING_NOT_NEW_ACQUISITION",
                "source_id_url_body_hash_preserved": True,
                **{k: projected_summary[k] for k in ("qualified_sources", "published_unique_evidence_words",
                    "historical_background_words", "invalid_citations", "background_invalid_citations")}}
        rows.extend(records)
        summaries.append(summary)
    write_ledger(rows, args.output_dir / "website_word_yield")
    websites = aggregate_websites(rows)
    write_ledger(websites, args.output_dir / "website_totals")
    agents = {}
    for case in summaries:
        result = agents.setdefault(case["agent"], {"cases": 0, "known_article_bodies": 0,
            "known_raw_article_words": 0, "known_published_unique_evidence_words": 0,
            "known_historical_background_words": 0, "cases_with_unknown_acquisition": [], "cases_with_unknown_publication": []})
        result["cases"] += 1
        for source, target in (("article_bodies", "known_article_bodies"), ("raw_article_words", "known_raw_article_words"),
                               ("published_unique_evidence_words", "known_published_unique_evidence_words"),
                               ("historical_background_words", "known_historical_background_words")):
            result[target] += case[source] or 0
        if case["article_bodies"] is None:
            result["cases_with_unknown_acquisition"].append(case["prompt_id"])
        if case["published_unique_evidence_words"] is None:
            result["cases_with_unknown_publication"].append(case["prompt_id"])
    rankings = {}
    agent_websites = aggregate_websites(rows, per_case=False)
    write_ledger(agent_websites, args.output_dir / "agent_website_totals")
    for agent in agents:
        selected = [w for w in agent_websites if w["agent"] == agent]
        agents[agent]["case_sums_are_not_cross_case_unique"] = True
        agents[agent]["cross_case_unique"] = cross_case_unique([r for r in rows if r["agent"] == agent])
        rankings[agent] = {
            "highest_raw_article_yield": sorted(selected, key=lambda w: -w["raw_article_words"])[:8],
            "highest_published_passage_yield": sorted(selected, key=lambda w: -(w["published_unique_evidence_words"] or 0))[:8],
            "highest_words_per_admission": sorted([w for w in selected if w["published_words_per_native_admission"] is not None],
                key=lambda w: -w["published_words_per_native_admission"])[:8],
            "bodies_without_published_passages": [w for w in selected if w["bodies_acquired"] and w["published_unique_evidence_words"] == 0],
            "discovery_only_or_failed": [w for w in selected if not w["bodies_acquired"]],
            "permission_rejections": [w for w in selected if w["permission_rejected_records"]],
        }
    (args.output_dir / "website_rankings.json").write_text(json.dumps(rankings, indent=2), encoding="utf-8")
    (args.output_dir / "agent_word_yield_summary.json").write_text(json.dumps({
        "word_definition": "Whitespace-delimited occurrences; exact body/text/span deduplication, not distinct vocabulary",
        "qualification_scope": "Automated source/passage heuristics, not independent factual accuracy or exact-task acceptance",
        "cases": summaries, "agents": agents, "cross_agent_unique": cross_case_unique(rows)}, indent=2), encoding="utf-8")
    return int(any(s["invalid_citations"] or s["background_invalid_citations"] for s in summaries))


if __name__ == "__main__":
    raise SystemExit(main())
