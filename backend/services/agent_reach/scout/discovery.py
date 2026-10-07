"""
Aegis Protocol — Scout Source Discovery Engine
==============================================
Discovers candidate sources across multiple search and platform indices.
Never assumes search rank = truth: produces prioritized CandidateSource pools
for subsequent hard gating, full-content acquisition, and semantic ranking.
"""

import logging
import re
import urllib.parse
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
from bs4 import BeautifulSoup

from backend.services.agent_reach.scout.models import CandidateSource, ScoutSourceRequest
from backend.services.agent_reach.scout.transport import scout_transport
from backend.services.agent_reach.native.source_discovery import (
    calculate_candidate_score,
    check_entity_semantic_match,
    extract_reddit_source,
    extract_x_source,
    is_valid_content_source,
    resolve_bing_redirect,
)

logger = logging.getLogger(__name__)


def clean_url(url: str) -> str:
    """Normalize and strip tracking parameters from discovered URLs."""
    if not url:
        return ""
    resolved = resolve_bing_redirect(url.strip())
    try:
        parsed = urllib.parse.urlparse(resolved)
        # Strip common tracking query params
        q_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
        tracking_keys = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "gclid", "fbclid", "msclkid", "ref", "spref", "feature"
        }
        filtered = {k: v for k, v in q_params.items() if k.lower() not in tracking_keys}
        new_query = urllib.parse.urlencode(filtered, doseq=True)
        return urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            new_query,
            ""  # strip fragment
        ))
    except Exception:
        return resolved


class DiscoveryStrategy(ABC):
    """Abstract base class for independent discovery routes."""

    @abstractmethod
    def discover(self, request: ScoutSourceRequest, limit: int = 5) -> List[CandidateSource]:
        pass


class BingDiscovery(DiscoveryStrategy):
    """Discovers web and news sources via Bing index."""

    def discover(self, request: ScoutSourceRequest, limit: int = 5) -> List[CandidateSource]:
        candidates: List[CandidateSource] = []
        q = request.query.strip()
        if request.target_entity and request.target_entity.lower() not in q.lower():
            q = f"{request.target_entity} {q}"
        encoded_q = urllib.parse.quote_plus(q)
        url = f"https://www.bing.com/search?q={encoded_q}&count={max(limit * 2, 10)}"

        status, text, _, _, err = scout_transport.get(url, timeout=8.0)
        if status != 200 or not text:
            logger.debug(f"[BingDiscovery] Query '{q}' returned status {status}, error: {err}")
            return candidates

        soup = BeautifulSoup(text, "html.parser")
        items = soup.select("li.b_algo")
        for rank, item in enumerate(items[:limit * 2]):
            a_tag = item.select_one("h2 a")
            if not a_tag:
                continue
            raw_url = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            caption = item.select_one(".b_caption p, .b_snippet, p")
            snippet = caption.get_text(strip=True) if caption else ""

            norm_url = clean_url(raw_url)
            if not norm_url or not norm_url.startswith("http"):
                continue

            candidates.append(CandidateSource(
                url=norm_url,
                canonical_url=norm_url,
                platform="web",
                source_type="article",
                external_id=norm_url,
                title=title,
                snippet=snippet,
                discovery_engine="bing",
                discovery_rank=rank + 1,
                metadata={"raw_href": raw_url}
            ))

        return candidates


class YahooDiscovery(DiscoveryStrategy):
    """Discovers web and financial reporting via Yahoo search index."""

    def discover(self, request: ScoutSourceRequest, limit: int = 5) -> List[CandidateSource]:
        candidates: List[CandidateSource] = []
        q = request.query.strip()
        encoded_q = urllib.parse.quote_plus(q)
        url = f"https://search.yahoo.com/search?p={encoded_q}&n={max(limit * 2, 10)}"

        status, text, _, _, err = scout_transport.get(url, timeout=8.0)
        if status != 200 or not text:
            return candidates

        soup = BeautifulSoup(text, "html.parser")
        results = soup.select(".algo-sr, .dd.algo, div.algo")
        for rank, r in enumerate(results[:limit * 2]):
            a_tag = r.select_one("h3 a, a.fz-m")
            if not a_tag:
                continue
            raw_url = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            snippet_elem = r.select_one(".compText, p, .fc-2nd")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            norm_url = clean_url(raw_url)
            if not norm_url or not norm_url.startswith("http"):
                continue

            candidates.append(CandidateSource(
                url=norm_url,
                canonical_url=norm_url,
                platform="news",
                source_type="article",
                external_id=norm_url,
                title=title,
                snippet=snippet,
                discovery_engine="yahoo",
                discovery_rank=rank + 1,
            ))

        return candidates


