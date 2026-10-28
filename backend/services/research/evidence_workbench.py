"""Exact-source passage publication, separate from findings and verdicts.

Pure deterministic projections: no retrieval, model use, persistence or change
to the winning excerpt consumed by existing assessments. Budgets are explicit;
omitted paragraphs are counted, never silently promoted or rewritten.
"""
import hashlib
import re
from collections import Counter

from backend.services.research.source_diversity import publisher_host


MAX_SOURCE_PASSAGES = 80
MAX_SOURCE_PASSAGE_CHARS = 20_000
MAX_WORKBENCH_PASSAGES = 512
MAX_WORKBENCH_TEXT_BYTES = 240_000


def text_key(text):
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().casefold().encode("utf-8")).hexdigest()


def _contained_text(shorter, longer):
    """Whole normalized source text, never token/subword similarity."""
    if not shorter:
        return False
    start = longer.find(shorter)
    while start >= 0:
        end = start + len(shorter)
        if ((start == 0 or not (longer[start - 1].isalnum() and shorter[0].isalnum()))
                and (end == len(longer) or not (longer[end].isalnum() and shorter[-1].isalnum()))):
            return True
        start = longer.find(shorter, start + 1)
    return False


def _collapse_contained_passages(rows):
    """Keep complete canonical context when captures split paragraphs differently.

    A merged paragraph can subsume several paragraphs in another capture. Keep
    its original text/offsets/hash; partial matches and paraphrases stay separate.
    Contained observations are not identical-passage aliases.
    """
    normalized = [re.sub(r"\s+", " ", row["text"]).strip().casefold() for row in rows]
    kept, contained, word_owners = [], 0, {}
    for index in sorted(range(len(rows)), key=lambda i: (-len(normalized[i]), i)):
        words = set(re.findall(r"\w+", normalized[index]))
        candidates = None
        for word in sorted(words, key=lambda word: len(word_owners.get(word, ()))):
            owners = word_owners.get(word, set())
            candidates = set(owners) if candidates is None else candidates & owners
            if not candidates:
                break
        owner = next((other for other in sorted(candidates if candidates is not None else kept)
                      if _contained_text(normalized[index], normalized[other])), None)
        if owner is None:
            kept.append(index)
            for word in words:
                word_owners.setdefault(word, set()).add(index)
            continue
        contained += 1
        observations = rows[owner].setdefault("contained_source_observations", [])
        aliases = [rows[index], *rows[index].get("also_reported_by", [])]
        for alias in aliases:
            if len(observations) >= 24:
                break
            observations.append({field: alias[field] for field in
                ("evidence_id", "passage_id", "source_url", "start", "end") if field in alias})
    return [rows[index] for index in sorted(kept)], contained


def _adjacent_issuer_paragraphs(item, target):
    """Publication-only context, never a new finding or source qualification.

    A one-issuer article often names the issuer once and then says "our" or
    "the company". Keep at most two immediately adjacent financial paragraphs
    with explicit pronoun references; stop at a heading, unrelated paragraph,
    comparison or another named subject. Preserve exact non-overlapping bytes.
    """
    from backend.services.research.content_roles import matches_objective, NON_EVENT_ROLES, paragraph_role
    from backend.services.research.passage_extractor import has_usable_passage
    from backend.infrastructure.acquisition.adapters.web.page_extraction import recovered_span_allowed
    body, page = item.content or "", item.metadata.get("page_metadata") or {}
    kind = page.get("body_kind") or (page.get("body_quality") or {}).get("body_kind")
    if (item.metadata.get("layer2_eligible") is False
            or item.metadata.get("temporal_required") and not item.metadata.get("temporal_eligible")
            or not target or kind != "ARTICLE_BODY" or not item.acquired_id and not item.metadata.get("read_success")
            or not re.match(r"^\s*" + re.escape(target) + r"\b", item.title or "", re.I)):
        return []
    if re.search(r"\b(?:roundup|comparison|versus|vs\.?|competitors?|rivals?|discusses|compares)\b", item.title, re.I):
        return []
    direct_anchor = (r"\b" + re.escape(target) + r"(?:\s*\([^)]{1,40}\))?(?:\s+(?:today|also))?\s+"
        r"(?:reported|recorded|generated|posted|earned)\s+"
        r"(?:(?:its|net|total|annual|quarterly|record|full.year|first.quarter|second.quarter|third.quarter|fourth.quarter|q[1-4])\s+){0,3}"
        r"(?:revenue|profit|income|earnings|sales|cash flow|financial results|results)\b")
    remaining, selected = 0, []
    for match in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", body):
        paragraph = match.group().rstrip()
        heading = paragraph in page.get("headings", []) or any(
            isinstance(row, dict) and row.get("role") == "HEADING" and row.get("start") == match.start()
            for row in page.get("text_blocks", []))
        allowed = (not heading and len(paragraph) <= 6000
            and recovered_span_allowed(body, page, match.start(), match.start() + len(paragraph))
            and paragraph_role(paragraph) not in NON_EVENT_ROLES
            and matches_objective(paragraph, "financial")
            and has_usable_passage({"content": paragraph, "content_depth": item.content_depth}))
        comparison = re.search(r"\b(?:while|whereas|unlike|compared|competitors?|rivals?|another company)\b", paragraph, re.I)
        if not allowed or comparison:
            remaining = 0
        elif re.search(r"\b" + re.escape(target) + r"\b", paragraph, re.I):
            subjects = re.findall(r"\b((?:[A-Z][\w'-]+[ \t]+){1,4})(?:reported|recorded|generated|earned|posted|increased|decreased)\b", paragraph)
            generic = {"the", "its", "it", "we", "our", "this", "these", "those", "the company"}
            other_subject = any(" ".join(subject.split()).casefold() not in generic | {target.casefold()} for subject in subjects)
            remaining = 2 if re.search(direct_anchor, paragraph, re.I) and not other_subject else 0
        elif remaining and re.match(r"^(?:the company|its|it|we|our)\b", paragraph, re.I):
            selected.append((1.5, paragraph))
            remaining -= 1
        else:
            remaining = 0
    return selected


