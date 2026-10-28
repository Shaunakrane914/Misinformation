"""
Aegis Protocol — Personal Watch Threat Assessment
=================================================
Synthesizes personal threats, claims, and narratives.
Includes LLM reasoning with untrusted data boundary and offline heuristic fallback.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from typing import Any, Dict, List

from backend.agents.personal_watch.extraction import personal_watch_extractor
from backend.services.agent_reach.channels import EvidenceFragment

logger = logging.getLogger(__name__)


def heuristic_threat_synthesis(
    subject_name: str,
    evidence_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Deterministic, offline fallback synthesis when Gemini is unavailable.
    Classifies threats using regex keywords and provenance matching without hallucinating.
    """
    frags = [
        EvidenceFragment(
            platform=ev.get("platform", "web"),
            title=ev.get("title", ""),
            content=ev.get("content", "") or ev.get("snippet", ""),
            snippet=ev.get("snippet", "") or ev.get("content", "")[:200],
            url=ev.get("url", ""),
            author=ev.get("author", ""),
            published=ev.get("published", ""),
            evidence_id=ev.get("evidence_id", ""),
        )
        for ev in evidence_list
    ]
    personal_intel = personal_watch_extractor.extract_personal_intelligence(
        person_name=subject_name,
        fragments=frags,
    )

    threats: List[Dict[str, Any]] = [t.to_dict() if hasattr(t, "to_dict") else t for t in personal_intel.threats]
    claims: List[Dict[str, Any]] = []
    narratives: List[Dict[str, Any]] = []
    impersonations: List[Dict[str, Any]] = [i.to_dict() if hasattr(i, "to_dict") else i for i in personal_intel.impersonations]
    scams: List[Dict[str, Any]] = []
    deepfakes: List[Dict[str, Any]] = []

    for i, ev in enumerate(evidence_list):
        text = f"{ev.get('title', '')} {ev.get('content', '')}".lower()
        ev_id = ev["evidence_id"]
        plat = ev.get("platform", "Web")

        # 1. Impersonation detection
        if any(w in text for w in ["impersonat", "fake account", "fake profile", "spoofed", "fake handle"]):
            threats.append({
                "threat_id": f"thr_imp_{i+1}",
                "threat_type": "IMPERSONATION",
                "risk_level": "HIGH",
                "title": f"Potential Impersonation Account Detected for {subject_name}",
                "reason": f"Signals of lookalike profile or unauthorized representation detected on {plat}.",
                "platform": plat,
                "evidence_ids": [ev_id],
                "confidence": 0.82,
                "indicators": ["Name similarity", "Unofficial profile mention"]
            })
            impersonations.append({
                "platform": plat,
                "handle": ev.get("author", "Unknown"),
                "claimed_identity": subject_name,
                "indicators": ["Lookalike account mention in evidence"],
                "evidence_ids": [ev_id]
            })

        # 2. Scam / Phishing detection
        elif any(w in text for w in ["scam", "phishing", "fake giveaway", "crypto fraud", "send btc", "investment scheme"]):
            threats.append({
                "threat_id": f"thr_scm_{i+1}",
                "threat_type": "SCAM",
                "risk_level": "HIGH",
                "title": f"Fraudulent Scam / Giveaway Campaign Exploiting {subject_name}",
                "reason": "Circulating scheme soliciting funds or credentials using subject's identity.",
                "platform": plat,
                "evidence_ids": [ev_id],
                "confidence": 0.88,
                "indicators": ["Urgent solicitations", "Unverified promotional claims"]
            })
            scams.append({
                "offer": "Fraudulent giveaway or investment solicitation",
                "call_to_action": "Solicitation flagged in report",
                "indicators": ["Unverified financial solicitation"],
                "evidence_ids": [ev_id]
            })

        # 3. Deepfake / Synthetic media claims
        elif any(w in text for w in ["deepfake", "ai voice", "voice clone", "manipulated video", "synthetic audio", "elevenlabs"]):
            threats.append({
                "threat_id": f"thr_df_{i+1}",
                "threat_type": "DEEPFAKE",
                "risk_level": "HIGH",
                "title": f"Deepfake / Synthetic Voice Manipulation Claim: {subject_name}",
                "reason": "Public discourse reports circulated synthetic media or AI clone. Technical forensic verification unavailable.",
                "platform": plat,
                "evidence_ids": [ev_id],
                "confidence": 0.78,
                "indicators": ["AI voice clone report", "Synthetic media mention"]
            })
            deepfakes.append({
                "claim_text": f"Deepfake/synthetic quote reported in {ev.get('title', '')}",
                "technical_forensics_run": False,
                "forensic_status": "Deepfake claim reported in public discourse. Technical verification unavailable.",
                "evidence_ids": [ev_id]
            })

        # 4. Doxxing / Privacy exposure
        elif any(w in text for w in ["doxx", "leaked database", "leaked phone", "leaked address", "credential breach"]):
            threats.append({
                "threat_id": f"thr_dox_{i+1}",
                "threat_type": "DOXXING_PRIVACY",
                "risk_level": "HIGH",
                "title": f"Public Doxxing / Credential Leak Mention for {subject_name}",
                "reason": "Public records reference exposed contact data or database leaks.",
                "platform": plat,
                "evidence_ids": [ev_id],
                "confidence": 0.85,
                "indicators": ["Public breach mention"]
            })

        # 5. Reputation attack / False claims
        elif any(w in text for w in ["allegation", "controversy", "smear", "lawsuit", "boycott", "rumor", "defamation"]):
            threats.append({
                "threat_id": f"thr_rep_{i+1}",
                "threat_type": "REPUTATION_ATTACK",
                "risk_level": "MEDIUM",
                "title": "Reputational Controversy / Smear Narrative Circulating",
                "reason": f"Active controversy and critical discussion circulating on {plat}.",
                "platform": plat,
                "evidence_ids": [ev_id],
                "confidence": 0.75,
                "indicators": ["Allegation keywords", "Community contention"]
            })
            claims.append({
                "claim_id": f"clm_{i+1}",
                "text": ev.get("title", f"Claim regarding {subject_name}"),
                "status": "unverified",
                "confidence": 0.65,
                "evidence_ids": [ev_id]
            })

    if not claims and evidence_list:
        claims.append({
            "claim_id": "clm_01",
            "text": f"Public discourse regarding {subject_name} activity and public statements.",
            "status": "unverified",
            "confidence": 0.0,
            "evidence_ids": [evidence_list[0]["evidence_id"]]
        })

    return {
        "threats": threats,
        "claims": claims,
        "narratives": narratives,
        "suspected_impersonations": impersonations,
        "suspected_scams": scams,
        "deepfake_claims": deepfakes,
        "ai_enrichment_active": False,
        "status_note": "AI enrichment offline: threats derived via deterministic rule-based pattern extraction."
    }


