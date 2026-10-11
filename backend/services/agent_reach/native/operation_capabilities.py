"""Runtime operation capability truth derived from declarations and observations.

This module does not probe providers.  It combines the static contract with the
production dispatch surface and the observations already produced at the
acquisition boundary.  Observations expire so a transient failure cannot disable
an operation forever; credentials and policy are evaluated on every decision.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional, Set, Tuple

from backend.services.agent_reach.native.channel_capabilities import CAPABILITY_MATRIX


# The canonical production dispatch contract.  Keep this narrower than the
# upstream declaration catalogue and protect it with dispatcher contract tests.
EXECUTABLE_CAPABILITIES: Dict[str, Set[str]] = {
    "news": {"search"},
    "web": {"search", "read"},
    "web_search": {"search"},
    "jina_reader": {"read"},
    "rss": {"search", "read"},
    "github": {"search", "read", "issues", "prs", "releases", "commits"},
    "youtube": {"search", "read", "transcript", "comments"},
    "v2ex": {"hot", "latest", "search", "topic", "replies"},
    "bilibili": {"search"},
    "reddit": {"search", "read", "comments"},
    "twitter": {"search", "profile", "status", "read"},
    "linkedin": {"jobs"},
    "xueqiu": {"search"},
    "xiaohongshu": {"search"},
    "instagram": {"search", "oembed"},
    "facebook": {"search", "oembed"},
    "boss": {"search_jobs"},
    "xiaoyuzhou": {"podcast", "episodes"},
}


OPERATION_DEPTHS: Dict[Tuple[str, str], Set[str]] = {
    ("news", "search"): {"SYNDICATED_SUMMARY"},
    ("rss", "search"): {"SYNDICATED_SUMMARY"},
    ("rss", "read"): {"SYNDICATED_SUMMARY"},
    ("web", "search"): {"SEARCH_INDEX_DISCOVERY"},
    ("web_search", "search"): {"SEARCH_INDEX_DISCOVERY"},
    ("web", "read"): {"DIRECT_CONTENT"},
    ("jina_reader", "read"): {"DIRECT_CONTENT"},
    ("github", "search"): {"DIRECT_METADATA"},
    ("github", "read"): {"DIRECT_CONTENT", "DIRECT_METADATA"},
    ("github", "issues"): {"DIRECT_CONTENT"},
    ("github", "prs"): {"DIRECT_CONTENT"},
    ("github", "releases"): {"DIRECT_CONTENT", "DIRECT_METADATA"},
    ("github", "commits"): {"DIRECT_CONTENT", "DIRECT_METADATA"},
    ("youtube", "search"): {"DIRECT_METADATA"},
    ("youtube", "read"): {"DIRECT_METADATA"},
    ("youtube", "transcript"): {"DIRECT_CONTENT"},
    ("youtube", "comments"): {"DIRECT_CONTENT"},
    ("v2ex", "hot"): {"DIRECT_CONTENT"},
    ("v2ex", "latest"): {"DIRECT_CONTENT"},
    ("v2ex", "search"): {"DIRECT_CONTENT"},
    ("v2ex", "topic"): {"DIRECT_CONTENT"},
    ("v2ex", "replies"): {"DIRECT_CONTENT"},
    ("bilibili", "search"): {"DIRECT_METADATA"},
    ("reddit", "search"): {"DIRECT_CONTENT", "SYNDICATED_SUMMARY", "SEARCH_INDEX_DISCOVERY"},
    ("reddit", "read"): {"DIRECT_CONTENT"},
    ("reddit", "comments"): {"DIRECT_CONTENT"},
    ("twitter", "search"): {"SEARCH_INDEX_DISCOVERY"},
    ("twitter", "profile"): {"DIRECT_METADATA"},
    ("twitter", "status"): {"DIRECT_CONTENT"},
    ("twitter", "read"): {"DIRECT_CONTENT", "DIRECT_METADATA"},
    ("linkedin", "jobs"): {"DIRECT_METADATA"},
    ("xiaoyuzhou", "podcast"): {"DIRECT_METADATA", "SYNDICATED_SUMMARY"},
    ("xiaoyuzhou", "episodes"): {"DIRECT_METADATA", "SYNDICATED_SUMMARY"},
}


AUTH_ENVIRONMENT: Dict[Tuple[str, str], str] = {
    ("xueqiu", "search"): "XUEQIU_COOKIE",
    ("xiaohongshu", "search"): "XIAOHONGSHU_COOKIE",
    ("instagram", "search"): "INSTAGRAM_COOKIE",
    ("facebook", "search"): "FACEBOOK_COOKIE",
    ("boss", "search_jobs"): "BOSS_CDP_PORT",
}


@dataclass
class OperationObservation:
    outcome: str
    content_class: str
    observed_at_monotonic: float
    observed_at: str
    network_observed: bool
    cache_only: bool
    http_statuses: list[int] = field(default_factory=list)
    error: Optional[str] = None
    retry_after_seconds: Optional[float] = None


class RuntimeOperationCapabilities:
    """Central operation-level capability evaluator used by planner and API."""

    SUCCESS_OUTCOMES = {
        "DIRECT_CONTENT", "DIRECT_METADATA", "SYNDICATED_SUMMARY",
        "SEARCH_INDEX_DISCOVERY", "PARTIAL_OR_UNCLASSIFIED",
    }

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        healthy_ttl_seconds: float = 900.0,
        failure_ttl_seconds: float = 90.0,
        rate_limit_ttl_seconds: float = 180.0,
    ) -> None:
        self._clock = clock
        self.healthy_ttl_seconds = healthy_ttl_seconds
        self.failure_ttl_seconds = failure_ttl_seconds
        self.rate_limit_ttl_seconds = rate_limit_ttl_seconds
        self._observations: Dict[Tuple[str, str], OperationObservation] = {}

    @staticmethod
    def normalize(channel: str, operation: str) -> Tuple[str, str]:
        canonical = "twitter" if (channel or "").lower() == "x" else (channel or "").lower()
        op = (operation or "search").lower()
        if "." in op:
            prefix, op_name = op.split(".", 1)
            if prefix in {canonical, "x" if canonical == "twitter" else canonical}:
                op = op_name
        return canonical, op

    def record_observation(
        self,
        channel: str,
        operation: str,
        telemetry: Dict[str, Any],
    ) -> None:
        channel, operation = self.normalize(channel, operation)
        statuses = [int(value) for value in telemetry.get("http_statuses", []) if value is not None]
        error = str(telemetry.get("error") or "") or None
        rate_limited = 429 in statuses or "rate limit" in (error or "").lower()
        cache_states = {str(value).upper() for value in telemetry.get("cache_statuses", [])}
        network_observed = bool(telemetry.get("network_observed", False))
        cache_only = bool(cache_states & {"HIT", "CACHE_HIT"}) and not network_observed
        retry_after = self.rate_limit_ttl_seconds if rate_limited else None
        outcome = "RATE_LIMITED" if rate_limited else str(telemetry.get("outcome", "UNKNOWN"))

        # A cache hit proves reusable evidence, but must not overwrite a newer
        # network-health observation for the same operation.
        existing = self._observations.get((channel, operation))
        if cache_only and existing and existing.network_observed:
            return
        now = self._clock()
        self._observations[(channel, operation)] = OperationObservation(
            outcome=outcome,
            content_class=str(telemetry.get("content_class", "UNKNOWN")),
            observed_at_monotonic=now,
            observed_at=datetime.now(timezone.utc).isoformat(),
            network_observed=network_observed,
            cache_only=cache_only,
            http_statuses=statuses,
            error=error,
            retry_after_seconds=retry_after,
        )

    def assess(
        self,
        channel: str,
        operation: str,
        *,
        required_depth: Optional[str] = None,
    ) -> Dict[str, Any]:
        channel, operation = self.normalize(channel, operation)
        key = (channel, operation)
        declared = operation in CAPABILITY_MATRIX.get(channel, _EMPTY_CAPABILITY).operations
        implemented = operation in EXECUTABLE_CAPABILITIES.get(channel, set())
        env_name = AUTH_ENVIRONMENT.get(key)
        credential_present = bool(os.getenv(env_name)) if env_name else True
        policy_blocked = (
            channel == "reddit"
            and operation in {"search", "read", "comments"}
            and os.getenv("REDDIT_APPROVED_ACCESS", "false").lower() not in {"1", "true", "yes"}
        )
        supported_depths = sorted(OPERATION_DEPTHS.get(key, {"PARTIAL_OR_UNCLASSIFIED"}))
        observation = self._observations.get(key)
        age: Optional[float] = None
        fresh = False
        temporary = False
        runtime_health = "UNKNOWN"
        decision = "ELIGIBLE_UNVERIFIED"
        reason = "No fresh runtime observation; bounded probing is allowed"

        if not implemented:
            decision, reason = "EXCLUDE", "NO_PRODUCTION_HANDLER"
            runtime_health = "UNAVAILABLE_NOT_IMPLEMENTED"
        elif policy_blocked:
            decision, reason = "EXCLUDE", "POLICY_BLOCKED: approved Reddit access is not configured"
            runtime_health = "BLOCKED"
        elif env_name and not credential_present:
            decision, reason = "EXCLUDE", f"AUTH_REQUIRED: {env_name} is not configured"
            runtime_health = "AUTH_REQUIRED"
        elif required_depth and not self._depth_satisfies(required_depth, supported_depths):
            decision = "EXCLUDE"
            reason = f"INSUFFICIENT_EVIDENCE_DEPTH: requires {required_depth}"
            runtime_health = "LIMITED"
        elif observation:
            age = max(0.0, self._clock() - observation.observed_at_monotonic)
            ttl = (
                self.rate_limit_ttl_seconds if observation.outcome == "RATE_LIMITED"
                else self.healthy_ttl_seconds if observation.outcome in self.SUCCESS_OUTCOMES
                else self.failure_ttl_seconds
            )
            fresh = age <= ttl
            if fresh and observation.outcome == "RATE_LIMITED":
                decision, reason = "DEFER_TEMPORARY", "RATE_LIMITED"
                runtime_health, temporary = "RATE_LIMITED", True
            elif fresh and observation.outcome in {"FAILED", "EMPTY", "UNAVAILABLE"}:
                decision, reason = "DEFER_TEMPORARY", f"RECENT_{observation.outcome}"
                runtime_health, temporary = "DEGRADED", True
            elif fresh and observation.outcome in self.SUCCESS_OUTCOMES:
                decision = "DEPRIORITIZE_CACHE" if observation.cache_only else "PREFER"
                reason = "CACHE_ONLY_OBSERVATION" if observation.cache_only else "RECENT_VERIFIED_OUTCOME"
                runtime_health = "LIMITED" if observation.outcome != "DIRECT_CONTENT" else "HEALTHY"
            else:
                reason = "Runtime observation expired; bounded recovery probe is allowed"
                runtime_health = "STALE"

        return {
            "channel": channel,
            "operation": operation,
            "declared": declared,
            "handler_available": implemented,
            "auth_environment": env_name,
            "credential_present": credential_present,
            "policy_eligible": not policy_blocked,
            "supported_depths": supported_depths,
            "required_depth": required_depth,
            "decision": decision,
            "reason": reason,
            "runtime_health": runtime_health,
            "temporary": temporary,
            "last_outcome": observation.outcome if observation else None,
            "last_observed_at": observation.observed_at if observation else None,
            "observation_age_seconds": round(age, 3) if age is not None else None,
            "observation_fresh": fresh,
            "network_observed": observation.network_observed if observation else False,
            "cache_only": observation.cache_only if observation else False,
            "retry_after_seconds": observation.retry_after_seconds if observation and fresh else None,
        }

    def inventory(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        channels = set(CAPABILITY_MATRIX) | set(EXECUTABLE_CAPABILITIES)
        result: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for channel in sorted(channels):
            declared = set(CAPABILITY_MATRIX.get(channel, _EMPTY_CAPABILITY).operations)
            operations = declared | EXECUTABLE_CAPABILITIES.get(channel, set())
            result[channel] = {
                operation: self.assess(channel, operation)
                for operation in sorted(operations)
            }
        return result

    def reset_observations(self) -> None:
        """Clear ephemeral runtime evidence (primarily for isolated test processes)."""
        self._observations.clear()

    @staticmethod
    def _depth_satisfies(required: str, supported: Iterable[str]) -> bool:
        required_upper = (required or "").upper()
        supported_upper = {value.upper() for value in supported}
        if required_upper in supported_upper or required_upper in {"CAPABILITY_DEPENDENT", "DIRECT_CONTENT_OR_METADATA"}:
            return True
        if required_upper in {"SYNDICATED_OR_INDEXED", "PROFILE_STATUS_OR_INDEX"}:
            return bool(supported_upper & {"SYNDICATED_SUMMARY", "SEARCH_INDEX_DISCOVERY", "DIRECT_METADATA", "DIRECT_CONTENT"})
        if required_upper in {"VIDEO_METADATA", "PROFILE_METADATA"}:
            return "DIRECT_METADATA" in supported_upper or "DIRECT_CONTENT" in supported_upper
        return False


@dataclass(frozen=True)
class _EmptyCapability:
    operations: Set[str] = field(default_factory=set)


_EMPTY_CAPABILITY = _EmptyCapability()
runtime_operation_capabilities = RuntimeOperationCapabilities()


__all__ = [
    "AUTH_ENVIRONMENT",
    "EXECUTABLE_CAPABILITIES",
    "OPERATION_DEPTHS",
    "OperationObservation",
    "RuntimeOperationCapabilities",
    "runtime_operation_capabilities",
]
