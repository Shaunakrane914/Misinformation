"""
Aegis Protocol — Scout Domain Agent Models
===========================================
Data contracts and typed definitions for Agent 1 Scout (Predictive Financial Engine).
Includes financial facts, corporate events, contradictions, market catalysts,
and domain extraction results.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Re-export source engine models for unified domain access
from backend.agents.scout.sources.models import (
    CandidateSource,
    ContradictionRecord,
    CorporateEventType,
    EpistemicStatus,
    FactDirection,
    FreshnessRequirement,
    MarketSession,
    RawSource,
    ScoutEvidence,
    ScoutFailureCode,
    ScoutResult,
    ScoutSourceRequest,
    SourceTier,
    StoryCluster,
)


@dataclass
class FinancialFact:
    """Domain financial metric fact extracted from evidence."""
    metric: str
    value: float
    raw_str: str
    currency: str = "USD"
    unit: str = "absolute"
    period: Optional[str] = None
    confidence: float = 0.90
    evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "raw_str": self.raw_str,
            "currency": self.currency,
            "unit": self.unit,
            "period": self.period,
            "confidence": self.confidence,
            "evidence_ids": self.evidence_ids,
        }


@dataclass
class CorporateEvent:
    """Domain corporate event (earnings, M&A, guidance, regulatory)."""
    event_id: str
    event_type: str  # "EARNINGS" | "MERGERS_ACQUISITIONS" | "GUIDANCE_UPDATE" | "REGULATORY" | "CONTRACT_WIN"
    summary: str
    company: str
    impact_potential: str  # "HIGH" | "MEDIUM" | "LOW"
    confidence: float = 0.88
    evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "summary": self.summary,
            "company": self.company,
            "impact_potential": self.impact_potential,
            "confidence": self.confidence,
            "evidence_ids": self.evidence_ids,
        }


@dataclass
class FinancialContradiction:
    """Detected numerical or topical contradiction between evidence sources."""
    contradiction_id: str
    topic: str
    claim_a: str
    claim_b: str
    evidence_id_a: str
    evidence_id_b: str
    divergence_score: float = 0.85

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contradiction_id": self.contradiction_id,
            "topic": self.topic,
            "claim_a": self.claim_a,
            "claim_b": self.claim_b,
            "evidence_id_a": self.evidence_id_a,
            "evidence_id_b": self.evidence_id_b,
            "divergence_score": self.divergence_score,
        }


@dataclass
class MarketCatalyst:
    """Financial catalyst candidate identifying market-moving events."""
    catalyst_id: str
    headline: str
    direction: str  # "BULLISH" | "BEARISH" | "NEUTRAL"
    impact_potential: str = "MEDIUM"  # "HIGH" | "MEDIUM" | "LOW"
    confidence: float = 0.80
    evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "catalyst_id": self.catalyst_id,
            "headline": self.headline,
            "direction": self.direction,
            "impact_potential": self.impact_potential,
            "confidence": self.confidence,
            "evidence_ids": self.evidence_ids,
        }


@dataclass
class ScoutExtractionResult:
    """Domain extraction package for financial market intelligence."""
    ticker_or_company: str
    financial_facts: List[FinancialFact] = field(default_factory=list)
    corporate_events: List[CorporateEvent] = field(default_factory=list)
    contradictions: List[FinancialContradiction] = field(default_factory=list)
    rumor_signals: List[Dict[str, Any]] = field(default_factory=list)
    market_sentiment: str = "NEUTRAL"
    total_signals_analyzed: int = 0
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker_or_company": self.ticker_or_company,
            "financial_facts": [f.to_dict() for f in self.financial_facts],
            "corporate_events": [e.to_dict() for e in self.corporate_events],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "rumor_signals": self.rumor_signals,
            "market_sentiment": self.market_sentiment,
            "total_signals_analyzed": self.total_signals_analyzed,
            "extracted_at": self.extracted_at,
        }


__all__ = [
    # Domain models
    "FinancialFact",
    "CorporateEvent",
    "FinancialContradiction",
    "MarketCatalyst",
    "ScoutExtractionResult",
    # Source engine models
    "MarketSession",
    "FreshnessRequirement",
    "SourceTier",
    "FactDirection",
    "CorporateEventType",
    "EpistemicStatus",
    "ScoutFailureCode",
    "ScoutSourceRequest",
    "CandidateSource",
    "RawSource",
    "ContradictionRecord",
    "StoryCluster",
    "ScoutEvidence",
    "ScoutResult",
]
