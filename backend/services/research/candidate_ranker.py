"""
Aegis Protocol — Deterministic Candidate Ranker
===============================================
Ranks broad discovery candidates to select high-value sources for deep investigation.
Balances institutional authority, relevance, freshness, primary-source bonuses,
and diversity penalties for syndicated wire duplication.
"""

import re
from typing import Dict, List, Optional, Set

from backend.services.research.research_models import ContentDepth, EvidenceItem, SourceRole


class CandidateRanker:
    """Ranks candidate evidence items deterministically."""

    def __init__(self):
        pass

    def _compute_relevance(self, item: EvidenceItem, target_name: str, intent: str = "") -> float:
        """Compute keyword and intent alignment score (0.0 to 1.0)."""
        text = f"{item.title} {item.snippet} {item.relevant_excerpt}".lower()
        if not text:
            return 0.20

        score = 0.30
        # Target name alignment
        target_clean = target_name.lower().strip() if target_name else ""
        if target_clean and target_clean in text:
            score += 0.35
        elif target_clean:
            words = target_clean.split()
            matched = sum(1 for w in words if len(w) >= 3 and w in text)
            if words:
                score += 0.25 * (matched / len(words))

        # Intent / query class alignment
        if intent:
            intent_words = [w for w in intent.lower().split() if len(w) >= 4]
            intent_matches = sum(1 for w in intent_words if w in text)
            if intent_words:
                score += min(0.25, 0.10 * intent_matches)

        if item.query_class and item.query_class != "general":
            score += 0.10

        return max(0.10, min(1.0, score))

    def _compute_recency(self, item: EvidenceItem) -> float:
        """Estimate recency score from published string."""
        pub = (item.published_at or "").lower()
        if any(w in pub for w in ["minute", "hour", "today", "yesterday", "just now"]):
            return 1.0
        if "day" in pub:
            return 0.85
        if "week" in pub:
            return 0.70
        if "month" in pub:
            return 0.50
        if "year" in pub:
            return 0.30
        return 0.60  # Default assumption for search results without clear date

    def rank_candidates(
        self,
        candidates: List[EvidenceItem],
        target_name: str,
        intent: str = "",
        query_classes: Optional[List[str]] = None
    ) -> List[EvidenceItem]:
        """
        Calculates candidate_score for each candidate and returns them sorted descending.
        """
        seen_domains: Set[str] = set()
        seen_syndication_groups: Set[str] = set()

        for item in candidates:
            # 1. Relevance
            rel_score = self._compute_relevance(item, target_name, intent)
            item.relevance_score = rel_score

            # 2. Recency
            rec_score = self._compute_recency(item)
            item.recency_score = rec_score

            # 3. Quality (already computed by SourceQualityEngine or base)
            qual_score = item.source_quality_score

            # 4. Primary Source Bonus
            primary_bonus = 0.25 if (item.primary_source or item.source_role == SourceRole.PRIMARY.value) else 0.0

            # 5. Content Depth Bonus
            depth_bonus = 0.0
            if item.content_depth in (ContentDepth.FULL_ARTICLE.value, ContentDepth.PRIMARY_DOCUMENT.value):
                depth_bonus = 0.15
            elif item.content_depth == ContentDepth.PARTIAL_CONTENT.value:
                depth_bonus = 0.05
            elif item.content_depth == ContentDepth.HEADLINE_ONLY.value:
                depth_bonus = -0.10

            # 6. Uniqueness vs Syndication Penalty
            uniqueness_bonus = 0.0
            domain = item.source_domain.lower() if item.source_domain else ""
            if domain and domain not in seen_domains:
                uniqueness_bonus = 0.12
                seen_domains.add(domain)

            syndication_penalty = 0.0
            if item.independence_group and item.independence_group.startswith("wire_"):
                if item.independence_group in seen_syndication_groups:
                    # Duplicate wire copy gets heavy penalty
                    syndication_penalty = 0.25
                else:
                    seen_syndication_groups.add(item.independence_group)

            # Combined deterministic score
            candidate_score = (
                (rel_score * 0.30)
                + (qual_score * 0.25)
                + (rec_score * 0.15)
                + primary_bonus
                + depth_bonus
                + uniqueness_bonus
                - syndication_penalty
            )
            item.metadata["candidate_score"] = round(candidate_score, 3)

        # Sort descending by candidate score
        ranked = sorted(candidates, key=lambda x: x.metadata.get("candidate_score", 0.0), reverse=True)
        return ranked


candidate_ranker = CandidateRanker()
