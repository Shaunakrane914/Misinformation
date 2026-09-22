"""
Aegis Protocol — Retrieval Planner
===================================
Domain-specific query construction and channel selection logic.
This is the intelligence layer that Aegis owns — Agent Reach provides
the channel primitives, the planner decides *what* to search and *where*.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

__all__ = [
    "RetrievalPlan",
    "RetrievalPlanner",
    "TICKER_NAME_MAP",
]


@dataclass
class RetrievalPlan:
    """
    Structured plan produced by the RetrievalPlanner.

    Specifies which channels to query and with what domain-optimized queries,
    ordered by priority for the given domain.
    """
    domain: str
    original_query: str
    channels_to_query: List[str] = field(default_factory=list)
    domain_queries: Dict[str, str] = field(default_factory=dict)
    priority_order: List[str] = field(default_factory=list)
    search_keywords: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "original_query": self.original_query,
            "channels_to_query": self.channels_to_query,
            "domain_queries": self.domain_queries,
            "priority_order": self.priority_order,
            "search_keywords": self.search_keywords,
        }


# Stopwords for keyword extraction from verbose claims
_STOPWORDS = {
    'that', 'this', 'with', 'from', 'have', 'been', 'were', 'what', 'when',
    'where', 'which', 'their', 'there', 'about', 'into', 'secretly',
    'according', 'alleged', 'reportedly', 'claims', 'stated', 'saying',
    'could', 'would', 'should', 'might',
}

# Common financial ticker to company mapping
TICKER_NAME_MAP: Dict[str, str] = {
    'NVDA': 'Nvidia',
    'AAPL': 'Apple',
    'TSLA': 'Tesla',
    'MSFT': 'Microsoft',
    'GOOGL': 'Alphabet Google',
    'AMZN': 'Amazon',
    'META': 'Meta',
    'NFLX': 'Netflix',
    'TATAMOTORS.NS': 'Tata Motors',
    'TATAMOTORS': 'Tata Motors',
    'RELIANCE.NS': 'Reliance Industries',
    'RELIANCE': 'Reliance Industries',
    'INFY.NS': 'Infosys',
    'INFY': 'Infosys',
    'TCS.NS': 'Tata Consultancy Services',
    'TCS': 'Tata Consultancy Services',
    'HDFCBANK.NS': 'HDFC Bank',
    'HDFCBANK': 'HDFC Bank',
    'WIPRO.NS': 'Wipro',
    'ICICIBANK.NS': 'ICICI Bank',
    'SBIN.NS': 'State Bank of India',
    'ADANIENT.NS': 'Adani Enterprises',
}


class RetrievalPlanner:
    """
    Domain-aware retrieval planner for Aegis Protocol.

    Takes a claim text and domain, produces a RetrievalPlan with:
    - Per-channel optimized queries (e.g., cashtags for financial, debunk keywords for fact_check)
    - Channel priority ordering based on domain relevance
    - Extracted search keywords for verbose claims

    This is a pure-function planner — no side effects, fully testable.
    """

    # Default channels available in the system
    ALL_CHANNELS = ["reddit", "twitter", "youtube", "news", "github", "rss"]

    # Domain -> channel priority ordering
    DOMAIN_PRIORITIES: Dict[str, List[str]] = {
        "technical": ["github", "news", "reddit", "youtube", "twitter"],
        "financial": ["twitter", "news", "reddit", "youtube", "rss"],
        "fact_check": ["news", "reddit", "twitter", "youtube", "rss"],
        "brand": ["reddit", "news", "twitter", "youtube", "rss"],
        "personal": ["twitter", "news", "reddit", "youtube", "rss"],
        "trending": ["twitter", "reddit", "youtube", "news", "rss"],
        "general": ["news", "reddit", "twitter", "youtube", "rss"],
    }


    def plan(
        self,
        query: str,
        domain: str = "general",
        include_channels: Optional[List[str]] = None,
        exclude_channels: Optional[List[str]] = None,
    ) -> RetrievalPlan:
        """
        Generate a retrieval plan for the given query and domain.

        Args:
            query: The claim or search text
            domain: Domain context (financial, fact_check, brand, personal, trending, general)
            include_channels: If set, only these channels are included
            exclude_channels: If set, these channels are excluded

        Returns:
            A RetrievalPlan with domain-optimized queries per channel
        """
        clean_q = query.strip()
        search_kw = self._extract_keywords(clean_q)

        # Determine channels to query
        priority = self.DOMAIN_PRIORITIES.get(domain, self.ALL_CHANNELS)

        if include_channels:
            channels = [c for c in priority if c in include_channels]
        else:
            channels = list(priority)

        if exclude_channels:
            channels = [c for c in channels if c not in exclude_channels]

        # Generate domain-specific queries
        domain_queries = self._craft_domain_queries(clean_q, search_kw, domain)

        return RetrievalPlan(
            domain=domain,
            original_query=clean_q,
            channels_to_query=channels,
            domain_queries=domain_queries,
            priority_order=channels,
            search_keywords=search_kw,
        )

    def _extract_keywords(self, query: str) -> str:
        """Extract salient search keywords for higher recall on verbose claims."""
        words = [
            w for w in re.findall(r'\b[A-Za-z0-9_-]{3,}\b', query)
            if w.lower() not in _STOPWORDS
        ]
        return " ".join(words[:5]) if len(words) >= 5 else query

    def _craft_domain_queries(
        self,
        clean_q: str,
        search_kw: str,
        domain: str
    ) -> Dict[str, str]:
        """
        Produce per-channel optimized queries based on domain context.

        This migrates the query-construction logic from agent_reach_scraper.omni_scan()
        into a clean, testable function.
        """
        if domain == "technical":
            return {
                "github": search_kw,
                "news": f"{search_kw} vulnerability OR patch OR release OR security",
                "reddit": f"{search_kw} (release OR CVE OR issue OR bug)",
                "twitter": f"{search_kw} CVE OR exploit OR update",
                "youtube": f"{search_kw} technical analysis walkthrough",
                "rss": f"{search_kw} release OR security advisory",
            }

        if domain == "financial":
            clean_ticker = clean_q.upper().replace(".NS", "").replace(".BO", "")
            company_name = TICKER_NAME_MAP.get(clean_q.upper(), TICKER_NAME_MAP.get(clean_ticker, clean_ticker))
            return {
                "reddit": f"{clean_ticker} OR \"{company_name}\" (crash OR scam OR fraud OR short OR plunge OR earnings OR DD)",
                "twitter": f"${clean_ticker} OR {clean_ticker} rumor OR crash OR short OR \"{company_name}\"",
                "youtube": f"{company_name} {clean_ticker} stock financial analysis crash",
                "news": f"{company_name} {clean_ticker} stock investigation OR crash OR SEC OR results OR earnings OR announcement",
                "rss": f"{company_name} {clean_ticker} investor relations filing regulatory annual report press release",
                "github": clean_q,
            }

        if domain == "fact_check":
            return {
                "reddit": f"{search_kw} (debunked OR hoax OR true OR fake)",
                "twitter": f"{search_kw} fake OR hoax OR debunked",
                "youtube": f"{search_kw} fact check debunked",
                "news": f"{search_kw} fact check OR verified OR official",
                "rss": f"{search_kw} fact check official statement",
                "github": clean_q,
            }

        if domain == "brand":
            return {
                "reddit": f"{clean_q} (scam OR \"fake review\" OR counterfeit OR complaint OR boycott)",
                "twitter": f"{clean_q} (scam OR boycott OR counterfeit OR fake OR lawsuit)",
                "youtube": f"{clean_q} (fake vs real OR scam review exposé OR defect)",
                "news": f"{clean_q} (recall OR counterfeit OR lawsuit OR scam OR investigation OR controversy)",
                "rss": f"{clean_q} press release recall statement official announcement",
                "github": clean_q,
            }

        if domain == "personal":
            return {
                "reddit": f"{clean_q} (scandal OR controversy OR impersonation OR fake OR leak)",
                "twitter": f"{clean_q} (deepfake OR impersonation OR scam OR fake OR leaked)",
                "youtube": f"{clean_q} (deepfake OR fake video OR AI voice OR controversy)",
                "news": f"{clean_q} (statement OR allegations OR lawsuit OR impersonation OR deepfake)",
                "rss": f"{clean_q} official statement announcement clarification",
                "github": clean_q,
            }

        if domain == "trending":
            return {
                "reddit": f"{clean_q} (trending OR viral OR controversy OR rumor OR news)",
                "twitter": f"{clean_q} (trending OR viral OR breaking OR controversy)",
                "youtube": f"{clean_q} viral trending news update reaction",
                "news": f"{clean_q} trending OR viral OR latest OR controversy OR announcement",
                "rss": f"{clean_q} latest news developments trending",
                "github": clean_q,
            }

        # General / unknown domain — pass through unmodified
        return {
            "reddit": clean_q,
            "twitter": clean_q,
            "youtube": clean_q,
            "news": clean_q,
            "github": clean_q,
            "rss": clean_q,
        }

    def build_financial_query_classes(self, ticker: str, company: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Generate structured classes of financial research queries:
        - General news
        - Financial results & earnings
        - Corporate & regulatory filings
        - Risk & controversies
        - Market narrative & investor sentiment
        - Contradiction verification
        """
        clean_ticker = ticker.upper().replace(".NS", "").replace(".BO", "")
        comp = company or TICKER_NAME_MAP.get(ticker.upper(), TICKER_NAME_MAP.get(clean_ticker, clean_ticker))

        return {
            "general_news": [
                f"{comp} latest news",
                f"{comp} today developments",
            ],
            "financial": [
                f"{comp} earnings results revenue",
                f"{comp} financial guidance analyst expectations",
            ],
            "corporate_filings": [
                f"{comp} investor relations announcement",
                f"{comp} regulatory filing SEBI SEC",
            ],
            "risk_investigation": [
                f"{comp} investigation controversy debt",
                f"{comp} credit downgrade rumor probe",
            ],
            "market_narrative": [
                f"${clean_ticker} investor sentiment discussion",
                f"{comp} stock market rumor social media",
            ],
            "contradictions": [
                f"{comp} positive outlook growth",
                f"{comp} negative outlook risks",
                f"{comp} rumor false debunked confirmed",
            ],
        }

    def build_brand_query_classes(self, brand: str, product: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Generate structured classes of brand protection & threat investigation queries:
        - General reputation
        - Counterfeit & unauthorized listings
        - Scam & phishing promotions
        - Brand impersonation & fake support
        - Review manipulation & consumer complaints
        - Regulatory, legal & product safety
        """
        target = f"{brand} {product}".strip() if product and product.lower() != brand.lower() else brand.strip()

        return {
            "general_reputation": [
                f"{target} latest news",
                f"{target} controversy reputation complaints",
            ],
            "counterfeit": [
                f"{target} counterfeit fake products",
                f"{target} unauthorized seller fake store clone listing",
            ],
            "phishing_scam": [
                f"{target} scam fake website phishing",
                f"{target} fake giveaway promotion fraud",
            ],
            "impersonation": [
                f"{target} fake account impersonation",
                f"{target} fake customer support handle verified",
            ],
            "reviews": [
                f"{target} fake reviews review manipulation",
                f"{target} review bombing customer complaints",
            ],
            "regulatory_legal": [
                f"{target} lawsuit investigation regulator",
                f"{target} product recall safety warning",
            ],
        }

    def build_personal_query_classes(
        self,
        name: str,
        aliases: Optional[List[str]] = None,
        handles: Optional[Dict[str, str]] = None,
        category: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Generate structured classes of personal threat investigation queries:
        - General public discourse & news
        - Impersonation & fake profiles
        - Phishing & scam campaigns
        - Deepfake & synthetic media claims
        - Reputation attacks, false claims & rumors
        - Publicly exposed breach/doxxing mentions
        """
        clean_name = name.strip()
        alias_terms = " OR ".join([f'"{a.strip()}"' for a in (aliases or []) if a.strip()])
        name_clause = f'("{clean_name}" OR {alias_terms})' if alias_terms else f'"{clean_name}"'

        twitter_handle = (handles or {}).get("twitter", "").lstrip("@")
        handle_clause = f" @{twitter_handle}" if twitter_handle else ""

        return {
            "general": [
                f"{name_clause} latest news",
                f"{name_clause} announcement public statement",
            ],
            "impersonation": [
                f"{name_clause} fake account impersonation",
                f"{name_clause} fake profile verified{handle_clause}",
                f"fake {clean_name} account support",
            ],
            "phishing_scam": [
                f"{name_clause} scam fake giveaway",
                f"{name_clause} phishing fraudulent investment crypto",
                f"{name_clause} fake offer money transaction",
            ],
            "deepfake_synthetic": [
                f"{name_clause} deepfake AI voice clone",
                f"{name_clause} fake video manipulated audio synthetic",
            ],
            "reputation_claims": [
                f"{name_clause} controversy allegations",
                f"{name_clause} false claim rumor smear campaign",
            ],
            "doxxing_privacy": [
                f"{name_clause} leaked data breach document",
                f"{name_clause} personal information leak public paste",
            ],
        }

    def build_trending_query_classes(
        self,
        query: str,
        is_discovery: bool = False,
        category: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Generate structured classes of trend intelligence & discovery queries.
        
        Supports two operational modes:
        1. Discovery Mode: Unsupervised discovery across regions/domains
        2. Entity Mode: Deep trend intelligence on a star, project, company, or topic
        """
        clean_q = query.strip()
        disc_indicators = [
            "what's trending", "whats trending", "trending in", "trending today",
            "viral today", "viral in", "current trends", "top trends", "today's trends"
        ]
        auto_discovery = is_discovery or any(ind in clean_q.lower() for ind in disc_indicators)

        if auto_discovery:
            # Extract region or domain if mentioned
            topic_str = clean_q
            for ind in disc_indicators:
                topic_str = re.sub(re.escape(ind), "", topic_str, flags=re.IGNORECASE).strip()
            topic_str = re.sub(r'^(in|for|across|of)\s+', '', topic_str, flags=re.IGNORECASE).strip()
            region_or_domain = topic_str if topic_str else (category or "India")

            return {
                "regional_trends": [
                    f"trending {region_or_domain} today",
                    f"viral news {region_or_domain} today",
                ],
                "domain_trends": [
                    f"top trends {region_or_domain} social media",
                    f"popular discussions {region_or_domain} today",
                ],
                "breaking_headlines": [
                    f"breaking news {region_or_domain} today",
                    f"top headlines {region_or_domain}",
                ],
                "social_momentum": [
                    f"viral social media {region_or_domain} buzz",
                    f"trending topics {region_or_domain} twitter reddit",
                ],
            }

        # Entity Mode
        return {
            "general_buzz": [
                f'"{clean_q}" latest news updates',
                f'"{clean_q}" today developments',
            ],
            "viral_moments": [
                f'"{clean_q}" viral trending social media',
                f'"{clean_q}" viral video moment clip',
            ],
            "controversy_rumors": [
                f'"{clean_q}" controversy rumors allegations drama',
                f'"{clean_q}" backlash statement explanation',
            ],
            "announcements_projects": [
                f'"{clean_q}" announcement project release trailer interview',
                f'"{clean_q}" official confirmation upcoming',
            ],
            "community_discourse": [
                f'"{clean_q}" fan reactions discussion reddit',
                f'"{clean_q}" public opinion social discourse',
            ],
            "claim_verification": [
                f'"{clean_q}" fact check debunked false rumor true',
                f'"{clean_q}" claims verified official clarification',
            ],
        }
