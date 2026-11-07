"""Task-scoped answer from retained cited passages, never an absence-of-risk verdict."""
from urllib.parse import urlsplit


def build_answer(report, data):
    evidence = [item for name in ("primary", "independent", "community") for item in getattr(report.evidence, name)]
    primary_ids = {item.evidence_id for item in evidence if item.source.is_primary}
    passages = report.evidence_workbench.get("passages", [])
    relevant = [p for p in passages if p.get("relevance") == "DIRECTLY_RELEVANT"]
    gaps = ["Source independence has not been verified."]
    selected = relevant
    if report.agent == "scout":
        selected = [p for p in relevant if p.get("content_role") == "FINANCIAL_STATEMENT" and p.get("evidence_id") in primary_ids]
        disclosures = data.get("financial_disclosures") or {}
        comparisons = disclosures.get("comparisons") or []
        facts = disclosures.get("facts") or []
        summary = (f"{len(selected)} cited primary financial passage(s); {len(facts)} structured financial source assertion(s); {len(comparisons)} compatible comparison(s). "
                   "Source assertions retain their fiscal scope; current-period completeness is not established.")
        gaps += ["Reconcile the requested fiscal period, currency, units and actual results versus guidance with the original filing."]
        action = "Open the cited issuer disclosure and compare the exact reporting period and units before relying on a financial amount."
    elif report.agent == "brandshield":
        selected = [p for p in relevant if p.get("content_role") in {"UNVERIFIED_ALLEGATION", "REPORTED_INCIDENT", "REPORTED_ENFORCEMENT", "DISPUTED_CLAIM", "SAFETY_WARNING", "CUSTOMER_COMPLAINT"}]
        summary = f"{len(selected)} cited incident/allegation passage(s). Reporting is attributed; an allegation is not a confirmed outcome or an active campaign."
        gaps += ["Primary incident confirmation, affected product/domain and case outcome require review."]
        action = "Check the named incident against its original agency/manufacturer notice; preserve allegation, denial and case-stage qualifications."
    elif report.agent == "personal_watch":
        selected = [p for p in relevant if p.get("content_role") == "PUBLIC_STATEMENT" and p.get("attribution") != "SOURCE_ASSERTION"]
        original = sum(p.get("evidence_id") in primary_ids for p in selected)
        summary = f"{len(selected)} attributed statement passage(s), {original} from classified primary sources. Reported quotations remain distinct from original statements; identity is not authenticated."
        gaps += ["A statement's publication date may differ from its event date."]
        action = "Compare the exact suspect quotation or account with the original transcript/recording; a name-only search does not verify a deception claim."
        import re
        if re.search(r"\b(?:false|fake|fabricated|misattributed)\s+(?:quotes?|statements?)\b|did not say", report.query or "", re.I):
            selected = []
            summary = "Exact-claim verification is unresolved. Ordinary interviews or attributed statements do not establish whether the disputed words were authentic."
            gaps.append("The exact quotation and original recording/transcript must be compared; no authenticity verdict is established here.")
    elif report.agent == "trending":
        from backend.services.research.temporal_guard import requested_trending_window
        observed_window = (data.get("retrieval_trace") or {}).get("trending_window_hours")
        window = (observed_window if type(observed_window) in (int, float) and 1 <= observed_window <= 168
                  else requested_trending_window(report.query))
        summary = f"{len(selected)} cited coverage passage(s) qualified under the requested {window:g}-hour window. Reporting volume does not establish popularity or narrative acceleration."
        gaps += ["Repeated comparable attention observations are needed to measure a trend."]
        action = "Review the dated reports and their event dates; compare a later observation over the same source set to assess attention change."
    else:
        return None
    if not selected and not (report.agent == "scout" and (data.get("financial_disclosures") or {}).get("facts")):
        summary = "No cited passage answers this task in the acquired sample. " + summary
        gaps.insert(0, "The requested evidence is missing; this does not establish absence of information or risk.")
    observations = []
    if report.next_steps and report.next_steps[0].startswith("Acquire and review the original report:"):
        action = report.next_steps[0]  # an observed task-specific lead is more actionable than generic advice
    for passage in sorted(selected, key=lambda p: p.get("evidence_id") not in primary_ids)[:3]:
        observations.append({key: passage.get(key) for key in ("text", "evidence_id", "passage_id", "source_url", "published_at", "attribution", "content_role", "start", "end", "captured_text_sha256")})
    return {"summary": summary, "observations": observations, "gaps": gaps,
        "next_action": action, "task_passages": len(selected),
        "observed_publishers": len({urlsplit(item.url or "").hostname for item in evidence if item.url}),
        "independence_verified": False, "identity_authenticated": False}
