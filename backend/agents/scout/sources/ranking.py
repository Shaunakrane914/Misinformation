"""
Aegis Protocol — Scout Hard Gates & Candidate Ranking Engine
============================================================
Implements:
1. Strict Hard Rejection Gates (Platform scope, URL structure, domain blacklist, anti-token-cheat).
2. Multi-axis semantic scoring tensor.
3. Top-5 default candidate ranking based on empirical benchmark findings.
"""

import re
import urllib.parse
from typing import List, Optional, Tuple
from backend.agents.scout.sources.models import (
    CandidateSource,
    ScoutFailureCode,
    ScoutSourceRequest,
)
from backend.services.agent_reach.native.source_discovery import (
    NON_SOCIAL_DOMAINS,
    TWITTER_RESERVED_PATHS,
    check_entity_semantic_match,
)


class ScoutRankingEngine:
    """
    Evaluates hard gates and ranks candidate sources semantically.
    """

    def apply_hard_gates(
        self,
        candidate: CandidateSource,
        request: ScoutSourceRequest
    ) -> Tuple[bool, Optional[ScoutFailureCode], str]:
        """
        Enforce strict non-negotiable rejection criteria.
        Returns:
            (passes_bool, failure_code_or_None, reason_str)
        """
        parsed = urllib.parse.urlparse(candidate.canonical_url)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower().strip("/")
        parts = [p for p in path.split("/") if p]

        # Gate 1: Non-Social Domain Filter on Social Tasks
        if request.platform_hint in ("reddit", "twitter") or (request.requested_scope and "r/" in request.requested_scope):
            if any(ns in netloc for ns in NON_SOCIAL_DOMAINS):
                return False, ScoutFailureCode.DOMAIN_REJECTED, f"Corporate/non-social domain '{netloc}' rejected for social search."

        # Gate 2: Reddit Platform Scope & URL Structure
        if candidate.platform == "reddit" or "reddit.com" in netloc:
            # Scope check
            if request.requested_scope and "r/" in request.requested_scope:
                req_sub = request.requested_scope.replace("r/", "").lower().strip()
                cand_sub = (candidate.subreddit or "").lower().strip()
                if cand_sub and cand_sub != req_sub:
                    return False, ScoutFailureCode.SOURCE_SCOPE_MISMATCH, f"Candidate subreddit 'r/{cand_sub}' does not match requested 'r/{req_sub}'."

            # Structure check: Must be /comments/<id> unless explicit subreddit overview requested
            if not any(p == "comments" for p in parts):
                return False, ScoutFailureCode.INVALID_URL_STRUCTURE, f"Reddit URL '{candidate.canonical_url}' lacks '/comments/<id>' content anchor."

        # Gate 3: X / Twitter Handle Scope & URL Structure
        if candidate.platform == "twitter" or any(s in netloc for s in ("x.com", "twitter.com")):
            # Handle scope check
            if request.requested_author:
                req_h = request.requested_author.lstrip("@").lower().strip()
                cand_h = (candidate.handle or "").lstrip("@").lower().strip()
                if cand_h and cand_h != req_h:
                    return False, ScoutFailureCode.SOURCE_SCOPE_MISMATCH, f"X handle '@{cand_h}' does not match requested '@{req_h}'."

            # Reserved non-content paths (settings, home, explore, etc.)
            if parts and parts[0] in TWITTER_RESERVED_PATHS:
                return False, ScoutFailureCode.INVALID_URL_STRUCTURE, f"X URL belongs to reserved non-content path '{parts[0]}'."

            # Structure check: Must be /status/<id> unless profile requested
            if not any(p == "status" for p in parts) and candidate.source_type != "profile":
                return False, ScoutFailureCode.INVALID_URL_STRUCTURE, f"X URL '{candidate.canonical_url}' lacks '/status/<id>' status anchor."

        # Gate 4: Anti-Token-Cheat Protection
        if request.target_entity:
            text = f"{candidate.title} {candidate.snippet}".lower()
            matched, weight = check_entity_semantic_match(text, request.target_entity)
            if not matched and weight == 0:
                # If target entity was specified and entity match failed completely
                return False, ScoutFailureCode.TOKEN_CHEAT_REJECTED, f"Candidate failed multi-token disambiguation for entity '{request.target_entity}'."

        return True, None, "PASS"

    def rank_candidates(
        self,
        candidates: List[CandidateSource],
        request: ScoutSourceRequest
    ) -> List[CandidateSource]:
        """
        Filter candidates through hard gates and rank remainder using multi-axis tensor.
        Selects Top 5 by default.
        """
        valid_candidates: List[CandidateSource] = []

        for cand in candidates:
            passes, code, reason = self.apply_hard_gates(cand, request)
            if passes:
                # Compute composite score
                cand.candidate_score = self._compute_score(cand, request)
                valid_candidates.append(cand)

        # Sort descending by composite score
        valid_candidates.sort(key=lambda c: c.candidate_score, reverse=True)

        # Candidate depth: Default Top-5
        depth = request.max_candidates or 5
        return valid_candidates[:depth]

    def _compute_score(self, cand: CandidateSource, request: ScoutSourceRequest) -> float:
        score = 0.50
        text = f"{cand.title} {cand.snippet}".lower()

        # Entity co-occurrence
        if request.target_entity:
            matched, weight = check_entity_semantic_match(text, request.target_entity)
            score += 0.20 * weight

        # Ticker match
        for ticker in request.tickers:
            t = ticker.lower()
            if t in text or f"${t}" in text:
                score += 0.15

        # Primary source bonus
        if cand.platform == "primary_filing" or "sec.gov" in cand.canonical_url or "investor." in cand.canonical_url:
            score += 0.25

        # Query term density
        q_words = [w for w in request.query.lower().split() if len(w) > 3]
        overlap = sum(1 for w in q_words if w in text)
        if q_words:
            score += 0.15 * (overlap / len(q_words))

        # Search rank penalty (gentle dampening for deeper ranks)
        score -= min(0.10, 0.01 * (cand.discovery_rank - 1))

        return max(0.10, min(0.99, score))


scout_ranking_engine = ScoutRankingEngine()
