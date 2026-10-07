"""
Aegis Protocol — Hard Relevance Gate & Provenance Validation Engine
====================================================================
Operates strictly BEFORE finding synthesis to prevent semantically
contaminated evidence (e.g. credit scores in Nike brand scans, bank portals
in NVDA semiconductor scans, or medical trials in tech claims) from entering
the evidence pool or being synthesized into findings.

Evaluates every evidence item deterministically:
- Direct entity matching in title, snippet, and canonical URL
- Domain-aware entity aliases and core terminology
- Strict negative domain heuristic rejection
- Full provenance recording: preserves accepted and rejected evidence
"""

import re
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict

# Known entity alias dictionary for high-precision entity resolution
KNOWN_ENTITY_ALIASES: Dict[str, Dict[str, Any]] = {
    "nike": {
        "aliases": ["nike", "air max", "jordan", "swoosh", "sneaker", "dunk", "air force 1"],
        "negative_terms": ["cibil", "credit score", "bankbazaar", "paisabazaar", "cibil score", "loan approval", "equifax", "experian report"],
        "domain_type": "brand"
    },
    "nvda": {
        "aliases": ["nvidia", "nvda", "blackwell", "jensen", "jensen huang", "geforce", "gpu", "semiconductor", "cuda"],
        "negative_terms": ["bank of baroda", "unesco", "teams tenant", "microsoft teams", "xiaomi", "charging", "kiosk", "mortgage", "world heritage list"],
        "domain_type": "financial"
    },
    "nvidia": {
        "aliases": ["nvidia", "nvda", "blackwell", "jensen", "jensen huang", "geforce", "gpu", "semiconductor", "cuda"],
        "negative_terms": ["bank of baroda", "unesco", "teams tenant", "microsoft teams", "xiaomi", "charging", "kiosk", "mortgage", "world heritage list"],
        "domain_type": "financial"
    },
    "tesla": {
        "aliases": ["tesla", "tsla", "elon", "elon musk", "robotaxi", "musk", "fsd", "cybertruck", "gigafactory"],
        "negative_terms": ["recipe", "fashion week", "horoscope", "cricket score"],
        "domain_type": "financial"
    },
    "tsla": {
        "aliases": ["tesla", "tsla", "elon", "elon musk", "robotaxi", "musk", "fsd", "cybertruck", "gigafactory"],
        "negative_terms": ["recipe", "fashion week", "horoscope", "cricket score"],
        "domain_type": "financial"
    },
    "sam altman": {
        "aliases": ["sam altman", "altman", "openai", "sama", "@sama", "samuel altman"],
        "negative_terms": ["google chrome", "chrome download", "download chrome", "chrome support", "printer driver", "samsung galaxy", "zhihu.com"],
        "domain_type": "personal"
    },
    "whatsapp": {
        "aliases": ["whatsapp", "red ticks", "three ticks", "tick", "meta", "messaging app"],
        "negative_terms": ["glycemic", "endocrine", "diabetes", "insulin", "oncology", "clinical trial", "blood sugar", "therapeutic efficacy", "chemotherapy"],
        "domain_type": "fact_check"
    },
    "ai regulation": {
        "aliases": ["ai regulation", "artificial intelligence", "eu ai act", "regulation", "ai policy", "white house executive order"],
        "negative_terms": ["recipe", "horoscope", "cricket score", "glycemic", "skin care", "dietary supplement"],
        "domain_type": "general"
    }
}


