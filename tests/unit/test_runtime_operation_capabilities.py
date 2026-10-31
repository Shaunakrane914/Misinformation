"""Runtime capability freshness, recovery, access, and depth contracts."""

from backend.services.agent_reach.native.operation_capabilities import (
    RuntimeOperationCapabilities,
    required_auth_environment,
)
from backend.services.agent_reach.source_planner import SourcePlanningEngine


def _telemetry(
    outcome, *, status=200, error=None, network=True, cache="MISS", retry_after=None
):
    return {
        "outcome": outcome,
        "content_class": "DIRECT" if outcome == "DIRECT_CONTENT" else "METADATA",
        "network_observed": network,
        "http_statuses": [] if status is None else [status],
        "cache_statuses": [cache],
        "error": error,
        "retry_after_seconds": retry_after,
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


def test_provider_retry_after_overrides_default_cooldown_with_a_bound():
    now = [10.0]
    runtime = RuntimeOperationCapabilities(
        clock=lambda: now[0], rate_limit_ttl_seconds=30.0,
        max_rate_limit_ttl_seconds=300.0,
    )
    runtime.record_observation(
        "web", "read",
        _telemetry("FAILED", status=429, error="rate limited", retry_after=120),
    )
    state = runtime.assess("web", "read")
    assert state["retry_after_seconds"] == 120.0
    now[0] = 119.0
    assert runtime.assess("web", "read")["decision"] == "DEFER_TEMPORARY"
    now[0] = 131.0
    assert runtime.assess("web", "read")["runtime_health"] == "STALE"

    runtime.record_observation(
        "web", "read",
        _telemetry("FAILED", status=429, error="rate limited", retry_after=9999),
    )
    assert runtime.assess("web", "read")["retry_after_seconds"] == 300.0


def test_new_success_immediately_recovers_from_temporary_failure():
    runtime = RuntimeOperationCapabilities()
    runtime.record_observation("web", "read", _telemetry("FAILED", status=503))
    assert runtime.assess("web", "read")["decision"] == "DEFER_TEMPORARY"
    runtime.record_observation("web", "read", _telemetry("DIRECT_CONTENT"))
    state = runtime.assess("web", "read", required_depth="DIRECT_CONTENT")
    assert state["decision"] == "PREFER"
    assert state["runtime_health"] == "HEALTHY"


def test_empty_query_observation_does_not_defer_future_searches():
    runtime = RuntimeOperationCapabilities()
    runtime.record_observation("web", "search", _telemetry("EMPTY"))
    state = runtime.assess("web", "search")
    assert state["decision"] == "ELIGIBLE_UNVERIFIED"
    assert state["runtime_health"] == "DEGRADED"
    assert state["temporary"] is False


def test_metadata_operation_is_rejected_when_full_content_is_required():
    runtime = RuntimeOperationCapabilities()
    state = runtime.assess("youtube", "search", required_depth="DIRECT_CONTENT")
    assert state["decision"] == "EXCLUDE"
    assert state["reason"].startswith("INSUFFICIENT_EVIDENCE_DEPTH")


def test_credentials_are_evaluated_on_every_decision(monkeypatch):
    runtime = RuntimeOperationCapabilities()
    monkeypatch.delenv("INSTAGRAM_COOKIE", raising=False)
    assert runtime.assess("instagram", "search")["runtime_health"] == "AUTH_REQUIRED"


def test_auth_contract_has_one_operation_aware_authority(monkeypatch):
    assert required_auth_environment("instagram", "search") == "INSTAGRAM_COOKIE"
    assert required_auth_environment("instagram", "oembed") is None
    assert required_auth_environment("linkedin", "jobs") is None
    assert required_auth_environment("xiaoyuzhou", "podcast") is None
    assert required_auth_environment("xiaoyuzhou", "transcribe") == "GROQ_API_KEY"

    runtime = RuntimeOperationCapabilities()
    monkeypatch.delenv("LINKEDIN_COOKIE", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert runtime.assess("linkedin", "jobs")["decision"] == "ELIGIBLE_UNVERIFIED"
    assert runtime.assess("xiaoyuzhou", "podcast")["decision"] == "ELIGIBLE_UNVERIFIED"
    assert runtime.assess("xiaoyuzhou", "transcribe")["auth_environment"] == "GROQ_API_KEY"
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
