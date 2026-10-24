"""Deterministic specialist coverage brief, not AI synthesis or threat adjudication."""
from backend.schemas.evidence_inspection import METADATA_DEPTHS
from backend.services.research.content_roles import NON_EVENT_ROLES, document_role, matches_objective
from backend.services.research.passage_extractor import has_usable_passage


def specialist_brief(data, agent, target, discovery):
    domain = "brand" if agent == "brandshield" else "personal"
    if domain == "personal":
        # The report query may be a source URL or allegation, not the subject
        # whose name appears in captured speaker attribution.
        subject = data.get("subject")
        subject = subject if isinstance(subject, dict) else {}
        target = subject.get("canonical_name") or subject.get("name") or data.get("vip_name") or target
    records, seen = [], set()
    for field in ("evidence", "sources", "documents", "officials", "news", "social", "impostor_accounts"):
        values = data.get(field)
        for record in values if isinstance(values, list) else []:
            if not isinstance(record, dict):
                continue
            identity = record.get("evidence_id") or record.get("id") or record.get("canonical_url") or record.get("url")
            if not identity or identity in seen:
                continue
            seen.add(identity)
            records.append(record)
    relevant = []
    profiles = 0
    public_statements = 0
    for record in records:
        meta = record.get("metadata") or record.get("raw_metadata") or {}
        meta = meta if isinstance(meta, dict) else {}
        depth = record.get("content_depth") or meta.get("content_depth") or "UNKNOWN"
        scoped_record = {**record, "metadata": meta, "content_depth": depth}
        role = document_role(scoped_record)
        profiles += role == "PROFILE"
        if depth in METADATA_DEPTHS or role in NON_EVENT_ROLES:
            continue
        from backend.services.research.passage_records import captured_passages
        # A captured article can coexist with navigation/related cards in the
        # raw buffer. Count only validated exact article passages, never the
        # whole navigation-heavy capture or an outside related-story snippet.
        passages = [p for p in captured_passages(scoped_record, domain, target)
                    if has_usable_passage({**scoped_record, "content": p["text"],
                                           "relevant_excerpt": "", "snippet": ""})]
        statement = domain == "personal" and any(
            p["content_role"] == "PUBLIC_STATEMENT" and p["attribution"] != "SOURCE_ASSERTION"
            for p in passages)
        public_statements += statement
        if statement or any(p["relevance"] == "DIRECTLY_RELEVANT" and matches_objective(p["text"], domain)
                            for p in passages):
            relevant.append(record)
    corpus = data.get("research_corpus") or {}
    corpus = corpus if isinstance(corpus, dict) else {}
    trace = data.get("retrieval_trace") or {}
    trace = trace if isinstance(trace, dict) else {}
    attempts = trace.get("acquisition_attempts", [])
    attempts = attempts if isinstance(attempts, list) else []
    failed = sum(isinstance(a, dict) and a.get("status") in {"FAILED", "TIMEOUT", "EMPTY_CONTENT"} for a in attempts)
    state = "REQUIRES_PASSAGE_REVIEW" if relevant else "INSUFFICIENT_EVIDENCE"
    objective = "brand abuse, product-safety concerns or consumer complaints" if domain == "brand" else "identity-abuse or synthetic-media exposure"
    record_description = (f"{len(records)} retained source record(s)" if domain == "brand" else
                          f"{len(records)} retained source record(s), including {profiles} profile(s)")
    summary = (f"{target}: {record_description}; "
               f"{len(relevant)} capture(s) contain task-related text and {discovery} lead(s) are discovery-only. ")
    summary += ("Captured text needs passage/context review; it does not confirm a threat. " if relevant else
                f"This sample cannot determine {objective}; background text is not a finding or proof of safety. ")
    if failed:
        summary += f"{failed} selected read(s) failed or timed out. "
    summary += ("No exhaustive brand/source coverage or independently verified threat assessment is established."
                if domain == "brand" else "No media forensics or exhaustive platform coverage is established.")
    if public_statements:
        summary += f" {public_statements} public statement record(s) have observed author/speaker attribution in the capture; this is not authenticated identity or evidence of abuse."
    leads = corpus.get("ranked_candidates") or []
    leads = leads if isinstance(leads, list) else []
    next_steps = []
    for lead in leads:
        if not isinstance(lead, dict):
            continue
        title = lead.get("title")
        if isinstance(title, str) and matches_objective(title, domain):
            next_steps.append("Acquire and review the original report: " + title[:170] +
                              ". The discovery headline alone is not confirmation.")
        if len(next_steps) >= 2:
            break
    if not next_steps:
        next_steps.append(
            f"Supply a specific brand allegation, product issue, listing or claim URL for {target}; generic catalogs cannot resolve the question."
            if domain == "brand" else
            f"Supply a concrete suspect account, listing or claim URL for {target}; generic profiles/catalogs cannot answer the abuse question.")
    next_steps.append("Check disclosed read failures and authorized source access before broadening the investigation.")
    next_steps.append("Preserve and independently review exact supporting passages before any alert, accusation or takedown.")
    return {"status": state, "records": len(records), "profiles": profiles,
            "task_text_candidates": len(relevant), "discovery_only": discovery,
            "failed_reads": failed, "entailment_verified": False}, summary, next_steps
