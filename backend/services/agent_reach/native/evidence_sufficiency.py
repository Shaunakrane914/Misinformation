"""
Aegis Protocol — Evidence Sufficiency Evaluator
===============================================
Evaluates whether an initial Top-5 candidate acquisition is sufficient
to support defensible domain reasoning, or whether bounded escalation
to Top-10 candidates is required.

Prevents unbounded network calls while guaranteeing epistemic robustness.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalRequest


@dataclass
class EvidenceSufficiencyResult:
    """
    Assessment result determining whether retrieval can stop at Top-5
    or must escalate to acquire candidates 6..10.
    """
    is_sufficient: bool
    reasons: List[str] = field(default_factory=list)
    should_escalate: bool = False
    independent_source_count: int = 0
    primary_source_present: bool = False
    average_score: float = 0.0
    contradictions_detected: bool = False


class EvidenceSufficiencyEvaluator:
    """
    Centrally evaluates post-acquisition evidence sufficiency.
    """

    @classmethod
    def evaluate(
        cls,
        fragments: List[EvidenceFragment],
        request: RetrievalRequest,
        remaining_candidates_count: int = 0
    ) -> EvidenceSufficiencyResult:
        if not fragments:
            return EvidenceSufficiencyResult(
                is_sufficient=False,
                reasons=["Zero evidence fragments successfully acquired"],
                should_escalate=remaining_candidates_count > 0,
            )

        reasons: List[str] = []
        should_escalate = False

        # 1. Independent source diversity (distinct domains and authors)
        unique_publishers: Set[str] = set()
        for f in fragments:
            pub = f.author or f.platform
            if f.url:
                from urllib.parse import urlparse
                domain = urlparse(f.url).netloc.lower().replace("www.", "")
                if domain:
                    pub = domain
            unique_publishers.add(pub)

        independent_count = len(unique_publishers)
        if independent_count < 2 and len(fragments) >= 2:
            reasons.append("Insufficient source independence: fewer than 2 distinct publishers")
            should_escalate = True

        # 2. Content depth check (do we only have snippets?)
        has_deep_content = any(
            f.content_depth in ("PARTIAL_CONTENT", "FULL_ARTICLE", "TRANSCRIPT", "STRUCTURED_METADATA")
            or len(f.content or "") > 350
            for f in fragments
        )
        if not has_deep_content and len(fragments) > 0:
            reasons.append("Low content depth: all acquired items are headline/search snippets")
            should_escalate = True

        # 3. Average quality / score threshold
        avg_score = sum(f.score for f in fragments) / len(fragments) if fragments else 0.0
        if avg_score < 40.0:
            reasons.append(f"Low aggregate semantic quality: average score {avg_score:.1f} < 40.0")
            should_escalate = True

        # 4. Primary source presence check for corporate/financial entities
        primary_present = any(
            f.platform in ("github", "sec_edgar")
            or "official" in (f.title or "").lower()
            or (request.entity and request.entity.lower() in (f.author or "").lower())
            for f in fragments
        )
        if request.agent == "scout" and not primary_present and len(fragments) < 4:
            reasons.append("Missing primary documentation for market intelligence request")
            should_escalate = True

        # Escalation is only actionable if remaining candidates are available
        can_escalate = should_escalate and remaining_candidates_count > 0

        return EvidenceSufficiencyResult(
            is_sufficient=not should_escalate,
            reasons=reasons if reasons else ["Evidence set meets epistemic sufficiency criteria"],
            should_escalate=can_escalate,
            independent_source_count=independent_count,
            primary_source_present=primary_present,
            average_score=round(avg_score, 1),
            contradictions_detected=False,
        )


evidence_sufficiency_evaluator = EvidenceSufficiencyEvaluator()
