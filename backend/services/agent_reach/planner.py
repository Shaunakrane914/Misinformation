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
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
            return {
                "reddit": f"{clean_ticker} (crash OR scam OR fraud OR short OR plunge OR earnings)",
                "twitter": f"${clean_ticker} OR {clean_ticker} rumor OR crash OR short",
                "youtube": f"{clean_ticker} stock crash analysis",
                "news": f"{clean_ticker} stock investigation OR crash OR SEC OR results",
                "rss": f"{clean_ticker} financial earnings regulatory",
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
                "reddit": f"{clean_q} (scam OR fake review OR counterfeit OR refund)",
                "twitter": f"{clean_q} scam OR boycott OR counterfeit OR fake",
                "youtube": f"{clean_q} fake vs real OR scam review exposé",
                "news": f"{clean_q} recall OR counterfeit OR lawsuit OR scam",
                "rss": f"{clean_q} press release recall statement",
                "github": clean_q,
            }

        if domain == "personal":
            return {
                "reddit": f"{clean_q} (scandal OR controversy OR leak OR arrested)",
                "twitter": f"{clean_q} leaked OR audio OR deepfake OR exposed",
                "youtube": f"{clean_q} deepfake OR leaked audio OR speech analysis",
                "news": f"{clean_q} statement OR allegations OR defamation OR lawsuit",
                "rss": f"{clean_q} official statement legal",
                "github": clean_q,
            }

        if domain == "trending":
            return {
                "reddit": f"{clean_q} rumor OR controversy",
                "twitter": f"{clean_q} viral OR drama OR trending",
                "youtube": f"{clean_q} viral clips drama",
                "news": f"{clean_q} viral OR buzz OR controversy",
                "rss": f"{clean_q} viral trending controversy",
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

