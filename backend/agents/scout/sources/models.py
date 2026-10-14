"""
Aegis Protocol — Scout Source Engine Data Models
==================================================
Strongly typed data contracts for requests, candidate sources, raw sources,
financial facts, corporate events, story clusters, contradictions, and evidence.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class MarketSession(str, Enum):
    PRE_MARKET = "PRE_MARKET"
    REGULAR = "REGULAR"
    AFTER_HOURS = "AFTER_HOURS"
    WEEKEND_CLOSED = "WEEKEND_CLOSED"


class FreshnessRequirement(str, Enum):
    BREAKING_5M = "BREAKING_5M"        # < 5 minutes
    RECENT_30M = "RECENT_30M"          # 5 to 30 minutes
    INTRADAY_2H = "INTRADAY_2H"        # 30m to 2 hours
    DAILY_24H = "DAILY_24H"            # 2 to 24 hours
    WEEKLY_7D = "WEEKLY_7D"            # 1 to 7 days
    ALL_TIME = "ALL_TIME"              # Historical context / regulatory filings


class SourceTier(str, Enum):
    TIER_1_PRIMARY = "TIER_1_PRIMARY"               # SEC, Exchange, Company IR, Government
    TIER_2_PRESS = "TIER_2_PRESS"                   # Reputable financial press (Bloomberg, Reuters)
    TIER_3_SPECIALIST = "TIER_3_SPECIALIST"         # Industry & sector technical publications
    TIER_4_COMMUNITY = "TIER_4_COMMUNITY"           # Social/public forums (Reddit, X, YouTube)
    TIER_5_AGGREGATE = "TIER_5_AGGREGATE"           # Search indices, RSS feeds, syndications


class FactDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    UNCERTAIN = "UNCERTAIN"


class CorporateEventType(str, Enum):
    EARNINGS = "EARNINGS"
    GUIDANCE_CHANGE = "GUIDANCE_CHANGE"
    M_AND_A = "M_AND_A"
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"
    PARTNERSHIP = "PARTNERSHIP"
    CAPEX_CHANGE = "CAPEX_CHANGE"
    LAYOFF = "LAYOFF"
    REGULATORY_ACTION = "REGULATORY_ACTION"
    LEGAL_ACTION = "LEGAL_ACTION"
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"
    SUPPLY_DISRUPTION = "SUPPLY_DISRUPTION"
    FINANCING = "FINANCING"
    MACRO_RELEASE = "MACRO_RELEASE"
    OTHER = "OTHER"


class EpistemicStatus(str, Enum):
    OFFICIAL = "OFFICIAL"                            # Backed by primary regulatory filing / IR
    CONFIRMED = "CONFIRMED"                          # Corroborated by 2+ independent Tier 2 outlets
    REPORTED = "REPORTED"                            # Reported by 1 reputable outlet without confirmation
    UNCONFIRMED_RUMOR = "UNCONFIRMED_RUMOR"          # Social discourse, anonymous leaks
    CONTRADICTED = "CONTRADICTED"                    # Competing claims conflict directly
    RETRACTED = "RETRACTED"                          # Formally retracted


class ScoutFailureCode(str, Enum):
    DISCOVERY_EMPTY = "DISCOVERY_EMPTY"
    DISCOVERY_RATE_LIMITED = "DISCOVERY_RATE_LIMITED"
    DISCOVERY_TIMEOUT = "DISCOVERY_TIMEOUT"
    INVALID_URL = "INVALID_URL"
    BLOCKED_SSRF = "BLOCKED_SSRF"
    SOURCE_SCOPE_MISMATCH = "SOURCE_SCOPE_MISMATCH"
    INVALID_URL_STRUCTURE = "INVALID_URL_STRUCTURE"
    TOKEN_CHEAT_REJECTED = "TOKEN_CHEAT_REJECTED"
    DOMAIN_REJECTED = "DOMAIN_REJECTED"
    CONTENT_UNAVAILABLE = "CONTENT_UNAVAILABLE"
    MIRROR_UNAVAILABLE = "MIRROR_UNAVAILABLE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    PARSE_FAILED = "PARSE_FAILED"
    INSUFFICIENT_CONTENT = "INSUFFICIENT_CONTENT"
    METADATA_MISSING = "METADATA_MISSING"
    SEMANTICALLY_IRRELEVANT = "SEMANTICALLY_IRRELEVANT"
    CONTRADICTION_UNRESOLVED = "CONTRADICTION_UNRESOLVED"
    STALE_CONTENT = "STALE_CONTENT"


@dataclass
class ScoutSourceRequest:
    query: str
    target_entity: str = ""
    tickers: List[str] = field(default_factory=list)
    sectors: List[str] = field(default_factory=list)
    event_types: List[str] = field(default_factory=list)
    target_sources: List[str] = field(default_factory=list)
    requested_scope: str = ""
    requested_author: str = ""
    requested_domain: str = ""
    platform_hint: Optional[str] = None
    freshness_requirement: FreshnessRequirement = FreshnessRequirement.DAILY_24H
    market_session: MarketSession = MarketSession.REGULAR
    max_candidates: int = 5
    max_depth: int = 2
    required_source_tier: str = SourceTier.TIER_4_COMMUNITY.value
    allow_social: bool = True
    allow_fallback: bool = True
    force_refresh: bool = False
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateSource:
    url: str
    canonical_url: str
    platform: str
    source_type: str                   # "article" | "post" | "filing" | "status" | "video"
    external_id: str                   # Post ID, status ID, filing accession number
    title: str = ""
    snippet: str = ""
    discovery_engine: str = "bing"     # "bing" | "yahoo" | "sec" | "ir" | "rss"
    discovery_rank: int = 0
    candidate_score: float = 0.50
    author: Optional[str] = None
    handle: Optional[str] = None
    subreddit: Optional[str] = None
    parent_id: Optional[str] = None
    published_hint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RawSource:
    candidate: CandidateSource
    content_raw: str
    content_type: str                  # "text/html" | "application/json" | "text/plain"
    status_code: int
    acquisition_method: str            # "direct_api" | "mirror" | "direct_http" | "scrapling" | "jina"
    latency_ms: int
    bytes_retrieved: int
    retrieved_at: str
    headers: Dict[str, str] = field(default_factory=dict)
    is_authenticated: bool = False
    error: Optional[str] = None


@dataclass
class FinancialFact:
    metric: str                        # "revenue" | "ebitda" | "eps" | "margin" | "capex" | "deal_value"
    raw_value: str                     # "$5.4B"
    normalized_value: float            # 5400000000.0
    unit: str                          # "billion" | "million" | "crore" | "bps" | "percent"
    currency: str                      # "USD" | "INR" | "EUR" | "GBP" | "NONE"
    period: Optional[str] = None       # "Q4" | "FY25" | "trailing_12m"
    direction: FactDirection = FactDirection.NEUTRAL
    comparison: Optional[str] = None   # "YoY" | "QoQ" | "vs_consensus"
    context_sentence: str = ""
    confidence: float = 1.0


@dataclass
class CorporateEvent:
    event_type: CorporateEventType
    company: str
    ticker: str
    event_time: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    direction: FactDirection = FactDirection.NEUTRAL
    description: str = ""
    confidence: float = 0.85


@dataclass
class ContradictionRecord:
    metric_or_aspect: str
    source_a_url: str
    source_a_claim: str
    source_b_url: str
    source_b_claim: str
    discrepancy_description: str
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class StoryCluster:
    cluster_id: str
    headline: str
    primary_source_url: str
    syndicated_urls: List[str] = field(default_factory=list)
    independent_sources: List[str] = field(default_factory=list)
    first_seen_at: str = ""
    last_updated_at: str = ""
    primary_source_present: bool = False
    epistemic_status: EpistemicStatus = EpistemicStatus.REPORTED
    contradictions: List[ContradictionRecord] = field(default_factory=list)
    confidence: float = 0.80


@dataclass
class ScoutEvidence:
    """
    Standard evidence unit emitted by ScoutSourceEngine.
    Implements full compatibility with Aegis EvidenceFragment.
    """
    evidence_id: str
    url: str
    canonical_url: str
    platform: str
    source_type: str
    source_tier: str                   # TIER_1_PRIMARY, TIER_2_PRESS, TIER_3_COMMUNITY
    external_id: str
    title: str
    author: str
    body: str
    snippet: str
    published_at: str
    event_at: Optional[str]
    retrieved_at: str
    financial_facts: List[FinancialFact] = field(default_factory=list)
    events: List[CorporateEvent] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    tickers: List[str] = field(default_factory=list)
    score: float = 0.50
    relevance_score: float = 0.50
    quality_score: float = 0.50
    freshness_score: float = 0.50
    retrieval_mode: str = "direct_api"
    adapter: str = "generic_web"
    search_engine: str = "bing"
    is_authenticated: bool = False
    is_primary: bool = False
    syndicated_from: Optional[str] = None
    cluster_id: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_evidence_fragment(self) -> Any:
        """Convert directly into canonical backend.services.agent_reach.channels.EvidenceFragment."""
        from backend.services.agent_reach.channels import EvidenceFragment
        return EvidenceFragment(
            platform=self.platform,
            title=self.title,
            content=self.body,
            url=self.canonical_url or self.url,
            author=self.author,
            published=self.published_at,
            snippet=self.snippet or self.body[:250],
            score=self.score,
            retrieval_method="scout_source_engine",
            retrieved_at=self.retrieved_at,
            channel_name=self.platform,
            content_depth="FULL_ARTICLE" if len(self.body) > 1000 else "PARTIAL_CONTENT",
            retrieval_mode=self.retrieval_mode,
            native_backend_id=self.adapter,
            is_authenticated=self.is_authenticated,
            raw_metadata={
                "financial_facts": [f.__dict__ for f in self.financial_facts],
                "events": [e.__dict__ for e in self.events],
                "source_tier": self.source_tier,
                "is_primary": self.is_primary,
                "event_at": self.event_at,
                "cluster_id": self.cluster_id,
                "provenance": self.provenance
            }
        )


@dataclass
class ScoutResult:
    """The aggregate response from ScoutSourceEngine to ScoutAgent."""
    query: str
    entity: str
    evidence_items: List[ScoutEvidence] = field(default_factory=list)
    clusters: List[StoryCluster] = field(default_factory=list)
    financial_facts: List[FinancialFact] = field(default_factory=list)
    events: List[CorporateEvent] = field(default_factory=list)
    contradictions: List[ContradictionRecord] = field(default_factory=list)
    primary_source_present: bool = False
    independent_source_count: int = 0
    epistemic_status: EpistemicStatus = EpistemicStatus.REPORTED
    telemetry: Dict[str, Any] = field(default_factory=dict)
