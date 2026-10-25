"""Source-relative brand observations, never adjudicated fraud or ownership.

A reporting URL identifies the document we acquired, not an actor mentioned by
that document. Only directly captured solicitations can supply an actor URL;
keyword matches in reporting or complaints cannot do so.
"""
import re


def _reported_legal_allegation(body):
    """Concrete reported filing/allegation, not a hypothetical advice example.

    Only acquired prose is considered. A warning mentioned by a lawsuit is not
    preventive guidance merely because the same document contains safety tips.
    This observes a source assertion; it does not authenticate a court filing.
    """
    for paragraph in re.split(r"\n\s*\n", body):
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            if re.search(r"\b(?:if|hypothetical|could|may|might|would|should|can)\b", sentence, re.I):
                continue
            if re.search(r"\b(?:lawsuits?|complaints?)\b[^.!?\n]{0,110}\b(?:filed|lodged|alleges?|accuses?)\b"
                         r"|\b(?:filed|lodged)\b[^.!?\n]{0,60}\b(?:lawsuits?|complaints?)\b", sentence, re.I):
                return True
    return False


def classify_brand_source(record, target=""):
    """Classify actual retained prose; titles alone do not establish activity."""
    body = str(record.get("content") or "")
    title = str(record.get("title") or "")
    depth = str(record.get("content_depth") or "").upper()
    outcome = {"evidence_id": record.get("evidence_id"), "source_url": record.get("url"),
               "classification": "BACKGROUND_INFORMATION", "actor_url": None,
               "epistemic_state": "UNVERIFIED", "ownership_verified": False}
    metadata = record.get("metadata") or record.get("raw_metadata") or {}
    page = metadata.get("page_metadata") or {}
    if isinstance(page, dict) and "article_body_recovery" in page:
        from backend.infrastructure.acquisition.adapters.web.page_extraction import recovered_span_allowed
        # This is an in-memory classification view, not a replacement capture.
        # Never let unrelated cards or stale recovery metadata restore a threat
        # that the exact-span passage extractor excluded.
        scoped = []
        for match in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", body):
            paragraph = match.group().rstrip()
            if recovered_span_allowed(body, page, match.start(), match.start() + len(paragraph)):
                scoped.append(paragraph)
        body = "\n\n".join(scoped)
        if not body:
            return {**outcome, "classification": "INSUFFICIENT_EVIDENCE", "reason": "NO_VALID_RECOVERED_ARTICLE_SPANS"}
    from backend.services.research.content_roles import document_role, paragraph_role, NON_EVENT_ROLES, LOCAL_BRAND_ABUSE, LOCAL_BRAND_WARNING, LOCAL_BRAND_NEGATION
    role = document_role(record)
    if role in NON_EVENT_ROLES - {"LANDING_PAGE"}:
        return {**outcome, "reason": "NON_INCIDENT_DOCUMENT_ROLE_" + role}
    if target and body:
        context = body + " " + title + " " + str(record.get("url") or "")
        tokens = re.findall(r"\w{2,}", target)
        if tokens and not all(re.search(r"\b" + re.escape(token) + r"\b", context, re.I) for token in tokens):
            return {**outcome, "classification": "INSUFFICIENT_EVIDENCE", "reason": "SUBJECT_NOT_ESTABLISHED"}
    if body:
        body = "\n\n".join(paragraph for paragraph in re.split(r"\n\s*\n", body)
                             if paragraph_role(paragraph) not in NON_EVENT_ROLES)
    if not body.strip() and not depth and record.get("snippet"):
        # Older adapters return title/snippet-only leads with no depth marker.
        # Keep that interface inspectable, explicitly below acquired evidence.
        text = title + " " + str(record["snippet"])
        if re.search(r"\b(?:delivery delayed|customer complaint|my refund)\b", text, re.I):
            return {**outcome, "classification": "CUSTOMER_COMPLAINT", "discovery_only": True,
                    "reason": "UNACQUIRED_COMPLAINT_LEAD"}
        if re.search(r"\b(?:counterfeit|replica|phishing|scam|recall|safety hazard)\b", text, re.I):
            return {**outcome, "classification": "REPORTED_ALLEGATION", "discovery_only": True,
                    "reason": "UNACQUIRED_ALLEGATION_LEAD"}
    if not body.strip() or depth in {"SNIPPET", "URL_ONLY", "DISCOVERY_ONLY", "PROFILE_METADATA"}:
        return {**outcome, "classification": "INSUFFICIENT_EVIDENCE", "reason": "NO_ACQUIRED_INCIDENT_PASSAGE"}
    # Text presented as an article is not necessarily its article body. The
    # caller's selected captured passages remain the source of supporting spans.
    if re.search(r"\b(?:I ordered|my order|my refund|never received|customer complaint|delivery delayed)\b", body, re.I):
        return {**outcome, "classification": "CUSTOMER_COMPLAINT", "reason": "COMPLAINT_NOT_ADJUDICATED_FRAUD"}
    abuse = re.search(r"\b(?:counterfeit\w*|replica\w*|knockoffs?|phishing|scams?|fraud\w*|impersonat\w*|credential\w*|fake)\b|" + LOCAL_BRAND_ABUSE, body, re.I)
    if abuse and re.search(LOCAL_BRAND_NEGATION, body, re.I):
        return {**outcome, "classification": "INSUFFICIENT_EVIDENCE", "reason": "NEGATED_OR_UNESTABLISHED_ALLEGATION"}
    attributed_disruption = re.search(
        r"\b(?:police|authorities|law enforcement|cyber command)\b[^.!?\n]{0,160}"
        r"\b(?:disrupted|dismantled|took down|shut down)\b[^.!?\n]{0,100}"
        r"\b(?:scams?|campaigns?|networks?|accounts?|operations?)\b", body, re.I)
    if abuse and (re.search(r"\b(?:seized|seizure|arrested|sentenced|convicted|charged|customs|court order|search warrant)\b", body, re.I)
                  or attributed_disruption):
        return {**outcome, "classification": "HISTORICAL_ENFORCEMENT", "reason": "REPORTED_ENFORCEMENT_NOT_CURRENT_ACTOR",
                "temporal_state": "HISTORICAL_OR_TIME_UNVERIFIED"}
    if abuse and _reported_legal_allegation(body):
        return {**outcome, "classification": "REPORTED_ALLEGATION",
                "reason": "REPORTED_LEGAL_ALLEGATION_NOT_PREVENTIVE_GUIDANCE"}
    warning = re.search(
        r"\b(?:beware|warning|warns|protect yourself|avoid scams|we never|we do not)\b"
        r"|\b(?:how to|tips to|guide to|recognize and avoid)\b.{0,70}\b(?:phishing|scams?|fraud|counterfeit)\b",
        body + " " + title, re.I)
    if not warning:
        # Preventive instructions need not use the literal word "warning".
        # Concrete filed allegations above still take precedence over advice.
        warning = re.search(r"\b(?:should|must)\s+(?:inspect|check|verify|review)\b[^.!?\n]{0,90}"
                            r"\b(?:seller|identity|details|link|account|before)\b", body, re.I)
    warning = warning or re.search(LOCAL_BRAND_WARNING, body + " " + title, re.I)
    if abuse and warning:
        official = str(record.get("source_role") or "").upper() in {"PRIMARY", "PRIMARY_OFFICIAL", "PRIMARY_REGULATORY"}
        return {**outcome, "classification": "OFFICIAL_WARNING" if official else "WARNING_ADVISORY",
                "reason": "PREVENTIVE_GUIDANCE_NOT_ACTIVE_ATTACK"}
    if abuse and re.search(r"\b(?:not (?:a |an )?(?:scam|counterfeit|phishing)|no evidence of (?:fraud|phishing|counterfeit))\b", body, re.I):
        return {**outcome, "classification": "INSUFFICIENT_EVIDENCE", "reason": "NEGATED_OR_UNESTABLISHED_ALLEGATION"}
    # Direct behavior must occur in acquired prose, not only in a headline or a
    # publisher's account of what another page allegedly requested.
    reporting = re.search(r"\b(?:reported|report (?:says|identifies|describes)|according to|researchers? (?:found|said|observed)|alleged\w*|victims? (?:said|reported)|instructed users|asked users)\b", body, re.I)
    solicitation = re.search(
        r"\b(?:send|transfer|deposit)\b.{0,60}\b(?:ETH|BTC|bitcoin|wallet)\b.{0,90}\b(?:receive|double|back|return)\b"
        r"|\b(?:enter|submit|verify)\b.{0,45}\b(?:password|credentials)\b"
        r"|\b(?:counterfeit|replica|knockoff)\b.{0,80}\b(?:for sale|buy now|add to cart|order now)\b"
        r"|\bbuy\b.{0,50}\b(?:counterfeit|replica|fake)\b",
        body, re.I)
    direct_voice = re.search(r"(?:^|[.!?\n])\s*(?:send|transfer|deposit|enter|submit|verify|buy|replica|counterfeit|knockoff)\b", body, re.I)
    if solicitation and direct_voice and not reporting:
        return {**outcome, "classification": "OBSERVED_SUSPICIOUS_ACTIVITY", "reason": "DIRECT_CAPTURED_SOLICITATION_UNVERIFIED",
                "actor_url": record.get("url") or None}
    if abuse or re.search(r"\b(?:recall(?:ed|s)?|safety hazard|battery fire|burn injury|lawsuit|subpoena|antitrust|regulatory (?:probe|inquiry|fine)|class action)\b", body, re.I):
        return {**outcome, "classification": "REPORTED_ALLEGATION", "reason": "SOURCE_ASSERTION_NOT_INDEPENDENTLY_VERIFIED"}
    return {**outcome, "reason": "NO_BRAND_INCIDENT_ESTABLISHED"}


