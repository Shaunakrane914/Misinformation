"""
Aegis Protocol — Empirically Validated Route Policy (Policy D)
==============================================================
Defines the authoritative routing decision matrix across platforms and channels.
Enforces the frozen production decision:
  1. Native API / Specialist Zero-Auth Public Mirror
  2. Scrapling HTTP / curl_cffi (General Web Primary)
  3. Playwright Rescue (Secondary, only on JS/client-side rendering failure)
  4. Search Index & Syndication Discovery (Walled Gardens & Fallback)

Blocks doomed unauthenticated paths and records selection rationales.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from backend.services.agent_reach.channels import CandidateSource, RetrievalMode


class RouteClass(str, Enum):
    NATIVE_API = "A_native_api"
    SPECIALIST_ADAPTER = "B_specialist_adapter"
    SCRAPLING_HTTP = "C_scrapling_http"
    PLAYWRIGHT_RESCUE = "D_playwright_rescue"
    SEARCH_DISCOVERY = "E_search_discovery"


# Platforms with walled gardens where unauthenticated scraping is doomed
WALLED_GARDEN_PLATFORMS = {
    "instagram": "Search index discovery required (Instaloader without auth doomed)",
    "facebook": "Search index discovery required (Direct scraping auth-walled)",
    "tiktok": "Search index discovery required (Direct page metadata incomplete)",
    "linkedin": "Search index discovery required (Zero-auth principle: no private session cookies)",
    "bilibili": "Search index discovery required (Unsigned native API empirically fails with HTTP 412)",
}


class RoutePolicyEngine:
    """
    Determines the optimal, smallest appropriate route for a candidate or channel request.
    Prevents doomed requests and provides transparent telemetry reasons.
    """

    @classmethod
    def resolve_channel_route(cls, channel: str) -> Dict[str, Any]:
        """
        Determine the primary and fallback route for a given channel name.
        """
        ch = channel.lower().strip()

        if ch == "github":
            return {
                "route_class": RouteClass.NATIVE_API.value,
                "primary_backend": "gh_api",
                "fallback_backend": "web_search_index",
                "reason": "Native GitHub API / gh tool provides deterministic structured metadata",
                "retrieval_mode": RetrievalMode.DIRECT_API.value,
            }

        if ch == "reddit":
            return {
                "route_class": RouteClass.SPECIALIST_ADAPTER.value,
                "primary_backend": "arctic_shift",
                "fallback_backend": "web_search_index",
                "reason": "Zero-auth Arctic Shift public mirror; avoids doomed unauth Reddit JSON API",
                "retrieval_mode": RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
            }

        if ch in ("twitter", "x"):
            return {
                "route_class": RouteClass.SPECIALIST_ADAPTER.value,
                "primary_backend": "fxtwitter",
                "fallback_backend": "web_search_index",
                "reason": "Zero-auth FxTwitter public status mirror; avoids rate-limited login walls",
                "retrieval_mode": RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
            }

        if ch == "youtube":
            return {
                "route_class": RouteClass.SPECIALIST_ADAPTER.value,
                "primary_backend": "yt_dlp_in_process",
                "fallback_backend": "web_search_index",
                "reason": "In-process yt-dlp Python import; eliminates 848ms process spawn overhead",
                "retrieval_mode": RetrievalMode.DIRECT_API.value,
            }

        if ch in WALLED_GARDEN_PLATFORMS:
            return {
                "route_class": RouteClass.SEARCH_DISCOVERY.value,
                "primary_backend": "search_discovery",
                "fallback_backend": None,
                "reason": WALLED_GARDEN_PLATFORMS[ch],
                "retrieval_mode": RetrievalMode.WEB_SEARCH_INDEX.value,
            }

        # Default general web / news / rss
        return {
            "route_class": RouteClass.SCRAPLING_HTTP.value,
            "primary_backend": "scrapling_http",
            "fallback_backend": "playwright_rescue",
            "reason": "Policy D: Scrapling HTTP primary; Playwright strictly secondary rescue",
            "retrieval_mode": RetrievalMode.WEB_READER.value,
        }

    @classmethod
    def should_attempt_playwright_rescue(
        cls,
        http_status: int,
        content_len: int,
        error_msg: Optional[str] = None
    ) -> bool:
        """
        Validate whether Playwright rescue is justified.
        Playwright is only invoked if lightweight HTTP encountered JS-rendering signs,
        anti-bot challenges, or an empty page shell (<250 chars).
        """
        if content_len < 250:
            return True
        if http_status in (403, 503):
            return True
        if error_msg:
            err_lower = error_msg.lower()
            if any(term in err_lower for term in ("javascript", "cloudflare", "challenge", "turnstile", "blocked")):
                return True
        return False