def _adjacent_brand_paragraphs(item, target):
    """Bounded article context only, not new observed attackers or findings."""
    from backend.services.research.content_roles import matches_objective, NON_EVENT_ROLES, paragraph_role
    from backend.services.research.passage_extractor import has_usable_passage
    from backend.infrastructure.acquisition.adapters.web.page_extraction import recovered_span_allowed
    body, page = item.content or "", item.metadata.get("page_metadata") or {}
    kind = page.get("body_kind") or (page.get("body_quality") or {}).get("body_kind")
    if (item.metadata.get("layer2_eligible") is False or kind != "ARTICLE_BODY" or not target
            or not item.acquired_id and not item.metadata.get("read_success")
            or not re.search(r"\b" + re.escape(target) + r"\b", item.title or "", re.I)):
        return []
    remaining, selected = 0, []
    for match in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", body):
        paragraph = match.group().rstrip()
        heading = paragraph in page.get("headings", []) or any(isinstance(row, dict)
            and row.get("role") == "HEADING" and row.get("start") == match.start()
            for row in page.get("text_blocks", []))
        if (heading or len(paragraph) > 6000 or paragraph_role(paragraph) in NON_EVENT_ROLES
                or not recovered_span_allowed(body, page, match.start(), match.start() + len(paragraph))
                or not has_usable_passage({"content": paragraph, "content_depth": item.content_depth})):
            remaining = 0
        elif re.search(r"\b" + re.escape(target) + r"\b", paragraph, re.I) and matches_objective(paragraph, "brand"):
            remaining = 2
        elif (remaining and re.match(r"^(?:this (?:message|offer|website|page)|the (?:message|offer|website|page)|"
                r"este|esta|el mensaje|la página|ce message|cette|le message|la page)\b", paragraph, re.I)
                and (matches_objective(paragraph, "brand") or re.search(
                    r"credential|password|personal data|credit card|datos personales|datos bancarios|tarjeta|formulario|formulaire|numéro de carte|mot de passe", paragraph, re.I))):
            selected.append((1.5, paragraph))
            remaining -= 1
        else:
            remaining = 0
    return selected


