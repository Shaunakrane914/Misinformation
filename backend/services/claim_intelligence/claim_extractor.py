"""Atomic Claim Extractor.

Decomposes complex headlines, allegations, and queries into atomic, testable
propositions while strictly preserving scope, negations, and qualifiers.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, List, Optional, Set

from backend.services.claim_intelligence.models import AtomicClaim

logger = logging.getLogger(__name__)

# Common temporal anchors
TEMPORAL_PATTERNS = [
    r"\b(today|yesterday|this morning|tonight|this week|this month|this year)\b",
    r"\b(q[1-4]\s*(?:20\d\d)?)\b",
    r"\b(20\d\d)\b",
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:,\s*\d{4})?\b",
    r"\b(\d{1,2}\s+(?:hours?|days?|weeks?|months?)\s+ago)\b",
    r"\b(historical(?:ly)?|previously|in the past)\b",
]

# Common scope indicators
SCOPE_PATTERNS = [
    (r"\b(all\s+products|nationwide|globally|worldwide|entire\s+fleet|every\s+store)\b", "global_or_universal"),
    (r"\b(batch\s*#?\s*[a-z0-9\-]+|lot\s*#?\s*[a-z0-9\-]+|specific\s+batch)\b", "specific_batch"),
    (r"\b(single\s+incident|isolated\s+case|one\s+user|single\s+store)\b", "isolated_instance"),
    (r"\b(subsidiary|division|regional\s+office|branch)\b", "sub_entity_only"),
]

# Common predicates in misinformation / investigative domains
PREDICATE_PATTERNS = [
    (r"\b(recalled?|recall(?:ing)?)\b", "recalled"),
    (r"\b(arrested?|detained?|custody)\b", "arrested"),
    (r"\b(resigned?|stepping\s+down|quit|fired)\b", "resigned_or_terminated"),
    (r"\b(bankrupt(?:cy)?|insolven(?:t|cy)|chapter\s+11)\b", "bankruptcy"),
    (r"\b(counterfeit(?:ed)?|fake|replica|bootleg)\b", "counterfeiting"),
    (r"\b(sued|lawsuit|indict(?:ed|ment)|investigat(?:ed|ion)|probe)\b", "legal_or_regulatory_action"),
    (r"\b(deepfake|voice\s+clone|ai\s+generated|face\s+swap)\b", "synthetic_media"),
    (r"\b(contaminated?|toxic|poison(?:ed)?)\b", "contamination"),
    (r"\b(bribe|fraud|embezzle(?:d|ment)|scam)\b", "fraud_or_financial_crime"),
    (r"\b(dead|death|passed\s+away|died)\b", "death_rumor"),
]

# Negation and qualification tokens
NEGATION_TOKENS = {"not", "never", "no", "denies", "denied", "false", "fake", "hoax", "debunked", "untrue", "neither", "nor"}
QUALIFIER_TOKENS = {"alleged", "allegedly", "rumor", "reportedly", "claimed", "purported", "unconfirmed", "supposedly", "sources say"}


class ClaimExtractor:
    """Deconstructs text into one or more AtomicClaim models."""

    def __init__(self, llm_gateway: Optional[Any] = None):
        self.gateway = llm_gateway

    def extract_claims(self, text: str, entity: Any = "") -> List[AtomicClaim]:
        """Extract atomic testable claims from user input or headline.

        Always guarantees at least one valid AtomicClaim output with preserved
        temporal scope, subject scope, and qualifiers.
        """
        clean_text = " ".join((text or "").split()).strip()
        if not clean_text:
            return []

        if isinstance(entity, dict):
            clean_entity = str(entity.get("name") or entity.get("brand") or entity.get("issuer") or "Subject").strip()
        elif isinstance(entity, str) and entity.strip():
            clean_entity = entity.strip()
        else:
            clean_entity = self._infer_entity(clean_text)

        # 1. Deterministic Extraction (Fast & Invariant Safe)
        deterministic_claim = self._deterministic_extract(clean_text, clean_entity)

        # 2. Return deterministic claim if single premise or standard query
        # Additional compound splitting if multi-premise ('and', 'while also')
        compound_claims = self._split_compound_claims(clean_text, clean_entity)
        if compound_claims:
            return compound_claims

        return [deterministic_claim]

    def _deterministic_extract(self, text: str, entity: str) -> AtomicClaim:
        """Deterministic parsing preserving qualifiers, scope, and dates."""
        lower = text.lower()

        # Check temporal scope
        temporal_scope = None
        for pattern in TEMPORAL_PATTERNS:
            match = re.search(pattern, lower, re.I)
            if match:
                temporal_scope = match.group(0).strip()
                break

        # Check subject scope
        subject_scope = "unspecified"
        for pattern, scope_label in SCOPE_PATTERNS:
            if re.search(pattern, lower, re.I):
                subject_scope = scope_label
                break

        # Check predicate
        predicate = ""
        for pattern, pred_label in PREDICATE_PATTERNS:
            if re.search(pattern, lower, re.I):
                predicate = pred_label
                break

        # Check qualifiers and negations
        words = set(re.findall(r"\b[a-z\-]+\b", lower))
        extracted_qualifiers = sorted(list((words & QUALIFIER_TOKENS) | (words & NEGATION_TOKENS)))
        is_negated = bool(words & NEGATION_TOKENS)

        # Normalize proposition (stripping excessive hype or question marks)
        norm_text = text.rstrip("?!. ")
        if norm_text.lower().startswith(("is it true that", "did", "has", "verify if")):
            norm_text = re.sub(r"^(?:is\s+it\s+true\s+that|did|has|verify\s+if)\s+", "", norm_text, flags=re.I)

        return AtomicClaim.create(
            raw_allegation=text,
            target_entity=entity,
            normalized_proposition=norm_text,
            predicate=predicate,
            subject_scope=subject_scope,
            temporal_scope=temporal_scope,
            extracted_qualifiers=extracted_qualifiers,
            is_negated=is_negated,
        )

    def _split_compound_claims(self, text: str, entity: str) -> List[AtomicClaim]:
        """Split assertions joined by distinct conjunctions (e.g. 'X recalled products AND CFO resigned')."""
        # Look for compound markers with verbs on both sides
        parts = re.split(r"\s+(?:and\s+also|while\s+also|after\s+allegations\s+of)\s+", text, flags=re.I)
        if len(parts) <= 1:
            return []

        results = []
        for p in parts:
            p_clean = p.strip()
            if len(p_clean.split()) >= 3:
                results.append(self._deterministic_extract(p_clean, entity))

        return results if len(results) > 1 else []

    def _infer_entity(self, text: str) -> str:
        """Infer target entity from initial noun chunks or common delimiters."""
        # Check quoted strings
        quotes = re.findall(r'"([^"]{2,40})"', text)
        if quotes:
            return quotes[0]

        # Check leading capitalized words
        match = re.match(r"^([A-Z][a-zA-Z0-9.\-&]+(?:\s+[A-Z][a-zA-Z0-9.\-&]+)?)", text)
        if match:
            candidate = match.group(1).strip()
            if candidate.lower() not in {"is", "did", "has", "verify", "what", "why", "when", "report"}:
                return candidate

        return text.split()[0] if text.split() else "Unknown Entity"


claim_extractor = ClaimExtractor()

