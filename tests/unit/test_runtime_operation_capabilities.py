"""Runtime capability freshness, recovery, access, and depth contracts."""

from backend.services.agent_reach.native.operation_capabilities import (
    RuntimeOperationCapabilities,
)
from backend.services.agent_reach.source_planner import SourcePlanningEngine


def _telemetry(outcome, *, status=200, error=None, network=True, cache="MISS"):
    return {
        "outcome": outcome,
        "content_class": "DIRECT" if outcome == "DIRECT_CONTENT" else "METADATA",
        "network_observed": network,
        "http_statuses": [] if status is None else [status],
        "cache_statuses": [cache],
        "error": error,
    }


def test_never_tested_operation_is_eligible_but_not_claimed_healthy():
    runtime = RuntimeOperationCapabilities()
    state = runtime.assess("web", "read", required_depth="DIRECT_CONTENT")
    assert state["decision"] == "ELIGIBLE_UNVERIFIED"
    assert state["runtime_health"] == "UNKNOWN"
    assert state["last_outcome"] is None


def test_rate_limit_is_temporary_and_expires_into_recovery_probe():
    now = [10.0]
    runtime = RuntimeOperationCapabilities(
        clock=lambda: now[0], rate_limit_ttl_seconds=30.0
    )
    runtime.record_observation(
        "web", "read", _telemetry("FAILED", status=429, error="rate limited")
    )
    limited = runtime.assess("web", "read", required_depth="DIRECT_CONTENT")
    assert limited["decision"] == "DEFER_TEMPORARY"
    assert limited["runtime_health"] == "RATE_LIMITED"
    now[0] = 41.0
    recovered_probe = runtime.assess("web", "read", required_depth="DIRECT_CONTENT")
    assert recovered_probe["decision"] == "ELIGIBLE_UNVERIFIED"
    assert recovered_probe["runtime_health"] == "STALE"


def test_new_success_immediately_recovers_from_temporary_failure():
    runtime = RuntimeOperationCapabilities()
    runtime.record_observation("web", "read", _telemetry("FAILED", status=503))
    assert runtime.assess("web", "read")["decision"] == "DEFER_TEMPORARY"
    runtime.record_observation("web", "read", _telemetry("DIRECT_CONTENT"))
    state = runtime.assess("web", "read", required_depth="DIRECT_CONTENT")
    assert state["decision"] == "PREFER"
    assert state["runtime_health"] == "HEALTHY"


def test_metadata_operation_is_rejected_when_full_content_is_required():
    runtime = RuntimeOperationCapabilities()
    state = runtime.assess("youtube", "search", required_depth="DIRECT_CONTENT")
    assert state["decision"] == "EXCLUDE"
    assert state["reason"].startswith("INSUFFICIENT_EVIDENCE_DEPTH")


def test_credentials_are_evaluated_on_every_decision(monkeypatch):
    runtime = RuntimeOperationCapabilities()
    monkeypatch.delenv("INSTAGRAM_COOKIE", raising=False)
    assert runtime.assess("instagram", "search")["runtime_health"] == "AUTH_REQUIRED"
    monkeypatch.setenv("INSTAGRAM_COOKIE", "fixture-session")
    restored = runtime.assess("instagram", "search")
    assert restored["decision"] == "ELIGIBLE_UNVERIFIED"
    monkeypatch.delenv("INSTAGRAM_COOKIE", raising=False)
    assert runtime.assess("instagram", "search")["runtime_health"] == "AUTH_REQUIRED"


def test_cache_hit_does_not_replace_a_network_health_observation():
    runtime = RuntimeOperationCapabilities()
    runtime.record_observation("web", "read", _telemetry("DIRECT_CONTENT"))
    runtime.record_observation(
        "web", "read",
        _telemetry("DIRECT_CONTENT", status=None, network=False, cache="CACHE_HIT"),
    )
    state = runtime.assess("web", "read")
    assert state["decision"] == "PREFER"
    assert state["network_observed"] is True
    assert state["cache_only"] is False


def test_reddit_is_policy_blocked_until_approved(monkeypatch):
    runtime = RuntimeOperationCapabilities()
    monkeypatch.delenv("REDDIT_APPROVED_ACCESS", raising=False)
    assert runtime.assess("reddit", "search")["runtime_health"] == "BLOCKED"
    monkeypatch.setenv("REDDIT_APPROVED_ACCESS", "true")
    assert runtime.assess("reddit", "search")["decision"] == "ELIGIBLE_UNVERIFIED"


def test_planner_exposes_runtime_exclusion_and_uses_working_alternatives():
    runtime = RuntimeOperationCapabilities()
    runtime.record_observation("web", "search", _telemetry("FAILED", status=429, error="rate limit"))
    plan = SourcePlanningEngine(runtime_capabilities=runtime).plan(
        "Nvidia is discontinuing the RTX 5090", entity="Nvidia"
    )
    assert not any(action.channel == "web" for action in plan.actions)
    assert any(action.channel == "news" for action in plan.actions)
    web_decision = next(
        item for item in plan.runtime_decisions
        if item["channel"] == "web" and item["operation"] == "search"
    )
    assert web_decision["decision"] == "DEFER_TEMPORARY"
