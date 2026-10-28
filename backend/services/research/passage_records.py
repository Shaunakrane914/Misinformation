"""Deterministic captured-passage observations, not inferred events or truth.

Offsets address the exact retained content. Complete paragraph context (including
negation/attribution) survives; long paragraphs are not sliced into assertions.
"""
import hashlib
import re
from backend.services.research.content_roles import paragraph_role, matches_objective, document_role, NON_EVENT_ROLES
from backend.schemas.evidence_inspection import METADATA_DEPTHS
from backend.infrastructure.acquisition.adapters.web.page_extraction import recovered_span_allowed


def _reported_quote_has_speaker(paragraph, speaker):
    quote = r'["“][^"”\n]{8,}["”]'
    relative = r"(?:\s*,\s*(?:who|the|a|an)\s+[^,.!?\n]{1,100},)?"
    verb = r"(?:said|says|wrote|writes|told)"
    name = r"\b(?:" + speaker + r")\b"
    after_quote = quote + r"[,\s]*(?:" + name + relative + r"\s+" + verb + r"|" + verb + r"\s+" + name + r")"
    before_quote = name + relative + r"\s+" + verb + r"(?:\s+(?:in a (?:statement|release|post)|that)){0,2}\s*[:,\-]?\s*" + quote
    return bool(re.search(after_quote + "|" + before_quote, paragraph, re.I))


def _captured_surname_unambiguous(body, target):
    names = target.split()
    if len(names) < 2 or len(names[-1]) < 3 or not re.search(r"\b" + re.escape(target) + r"\b", body, re.I):
        return False
    roles = {"chief", "executive", "officer", "president", "chair", "chairman", "chairwoman", "ceo", "cfo", "cto", "coo",
             "director", "minister", "founder", "professor", "dr", "mr", "ms", "mrs"}
    prefixes = re.findall(r"\b((?:[^\W\d_]+\.?[ \t]+){1,5})(?i:" + re.escape(names[-1]) + r")\b", body)
    if not prefixes:
        return False
    expected = [part.casefold() for part in names[:-1]]
    named = 0
    for prefix in prefixes:
        given = prefix.split()
        last_lower = max((i for i, part in enumerate(given) if not part[0].isupper()), default=-1)
        given = given[last_lower + 1:]
        last_role = max((i for i, part in enumerate(given) if part.casefold().rstrip('.') in roles), default=-1)
        given = given[last_role + 1:]
        if not given:
            continue
        # Sentence-leading connective/adverb words are not competing given
        # names. Keep actual alternative names (e.g. Jessica Rivera) ambiguous.
        if len(given) == 1 and given[0].casefold() in {
                'and', 'but', 'however', 'perhaps', 'despite', 'although', 'while',
                'when', 'then', 'meanwhile', 'instead', 'nevertheless', 'yet'}:
            continue
        named += 1
        exact = [part.casefold() for part in given] == expected
        middle_initial = (len(expected) == 1 and len(given) == 2 and given[0].casefold() == expected[0]
                          and re.fullmatch(r"[A-Z]\.", given[1]))
        if not exact and not middle_initial:
            return False
    return named > 0


