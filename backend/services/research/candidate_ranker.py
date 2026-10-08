"""
Aegis Protocol — Hybrid Candidate Ranker & Reranker Engine
===========================================================
Ranks and reranks broad discovery candidates to select high-value sources for deep investigation.
Combines:
- Canonical entity exactness and disambiguation confidence
- Intent phrase and lexical match
- Institutional authority & source quality
- Freshness and recency
- Primary-source bonuses
- Syndication diversity penalties
"""

import re
from typing import Any, Dict, List, Optional, Set

from backend.services.research.entity_resolver import entity_resolver
from backend.services.research.research_models import ContentDepth, EvidenceItem, SourceRole


class CandidateReranker:
    """
    Reranker abstraction evaluating alignment between an investigation query/target
    and candidate evidence items.
    """

    def __init__(self, scoring_mechanism: str = "aegis_deterministic_reranker"):
        self.scoring_mechanism = scoring_mechanism

    def score(self, query: str, candidate: Any) -> float:
        """
        Calculates a real reranker score between query and candidate.
        Returns a float between 0.0 and 1.0.
        """
        title = getattr(candidate, "title", "") or (candidate.get("title", "") if isinstance(candidate, dict) else "")
        snippet = getattr(candidate, "snippet", "") or getattr(candidate, "content", "") or (candidate.get("snippet", "") if isinstance(candidate, dict) else "")
        url = getattr(candidate, "canonical_url", "") or getattr(candidate, "url", "") or (candidate.get("url", "") if isinstance(candidate, dict) else "")
        combined = f"{title} {snippet} {url}".strip()

        # 1. Entity resolution alignment
        target_profile = entity_resolver.resolve_entity(query)
        ent_score, _, entity_rejection = entity_resolver.evaluate_entity_match(combined, target_profile)
        if entity_rejection or ent_score < 0.35:
            return round(max(0.02, ent_score * 0.3), 3)

        # 2. Lexical & intent overlap
        words = [w.lower() for w in re.findall(r'[a-zA-Z0-9]+', query) if len(w) >= 3]
        matched_words = sum(1 for w in words if w in combined.lower())
        lex_ratio = matched_words / len(words) if words else 0.50

        # 3. Source quality indicator
        sq = 0.50
        if isinstance(candidate, dict):
            sq = candidate.get("source_quality_score", 0.50)
        else:
            sq = getattr(candidate, "source_quality_score", 0.50)

        # Composite score
        final_score = (ent_score * 0.50) + (lex_ratio * 0.30) + (sq * 0.20)
        return round(min(1.0, max(0.0, final_score)), 3)


class CandidateRanker(CandidateReranker):
    """
    Full pipeline ranker sorting candidates by composite utility tensor.
    """

    def __init__(self):
        super().__init__(scoring_mechanism="aegis_hybrid_ranker")

    def _compute_relevance(self, item: EvidenceItem, target_name: str, intent: str = "") -> float:
        """Compute keyword and entity alignment score (0.0 to 1.0)."""
        text = f"{item.title} {item.snippet} {item.relevant_excerpt} {item.canonical_url}".strip()
        if not text:
            return 0.20

        # Use canonical entity evaluation
        target_profile = entity_resolver.resolve_entity(target_name)
        ent_score, _, ent_rej = entity_resolver.evaluate_entity_match(text, target_profile)
        if ent_rej:
            return max(0.05, ent_score)

        # Intent / query class alignment
        score = ent_score * 0.70
        if intent:
            intent_words = [w for w in re.findall(r'[a-zA-Z0-9]+', intent.lower()) if len(w) >= 4]
            intent_matches = sum(1 for w in intent_words if w in text.lower())
            if intent_words:
                score += min(0.30, 0.10 * intent_matches)

        if item.query_class and item.query_class != "general":
            score += 0.05

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
        return 0.60

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
            item.relevance_score = round(rel_score, 3)

            # 2. Recency
            rec_score = self._compute_recency(item)
            item.recency_score = round(rec_score, 3)

            # 3. Quality
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
                    syndication_penalty = 0.25
                else:
                    seen_syndication_groups.add(item.independence_group)

            # Combined deterministic score
            candidate_score = (
                (rel_score * 0.35)
                + (qual_score * 0.25)
                + (rec_score * 0.10)
                + primary_bonus
                + depth_bonus
                + uniqueness_bonus
                - syndication_penalty
            )
            item.metadata["candidate_score"] = round(candidate_score, 3)
            item.metadata["ranking_mechanism"] = self.scoring_mechanism

        # Sort descending by candidate score
        ranked = sorted(candidates, key=lambda x: x.metadata.get("candidate_score", 0.0), reverse=True)
        for rank_idx, item in enumerate(ranked):
            item.metadata["rank"] = rank_idx + 1
            if not getattr(item, "ranked_id", None):
                item.ranked_id = f"cand_rank_{item.id}"
        return ranked


candidate_ranker = CandidateRanker()
candidate_reranker = CandidateReranker()
