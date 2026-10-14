"""
Aegis Protocol — Trending Domain Models & Catalogs
==================================================
Typed data models, known entity catalogs, and syndication signatures for
Trend Discovery and Trend Intelligence.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── Structured Trend Data Models ─────────────────────────────────────────────

@dataclass
class TrendEvidence:
    evidence_id: str
    platform: str                    # "news" | "reddit" | "twitter" | "youtube" | "instagram" | "web" | "rss"
    source: str                      # Outlet name, subreddit, handle, or channel
    title: str
    content: str
    snippet: str = ""
    url: str = ""                         # Validated real URL (never '#' or invented)
    canonical_url: str = ""
    author: str = ""
    published_at: str = ""                # Real ISO or formatted timestamp
    retrieved_at: str = ""                # ISO timestamp
    source_role: str = "COMMUNITY"        # "PRIMARY" | "SECONDARY" | "COMMUNITY" | "COMMENTARY" | "DIRECT_MEDIA" | "DISCOVERY"
    source_tier: str = "TIER_3"           # "TIER_1" | "TIER_2" | "TIER_3" | "TIER_4"
    source_group_id: str = "G-01"         # Group ID for wire syndication / copies (e.g. "G-01")
    retrieval_method: str = "agent_reach" # "agent_reach" | "apify" | "google_news" | "direct_web"
    discovered_candidate_id: Optional[str] = None
    ranked_candidate_id: Optional[str] = None
    accepted_candidate_id: Optional[str] = None
    acquisition_attempt_id: Optional[str] = None
    acquired_candidate_id: Optional[str] = None
    selection_decision: Optional[str] = None
    selection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrendNarrative:
    narrative_id: str
    title: str
    summary: str
    sentiment: str                   # "POSITIVE" | "NEUTRAL" | "NEGATIVE" | "MIXED"
    evidence_ids: List[str] = field(default_factory=list)
    platforms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrendClaim:
    claim_id: str
    claim_text: str
    status: str                      # "VERIFIED" | "SUPPORTED" | "UNVERIFIED" | "CONTRADICTED" | "UNKNOWN"
    supporting_sources: int = 0
    contradicting_sources: int = 0
    evidence_ids: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Trend:
    trend_id: str
    topic: str
    category: str
    first_seen_at: str
    latest_seen_at: str
    signal_count: int
    source_count: int
    unique_source_count: int
    independent_source_count: int
    platform_count: int
    velocity: Dict[str, Any]
    origin: Dict[str, Any]
    narratives: List[Dict[str, Any]]
    claims: List[Dict[str, Any]]
    sentiment: str                   # "POSITIVE" | "NEUTRAL" | "NEGATIVE" | "MIXED"
    sentiment_score: int             # -100 to 100
    misinformation_risk: str         # "LOW" | "MEDIUM" | "HIGH"
    misinformation_rationale: str
    evidence_ids: List[str]
    status: str = "active"           # "active" | "emerging" | "stable" | "declining" | "resolved"
    trend_nature: str = "TRENDING"   # "TRENDING" | "VIRAL" | "NEWSWORTHY" | "RECURRING" | "HIGH_VOLUME" | "NEWLY_EMERGING"
    why_trending: str = ""
    emergence_window: str = ""
    underlying_event: str = ""
    debunk_status: str = "NO_CONTRADICTION"
    contradictions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Domain Extraction Records ────────────────────────────────────────────────

@dataclass
class NarrativeCluster:
    narrative_id: str
    title: str
    summary: str
    platforms: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    coherence_score: float = 0.85

    def to_dict(self) -> Dict[str, Any]:
        return {
            "narrative_id": self.narrative_id,
            "title": self.title,
            "summary": self.summary,
            "platforms": self.platforms,
            "evidence_ids": self.evidence_ids,
            "coherence_score": self.coherence_score,
        }


@dataclass
class TrendRecord:
    trend_id: str
    topic: str
    category: str                            # "entertainment" | "tech" | "business" | "politics" | "general"
    sentiment: str                           # "POSITIVE" | "NEGATIVE" | "MIXED" | "NEUTRAL"
    misinformation_risk: str                 # "LOW" | "MEDIUM" | "HIGH"
    misinformation_rationale: str
    velocity: Dict[str, Any]                 # {"label": "HIGH_MOMENTUM" | "STEADY" | "DECLINING", "score": float}
    platform_count: int
    narratives: List[NarrativeCluster] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_id": self.trend_id,
            "topic": self.topic,
            "category": self.category,
            "sentiment": self.sentiment,
            "misinformation_risk": self.misinformation_risk,
            "misinformation_rationale": self.misinformation_rationale,
            "velocity": self.velocity,
            "platform_count": self.platform_count,
            "narratives": [n.to_dict() for n in self.narratives],
            "evidence_ids": self.evidence_ids,
        }


@dataclass
class TrendingExtractionResult:
    target_entity: str
    identity_confidence: float = 0.95
    trends: List[TrendRecord] = field(default_factory=list)
    narrative_clusters: List[NarrativeCluster] = field(default_factory=list)
    observed: List[str] = field(default_factory=list)
    inferred: List[str] = field(default_factory=list)
    uncertain: List[str] = field(default_factory=list)
    sentiment: Dict[str, Any] = field(default_factory=dict)
    syndication_groups: Dict[str, List[str]] = field(default_factory=dict)
    total_signals: int = 0
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_entity": self.target_entity,
            "identity_confidence": self.identity_confidence,
            "trends": [t.to_dict() for t in self.trends],
            "narrative_clusters": [n.to_dict() for n in self.narrative_clusters],
            "observed": self.observed,
            "inferred": self.inferred,
            "uncertain": self.uncertain,
            "sentiment": self.sentiment,
            "syndication_groups": self.syndication_groups,
            "total_signals": self.total_signals,
            "extracted_at": self.extracted_at,
        }


# ── Catalogs and Syndication Signatures ──────────────────────────────────────

KNOWN_ENTITY_CATALOG: Dict[str, Dict[str, Any]] = {
    "DEEPIKA": {
        "canonical": "Deepika Padukone",
        "aliases": ["Deepika", "Deepika P"],
        "category": "entertainment",
        "role": "Actor / Producer"
    },
    "DEEPIKA PADUKONE": {
        "canonical": "Deepika Padukone",
        "aliases": ["Deepika", "Deepika P"],
        "category": "entertainment",
        "role": "Actor / Producer"
    },
    "SRK": {
        "canonical": "Shah Rukh Khan",
        "aliases": ["SRK", "Shahrukh Khan", "King Khan"],
        "category": "entertainment",
        "role": "Actor / Producer"
    },
    "SHAH RUKH KHAN": {
        "canonical": "Shah Rukh Khan",
        "aliases": ["SRK", "Shahrukh Khan", "King Khan"],
        "category": "entertainment",
        "role": "Actor / Producer"
    },
    "RANVEER SINGH": {
        "canonical": "Ranveer Singh",
        "aliases": ["Ranveer", "RS"],
        "category": "entertainment",
        "role": "Actor"
    },
    "ALIA BHATT": {
        "canonical": "Alia Bhatt",
        "aliases": ["Alia", "Alia Kapoor"],
        "category": "entertainment",
        "role": "Actor / Producer"
    },
    "KATRINA KAIF": {
        "canonical": "Katrina Kaif",
        "aliases": ["Katrina", "Kat"],
        "category": "entertainment",
        "role": "Actor / Entrepreneur"
    },
    "JAWAN": {
        "canonical": "Jawan (Film)",
        "aliases": ["Jawan Movie", "Jawan Film"],
        "category": "cinema",
        "role": "Feature Film"
    },
    "OPENAI": {
        "canonical": "OpenAI",
        "aliases": ["ChatGPT", "GPT-4", "Sora"],
        "category": "technology",
        "role": "AI Research & Deployment"
    },
    "TESLA": {
        "canonical": "Tesla, Inc.",
        "aliases": ["Tesla", "TSLA"],
        "category": "business",
        "role": "Automotive & Clean Energy"
    },
    "SAM ALTMAN": {
        "canonical": "Sam Altman",
        "aliases": ["Sama"],
        "category": "technology",
        "role": "Executive / Tech Leader"
    }
}

WIRE_SIGNATURES = [
    "press trust of india", "pti", "asian news international", "ani",
    "reuters", "associated press", "ap wire", "ians", "pr newswire", "bloomberg"
]

WIRE_SYNDICATION_DOMAINS = {
    "reuters.com": "Reuters Wire",
    "apnews.com": "Associated Press",
    "ptinews.com": "Press Trust of India",
    "bloomberg.com": "Bloomberg News",
    "prnewswire.com": "PR Newswire",
    "businesswire.com": "Business Wire",
}
