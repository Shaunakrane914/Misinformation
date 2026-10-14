"""Conservative lexical evidence alignment; this is not semantic entailment calibration.

Related entity mentions and source authority cannot substitute for a matching
proposition. Ambiguous contexts abstain; all scores are heuristic.
"""

import re

from backend.services.research.source_quality import canonical_hostname

_STOP = set("a an the and or of to for in on at by as with from is are was were be been has have had did does do its it that this company corp corporation officially official reportedly reported reports report posts posted announces announced confirms confirmed says said rumor rumors claim claims false unfounded denies denied refuted rejected dismissed debunked".split())
_NORMAL = {
    "acquired": "acquire", "acquires": "acquire", "acquisition": "acquire",
    "buyout": "acquire", "merger": "acquire", "bought": "acquire",
    "files": "file", "filed": "file", "filing": "file",
    "profits": "profit", "earnings": "profit", "revenues": "revenue",
}
_NEGATION = re.compile(r"\b(?:not|never|no|denied|denies|refuted|rejected|debunked|hoax|false rumor)\b", re.I)
_AMBIGUOUS = re.compile(r"\b(?:if|unless|could|might|would|allegedly|according to|may)\b", re.I)


def terms(text):
    return {_NORMAL.get(t, t) for t in re.findall(r"[a-z0-9]+", text.lower())
            if t not in _STOP and t not in {"not", "never", "no"}}


def context_compatible(first, second, numeric=True):
    """Do not compare different periods, scopes, currencies or measurement bases."""
    patterns = [
        r"\b(?:19|20)\d{2}\b|\bq[1-4]\b",
        r"\b(?:ohio|florida|texas|california|china|europe|us|uk|india)\b",
    ]
    if numeric:
        patterns += [
        r"\b(?:annual|quarterly|monthly|cash|including debt|inclusive of debt|excluding debt)\b",
        r"[$€£¥₹]|\b(?:usd|eur|gbp|inr)\b",
        ]
    for pattern in patterns:
        a = set(re.findall(pattern, first.lower()))
        b = set(re.findall(pattern, second.lower()))
        if a != b and ((a or b) if numeric else (a and b)):
            return False
    return True


def relation(claim_text, entity, item):
    """Return SUPPORT, CONTRADICT or NONE only for an inspectable aligned passage."""
    if not canonical_hostname(item.canonical_url) or item.retrieval_status not in {"SUCCESS", "DEGRADED"}:
        return "NONE", ""
    if item.selection_decision == "REJECTED" or item.source_role in {"UTILITY_PORTAL", "SEARCH_INDEX"}:
        return "NONE", ""
    if item.content_depth in {"DIRECT_METADATA", "HEADLINE_ONLY", "VIDEO_METADATA", "METADATA", "SEARCH_SNIPPET"}:
        return "NONE", ""
    wanted = terms(claim_text)
    if not wanted or _AMBIGUOUS.search(claim_text):
        return "NONE", ""
    # Title is discovery context. Use actually supplied passage text for verdicts.
    text = item.relevant_excerpt or item.content or item.snippet
    if not text:
        return "NONE", ""
    entity_terms = terms(entity) if entity and entity != "General Entity" else set()
    if entity_terms and not entity_terms.issubset(terms(item.title + " " + text)):
        return "NONE", ""
    wanted -= entity_terms
    if not wanted:
        return "NONE", ""
    for passage in re.split(r"(?<=[.!?])\s+|[\r\n]+", text):
        if not context_compatible(claim_text, passage) or _AMBIGUOUS.search(passage):
            continue
        available = terms(passage)
        # Require every meaningful claim term, including entity and object.
        if not wanted.issubset(available):
            continue
        opposed = bool(_NEGATION.search(claim_text)) != bool(_NEGATION.search(passage))
        return ("CONTRADICT" if opposed else "SUPPORT"), passage[:500]
    return "NONE", ""


def publisher_key(url):
    """Conservative publisher grouping, not proof of independent reporting.

    Known compound suffixes handle common deployments; unknown/multitenant
    domains can be over-grouped, which reduces rather than inflates confirmation.
    """
    host = canonical_hostname(url)
    parts = host.split(".")
    compound = {"co.uk", "org.uk", "gov.uk", "co.in", "gov.in", "com.au", "co.jp", "com.cn"}
    count = 3 if ".".join(parts[-2:]) in compound else 2
    return ".".join(parts[-count:]) if host else ""


def evaluate_grounded_claim(claim, items):
    claim.supporting_evidence_ids = []
    claim.contradicting_evidence_ids = []
    claim.evidence_citations = []
    seen = set()
    support_origins, opposing_origins = set(), set()
    primary_support, primary_opposition = False, False
    for item in items:
        alignment, passage = relation(claim.claim_text, claim.entity, item)
        url = item.canonical_url.split("#", 1)[0]
        if alignment == "NONE" or url in seen:
            continue
        seen.add(url)
        origin = item.independence_group if item.independence_group not in {"", "independent"} else publisher_key(url)
        claim.evidence_citations.append({
            "evidence_id": item.id, "canonical_url": url, "source_name": item.source_name,
            "source_role": item.source_role, "source_tier": item.source_tier,
            "primary_source": item.primary_source, "published_at": item.published_at or "",
            "relevant_excerpt": passage, "relation": alignment,
            "alignment_method": "conservative_lexical", "is_heuristic": True,
        })
        if alignment == "SUPPORT":
            claim.supporting_evidence_ids.append(item.id)
            support_origins.add(origin)
            primary_support |= item.primary_source
        else:
            claim.contradicting_evidence_ids.append(item.id)
            opposing_origins.add(origin)
            primary_opposition |= item.primary_source
    if support_origins and opposing_origins:
        claim.verdict, claim.confidence = "MIXED", 0.5
        claim.rationale = "Aligned passages disagree; authority alone does not resolve the conflict."
    elif primary_opposition:
        claim.verdict, claim.confidence = "REFUTED", 0.85
        claim.rationale = "An inspectable primary-source passage explicitly opposes the aligned proposition; lexical assessment requires contextual review."
    elif len(support_origins) >= 2 and primary_support:
        claim.verdict, claim.confidence = "SUPPORTED", 0.85
        claim.rationale = "Matching passages from distinct grouped origins include a primary record. Grouping and confidence remain heuristic."
    elif claim.evidence_citations:
        claim.verdict, claim.confidence = "UNVERIFIED", 0.35
        claim.rationale = "Aligned sampled passages are available, but independent authoritative confirmation is insufficient."
    else:
        claim.verdict, claim.confidence = "INSUFFICIENT_EVIDENCE", 0.0
        claim.rationale = "No inspectable passage establishes the full proposition, polarity, period and scope."
    return claim
