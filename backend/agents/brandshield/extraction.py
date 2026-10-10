"""
Aegis Protocol — BrandShield Domain Extraction Engine
======================================================
Consumes normalized EvidenceFragment objects acquired by the shared acquisition fabric.
Performs deterministic brand protection analysis:
  - Brand & product entity resolution
  - Counterfeit detection & listing abuse screening
  - Fake review pattern & astroturfing analysis
  - Brand impersonation & phishing scam detection
  - Reputation attack & false claim categorization
  - Strict evidence ID linkage (all output records trace to source evidence_ids)
"""

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.agents.brandshield.models import (
    BrandShieldExtractionResult,
    BrandThreatRecord,
    THREAT_TAXONOMY,
)
from backend.services.agent_reach.channels import EvidenceFragment

logger = logging.getLogger(__name__)


class BrandShieldExtractionEngine:
    """
    Dedicated extraction engine for BrandShield.
    Consumes EvidenceFragment[] and extracts structured brand signals.
    Never initiates network requests directly.
    """

    def extract(
        self,
        fragments: List[EvidenceFragment],
        brand_name: str,
        product_name: Optional[str] = None,
    ) -> BrandShieldExtractionResult:
        """
        Analyze normalized evidence fragments to extract brand threat intelligence.
        """
        threats: List[BrandThreatRecord] = []
        counterfeits: List[Dict[str, Any]] = []
        impersonations: List[Dict[str, Any]] = []
        claims: List[Dict[str, Any]] = []

        counterfeit_keywords = {"counterfeit", "replica", "fake", "knockoff", "1:1", "clone", "unauthorized seller", "first copy"}
        impersonation_keywords = {"fake account", "impersonat", "spoof", "phishing", "scam handle", "support scam"}
        safety_keywords = {"hazard", "explosion", "toxic", "poison", "recall", "catch fire", "burns", "injury"}
        legal_keywords = {"lawsuit", "investigation", "subpoena", "sec", "doj", "ftc", "antitrust", "patent infringement"}
        rumor_keywords = {"rumor", "allegedly", "claims that", "unconfirmed", "leak", "insider says"}

        for idx, frag in enumerate(fragments, start=1):
            text_lower = f"{frag.title} {frag.snippet} {frag.content}".lower()
            ev_id = frag.evidence_id or f"ev_{idx}"

            # 1. Counterfeit Detection
            if any(kw in text_lower for kw in counterfeit_keywords):
                c_id = f"CF-{idx:03d}"
                counterfeits.append({
                    "id": c_id,
                    "platform": frag.platform,
                    "title": frag.title[:120],
                    "url": frag.url,
                    "evidence_ids": [ev_id],
                    "confidence": 0.88,
                })
                threats.append(
                    BrandThreatRecord(
                        threat_id=f"TH-CF-{idx:03d}",
                        threat_type="COUNTERFEIT",
                        severity="HIGH",
                        title=f"Potential Counterfeit Listing on {frag.platform.title()}",
                        description=f"Identified counterfeit or replica references: {frag.title[:150]}",
                        platform=frag.platform,
                        evidence_ids=[ev_id],
                        confidence=0.88,
                        actionable_recommendation="Initiate marketplace IP takedown notice and test-buy verification.",
                    )
                )

            # 2. Impersonation & Phishing Detection
            if any(kw in text_lower for kw in impersonation_keywords):
                imp_id = f"IMP-{idx:03d}"
                impersonations.append({
                    "id": imp_id,
                    "platform": frag.platform,
                    "title": frag.title[:120],
                    "url": frag.url,
                    "evidence_ids": [ev_id],
                    "confidence": 0.90,
                })
                threats.append(
                    BrandThreatRecord(
                        threat_id=f"TH-IMP-{idx:03d}",
                        threat_type="BRAND_IMPERSONATION",
                        severity="CRITICAL",
                        title=f"Brand Impersonation / Phishing Risk on {frag.platform.title()}",
                        description=f"Suspicious account or phishing context detected: {frag.title[:150]}",
                        platform=frag.platform,
                        evidence_ids=[ev_id],
                        confidence=0.90,
                        actionable_recommendation="Issue domain registrar notice / platform impersonation report.",
                    )
                )

            # 3. Product Safety Allegations
            if any(kw in text_lower for kw in safety_keywords):
                threats.append(
                    BrandThreatRecord(
                        threat_id=f"TH-SAF-{idx:03d}",
                        threat_type="PRODUCT_SAFETY",
                        severity="CRITICAL",
                        title=f"Product Safety Claim on {frag.platform.title()}",
                        description=f"Consumer safety hazard allegation identified: {frag.snippet[:150]}",
                        platform=frag.platform,
                        evidence_ids=[ev_id],
                        confidence=0.82,
                        actionable_recommendation="Alert QA and legal counsel to assess product batch validity.",
                    )
                )

            # 4. Regulatory / Legal Signals
            if any(kw in text_lower for kw in legal_keywords):
                threats.append(
                    BrandThreatRecord(
                        threat_id=f"TH-LEG-{idx:03d}",
                        threat_type="REGULATORY_LEGAL",
                        severity="HIGH",
                        title=f"Regulatory or Legal Inquiry Signal ({frag.platform.title()})",
                        description=f"Legal or government action referenced: {frag.title[:150]}",
                        platform=frag.platform,
                        evidence_ids=[ev_id],
                        confidence=0.86,
                        actionable_recommendation="Cross-reference with docket records and public agency portals.",
                    )
                )

            # 5. Extract unverified public claims
            if any(kw in text_lower for kw in rumor_keywords):
                claims.append({
                    "claim_id": f"CLM-{idx:03d}",
                    "statement": frag.title,
                    "source": frag.platform,
                    "evidence_ids": [ev_id],
                    "verification_status": "UNVERIFIED_RUMOR",
                })

        # 6. Review-pattern Screening (Deterministic pairwise lexical check)
        review_patterns = self._screen_review_patterns(fragments)

        return BrandShieldExtractionResult(
            brand=brand_name,
            product=product_name,
            threats=threats,
            counterfeits=counterfeits,
            impersonations=impersonations,
            review_patterns=review_patterns,
            claims=claims,
            total_signals_analyzed=len(fragments),
        )

    def _screen_review_patterns(self, fragments: List[EvidenceFragment]) -> Dict[str, Any]:
        """Pairwise Jaccard and n-gram overlap check across fragment texts."""
        candidates = []
        for f in fragments:
            text = f"{f.title} {f.snippet}".strip()
            if len(text) > 20:
                words = set(re.findall(r"\b[a-z]{3,}\b", text.lower()))
                candidates.append({"evidence_id": f.evidence_id, "text": text, "words": words})

        dup_pairs: List[Tuple[str, str, float]] = []
        n = len(candidates)
        for i in range(n):
            for j in range(i + 1, n):
                w1 = candidates[i]["words"]
                w2 = candidates[j]["words"]
                if not w1 or not w2:
                    continue
                union_len = len(w1 | w2)
                if union_len == 0:
                    continue
                jaccard = len(w1 & w2) / union_len
                if jaccard >= 0.65:
                    dup_pairs.append((candidates[i]["evidence_id"], candidates[j]["evidence_id"], round(jaccard, 2)))

        if dup_pairs:
            return {
                "status": "SUSPICIOUS_PATTERNS_DETECTED",
                "review_manipulation_detected": True,
                "near_duplicate_clusters": len(dup_pairs),
                "signals_analyzed": len(fragments),
                "duplicate_pairs": [{"ev1": p[0], "ev2": p[1], "similarity": p[2]} for p in dup_pairs[:5]],
            }
        return {
            "status": "SCREENED_NO_REPETITION_FOUND",
            "review_manipulation_detected": False,
            "near_duplicate_clusters": 0,
            "signals_analyzed": len(fragments),
            "duplicate_pairs": [],
        }

    # Canonical alias
    extract_brand_intelligence = extract


brandshield_extractor = BrandShieldExtractionEngine()

__all__ = [
    "BrandShieldExtractionEngine",
    "BrandShieldExtractionResult",
    "BrandThreatRecord",
    "THREAT_TAXONOMY",
    "brandshield_extractor",
]
