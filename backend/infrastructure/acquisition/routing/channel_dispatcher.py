"""Channel dispatch orchestration with shared telemetry and error semantics."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

from backend.infrastructure.acquisition.routing.social_handlers import SocialChannelHandlers
from backend.infrastructure.acquisition.routing.standard_handlers import StandardChannelHandlers
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.agent_reach.native.channel_capabilities import get_capability
from backend.services.agent_reach.native.errors import AuthRequiredError

if TYPE_CHECKING:
    from backend.infrastructure.acquisition.routing.router import NativeRouter


class ChannelQueryDispatcher:
    """Selects a cohesive handler and applies channel-independent invariants."""

    SOCIAL_CHANNELS = {"reddit", "twitter", "x"}

    def __init__(self, router: "NativeRouter") -> None:
        self.router = router
        self.social = SocialChannelHandlers(router)
        self.standard = StandardChannelHandlers(router)

    def execute(
        self,
        platform: str,
        query: str,
        limit: int = 5,
        query_id: str = "",
        query_class: str = "",
        query_text: str = "",
        **kwargs: Any,
    ) -> Tuple[List[EvidenceFragment], Dict[str, Any]]:
        started = time.perf_counter()
        telemetry = self._new_telemetry(platform)
        fragments: List[EvidenceFragment] = []
        try:
            handler = self.social if platform in self.SOCIAL_CHANNELS else self.standard
            fragments = handler.execute(
                platform, query, limit, query_id, query_class, query_text or query,
                telemetry, **kwargs,
            )
        except AuthRequiredError as error:
            telemetry.update(status="AUTH_REQUIRED", error=str(error))
        except Exception as error:
            telemetry.update(status="FAILED", error=str(error))

        telemetry["latency_ms"] = int((time.perf_counter() - started) * 1000)
        self._apply_provenance_defaults(fragments, platform)
        return fragments, telemetry

    def _new_telemetry(self, platform: str) -> Dict[str, Any]:
        capability = get_capability(platform)
        status = self.router.doctor.get_channel_status(platform)
        backend = status.get("active_backend") or (capability.backends[0] if capability.backends else "default")
        return {
            "platform": platform,
            "backend": backend,
            "operation": f"{platform}.search",
            "status": "INITIATED",
            "fallback_used": False,
            "fallback_backend": None,
            "attempts": 1,
            "latency_ms": 0,
            "error": None,
        }

    @staticmethod
    def _apply_provenance_defaults(fragments: List[EvidenceFragment], platform: str) -> None:
        for fragment in fragments:
            if not getattr(fragment, "requested_channel", None):
                fragment.requested_channel = platform
            if not getattr(fragment, "actual_retrieval_channel", None):
                fragment.actual_retrieval_channel = getattr(fragment, "channel_name", None) or platform