def select_source_passages(item, scored, winner, domain, target="", intent=""):
    """Publish complete already-gated paragraphs, winner first for admission.

    Do not expand a short passage into arbitrary nearby text. Every row has
    exact offsets and a body hash, and receives its own observed content role.
    """
    from backend.services.research.passage_records import classify_passage, without_related_link_tail
    body = item.content or item.snippet or ""
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    selected, seen, available, chars, omitted, excluded, overlaps = [], set(), 0, 0, 0, 0, 0
    adjacent = (_adjacent_issuer_paragraphs(item, target) if domain == "financial"
                else _adjacent_brand_paragraphs(item, target) if domain == "brand" else [])
    inherited = {text_key(paragraph) for _, paragraph in adjacent}
    for _, paragraph in [(float("inf"), winner), *sorted([*scored, *adjacent], key=lambda row: -row[0])]:
        if domain == "personal":
            paragraph = without_related_link_tail(paragraph)
        key = text_key(paragraph)
        start = body.find(paragraph)
        if not paragraph or key in seen or start < 0:
            continue
        seen.add(key)
        # A losing headline/question or multi-company calendar cannot regain
        # evidentiary prominence merely because publication is now deeper.
        if domain == "financial" and (re.match(r"\s*(?:from live coverage|read more|related stories)\s*:", paragraph, re.I)
                or re.search(r"\blist (?:of companies )?(?:includes|including)\b", paragraph, re.I)):
            excluded += 1
            continue
        available += 1
        if len(selected) >= MAX_SOURCE_PASSAGES or chars + len(paragraph) > MAX_SOURCE_PASSAGE_CHARS:
            omitted += 1
            continue
        end = start + len(paragraph)
        # The compatibility winner can span several paragraphs. Retain it
        # unchanged, but never publish its captured bytes again as child rows.
        if any(start < row["end"] and end > row["start"] for row in selected):
            overlaps += 1
            continue
        role = classify_passage(paragraph, domain=domain)
        context = {}
        attribution = "SOURCE_ASSERTION"
        if domain == "personal":
            from backend.services.research.passage_records import public_statement_attribution
            observed_speaker = public_statement_attribution(item, paragraph, target)
            if observed_speaker:
                attribution = observed_speaker
                context["identity_authenticated"] = False
                if role == "ARTICLE_CONTENT":
                    role = "PUBLIC_STATEMENT"
            elif role == "PUBLIC_STATEMENT":
                role = "ARTICLE_CONTENT"
        if re.search(r"\b(?:correction|headline was amended|article has been updated|clarification)\b", paragraph, re.I):
            role = "CORRECTION_OR_RESPONSE"
        elif domain == "brand" and role == "PUBLIC_STATEMENT":
            # Product-safety reports/quoted allegations aren't attributed speech
            # by a monitored person and must not look like confirmed incidents.
            role = "PRODUCT_SAFETY_REPORT" if re.search(r"recall|defect|product safety|component issue", paragraph, re.I) else "SOURCE_REPORTED_CONTEXT"
        if domain == "financial":
            from backend.services.research.financial_context import financial_passage_context
            observed = financial_passage_context(paragraph, title=item.title, published_at=item.published_at,
                observed_at=item.metadata.get("acquired_at") or item.metadata.get("retrieved_at") or item.discovered_at,
                issuer=target, intent=intent)
            context = {key: observed[key] for key in ("publication_scope", "result_scope", "content_kind", "period_alignment")}
            if observed["publication_scope"] == "HISTORICAL_BACKGROUND":
                role = "HISTORICAL_FINANCIAL_CONTEXT"
            elif observed["result_scope"] == "FORECAST_OR_MIXED_REPORTED_CONTEXT":
                role = "FORECAST_OR_MIXED_FINANCIAL_CONTEXT"
        if key in inherited:
            context["subject_context"] = ("HEURISTIC_ADJACENT_ISSUER_CONTEXT" if domain == "financial"
                                           else "HEURISTIC_ADJACENT_BRAND_CONTEXT")
        selected.append({"passage_id": "ps_" + hashlib.sha256(
            (item.id + ":" + str(start) + ":" + paragraph).encode("utf-8")).hexdigest()[:16],
            "evidence_id": item.id, "start": start, "end": end, "text": paragraph,
            "captured_text_sha256": digest, "content_role": role,
            "relevance": "DIRECTLY_RELEVANT", "claim_status": "UNVERIFIED",
            "attribution": attribution, "source_url": item.canonical_url,
            "published_at": item.published_at or None, "scope": "HEURISTIC_PASSAGE_SELECTION_NOT_ENTAILMENT",
            "context_labels": context})
        chars += len(paragraph)
    return sorted(selected, key=lambda row: row["start"]), {
        "eligible_unique_paragraphs": available, "published_paragraphs": len(selected),
        "omitted_by_source_budget": omitted, "max_passages": MAX_SOURCE_PASSAGES,
        "max_chars": MAX_SOURCE_PASSAGE_CHARS, "excluded_non_assertive_context": excluded,
        "overlapping_source_spans_omitted": overlaps,
    }