def contextualize_brand_threat(threat, sources, target):
    """Remove actor/takedown inferences introduced by legacy keyword engines."""
    assessments = [classify_brand_source(source, target) for source in sources]
    classes = {entry["classification"] for entry in assessments}
    threat.update(epistemic_state="UNVERIFIED", confidence_is_heuristic=True,
                  ownership_verified=False, actor_url=None, source_urls=[s.get("url") for s in sources if s.get("url")])
    if any(entry.get("discovery_only") for entry in assessments):
        threat["discovery_only"] = True
        threat["acquired_evidence"] = False
    if classes & {"HISTORICAL_ENFORCEMENT"}:
        classification, relation, kind = "HISTORICAL_ENFORCEMENT", "REPORTS_ENFORCEMENT", "ENFORCEMENT_REPORT"
        summary = "The captured source reports earlier enforcement or legal action; current activity and any actor endpoint are not established."
    elif classes & {"OFFICIAL_WARNING", "WARNING_ADVISORY"}:
        classification = "OFFICIAL_WARNING" if "OFFICIAL_WARNING" in classes else "WARNING_ADVISORY"
        relation, kind = "REPORTS_SAFETY_ADVICE", "SAFETY_ADVISORY"
        summary = "The captured source publishes preventive guidance. A warning is not an observed active scam, counterfeit seller or confirmed threat."
    elif classes & {"CUSTOMER_COMPLAINT"}:
        classification, relation, kind = "CUSTOMER_COMPLAINT", "REPORTS_COMPLAINT", "CUSTOMER_COMPLAINT"
        summary = "The captured source records a customer complaint. Transaction facts, author authenticity and any allegation of fraud remain unverified."
    elif classes & {"OBSERVED_SUSPICIOUS_ACTIVITY"}:
        threat.update(classification="OBSERVED_SUSPICIOUS_ACTIVITY", source_relation="DIRECT_CAPTURE_OF_SUSPICIOUS_BEHAVIOR",
                      actor_url=next((entry["actor_url"] for entry in assessments if entry["actor_url"]), None),
                      is_threat=True, evidence_class="OBSERVED_SUSPICIOUS_BEHAVIOR_NOT_CONFIRMED_FRAUD",
                      confidence=None,
                      actionable_recommendation="Preserve the captured behavior and verify ownership, affiliation and context before considering an abuse report.")
        return threat
    elif classes & {"REPORTED_ALLEGATION"}:
        classification, relation = "REPORTED_ALLEGATION", "REPORTS_ALLEGATION"
        kind = threat.get("type") or threat.get("threat_type") or "UNVERIFIED_RUMOR"
        if kind in {"ENFORCEMENT_REPORT", "SAFETY_ADVISORY", "CUSTOMER_COMPLAINT"}:
            # The final full-source role overrides provisional legacy labels.
            kind = "REPORTED_ALLEGATION"
        summary = "The captured source reports a brand-related allegation or suspicious incident. Its reporting URL is not an attacker endpoint; the underlying claim is not independently verified."
        if kind == "PRODUCT_SAFETY" and any(re.search(
                r"\b(?:recall(?:ed|s)?|product.safety|safety hazard|battery fire|burn injur(?:y|ies))\b",
                str(source.get("content") or ""), re.I) for source in sources):
            # Preserve recall corrections/company responses in their exact
            # supporting spans. Product safety is not a synonym for fraud.
            summary = ("The captured source reports a product-safety issue or recall. "
                       "Review the exact supporting passage, including any correction or company response. "
                       "This record alone does not establish counterfeit sales, phishing or fraud.")
    else:
        return None
    threat.update(classification=classification, source_relation=relation, type=kind, threat_type=kind,
                  is_threat=False, confidence=None, severity="info" if kind != "CUSTOMER_COMPLAINT" else "low",
                  evidence_class=classification, title="Source-reported " + classification.lower().replace("_", " ") + " involving " + target,
                  summary=summary, description=summary,
                  actionable_recommendation="Inspect the captured passage, source date and named parties. Obtain direct, current actor evidence and verify context before legal escalation; this record alone does not justify a takedown.")
    return threat
