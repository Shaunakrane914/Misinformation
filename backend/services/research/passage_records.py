"""Deterministic captured-passage observations, not inferred events or truth.

Offsets address the exact retained content. Complete paragraph context (including
negation/attribution) survives; long paragraphs are not sliced into assertions.
"""
import hashlib
import re
from backend.services.research.content_roles import paragraph_role, matches_objective, document_role, NON_EVENT_ROLES
from backend.schemas.evidence_inspection import METADATA_DEPTHS


def classify_passage(text, *, domain=""):
    role = paragraph_role(text)
    if role != "SUBSTANTIVE_CANDIDATE":
        return role
    if re.search(r"\b(?:beware|warns|warning|we never|we do not|protect yourself|avoid scams)\b", text, re.I) and re.search(r"scam|fraud|phishing|fake", text, re.I):
        return "SAFETY_WARNING"
    if re.search(r"\b(?:add to cart|shop now|shop all|free shipping|size guide)\b", text, re.I):
        return "PRODUCT_CATALOG"
    if re.search(r"\b(?:sponsored content|advertisement|paid promotion)\b", text, re.I):
        return "ADVERTISEMENT"
    if domain == "brand" and re.search(r"\b(?:I ordered|my order|never received|my refund|delivery delayed|customer complaint)\b", text, re.I):
        return "CUSTOMER_COMPLAINT"
    if domain in {"brand", "personal"} and matches_objective(text, domain):
        return "UNVERIFIED_ALLEGATION" if re.search(r"scam|counterfeit|impersonat|deepfake|fake |phishing|fraud", text, re.I) else "PUBLIC_STATEMENT"
    if domain == "financial" and re.search(r"revenue|profit|earnings|cash flow", text, re.I):
        return "FINANCIAL_STATEMENT"
    return "ARTICLE_CONTENT"


def captured_passages(record, domain="", target=""):
    get = record.get if isinstance(record, dict) else lambda key, default=None: getattr(record, key, default)
    body = get("content", "") or ""
    identity = get("id") or get("evidence_id")
    meta = get("metadata", {}) or {}
    depth = get("content_depth", "") or meta.get("content_depth", "")
    if not isinstance(body, str) or not identity:
        return []
    metadata_only = depth in METADATA_DEPTHS or document_role(record) in NON_EVENT_ROLES
    result = []
    # Paragraph boundaries only: a following negation/qualification is not lost.
    for match in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", body):
        text = match.group().rstrip()
        if len(text) < 25:
            continue
        role = classify_passage(text, domain=domain)
        attributed = (domain == "personal" and (get("query_class") or meta.get("query_class")) == "public_statement_discovery"
            and (get("source_name") or get("author") or "").casefold().strip() == target.casefold().strip())
        if attributed and role == "ARTICLE_CONTENT":
            role = "PUBLIC_STATEMENT"
        subject_tokens = re.findall(r"\w{3,}", target.casefold())
        subject = attributed or not target or all(token in text.casefold() for token in subject_tokens[:3])
        relevance = ("DISCOVERY_ONLY" if metadata_only else "BACKGROUND" if role in NON_EVENT_ROLES | {"PRODUCT_CATALOG", "ADVERTISEMENT"}
                     else "DIRECTLY_RELEVANT" if subject and (attributed or matches_objective(text, domain)) else "CONTEXTUAL")
        # Oversized paragraphs remain raw/inspectable, not partially adjudicated.
        if len(text) > 6000:
            continue
        start, end = match.start(), match.start() + len(text)
        digest = hashlib.sha256((str(identity)+":"+str(start)+":"+text).encode()).hexdigest()[:16]
        result.append({"passage_id": "ps_"+digest, "evidence_id": identity, "start": start, "end": end,
            "text": text, "content_role": role, "relevance": relevance,
            "attribution": "SOURCE_ASSERTION", "claim_status": "UNVERIFIED",
            "dates": re.findall(r"\b20\d\d-\d{2}-\d{2}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? 20\d\d", text),
            "negation_present": bool(re.search(r"\b(?:not|never|no|denied|denies|without)\b", text, re.I)),
            "source_url": get("canonical_url") or get("url"), "published_at": get("published_at") or None})
        if len(result) == 16:
            break
    return result
