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


from dataclasses import dataclass, field


@dataclass
class RouteDecision:
    """
    Canonical route decision specifying the primary and fallback backends,
    retrieval mode, timeout, authentication status, and policy version.
    """
    request_id: str
    platform: str
    route_class: str
    primary_backend: str
    fallback_backends: List[str]
    retrieval_mode: str
    authentication_required: bool
    max_attempts: int
    timeout_ms: int
    reason: str
    policy_version: str = "policy_d_v3"
    is_walled_garden: bool = False
    requires_search_discovery: bool = False
    browser_rescue_permitted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "platform": self.platform,
            "route_class": self.route_class,
            "primary_backend": self.primary_backend,
            "fallback_backends": self.fallback_backends,
            "retrieval_mode": self.retrieval_mode,
            "authentication_required": self.authentication_required,
            "max_attempts": self.max_attempts,
            "timeout_ms": self.timeout_ms,
            "reason": self.reason,
            "policy_version": self.policy_version,
            "is_walled_garden": self.is_walled_garden,
            "requires_search_discovery": self.requires_search_discovery,
            "browser_rescue_permitted": self.browser_rescue_permitted,
        }


class RoutePolicyEngine:
    """
    Determines the optimal, smallest appropriate route for a candidate or channel request.
    Prevents doomed requests and provides transparent telemetry reasons.
    """

    @classmethod
    def decide_route(
        cls,
        platform: str,
        request_id: str = "",
        task_type: str = "SEARCH",
        is_url: bool = False
    ) -> RouteDecision:
        """
        Authoritative routing decision generator enforcing Policy D.
        """
        ch = platform.lower().strip()

        if ch == "github":
            return RouteDecision(
                request_id=request_id,
                platform="github",
                route_class=RouteClass.NATIVE_API.value,
                primary_backend="gh_api",
                fallback_backends=["web_search_index"],
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                authentication_required=False,
                max_attempts=2,
                timeout_ms=5000,
                reason="Native GitHub API / gh tool provides deterministic structured metadata",
                policy_version="policy_d_v3",
                is_walled_garden=False,
                requires_search_discovery=False,
                browser_rescue_permitted=False,
            )

        if ch == "reddit":
            return RouteDecision(
                request_id=request_id,
                platform="reddit",
                route_class=RouteClass.SPECIALIST_ADAPTER.value,
                primary_backend="arctic_shift",
                fallback_backends=["web_search_index"],
                retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
                authentication_required=False,
                max_attempts=2,
                timeout_ms=7000,
                reason="Zero-auth Arctic Shift public mirror; avoids doomed unauth Reddit JSON API",
                policy_version="policy_d_v3",
                is_walled_garden=False,
                requires_search_discovery=not is_url,
                browser_rescue_permitted=False,
            )

        if ch in ("twitter", "x"):
            return RouteDecision(
                request_id=request_id,
                platform="twitter",
                route_class=RouteClass.SPECIALIST_ADAPTER.value,
                primary_backend="fxtwitter",
                fallback_backends=["web_search_index"],
                retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
                authentication_required=False,
                max_attempts=2,
                timeout_ms=6000,
                reason="Zero-auth FxTwitter public status mirror; avoids rate-limited login walls",
                policy_version="policy_d_v3",
                is_walled_garden=False,
                requires_search_discovery=not is_url,
                browser_rescue_permitted=False,
            )

        if ch == "youtube":
            return RouteDecision(
                request_id=request_id,
                platform="youtube",
                route_class=RouteClass.SPECIALIST_ADAPTER.value,
                primary_backend="yt_dlp_in_process",
                fallback_backends=["web_search_index"],
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                authentication_required=False,
                max_attempts=2,
                timeout_ms=10000,
                reason="In-process yt-dlp Python import; eliminates 848ms process spawn overhead",
                policy_version="policy_d_v3",
                is_walled_garden=False,
                requires_search_discovery=False,
                browser_rescue_permitted=False,
            )

        if ch in WALLED_GARDEN_PLATFORMS:
            return RouteDecision(
                request_id=request_id,
                platform=ch,
                route_class=RouteClass.SEARCH_DISCOVERY.value,
                primary_backend="search_discovery",
                fallback_backends=[],
                retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                authentication_required=False,
                max_attempts=1,
                timeout_ms=6000,
                reason=WALLED_GARDEN_PLATFORMS[ch],
                policy_version="policy_d_v3",
                is_walled_garden=True,
                requires_search_discovery=True,
                browser_rescue_permitted=False,
            )

        # Default general web / news / rss
        return RouteDecision(
            request_id=request_id,
            platform="web",
            route_class=RouteClass.SCRAPLING_HTTP.value,
            primary_backend="scrapling_http",
            fallback_backends=["playwright_rescue", "web_search_index"],
            retrieval_mode=RetrievalMode.WEB_READER.value,
            authentication_required=False,
            max_attempts=2,
            timeout_ms=8000,
            reason="Policy D: Scrapling HTTP primary; Playwright strictly secondary rescue",
            policy_version="policy_d_v3",
            is_walled_garden=False,
            requires_search_discovery=False,
            browser_rescue_permitted=True,
        )

    @classmethod
    def resolve_channel_route(cls, channel: str) -> Dict[str, Any]:
        """
        Determine the primary and fallback route for a given channel name.
        Maintains backward compatibility with legacy consumers.
        """
        decision = cls.decide_route(platform=channel)
        return {
            "route_class": decision.route_class,
            "primary_backend": decision.primary_backend,
            "fallback_backend": decision.fallback_backends[0] if decision.fallback_backends else None,
            "reason": decision.reason,
            "retrieval_mode": decision.retrieval_mode,
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
