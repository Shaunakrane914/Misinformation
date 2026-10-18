"""
Aegis Protocol — BrandShield Assessment & Threat Synthesis
==========================================================
Deterministic review pattern screening, LLM-grounded threat reasoning,
and offline rule-based heuristic fallback synthesis.
"""

import json
import logging
import re
from typing import Any, Dict, List

from backend.agents.brandshield.dossier import build_investigation_dossiers
from backend.services.research.source_quality import is_utility_or_auth_url
from backend.services.research.content_roles import contains_word_or_phrase

logger = logging.getLogger(__name__)


def screen_review_patterns(evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministic review-pattern screening over retrieved evidence.
    Uses text normalization and pairwise Jaccard word-set similarity
    to detect near-duplicate wording or coordinated phrasing across review signals.
    Never fabricates conclusions without real pairwise analysis.
    """
    if not evidence_list:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "review_manipulation_detected": False,
            "assessment": "Insufficient evidence: no review signals retrieved for pattern screening.",
            "confidence": None,
            "signals_analyzed": 0,
            "near_duplicate_clusters": 0,
            "signals_found": [],
            "cluster_notes": "No reviews were retrieved by active search channels."
        }

    # Filter signals that contain genuine consumer review, feedback, rating, complaint, or seller discourse
    from backend.services.research.source_quality import is_utility_or_auth_url

    review_keywords = (
        "customer review", "product review", "seller review", "review", "rating",
        "star rating", "feedback", "complaint", "order", "buyer", "refund", "delivered",
        "seller", "star", "purchase", "recommend"
    )
    boilerplate_terms = {"skip", "main", "content", "cookie", "cookies", "terms", "privacy", "sign", "account", "rights", "reserved", "help", "manage"}

    review_candidates = []
    for ev in evidence_list:
        is_util, _ = is_utility_or_auth_url(ev.get("url", ""))
        if is_util:
            continue
        # Skip official corporate root pages from consumer review detection
        if ev.get("source_role") == "PRIMARY" and any(corp in (ev.get("url", "")).lower() for corp in ("microsoft.com", "apple.com", "tesla.com", "nvidia.com")):
            continue

        text = f"{ev.get('title', '')} {ev.get('snippet', '')} {ev.get('content', '')}".strip()
        text_lower = text.lower()
        if not any(k in text_lower for k in review_keywords):
            continue

        text_clean = re.sub(r'[^a-z0-9\s]', ' ', text_lower)
        text_clean = " ".join(text_clean.split())
        words = set(re.findall(r'[a-z]{3,}', text_lower)) - boilerplate_terms
        if len(words) >= 4:
            review_candidates.append({
                "evidence_id": ev.get("evidence_id", ""),
                "platform": ev.get("platform", "Web"),
                "text": text,
                "text_clean": text_clean,
                "words": words
            })

    signals_analyzed = len(review_candidates)
    if signals_analyzed < 2:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "review_manipulation_detected": False,
            "assessment": f"Insufficient review signals retrieved ({signals_analyzed} signals identified). At least 2 candidate texts are required for pairwise pattern analysis.",
            "confidence": None,
            "signals_analyzed": signals_analyzed,
            "near_duplicate_clusters": 0,
            "signals_found": [c["text"][:120] for c in review_candidates],
            "cluster_notes": "Minimum candidate volume not met for empirical similarity clustering."
        }

    # Deterministic pairwise similarity and verbatim phrasing check
    duplicate_pairs = []
    n = len(review_candidates)
    for i in range(n):
        for j in range(i + 1, n):
            w1 = review_candidates[i]["words"]
            w2 = review_candidates[j]["words"]
            union_len = len(w1 | w2)
            if union_len == 0:
                continue
            jaccard = len(w1 & w2) / union_len

            # Check for shared long phrase (5+ consecutive words)
            t1 = review_candidates[i]["text_clean"]
            t2 = review_candidates[j]["text_clean"]
            has_shared_phrase = False
            words1 = t1.split()
            if len(words1) >= 5:
                for k in range(len(words1) - 4):
                    phrase = " ".join(words1[k:k+5])
                    if phrase in t2:
                        has_shared_phrase = True
                        break

            if jaccard >= 0.65 or has_shared_phrase:
                overlap_score = round(max(jaccard, 0.80 if has_shared_phrase else jaccard), 2)
                duplicate_pairs.append((i, j, overlap_score))

    if duplicate_pairs:
        near_duplicate_clusters = len(duplicate_pairs)
        signals_found = []
        for p in duplicate_pairs[:5]:
            c1 = review_candidates[p[0]]
            c2 = review_candidates[p[1]]
            signals_found.append(
                f"Match between {c1['evidence_id']} and {c2['evidence_id']} ({int(p[2]*100)}% overlap): \"{c1['text'][:65]}...\""
            )
        return {
            "status": "REPETITION_REQUIRES_REVIEW",
            "review_manipulation_detected": False,
            "repetition_observed": True,
            "assessment_is_heuristic": True,
            "assessment": f"Review-pattern screening completed. {signals_analyzed} review signals analyzed; {near_duplicate_clusters} near-duplicate text pairs identified.",
            "confidence": 0.35,
            "signals_analyzed": signals_analyzed,
            "near_duplicate_clusters": near_duplicate_clusters,
            "signals_found": signals_found,
            "cluster_notes": f"Identified {near_duplicate_clusters} near-duplicate phrasing pairs exceeding lexical similarity threshold."
        }
    else:
        return {
            "status": "SCREENED_NO_REPETITION_FOUND",
            "review_manipulation_detected": False,
            "assessment": f"Review-pattern screening completed. {signals_analyzed} review signals analyzed. Pairwise text comparison found no duplicate or coordinated phrasing patterns (threshold 0.65).",
            "confidence": None,
            "signals_analyzed": signals_analyzed,
            "near_duplicate_clusters": 0,
            "signals_found": [],
            "cluster_notes": f"{signals_analyzed} review signals evaluated for lexical overlap. All signals exhibit natural lexical variance."
        }


def synthesize_brand_threats(brand_info, evidence_list):
    """Deterministic assessment. Generative threat/claim adjudication is disabled."""
    if not evidence_list:
        return {"threats": [], "claims": [], "narratives": [], "dossiers": [],
                "counterfeits": [], "impersonations": [], "review_intel": screen_review_patterns([]),
                "recommendations": ["Insufficient evidence; inspect source access and acquisition failures."],
                "ai_enrichment": "NOT_REQUIRED_EMPTY_DATA"}
    return heuristic_threat_synthesis(brand_info, evidence_list)


def heuristic_threat_synthesis(
    brand_info: Dict[str, Any],
    evidence_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Deterministic, rule-based forensic analysis over retrieved evidence when AI is offline.
    Strictly operates on retrieved items without inventing fake platforms or reviews.
    """
    brand_name = brand_info.get("brand", "Unknown")
    target_name = brand_info.get("resolved_entity", brand_name)

    # Real execution stage: invoke BrandShieldExtractionEngine
    # Generic company/about text must not create complaint/attacker signals.
    # Select an actual subject/objective passage before either heuristic engine.
    from backend.services.research.content_roles import NON_EVENT_ROLES, document_role, matches_objective, paragraph_role
    from backend.services.research.research_models import EvidenceItem
    relevant = []
    for record in evidence_list:
        from backend.services.research.passage_records import captured_passages, classify_passage
        from backend.services.research.source_quality import canonical_hostname, hostname_matches, ENCYCLOPEDIA_DOMAINS
        passages = captured_passages(record, "brand", target_name)
        record["passages"] = passages
        record["intelligence_class"] = classify_passage(record.get("content") or record.get("snippet") or "", domain="brand")
        if any(hostname_matches(canonical_hostname(record.get("url", "")), host) for host in ENCYCLOPEDIA_DOMAINS):
            record["intelligence_class"] = "BACKGROUND_REFERENCE"
            continue
        excluded_roles = NON_EVENT_ROLES | {"SAFETY_WARNING", "PRODUCT_CATALOG", "ADVERTISEMENT", "DISPUTED_CLAIM"}
        record_context = (str(record.get("title", "")) + " " + str(record.get("content", "")) + " " + str(record.get("url", ""))).casefold()
        has_target = bool(target_name) and target_name.casefold() in record_context
        usable = [p for p in passages if p["content_role"] not in excluded_roles
                  and (p["relevance"] == "DIRECTLY_RELEVANT" or
                       (has_target and matches_objective(str(record.get("title", "")) + " " + p["text"], "brand")))]
        if passages and not usable:
            continue
        # Classify only complete selected paragraphs. Keep the original captured
        # record/text/offsets intact for inspection, including rejected warnings.
        selected = "\n\n".join(p["text"] for p in usable)
        candidate = {**record, "content": selected, "snippet": selected} if selected else record
        item = EvidenceItem(id=record.get("evidence_id", ""), canonical_url=record.get("url", ""),
            content=candidate.get("content") or candidate.get("snippet") or "",
            content_depth=record.get("content_depth") or "PARTIAL_CONTENT",
            title=record.get("title", ""), metadata=dict(record.get("raw_metadata") or {}))
        if document_role(item) == "LANDING_PAGE" and not re.search(
            r"\b(?:counterfeit|replica|knockoff)\b.{0,100}\b(?:for sale|buy|add to cart|order)|\bI ordered\b|\b(?:verify|enter|submit)\b.{0,60}\b(?:credentials|password)\b",
            item.content, re.I):
            # Repair/recall menu entries are not observed defective products.
            # Keep explicit suspicious offers and customer reports investigable.
            continue
        # The legacy threat taxonomy accepts short, title-led leads. Retain
        # that interface without treating it as a grounded/shared finding.
        context = item.title + " " + item.content
        if (document_role(item) not in NON_EVENT_ROLES - {"LANDING_PAGE"} and paragraph_role(item.content) not in NON_EVENT_ROLES
                and matches_objective(context, "brand")):
            relevant.append(candidate)
    evidence_list = relevant

    from backend.services.agent_reach.channels import EvidenceFragment
    from backend.agents.brandshield.extraction import brandshield_extractor

    frags = [
        EvidenceFragment(
            platform=ev.get("platform", "web"),
            title=ev.get("title", ""),
            content=ev.get("snippet", "") or ev.get("content", ""),
            snippet=ev.get("snippet", ""),
            url=ev.get("url", ""),
            author=ev.get("author", ""),
            published=ev.get("published", ""),
            evidence_id=ev.get("evidence_id", ""),
        )
        for ev in evidence_list
    ]
    extracted_intel = brandshield_extractor.extract_brand_intelligence(
        brand_name=target_name,
        product_name=brand_info.get("product", ""),
        fragments=frags,
    )

    threats = [t.to_dict() if hasattr(t, "to_dict") else t for t in extracted_intel.threats]
    claims = [c.to_dict() if hasattr(c, "to_dict") else c for c in extracted_intel.claims]
    narratives = []
    counterfeits = [c.to_dict() if hasattr(c, "to_dict") else c for c in extracted_intel.counterfeits]
    impersonations = [i.to_dict() if hasattr(i, "to_dict") else i for i in extracted_intel.impersonations]

    counterfeit_kw = ["counterfeit", "fake", "replica", "clone", "knockoff", "first copy", "unauthorized seller"]
    scam_kw = ["scam", "phishing", "fraud", "stolen", "hack", "giveaway", "free gift"]
    impersonation_kw = ["impersonat", "fake account", "fake handle", "spoofed", "fake support"]
    safety_kw = ["safety hazard", "product recall", "battery fire", "explosion hazard", "toxic defect", "burn injury"]
    legal_patterns = [
        r"\blawsuit\b", r"\bsubpoena\b", r"\bantitrust\b", r"\bpatent infringement\b",
        r"\bregulatory\s+(?:probe|inquiry|investigation|action|fine|penalty)\b",
        r"\b(?:sec|ftc|doj)\s+(?:investigation|probe|lawsuit|inquiry|subpoena|enforcement|fine)\b",
        r"\bclass action\b", r"\bcourt\s+order\b", r"\bfined\s+by\s+regulator\b"
    ]
    # Navigation labels such as billing/refunds/issues are not customer grievances.
    complaint_kw = ["customer complaint", "delivery delayed", "broken", "worst", "bad service", "poor service", "never received", "my refund"]

    for idx, ev in enumerate(evidence_list):
        is_util, _ = is_utility_or_auth_url(ev.get("url", ""))
        from backend.services.research.source_quality import canonical_hostname, hostname_matches
        is_official = any(hostname_matches(canonical_hostname(ev.get("url", "")), corp) for corp in ("microsoft.com", "apple.com", "tesla.com", "nvidia.com", "tatamotors.com", "nike.com"))

        full_text = f"{ev['title']} {ev.get('snippet', '')} {ev.get('content', '')}".lower()
        # A warning/advisory is a report ABOUT abuse, not an observed attacker.
        # Do not grant ownership or suppress separate listings on the same domain.
        safety_notice = bool(re.search(
            r"\b(?:beware of|avoid|warning about|reporting|protect yourself from)\b.{0,60}\b(?:scams?|fraud|phishing)\b"
            r"|\bwe (?:do not|never) (?:charge|accept|ask|request)\b", full_text))

        if not is_official and contains_word_or_phrase(full_text, counterfeit_kw):
            threats.append({
                "threat_id": f"thr_{len(threats)+1:03d}",
                "type": "COUNTERFEIT",
                "title": f"Potential counterfeit / unauthorized listing: {ev['title'][:55]}",
                "summary": f"Signal identified on {ev['platform']} indicating potential counterfeit or unauthorized replica distribution.",
                "severity": "high",
                "confidence": 0.82,
                "status": "investigating",
                "platforms": [ev["platform"]],
                "evidence_ids": [ev["evidence_id"]],
                "origin_evidence_id": ev["evidence_id"]
            })
            counterfeits.append({
                "product": target_name,
                "marketplace_or_domain": ev.get("platform", "Web"),
                "seller": ev.get("author") or "Unspecified Seller",
                "risk_level": "high",
                "evidence_ids": [ev["evidence_id"]]
            })

        elif not is_official and not safety_notice and any(k in full_text for k in scam_kw):
            threats.append({
                "threat_id": f"thr_{len(threats)+1:03d}",
                "type": "PHISHING_SCAM",
                "title": f"Suspected scam / phishing vector: {ev['title'][:55]}",
                "summary": f"Discussion or listing on {ev['platform']} referencing fraudulent promotions or scams.",
                "severity": "high",
                "confidence": 0.78,
                "confidence_is_heuristic": True,
                "status": "investigating",
                "platforms": [ev["platform"]],
                "evidence_ids": [ev["evidence_id"]],
                "origin_evidence_id": ev["evidence_id"]
            })

        elif not is_official and any(k in full_text for k in impersonation_kw):
            threats.append({
                "threat_id": f"thr_{len(threats)+1:03d}",
                "type": "BRAND_IMPERSONATION",
                "title": f"Suspected brand impersonator: {ev['title'][:55]}",
                "summary": f"Impersonation report or lookalike account observed on {ev['platform']}.",
                "severity": "medium",
                "confidence": 0.75,
                "status": "investigating",
                "platforms": [ev["platform"]],
                "evidence_ids": [ev["evidence_id"]],
                "origin_evidence_id": ev["evidence_id"]
            })
            impersonations.append({
                "handle_or_domain": ev.get("author") or ev.get("title", "")[:30],
                "platform": ev.get("platform", "Web"),
                "risk_level": "medium",
                "evidence_ids": [ev["evidence_id"]]
            })

        elif not is_util and any(k in full_text for k in safety_kw):
            threats.append({
                "threat_id": f"thr_{len(threats)+1:03d}",
                "type": "PRODUCT_SAFETY",
                "title": f"Product safety or recall discussion: {ev['title'][:55]}",
                "summary": f"Safety concern or recall alert circulating across {ev['platform']}.",
                "severity": "high",
                "confidence": 0.85,
                "status": "unverified",
                "platforms": [ev["platform"]],
                "evidence_ids": [ev["evidence_id"]],
                "origin_evidence_id": ev["evidence_id"]
            })
            claims.append({
                "claim_id": f"clm_{len(claims)+1:03d}",
                "claim_text": ev["title"][:90],
                "status": "unverified",
                "category": "product_defect",
                "evidence_ids": [ev["evidence_id"]]
            })

        elif any(re.search(pat, full_text) for pat in legal_patterns):
            is_reg_authority = (
                ev.get("source_tier") == "TIER_1_OFFICIAL_FILING" or
                any(hostname_matches(canonical_hostname(ev.get("url", "")), reg) for reg in ("sec.gov", "ftc.gov", "justice.gov", "cpsc.gov"))
            )
            threats.append({
                "threat_id": f"thr_{len(threats)+1:03d}",
                "type": "REGULATORY_LEGAL",
                "title": f"Regulatory or legal inquiry: {ev['title'][:55]}",
                "summary": f"Legal proceedings or regulatory inquiries reported by {ev['platform']}.",
                "severity": "medium",
                "confidence": 0.90 if is_reg_authority else 0.70,
                "status": "unverified",
                "platforms": [ev["platform"]],
                "evidence_ids": [ev["evidence_id"]],
                "origin_evidence_id": ev["evidence_id"]
            })

        elif not is_official and any(k in full_text for k in complaint_kw):
            # Classify legitimate customer complaints distinctly from malicious attacks
            threats.append({
                "threat_id": f"thr_{len(threats)+1:03d}",
                "type": "CUSTOMER_COMPLAINT",
                "title": f"Consumer service grievance: {ev['title'][:55]}",
                "summary": f"User complaint regarding service or product performance on {ev['platform']}.",
                "severity": "low",
                "confidence": 0.35,
                "status": "unverified",
                "platforms": [ev["platform"]],
                "evidence_ids": [ev["evidence_id"]],
                "origin_evidence_id": ev["evidence_id"]
            })

    narratives.append({
        "theme": f"Sampled references mentioning {target_name}",
        "description": "These retrieved records do not by themselves establish consumer sentiment, a campaign or the brand's overall risk.",
        "threat_level": "unassessed",
        "evidence_ids": [e["evidence_id"] for e in evidence_list[:5]]
    })

    review_intel = screen_review_patterns(evidence_list)
    if review_intel.get("review_manipulation_detected") and not any(t.get("type") == "FAKE_REVIEW" for t in threats):
        threats.append({
            "threat_id": f"thr_{len(threats)+1:03d}",
            "type": "FAKE_REVIEW",
            "title": f"Coordinated review pattern: {review_intel.get('near_duplicate_clusters', 1)} clusters detected",
            "summary": review_intel.get("assessment", "Near-duplicate review signals detected."),
            "severity": "medium",
            "confidence": 0.85,
            "status": "investigating",
            "platforms": ["Web"],
            "evidence_ids": [e["evidence_id"] for e in evidence_list[:2]],
            "origin_evidence_id": evidence_list[0]["evidence_id"] if evidence_list else ""
        })

    for threat in threats:
        threat["epistemic_state"] = "UNVERIFIED"
        threat["confidence_is_heuristic"] = True
        threat["supporting_passages"] = [p for ev in evidence_list
            if ev.get("evidence_id") in threat.get("evidence_ids", []) for p in ev.get("passages", [])
            if p["relevance"] == "DIRECTLY_RELEVANT"][:4]
        threat["evidence_class"] = "OBSERVED_COMPLAINT" if threat.get("type") == "CUSTOMER_COMPLAINT" else "UNVERIFIED_ALLEGATION"
        matched = [ev for ev in evidence_list if ev.get("evidence_id") in threat.get("evidence_ids", [])]
        if any(p["content_role"] == "REPORTED_ENFORCEMENT" for ev in matched for p in ev.get("passages", [])):
            threat["source_relation"] = "REPORTS_ENFORCEMENT"
            threat["actor_url"] = None
            threat["evidence_class"] = "REPORTED_ENFORCEMENT_UNVERIFIED"
            threat["title"] = "Source-reported enforcement involving " + target_name
            threat["summary"] = "The source reports enforcement or legal action. Its citation URL identifies the reporting source, not an observed seller, impersonator or phishing endpoint."
    dossiers = build_investigation_dossiers(brand_info, threats, claims, evidence_list)

    return {
        "threats": threats[:6],
        "claims": claims[:6],
        "narratives": narratives,
        "dossiers": dossiers,
        "counterfeits": counterfeits[:4],
        "impersonations": impersonations[:4],
        "review_intel": review_intel,
        "recommendations": [
            f"Verify seller credentials on reported {target_name} listings.",
            "Review primary corporate communication channels for official statements."
        ],
        "ai_enrichment": "OFFLINE_HEURISTIC"
    }


def detect_executive_impersonation(
    brand_name: str,
    executive_name: str,
    candidate_profiles: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 8C BrandShield Specialization:
    Scans and classifies candidate social profiles claiming association with brand executives.
    Detects lookalike handles, unauthorized giveaways/solicitations, and unverified impostors.
    """
    if not candidate_profiles:
        return {
            "status": "NO_PROFILES_EXAMINED",
            "impersonation_threats": [],
            "max_risk_level": "NOMINAL",
            "summary": "Zero candidate profiles provided for impersonation analysis."
        }

    threats = []
    max_risk = "NOMINAL"
    import re

    clean_exec = re.sub(r'[^a-z0-9]', '', executive_name.lower())
    clean_brand = re.sub(r'[^a-z0-9]', '', brand_name.lower())

    for idx, prof in enumerate(candidate_profiles):
        handle = prof.get("handle", prof.get("username", "")).lstrip("@").strip()
        display_name = prof.get("name", prof.get("display_name", "")).strip()
        bio = prof.get("bio", prof.get("description", "")).lower()
        verified = prof.get("verified", False)
        platform = prof.get("platform", "Social")
        profile_url = prof.get("url", "")

        clean_handle = re.sub(r'[^a-z0-9]', '', handle.lower())

        is_exec_name_claimed = (
            executive_name.lower() in display_name.lower() or
            clean_exec in clean_handle
        )

        indicators = []
        risk_level = "NOMINAL"
        classification = "UNRELATED"

        if is_exec_name_claimed and not verified:
            # Check for lookalike handle anomalies (e.g. trailing digits, 'official', 'real', 'ceo')
            has_lookalike_affix = any(aff in handle.lower() for aff in ["official", "real", "ceo", "direct", "_", "1", "2"])
            has_solicitation = any(w in bio for w in ["dm for", "giveaway", "crypto", "invest", "telegram", "whatsapp", "funds", "airdrop"])

            if has_solicitation:
                risk_level = "CRITICAL_FRAUDULENT_IMPERSONATION"
                classification = "SUSPECTED_IMPERSONATION_REQUIRES_REVIEW"
                indicators.append("Unverified lookalike profile soliciting funds, DMs, or cryptocurrency.")
            elif has_lookalike_affix:
                risk_level = "HIGH_SUSPICIOUS_LOOKALIKE"
                classification = "SUSPICIOUS_LOOKALIKE"
                indicators.append("Unverified handle mimicking executive name with synthetic affixes/underscores.")
            else:
                risk_level = "MEDIUM_UNVERIFIED_MATCH"
                classification = "UNVERIFIED_IDENTITY"
                indicators.append("Display name matches executive but lacks platform verification badge.")

        elif verified and is_exec_name_claimed:
            risk_level = "NOMINAL"
            classification = "BADGE_REPORTED_IDENTITY_UNVERIFIED"
            indicators.append("Input reports a badge; a badge alone does not authenticate executive identity.")

        if risk_level != "NOMINAL":
            if max_risk in ("NOMINAL", "MEDIUM_UNVERIFIED_MATCH") and risk_level.startswith("HIGH"):
                max_risk = "HIGH"
            elif risk_level.startswith("CRITICAL"):
                max_risk = "CRITICAL"

            threats.append({
                "impersonation_id": f"imp_{idx+1:02d}",
                "platform": platform,
                "handle": f"@{handle}",
                "display_name": display_name,
                "claimed_executive": executive_name,
                "brand": brand_name,
                "classification": classification,
                "risk_level": risk_level,
                "profile_url": profile_url,
                "indicators": indicators,
                "recommended_action": (
                    "Verify account ownership and solicitation context before requesting platform review."
                    if risk_level.startswith("CRITICAL")
                    else "Monitor handle and issue public brand verification advisory."
                )
            })

    return {
        "status": "ANALYSIS_COMPLETE",
        "brand": brand_name,
        "executive": executive_name,
        "profiles_analyzed": len(candidate_profiles),
        "assessment_is_heuristic": True,
        "impersonation_threats": threats,
        "max_risk_level": max_risk,
        "summary": f"Analyzed {len(candidate_profiles)} profiles for {executive_name}. Detected {len(threats)} potential impersonation threats."
    }


def classify_smear_vs_organic_criticism(
    reviews_or_posts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 8C BrandShield Specialization:
    Differentiates authentic consumer criticism/bad reviews from coordinated brand smear campaigns.
    Strictly enforces: negative reviews are NOT automatically misinformation.
    """
    if len(reviews_or_posts) < 2:
        return {
            "classification": "INSUFFICIENT_SIGNALS",
            "confidence": 0.0,
            "smear_campaign_detected": False,
            "evidence_quality": "INSUFFICIENT",
            "reasons": ["At least 2 reviews or posts required for comparative pattern classification."]
        }

    import re
    from backend.agents.trending.temporal import parse_timestamp_epoch

    texts = []
    for r in reviews_or_posts:
        content = f"{r.get('title', '')} {r.get('snippet', '')} {r.get('content', '')}".strip()
        words = set(re.findall(r'[a-z]{3,}', content.lower()))
        texts.append({
            "record": r,
            "content": content,
            "words": words,
            "published": r.get("published_at", r.get("published", ""))
        })

    # 1. Pairwise lexical Jaccard overlap
    duplicate_pairs = 0
    n = len(texts)
    for i in range(n):
        for j in range(i + 1, n):
            w1 = texts[i]["words"]
            w2 = texts[j]["words"]
            if w1 and w2:
                jaccard = len(w1 & w2) / len(w1 | w2)
                if jaccard >= 0.65:
                    duplicate_pairs += 1

    # 2. Time burst check (<1 hour between multiple negative posts)
    epochs = [parse_timestamp_epoch(t["published"]) for t in texts]
    valid_epochs = sorted([ep for ep in epochs if ep > 0])
    burst_detected = False
    if len(valid_epochs) >= 2:
        span_sec = valid_epochs[-1] - valid_epochs[0]
        if span_sec < 3600:  # <1 hour
            burst_detected = True

    # 3. Check for specific product detail words vs purely generic attacks
    product_detail_terms = {"delivered", "size", "fit", "broke", "customer", "support", "refund", "receipt", "shipping", "quality", "material", "smell", "taste"}
    has_specific_product_feedback = any(len(t["words"] & product_detail_terms) >= 2 for t in texts)

    is_smear = duplicate_pairs >= 2 or (duplicate_pairs >= 1 and not has_specific_product_feedback)

    if is_smear:
        classification = "REPETITION_REQUIRES_REVIEW"
        confidence = 0.35
        smear_flag = False
        reason = (
            f"Observed similar wording across {duplicate_pairs} pairs; temporal burst={burst_detected}. "
            "Repetition can come from quotations, syndication or shared experiences and does not establish malicious coordination."
        )
    elif has_specific_product_feedback:
        classification = "PRODUCT_FEEDBACK_IN_SAMPLE"
        confidence = 0.35
        smear_flag = False
        reason = (
            "Records contain product or transaction language. Author authenticity, independence and motive are unverified."
        )
    else:
        classification = "MIXED_DISCOURSE"
        confidence = 0.60
        smear_flag = False
        reason = "Discourse contains negative sentiment without conclusive markers of either coordinated automation or verified consumer transactions."

    return {
        "classification": classification,
        "confidence": confidence,
        "smear_campaign_detected": smear_flag,
        "duplicate_phrasing_pairs": duplicate_pairs,
        "temporal_burst_detected": burst_detected,
        "organic_detail_present": has_specific_product_feedback,
        "reasoning": reason,
        "signals_analyzed": len(reviews_or_posts)
    }


def detect_counterfeit_domains(
    brand_domain: str,
    candidate_domains: List[str]
) -> List[Dict[str, Any]]:
    """
    Stage 8C BrandShield Specialization:
    Detects typosquatting, lookalike domains, brand name hijacking, and phishing endpoints.
    """
    import difflib
    findings = []
    suspicious_tlds = {".top", ".xyz", ".shop", ".cfd", ".vip", ".cc", ".icu", ".work", ".click"}
    brand_core = brand_domain.split(".")[0].lower()

    for cand in candidate_domains:
        cand_clean = cand.lower().replace("https://", "").replace("http://", "").split("/")[0].strip()
        if not cand_clean or cand_clean == brand_domain.lower():
            continue

        indicators = []
        cand_core = cand_clean.split(".")[0]
        cand_tld = "." + cand_clean.split(".")[-1] if "." in cand_clean else ""

        is_typo = False
        parts = [cand_core] + [p for p in cand_core.split("-") if p] + [p for p in cand_core.split("_") if p]
        for part in parts:
            ratio = difflib.SequenceMatcher(None, brand_core, part).ratio()
            if 0.70 <= ratio < 1.0 and abs(len(part) - len(brand_core)) <= 2:
                is_typo = True
                indicators.append(f"Typosquatting permutation: {part} vs {brand_core} (similarity {int(ratio*100)}%).")
                break

        if brand_core in cand_clean and cand_clean != brand_domain.lower():
            indicators.append(f"Brand name injection into third-party host: '{brand_core}' in '{cand_clean}'.")

        if cand_tld in suspicious_tlds:
            indicators.append(f"High-abuse top-level domain: {cand_tld}.")

        if indicators:
            findings.append({
                "candidate_domain": cand_clean,
                "brand_domain": brand_domain,
                "threat_type": "TYPOSQUAT_PHISHING" if is_typo else "BRAND_HIJACKING",
                "risk_score": 0.90 if (is_typo and cand_tld in suspicious_tlds) else 0.75,
                "indicators": indicators,
                "epistemic_state": "UNVERIFIED",
                "confidence_is_heuristic": True,
                "ownership_verified": False,
                "recommended_action": "Review ownership, affiliation and observed page behavior before considering an abuse report. Similar spelling alone does not establish phishing."
            })

    return findings