class SocialDiscovery(DiscoveryStrategy):
    """Discovers public Reddit threads and X statuses via site-scoped search queries."""

    def discover(self, request: ScoutSourceRequest, limit: int = 5) -> List[CandidateSource]:
        if not request.allow_social:
            return []

        candidates: List[CandidateSource] = []
        entity = request.target_entity or request.query
        platforms = ["reddit.com", "x.com"] if not request.platform_hint else [request.platform_hint]

        for p in platforms:
            site_filter = "site:reddit.com" if "reddit" in p else "site:x.com"
            q = f"{site_filter} {entity} {request.query}".strip()
            encoded_q = urllib.parse.quote_plus(q)
            search_url = f"https://www.bing.com/search?q={encoded_q}&count=8"

            status, text, _, _, _ = scout_transport.get(search_url, timeout=7.0)
            if status != 200 or not text:
                continue

            soup = BeautifulSoup(text, "html.parser")
            for rank, item in enumerate(soup.select("li.b_algo")[:8]):
                a = item.select_one("h2 a")
                if not a:
                    continue
                raw_href = a.get("href", "")
                title = a.get_text(strip=True)
                snippet_elem = item.select_one(".b_caption p, p")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                if "reddit" in p:
                    res = extract_reddit_source(raw_href, query=request.query)
                    if res:
                        candidates.append(CandidateSource(
                            url=res.canonical_url,
                            canonical_url=res.canonical_url,
                            platform="reddit",
                            source_type=res.source_type,
                            external_id=res.external_id,
                            title=title,
                            snippet=snippet,
                            discovery_engine="bing_social",
                            discovery_rank=rank + 1,
                            subreddit=res.subreddit,
                            author=res.handle,
                        ))
                elif "x.com" in p or "twitter" in p:
                    res = extract_x_source(raw_href, query=request.query)
                    if res:
                        candidates.append(CandidateSource(
                            url=res.canonical_url,
                            canonical_url=res.canonical_url,
                            platform="twitter",
                            source_type=res.source_type,
                            external_id=res.external_id,
                            title=title,
                            snippet=snippet,
                            discovery_engine="bing_social",
                            discovery_rank=rank + 1,
                            handle=res.handle,
                        ))

        return candidates


class PrimaryFilingDiscovery(DiscoveryStrategy):
    """Discovers primary disclosures, SEC EDGAR filings, and corporate IR releases."""

    def discover(self, request: ScoutSourceRequest, limit: int = 5) -> List[CandidateSource]:
        candidates: List[CandidateSource] = []
        entity = request.target_entity or ""
        ticker = request.tickers[0] if request.tickers else ""
        if not entity and not ticker:
            return candidates

        q = f'("{entity}" OR "{ticker}") (site:sec.gov OR "investor relations" OR "quarterly results" OR "press release")'
        encoded_q = urllib.parse.quote_plus(q)
        search_url = f"https://www.bing.com/search?q={encoded_q}&count=6"

        status, text, _, _, _ = scout_transport.get(search_url, timeout=7.0)
        if status != 200 or not text:
            return candidates

        soup = BeautifulSoup(text, "html.parser")
        for rank, item in enumerate(soup.select("li.b_algo")[:limit]):
            a = item.select_one("h2 a")
            if not a:
                continue
            raw_href = a.get("href", "")
            title = a.get_text(strip=True)
            snippet_elem = item.select_one(".b_caption p, p")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            norm_url = clean_url(raw_href)
            if not norm_url.startswith("http"):
                continue

            candidates.append(CandidateSource(
                url=norm_url,
                canonical_url=norm_url,
                platform="primary_filing",
                source_type="filing" if "sec.gov" in norm_url else "press_release",
                external_id=norm_url,
                title=title,
                snippet=snippet,
                discovery_engine="primary_discovery",
                discovery_rank=rank + 1,
                metadata={"is_primary_lead": True}
            ))

        return candidates


class ScoutDiscoveryEngine:
    """
    Coordinates multi-strategy discovery, removes duplicates, and generates
    a candidate source pool for Scout.
    """

    def __init__(self):
        self.strategies: Dict[str, DiscoveryStrategy] = {
            "bing": BingDiscovery(),
            "yahoo": YahooDiscovery(),
            "social": SocialDiscovery(),
            "primary": PrimaryFilingDiscovery(),
        }

    def discover_candidates(self, request: ScoutSourceRequest) -> List[CandidateSource]:
        """Run adaptive discovery based on requested source tiers and task importance."""
        all_candidates: List[CandidateSource] = []
        seen_urls: Set[str] = set()

        # 1. Primary Disclosures if relevant or high importance
        if request.target_entity or request.tickers:
            p_cands = self.strategies["primary"].discover(request, limit=3)
            for c in p_cands:
                if c.canonical_url not in seen_urls:
                    seen_urls.add(c.canonical_url)
                    all_candidates.append(c)

        # 2. Web Search Discovery (Bing)
        bing_cands = self.strategies["bing"].discover(request, limit=request.max_candidates)
        for c in bing_cands:
            if c.canonical_url not in seen_urls:
                seen_urls.add(c.canonical_url)
                all_candidates.append(c)

        # 3. Yahoo Financial Search
        if len(all_candidates) < request.max_candidates * 2:
            yahoo_cands = self.strategies["yahoo"].discover(request, limit=request.max_candidates)
            for c in yahoo_cands:
                if c.canonical_url not in seen_urls:
                    seen_urls.add(c.canonical_url)
                    all_candidates.append(c)

        # 4. Social Signals (Reddit / X) if requested
        if request.allow_social:
            social_cands = self.strategies["social"].discover(request, limit=4)
            for c in social_cands:
                if c.canonical_url not in seen_urls:
                    seen_urls.add(c.canonical_url)
                    all_candidates.append(c)

        # 5. Preliminary scoring
        for c in all_candidates:
            c.candidate_score = self._score_candidate(c, request)

        # Sort descending by preliminary score
        all_candidates.sort(key=lambda x: x.candidate_score, reverse=True)
        return all_candidates[:request.max_candidates * 2]

    def _score_candidate(self, cand: CandidateSource, request: ScoutSourceRequest) -> float:
        """Calculate preliminary relevance score."""
        score = 0.50
        text = f"{cand.title} {cand.snippet}".lower()
        ent = (request.target_entity or "").lower()

        if ent:
            matched, weight = check_entity_semantic_match(text, ent)
            if matched:
                score += 0.25 * weight
            else:
                score -= 0.20

        for t in request.tickers:
            if t.lower() in text or f"${t.lower()}" in text:
                score += 0.15

        if cand.platform == "primary_filing" or "sec.gov" in cand.canonical_url:
            score += 0.20

        return max(0.05, min(0.99, score))


scout_discovery = ScoutDiscoveryEngine()
