"""
Aegis Protocol — Shared Claim Intelligence Engine
==================================================
Multi-dimensional claim extraction, cross-channel contradiction and divergence
detection, calibrated confidence scoring, non-binary epistemic verdicts, and
strict forensic evidence grounding.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from backend.services.research.research_models import (
    AtomicClaim,
    ClaimVerdict,
    ConfidenceLevel,
    ContradictionType,
    EvidenceItem,
    SourceRole,
    SourceTier,
)

logger = logging.getLogger(__name__)

# Patterns for denials and debunking
DENIAL_PATTERNS = [
    re.compile(r'\b(?:denied|denies|dismissed|refuted|debunked|rejected|unfounded|disproven)\b', re.I),
    re.compile(r'\b(?:not true|false rumor|no plans|categorically denies|hoax|fake news|fabrication)\b', re.I),
    re.compile(r'\b(?:spokesperson confirms alive|denies report|officially denied)\b', re.I),
]

# Patterns for temporal shifts and outdated narratives
TEMPORAL_SHIFT_PATTERNS = [
    re.compile(r'\b(?:previously|formerly|in 20\d\d|resurfaced|old video|past event|archived|superseded)\b', re.I),
    re.compile(r'\b(?:no longer|stepped down|departed|since reversed|updated policy|corrected)\b', re.I),
]

# Non-subject stop words for lexical alignment
NON_SUBJECT_TERMS: Set[str] = {
    "about", "after", "against", "also", "and", "are", "being", "but",
    "claim", "claims", "company", "could", "from", "has", "have", "into",
    "its", "new", "not", "official", "over", "report", "reported", "reports",
    "rumor", "rumors", "said", "says", "source", "sources", "that", "the",
    "their", "this", "was", "were", "will", "with", "denied", "denies",
    "dismissed", "refuted", "debunked", "rejected", "unfounded", "false",
    "fake", "news", "hoax", "fabrication", "alleged", "statement", "online",
    "circulating", "post", "video", "media",
}

# Number extraction pattern: extracts numeric tokens including currency, multipliers, percentages
NUMERIC_VALUE_PATTERN = re.compile(
    r'(?:[\$€£¥₹]\s*)?(\d+(?:\.\d+)?)\s*(%|percent|billion|million|trillion|b|m|k)?\b',
    re.I
)


def extract_numeric_facts(text: str) -> List[Dict[str, Any]]:
    """Extract quantitative values with metric context and normalized float magnitude."""
    facts = []
    if not text:
        return facts
    for match in NUMERIC_VALUE_PATTERN.finditer(text):
        num_str = match.group(1)
        unit = (match.group(2) or "").lower()
        try:
            val = float(num_str)
        except ValueError:
            continue

        multiplier = 1.0
        if unit in ("billion", "b"):
            multiplier = 1e9
        elif unit in ("million", "m"):
            multiplier = 1e6
        elif unit in ("trillion",):
            multiplier = 1e12
        elif unit in ("k",):
            multiplier = 1e3
        elif unit in ("%", "percent"):
            multiplier = 0.01

        normalized_val = val * multiplier
        # Context window: 40 chars before and after
        start = max(0, match.start() - 40)
        end = min(len(text), match.end() + 40)
        context = text[start:end].strip()

        facts.append({
            "raw_text": match.group(0).strip(),
            "raw_number": val,
            "unit": unit,
            "normalized_value": normalized_val,
            "context": context,
        })
    return facts


def subject_terms(text: str, target_name: str = "") -> Set[str]:
    """Extract salient subject terms, filtering out stopwords and target boilerplate."""
    target_tokens = set(re.findall(r'[a-z0-9]+', target_name.lower())) if target_name else set()
    terms = set()
    for token in re.findall(r'[a-z0-9]+', text.lower()):
        if len(token) >= 3 and token not in NON_SUBJECT_TERMS and token not in target_tokens:
            terms.add(token)
    return terms


class ClaimIntelligenceEngine:
    """
    Central shared intelligence engine implementing Stage 8C specifications:
    - Atomic claim extraction
    - Multi-dimensional contradiction and divergence detection
    - Calibrated confidence scoring
    - Non-binary verdicts
    - Grounded evidence citations
    """

    def __init__(self):
        logger.info("[ClaimIntelligenceEngine] Initialized with 5-dimension contradiction detection and calibrated verdicts")

    def decompose_claims(self, text: str) -> List[AtomicClaim]:
        """
        Decomposes compound unstructured text into atomic, testable claims.
        Extracts entities, verifiable dimensions, temporal/scope anchors, and claim types.
        """
        raw = (text or "").strip()
        if not raw:
            return []

        # Split on sentence boundaries, coordinating conjunctions, or bullet points
        raw_clean = re.sub(r'[\r\n]+', '\n', raw)
        lines = [line.strip().lstrip('-*• ') for line in raw_clean.split('\n') if line.strip()]
        
        candidates: List[str] = []
        for line in lines:
            parts = [p.strip() for p in re.split(r'(?<=[.?!])\s+|\s+(?:and also|additionally|furthermore|claiming that)\s+', line) if len(p.strip()) > 8]
            if parts:
                candidates.extend(parts)
            elif len(line) > 8:
                candidates.append(line)

        if not candidates:
            candidates = [raw]

        claims: List[AtomicClaim] = []
        for idx, candidate in enumerate(candidates):
            c_id = f"claim_{idx + 1:03d}"
            
            # 1. Entity Extraction
            capitalized = re.findall(r'\b[A-Z][a-zA-Z0-9_\-\.]{2,}\b', candidate)
            # Filter common sentence-initial non-entities
            filtered_entities = [w for w in capitalized if w.lower() not in {"the", "according", "sources", "reports", "after", "yesterday", "recent"}]
            entity = filtered_entities[0] if filtered_entities else (capitalized[0] if capitalized else "General Entity")

            # 2. Time anchor
            time_matches = re.findall(r'\b(?:19|20)\d{2}\b|\b(?:today|yesterday|this week|last month|january|february|march|april|may|june|july|august|september|october|november|december|q[1-4])\b', candidate, re.I)
            time_anchor = time_matches[0] if time_matches else ""

            # 3. Location / Scope anchor
            loc_matches = re.findall(r'\b(?:us|usa|china|europe|eu|delaware|california|new york|india|uk|japan|germany|sec|ftc|court)\b', candidate, re.I)
            location = loc_matches[0].upper() if loc_matches else ""

            # 4. Verifiable dimensions
            dims: List[str] = []
            if re.search(r'[\$€£¥₹]|\b\d+(?:\.\d+)?%|\b\d+\s*(?:billion|million|trillion|shares|dollars|basis points)\b', candidate, re.I):
                dims.append("QUANTITATIVE_VALUE")
            if time_anchor:
                dims.append("TEMPORAL_ANCHOR")
            if location:
                dims.append("GEOGRAPHIC_SCOPE")
            if any(w in candidate.lower() for w in ["acquired", "bought", "merger", "filed", "resigned", "sued", "announced", "launched", "halted", "cured", "died"]):
                dims.append("ACTION_EVENT")
            if any(w in candidate.lower() for w in ["according to", "reported by", "statement by", "filing reveals", "spokesperson"]):
                dims.append("AUTHORITY_CITATION")
            if not dims:
                dims.append("FACTUAL_ASSERTION")

            # 5. Claim Type
            claim_type = "FACTUAL"
            c_lower = candidate.lower()
            if "quant" in "".join(dims).lower():
                claim_type = "NUMERICAL"
            elif any(w in c_lower for w in ["will", "predicted to", "expects to", "projected"]):
                claim_type = "PREDICTIVE"
            elif any(w in c_lower for w in ["because", "due to", "caused by", "driven by", "result of"]):
                claim_type = "CAUSAL"
            elif any(w in c_lower for w in ["said that", "claimed that", "stated that", "attributed to"]):
                claim_type = "ATTRIBUTIVE"
            elif time_anchor and "TEMPORAL_ANCHOR" in dims:
                claim_type = "TEMPORAL"

            claims.append(AtomicClaim(
                claim_id=c_id,
                claim_text=candidate,
                entity=entity,
                event=dims[0] if dims else "ASSERTION",
                time=time_anchor,
                location=location,
                claim_type=claim_type,
                verifiable_dimensions=dims,
                verdict=ClaimVerdict.UNVERIFIED.value,
                confidence=0.50,
                rationale="Ingested and decomposed into atomic claim."
            ))

        return claims

    def detect_contradictions(
        self,
        items: List[EvidenceItem],
        target_name: str = "",
        claims: Optional[List[AtomicClaim]] = None
    ) -> List[Dict[str, Any]]:
        """
        Multi-dimensional contradiction and divergence detector covering 5 distinct axes:
        1. FACTUAL_CONTRADICTION: Direct factual denial or opposing assertion.
        2. TEMPORAL_DIVERGENCE: Narrative was true at T1, but updated/invalidated at T2.
        3. NUMERICAL_DISCREPANCY: Conflicting numbers/percentages for the same metric (>20% difference).
        4. SCOPE_CONTEXT_MISMATCH: Geographic, jurisdictional, or situational transposition.
        5. CREDIBILITY_ASYMMETRY: High-tier official/regulatory document refutes low-tier social rumor.
        """
        contradictions: List[Dict[str, Any]] = []
        if len(items) < 2:
            return contradictions

        # Reset contradiction flags
        for item in items:
            item.contradiction_flag = False

        # --- Axis 1 & 5: Factual Contradiction and Credibility Asymmetry ---
        denial_items: List[EvidenceItem] = []
        affirmative_items: List[EvidenceItem] = []

        for item in items:
            text = f"{item.title} {item.snippet} {item.relevant_excerpt}".lower()
            if any(p.search(text) for p in DENIAL_PATTERNS):
                denial_items.append(item)
            else:
                affirmative_items.append(item)

        for d_item in denial_items:
            d_text = f"{d_item.title} {d_item.snippet} {d_item.relevant_excerpt}"
            d_terms = subject_terms(d_text, target_name)

            for a_item in affirmative_items:
                a_text = f"{a_item.title} {a_item.snippet} {a_item.relevant_excerpt}"
                shared = subject_terms(a_text, target_name) & d_terms

                if len(shared) >= 2:
                    d_item.contradiction_flag = True
                    a_item.contradiction_flag = True
                    c_id = f"cont_fac_{len(contradictions) + 1:03d}"

                    # Check credibility asymmetry (e.g. Tier 1 / Primary vs Tier 3 / Social)
                    is_asymmetry = (
                        d_item.primary_source or d_item.source_tier == SourceTier.TIER_1_OFFICIAL_FILING.value
                    ) and (
                        a_item.source_role == SourceRole.COMMUNITY.value or a_item.source_tier == SourceTier.TIER_3_SOCIAL_SIGNALS.value
                    )

                    c_type = (
                        ContradictionType.CREDIBILITY_ASYMMETRY.value
                        if is_asymmetry
                        else ContradictionType.FACTUAL_CONTRADICTION.value
                    )

                    explanation = (
                        f"Official primary source '{d_item.source_name}' explicitly denies/refutes claim circulating on community/social source '{a_item.source_name}'."
                        if is_asymmetry
                        else f"Possible factual disagreement: '{d_item.source_name}' explicitly refutes/denies the premise reported by '{a_item.source_name}' on shared subject '{' '.join(list(shared)[:3])}'."
                    )

                    contradictions.append({
                        "contradiction_id": c_id,
                        "type": c_type,
                        "statement_a": a_item.title,
                        "source_a": a_item.source_name,
                        "source_a_id": a_item.id,
                        "statement_b": d_item.title,
                        "source_b": d_item.source_name,
                        "source_b_id": d_item.id,
                        "shared_terms": sorted(list(shared)),
                        "explanation": explanation,
                        "severity": "HIGH" if (d_item.primary_source or is_asymmetry) else "MEDIUM"
                    })

        # --- Axis 2: Temporal Divergence (Outdated Narrative) ---
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                it1, it2 = items[i], items[j]
                t1 = f"{it1.title} {it1.snippet}".lower()
                t2 = f"{it2.title} {it2.snippet}".lower()
                
                shared_subj = subject_terms(t1, target_name) & subject_terms(t2, target_name)
                if len(shared_subj) >= 2:
                    has_temporal1 = any(p.search(t1) for p in TEMPORAL_SHIFT_PATTERNS)
                    has_temporal2 = any(p.search(t2) for p in TEMPORAL_SHIFT_PATTERNS)
                    if has_temporal1 or has_temporal2:
                        newer = it2 if (it2.published_at or "") > (it1.published_at or "") else it1
                        older = it1 if newer is it2 else it2
                        c_id = f"cont_tmp_{len(contradictions) + 1:03d}"
                        it1.contradiction_flag = True
                        it2.contradiction_flag = True
                        contradictions.append({
                            "contradiction_id": c_id,
                            "type": ContradictionType.TEMPORAL_DIVERGENCE.value,
                            "statement_a": older.title,
                            "source_a": older.source_name,
                            "source_a_id": older.id,
                            "statement_b": newer.title,
                            "source_b": newer.source_name,
                            "source_b_id": newer.id,
                            "explanation": f"Temporal divergence: status/narrative in '{older.source_name}' was superseded or recognized as historical context by '{newer.source_name}'.",
                            "severity": "HIGH" if newer.primary_source else "MEDIUM"
                        })

        # --- Axis 3: Numerical Discrepancy ---
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                it1, it2 = items[i], items[j]
                facts1 = extract_numeric_facts(f"{it1.title} {it1.snippet}")
                facts2 = extract_numeric_facts(f"{it2.title} {it2.snippet}")
                
                if facts1 and facts2:
                    shared_subj = subject_terms(f"{it1.title} {it1.snippet}", target_name) & subject_terms(f"{it2.title} {it2.snippet}", target_name)
                    if len(shared_subj) >= 2:
                        for f1 in facts1:
                            for f2 in facts2:
                                v1 = f1["normalized_value"]
                                v2 = f2["normalized_value"]
                                if v1 > 0 and v2 > 0 and f1["unit"] == f2["unit"]:
                                    ratio = max(v1, v2) / min(v1, v2)
                                    if ratio > 1.25:  # > 25% discrepancy
                                        c_id = f"cont_num_{len(contradictions) + 1:03d}"
                                        it1.contradiction_flag = True
                                        it2.contradiction_flag = True
                                        contradictions.append({
                                            "contradiction_id": c_id,
                                            "type": ContradictionType.NUMERICAL_DISCREPANCY.value,
                                            "statement_a": f"{it1.title} ({f1['raw_text']})",
                                            "source_a": it1.source_name,
                                            "source_a_id": it1.id,
                                            "statement_b": f"{it2.title} ({f2['raw_text']})",
                                            "source_b": it2.source_name,
                                            "source_b_id": it2.id,
                                            "discrepancy_ratio": round(ratio, 2),
                                            "explanation": f"Numerical discrepancy on shared subject: '{it1.source_name}' reports {f1['raw_text']} vs '{it2.source_name}' reports {f2['raw_text']} ({round((ratio-1)*100)}% discrepancy).",
                                            "severity": "HIGH"
                                        })
                                        break

        # --- Axis 4: Scope / Context Mismatch ---
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                it1, it2 = items[i], items[j]
                t1 = f"{it1.title} {it1.snippet}".lower()
                t2 = f"{it2.title} {it2.snippet}".lower()
                shared_subj = subject_terms(t1, target_name) & subject_terms(t2, target_name)
                if len(shared_subj) >= 2:
                    # Look for opposing location scopes (e.g., Europe vs US, or State A vs State B)
                    locs1 = set(re.findall(r'\b(?:ohio|florida|texas|california|china|europe|us|uk|india)\b', t1))
                    locs2 = set(re.findall(r'\b(?:ohio|florida|texas|california|china|europe|us|uk|india)\b', t2))
                    if locs1 and locs2 and not (locs1 & locs2):
                        c_id = f"cont_scp_{len(contradictions) + 1:03d}"
                        it1.contradiction_flag = True
                        it2.contradiction_flag = True
                        contradictions.append({
                            "contradiction_id": c_id,
                            "type": ContradictionType.SCOPE_CONTEXT_MISMATCH.value,
                            "statement_a": f"{it1.title} (Scope: {', '.join(locs1)})",
                            "source_a": it1.source_name,
                            "source_a_id": it1.id,
                            "statement_b": f"{it2.title} (Scope: {', '.join(locs2)})",
                            "source_b": it2.source_name,
                            "source_b_id": it2.id,
                            "explanation": f"Scope/context mismatch: incident/claim attributed to '{', '.join(locs1)}' by '{it1.source_name}' but '{', '.join(locs2)}' by '{it2.source_name}'.",
                            "severity": "MEDIUM"
                        })

        return contradictions

    def evaluate_claim(
        self,
        claim: AtomicClaim,
        evidence_items: List[EvidenceItem]
    ) -> AtomicClaim:
        """
        Evaluates an individual atomic claim against acquired evidence items:
        - Links citations (evidence_id, url, source_name, role, excerpt).
        - Computes calibrated confidence and non-binary verdict.
        """
        if not evidence_items:
            claim.verdict = ClaimVerdict.INSUFFICIENT_EVIDENCE.value
            claim.confidence = 0.0
            claim.rationale = "Zero acquired evidence items available for verification. Never fabricating results."
            claim.supporting_evidence_ids = []
            claim.contradicting_evidence_ids = []
            claim.evidence_citations = []
            return claim

        claim_text = claim.claim_text.lower()
        c_terms = subject_terms(claim_text, claim.entity)

        supporting_ids: List[str] = []
        contradicting_ids: List[str] = []
        citations: List[Dict[str, Any]] = []

        primary_corroboration = 0
        secondary_corroboration = 0
        community_signals = 0
        denial_detected = False
        temporal_shift_detected = False

        for item in evidence_items:
            ev_text = f"{item.title} {item.snippet} {item.relevant_excerpt}".lower()
            ev_terms = subject_terms(ev_text, claim.entity)
            shared = c_terms & ev_terms

            # If evidence discusses the same entity/event
            if len(shared) >= 1 or (claim.entity.lower() in ev_text and len(ev_terms) > 0):
                # Check for explicit denial or debunking
                is_denial = any(p.search(ev_text) for p in DENIAL_PATTERNS)
                is_temporal = any(p.search(ev_text) for p in TEMPORAL_SHIFT_PATTERNS)

                citation_entry = {
                    "evidence_id": item.id,
                    "canonical_url": item.canonical_url,
                    "source_name": item.source_name,
                    "source_role": item.source_role,
                    "source_tier": item.source_tier,
                    "primary_source": item.primary_source,
                    "published_at": item.published_at or "Recent",
                    "relevant_excerpt": item.relevant_excerpt[:200] if item.relevant_excerpt else item.snippet[:200],
                }
                citations.append(citation_entry)

                if is_denial:
                    denial_detected = True
                    contradicting_ids.append(item.id)
                elif is_temporal:
                    temporal_shift_detected = True
                    contradicting_ids.append(item.id)
                else:
                    supporting_ids.append(item.id)

                if item.primary_source or item.source_tier == SourceTier.TIER_1_OFFICIAL_FILING.value:
                    primary_corroboration += 1
                elif item.source_role == SourceRole.SECONDARY.value:
                    secondary_corroboration += 1
                else:
                    community_signals += 1

        claim.supporting_evidence_ids = supporting_ids
        claim.contradicting_evidence_ids = contradicting_ids
        claim.evidence_citations = citations

        # Epistemic Decision Engine
        if not citations:
            claim.verdict = ClaimVerdict.INSUFFICIENT_EVIDENCE.value
            claim.confidence = 0.0
            claim.rationale = "No retrieved evidence items matched the factual proposition of this claim."
            return claim

        if denial_detected and primary_corroboration > 0:
            claim.verdict = ClaimVerdict.REFUTED.value
            claim.confidence = min(0.98, round(0.85 + 0.04 * primary_corroboration, 2))
            claim.rationale = f"Claim refuted by {primary_corroboration} authoritative primary/official source(s) with explicit denial language."
        elif denial_detected:
            claim.verdict = ClaimVerdict.REFUTED.value
            claim.confidence = 0.82
            claim.rationale = "Claim contradicts reporting that contains explicit debunking or denial statements."
        elif temporal_shift_detected:
            claim.verdict = ClaimVerdict.OUTDATED.value
            claim.confidence = 0.88
            claim.rationale = "Evidence indicates the claimed event/status was historical or has been superseded by subsequent updates."
        elif supporting_ids and contradicting_ids:
            claim.verdict = ClaimVerdict.MIXED.value
            claim.confidence = 0.55
            claim.rationale = "Conflicting evidence retrieved across monitored channels without definitive authoritative resolution."
        elif primary_corroboration >= 2:
            claim.verdict = ClaimVerdict.SUPPORTED.value
            claim.confidence = min(0.96, round(0.85 + 0.03 * primary_corroboration, 2))
            claim.rationale = f"Strongly corroborated by {primary_corroboration} independent primary/official sources with no contradictions."
        elif primary_corroboration == 1 and secondary_corroboration >= 1:
            claim.verdict = ClaimVerdict.SUPPORTED.value
            claim.confidence = 0.88
            claim.rationale = "Corroborated by primary source and verified secondary reporting."
        elif secondary_corroboration >= 2:
            claim.verdict = ClaimVerdict.SUPPORTED.value
            claim.confidence = 0.78
            claim.rationale = "Corroborated by multiple secondary journalistic sources."
        elif community_signals >= 1 and primary_corroboration == 0 and secondary_corroboration == 0:
            claim.verdict = ClaimVerdict.UNVERIFIED.value
            claim.confidence = min(0.40, round(0.20 + 0.05 * community_signals, 2))
            claim.rationale = "Claim circulating solely across unverified community/social channels without primary corroboration."
        else:
            claim.verdict = ClaimVerdict.UNVERIFIED.value
            claim.confidence = 0.45
            claim.rationale = "Sparse corroboration retrieved; claim remains unverified pending independent confirmation."

        return claim

    def synthesize_intelligence(
        self,
        text_or_claims: Union[str, List[AtomicClaim]],
        evidence_items: List[EvidenceItem],
        target_name: str = ""
    ) -> Dict[str, Any]:
        """
        Full end-to-end intelligence synthesis:
        - Decomposes text into atomic claims (if string).
        - Runs 5-dimension contradiction detector.
        - Evaluates each claim with exact citations and calibrated confidence.
        - Produces unified synthesis payload.
        """
        if isinstance(text_or_claims, str):
            claims = self.decompose_claims(text_or_claims)
        else:
            claims = text_or_claims

        contradictions = self.detect_contradictions(evidence_items, target_name=target_name, claims=claims)
        evaluated_claims = [self.evaluate_claim(c, evidence_items) for c in claims]

        # Epistemic counts
        counts: Dict[str, int] = {}
        for c in evaluated_claims:
            counts[c.verdict] = counts.get(c.verdict, 0) + 1

        # Aggregate verdict
        if not evaluated_claims or all(c.verdict == ClaimVerdict.INSUFFICIENT_EVIDENCE.value for c in evaluated_claims):
            overall_verdict = ClaimVerdict.INSUFFICIENT_EVIDENCE.value
            overall_confidence = 0.0
        elif counts.get(ClaimVerdict.REFUTED.value, 0) > 0:
            overall_verdict = ClaimVerdict.REFUTED.value
            overall_confidence = max(c.confidence for c in evaluated_claims if c.verdict == ClaimVerdict.REFUTED.value)
        elif counts.get(ClaimVerdict.OUTDATED.value, 0) > 0:
            overall_verdict = ClaimVerdict.OUTDATED.value
            overall_confidence = max(c.confidence for c in evaluated_claims if c.verdict == ClaimVerdict.OUTDATED.value)
        elif counts.get(ClaimVerdict.MIXED.value, 0) > 0:
            overall_verdict = ClaimVerdict.MIXED.value
            overall_confidence = 0.55
        elif counts.get(ClaimVerdict.SUPPORTED.value, 0) > 0 and counts.get(ClaimVerdict.UNVERIFIED.value, 0) == 0:
            overall_verdict = ClaimVerdict.SUPPORTED.value
            overall_confidence = round(sum(c.confidence for c in evaluated_claims) / max(1, len(evaluated_claims)), 2)
        elif counts.get(ClaimVerdict.UNVERIFIED.value, 0) > 0:
            overall_verdict = ClaimVerdict.UNVERIFIED.value
            overall_confidence = min(c.confidence for c in evaluated_claims)
        else:
            overall_verdict = ClaimVerdict.UNVERIFIED.value
            overall_confidence = 0.50

        # Unique citation list
        seen_urls = set()
        deduped_citations = []
        for c in evaluated_claims:
            for cit in c.evidence_citations:
                u = cit.get("canonical_url") or cit.get("evidence_id")
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    deduped_citations.append(cit)

        return {
            "overall_verdict": overall_verdict,
            "overall_confidence": overall_confidence,
            "claims": [c.to_dict() for c in evaluated_claims],
            "contradictions": contradictions,
            "contradiction_count": len(contradictions),
            "citations": deduped_citations,
            "epistemic_breakdown": counts,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }


claim_intelligence_engine = ClaimIntelligenceEngine()
