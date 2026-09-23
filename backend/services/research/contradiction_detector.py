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
    re.compile(r'\b(?:denied|dismissed|refuted|clarified|debunked|rejected|unfounded)\b', re.I),
    re.compile(r'\b(?:not true|false rumor|no plans|categorically denies|hoax)\b', re.I),
    re.compile(r'\b(?:fake news|misinformation|fabrication)\b', re.I)
]

ATTRIBUTION_PATTERNS = [
    re.compile(r'\b(?:attributed to|analysts cite|driven by|blamed on|due to|rather than)\b', re.I),
    re.compile(r'\b(?:contrasting with|disputing claims that)\b', re.I)
]

INTERPRETATION_PATTERNS = [
    re.compile(r'\b(?:bullish|bearish|upgrade|downgrade|optimistic|pessimistic)\b', re.I),
    re.compile(r'\b(?:undervalued|overvalued|headwind|tailwinds)\b', re.I)
]


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
        if len(items) < 2:
            return contradictions

        # Group items that contain denials or debunking markers
        denial_items = []
        affirmative_items = []

        for item in items:
            text = f"{item.title} {item.snippet} {item.relevant_excerpt}".lower()
            is_denial = any(p.search(text) for p in DENIAL_PATTERNS)
            if is_denial:
                denial_items.append(item)
            else:
                affirmative_items.append(item)

        # Detect FACTUAL_CONTRADICTION between affirmative reports and official/clear denials
        for d_item in denial_items:
            d_text = f"{d_item.title} {d_item.snippet}".lower()
            d_item.contradiction_flag = True

            for a_item in affirmative_items:
                a_text = f"{a_item.title} {a_item.snippet}".lower()
                # If they share target keywords but one affirms and one denies
                shared_tokens = set(a_text.split()) & set(d_text.split())
                if len(shared_tokens) >= 4:
                    a_item.contradiction_flag = True
                    c_id = f"cont_{len(contradictions) + 1:03d}"
                    contradictions.append({
                        "contradiction_id": c_id,
                        "type": ContradictionType.FACTUAL_CONTRADICTION.value,
                        "statement_a": a_item.title,
                        "source_a": a_item.source_name,
                        "source_a_id": a_item.id,
                        "statement_b": d_item.title,
                        "source_b": d_item.source_name,
                        "source_b_id": d_item.id,
                        "explanation": f"Source '{d_item.source_name}' explicitly denies, clarifies, or refutes statements reported in '{a_item.source_name}'.",
                        "severity": "HIGH" if d_item.primary_source else "MEDIUM"
                    })
                    break

        # Detect ATTRIBUTION_DIFFERENCE in financial / market explanations
        attribution_items = []
        for item in items:
            text = f"{item.title} {item.snippet}".lower()
            if any(p.search(text) for p in ATTRIBUTION_PATTERNS):
                attribution_items.append(item)

        if len(attribution_items) >= 2:
            it1, it2 = attribution_items[0], attribution_items[1]
            if it1.source_domain != it2.source_domain and it1.title != it2.title:
                c_id = f"cont_{len(contradictions) + 1:03d}"
                contradictions.append({
                    "contradiction_id": c_id,
                    "type": ContradictionType.ATTRIBUTION_DIFFERENCE.value,
                    "statement_a": it1.title,
                    "source_a": it1.source_name,
                    "source_a_id": it1.id,
                    "statement_b": it2.title,
                    "source_b": it2.source_name,
                    "source_b_id": it2.id,
                    "explanation": f"Differing causal drivers or market attributions reported between '{it1.source_name}' and '{it2.source_name}'.",
                    "severity": "LOW"
                })

        return contradictions


contradiction_detector = ContradictionDetector()
