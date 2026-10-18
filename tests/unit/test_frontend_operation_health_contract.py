"""Operation-level capability truth must reach every agent interface."""

import shutil
import subprocess
import tomllib
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


def test_operation_health_js_ttl_and_stale_contracts():
    source = (ROOT / "frontend" / "operation-health.js").read_text(encoding="utf-8")
    assert "ttlMs: 45000" in source
    assert "staleThresholdMs: 90000" in source
    assert "inFlightPromise" in source
    assert "invalidateCapabilities" in source
    assert "visibilitychange" in source
    assert "Stale observation" in source
    assert "getCacheState" in source


def test_operation_health_node_suite_executes_successfully():
    node_exe = shutil.which("node")
    if not node_exe:
        return
    test_script = ROOT / "tests" / "frontend" / "test_operation_health.js"
    res = subprocess.run([node_exe, str(test_script)], capture_output=True, text=True, check=False)
    assert res.returncode == 0, f"Node test suite failed:\n{res.stdout}\n{res.stderr}"
    assert "ALL FRONTEND OPERATION HEALTH TESTS PASSED" in res.stdout


def test_real_page_health_and_security_behaviors():
    node_exe = shutil.which("node")
    if not node_exe:
        return
    test_script = ROOT / "tests" / "frontend" / "test_security_and_health_regressions.js"
    res = subprocess.run([node_exe, str(test_script)], capture_output=True, text=True, check=False, timeout=30)
    assert res.returncode == 0, f"Frontend regression suite failed:\n{res.stdout}\n{res.stderr}"
    assert "FRONTEND SECURITY AND HEALTH REGRESSIONS PASSED" in res.stdout


def test_unhashed_runtime_assets_revalidate_on_cloudflare_pages():
    cloudflare_rules = {}
    current = None
    for line in (ROOT / "frontend" / "_headers").read_text(encoding="utf-8").splitlines():
        if line.startswith("/"):
            current = line.strip()
            cloudflare_rules[current] = {}
        elif current and line.strip() and not line.lstrip().startswith("#"):
            name, value = line.strip().split(":", 1)
            cloudflare_rules[current][name] = value.strip()
    for pattern in ("/*.js", "/*.css"):
        headers = cloudflare_rules[pattern]
        cache = headers["Cache-Control"]
        assert "no-cache" in cache
        assert "max-age=0" in cache
        assert "must-revalidate" in cache
        assert "immutable" not in cache


def test_cloudflare_pages_does_not_mask_missing_routes_with_successful_homepage():
    rules = (ROOT / "frontend" / "_redirects").read_text(encoding="utf-8").splitlines()
    catchalls = [line.split() for line in rules if line.strip().startswith("/* ")]
    assert all(parts[1:] == ["/404.html", "404"] for parts in catchalls)
    # Ensure there is no SPA redirect rule masking 404 with 200 (e.g. /* /index.html 200)
    assert not any(line.strip().startswith("/* ") and "200" in line for line in rules)
