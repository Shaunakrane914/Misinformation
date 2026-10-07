"""
Aegis Protocol — Agent Retrieval Profiles & Acquisition Customization
=====================================================================
Defines the standard RetrievalProfile model and AgentAcquisitionBase contract.
Enables domain-specific evidence profiles (BrandShield, Trending, Scout, Personal Watch)
while strictly adhering to the shared acquisition architecture, contracts, security,
provenance, and routing rules.
"""

from typing import Any, Dict, List, Optional

from backend.services.agent_reach.channels import (
    AgentAcquisitionBase,
    CandidateSource,
    EvidenceFragment,
    FetchedDocument,
    RetrievalProfile,
    RetrievalRequest,
)


# ── Canonical Agent Profiles ────────────────────────────────────────────────

BRANDSHIELD_PROFILE = RetrievalProfile(
    agent="brandshield",
    required_fields=[
        "brand", "product", "seller", "listing", "price",
        "author", "handle", "domain", "url",
    ],
    preferred_platforms=["web", "reddit", "twitter"],
    content_depth="PARTIAL_CONTENT",
    max_candidates=5,
    max_deep_reads=3,
    need_comments=True,
    need_transcript=False,
    need_engagement=False,
    need_structured_metadata=True,
    need_primary_source=False,
    extraction_hints={
        "focus": "trademark_and_counterfeiting",
        "prioritize_marketplace_listings": True,
        "screen_review_patterns": True,
    },
)

TRENDING_PROFILE = RetrievalProfile(
    agent="trending",
    required_fields=[
        "timestamp", "engagement", "platform", "author",
        "title", "content", "narrative", "claim",
    ],
    preferred_platforms=["twitter", "reddit", "news", "youtube", "web"],
    content_depth="SNIPPET",
    max_candidates=5,
    max_deep_reads=3,
    need_comments=False,
    need_transcript=False,
    need_engagement=True,
    need_structured_metadata=False,
    need_primary_source=False,
    extraction_hints={
        "focus": "narrative_diffusion_and_velocity",
        "track_syndication_clusters": True,
        "separate_sentiment_from_risk": True,
    },
)

SCOUT_PROFILE = RetrievalProfile(
    agent="scout",
    required_fields=[
        "title", "financial_facts", "earnings", "guidance",
        "corporate_events", "publication_date", "author", "source", "body",
    ],
    preferred_platforms=["news", "web", "twitter", "reddit"],
    content_depth="FULL_ARTICLE",
    max_candidates=5,
    max_deep_reads=5,
    need_comments=False,
    need_transcript=False,
    need_engagement=False,
    need_structured_metadata=True,
    need_primary_source=True,
    extraction_hints={
        "focus": "market_and_financial_catalysts",
        "require_primary_filings": True,
        "multi_currency_normalization": True,
        "contradiction_divergence_threshold": 0.20,
    },
)

PERSONAL_WATCH_PROFILE = RetrievalProfile(
    agent="personal",
    required_fields=[
        "identity", "public_statement", "career_movement",
        "professional_announcement", "platform", "author", "timestamp",
    ],
    preferred_platforms=["twitter", "news", "web", "linkedin"],
    content_depth="PARTIAL_CONTENT",
    max_candidates=5,
    max_deep_reads=3,
    need_comments=False,
    need_transcript=False,
    need_engagement=False,
    need_structured_metadata=False,
    need_primary_source=False,
    extraction_hints={
        "focus": "executive_and_public_figure_monitoring",
        "filter_sensitive_pii": True,
        "screen_impersonation_handles": True,
        "screen_crypto_giveaways": True,
    },
)

AGENT_PROFILES: Dict[str, RetrievalProfile] = {
    "brandshield": BRANDSHIELD_PROFILE,
    "trending": TRENDING_PROFILE,
    "scout": SCOUT_PROFILE,
    "personal": PERSONAL_WATCH_PROFILE,
}


