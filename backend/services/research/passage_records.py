"""Deterministic captured-passage observations, not inferred events or truth.

Offsets address the exact retained content. Complete paragraph context (including
negation/attribution) survives; long paragraphs are not sliced into assertions.
"""
import hashlib
import re
from backend.services.research.content_roles import paragraph_role, matches_objective, document_role, NON_EVENT_ROLES
from backend.schemas.evidence_inspection import METADATA_DEPTHS
from backend.infrastructure.acquisition.adapters.web.page_extraction import recovered_span_allowed


def public_statement_attribution(record, paragraph, target):
    """Observed speaker/author linkage only, never identity authentication.

    A section label is valid only until the next observed speaker label. This
    prevents attributing Ryan Roslansky's message to Satya on a joint statement.
    """
    get = record.get if isinstance(record, dict) else lambda key, default=None: getattr(record, key, default)
    meta = get("metadata", {}) or get("raw_metadata", {}) or {}
    if not target:
        return None
    page = meta.get("page_metadata") or {}
    if isinstance(page, dict) and "article_body_recovery" in page:
        # Recovered article scope is narrower than the retained capture. A
        # sidebar quotation cannot regain speaker attribution downstream.
        body = get("content", "") or ""
        offset = body.find(paragraph)
        if not recovered_span_allowed(body, page, offset, offset + len(paragraph)):
            return None
    # A denial or a report about a fabricated quotation remains inspectable as
    # disputed-claim context, never direct attribution to the named speaker.
    denial = re.search(r"\b(?:fabricated|misattributed|debunked|falsely attributed|false quote|fake quote|false claim)\b|\b(?:did not say|never said|never endorsed)\b", paragraph, re.I)
    if denial:
        return None
    statement_scope = ((get("query_class") or meta.get("query_class")) in {"public_statement_discovery", "explicit_url"}
                       or meta.get("acquisition_objective") == "PUBLIC_STATEMENT")
    if not statement_scope:
        # A real reported quotation can be discovered incidentally by a threat
        # query. Planner class is not evidence about what the captured article
        # actually says. This exception requires native article acquisition and
        # explicit full-name speaker linkage; metadata/snippets/profile bios,
        # surname guesses and author shortcuts do not qualify here.
        page = meta.get("page_metadata") or {}
        quality = page.get("body_quality") or {}
        kind = page.get("body_kind") or (quality.get("body_kind") if isinstance(quality, dict) else None)
        captured = meta.get("read_success") is True or bool(get("acquired_id"))
        if not captured or kind != "ARTICLE_BODY" or get("content_depth") in METADATA_DEPTHS:
            return None
        body = get("content", "") or ""
        if paragraph not in body:
            return None
        quoted = re.search(r'"[^"\n]{8,}"|\u201c[^\u201d\n]{8,}\u201d', paragraph)
        escaped = re.escape(target)
        speaker = re.search(r"\b" + escaped + r"(?:\s*,[^,.!?]{0,45},)?\s+(?:said|says|wrote|writes|told)\b|\b(?:said|says|wrote|writes)\s+" + escaped + r"\b", paragraph, re.I)
        return "REPORTED_QUOTATION" if quoted and speaker else None
    if (get("source_name") or get("author") or "").casefold().strip() == target.casefold().strip():
        return "OBSERVED_FEED_AUTHOR"
    body = get("content", "") or ""
    offset = body.find(paragraph)
    if offset < 0:
        return None
    labels = list(re.finditer(r"(?m)^([A-Z][A-Z .'-]{4,70}) MESSAGE\s*$", body[:offset]))
    if labels:
        normalize = lambda text: re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
        return "OBSERVED_SPEAKER_SECTION" if normalize(labels[-1].group(1)) == normalize(target) else None
    escaped = re.escape(target)
    if re.search(r"\b" + escaped + r"\s*:", paragraph, re.I):
        return "OBSERVED_SPEAKER_LABEL"
    if re.search(r"\b(?:said|says|wrote|writes)\s+" + escaped + r"\b|\b" + escaped + r"(?:\s*,[^,.!?]{0,45},)?\s+(?:said|says|wrote|writes|told)\b", paragraph, re.I) and re.search(r'["“”]', paragraph):
        return "REPORTED_QUOTATION"
    # Releases often introduce a full name and then use a surname. Only use
    # that observed alias when this capture contains the full target and no
    # competing capitalized full name with that surname. This is attribution,
    # not an authenticated identity or a claim that the quotation is true.
    names = target.split()
    if len(names) >= 2 and len(names[-1]) >= 3 and re.search(r"\b" + escaped + r"\b", body, re.I):
        surname = re.escape(names[-1])
        observed_names = re.findall(r"\b([A-Z][a-z]+(?:[- ][A-Z][a-z]+){0,2})\s+(?i:" + surname + r")\b", body)
        unambiguous = observed_names and all(name.casefold() == " ".join(names[:-1]).casefold() for name in observed_names)
        if unambiguous and re.search(r"\b(?:said|says|wrote|writes)\s+" + surname + r"\b", paragraph, re.I) and re.search(r'["“”]', paragraph):
            return "REPORTED_QUOTATION_SURNAME_IN_CAPTURE"
    return None


