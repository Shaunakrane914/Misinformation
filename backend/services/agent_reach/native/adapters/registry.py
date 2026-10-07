"""
Aegis Protocol — Adapter Registry for Route Decision Execution
==============================================================
The authoritative registry mapping RouteDecision.primary_backend and
platform contracts directly to concrete PlatformAdapter instances.
Eliminates all dispatch contradictions and prevents walled-garden fall-through bugs.
"""

import logging
from typing import Dict, List, Optional

from backend.services.agent_reach.channels import CandidateSource
from backend.services.agent_reach.native.adapters.base import PlatformAdapter
from backend.services.agent_reach.native.adapters.github import GitHubAdapter
from backend.services.agent_reach.native.adapters.reddit import RedditAdapter
from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
from backend.services.agent_reach.native.adapters.twitter import TwitterAdapter
from backend.services.agent_reach.native.adapters.web import WebAdapter
from backend.services.agent_reach.native.adapters.youtube import YouTubeAdapter
from backend.services.agent_reach.native.route_policy import RouteDecision, WALLED_GARDEN_PLATFORMS

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """
    Central registry for platform adapters.
    Guarantees that RouteDecision.primary_backend unambiguously maps to the intended adapter.
    """

    def __init__(self):
        self._adapters_by_backend: Dict[str, PlatformAdapter] = {}
        self._adapters_by_platform: Dict[str, PlatformAdapter] = {}

        # Default singleton adapter instances
        self.web_adapter = WebAdapter()
        self.reddit_adapter = RedditAdapter()
        self.twitter_adapter = TwitterAdapter()
        self.youtube_adapter = YouTubeAdapter()
        self.github_adapter = GitHubAdapter()
        self.search_adapter = SearchDiscoveryAdapter()

        self._register_defaults()

    def _register_defaults(self):
        # Web
        self.register(self.web_adapter, ["scrapling_http", "scrapling", "playwright_rescue", "web_reader"])
        # Reddit
        self.register(self.reddit_adapter, ["arctic_shift", "pullpush", "reddit_json"])
        # Twitter / X
        self.register(self.twitter_adapter, ["fxtwitter", "vxtwitter", "twitter_syndication"])
        # YouTube
        self.register(self.youtube_adapter, ["yt_dlp_in_process", "yt_dlp_subprocess", "rapidapi_youtube"])
        # GitHub
        self.register(self.github_adapter, ["gh_api", "github_rest", "gh_cli"])
        # Search / Walled Gardens
        self.register(
            self.search_adapter,
            ["search_discovery", "search_index_discovery", "search_index_fallback", "bing_yahoo", "web_search_index"]
        )

    def register(self, adapter: PlatformAdapter, backend_ids: List[str]):
        """Register an adapter for its platform and associated backend IDs."""
        self._adapters_by_platform[adapter.platform.lower()] = adapter
        for b_id in backend_ids:
            self._adapters_by_backend[b_id.lower()] = adapter

    def get_adapter_by_backend(self, backend_id: str) -> Optional[PlatformAdapter]:
        """Lookup adapter directly by backend identifier."""
        return self._adapters_by_backend.get((backend_id or "").lower())

    def get_adapter_by_platform(self, platform: str) -> Optional[PlatformAdapter]:
        """Lookup adapter by platform name."""
        return self._adapters_by_platform.get((platform or "").lower())

    def get_adapter_for_candidate(self, candidate: CandidateSource) -> PlatformAdapter:
        """Lookup adapter appropriate for a candidate source."""
        plat = (candidate.platform or "").lower()
        if plat in WALLED_GARDEN_PLATFORMS:
            return self.search_adapter
        if plat == "reddit":
            return self.reddit_adapter
        if plat in ("twitter", "x"):
            return self.twitter_adapter
        if plat == "youtube":
            return self.youtube_adapter
        if plat == "github":
            return self.github_adapter
        return self.web_adapter

    def get_adapter_for_decision(
        self,
        decision: RouteDecision,
        candidate: Optional[CandidateSource] = None
    ) -> PlatformAdapter:
        """
        Derive the exact runtime adapter directly from the authoritative RouteDecision.
        Strictly prevents walled-garden fall-through bugs into Scrapling.
        """
        # 1. Walled garden platforms MUST route to search discovery
        if decision.is_walled_garden or decision.primary_backend == "search_discovery":
            return self.search_adapter

        # 2. Candidate platform check for walled gardens
        if candidate:
            cand_plat = (candidate.platform or "").lower()
            if cand_plat in WALLED_GARDEN_PLATFORMS:
                return self.search_adapter

        # 3. Direct backend mapping
        primary_b = (decision.primary_backend or "").lower()
        adapter = self._adapters_by_backend.get(primary_b)
        if adapter is not None:
            return adapter

        # 4. Platform fallback mapping
        plat = (decision.platform or "").lower()
        adapter = self._adapters_by_platform.get(plat)
        if adapter is not None:
            return adapter

        # 5. Candidate platform fallback
        if candidate:
            return self.get_adapter_for_candidate(candidate)

        # 6. Default to web adapter
        return self.web_adapter


# Global adapter registry singleton
adapter_registry = AdapterRegistry()