def get_agent_profile(agent_name: str) -> RetrievalProfile:
    """Retrieve the domain-specific retrieval profile for an agent."""
    key = (agent_name or "").lower().strip()
    return AGENT_PROFILES.get(
        key,
        RetrievalProfile(
            agent=key or "generic",
            required_fields=["title", "content", "url", "author"],
            preferred_platforms=["web", "news"],
            content_depth="SNIPPET",
        ),
    )




# ── Domain-Specific Acquisition Implementations ─────────────────────────────

class BrandShieldAcquisition(AgentAcquisitionBase):
    """Custom acquisition strategy optimized for brand protection & marketplace listings."""

    def __init__(self, profile: Optional[RetrievalProfile] = None):
        self.profile = profile or BRANDSHIELD_PROFILE

    def get_profile(self) -> RetrievalProfile:
        return self.profile

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
        return SearchDiscoveryAdapter().discover_candidates(query=query, limit=limit)

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        return adapter.acquire(candidate, request)

    def normalize(
        self,
        doc: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        frags = adapter.normalize(doc, candidate, request)
        for f in frags:
            f.content_depth = self.profile.content_depth
        return frags

    def health(self) -> Dict[str, Any]:
        return {"agent": self.profile.agent, "status": "HEALTHY", "depth": self.profile.content_depth}

    def capabilities(self) -> Dict[str, Any]:
        return self.profile.to_dict()


class TrendingAcquisition(AgentAcquisitionBase):
    """Custom acquisition strategy optimized for real-time trend discovery and narrative flow."""

    def __init__(self, profile: Optional[RetrievalProfile] = None):
        self.profile = profile or TRENDING_PROFILE

    def get_profile(self) -> RetrievalProfile:
        return self.profile

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
        return SearchDiscoveryAdapter().discover_candidates(query=query, limit=limit)

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        return adapter.acquire(candidate, request)

    def normalize(
        self,
        doc: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        frags = adapter.normalize(doc, candidate, request)
        for f in frags:
            f.content_depth = self.profile.content_depth
        return frags

    def health(self) -> Dict[str, Any]:
        return {"agent": self.profile.agent, "status": "HEALTHY", "depth": self.profile.content_depth}

    def capabilities(self) -> Dict[str, Any]:
        return self.profile.to_dict()


class ScoutAcquisition(AgentAcquisitionBase):
    """Custom acquisition strategy optimized for financial data, filings, and corporate news."""

    def __init__(self, profile: Optional[RetrievalProfile] = None):
        self.profile = profile or SCOUT_PROFILE

    def get_profile(self) -> RetrievalProfile:
        return self.profile

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
        return SearchDiscoveryAdapter().discover_candidates(query=query, limit=limit)

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        return adapter.acquire(candidate, request)

    def normalize(
        self,
        doc: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        frags = adapter.normalize(doc, candidate, request)
        for f in frags:
            f.content_depth = self.profile.content_depth
        return frags

    def health(self) -> Dict[str, Any]:
        return {"agent": self.profile.agent, "status": "HEALTHY", "depth": self.profile.content_depth}

    def capabilities(self) -> Dict[str, Any]:
        return self.profile.to_dict()


class PersonalWatchAcquisition(AgentAcquisitionBase):
    """Custom acquisition strategy with active privacy preservation and executive monitoring."""

    def __init__(self, profile: Optional[RetrievalProfile] = None):
        self.profile = profile or PERSONAL_WATCH_PROFILE

    def get_profile(self) -> RetrievalProfile:
        return self.profile

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
        return SearchDiscoveryAdapter().discover_candidates(query=query, limit=limit)

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        return adapter.acquire(candidate, request)

    def normalize(
        self,
        doc: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        frags = adapter.normalize(doc, candidate, request)
        for f in frags:
            f.content_depth = self.profile.content_depth
        return frags

    def health(self) -> Dict[str, Any]:
        return {"agent": self.profile.agent, "status": "HEALTHY", "depth": self.profile.content_depth}

    def capabilities(self) -> Dict[str, Any]:
        return self.profile.to_dict()