def build_evidence_workbench(evidence):
    """Round-robin source publication; count identical text once across sources.

    Receives inspected public records, never raw unqualified candidates. Missing
    new-style inspections remain unknown rather than being reconstructed from
    discovery snippets. Source aliases preserve attribution of identical text.
    """
    sources, queues, seen_sources = [], [], set()
    invalid, source_omitted, overlapping_spans = 0, 0, 0
    for item in evidence[:100]:
        identity = item.get("evidence_id")
        extraction = item.get("extraction") or {}
        if not identity or identity in seen_sources:
            continue
        seen_sources.add(identity)
        rows = extraction.get("evidence_passages") or []
        if extraction.get("evidentiary_use") == "DISCOVERY_ONLY":
            invalid += len(rows)
            continue
        valid = []
        for row in rows[:MAX_SOURCE_PASSAGES]:
            if (not isinstance(row, dict) or row.get("evidence_id") != identity
                    or not isinstance(row.get("text"), str) or not row["text"].strip()
                    or type(row.get("start")) is not int or type(row.get("end")) is not int
                    or not 0 <= row["start"] < row["end"]
                    or row.get("captured_text_sha256") != extraction.get("captured_text_sha256")
                    or row.get("relevance") != "DIRECTLY_RELEVANT"):
                invalid += 1
                continue
            if any(row["start"] < other["end"] and row["end"] > other["start"] for other in valid):
                overlapping_spans += 1
                continue
            valid.append({**row, "claim_status": "UNVERIFIED", "source_url": item.get("url"),
                          "publisher_host": publisher_host(item.get("url")), "source_title": item.get("title"),
                          **({'source_permission': extraction['source_observations']['source_permission']}
                             if (extraction.get('source_observations') or {}).get('source_permission') else {}),
                          **({'content_language': extraction['source_observations']['content_language'], 'translation': 'NOT_GENERATED'}
                             if (extraction.get('source_observations') or {}).get('content_language') else {})})
        accounting = extraction.get("evidence_passage_accounting") or {}
        omitted = accounting.get("omitted_by_source_budget", 0)
        source_omitted += omitted if type(omitted) is int and omitted >= 0 else 0
        overlaps = accounting.get("overlapping_source_spans_omitted", 0)
        overlapping_spans += overlaps if type(overlaps) is int and overlaps >= 0 else 0
        if valid:
            sources.append({"evidence_id": identity, "url": item.get("url"), "title": item.get("title"),
                "publisher_host": publisher_host(item.get("url")),
                "available_passages": len(valid), "captured_words": (extraction.get("text_metrics") or {}).get("readable_words")})
            queues.append(valid)
    ordered = [queue[index] for index in range(max((len(q) for q in queues), default=0))
               for queue in queues if index < len(queue)]
    published, by_text, bytes_used, omitted = [], {}, 0, 0
    duplicate_rows = 0
    for row in ordered:
        key = text_key(row["text"])
        if key in by_text:
            duplicate_rows += 1
            aliases = by_text[key].setdefault("also_reported_by", [])
            if row["evidence_id"] != by_text[key]["evidence_id"] and len(aliases) < 24:
                aliases.append({field: row[field] for field in ("evidence_id", "passage_id", "source_url", "start", "end")})
            continue
        by_text[key] = dict(row)
    unique_rows, contained_rows = _collapse_contained_passages(list(by_text.values()))
    for row in unique_rows:
        if len(published) >= MAX_WORKBENCH_PASSAGES or bytes_used + len(row["text"].encode("utf-8")) > MAX_WORKBENCH_TEXT_BYTES:
            omitted += 1
            continue
        published.append(row)
        bytes_used += len(row["text"].encode("utf-8"))
    return {
        "schema": "evidence-workbench-v1", "target_multiplier": 20,
        "target_status": "NOT_EVALUATED", "scope": "Source assertions selected by heuristics, not verified claims",
        "passages": published, "sources": sources,
        "accounting": {"source_records_with_passages": len(sources),
            "observed_publisher_hosts": len({row["publisher_host"] for row in sources} - {""}),
            "available_unique_passages": len(unique_rows), "published_passages": len(published),
            "published_unique_words": sum(len(row["text"].split()) for row in published),
            "published_text_utf8_bytes": bytes_used, "identical_text_observations": duplicate_rows,
            "contained_text_observations": contained_rows, "overlapping_source_spans_omitted": overlapping_spans,
            "omitted_by_workbench_budget": omitted, "omitted_by_source_budget": source_omitted,
            "invalid_passage_records": invalid, "roles": dict(Counter(row["content_role"] for row in published)),
            "independence_verified": False},
        "limits": {"max_passages": MAX_WORKBENCH_PASSAGES, "max_text_utf8_bytes": MAX_WORKBENCH_TEXT_BYTES},
    }