@dataclass
class RelevanceAssessment:
    evidence_id: str
    relevance_score: float                  # 0.0 to 1.0
    relevance_class: str                    # DIRECT | RELATED | WEAK | UNRELATED | REJECTED
    is_accepted: bool
    matched_entities: List[str] = field(default_factory=list)
    matched_terms: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    title: str = ""
    url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RelevanceGate:
    """
    Deterministic hybrid gate ensuring that only verifiably relevant evidence
    survives to deep reading and grounded finding synthesis.
    """

    def __init__(self, acceptance_threshold: float = 0.35):
        self.acceptance_threshold = acceptance_threshold

    def _resolve_target_profile(self, target: str) -> Dict[str, Any]:
        """Resolve aliases and negative terms for a target entity."""
        t_clean = target.lower().strip()
        
        # Check direct alias dictionary
        for key, profile in KNOWN_ENTITY_ALIASES.items():
            if key in t_clean or t_clean in key:
                return profile

        # Dynamic fallback generation from target string
        words = [w for w in re.split(r'[^a-zA-Z0-9]', t_clean) if len(w) >= 3]
        return {
            "aliases": [target.lower()] + words,
            "negative_terms": [],
            "domain_type": "general"
        }

    def evaluate_item(
        self,
        item: Any,
        target_entity: str,
        domain: str = "general"
    ) -> RelevanceAssessment:
        """
        Evaluate a single candidate EvidenceItem or dict.
        """
        if isinstance(item, dict):
            e_id = item.get("id") or item.get("evidence_id") or "ev_unknown"
            title = (item.get("title") or item.get("headline") or "").strip()
            snippet = (item.get("relevant_excerpt") or item.get("snippet") or item.get("content") or "").strip()
            url = item.get("canonical_url") or item.get("url") or ""
        else:
            e_id = getattr(item, "id", None) or getattr(item, "evidence_id", "ev_unknown")
            title = (getattr(item, "title", None) or getattr(item, "headline", "") or "").strip()
            snippet = (getattr(item, "relevant_excerpt", None) or getattr(item, "snippet", None) or getattr(item, "content", "") or "").strip()
            url = getattr(item, "canonical_url", None) or getattr(item, "url", "") or ""
        
        combined_text = f"{title} {snippet} {url}".lower()
        title_lower = title.lower()

        profile = self._resolve_target_profile(target_entity)
        aliases = profile.get("aliases", [target_entity.lower()])
        negatives = profile.get("negative_terms", [])

        # 1. Hard Negative Check (Immediate rejection)
        for neg in negatives:
            if neg in combined_text:
                return RelevanceAssessment(
                    evidence_id=e_id,
                    relevance_score=0.05,
                    relevance_class="REJECTED",
                    is_accepted=False,
                    rejection_reason=f"Matches known off-topic contamination marker: '{neg}'",
                    title=title,
                    url=url
                )

        # Domain-specific cross-domain contaminations:
        # If technical / tech rumor, reject medical trial jargon unless claim is medical
        if domain in ("fact_check", "trending", "technical", "financial", "brand"):
            is_medical_claim = any(m in target_entity.lower() for m in ["cancer", "diabetes", "cure", "health", "disease", "vaccine", "medicine"])
            if not is_medical_claim:
                medical_jargon = ["glycemic efficacy", "endocrine society", "peer-reviewed clinical trials", "blood glucose", "placebo-controlled trial"]
                for med in medical_jargon:
                    if med in combined_text:
                        return RelevanceAssessment(
                            evidence_id=e_id,
                            relevance_score=0.02,
                            relevance_class="REJECTED",
                            is_accepted=False,
                            rejection_reason=f"Unrelated clinical/medical terminology ('{med}') in non-medical claim",
                            title=title,
                            url=url
                        )

        # 2. Entity / Alias Matching
        matched_aliases = [a for a in aliases if a in combined_text]
        matched_in_title = [a for a in aliases if a in title_lower]
        
        # Domain token matching (specific key nouns from target)
        target_tokens = [w for w in re.split(r'[^a-zA-Z0-9]', target_entity.lower()) if len(w) >= 4]
        token_matches = [t for t in target_tokens if t in combined_text]

        # 3. Calculate Normalized Relevance Score
        score = 0.0
        if matched_in_title:
            score += 0.60
        if matched_aliases:
            score += 0.25
        if len(token_matches) >= 2:
            score += 0.15
        elif len(token_matches) == 1:
            score += 0.05

        # Check URL domain alignment
        domain_name = urllib.parse.urlparse(url).netloc.lower() if url else ""
        if any(a.replace(" ", "") in domain_name for a in aliases):
            score = min(1.0, score + 0.20)

        score = round(min(1.0, max(0.0, score)), 3)

        # 4. Classify
        if score >= 0.80 and matched_in_title:
            rel_class = "DIRECT"
        elif score >= 0.50:
            rel_class = "RELATED"
        elif score >= self.acceptance_threshold:
            rel_class = "WEAK"
        else:
            rel_class = "UNRELATED"

        is_acc = score >= self.acceptance_threshold

        reason = None
        if not is_acc:
            reason = f"Insufficient entity relevance score ({score} < {self.acceptance_threshold}); zero target entity tokens matched in title."

        return RelevanceAssessment(
            evidence_id=e_id,
            relevance_score=score,
            relevance_class=rel_class,
            is_accepted=is_acc,
            matched_entities=matched_aliases,
            matched_terms=token_matches,
            rejection_reason=reason,
            title=title,
            url=url
        )

    def filter_candidates(
        self,
        candidates: List[Any],
        target_entity: str,
        domain: str = "general"
    ) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """
        Partition candidates into accepted items and rejected audit records.
        Updates item metadata with relevance assessment.
        """
        accepted = []
        rejected_audit = []

        for item in candidates:
            assessment = self.evaluate_item(item, target_entity=target_entity, domain=domain)
            
            # Tag metadata on object if supported
            if hasattr(item, "relevance_score"):
                item.relevance_score = assessment.relevance_score
            if hasattr(item, "metadata") and isinstance(item.metadata, dict):
                item.metadata["relevance_class"] = assessment.relevance_class
                item.metadata["relevance_score"] = assessment.relevance_score
                item.metadata["matched_entities"] = assessment.matched_entities
                item.metadata["rejection_reason"] = assessment.rejection_reason
            elif isinstance(item, dict):
                item["relevance_score"] = assessment.relevance_score
                item["relevance_class"] = assessment.relevance_class
                item["rejection_reason"] = assessment.rejection_reason

            if assessment.is_accepted:
                accepted.append(item)
            else:
                rejected_audit.append(assessment.to_dict())

        return accepted, rejected_audit


# Global singleton
relevance_gate = RelevanceGate()
