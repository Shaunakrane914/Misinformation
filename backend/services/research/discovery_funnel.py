"""Measured acquisition boundaries; unknown historic provider counts stay unknown."""
from collections import Counter
from backend.services.research.content_roles import document_role
from backend.services.research.passage_extractor import has_usable_passage
from backend.schemas.evidence_inspection import METADATA_DEPTHS


def summarize_qualification_decisions(rejected):
    """Keep source qualification separate from observed publisher-link audits.

    A homepage can expose hundreds of rejected navigation links without those
    links ever becoming research candidates. Counts below are distinct source
    identities; decision/audit event counts are separately labeled observations.
    Full counts are computed before the bounded diagnostic samples are taken.
    """
    from backend.services.research.source_identity import source_url_key
    qualification, links = [], []
    identities, stage_ids, reason_ids = set(), {}, {}
    unidentifiable = 0
    for row in rejected:
        if not isinstance(row, dict):
            continue
        if row.get("parent_id") and not (row.get("candidate_id") or row.get("evidence_id")):
            links.append(dict(row))
            continue
        if row.get("is_accepted") is True:
            continue
        normalized = dict(row)
        reason = row.get("rejection_reason") or row.get("reason") or row.get("discard_reason")
        stage = row.get("rejection_stage") or ("CANDIDATE_SELECTION" if row.get("candidate_id") else "QUALIFICATION")
        normalized.update(rejection_stage=stage, rejection_reason=reason or "UNRECORDED_REASON")
        qualification.append(normalized)
        url = row.get("url") or row.get("canonical_url") or row.get("source_url")
        identity = source_url_key(url) if isinstance(url, str) and url else None
        identity = identity or row.get("candidate_id") or row.get("evidence_id") or row.get("id")
        if not identity:
            unidentifiable += 1
            continue
        identities.add(identity)
        stage_ids.setdefault(stage, set()).add(identity)
        reason_ids.setdefault(normalized["rejection_reason"], set()).add(identity)
    return {
        "qualification_rejections": qualification[:100],
        "qualification_decision_count": len(qualification),
        "rejected_candidate_count": len(identities),
        "qualification_decisions_without_identity": unidentifiable,
        "qualification_rejection_counts_by_stage": {key: len(ids) for key, ids in stage_ids.items()},
        "qualification_rejection_counts_by_reason": {key: len(ids) for key, ids in reason_ids.items()},
        "publisher_link_audit_from_rejections": links[:200],
        "publisher_link_decision_count": len(links),
        "publisher_link_discard_reasons": dict(Counter(
            row.get("discard_reason") or row.get("reason") for row in links
            if row.get("discard_reason") or row.get("reason"))),
        "qualification_count_scope": "Distinct observed source identities, not link-audit events; one source can have multiple reasons",
    }


def build_discovery_funnel(plan, query_records, raw, accepted, rejected, read, findings):
    rows = [row.to_dict() if hasattr(row, "to_dict") else row for row in query_records]
    attempts = read.telemetry.get("acquisition_attempts", [])
    nested = [row for attempt in attempts for row in (attempt.get("wrapper_resolution") or {}).get("query_records", [])]
    provider_rows = [provider for row in rows + nested for provider in row.get("search_attempts", [])]
    bodies = [item for item in read.investigated if item.content and item.metadata.get("read_success")
              and item.content_depth not in METADATA_DEPTHS and document_role(item) != "ASSET_METADATA"]
    articles = [item for item in bodies if document_role(item) == "SUBSTANTIVE_CANDIDATE"]
    qualified = [item for item in articles if has_usable_passage(item) and item.extraction_status == "SUCCESS"]
    decisions = [decision for provider in provider_rows for decision in provider.get("decisions", [])]
    from backend.services.research.source_identity import source_url_key
    observed_urls = {source_url_key(row["url"]) for row in decisions
                     if isinstance(row, dict) and isinstance(row.get("url"), str) and row["url"]}
    # Final qualification can empty `accepted` after actual reads. Never move
    # that loss backwards to pre-read selection merely because its list is empty.
    selection_observed = bool(accepted or attempts or read.investigated or read.telemetry.get("attempted")
                              or read.telemetry.get("read_failure_reason") == "READING_DEADLINE_EXHAUSTED")
    boundary = ("PLANNING" if not rows and not raw and not selection_observed else
                "SEARCH_TRANSPORT" if not raw and rows and not any(row.get("status") == "SUCCESS" for row in rows) else
                "SEARCH_RANKING" if not raw and any(provider.get("candidate_count", 0) for provider in provider_rows) else
                "DISCOVERY_NO_RESULTS" if not raw and not selection_observed else
                "CANDIDATE_QUALIFICATION" if not selection_observed else
                "READING_BUDGET" if not bodies and read.telemetry.get("read_failure_reason") == "READING_DEADLINE_EXHAUSTED" else
                "PUBLISHER_RESOLUTION" if not articles and any(row.get("failure_kind") == "PUBLISHER_UNRESOLVED" for row in attempts) else
                "READING" if not bodies else "ARTICLE_EXTRACTION" if not articles else
                "BODY_OR_PASSAGE_QUALIFICATION" if not qualified else None)
    rejected_summary = summarize_qualification_decisions(rejected)
    return {
        "scope": "Main queries plus separately labeled nested resolver attempts; not complete HTTP accounting or independent accuracy",
        "generated_queries": [{"channel": channel, **query} for channel, queries in plan.channel_queries.items() for query in queries],
        "query_records": len(rows), "provider_attempts_observed": len(provider_rows) if provider_rows else None,
        "query_records_without_provider_observations": sum(not row.get("search_attempts") for row in rows),
        "provider_coverage_limit": "Instrumented web and news/RSS search calls; other absent observations are unknown, not zero requests; legacy fallback transport unverified",
        "search_responses_observed": sum(row.get("response_received") is True for row in provider_rows) if provider_rows else None,
        "provider_observations": provider_rows,
        "candidate_urls_observed_in_search_sample": len(observed_urls),
        "candidate_url_decision_events_observed_in_search_sample": len(decisions),
        "candidate_search_discards": dict(Counter(row["discard_reason"] for row in decisions if row.get("discard_reason"))),
        "normalized_candidates": len(raw), "accepted_candidates": len(accepted),
        **rejected_summary,
        "selected_acquisition_attempts": read.telemetry.get("attempted", 0),
        "read_attempts": attempts,
        "read_failure_reasons": dict(Counter(row.get("failure_kind", "UNKNOWN") for row in attempts if row.get("status") != "SUCCESS")),
        "successful_body_captures": len(bodies), "extracted_article_bodies": len(articles),
        "qualified_evidence": len(qualified), "qualified_evidence_ids": [item.id for item in qualified],
        "agent_research_findings": len(findings),
        "unverified_or_uninvestigated_findings": sum(getattr(item, "epistemic_state", "") in {
            "UNVERIFIED", "UNKNOWN_NOT_INVESTIGATED", "INSUFFICIENT_EVIDENCE"} for item in findings),
        "empty_findings_abstention": not bool(findings),
        "first_observed_empty_boundary": boundary,
        "causal_limit": "An empty boundary is not proof that rejected or inaccessible sources were relevant; inspect candidate decisions",
        "publisher_link_audit": read.telemetry.get("publisher_link_audit", []),
        "reading_failure_reason": read.telemetry.get("read_failure_reason"),
        "duplicate_captures": read.telemetry.get("duplicate_captures", []),
        "post_read_qualification": [{"id": item.id, "status": item.extraction_status,
                                     "reason": item.metadata.get("post_read_qualification_reason")}
                                    for item in read.investigated],
    }