def _source_report_synthesis(subject_name, evidence_list):
    """Normalize captured allegations without inventing observed actors or risk.

    These records enter through UNVERIFIED_ALLEGATION passages. Neither the
    publisher's byline nor a report about a recording is a captured suspect
    account/media asset. The legacy extractor's keyword scores cannot establish
    either. Keep one report observation per primary kind and canonical source
    set, while preserving every exact supporting passage for inspection.
    """
    result = {"threats": [], "claims": [], "narratives": [],
              "suspected_impersonations": [], "suspected_scams": [],
              "deepfake_claims": [], "ai_enrichment_active": False}
    kinds = [
        ("IMPERSONATION", r"impersonat|fake account|fake profile|spoofed|fake handle"),
        ("SCAM", r"scam|phishing|fake giveaway|fraud|send btc|investment scheme"),
        ("DEEPFAKE", r"deepfake|ai[- ]generated|ai voice|voice clone|manipulated video|synthetic audio|elevenlabs"),
        ("DOXXING_PRIVACY", r"doxx|leaked database|leaked phone|leaked address|credential breach"),
        ("REPUTATION_ATTACK", r"allegation|controversy|smear|lawsuit|boycott|rumor|defamation"),
    ]
    observations = {}
    for record in evidence_list:
        passages = record["allegation_passages"]
        text = "\n\n".join(p["text"] for p in passages)
        detected = [kind for kind, pattern in kinds if re.search(pattern, text, re.I)]
        if not detected:
            continue
        kind = detected[0]
        evidence_ids = list(dict.fromkeys(p["evidence_id"] for p in passages))
        key = (kind, tuple(sorted(evidence_ids)))
        if key in observations:
            existing = observations[key]["source_passages"]
            known = {p["passage_id"] for p in existing}
            existing.extend(dict(p) for p in passages if p["passage_id"] not in known)
            continue
        observation = {
            "threat_id": f"reported_{kind.lower()}_{len(observations) + 1}",
            "threat_type": kind, "risk_level": "UNASSESSED",
            "title": f"Source-reported {kind.lower().replace('_', ' ')} allegation concerning {subject_name}",
            "reason": "Captured publisher allegation; actor identity, current activity and authenticity are not established.",
            "platform": record.get("platform", "Web"), "evidence_ids": evidence_ids,
            "confidence": None, "confidence_basis": "NOT_ASSESSED",
            "confidence_is_heuristic": False, "epistemic_state": "UNVERIFIED",
            "assessment_status": "SOURCE_REPORT_ONLY", "technical_forensics_run": False,
            "direct_actor_capture": False, "observed_actor_url": None,
            "indicators": [], "reported_signal_types": detected,
            "source_report_title": record.get("title", ""),
            "source_report_url": record.get("canonical_url") or record.get("url", ""),
            "source_published_at": record.get("published_at") or record.get("published") or None,
            "source_date_status": "DECLARED_SOURCE_DATE_UNVERIFIED",
            "temporal_state": "CURRENT_ACTIVITY_NOT_ESTABLISHED",
            "source_passages": [dict(p) for p in passages],
        }
        observations[key] = observation
        result["threats"].append(observation)
        result["claims"].append({
            "claim_id": f"reported_claim_{len(observations)}", "text": passages[0]["text"],
            "status": "unverified", "confidence": None, "evidence_ids": evidence_ids,
            "assessment_status": "SOURCE_REPORT_ONLY", "source_passages": observation["source_passages"],
        })
        report = {"platform": record.get("platform", "Web"), "evidence_ids": evidence_ids,
                  "assessment_status": "SOURCE_REPORT_ONLY", "epistemic_state": "UNVERIFIED",
                  "source_report_url": observation["source_report_url"],
                  "source_published_at": observation["source_published_at"],
                  "source_date_status": observation["source_date_status"],
                  "temporal_state": observation["temporal_state"],
                  "source_passages": observation["source_passages"], "indicators": []}
        if kind == "IMPERSONATION":
            result["suspected_impersonations"].append({**report, "handle": None,
                "claimed_identity": subject_name, "observed_actor_url": None})
        elif kind == "SCAM":
            result["suspected_scams"].append({**report, "offer": None, "call_to_action": None})
        elif kind == "DEEPFAKE":
            result["deepfake_claims"].append({**report, "claim_text": passages[0]["text"],
                "technical_forensics_run": False,
                "forensic_status": "Source-reported synthetic media allegation; technical verification unavailable."})
    return result


