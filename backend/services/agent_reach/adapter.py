"""
Aegis Protocol — Agent Reach Service & Adapter
================================================
Central internet evidence-acquisition capability layer for Aegis.
Owns channel coordination, bounded concurrent retrieval, deduplication,
source independence clustering, and SSRF-hardened reading.
Preserves full backward compatibility with the legacy AgentReachScraper.
"""

import concurrent.futures
import logging
import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from backend.services.agent_reach.channels import (
    Channel,
    ChannelStatus,
    EvidenceFragment,
    RetrievalResult,
)
from backend.services.agent_reach.channels_impl import (
    AuthenticatedOptionalChannel,
    GitHubChannel,
    JinaReaderChannel,
    NewsChannel,
    RedditChannel,
    RssChannel,
    TwitterChannel,
    YouTubeChannel,
)
from backend.services.agent_reach.planner import RetrievalPlan, RetrievalPlanner
from backend.services.agent_reach.registry import CapabilityRegistry
from backend.services.url_validator import is_safe_url

logger = logging.getLogger(__name__)

# Known news wire syndication signatures for source-independence clustering
SYNDICATION_MARKERS = [
    "reuters", "associated press", "ap news", "bloomberg",
    "pr newswire", "business wire", "globe newswire", "afp",
]


class AgentReachService:
    """
    Canonical internet evidence acquisition service.

    Orchestrates retrieval across heterogeneous channels (web, news, social,
    video, code repositories), enforces timeout budgets, sanitizes external
    inputs, normalizes fragments, and detects syndication clusters.
    """

    def __init__(self):
        self.registry = CapabilityRegistry()
        self.planner = RetrievalPlanner()
        self._register_default_channels()
        logger.info("[AgentReachService] Initialized with 14 tracked channels and domain planner")

    def _register_default_channels(self) -> None:
        """Register primary zero-config channels and optional authenticated channels."""
        # Core zero-config channels (cloud-ready)
        self.registry.register(RedditChannel())
        self.registry.register(TwitterChannel())
        self.registry.register(YouTubeChannel())
        self.registry.register(NewsChannel())
        self.registry.register(JinaReaderChannel())
        self.registry.register(GitHubChannel())
        self.registry.register(RssChannel())

        # Optional / authenticated channels (gracefully report status)
        self.registry.register(AuthenticatedOptionalChannel("linkedin", "LinkedIn", "LINKEDIN_SESSION_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("bilibili", "Bilibili", "BILIBILI_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("xueqiu", "Xueqiu", "XUEQIU_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("xiaohongshu", "Xiaohongshu", "XIAOHONGSHU_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("instagram", "Instagram", "INSTAGRAM_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("facebook", "Facebook", "FACEBOOK_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("v2ex", "V2EX", "V2EX_TOKEN"))

    # ── Diagnostics & Capabilities ──────────────────────────────────────────

    def capabilities(self) -> Dict[str, Any]:
        """Return the complete channel capability inventory and server compatibility status."""
        cap_map = self.registry.capability_map()
        available_count = sum(1 for c in cap_map.values() if c["status"] == ChannelStatus.AVAILABLE.value)
        return {
            "service": "AgentReachService",
            "version": "2.0.0",
            "total_channels": len(cap_map),
            "available_channels": available_count,
            "channels": cap_map,
            "supported_domains": list(self.planner.DOMAIN_PRIORITIES.keys()),
        }

    def health(self) -> Dict[str, Any]:
        """Probe all registered channels and return a structured health report."""
        discovery = self.registry.discover()
        healthy = sum(1 for s in discovery.values() if s == ChannelStatus.AVAILABLE.value)
        degraded = sum(1 for s in discovery.values() if s == ChannelStatus.DEGRADED.value)
        auth_req = sum(1 for s in discovery.values() if s == ChannelStatus.AUTH_REQUIRED.value)
        unavail = sum(1 for s in discovery.values() if s == ChannelStatus.UNAVAILABLE.value)
        return {
            "status": "HEALTHY" if healthy >= 3 else "DEGRADED",
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "healthy": healthy,
                "degraded": degraded,
                "auth_required": auth_req,
                "unavailable": unavail,
            },
            "channels": discovery,
        }

    # ── Safe Content Reading ────────────────────────────────────────────────

    def read(self, url: str, max_chars: int = 4000) -> Dict[str, Any]:
        """
        Safely fetch and parse a web document into clean markdown.
        Enforces strict SSRF validation before network transmission.
        """
        if not url:
            return {"status": "error", "error": "Empty URL provided", "url": ""}

        safe, reason = is_safe_url(url)
        if not safe:
            logger.warning(f"[AgentReachService] SSRF defense blocked URL: {url} ({reason})")
            return {
                "status": "blocked_ssrf",
                "error": f"URL blocked by SSRF defense: {reason}",
                "url": url,
            }

        try:
            reader = self.registry._channels.get("jina_reader")
            if reader:
                fragments = reader.search(url, limit=1)
                if fragments:
                    f = fragments[0]
                    return {
                        "status": "success",
                        "title": f.title,
                        "markdown": f.content[:max_chars],
                        "url": f.url,
                        "char_count": len(f.content),
                    }
        except Exception as e:
            logger.warning(f"[AgentReachService] Reader failed for {url}: {e}")

        # Fallback reading
        try:
            from backend.services.agent_reach_scraper import reach_scraper
            return reach_scraper.read_article_markdown(url, max_chars=max_chars)
        except Exception as e:
            return {"status": "error", "error": str(e), "url": url}

    # ── Core Retrieval Pipeline ─────────────────────────────────────────────

    def search_channel(self, channel_name: str, query: str, limit: int = 6) -> List[EvidenceFragment]:
        """Execute a targeted search on a single channel."""
        channel = self.registry._channels.get(channel_name)
        if not channel:
            logger.warning(f"[AgentReachService] Channel '{channel_name}' not registered")
            return []
        try:
            return channel.search(query, limit=limit)
        except Exception as e:
            logger.warning(f"[AgentReachService] Channel '{channel_name}' search failed: {e}")
            self.registry.mark_degraded(channel_name)
            return []

    def retrieve(
        self,
        query: str,
        domain: str = "general",
        channels: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        limit_per_channel: int = 6,
        timeout: float = 12.0,
    ) -> RetrievalResult:
        """
        Execute domain-planned, concurrent internet evidence retrieval.

        Pipeline:
        1. Query Planning (per-channel optimized queries)
        2. Source URL reading (SSRF safe)
        3. Parallel channel querying with bounded concurrency
        4. Deduplication & URL normalization
        5. Source independence & syndication grouping
        6. Source role & tier attribution
        """
        start_time = datetime.utcnow()
        clean_q = query.strip()

        # 1. Retrieval Planning
        plan = self.planner.plan(clean_q, domain=domain, include_channels=channels)
        logger.info(f"[AgentReachService] Plan for '{clean_q[:40]}...' (domain={domain}): channels={plan.channels_to_query}")

        # 2. Source Article Acquisition (if provided)
        source_doc = None
        if source_url:
            source_doc = self.read(source_url)

        # 3. Concurrent Retrieval across planned channels
        raw_fragments: List[EvidenceFragment] = []
        channel_health_map: Dict[str, str] = {}

        # Filter to healthy channels
        available_map = {c.name: c for c in self.registry.get_available(set(plan.channels_to_query))}

        def _fetch(ch_name: str) -> List[EvidenceFragment]:
            ch = available_map.get(ch_name)
            if not ch:
                return []
            q = plan.domain_queries.get(ch_name, clean_q)
            return ch.search(q, limit=limit_per_channel)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_channel = {
                executor.submit(_fetch, ch_name): ch_name
                for ch_name in plan.channels_to_query
                if ch_name in available_map
            }

            for future in concurrent.futures.as_completed(future_to_channel, timeout=timeout + 2.0):
                ch_name = future_to_channel[future]
                try:
                    res = future.result(timeout=timeout)
                    if res:
                        raw_fragments.extend(res)
                        channel_health_map[ch_name] = ChannelStatus.AVAILABLE.value
                    else:
                        channel_health_map[ch_name] = ChannelStatus.DEGRADED.value
                except Exception as e:
                    logger.warning(f"[AgentReachService] Channel {ch_name} timed out or failed: {e}")
                    channel_health_map[ch_name] = ChannelStatus.UNAVAILABLE.value
                    self.registry.mark_degraded(ch_name)

        # 4. Deduplication & Normalization
        deduped_fragments, dupes_removed = self._deduplicate_fragments(raw_fragments)

        # 5. Source Independence & Syndication Grouping
        independence_groups = self._cluster_source_independence(deduped_fragments)

        # 6. Assign semantic source roles
        self._assign_source_roles(deduped_fragments)

        result = RetrievalResult(
            query=clean_q,
            domain=domain,
            fragments=deduped_fragments,
            channel_health=channel_health_map,
            total_signals=len(deduped_fragments),
            retrieval_plan=plan.to_dict(),
            source_article=source_doc,
        )
        return result

    # ── Deduplication & Independence Logic ──────────────────────────────────

    def _normalize_url(self, raw_url: str) -> str:
        """Strip tracking parameters (utm_*, ref, etc.) and normalize URL for dedup."""
        if not raw_url:
            return ""
        try:
            parsed = urllib.parse.urlparse(raw_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            # Remove tracking params
            filtered = {k: v for k, v in query_params.items() if not k.startswith("utm_") and k not in ("ref", "fbclid")}
            clean_query = urllib.parse.urlencode(filtered, doseq=True)
            return urllib.parse.urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip("/"),
                parsed.params,
                clean_query,
                ""  # drop fragment
            ))
        except Exception:
            return raw_url.strip().lower()

    def _deduplicate_fragments(
        self,
        fragments: List[EvidenceFragment]
    ) -> (List[EvidenceFragment], int):
        """Deduplicate fragments across multiple search providers and channels."""
        seen_urls: Set[str] = set()
        seen_titles: Set[str] = set()
        unique: List[EvidenceFragment] = []
        dupes_count = 0

        for f in fragments:
            norm_url = self._normalize_url(f.url)
            norm_title = re.sub(r'[^a-zA-Z0-9]', '', f.title.lower())[:60]

            if norm_url and norm_url in seen_urls:
                dupes_count += 1
                continue
            if norm_title and len(norm_title) > 15 and norm_title in seen_titles:
                dupes_count += 1
                continue

            if norm_url:
                seen_urls.add(norm_url)
            if norm_title:
                seen_titles.add(norm_title)

            unique.append(f)

        return unique, dupes_count

    def _cluster_source_independence(
        self,
        fragments: List[EvidenceFragment]
    ) -> Dict[str, List[str]]:
        """
        Group syndicated stories to prevent duplicate confirmation counting.
        E.g., 4 outlets republishing the same AP wire are clustered into 1 group.
        """
        groups: Dict[str, List[str]] = {}

        for f in fragments:
            assigned_group = "independent"
            content_lower = (f.title + " " + f.snippet).lower()

            for marker in SYNDICATION_MARKERS:
                if marker in content_lower:
                    assigned_group = f"syndicated_{marker.replace(' ', '_')}"
                    break

            f.raw_metadata["source_independence_group"] = assigned_group
            groups.setdefault(assigned_group, []).append(f.url or f.title)

        return groups

    def _assign_source_roles(self, fragments: List[EvidenceFragment]) -> None:
        """Tag fragments with their forensic source role (PRIMARY, SECONDARY, etc.)."""
        primary_markers = [
            "sec.gov", "bseindia.com", "nseindia.com", "investor", "ir.",
            "tatamotors.com", "nvidia.com", "apple.com", "tesla.com",
            "regulatory filing", "investor relations", "annual report",
            "exchange filing", "press release", "official statement",
            "form 10-k", "form 10-q", "sebi.gov"
        ]
        financial_press = [
            "reuters", "bloomberg", "moneycontrol", "economictimes",
            "livemint", "business-standard", "financialexpress", "cnbc",
            "wsj", "ft.com", "apnews"
        ]

        for f in fragments:
            platform = f.platform.lower()
            method = f.retrieval_method.lower()
            url_lower = (f.url or "").lower()
            title_lower = (f.title or "").lower()
            combined_text = f"{url_lower} {title_lower}"

            if any(pm in combined_text for pm in primary_markers):
                f.raw_metadata["source_role"] = "PRIMARY"
                f.raw_metadata["source_tier"] = "TIER_1_OFFICIAL_FILING"
            elif "github" in platform or "github" in method:
                f.raw_metadata["source_role"] = "PRIMARY"
                f.raw_metadata["source_tier"] = "TIER_1_CODE_METADATA"
            elif any(fp in combined_text for fp in financial_press) or "news" in platform or "wire" in platform:
                f.raw_metadata["source_role"] = "SECONDARY"
                f.raw_metadata["source_tier"] = "TIER_2_FINANCIAL_PRESS"
            elif "reddit" in platform:
                f.raw_metadata["source_role"] = "COMMUNITY"
                f.raw_metadata["source_tier"] = "TIER_3_INVESTOR_COMMUNITY"
            elif "twitter" in platform:
                f.raw_metadata["source_role"] = "COMMENTARY"
                f.raw_metadata["source_tier"] = "TIER_3_SOCIAL_SIGNALS"
            elif "youtube" in platform:
                f.raw_metadata["source_role"] = "DIRECT_MEDIA"
                f.raw_metadata["source_tier"] = "TIER_2_VIDEO_ANALYSIS"
            elif "web article" in platform or "jina" in method:
                f.raw_metadata["source_role"] = "PRIMARY"
                f.raw_metadata["source_tier"] = "TIER_1_ORIGINAL_DOCUMENT"
            else:
                f.raw_metadata["source_role"] = "DISCOVERY"
                f.raw_metadata["source_tier"] = "TIER_3_AGGREGATE"

    # ── Backward Compatibility with legacy AgentReachScraper ───────────────

    def omni_scan(
        self,
        query: str = "",
        claim_text: str = "",
        domain: str = "general",
        target_company: str = None,
        include_platforms: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        limit_per_channel: int = 6,
    ) -> Dict[str, Any]:
        """
        Legacy omni_scan compatibility method.
        Accepts both 'query' and 'claim_text', returns identical dictionary shape
        with enhanced retrieval metadata.
        """
        target_q = query or claim_text
        res = self.retrieve(
            query=target_q,
            domain=domain,
            channels=include_platforms,
            source_url=source_url,
            limit_per_channel=limit_per_channel,
        )

        output = res.to_dict()
        # Add legacy top-level keys expected by existing agents and endpoints
        output["channels"] = res.channels
        output["items"] = res.items
        output["total_signals"] = len(res.fragments)
        return output

    def unified_scan(
        self,
        query: str,
        platforms: Optional[List[str]] = None,
        max_results_per_platform: int = 5,
    ) -> Dict[str, Any]:
        """Legacy unified_scan compatibility method."""
        return self.omni_scan(
            query=query,
            domain="general",
            include_platforms=platforms,
            limit_per_channel=max_results_per_platform,
        )

    def doctor(self) -> Dict[str, Any]:
        """Legacy doctor compatibility method."""
        return self.health()

    def read_article_markdown(self, url: str, max_chars: int = 4000) -> Dict[str, Any]:
        """Legacy read_article_markdown compatibility method."""
        return self.read(url, max_chars=max_chars)

    def search_reddit(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.search_channel("reddit", query, limit=limit)]

    def search_twitter(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.search_channel("twitter", query, limit=limit)]

    def search_youtube(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.search_channel("youtube", query, limit=limit)]

    def search_news(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.search_channel("news", query, limit=limit)]


# Canonical singleton instances for Aegis
agent_reach_service = AgentReachService()
reach_adapter = agent_reach_service