def classify_passage(text, *, domain=""):
    role = paragraph_role(text)
    if role != "SUBSTANTIVE_CANDIDATE":
        return role
    if re.search(r"\b(?:false|fabricated|misattributed|debunked) (?:claim|quote|allegation)|\b(?:did not|never) (?:say|endorse)", text, re.I):
        return "DISPUTED_CLAIM"
    if re.search(r"\b(?:beware|warns|warning|we never|we do not|protect yourself|avoid scams)\b", text, re.I) and re.search(r"scam|fraud|phishing|fake", text, re.I):
        return "SAFETY_WARNING"
    if re.search(r"\b(?:add to cart|shop now|shop all|free shipping|size guide)\b", text, re.I) and not re.search(r"\b(?:counterfeit|replica|knockoff|unauthorized seller)\b", text, re.I):
        return "PRODUCT_CATALOG"
    if re.search(r"\b(?:sponsored content|advertisement|paid promotion)\b", text, re.I):
        return "ADVERTISEMENT"
    if domain == "brand" and re.search(r"\b(?:I ordered|my order|never received|my refund|delivery delayed|customer complaint)\b", text, re.I):
        return "CUSTOMER_COMPLAINT"
    if domain == "brand" and re.search(r"counterfeit|phishing|impersonat|scam|fraud", text, re.I) and re.search(r"\b(?:seized|arrested|charged|convicted|court|police|customs|CBP)\b", text, re.I):
        return "REPORTED_ENFORCEMENT"
    if domain in {"brand", "personal"} and matches_objective(text, domain):
        return "UNVERIFIED_ALLEGATION" if re.search(r"scam|counterfeit|impersonat|deepfake|fake |phishing|fraud", text, re.I) else "PUBLIC_STATEMENT"
    if domain == "financial" and re.search(r"revenue|profit|earnings|cash flow", text, re.I):
        return "FINANCIAL_STATEMENT"
    return "ARTICLE_CONTENT"


def quotation_span(paragraph, target, paragraph_offset):
    """An exact explicit-speaker quote span, not the whole surrounding paragraph.

    Related-story links can contain another person's quotation in the same
    paragraph. Preserve that original context, but never label all of it as the
    monitored subject's own words.
    """
    name = re.escape(target)
    patterns = [r"\b" + name + r"(?:\s*,[^,.!?]{0,45},)?\s+(?:said|says|wrote|writes|told)\b\s*[:,-]?\s*[\"“](?P<quote>[^\"”\n]{8,})[\"”]",
                r"[\"“](?P<quote>[^\"”\n]{8,})[\"”][,\s]*(?:said|says|wrote|writes)\s+" + name + r"\b"]
    for pattern in patterns:
        match = re.search(pattern, paragraph, re.I)
        if match:
            return {"text": match.group("quote"), "start": paragraph_offset + match.start("quote"),
                    "end": paragraph_offset + match.end("quote"), "speaker": target,
                    "attribution_status": "REPORTED_QUOTATION_UNVERIFIED", "identity_authenticated": False}
    return None