def synthesize_personal_threats(subject_info, evidence_list):
    """Deterministic public observations; no generative threat adjudication."""
    from backend.schemas.evidence_inspection import METADATA_DEPTHS
    from backend.services.research.content_roles import document_role, NON_EVENT_ROLES
    from backend.services.research.passage_records import captured_passages
    subject_name = subject_info.get("canonical_name", subject_info.get("name", ""))
    records = []
    for ev in evidence_list:
        metadata = ev.get("metadata") or ev.get("raw_metadata") or {}
        depth = ev.get("content_depth") or metadata.get("content_depth")
        page = metadata.get("page_metadata") or {}
        if (document_role(ev) in NON_EVENT_ROLES | {"METADATA"}
                or depth in METADATA_DEPTHS | {"SEARCH_SNIPPET"} or metadata.get("layer2_eligible") is False
                or page.get("content_scope") in {"FEED_INDEX", "SITEMAP_INDEX", "PUBLIC_DISCOVERY_INDEX"}):
            continue
        # Normalization and output annotation must not alter the caller's raw
        # evidence, existing passage cache or nested metadata.
        records.append(copy.deepcopy(ev))
    if not records:
        return {"threats": [], "claims": [], "narratives": [], "suspected_impersonations": [],
                "suspected_scams": [], "deepfake_claims": [], "ai_enrichment_active": False,
                "public_statements": [], "disputed_claims": [], "identity_authenticated": False,
                "identity_risk": "UNASSESSED", "impersonation_status": "UNASSESSED",
                "status_note": "No verified live evidence was retrieved; metadata does not establish identity abuse."}
    for record in records:
        record["passages"] = captured_passages(record, "personal", subject_name)
    disputed = []
    disputed_ids = set()
    subject_tokens = re.findall(r"\w+", subject_name.casefold())
    for record in records:
        for passage in record["passages"]:
            text = passage["text"]
            # Broader quotation wording remains a source assertion, not a
            # statement authored by the monitored person or an adjudication.
            dispute = (passage["content_role"] == "DISPUTED_CLAIM" or bool(re.search(
                r"\b(?:fabricated|misattributed|false|fake)\s+(?:quote|quotation|claim)\b"
                r"|\bfalsely attributed\b|\b(?:did not|never)\s+(?:say|said|endorse|endorsed)\b", text, re.I)))
            target_link = bool(subject_tokens) and all(
                re.search(r"\b" + re.escape(token) + r"\b", text, re.I) for token in subject_tokens)
            if (not dispute or not target_link or passage["relevance"] in {"BACKGROUND", "DISCOVERY_ONLY"}
                    or passage["passage_id"] in disputed_ids):
                continue
            disputed_ids.add(passage["passage_id"])
            source_passage = {**copy.deepcopy(passage), "content_role": "DISPUTED_CLAIM",
                              "attribution": "SOURCE_ASSERTION", "claim_status": "UNVERIFIED"}
            disputed.append({
                "claim_id": "disputed_" + passage["passage_id"], "claim_type": "DISPUTED_ATTRIBUTION",
                "text": text, "speaker": None, "claim_status": "UNVERIFIED",
                "epistemic_state": "UNVERIFIED", "assessment_status": "SOURCE_REPORT_ONLY",
                "confidence": None, "identity_authenticated": False, "technical_forensics_run": False,
                "evidence_ids": [passage["evidence_id"]], "source_passages": [source_passage],
                "source_report_url": passage["source_url"], "source_published_at": passage["published_at"],
                "interpretation": "Publisher-reported disputed attribution; the quotation, original speaker and dispute are not independently verified.",
            })
    disputed = disputed[:16]
    # Public statements are observations, not identity-abuse incidents simply
    # because an author discusses scams, litigation or synthetic media policy.
    threat_records = []
    for record in records:
        title_link = bool(subject_name) and subject_name.casefold() in str(record.get("title", "")).casefold()
        body_link = bool(subject_name) and subject_name.casefold() in str(record.get("content", "")).casefold()
        passages = [p for p in record["passages"]
                    if (p["relevance"] == "DIRECTLY_RELEVANT" or title_link or body_link)
                    and p["content_role"] == "UNVERIFIED_ALLEGATION"
                    and p["passage_id"] not in disputed_ids]
        query_class = record.get("query_class") or (record.get("metadata") or {}).get("query_class")
        if passages and query_class != "public_statement_discovery":
            threat_records.append({**record, "allegation_passages": passages})
    result = _source_report_synthesis(subject_name, threat_records)
    if not threat_records:
        result["claims"] = []
    observed_attributions = {"OBSERVED_FEED_AUTHOR", "OBSERVED_SPEAKER_SECTION", "OBSERVED_SPEAKER_LABEL",
                             "OBSERVED_TRANSCRIPT_SPEAKER_SECTION",
                             "REPORTED_QUOTATION", "REPORTED_QUOTATION_SURNAME_IN_CAPTURE"}
    result["public_statements"] = [copy.deepcopy(p) for record in records for p in record["passages"]
                                   if p["content_role"] == "PUBLIC_STATEMENT"
                                   and p["attribution"] in observed_attributions
                                   and p["relevance"] not in {"BACKGROUND", "DISCOVERY_ONLY"}
                                   and p["passage_id"] not in disputed_ids][:16]
    for statement in result["public_statements"]:
        statement.update(speaker=subject_name, identity_authenticated=False,
                         interpretation="Publisher-attributed public statement; attribution is not independently verified.")
    result["disputed_claims"] = disputed
    result["identity_authenticated"] = False
    result["identity_risk"] = "UNVERIFIED_ALLEGATIONS" if threat_records else "UNASSESSED"
    result["impersonation_status"] = "UNVERIFIED_ALLEGATION" if result["suspected_impersonations"] else "UNASSESSED"
    result["status_note"] = "Captured public observations and unverified allegations; identity, intent and media authenticity are not established."
    return result


