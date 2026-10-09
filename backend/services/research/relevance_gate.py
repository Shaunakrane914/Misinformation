"""
Aegis Protocol — Hard Relevance Gate & Multi-Stage Provenance Validation Engine
================================================================================
Operates strictly BEFORE finding synthesis and deep reading to prevent semantically
contaminated evidence (e.g. Magic the Gathering cards in Microsoft investigations,
unrelated Bollywood movies or Sanskrit philosophical concepts in Satya Nadella scans)
from entering the evidence pool.

Evaluates every evidence item across dedicated orthogonal dimensions:
1. Hard Entity Gate & Multi-Word Disambiguation (entity_score)
2. Negative Context & Domain Contamination Rejection (hard negative filters)
3. Intent & Topic Alignment (intent_score)
4. Source Legitimacy & Structural Platform Validity (source_quality_score)
5. Final Acceptance Decision with stage-level rejection accounting
"""

import re
import urllib.parse
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.research.entity_resolver import (
    ACTION_VERBS,
    GENERAL_STOPWORDS,
    TargetEntity,
    entity_resolver,
)
from backend.services.research.temporal_guard import temporal_guard, TemporalAssessment


@dataclass
class RelevanceAssessment:
    evidence_id: str
    relevance_score: float                  # Composite 0.0 to 1.0
    relevance_class: str                    # DIRECT | RELATED | WEAK | UNRELATED | REJECTED
    is_accepted: bool
    entity_score: float = 0.0               # Orthogonal entity alignment
    intent_score: float = 0.0               # Orthogonal intent alignment
    source_quality_score: float = 0.50      # Orthogonal source quality
    matched_entities: List[str] = field(default_factory=list)
    matched_terms: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    rejection_stage: Optional[str] = None   # HARD_GATE_ERROR | ENTITY_RESOLUTION_ERROR | RELEVANCE_REJECTION | TEMPORAL_GATE_ERROR
    title: str = ""
    url: str = ""
    temporal_status: Optional[str] = None
    recency_score: float = 0.50

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RelevanceGate:
    """
    Deterministic multi-stage hybrid gate ensuring that only verifiably relevant,
    entity-grounded, and temporally fresh evidence survives to deep reading and grounded finding synthesis.
    """

    def __init__(
        self,
        acceptance_threshold: float = 0.35,
        trending_window_hours: float = 48.0,
        reference_time: Optional[datetime] = None,
        allow_updated: bool = False,
    ):
        self.acceptance_threshold = acceptance_threshold
        self.trending_window_hours = trending_window_hours
        self.reference_time = reference_time
        self.allow_updated = allow_updated

    def evaluate_item(
        self,
        item: Any,
        target_entity: str,
        domain: str = "general",
        intent: str = "",
        reference_time: Optional[datetime] = None,
        window_hours: Optional[float] = None,
        allow_updated: Optional[bool] = None,
    ) -> RelevanceAssessment:
        """
        Evaluate a single candidate EvidenceItem or dict.
        Separates entity matching from intent matching and applies strict hard gates.
        """
        if isinstance(item, dict):
            e_id = item.get("id") or item.get("evidence_id") or "ev_unknown"
            title = (item.get("title") or item.get("headline") or "").strip()
            snippet = (item.get("relevant_excerpt") or item.get("snippet") or item.get("content") or "").strip()
            url = item.get("canonical_url") or item.get("url") or ""
            source = item.get("source") or item.get("platform") or ""
        else:
            e_id = getattr(item, "id", None) or getattr(item, "evidence_id", "ev_unknown")
            title = (getattr(item, "title", None) or getattr(item, "headline", "") or "").strip()
            snippet = (getattr(item, "relevant_excerpt", None) or getattr(item, "snippet", None) or getattr(item, "content", "") or "").strip()
            url = getattr(item, "canonical_url", None) or getattr(item, "url", "") or ""
            source = getattr(item, "source_name", None) or getattr(item, "platform", "") or ""

        combined_text = f"{title} {snippet} {url}".strip()
        combined_lower = combined_text.lower()
        title_lower = title.lower()

        # ── Stage 1: Resolve Canonical Target Entity ──
        parsed_req = entity_resolver.parse_request(target_entity, domain=domain)
        target_profile = parsed_req.target_entity

        # ── Stage 2: Orthogonal Entity Match & Negative Disambiguation ──
        entity_score, matched_signals, entity_reject_reason = entity_resolver.evaluate_entity_match(
            combined_text, target_profile
        )

        # In fact-checking / claim verification, target_entity is often a full propositional claim rather than a single named entity
        if domain in ("fact_check", "claims"):
            claim_tokens = [w.lower() for w in re.split(r'[^a-zA-Z0-9]', target_entity) if len(w) >= 3 and w.lower() not in GENERAL_STOPWORDS and w.lower() not in ACTION_VERBS]
            matching_tokens = [t for t in claim_tokens if re.search(r'\b' + re.escape(t) + r'\b', combined_lower)]
            token_ratio = len(matching_tokens) / len(claim_tokens) if claim_tokens else 0.0
            if matching_tokens:
                entity_score = max(entity_score, min(1.0, 0.45 + token_ratio * 0.50))
                matched_signals.append(f"claim_token_match:{','.join(matching_tokens[:4])}")
                entity_reject_reason = None

        # In Trending Discovery mode, investigations target broad regional/thematic trends without a fixed single entity
        if domain == "trending" and any(target_entity.lower().startswith(p) for p in ["trending in", "trending", "what's trending", "discovery"]):
            entity_score = max(entity_score, 0.85)
            matched_signals.append("discovery_mode_topic")
            entity_reject_reason = None

        # Hard Entity Rejection: If entity score is too low or negative collision triggered
        if entity_reject_reason or entity_score < self.acceptance_threshold:
            rejection_stage = "ENTITY_RESOLUTION_ERROR" if "Ambiguous" in str(entity_reject_reason) or "first_name" in str(entity_reject_reason) else "HARD_GATE_ERROR"
            return RelevanceAssessment(
                evidence_id=e_id,
                relevance_score=entity_score,
                relevance_class="REJECTED",
                is_accepted=False,
                entity_score=entity_score,
                intent_score=0.0,
                source_quality_score=0.50,
                matched_entities=matched_signals,
                rejection_reason=entity_reject_reason or f"Failed entity gate: score {entity_score} < {self.acceptance_threshold}",
                rejection_stage=rejection_stage,
                title=title,
                url=url
            )

        # ── Stage 3: Cross-Domain Medical / Non-Tech Contamination Check ──
        if domain in ("fact_check", "trending", "technical", "financial", "brand", "personal"):
            is_medical_claim = any(m in target_entity.lower() for m in ["cancer", "diabetes", "cure", "health", "disease", "vaccine", "medicine", "infection", "antibiotic", "honey"])
            if not is_medical_claim:
                medical_jargon = ["glycemic efficacy", "endocrine society", "peer-reviewed clinical trials", "blood glucose", "placebo-controlled trial", "oncology regimen"]
                for med in medical_jargon:
                    if med in combined_lower:
                        return RelevanceAssessment(
                            evidence_id=e_id,
                            relevance_score=0.02,
                            relevance_class="REJECTED",
                            is_accepted=False,
                            entity_score=entity_score,
                            intent_score=0.0,
                            source_quality_score=0.10,
                            rejection_reason=f"Unrelated clinical/medical terminology ('{med}') in non-medical investigation",
                            rejection_stage="HARD_GATE_ERROR",
                            title=title,
                            url=url
                        )

        # ── Stage 3b: Trending Temporal Freshness & Eligibility Gate ──
        temporal_assessment = None
        if domain == "trending":
            ref_t = reference_time if reference_time is not None else self.reference_time
            win_h = window_hours if window_hours is not None else self.trending_window_hours
            allow_upd = allow_updated if allow_updated is not None else self.allow_updated
            temporal_assessment = temporal_guard.evaluate(
                item,
                reference_time=ref_t,
                window_hours=win_h,
                allow_updated=allow_upd,
            )

            # Store temporal telemetry in candidate metadata
            if hasattr(item, "metadata") and isinstance(item.metadata, dict):
                item.metadata["temporal_assessment"] = temporal_assessment.to_dict()
                item.metadata["temporal_eligible"] = temporal_assessment.is_eligible
                item.metadata["temporal_status"] = temporal_assessment.status
                item.metadata["recency_score"] = temporal_assessment.recency_score
            elif isinstance(item, dict):
                item["temporal_assessment"] = temporal_assessment.to_dict()
                item["temporal_eligible"] = temporal_assessment.is_eligible
                item["temporal_status"] = temporal_assessment.status
                item["recency_score"] = temporal_assessment.recency_score

            if not temporal_assessment.is_eligible:
                return RelevanceAssessment(
                    evidence_id=e_id,
                    relevance_score=0.0,
                    relevance_class="REJECTED",
                    is_accepted=False,
                    entity_score=entity_score,
                    intent_score=0.0,
                    source_quality_score=0.50,
                    matched_entities=matched_signals,
                    rejection_reason=temporal_assessment.rejection_reason,
                    rejection_stage="TEMPORAL_GATE_ERROR",
                    title=title,
                    url=url,
                    temporal_status=temporal_assessment.status,
                    recency_score=temporal_assessment.recency_score,
                )

        # ── Stage 4: Orthogonal Intent Scoring ──
        intent_score = 0.50  # Neutral base
        intent_text = intent or target_entity
        intent_tokens = [
            w.lower() for w in re.findall(r'[a-zA-Z0-9]+', intent_text)
            if len(w) >= 4 and w.lower() not in GENERAL_STOPWORDS and w.lower() not in ACTION_VERBS
        ]
        matched_intent_terms = [t for t in intent_tokens if t in combined_lower]

        if intent_tokens:
            intent_ratio = len(matched_intent_terms) / len(intent_tokens)
            intent_score = round(min(1.0, 0.30 + 0.70 * intent_ratio), 3)

        # Boost intent if domain-specific threat/financial terms appear
        if domain == "brand":
            threat_terms = ["counterfeit", "fake", "phishing", "scam", "impersonation", "recall", "lawsuit", "complaint", "vulnerability"]
            if any(t in combined_lower for t in threat_terms):
                intent_score = min(1.0, intent_score + 0.25)
        elif domain == "financial":
            fin_terms = ["earnings", "revenue", "guidance", "stock", "shares", "sec", "10-k", "10-q", "quarter", "operating margin"]
            if any(t in combined_lower for t in fin_terms):
                intent_score = min(1.0, intent_score + 0.25)

        # ── Stage 5: Source Quality & Platform Structure Check ──
        sq_score = 0.60
        domain_name = urllib.parse.urlparse(url).netloc.lower() if url else ""
        if domain_name:
            if any(ext in domain_name for ext in [".gov", ".edu", "sec.gov", "microsoft.com", "reuters.com", "bloomberg.com", "wsj.com", "cnbc.com"]):
                sq_score = 0.95
            elif any(plat in domain_name for plat in ["x.com", "twitter.com", "reddit.com", "youtube.com"]):
                sq_score = 0.85
            elif "stackoverflow.com" in domain_name or "zhihu.com" in domain_name:
                sq_score = 0.40  # Generic developer / Q&A forums penalized unless tech domain

        # ── Stage 6: Calculate Composite Relevance Score ──
        # Formula: 50% entity match, 35% intent match, 15% source quality
        composite_score = round(0.50 * entity_score + 0.35 * intent_score + 0.15 * sq_score, 3)

        # Classify
        if composite_score >= 0.80 and any("canonical_phrase" in s or "token_cooccurrence" in s for s in matched_signals):
            rel_class = "DIRECT"
        elif composite_score >= 0.55:
            rel_class = "RELATED"
        elif composite_score >= self.acceptance_threshold:
            rel_class = "WEAK"
        else:
            rel_class = "UNRELATED"

        is_acc = composite_score >= self.acceptance_threshold and entity_score >= self.acceptance_threshold

        reason = None
        rejection_stage = None
        if not is_acc:
            reason = f"Composite relevance score below threshold ({composite_score} < {self.acceptance_threshold})"
            rejection_stage = "SEMANTIC_RANKING_ERROR"

        return RelevanceAssessment(
            evidence_id=e_id,
            relevance_score=composite_score,
            relevance_class=rel_class,
            is_accepted=is_acc,
            entity_score=entity_score,
            intent_score=intent_score,
            source_quality_score=sq_score,
            matched_entities=matched_signals,
            matched_terms=matched_intent_terms,
            rejection_reason=reason,
            rejection_stage=rejection_stage,
            title=title,
            url=url,
            temporal_status=temporal_assessment.status if temporal_assessment else None,
            recency_score=temporal_assessment.recency_score if temporal_assessment else 0.50,
        )

    def filter_candidates(
        self,
        candidates: List[Any],
        target_entity: str,
        domain: str = "general",
        intent: str = "",
        reference_time: Optional[datetime] = None,
        window_hours: Optional[float] = None,
        allow_updated: Optional[bool] = None,
    ) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """
        Partition candidates into accepted items and rejected audit records.
        Updates item metadata with detailed multi-dimensional assessment.
        """
        accepted = []
        rejected_audit = []

        for item in candidates:
            assessment = self.evaluate_item(
                item,
                target_entity=target_entity,
                domain=domain,
                intent=intent,
                reference_time=reference_time,
                window_hours=window_hours,
                allow_updated=allow_updated,
            )
            
            # Tag metadata on object if supported
            if hasattr(item, "relevance_score"):
                item.relevance_score = assessment.relevance_score
            if hasattr(item, "metadata") and isinstance(item.metadata, dict):
                item.metadata["relevance_class"] = assessment.relevance_class
                item.metadata["relevance_score"] = assessment.relevance_score
                item.metadata["entity_score"] = assessment.entity_score
                item.metadata["intent_score"] = assessment.intent_score
                item.metadata["matched_entities"] = assessment.matched_entities
                item.metadata["rejection_reason"] = assessment.rejection_reason
                item.metadata["rejection_stage"] = assessment.rejection_stage
                item.metadata["recency_score"] = assessment.recency_score
                if assessment.temporal_status:
                    item.metadata["temporal_status"] = assessment.temporal_status
                    item.metadata["temporal_eligible"] = assessment.is_accepted
            elif isinstance(item, dict):
                item["relevance_score"] = assessment.relevance_score
                item["relevance_class"] = assessment.relevance_class
                item["entity_score"] = assessment.entity_score
                item["intent_score"] = assessment.intent_score
                item["rejection_reason"] = assessment.rejection_reason
                item["rejection_stage"] = assessment.rejection_stage
                item["recency_score"] = assessment.recency_score
                if assessment.temporal_status:
                    item["temporal_status"] = assessment.temporal_status
                    item["temporal_eligible"] = assessment.is_accepted

            if assessment.is_accepted:
                accepted.append(item)
            else:
                rejected_audit.append(assessment.to_dict())

        return accepted, rejected_audit


# Global singleton
relevance_gate = RelevanceGate()
