"""
Aegis Protocol — Relevant Passage & Entity Extraction Engine
============================================================
Extracts high-signal, relevant passages, factual claims, and named entities
from full-text articles rather than dumping raw markdown to reasoning models.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from backend.services.research.research_models import EvidenceItem
from backend.services.research.content_roles import NON_EVENT_ROLES, document_role, matches_objective, paragraph_role, local_prose_predicate
from backend.services.research.clause_predicates import has_finite_predicate
from backend.infrastructure.acquisition.adapters.web.page_extraction import recovered_span_allowed

# High-signal action verbs and investigative indicators
SIGNAL_MARKERS: Set[str] = {
    "announced", "reported", "disclosed", "filed", "confirmed", "denied",
    "investigating", "lawsuit", "alleged", "probe", "regulatory", "earnings",
    "revenue", "profit", "loss", "plunged", "surged", "counterfeit", "scam",
    "warning", "advisory", "recalled", "halted", "resigned", "settlement", "impersonated",
    "said", "says", "wrote", "writes", "warned", "warns", "achieved", "recorded", "generated"
}

DISCLOSURE_CONTEXT = ("forward-looking statements", "certain statements in this press release",
                      "safe harbor statement")

# This is an explicitly heuristic passage-quality filter, not entailment or
# calibrated confidence. Preserve rejected text in the corpus for inspection.
NAVIGATION_MARKERS = ("toggle navigation", "switch to dark", "switch to light", "shop all",
                      "privacy policy", "contact us", "men women", "add to cart", "browse select")


def _topic_token_keys(text):
    """Conservative regular -ies plurals for topic matching, not identity joins.

    Preserve source bytes and the existing token-overlap threshold. This is not
    synonym expansion, arbitrary stemming or support for a source's assertion.
    """
    return {token[:-3] + "y" if re.search(r"[^aeiou]ies$", token) and len(token) > 4 else token
            for token in re.findall(r"[a-z0-9]{3,}", text.casefold())}


def _bare_label(text):
    """A short keyword/date label is not a proposition. Numeric rows survive.

    This is a conservative fallback for text without DOM spans, not a parser
    proving grammar/entailment. Captured headings are excluded independently.
    """
    if len(text) > 160:
        return False
    predicate = re.search(r"\b(?:is|are|was|were|has|have|had|will|can|could|may|must|did|does|do|said|says|wrote|writes|reported|reports|announced|announces|confirmed|confirms|denied|denies|warned|warns|seized|charged|arrested|filed|rose|fell|grew|increased|decreased|appointed|joined|tested|found|shows|offers|offered|sold|allows|contains|includes|limits|rated|received|ordered|launched|released|endorsed|claimed|claims)\b", text, re.I)
    measurement = re.search(r"(?:[$€£₹]|\b(?:USD|INR|EUR|GBP)\b)\s*\d|\d+(?:\.\d+)?\s*(?:%|(?:percent|million|billion|crore)\b)", text, re.I)
    return not predicate and not measurement and not local_prose_predicate(text)


def has_usable_passage(item) -> bool:
    from backend.schemas.evidence_inspection import METADATA_DEPTHS
    value = item.get if isinstance(item, dict) else lambda key, default=None: getattr(item, key, default)
    depth = str(value("content_depth", "UNKNOWN") or "UNKNOWN").upper()
    if depth in METADATA_DEPTHS | {"SEARCH_SNIPPET", "SEARCH_INDEX_DISCOVERY", "SYNDICATED_SUMMARY"}:
        return False
    if (value("metadata", {}) or {}).get("layer2_eligible") is False:
        return False
    if value("extraction_status") in {"EMPTY", "NO_RELEVANT_PASSAGE", "METADATA_ONLY", "FALLBACK", "TEMPORAL_INELIGIBLE", "LAYER2_REJECTED", "SOURCE_PERMISSION_REQUIRED"}:
        return False
    if document_role(item) in NON_EVENT_ROLES:
        return False
    text = value("relevant_excerpt") or value("content") or value("snippet") or ""
    lower = text.lower()
    return (paragraph_role(text) not in NON_EVENT_ROLES and len(text.strip()) >= 40 and not _bare_label(text)
            and sum(marker in lower for marker in NAVIGATION_MARKERS) < 2
            and bool(has_finite_predicate(text)
                     or any(re.search(r"\b" + marker + r"\b", lower) for marker in SIGNAL_MARKERS)
                     or local_prose_predicate(text)))


def _brand_context_window(item, raw_text, target_tokens, clean_target):
    """At most three adjacent actual-article paragraphs, never headline joins.

    Incident prose may name a brand once and describe the same operation in the
    following paragraph. This exception requires an explicit incident verb and
    objective in the subject paragraph; generic product prose cannot borrow an
    unrelated accusation from another paragraph or a related-story heading.
    """
    page = item.metadata.get("page_metadata") or {}
    quality = page.get("body_quality") or {}
    kind = page.get("body_kind") or (quality.get("body_kind") if isinstance(quality, dict) else None)
    acquired = item.metadata.get("read_success") is True or bool(item.acquired_id)
    if kind != "ARTICLE_BODY" or not acquired:
        return None
    spans = list(re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", raw_text))
    for index, anchor in enumerate(spans):
        paragraph = anchor.group().rstrip()
        if not recovered_span_allowed(raw_text, page, anchor.start(), anchor.start() + len(paragraph)):
            continue
        lower = paragraph.casefold()
        present = target_tokens & set(re.findall(r"[a-z0-9]{3,}", lower))
        subject = bool(clean_target and clean_target in lower) or bool(target_tokens and len(present) >= min(2, len(target_tokens)))
        incident_verb = re.search(r"\b(?:uncovered|unearthed|intercepted|recovered|documented|reported|investigated|seized|arrested|charged)\b", paragraph, re.I)
        objective = matches_objective(paragraph, "brand") or bool(
            re.search(r"\billicit (?:operation|goods|merchandise)\b", paragraph, re.I)
            and re.search(r"\b(?:dupes|imitations)\b", paragraph, re.I))
        if not subject or not incident_verb or not objective:
            continue
        for end_index in range(index, min(index + 3, len(spans))):
            current = spans[end_index]
            text = current.group().rstrip()
            if (not recovered_span_allowed(raw_text, page, current.start(), current.start() + len(text))
                    or len(text) < 40 or paragraph_role(text) in NON_EVENT_ROLES
                    or text in page.get("headings", [])
                    or any(isinstance(row, dict) and row.get("role") == "HEADING"
                           and row.get("start") == current.start() for row in page.get("text_blocks", []))):
                break
            window = raw_text[anchor.start():current.start() + len(text)]
            if len(window) > 2000:
                break
            if has_usable_passage({"content": window, "content_depth": item.content_depth}):
                return window
    return None


class PassageExtractor:
    """Extracts target-relevant passages and key factual claims from source text."""

    def __init__(self):
        pass

    def extract_passages(
        self,
        items: List[EvidenceItem],
        target_name: str,
        intent: str = "",
        domain: str = "",
    ) -> List[EvidenceItem]:
        """
        Processes each evidence item, finding the most relevant excerpt and entities.
        """
        clean_target = re.sub(r"\([^)]*\)", "", target_name or "").lower().strip()
        target_tokens = set(re.findall(r"[a-z0-9]{3,}", clean_target)) - {"inc", "ltd", "limited", "corp", "corporation", "company"}
        intent_tokens = set(w for w in (intent or "").lower().split() if len(w) >= 4)
        from backend.services.research.entity_resolver import entity_resolver
        profile = entity_resolver.parse_request(target_name).target_entity
        topic_aliases = profile.aliases if profile.entity_type == "topic" else []

        for item in items:
            item.relevant_excerpt = ""
            # Recompute from current bytes; never trust a stale stored projection.
            item.metadata.pop("evidence_passages", None)
            item.metadata.pop("evidence_passage_accounting", None)
            item.excerpt_start = item.excerpt_end = -1
            from backend.services.research.source_registry import source_registry
            permission = (source_registry.excerpt_decision(item.canonical_url, item.metadata.get('page_metadata'))
                          if item.metadata.get('topic_source_controlled') or source_registry.match_url(item.canonical_url)
                          or (item.metadata.get('page_metadata') or {}).get('rights_exception_observed') else {'eligible': True})
            if permission.get('source_family'):
                item.metadata['source_use_permission'] = permission
            if not permission['eligible']:
                item.metadata['post_read_qualification_reason'] = permission.get('reason', 'PERMISSION_REQUIRED')
                item.extraction_status = 'SOURCE_PERMISSION_REQUIRED'
                continue
            if item.metadata.get("temporal_required") and not item.metadata.get("temporal_eligible"):
                item.extraction_status = "TEMPORAL_INELIGIBLE"
                continue
            if domain == "brand":
                from backend.services.research.source_quality import canonical_hostname, hostname_matches, ENCYCLOPEDIA_DOMAINS
                if any(hostname_matches(canonical_hostname(item.canonical_url), host) for host in ENCYCLOPEDIA_DOMAINS):
                    item.metadata["content_role"] = "BACKGROUND_REFERENCE"
                    item.extraction_status = "NO_RELEVANT_PASSAGE"
                    continue
            role = document_role(item)
            if role in NON_EVENT_ROLES:
                item.metadata["content_role"] = role
                item.extraction_status = "NO_RELEVANT_PASSAGE"
                continue
            from backend.schemas.evidence_inspection import METADATA_DEPTHS
            if item.content_depth in METADATA_DEPTHS | {"SEARCH_SNIPPET", "SEARCH_INDEX_DISCOVERY", "SYNDICATED_SUMMARY"}:
                item.relevant_excerpt = ""
                item.extraction_status = "METADATA_ONLY"
                continue
            raw_text = item.content or item.snippet
            if not raw_text:
                item.relevant_excerpt = item.title
                item.extraction_status = "EMPTY"
                continue

            if domain == "trending":
                from backend.services.research.trend_context import classify_source_context
                context = classify_source_context(item.title, raw_text, clean_target,
                    is_topic=profile.entity_type == "topic")
                item.metadata["trend_source_context"] = context
                if context["classification"] == "INCIDENTAL_MENTION":
                    item.extraction_status = "NO_RELEVANT_PASSAGE"
                    item.metadata["post_read_qualification_reason"] = context["reason"]
                    continue

            # A following sentence can negate or qualify the first. Select
            # complete source paragraphs, never isolated affirmative sentences.
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', raw_text) if len(p.strip()) >= 40]

            if not paragraphs:
                # Preserve a bounded display-only fallback for compatibility;
                # it is explicitly ineligible for findings, even if a later
                # caller bypasses this extractor's subject/objective gates.
                item.relevant_excerpt = raw_text[:350]
                item.extraction_status = "FALLBACK"
                continue

            # Score each paragraph
            best_p = paragraphs[0]
            best_score = -1.0
            best_idx = 0
            eligible_paragraphs = []

            for idx, p in enumerate(paragraphs):
                page = item.metadata.get("page_metadata") or {}
                start = raw_text.find(p)
                if not recovered_span_allowed(raw_text, page, start, start + len(p)):
                    continue
                structural_heading = any(isinstance(row, dict) and row.get("role") == "HEADING"
                    and row.get("start") == start and row.get("end") == start + len(p)
                    for row in page.get("text_blocks", []))
                # Older genuine captures have heading text, not span metadata.
                if (structural_heading or p in page.get("headings", [])
                        or p in {item.title, page.get("title")}):
                    continue
                from backend.services.research.passage_records import public_statement_attribution
                attributed_statement = domain == "personal" and bool(public_statement_attribution(item, p, clean_target))
                if not matches_objective(p, domain) and not attributed_statement:
                    continue
                if not has_usable_passage({"content": p, "content_depth": item.content_depth}):
                    continue
                p_lower = p.lower()
                present = target_tokens & set(re.findall(r"[a-z0-9]{3,}", p_lower))
                if domain == "trending" and profile.entity_type in {"topic", "concept", "product", "general"}:
                    present = _topic_token_keys(" ".join(target_tokens)) & _topic_token_keys(p_lower)
                topic_match = any(re.search(r"\b" + re.escape(alias.casefold()) + r"\b", p_lower) for alias in topic_aliases)
                if target_tokens and len(present) < min(2, len(target_tokens)) and clean_target not in p_lower and not topic_match and not attributed_statement:
                    continue
                score = 0.0
                if attributed_statement:
                    score += 3.0

                # Target presence
                if topic_match or (clean_target and clean_target in p_lower):
                    score += 3.0
                elif any(t in p_lower for t in target_tokens):
                    score += 1.5

                # Intent presence
                if any(it in p_lower for it in intent_tokens):
                    score += 1.0

                # Action markers
                matched_signals = sum(1 for m in SIGNAL_MARKERS if m in p_lower)
                score += min(2.0, 0.5 * matched_signals)

                # Numbers / currency / statistics presence
                if re.search(r'[\$₹€£]|\b\d+(\.\d+)?%|\b\d{4}\b|\bcrore\b|\bbillion\b|\bmillion\b', p_lower):
                    score += 1.0

                # Quotes presence
                if '"' in p or '“' in p or "'" in p:
                    score += 0.5

                # Keyword-dense legal disclosures must not crowd out the
                # substantive announcement. Keep them in captured source text;
                # this is selection priority, never prose deletion or truth.
                if any(marker in p_lower for marker in DISCLOSURE_CONTEXT):
                    score -= 3.0

                if domain == "trending":
                    # Fresh publication is not proof every paragraph describes
                    # a new event. Prefer an explicit source-reported lead over
                    # keyword/number-heavy historical comparison. This ranks
                    # exact source text; it does not infer an event timestamp,
                    # remove qualifications or verify a publisher's assertions.
                    if idx < 3 and re.search(
                        r"\b(?:has|have)\s+(?:(?:just|now|recently|not)\s+){0,2}"
                        r"(?:begun|started|launched|opened|announced|released|introduced)\b"
                        r"|\b(?:is|are)\s+(?:now\s+)?(?:testing|launching|opening|deploying)\b",
                        p_lower,
                    ):
                        score += 2.0
                    if re.search(r"\b(?:historically|historical background|in the past)\b", p_lower):
                        score -= 2.0
                    from backend.services.research.trend_context import event_priority
                    score += event_priority(p, idx)

                if domain == "financial" and clean_target:
                    # Prefer the paragraph's actual target proposition over a
                    # comparison that merely says "beside <target>" and then
                    # reports another company's figures. Do not delete context
                    # or infer that two brands/affiliates are the same issuer.
                    first_sentence = re.split(r"(?<=[.!?])\s+", p, maxsplit=1)[0]
                    target_subject = re.search(r"\b" + re.escape(clean_target)
                        + r"(?:\s+[A-Za-z-]+){0,2}\s+(?:said|reported|posted|announced|expects?|projects?|sees|recorded|achieved|disclosed|earned|generated|plans?|will|has|had)\b", p_lower)
                    if target_subject:
                        score += 2.5
                    nearby_financial = any(re.search(r"\b(?:profits?|revenues?|earnings|sales|margins?|shares?|prices?|dividends?)\b",
                        p_lower[max(0, match.start() - 100):match.end() + 130])
                        for match in re.finditer(r"\b" + re.escape(clean_target) + r"\b", p_lower))
                    if nearby_financial:
                        score += 2.5
                    from backend.services.research.financial_context import extract_financial_metrics_and_scales
                    observed_amounts = extract_financial_metrics_and_scales(p)
                    # Prefer exact financial performance text over a webcast
                    # schedule or a list of companies in an earnings preview.
                    # Amount presence is a relevance signal, never verification;
                    # consensus/forecast values keep their own explicit roles.
                    if observed_amounts:
                        score += 4.0 if any(row["amount_role"] == "REPORTED_AMOUNT"
                                            for row in observed_amounts) else 2.0
                    if not observed_amounts and re.search(
                            r"\b(?:webcast|conference call|investor relations website|dial.in|replay available)\b", p_lower):
                        score -= 4.0
                    if re.search(r"\b(?:list (?:of companies )?(?:includes|including)|companies likely to|earnings preview)\b", p_lower):
                        score -= 2.0
                    if re.search(r"\b(?:beside|besides|except for|compared with|unlike)\s+" + re.escape(clean_target) + r"\b", first_sentence, re.I):
                        score -= 3.0
                    # Prefer a concise complete paragraph, never an arbitrary
                    # clipped sentence window that could lose a qualification.
                    score -= min(4.0, max(0.0, (len(p.split()) - 180) / 100))

                if score >= 1.5 and len(p) <= 6000:
                    eligible_paragraphs.append((score, p))
                if score > best_score:
                    best_score = score
                    best_p = p
                    best_idx = idx

            if best_score < 1.5:
                if domain == "brand":
                    contextual = _brand_context_window(item, raw_text, target_tokens, clean_target)
                    if contextual:
                        best_p = contextual
                        best_score = 3.0
                        item.metadata["excerpt_context"] = "BOUNDED_ADJACENT_ARTICLE_PARAGRAPHS"
                if best_score < 1.5:
                    item.relevant_excerpt = ""
                    item.extraction_status = "NO_RELEVANT_PASSAGE"
                    continue

            # Clean and truncate best excerpt
            # Preserve exact offsets and qualifications. A short display
            # preview must not silently delete a later negation/date. The full
            # captured source remains available even if this bounded window ends.
            if len(best_p) > 6000:
                item.extraction_status = "NO_RELEVANT_PASSAGE"
                item.metadata["excerpt_truncated"] = True
                continue
            clean_excerpt = best_p
            if domain == "personal":
                from backend.services.research.passage_records import without_related_link_tail
                clean_excerpt = without_related_link_tail(clean_excerpt)

            item.relevant_excerpt = clean_excerpt
            item.excerpt_start = raw_text.find(best_p)
            item.excerpt_end = item.excerpt_start + len(clean_excerpt)
            item.extraction_status = "SUCCESS"
            # Keep the compatibility winner for verdict engines, while exposing
            # all bounded paragraphs that passed these same subject/objective/
            # structural gates. These are source assertions, never extra verdicts.
            if has_usable_passage(item):
                from backend.services.research.evidence_workbench import select_source_passages
                item.metadata["evidence_passages"], item.metadata["evidence_passage_accounting"] = select_source_passages(
                    item, eligible_paragraphs, clean_excerpt, domain, clean_target, intent)

            # Extract named entities & factual numbers
            entities = set()
            # Find capitalized entity sequences
            cap_entities = re.findall(r'\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*\b', clean_excerpt)
            for ce in cap_entities:
                if len(ce) > 3 and ce.lower() not in clean_target and ce not in ("The", "This", "That", "According", "However"):
                    entities.add(ce)
            item.entities = list(entities)[:5]

            # Extract numerical figures as topics
            facts = re.findall(r'[\$₹€£]\s*[\d\.,]+(?:\s*(?:billion|million|crore|lakh))?|\b\d+(?:\.\d+)?%', clean_excerpt, flags=re.IGNORECASE)
            item.topics = list(set(facts))[:4]

        return items


passage_extractor = PassageExtractor()