def verify_identity_match(
    catalog_profile: Dict[str, Any],
    candidate_record: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage 8C Personal Watch Specialization:
    Distinguishes the monitored VIP reference persona from ambiguous namesake candidates.
    Matches entity name, corporate affiliation, executive title, and known handles.
    """
    import re
    canonical_name = catalog_profile.get("canonical_name") or catalog_profile.get("name", "")
    known_orgs = [o.lower() for o in catalog_profile.get("affiliations", catalog_profile.get("organizations", []))]
    known_titles = [t.lower() for t in catalog_profile.get("titles", catalog_profile.get("roles", []))]
    known_handles = [h.lower().lstrip("@") for h in catalog_profile.get("known_handles", [])]

    cand_text = f"{candidate_record.get('title', '')} {candidate_record.get('snippet', '')} {candidate_record.get('content', '')}".lower()
    cand_author = candidate_record.get("author", "").lower().lstrip("@")

    # Name check
    name_clean = canonical_name.lower().strip()
    if not name_clean or name_clean not in cand_text:
        return {
            "match_status": "MATCH_REJECTED_NAMESAKE",
            "match_confidence": 0.05,
            "canonical_name": canonical_name,
            "rationale": "Candidate record does not mention the subject's canonical name."
        }

    org_matches = [org for org in known_orgs if org in cand_text]
    title_matches = [t for t in known_titles if t in cand_text]
    handle_match = any(h in cand_author or h in cand_text for h in known_handles) if known_handles else False

    score = 0.50  # Name is present
    if org_matches:
        score += 0.25
    if title_matches:
        score += 0.15
    if handle_match:
        score += 0.15

    score = min(0.99, score)

    # Check for strong conflicting professional domains (e.g. subject is Tech CEO, but candidate is local dentist)
    conflicting_roles = {"dentist", "plumber", "high school student", "realtor", "mechanic", "athlete"}
    has_conflict = any(re.search(rf'\b{r}\b', cand_text) for r in conflicting_roles) and not any(r in "".join(known_titles) for r in conflicting_roles)

    if has_conflict and not org_matches:
        return {
            "match_status": "MATCH_REJECTED_NAMESAKE",
            "match_confidence": 0.20,
            "canonical_name": canonical_name,
            "matched_affiliations": [],
            "rationale": f"Candidate mentions '{canonical_name}' but describes an incompatible profession/domain without organizational affiliation."
        }

    if score >= 0.75:
        status = "CONTEXTUAL_MATCH_UNVERIFIED"
        rationale = f"Candidate text contextually matches '{canonical_name}' and affiliation ({', '.join(org_matches) or 'title/handle'}); identity is not authenticated."
    elif score >= 0.50 and (known_orgs or known_titles):
        status = "AMBIGUOUS_NAMESAKE"
        rationale = f"Candidate mentions '{canonical_name}' but lacks confirming corporate affiliation or title context."
    else:
        status = "CONTEXTUAL_MATCH_UNVERIFIED"
        rationale = f"Candidate matches '{canonical_name}'."

    return {
        "match_status": status,
        "match_confidence": round(score, 2),
        "canonical_name": canonical_name,
        "matched_affiliations": org_matches,
        "matched_titles": title_matches,
        "identity_authenticated": False,
        "assessment_is_heuristic": True,
        "rationale": rationale
    }


def detect_doxxing_exposure(
    subject_name: str,
    text: str
) -> Dict[str, Any]:
    """
    Stage 8C Personal Watch Specialization:
    Scans candidate text for unauthorized exposure of Personally Identifiable Information (PII):
    residential street addresses, personal phone numbers, Social Security Numbers, and personal emails.
    """
    import re
    findings = []
    severity = "NOMINAL"

    # 1. Phone number pattern: US/intl formats
    phone_regex = re.compile(r'(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
    phones = phone_regex.findall(text)
    for p in phones:
        findings.append({"type": "PHONE_NUMBER", "redacted_value": p[:3] + "XXX-XXXX", "severity": "HIGH"})
        if severity in ("NOMINAL", "MEDIUM"):
            severity = "HIGH"

    # 2. SSN / National ID pattern: \d{3}-\d{2}-\d{4}
    ssn_regex = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    ssns = ssn_regex.findall(text)
    for s in ssns:
        findings.append({"type": "GOVERNMENT_ID_SSN", "redacted_value": "XXX-XX-" + s[-4:], "severity": "CRITICAL"})
        severity = "CRITICAL"

    # 3. Personal email pattern (free webmail domains)
    email_regex = re.compile(r'\b[A-Za-z0-9._%+-]+@(?:gmail|yahoo|hotmail|outlook|icloud|protonmail)\.com\b', re.I)
    emails = email_regex.findall(text)
    for em in emails:
        parts = em.split("@")
        findings.append({"type": "PERSONAL_EMAIL", "redacted_value": parts[0][:2] + "***@" + parts[1], "severity": "HIGH"})
        if severity != "CRITICAL":
            severity = "HIGH"

    # 4. Physical address pattern: street number + suffix (Street, St, Ave, Road, Rd, Drive, Dr, Blvd, Terrace) + Zip
    addr_regex = re.compile(r'\b\d{1,5}\s+[A-Za-z0-9\s.,]{3,30}\s+(?:street|st|avenue|ave|road|rd|drive|dr|court|ct|boulevard|blvd|lane|ln|terrace|ter|way|place|pl)\b', re.I)
    addrs = addr_regex.findall(text)
    for a in addrs:
        findings.append({"type": "RESIDENTIAL_ADDRESS", "redacted_value": a[:6] + " [REDACTED STREET ADDRESS]", "severity": "CRITICAL"})
        severity = "CRITICAL"

    return {
        "status": "PII_PATTERN_REQUIRES_REVIEW" if findings else "NO_PII_PATTERN_IN_SAMPLE",
        "unauthorized_exposure_verified": False,
        "assessment_is_heuristic": True,
        "subject_name": subject_name,
        "exposure_severity": severity,
        "pii_findings_count": len(findings),
        "findings": findings,
        "defensive_recommendation": (
            "Urgently verify subject linkage, privacy context and authorization before escalating or requesting removal."
            if severity == "CRITICAL"
            else ("Review subject linkage and public/private context before requesting removal." if severity == "HIGH" else "No PII pattern was established in this sample.")
        )
    }


def assess_synthetic_media_allegations(
    evidence_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 8C Personal Watch Specialization:
    Differentiates confirmed deepfake/voice clone operations from authentic verified footage or debunked claims.
    """
    import re
    if not evidence_list:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "epistemic_state": "UNVERIFIED",
            "confidence": 0.0,
            "summary": "No media evidence items provided for synthetic media assessment."
        }

    deepfake_keywords = {"deepfake", "ai voice", "voice clone", "synthetic audio", "elevenlabs", "face swap"}
    debunk_keywords = {"debunked", "false claim", "authentic video", "original footage", "verified by reuters", "fact-check"}

    synthetic_claims = 0
    debunk_claims = 0
    primary_authentic = 0

    media_indicators = {"video", "audio", "recording", "broadcast", "speech", "interview", "podcast", "footage", "clip", "stream", "livestream", "youtube", "vimeo", "mp4", "mp3", "wav"}
    media_count = 0

    for ev in evidence_list:
        text = f"{ev.get('title', '')} {ev.get('snippet', '')} {ev.get('content', '')} {ev.get('url', '')}".lower()
        if any(w in text for w in deepfake_keywords):
            synthetic_claims += 1
        if any(w in text for w in debunk_keywords):
            debunk_claims += 1
        if re.search(r'https?://[^\s]+\.(?:mp4|mp3|wav|webm)(?:[?\s]|$)|https?://(?:www\.)?(?:youtube\.com/watch\?|youtu\.be/|vimeo\.com/\d)', text):
            media_count += 1
        if ev.get("source_role") in ("PRIMARY", "PRIMARY_OFFICIAL"):
            primary_authentic += 1

    if debunk_claims >= 1:
        epistemic = "REPORTED_DEBUNKING_UNVERIFIED"
        conf = 0.35
        expl = "The sample contains debunking language. This text-only screen does not establish which recording was examined or verify its authenticity."
    elif synthetic_claims >= 2 and debunk_claims == 0:
        epistemic = "SUSPICIOUS_UNVERIFIED_SYNTHETIC_CLAIM"
        conf = 0.70
        expl = "Multiple sources report viral synthetic media circulating without formal forensic verification or primary corroboration."
    elif synthetic_claims == 0 and primary_authentic >= 1 and media_count >= 1:
        epistemic = "UNVERIFIED_MEDIA_AUTHENTICITY"
        conf = 0.0
        expl = "A media URL was referenced by a primary-labeled record. No recording bytes or forensic analysis were performed; authenticity remains unverified."
    elif media_count == 0 and synthetic_claims == 0:
        epistemic = "UNVERIFIED_IN_SAMPLE"
        conf = 0.0
        expl = "Evaluated sample contains no audio or video recording assets; cannot establish recording authenticity or absence of threats across the internet."
    else:
        epistemic = "UNVERIFIED"
        conf = 0.45
        expl = "Insufficient signals to establish authenticity or synthetic status."

    return {
        "status": "ANALYSIS_COMPLETE",
        "epistemic_state": epistemic,
        "confidence": conf,
        "synthetic_mentions": synthetic_claims,
        "debunk_mentions": debunk_claims,
        "media_assets_analyzed": 0,
        "media_assets_referenced": media_count,
        "summary": expl
    }