def _transcript_speaker_section(body, offset, target, end=None):
    """Explicit transcript boundary plus an observed speaker label, not a roster.

    The last speaker owns only the following section. This never authenticates
    identity or treats a page's title/intro as words spoken by its subject.
    """
    markers = list(re.finditer(r"(?mi)^\s*(?:full |interview )?transcript\s*:\s*$", body))
    label = re.compile(r"(?m)^([A-Z][\w.'-]+(?:[ \t]+[A-Z][\w.'-]+){1,4})[ \t]*"
                       r"(?:[–—-][ \t]*(?:CEO|CFO|CTO|SVP|VP|Director|Manager|President|Founder|Engineer|Host|Moderator|Interviewer)\b[^\n]*|:[^\n]*)$")
    labels = list(label.finditer(body))
    if not labels:
        return None
    def normalize(value):
        value = re.sub(r"^(?:dr|prof|mr|mrs|ms)\.?\s+", "", value, flags=re.I)
        return re.sub(r"[^\w]+", " ", value.casefold()).strip()
    prior_markers = [marker for marker in markers if marker.start() <= offset]
    if prior_markers:
        labels = [row for row in labels if row.start() >= prior_markers[-1].end()]
    else:
        # Some acquired transcripts use a title rather than a standalone
        # TRANSCRIPT: delimiter. Require a transcript heading AND repeated
        # explicit turns by multiple full-name speakers, not a speaker roster.
        heading = re.search(r"(?mi)^\s*[^\n]{0,100}\btranscript\b[^\n]{0,120}$", body)
        turns = [row for row in labels if heading and row.start() > heading.end()
                 and ":" in row.group(0)]
        if not heading or len(turns) < 3 or len({normalize(row.group(1)) for row in turns}) < 2:
            return None
        labels = turns
    owners = [row for row in labels if row.start() <= offset]
    # Editorial introductions and spans crossing a turn boundary cannot be
    # attributed to the following speaker. Original captured text is untouched.
    if not owners or (end is not None and any(offset < row.start() < end for row in labels)):
        return "OTHER_OBSERVED_TRANSCRIPT_SPEAKER"
    return ("OBSERVED_TRANSCRIPT_SPEAKER_SECTION" if normalize(owners[-1].group(1)) == normalize(target)
            else "OTHER_OBSERVED_TRANSCRIPT_SPEAKER")


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
        # The planner's search angle cannot erase an explicit speaker turn in
        # an actually acquired transcript. Incidental transcript discovery uses
        # the same full-name/boundary checks, never a feed-author shortcut.
        offset = body.find(paragraph)
        speaker_section = _transcript_speaker_section(body, offset, target, offset + len(paragraph))
        if speaker_section:
            return speaker_section if speaker_section == "OBSERVED_TRANSCRIPT_SPEAKER_SECTION" else None
        unambiguous = len(target.split()) < 2 or _captured_surname_unambiguous(body, target)
        if unambiguous and _reported_quote_has_speaker(paragraph, re.escape(target)):
            return "REPORTED_QUOTATION"
        names = target.split()
        if (len(names) >= 2 and len(names[-1]) >= 3 and unambiguous
                and _reported_quote_has_speaker(paragraph, re.escape(names[-1]))):
            return "REPORTED_QUOTATION_SURNAME_IN_CAPTURE"
        return None
    body = get("content", "") or ""
    offset = body.find(paragraph)
    if offset < 0:
        return None
    transcript_speaker = _transcript_speaker_section(body, offset, target, offset + len(paragraph))
    if transcript_speaker == "OTHER_OBSERVED_TRANSCRIPT_SPEAKER":
        return None
    if transcript_speaker:
        return transcript_speaker
    if (get("source_name") or get("author") or "").casefold().strip() == target.casefold().strip():
        return "OBSERVED_FEED_AUTHOR"
    labels = list(re.finditer(r"(?m)^([A-Z][A-Z .'-]{4,70}) MESSAGE\s*$", body[:offset]))
    if labels:
        normalize = lambda text: re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
        return "OBSERVED_SPEAKER_SECTION" if normalize(labels[-1].group(1)) == normalize(target) else None
    escaped = re.escape(target)
    if re.search(r"\b" + escaped + r"\s*:", paragraph, re.I):
        return "OBSERVED_SPEAKER_LABEL"
    if (_reported_quote_has_speaker(paragraph, escaped)
            and (len(target.split()) < 2 or _captured_surname_unambiguous(body, target))):
        return "REPORTED_QUOTATION"
    # Releases often introduce a full name and then use a surname. Only use
    # that observed alias when this capture contains the full target and no
    # competing capitalized full name with that surname. This is attribution,
    # not an authenticated identity or a claim that the quotation is true.
    names = target.split()
    if len(names) >= 2 and len(names[-1]) >= 3 and re.search(r"\b" + escaped + r"\b", body, re.I):
        surname = re.escape(names[-1])
        # Require the introduced full given name, excluding job-title prefixes.
        # Matching just the final given name would conflate two people sharing
        # a middle name. Quote and reporting verb must belong to this speaker.
        if _captured_surname_unambiguous(body, target) and _reported_quote_has_speaker(paragraph, surname):
            return "REPORTED_QUOTATION_SURNAME_IN_CAPTURE"
    return None


