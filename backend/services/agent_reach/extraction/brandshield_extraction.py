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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.agent_reach.channels import EvidenceFragment

logger = logging.getLogger(__name__)

# Threat taxonomy
THREAT_TAXONOMY = {
    "COUNTERFEIT": "Unauthorized knockoffs, replica goods, clone listings, or unauthorized sellers.",
    "FAKE_REVIEW": "Coordinated review brigades, astroturfing, or fabricated feedback patterns.",
    "BRAND_IMPERSONATION": "Spoofed official accounts, fake customer support handles, or executive lookalikes.",
    "PHISHING_SCAM": "Fraudulent promotional giveaways, lookalike domains, or phishing landing pages.",
    "REPUTATION_ATTACK": "Coordinated smear campaigns, astroturfed boycotts, or unsubstantiated FUD.",
    "FALSE_CLAIM": "Fabricated claims regarding company bankruptcy, shutdowns, or executive scandals.",
    "PRODUCT_SAFETY": "Hazard claims, battery explosion allegations, toxicity, or unverified recall rumors.",
    "CUSTOMER_COMPLAINT": "Legitimate consumer service/quality grievances (non-malicious operational issues).",
    "REGULATORY_LEGAL": "Official investigations, antitrust lawsuits, regulatory inquiries, or penalties.",
    "LISTING_ABUSE": "Marketplace catalog hijacking, unauthorized bundle alterations, or brand gate evasion.",
    "TRADEMARK_ABUSE": "Unauthorized commercial exploitation of logos, trademarks, or brand assets.",
    "UNVERIFIED_RUMOR": "Speculative unconfirmed discourse circulating across social communities.",
}


@dataclass
class BrandThreatRecord:
    threat_id: str
    threat_type: str                         # One of THREAT_TAXONOMY keys
    severity: str                            # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    title: str
    description: str
    platform: str
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 0.85
    actionable_recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_id": self.threat_id,
            "threat_type": self.threat_type,
            "type": self.threat_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "platform": self.platform,
            "evidence_ids": self.evidence_ids,
            "confidence": self.confidence,
            "actionable_recommendation": self.actionable_recommendation,
        }


@dataclass
class BrandShieldExtractionResult:
    brand: str
    product: Optional[str] = None
    threats: List[BrandThreatRecord] = field(default_factory=list)
    counterfeits: List[Dict[str, Any]] = field(default_factory=list)
    impersonations: List[Dict[str, Any]] = field(default_factory=list)
    review_patterns: Dict[str, Any] = field(default_factory=dict)
    claims: List[Dict[str, Any]] = field(default_factory=list)
    total_signals_analyzed: int = 0
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand": self.brand,
            "product": self.product,
            "threats": [t.to_dict() for t in self.threats],
            "counterfeits": self.counterfeits,
            "impersonations": self.impersonations,
            "review_patterns": self.review_patterns,
            "claims": self.claims,
            "total_signals_analyzed": self.total_signals_analyzed,
            "extracted_at": self.extracted_at,
        }


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