def without_related_link_tail(text):
    """Drop an explicitly labeled terminal related-story promo, not context.

    The returned prefix still maps exactly to the original retained body. Raw
    article bytes/hash remain unchanged; arbitrary parenthetical qualifications,
    negations, citations or commentary are never removed by this narrow rule.
    """
    match = re.search(r"\s+\((?:also read|read also):[^)]{1,1500}\)\s*$", text, re.I)
    return text[:match.start()].rstrip() if match else text


def captured_passages(record, domain="", target=""):
    get = record.get if isinstance(record, dict) else lambda key, default=None: getattr(record, key, default)
    body = get("content", "") or ""
    identity = get("id") or get("evidence_id")
    meta = get("metadata", {}) or get("raw_metadata", {}) or {}
    depth = get("content_depth", "") or meta.get("content_depth", "")
    if not isinstance(body, str) or not identity:
        return []
    metadata_only = depth in METADATA_DEPTHS or document_role(record) in NON_EVENT_ROLES
    page = meta.get("page_metadata") or {}
    result = []
    # Paragraph boundaries only: a following negation/qualification is not lost.
    for match in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", body):
        text = match.group().rstrip()
        # The source buffer retains every byte, but only structurally observed
        # article spans may become specialist passages. Validate the original
        # complete paragraph before any display-only related-link trimming.
        if not recovered_span_allowed(body, page, match.start(), match.start() + len(text)):
            continue
        if domain == "personal":
            text = without_related_link_tail(text)
        if len(text) < 25:
            continue
        role = classify_passage(text, domain=domain)
        attribution = public_statement_attribution(record, text, target) if domain == "personal" else None
        attributed = bool(attribution)
        if attributed and role == "ARTICLE_CONTENT":
            role = "PUBLIC_STATEMENT"
        subject_tokens = list(dict.fromkeys(re.findall(r"\w{2,}" if domain == "personal" else r"\w{3,}", target.casefold())))
        subject = attributed or not target or all(re.search(r"\b" + re.escape(token) + r"\b", text.casefold()) for token in subject_tokens[:3])
        relevance = ("DISCOVERY_ONLY" if metadata_only else "BACKGROUND" if role in NON_EVENT_ROLES | {"PRODUCT_CATALOG", "ADVERTISEMENT"}
                     else "DIRECTLY_RELEVANT" if subject and (attributed or matches_objective(text, domain)) else "CONTEXTUAL")
        # Oversized paragraphs remain raw/inspectable, not partially adjudicated.
        if len(text) > 6000:
            continue
        start, end = match.start(), match.start() + len(text)
        digest = hashlib.sha256((str(identity)+":"+str(start)+":"+text).encode()).hexdigest()[:16]
        result.append({"passage_id": "ps_"+digest, "evidence_id": identity, "start": start, "end": end,
            "text": text, "content_role": role, "relevance": relevance,
            "attribution": attribution or "SOURCE_ASSERTION", "claim_status": "UNVERIFIED",
            "dates": re.findall(r"\b20\d\d-\d{2}-\d{2}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? 20\d\d", text),
            "negation_present": bool(re.search(r"\b(?:not|never|no|denied|denies|without)\b", text, re.I)),
            "source_url": get("canonical_url") or get("url"), "published_at": get("published_at") or None})
        if attributed:
            quote = quotation_span(text, target, start)
            if quote:
                result[-1]["quotation"] = quote
    # A navigation-heavy capture can put the actual incident after the first
    # sixteen paragraphs. Bound the display projection by relevance, not by
    # position; preserve original offsets and reading order of selected spans.
    priority = {"DIRECTLY_RELEVANT": 0, "CONTEXTUAL": 1, "DISCOVERY_ONLY": 2, "BACKGROUND": 3}
    selected = sorted(result, key=lambda p: (priority[p["relevance"]], p["start"]))[:16]
    return sorted(selected, key=lambda p: p["start"])
