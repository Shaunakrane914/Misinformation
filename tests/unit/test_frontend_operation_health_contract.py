"""Operation-level capability truth must reach every agent interface."""

from pathlib import Path

from backend.infrastructure.acquisition.service import agent_reach_service


ROOT = Path(__file__).resolve().parents[2]
AGENT_PAGES = (
    "scout-agent.html",
    "trending-agent.html",
    "brandshield-agent.html",
    "personal-watch-agent.html",
)


def test_capability_api_payload_exposes_operation_level_truth():
    payload = agent_reach_service.capabilities()
    twitter = payload["channels"]["twitter"]["operation_capabilities"]
    assert {"search", "profile", "status"} <= set(twitter)
    for operation in twitter.values():
        assert operation["runtime_health"] in {
            "UNKNOWN", "STALE", "HEALTHY", "LIMITED", "DEGRADED",
            "RATE_LIMITED", "AUTH_REQUIRED", "BLOCKED",
            "UNAVAILABLE_NOT_IMPLEMENTED",
        }
        assert operation["decision"] in {
            "ELIGIBLE_UNVERIFIED", "PREFER", "DEPRIORITIZE_CACHE",
            "DEFER_TEMPORARY", "EXCLUDE",
        }


def test_all_four_agent_pages_use_shared_operation_health_presenter():
    for page_name in AGENT_PAGES:
        page = (ROOT / "frontend" / page_name).read_text(encoding="utf-8")
        assert '<script src="operation-health.js"></script>' in page
        assert "AegisOperationHealth" in page


def test_presenter_prevents_mixed_operation_state_from_becoming_green():
    source = (ROOT / "frontend" / "operation-health.js").read_text(encoding="utf-8")
    assert "Mixed operation health must never become a generic green channel" in source
    assert "states.has('healthy') || states.has('limited')" in source
    assert "state = 'limited'" in source
    assert "Authentication required" in source
    assert "Policy blocked" in source
    assert "Not implemented" in source
    assert "Not yet verified" in source


def test_brandshield_no_longer_hardcodes_provider_success_badges():
    page = (ROOT / "frontend" / "brandshield-agent.html").read_text(encoding="utf-8")
    assert '<span class="health-pill healthy"><span>Reddit</span>' not in page
    assert '<span class="health-pill healthy"><span>Twitter</span>' not in page
