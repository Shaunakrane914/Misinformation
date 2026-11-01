"""Passage-Level Stance and Grounding Engine.

Maps atomic claims to exact source passages, computing stance (SUPPORTS,
CONTRADICTS, MENTIONS, IRRELEVANT) with cryptographic byte hashes and
explicit corporate denial isolation (denials != proof of falsity).
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.services.claim_intelligence.models import (
    AtomicClaim,
    EvidenceLink,
    StanceType,
)

logger = logging.getLogger(__name__)

# Lexical cues for corporate denials
DENIAL_PATTERNS = [
    r"\b(denie[ds]?|denying|denial|refute[ds]?|refuting|reject[ds]?)\b",
    r"\b(categorically\s+refutes?|strongly\s+rejects?|firmly\s+denies?)\b",
    r"\b(spokesperson\s+.*?\s*(?:said|stated|clarified|noted)\s+that\s+no\b)",
    r"\b(?:stated|clarified|reiterated|confirmed)\s+that\s+no\s+[a-z0-9\-]+\s+(?:has\s+occurred|took\s+place|exists)\b",
    r"\b(unfounded\s+rumors?|baseless\s+claims?|false\s+reports?|completely\s+untrue)\b",
    r"\b(company\s+(?:clarified|stated|reiterated)\s+there\s+is\s+no\b)",
    r"\bno\s+(?:recall|subpoena|lawsuit|investigation|truth|basis)\b",
]

# Lexical cues for explicit corroboration / confirmation
CONFIRMATION_PATTERNS = [
    r"\b(confirmed|announces?|announced|issued\s+a\s+statement\s+confirming)\b",
    r"\b(regulatory\s+filing\s+(?:shows|indicates|reveals))\b",
    r"\b(official\s+notice|formal\s+recall|sec\s+filing|fda\s+warning)\b",
    r"\b(admitted|pleaded\s+guilty|settlement\s+agreement)\b",
]

# Lexical cues for contradiction / debunking
CONTRADICTION_PATTERNS = [
    r"\b(debunked|proven\s+false|fact\s+check\s+finds|fabricated)\b",
    r"\b(did\s+not\s+(?:occur|happen|recall|resign|file))\b",
    r"\b(no\s+evidence\s+(?:supports|indicates|shows))\b",
    r"\b(hoax|parody|satire|misleading\s+context)\b",
]


class StanceAnalyzer:
    """Evaluates passage stance and provenance grounding against an atomic claim."""

    def evaluate_passage(
        self,
        claim: AtomicClaim,
        passage_text: str,
        source_id: str,
        source_url: str,
        publisher: str,
        full_source_text: Optional[str] = None,
        published_at: Optional[str] = None,
    ) -> EvidenceLink:
        """Evaluate how a passage relates to an atomic claim."""
        p_clean = " ".join((passage_text or "").split()).strip()
        offsets = self._calculate_offsets(p_clean, full_source_text)
        
        stance, confidence, is_denial, temporal_match, rationale = self._analyze_stance(
            claim, p_clean, publisher, published_at
        )

        return EvidenceLink.create(
            claim_id=claim.claim_id,
            source_id=source_id,
            source_url=source_url,
            publisher=publisher,
            passage_text=p_clean,
            passage_offsets=offsets,
            stance=stance,
            confidence=confidence,
            published_at=published_at,
            is_corporate_denial=is_denial,
            temporal_match=temporal_match,
            rationale=rationale,
        )

    def evaluate_source_passages(
        self,
        claim: AtomicClaim,
        passages: List[Dict[str, Any]],
    ) -> List[EvidenceLink]:
        """Evaluate a batch of passages against an atomic claim."""
        links: List[EvidenceLink] = []
        for p in passages:
            text = p.get("text") or p.get("passage_text") or p.get("content") or ""
            if not text or len(text.strip()) < 15:
                continue
            src_id = p.get("source_id") or p.get("evidence_id") or "unknown_src"
            url = p.get("source_url") or p.get("url") or ""
            pub = p.get("publisher_host") or p.get("publisher") or "Unknown Publisher"
            pub_date = p.get("published_at")
            full_body = p.get("full_content") or p.get("body")

            link = self.evaluate_passage(
                claim=claim,
                passage_text=text,
                source_id=src_id,
                source_url=url,
                publisher=pub,
                full_source_text=full_body,
                published_at=pub_date,
            )
            if link.stance != StanceType.IRRELEVANT:
                links.append(link)

        return links

    def _analyze_stance(
        self,
        claim: AtomicClaim,
        passage: str,
        publisher: str,
        published_at: Optional[str],
    ) -> Tuple[StanceType, float, bool, bool, str]:
        """Deterministic stance extraction with corporate denial isolation."""
        lower_pass = passage.lower()
        lower_claim = claim.normalized_proposition.lower()
        entity_lower = claim.target_entity.lower()

        # Check entity presence
        has_entity = entity_lower in lower_pass or any(t in lower_pass for t in entity_lower.split() if len(t) > 3)
        if not has_entity:
            return StanceType.IRRELEVANT, 0.2, False, True, "Entity not mentioned in passage."

        # Check corporate denial patterns
        is_denial = any(re.search(pat, lower_pass, re.I) for pat in DENIAL_PATTERNS)
        
        # Check temporal match
        temporal_match = True
        if claim.temporal_scope and claim.temporal_scope in {"today", "yesterday", "this week"}:
            # If claim claims 'today', but passage explicitly dates to an older year
            year_matches = re.findall(r"\b(201\d|202[0-4])\b", lower_pass)
            if year_matches:
                temporal_match = False

        # 1. Corporate Denial Detection
        if is_denial:
            # Denials refute the assertion's certainty, but are evidence of a denial
            rationale = (
                f"Passage records an explicit corporate denial or refutation by {publisher}. "
                "Recorded as evidence of denial, not automatic proof of falsity."
            )
            return StanceType.CONTRADICTS, 0.85, True, temporal_match, rationale

        # 2. Objective Contradiction Detection
        has_contradiction = any(re.search(pat, lower_pass, re.I) for pat in CONTRADICTION_PATTERNS)
        if has_contradiction:
            rationale = "Passage explicitly refutes, debunks, or contradicts the claimed assertion."
            return StanceType.CONTRADICTS, 0.90, False, temporal_match, rationale

        # 3. Confirmation / Support Detection
        has_confirm = any(re.search(pat, lower_pass, re.I) for pat in CONFIRMATION_PATTERNS)
        predicate_matched = bool(claim.predicate and (claim.predicate in lower_pass or claim.predicate.rstrip("ed") in lower_pass))

        if has_confirm or predicate_matched:
            if not temporal_match:
                rationale = (
                    f"Passage confirms a historical {claim.predicate or 'event'}, but does not match "
                    f"the asserted temporal window ('{claim.temporal_scope}'). Potential misleading context."
                )
                return StanceType.MENTIONS, 0.70, False, False, rationale
            elif has_confirm or (predicate_matched and claim.predicate in {"recalled", "counterfeiting", "bankruptcy", "arrested"}):
                rationale = "Passage provides affirmative documentation confirming the core proposition."
                return StanceType.SUPPORTS, 0.88, False, True, rationale

        # 4. Standard Mention / Relevant Observation
        if any(word in lower_pass for word in lower_claim.split() if len(word) > 4):
            if not temporal_match:
                rationale = (
                    f"Passage discusses the subject matter but references historical events rather than "
                    f"asserted '{claim.temporal_scope}'. Potential misleading context."
                )
            else:
                rationale = "Passage discusses the subject matter but neither definitively verifies nor refutes the core assertion."
            return StanceType.MENTIONS, 0.60, False, temporal_match, rationale

        return StanceType.IRRELEVANT, 0.3, False, True, "Passage content is topical but not evidentiary towards claim."

    def _calculate_offsets(self, passage: str, full_text: Optional[str]) -> Tuple[int, int]:
        """Find character start and end index of passage in full document."""
        if not full_text or not passage:
            return (0, len(passage))
        idx = full_text.find(passage)
        if idx != -1:
            return (idx, idx + len(passage))
        # Case-insensitive fallback
        idx_lower = full_text.lower().find(passage.lower())
        if idx_lower != -1:
            return (idx_lower, idx_lower + len(passage))
        return (0, len(passage))


stance_analyzer = StanceAnalyzer()
