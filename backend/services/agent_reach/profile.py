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

import re
import urllib.parse


class BrandShieldAcquisition(AgentAcquisitionBase):
    """
    Custom acquisition strategy optimized for brand protection & marketplace listings.
    Behaviorally prioritizes marketplace listings, seller identification, product pricing,
    and user complaint comments.
    """

    MARKETPLACE_DOMAINS = (
        "amazon.", "ebay.", "etsy.", "aliexpress.", "walmart.", "target.",
        "shopify.com", "myshopify.com", "dhgate.", "wish.com", "temu."
    )

    COMPLAINT_PATTERNS = re.compile(
        r"\b(counterfeit|fake|knockoff|replica|scam|broken|fraud|defective|rip[\s-]?off|stolen)\b",
        re.IGNORECASE
    )

    PRICE_PATTERN = re.compile(r"(\$|€|£|₹|\bUSD\b|\bEUR\b|\bINR\b)\s?(\d+(?:[,\.]\d+)?)", re.IGNORECASE)

    def __init__(self, profile: Optional[RetrievalProfile] = None):
        self.profile = profile or BRANDSHIELD_PROFILE

    def get_profile(self) -> RetrievalProfile:
        return self.profile

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """
        Marketplace & complaint-heavy candidate discovery.
        Formulates e-commerce, counterfeit, and complaint-targeted search queries.
        """
        from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
        search_adapter = SearchDiscoveryAdapter()

        brand_queries = [
            f"{query} official store counterfeit fake replica",
            f"{query} seller price discount shop buy",
            f"site:reddit.com {query} scam complaint fake defective",
        ]

        candidates: List[CandidateSource] = []
        for q in brand_queries:
            discovered = search_adapter.discover_candidates(query=q, limit=limit)
            for cand in discovered:
                # Tag marketplace and complaint indicators
                url_low = (cand.canonical_url or cand.url).lower()
                is_marketplace = any(d in url_low for d in self.MARKETPLACE_DOMAINS)
                has_complaint = bool(self.COMPLAINT_PATTERNS.search(f"{cand.title} {cand.snippet}"))

                cand.metadata["is_marketplace"] = is_marketplace
                cand.metadata["has_complaint_signal"] = has_complaint

                # Boost semantic score for marketplace listings or explicit complaints
                if is_marketplace:
                    cand.semantic_score = min(100.0, cand.semantic_score + 15.0)
                if has_complaint:
                    cand.semantic_score = min(100.0, cand.semantic_score + 10.0)

                candidates.append(cand)

        # Deduplicate candidates by canonical URL
        seen_urls = set()
        deduped = []
        for c in sorted(candidates, key=lambda x: x.semantic_score, reverse=True):
            if c.canonical_url not in seen_urls:
                seen_urls.add(c.canonical_url)
                deduped.append(c)
        return deduped[:limit]

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """
        Targeted acquisition extracting product details, seller info, and forum comments.
        """
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)

        # Ensure request preserves BrandShield's need_comments and structured metadata
        req_copy = RetrievalRequest(
            request_id=request.request_id,
            agent="brandshield",
            entity=request.entity,
            intent=request.intent,
            task_type="READ" if candidate.url.startswith("http") else "SEARCH",
            scope=request.scope,
            candidate_budget=request.candidate_budget,
            profile=self.profile,
            metadata=dict(request.metadata, need_comments=self.profile.need_comments),
        )
        return adapter.acquire(candidate, req_copy)

    def normalize(
        self,
        doc: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """
        Normalizes into EvidenceFragment with seller, price, and counterfeit metadata.
        """
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        frags = adapter.normalize(doc, candidate, request)

        for f in frags:
            f.content_depth = self.profile.content_depth
            text_corpus = f"{f.title} {f.content} {f.snippet}"

            # Extract seller / store domain
            parsed_url = urllib.parse.urlparse(f.url)
            f.metadata["domain"] = parsed_url.netloc
            f.metadata["seller"] = f.author or parsed_url.netloc

            # Detect price references
            price_match = self.PRICE_PATTERN.search(text_corpus)
            if price_match:
                f.metadata["price"] = f"{price_match.group(1)}{price_match.group(2)}"

            # Detect counterfeit indicators
            f.metadata["counterfeit_indicators"] = self.COMPLAINT_PATTERNS.findall(text_corpus)
            is_mkt = any(m in parsed_url.netloc for m in self.MARKETPLACE_DOMAINS) or candidate.metadata.get("is_marketplace", False)
            f.metadata["marketplace_listing"] = is_mkt
            f.metadata["is_marketplace"] = is_mkt

        return frags

    def health(self) -> Dict[str, Any]:
        return {
            "agent": self.profile.agent,
            "status": "HEALTHY",
            "depth": self.profile.content_depth,
            "strategy": "marketplace_and_complaint_harvesting"
        }

    def capabilities(self) -> Dict[str, Any]:
        return self.profile.to_dict()


class TrendingAcquisition(AgentAcquisitionBase):
    """
    Custom acquisition strategy optimized for viral velocity, narrative diffusion,
    and wire syndication detection.
    """

    WIRE_OUTLETS = ("reuters.com", "apnews.com", "bloomberg.com", "afp.com", "upi.com")

    def __init__(self, profile: Optional[RetrievalProfile] = None):
        self.profile = profile or TRENDING_PROFILE

    def get_profile(self) -> RetrievalProfile:
        return self.profile

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """
        Social-first candidate discovery with velocity and breaking news focus.
        """
        from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
        search_adapter = SearchDiscoveryAdapter()

        velocity_queries = [
            f"{query} viral trending discussion",
            f"{query} breaking news controversy",
        ]

        candidates: List[CandidateSource] = []
        for q in velocity_queries:
            discovered = search_adapter.discover_candidates(query=q, limit=limit)
            for cand in discovered:
                plat = cand.platform.lower()
                # Social sources get prioritization for trend velocity
                if plat in ("twitter", "x", "reddit", "youtube"):
                    cand.semantic_score = min(100.0, cand.semantic_score + 10.0)
                    cand.metadata["social_origin"] = True
                candidates.append(cand)

        seen_urls = set()
        deduped = []
        for c in sorted(candidates, key=lambda x: x.semantic_score, reverse=True):
            if c.canonical_url not in seen_urls:
                seen_urls.add(c.canonical_url)
                deduped.append(c)
        return deduped[:limit]

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """
        Acquires candidate with focus on engagement metrics and propagation timestamps.
        """
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        return adapter.acquire(candidate, request)

    def normalize(
        self,
        doc: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """
        Normalizes into EvidenceFragment with engagement metrics and syndication tags.
        """
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        frags = adapter.normalize(doc, candidate, request)

        for f in frags:
            f.content_depth = self.profile.content_depth
            netloc = urllib.parse.urlparse(f.url).netloc.lower()

            # Identify wire syndication vs independent narrative post
            is_wire = any(w in netloc for w in self.WIRE_OUTLETS)
            f.metadata["is_wire_syndication"] = is_wire
            f.metadata["social_origin"] = candidate.metadata.get("social_origin", False)

            # Preserve engagement signals
            if "likes" in doc.raw_metadata:
                f.metadata["likes"] = doc.raw_metadata["likes"]
            if "retweets" in doc.raw_metadata:
                f.metadata["retweets"] = doc.raw_metadata["retweets"]
            if "views" in doc.raw_metadata:
                f.metadata["views"] = doc.raw_metadata["views"]

        return frags

    def health(self) -> Dict[str, Any]:
        return {
            "agent": self.profile.agent,
            "status": "HEALTHY",
            "depth": self.profile.content_depth,
            "strategy": "social_velocity_and_wire_syndication"
        }

    def capabilities(self) -> Dict[str, Any]:
        return self.profile.to_dict()


class ScoutAcquisition(AgentAcquisitionBase):
    """
    Custom acquisition strategy optimized for financial filings, earnings reports,
    M&A deal values, and primary regulatory documents.
    Enforces deep paragraph-level acquisition rather than headline snippets.
    """

    PRIMARY_FINANCIAL_DOMAINS = (
        "sec.gov", "investor.", "ir.", "edgar.", "prnewswire.com", "businesswire.com"
    )

    def __init__(self, profile: Optional[RetrievalProfile] = None):
        self.profile = profile or SCOUT_PROFILE

    def get_profile(self) -> RetrievalProfile:
        return self.profile

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """
        Financial & regulatory candidate discovery. Formulates primary filing,
        earnings, and M&A queries, promoting SEC and IR candidates.
        """
        from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
        search_adapter = SearchDiscoveryAdapter()

        financial_queries = [
            f"{query} SEC filing 10-K 10-Q press release IR",
            f"{query} earnings revenue guidance EBITDA deal valuation",
            f"{query} acquisition merger regulatory filing",
        ]

        candidates: List[CandidateSource] = []
        for q in financial_queries:
            discovered = search_adapter.discover_candidates(query=q, limit=limit)
            for cand in discovered:
                url_low = (cand.canonical_url or cand.url).lower()
                is_primary = any(p in url_low for p in self.PRIMARY_FINANCIAL_DOMAINS)
                cand.metadata["is_primary_source"] = is_primary

                # Heavy boost for primary regulatory filings and investor relations
                if is_primary:
                    cand.semantic_score = min(100.0, cand.semantic_score + 25.0)

                candidates.append(cand)

        seen_urls = set()
        deduped = []
        for c in sorted(candidates, key=lambda x: x.semantic_score, reverse=True):
            if c.canonical_url not in seen_urls:
                seen_urls.add(c.canonical_url)
                deduped.append(c)
        return deduped[:limit]

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """
        Deep acquisition enforcing full paragraph extraction for financial numbers.
        """
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)

        # Force full content depth in retrieval request for Scout
        req_copy = RetrievalRequest(
            request_id=request.request_id,
            agent="scout",
            entity=request.entity,
            intent=request.intent,
            task_type="READ" if candidate.url.startswith("http") else "SEARCH",
            scope=request.scope,
            candidate_budget=request.candidate_budget,
            profile=self.profile,
            metadata=dict(request.metadata, need_full_article=True),
        )
        return adapter.acquire(candidate, req_copy)

    def normalize(
        self,
        doc: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """
        Normalizes into FULL_ARTICLE EvidenceFragment records with financial metadata.
        """
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        frags = adapter.normalize(doc, candidate, request)

        for f in frags:
            f.content_depth = self.profile.content_depth  # FULL_ARTICLE
            url_low = f.url.lower()
            is_primary = any(p in url_low for p in self.PRIMARY_FINANCIAL_DOMAINS)
            f.metadata["is_primary_source"] = is_primary
            f.metadata["financial_domain"] = True

        return frags

    def health(self) -> Dict[str, Any]:
        return {
            "agent": self.profile.agent,
            "status": "HEALTHY",
            "depth": self.profile.content_depth,
            "strategy": "primary_filing_and_full_article_extraction"
        }

    def capabilities(self) -> Dict[str, Any]:
        return self.profile.to_dict()


class PersonalWatchAcquisition(AgentAcquisitionBase):
    """
    Custom acquisition strategy for executive monitoring, public statements,
    and verified professional announcements, with strict automated PII filtering.
    """

    PII_PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
    PII_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    PII_ADDRESS_PATTERN = re.compile(
        r"\b\d{1,5}\s+[A-Za-z0-9\.\s]+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Terrace|Ter|Way|Place|Pl|Court|Ct)\b",
        re.IGNORECASE
    )

    def __init__(self, profile: Optional[RetrievalProfile] = None):
        self.profile = profile or PERSONAL_WATCH_PROFILE

    def get_profile(self) -> RetrievalProfile:
        return self.profile

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """
        Executive statement & verified announcement candidate discovery.
        """
        from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
        search_adapter = SearchDiscoveryAdapter()

        executive_queries = [
            f'"{query}" official statement announcement appointment',
            f'"{query}" interview transcript career resignation',
            f'"{query}" public address executive verified',
        ]

        candidates: List[CandidateSource] = []
        for q in executive_queries:
            discovered = search_adapter.discover_candidates(query=q, limit=limit)
            for cand in discovered:
                url_low = cand.canonical_url.lower()
                # Prioritize verified public statement sources
                if any(k in url_low for k in ("linkedin.com", "twitter.com", "x.com", "press", "news")):
                    cand.semantic_score = min(100.0, cand.semantic_score + 10.0)
                candidates.append(cand)

        seen_urls = set()
        deduped = []
        for c in sorted(candidates, key=lambda x: x.semantic_score, reverse=True):
            if c.canonical_url not in seen_urls:
                seen_urls.add(c.canonical_url)
                deduped.append(c)
        return deduped[:limit]

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """
        Acquires candidate focusing on quoted public statements and verified accounts.
        """
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        return adapter.acquire(candidate, request)

    def normalize(
        self,
        doc: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """
        Normalizes evidence while actively redacting sensitive private PII.
        """
        from backend.services.agent_reach.native.router import native_router
        adapter = native_router.adapter_registry.get_adapter_for_candidate(candidate)
        frags = adapter.normalize(doc, candidate, request)

        for f in frags:
            f.content_depth = self.profile.content_depth

            # Automated PII sanitization across snippet and content
            sanitized_content = self._sanitize_pii(f.content)
            sanitized_snippet = self._sanitize_pii(f.snippet)

            f.content = sanitized_content
            f.snippet = sanitized_snippet
            f.metadata["pii_filtered"] = True
            f.metadata["public_figure_monitoring"] = True

        return frags

    def _sanitize_pii(self, text: str) -> str:
        """Redact phone numbers, SSNs, and residential street addresses."""
        if not text:
            return ""
        text = self.PII_PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
        text = self.PII_SSN_PATTERN.sub("[REDACTED_SSN]", text)
        text = self.PII_ADDRESS_PATTERN.sub("[REDACTED_RESIDENTIAL_ADDRESS]", text)
        return text

    def health(self) -> Dict[str, Any]:
        return {
            "agent": self.profile.agent,
            "status": "HEALTHY",
            "depth": self.profile.content_depth,
            "strategy": "executive_statements_with_pii_sanitization"
        }

    def capabilities(self) -> Dict[str, Any]:
        return self.profile.to_dict()


AGENT_ACQUISITION_STRATEGIES: Dict[str, AgentAcquisitionBase] = {
    "brandshield": BrandShieldAcquisition(),
    "trending": TrendingAcquisition(),
    "scout": ScoutAcquisition(),
    "personal": PersonalWatchAcquisition(),
    "personal_watch": PersonalWatchAcquisition(),
}


def get_agent_acquisition_strategy(agent_name: str) -> Optional[AgentAcquisitionBase]:
    """Retrieve the domain-specific acquisition strategy instance for an agent."""
    key = (agent_name or "").lower().strip()
    return AGENT_ACQUISITION_STRATEGIES.get(key)


