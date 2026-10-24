"""
Aegis Protocol — Contradiction Detection Engine
===============================================
Detects and categorizes conflicting statements, opposing attributions,
denials, and debunked claims across retrieved evidence items.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.services.research.research_models import ContradictionType, EvidenceItem

DENIAL_PATTERNS = [
    re.compile(r'\b(?:denied|denies|dismissed|refuted|debunked|rejected|unfounded)\b', re.I),
    re.compile(r'\b(?:not true|false rumor|no plans|categorically denies|hoax)\b', re.I),
    re.compile(r'\b(?:fake news|fabrication)\b', re.I)
]

_NON_SUBJECT_TERMS = {
    "about", "after", "against", "also", "and", "are", "being", "but",
    "claim", "claims", "company", "could", "from", "has", "have", "into",
    "its", "new", "not", "official", "over", "report", "reported", "reports",
    "rumor", "rumors", "said", "says", "source", "sources", "that", "the",
    "their", "this", "was", "were", "will", "with", "denied", "denies",
    "dismissed", "refuted", "debunked", "rejected", "unfounded", "false",
    "fake", "news", "hoax", "fabrication",
}


def _subject_terms(text: str, target_name: str) -> set[str]:
    """Keep only distinctive shared subject words; generic news prose is not a claim match."""
    target_terms = set(re.findall(r"[a-z0-9]+", target_name.lower()))
    return {
        term for term in re.findall(r"[a-z0-9]+", text.lower())
        if len(term) >= 3 and term not in _NON_SUBJECT_TERMS
        and term not in target_terms
    }


def _captured_reference(item, target_name):
    """Return an exact captured paragraph, never a discovery headline as proof."""
    from backend.services.research.passage_records import captured_passages
    rows = captured_passages(item, target=target_name) if item.content else []
    return next((row for row in rows if row["relevance"] != "DISCOVERY_ONLY"
                 and row["content_role"] not in {"NAVIGATION", "SOURCE_METADATA", "AUTHOR_BIO"}), None)


class ContradictionDetector:
    """Identifies and classifies evidentiary conflicts across candidates."""

    def __init__(self):
        pass

    def detect_contradictions(
        self,
        items: List[EvidenceItem],
        target_name: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Scans evidence items for factual contradictions, denials, and attribution differences.
        """
        contradictions: List[Dict[str, Any]] = []
        for item in items:
            item.contradiction_flag = False
        if len(items) < 2:
            return contradictions

        # Group items that contain denials or debunking markers
        denial_items = []
        affirmative_items = []

        for item in items:
            text = f"{item.title} {item.snippet} {item.relevant_excerpt} {item.content}".lower()
            is_denial = any(p.search(text) for p in DENIAL_PATTERNS)
            if is_denial:
                denial_items.append(item)
            else:
                affirmative_items.append(item)

        # This is a conservative lexical candidate detector, not semantic entailment.
        # A denial marker by itself is not evidence that another item disagrees.
        for d_item in denial_items:
            d_text = f"{d_item.title} {d_item.snippet} {d_item.relevant_excerpt}"
            d_terms = _subject_terms(d_text, target_name)

            for a_item in affirmative_items:
                a_text = f"{a_item.title} {a_item.snippet} {a_item.relevant_excerpt}"
                shared_subject = _subject_terms(a_text, target_name) & d_terms
                # The named target and boilerplate alone cannot establish that
                # both sources are discussing the same proposition.
                if len(shared_subject) >= 2:
                    a_ref = _captured_reference(a_item, target_name)
                    d_ref = _captured_reference(d_item, target_name)
                    c_id = f"cont_{len(contradictions) + 1:03d}"
                    contradictions.append({
                        "contradiction_id": c_id,
                        # Shared terms + denial language are a review lead,
                        # even with captured paragraphs, not semantic entailment.
                        "type": "POSSIBLE_DISAGREEMENT",
                        "established": False,
                        "claim_support_verified": False,
                        "passage_references": [ref for ref in (a_ref, d_ref) if ref],
                        "statement_a": a_ref["text"] if a_ref else a_item.title,
                        "source_a": a_item.source_name,
                        "source_a_id": a_item.id,
                        "statement_b": d_ref["text"] if d_ref else d_item.title,
                        "source_b": d_item.source_name,
                        "source_b_id": d_item.id,
                        "explanation": (
                            f"Possible factual disagreement: '{d_item.source_name}' uses explicit denial language "
                            f"on the same sampled subject as '{a_item.source_name}'. "
                            "Verify claim wording and context before treating this as a resolved contradiction."
                        ),
                        "severity": "REVIEW_REQUIRED"
                    })
                    break
        # Two articles saying "due to" or "driven by" do not imply exclusive
        # causes. Attribution differences need an explicit claim-level model;
        # the former marker-only heuristic produced unsupported conflicts.

        return contradictions


contradiction_detector = ContradictionDetector()