def classify_passage(text, *, domain=""):
    from backend.services.research.content_roles import LOCAL_BRAND_ABUSE, LOCAL_BRAND_WARNING, LOCAL_BRAND_NEGATION
    role = paragraph_role(text)
    if role != "SUBSTANTIVE_CANDIDATE":
        return role
    if domain == "brand" and re.search(LOCAL_BRAND_NEGATION, text, re.I):
        return "DISPUTED_CLAIM"
    if re.search(r"\b(?:false|fabricated|misattributed|debunked) (?:claim|quote|allegation)|\b(?:did not|never) (?:say|endorse)", text, re.I):
        return "DISPUTED_CLAIM"
    if ((re.search(r"\b(?:beware|warns|warning|we never|we do not|protect yourself|avoid scams)\b", text, re.I)
            or re.search(LOCAL_BRAND_WARNING, text, re.I))
            and re.search(r"scam|fraud|phishing|fake|" + LOCAL_BRAND_ABUSE, text, re.I)):
        return "SAFETY_WARNING"
    if re.search(r"\b(?:add to cart|shop now|shop all|free shipping|size guide)\b", text, re.I) and not re.search(r"\b(?:counterfeit|replica|knockoff|unauthorized seller)\b", text, re.I):
        return "PRODUCT_CATALOG"
    if re.search(r"\b(?:sponsored content|advertisement|paid promotion)\b", text, re.I):
        return "ADVERTISEMENT"
    if domain == "brand" and re.search(r"\b(?:I ordered|my order|never received|my refund|delivery delayed|customer complaint)\b", text, re.I):
        return "CUSTOMER_COMPLAINT"
    if domain == "brand" and re.search(r"counterfeit|phishing|impersonat|scam|fraud", text, re.I) and re.search(r"\b(?:seized|arrested|charged|convicted|court|police|customs|CBP)\b", text, re.I):
        return "REPORTED_ENFORCEMENT"
    if domain == "personal" and re.search(r"\b(?:scams?|frauds?)\b", text, re.I):
        # Political/financial criticism can call a policy or buyback a "scam".
        # Preserve the publisher's exact assertion as context, but require a
        # described abuse mechanism/incident before reporting an identity threat.
        incident = re.search(r"phishing|fake giveaway|crypto fraud|send btc|investment scheme|impersonat|deepfake"
            r"|fake (?:account|profile|handle)|identity theft|victims?|scammers?|scammed|defraud|fraudulent"
            r"|solicit|endorse|promot|charged|arrest|convict|doxx|leaked|targeted.{0,50}scam"
            r"|contribution address|(?:send|double).{0,80}(?:money|amount|crypto)", text, re.I)
        return "UNVERIFIED_ALLEGATION" if incident else "SOURCE_REPORTED_CONTEXT"
    if domain in {"brand", "personal"} and matches_objective(text, domain):
        if re.search(r"scam|counterfeit|impersonat|deepfake|fake |phishing|fraud|" + LOCAL_BRAND_ABUSE, text, re.I):
            return "UNVERIFIED_ALLEGATION"
        if re.search(r"\b(?:denied|denies|authentic|transcript)\b", text, re.I):
            return "PUBLIC_STATEMENT"
        return "ARTICLE_CONTENT"
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
            if _transcript_speaker_section(body, match.start(), target, match.start() + len(text)) == "OTHER_OBSERVED_TRANSCRIPT_SPEAKER":
                continue
        if len(text) < 25:
            continue
        role = classify_passage(text, domain=domain)
        attribution = public_statement_attribution(record, text, target) if domain == "personal" else None
        attributed = bool(attribution)
        if domain == "personal" and role == "PUBLIC_STATEMENT" and not attributed:
            role = "ARTICLE_CONTENT"
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
