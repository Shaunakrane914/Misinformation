"""Channel dispatch orchestration with shared telemetry and error semantics."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

from backend.infrastructure.acquisition.routing.social_handlers import SocialChannelHandlers
from backend.infrastructure.acquisition.routing.standard_handlers import StandardChannelHandlers
from backend.infrastructure.acquisition.network.http import ProviderHTTPError
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.agent_reach.native.channel_capabilities import get_capability
from backend.services.agent_reach.native.errors import AuthRequiredError
from backend.services.agent_reach.native.operation_capabilities import runtime_operation_capabilities

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
        platform, operation = runtime_operation_capabilities.normalize(platform, kwargs.get("operation", "search"))
        kwargs["operation"] = operation
        telemetry = self._new_telemetry(platform)
        telemetry["operation"] = f"{platform}.{operation}"
        assessment = runtime_operation_capabilities.assess(platform, operation)
        if limit <= 0 or assessment["decision"] in {"EXCLUDE", "DEFER_TEMPORARY"}:
            # A denied action is not a new provider failure: do not overwrite
            # the observation/cooldown that caused this decision.
            telemetry.update(
                status="AUTH_REQUIRED" if assessment["runtime_health"] == "AUTH_REQUIRED" else "SKIPPED",
                outcome="DEFERRED" if assessment["decision"] == "DEFER_TEMPORARY" else "EXCLUDED",
                content_class="NONE", error=assessment["reason"] if limit > 0 else "Result budget is zero",
                attempts=0, runtime_decision=assessment,
            )
            return [], telemetry
        fragments: List[EvidenceFragment] = []
        try:
            handler = self.social if platform in self.SOCIAL_CHANNELS else self.standard
            fragments = handler.execute(
                platform, query, limit, query_id, query_class, query_text or query,
                telemetry, **kwargs,
            )
        except AuthRequiredError as error:
            telemetry.update(status="AUTH_REQUIRED", error=str(error))
        except ProviderHTTPError as error:
            telemetry.update(
                status="FAILED",
                error=str(error),
                attempts=error.attempts,
                network_observed=error.network_observed,
                http_statuses=[] if error.status_code is None else [error.status_code],
                source_endpoints=[error.endpoint] if error.endpoint else [],
                retry_after_seconds=error.retry_after_seconds,
                rate_limit_remaining=error.rate_limit_remaining,
                rate_limit_reset_at=error.rate_limit_reset_at,
                failure_kind=error.failure_kind,
            )
        except Exception as error:
            telemetry.update(status="FAILED", error=str(error))

        telemetry["latency_ms"] = int((time.perf_counter() - started) * 1000)
        self._apply_provenance_defaults(fragments, platform)
        self._finalize_outcome(telemetry, fragments)
        self.router.doctor.record_observation(platform, telemetry, fragments)
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
            "outcome": "INITIATED",
            "content_class": "UNKNOWN",
            "network_observed": False,
            "http_statuses": [],
            "source_endpoints": [],
            "cache_statuses": [],
            "retry_after_seconds": None,
            "rate_limit_remaining": None,
            "rate_limit_reset_at": None,
            "usable_text_chars": 0,
            "evidence_item_count": 0,
        }

    @staticmethod
    def _finalize_outcome(telemetry: Dict[str, Any], fragments: List[EvidenceFragment]) -> None:
        """Classify evidence depth independently from transport success."""
        transport = list(telemetry.get("transport_observations", []))
        transport.extend(
            (getattr(f, "raw_metadata", {}) or {}).get("transport", {})
            for f in fragments
        )
        transport = [item for item in transport if item]
        observed = [item for item in transport if item.get("network_observed_this_attempt") is True]
        http_statuses = sorted(
            {int(item) for item in telemetry.get("http_statuses", []) if item is not None}
            | {int(item["http_status"]) for item in observed if item.get("http_status") is not None}
        )
        endpoints = list(dict.fromkeys([
            *telemetry.get("source_endpoints", []),
            *(item.get("endpoint") for item in observed if item.get("endpoint")),
        ]))
        cache_statuses = sorted({
            item.get("cache_status", "UNKNOWN") for item in transport
        })
        telemetry.update(
            network_observed=bool(telemetry.get("network_observed")) or bool(observed),
            http_statuses=http_statuses,
            source_endpoints=endpoints,
            cache_statuses=cache_statuses or telemetry.get("cache_statuses") or ["UNKNOWN"],
        )
        if telemetry.get("status") == "AUTH_REQUIRED":
            telemetry.update(outcome="AUTH_REQUIRED", content_class="NONE")
            return
        if telemetry.get("status") == "FAILED":
            telemetry.update(outcome="FAILED", content_class="NONE")
            return

        depths = {str(getattr(f, "content_depth", "") or "").upper() for f in fragments}
        modes = {str(getattr(f, "retrieval_mode", "") or "").lower() for f in fragments}
        usable_chars = sum(
            int((getattr(f, "raw_metadata", {}) or {}).get("usable_body_chars", len((getattr(f, "content", "") or "").strip())))
            for f in fragments
        )

        direct_depths = {
            "FULL_ARTICLE", "PARTIAL_CONTENT", "PRIMARY_DOCUMENT", "REGULATORY_FILING",
            "OFFICIAL_STATEMENT", "SOCIAL_POST", "TWEET_STATUS", "COMMENT",
            "COMMENTS", "VIDEO_TRANSCRIPT", "FULL_CONTENT",
        }
        metadata_depths = {"PROFILE_METADATA", "VIDEO_METADATA", "HEADLINE_ONLY", "METADATA"}
        if not fragments:
            outcome, content_class = "EMPTY", "NONE"
        elif "web_search_index" in modes or "INDEX_SNIPPET" in depths:
            outcome, content_class = "SEARCH_INDEX_DISCOVERY", "SEARCH_INDEX"
        elif depths & {"FEED_ENTRY_SUMMARY", "FEED_ENTRY_CONTENT"}:
            outcome, content_class = "SYNDICATED_SUMMARY", "SYNDICATED"
        elif depths & direct_depths:
            outcome, content_class = "DIRECT_CONTENT", "DIRECT"
        elif depths and depths <= metadata_depths:
            outcome, content_class = "DIRECT_METADATA", "METADATA"
        else:
            outcome, content_class = "PARTIAL_OR_UNCLASSIFIED", "PARTIAL"

        telemetry.update(
            outcome=outcome,
            content_class=content_class,
            usable_text_chars=usable_chars,
            evidence_item_count=len(fragments),
        )

    @staticmethod
    def _apply_provenance_defaults(fragments: List[EvidenceFragment], platform: str) -> None:
        for fragment in fragments:
            if not getattr(fragment, "requested_channel", None):
                fragment.requested_channel = platform
            if not getattr(fragment, "actual_retrieval_channel", None):
                fragment.actual_retrieval_channel = getattr(fragment, "channel_name", None) or platform