def verify_quote_attribution(
    subject_name: str,
    quote: str,
    evidence_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 8C Personal Watch Specialization:
    Cross-checks a controversial quote attributed to the subject against official speeches,
    press transcripts, and debunking reports to verify authenticity or expose fabrication.
    """
    if not quote or not evidence_list:
        return {
            "subject": subject_name,
            "quote": quote,
            "verdict": "INSUFFICIENT_EVIDENCE",
            "confidence": 0.0,
            "summary": "Zero evidence or empty quote provided for attribution analysis."
        }

    import re
    quote_clean = quote.lower().strip("\"' ")
    quote_words = set(re.findall(r'[a-z]{3,}', quote_clean))

    primary_matches = []
    debunk_matches = []
    social_only_matches = []

    for ev in evidence_list:
        text = f"{ev.get('title', '')} {ev.get('snippet', '')} {ev.get('content', '')}".lower()
        shared = quote_words & set(re.findall(r'[a-z]{3,}', text))
        overlap_ratio = len(shared) / max(1, len(quote_words))

        is_debunk = any(w in text for w in ["never said", "fabricated quote", "misattributed", "false quote", "fake quote", "debunked"])
        is_primary = ev.get("source_role") in ("PRIMARY", "PRIMARY_OFFICIAL")

        if is_debunk and overlap_ratio >= 0.40:
            debunk_matches.append(ev)
        elif is_primary and overlap_ratio >= 0.70:
            primary_matches.append(ev)
        elif overlap_ratio >= 0.40:
            social_only_matches.append(ev)

    if debunk_matches:
        verdict = "REPORTED_MISATTRIBUTION_UNVERIFIED"
        conf = 0.35
        summary = "The sample contains overlapping words and debunking language; speaker, exact quote and transcript attribution require review."
    elif primary_matches:
        verdict = "UNVERIFIED_PRIMARY_TEXT_MATCH"
        conf = 0.35
        summary = "Primary-labeled text overlaps the quote; word overlap does not verify speaker attribution, context or an original recording."
    elif social_only_matches and not primary_matches:
        verdict = "UNVERIFIED_SECONDARY_TEXT_MATCH"
        conf = 0.35
        summary = "Secondary source text overlaps the quote; original speaker attribution, context and circulation or virality are not established."
    else:
        verdict = "INSUFFICIENT_EVIDENCE"
        conf = 0.0
        summary = "No evidence items directly matched the wording of this statement."

    return {
        "subject": subject_name,
        "quote": quote,
        "verdict": verdict,
        "confidence": conf,
        "primary_matches_count": len(primary_matches),
        "debunk_matches_count": len(debunk_matches),
        "assessment_is_heuristic": True,
        "summary": summary
    }

