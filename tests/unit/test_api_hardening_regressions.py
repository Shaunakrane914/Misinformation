"""Behavioral regressions for reviewed API authorization and telemetry failures."""

import asyncio
import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.api import agent_reach, agents, system
from backend.api.security import settings
from backend.agents.brandshield.agent import BrandShieldAgent


@pytest.fixture
def api_client():
    app = FastAPI()
    app.include_router(agents.router)
    app.include_router(agent_reach.router)
    app.include_router(system.router)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/api/deploy-response", "/deploy-response"])
def test_response_mutation_requires_operator_before_database(api_client, monkeypatch, path):
    database = MagicMock()
    monkeypatch.setattr(agents.db, "supabase", database)
    monkeypatch.setattr(settings, "admin_api_token", "operator-test-secret")
    for authorization in (None, "Bearer wrong", "Basic operator-test-secret"):
        headers = {"Authorization": authorization} if authorization else {}
        response = api_client.post(path, json={"event_id": 1, "response_type": "official_denial"}, headers=headers)
        assert response.status_code == 401
        assert "operator-test-secret" not in response.text
        database.table.assert_not_called()


def test_unconfigured_operator_is_fail_closed(api_client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_token", "")
    response = api_client.post("/api/deploy-response", json={"event_id": 1, "response_type": "official_denial"})
    assert response.status_code == 503


def test_valid_operator_can_deploy_response(api_client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_token", "operator-test-secret")
    table = MagicMock()
    table.select.return_value.eq.return_value.execute.return_value = SimpleNamespace(data=[{"id": 1, "ticker": "NVDA", "current_price": 10}])
    table.insert.return_value.execute.return_value = SimpleNamespace(data=[{"id": 42}])
    database = MagicMock()
    database.table.return_value = table
    monkeypatch.setattr(agents.db, "supabase", database)
    monkeypatch.setattr(agents, "get_scout_agent", lambda: SimpleNamespace(check_stock_impact=lambda ticker: {"current_price": 12}))
    response = api_client.post("/api/deploy-response", json={"event_id": 1, "response_type": "official_denial"}, headers={"Authorization": "Bearer operator-test-secret"})
    assert response.status_code == 200
    assert response.json()["measure_id"] == 42
    table.insert.assert_called_once()
    table.update.assert_called_once_with({"response_deployed": True})


@pytest.mark.parametrize("label, expected", [
    ("INSUFFICIENT_EVIDENCE", "Insufficient Evidence"), ("Insufficient Evidence", "Insufficient Evidence"),
    ("UNVERIFIED", "Unverified"), (None, "Unverified"), ("unknown", "Unverified"),
    ("FALSE", "False"), ("TRUE", "True"), ("MISLEADING", "Misleading"),
])
def test_dashboard_preserves_verdict_semantics(api_client, monkeypatch, label, expected):
    table = MagicMock()
    table.select.return_value.eq.return_value.not_.is_.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[{"claim_text": "A claim", "verdict": label}]
    )
    database = MagicMock()
    database.table.return_value = table
    monkeypatch.setattr(system.db, "supabase", database)
    monkeypatch.setattr(system, "load_random_dashboard_claims", lambda n: [])
    response = api_client.get("/api/dashboard/claims?fresh=true")
    assert response.status_code == 200
    assert response.json()[0]["verdict"] == expected
    assert response.json()[0]["record_origin"] == "investigation"


@pytest.mark.parametrize("enabled, expected", [(False, []), (True, ["reddit"])])
def test_scan_honors_platform_optouts(api_client, monkeypatch, enabled, expected):
    scan = MagicMock(return_value={"items": []})
    monkeypatch.setattr(agent_reach.agent_reach_service, "unified_scan", scan)
    response = api_client.post("/api/agent-reach/scan", json={
        "query": "test", "include_reddit": enabled, "include_twitter": False,
        "include_youtube": False, "include_news": False, "limit": 3,
    })
    assert response.status_code == 200
    assert scan.call_args.kwargs["platforms"] == expected


@pytest.mark.parametrize("path, payload", [
    ("/api/agent-reach/scan", {"query": "test", "limit": 0}),
    ("/api/agent-reach/scan", {"query": "test", "limit": 100000}),
    ("/api/agent-reach/read", {"url": "https://example.org", "max_chars": 1000000}),
    ("/api/gemini", {"prompt": "x" * 20001}),
])
def test_public_api_rejects_unbounded_budgets(api_client, path, payload):
    assert api_client.post(path, json=payload).status_code == 422


def test_empty_brand_scan_has_zero_groups_and_no_live_ai(monkeypatch):
    agent = BrandShieldAgent()
    monkeypatch.setattr(agent, "search_brand_evidence", lambda info: ([], {}, {}, 0))
    result = agent.scan("Example")
    assert result["summary"]["independent_groups_count"] == 0
    assert result["scan_metadata"]["ai_enrichment"] == "NOT_REQUIRED_EMPTY_DATA"


def test_inventory_does_not_claim_unprobed_agents_are_healthy(api_client):
    status = api_client.get("/api/system/deployment-status").json()
    assert status["healthy_agent_count"] == 0
    assert status["healthy_agent_count_status"] == "NOT_PROBED"
    inventory = api_client.get("/api/system/agents").json()
    assert all(a["status"] == "REGISTERED_ON_DEMAND" for a in inventory["agents"].values())
    assert "doxxing_darkweb_leaks" not in inventory["agents"]["personal_watch"]["capabilities"]


def test_stock_endpoint_uses_bounded_safe_transport(api_client, monkeypatch):
    fetch = MagicMock(return_value=SimpleNamespace(status_code=200, body=json.dumps({
        "chart": {"result": [{"meta": {"symbol": "NVDA", "regularMarketPrice": 12, "chartPreviousClose": 10},
                                  "indicators": {"quote": [{"close": [10, 11, 12]}]}}]}
    }).encode()))
    monkeypatch.setattr(agents, "fetch_public_http", fetch)
    assert api_client.get("/api/stock?ticker=NVDA").json()["current_price"] == 12
    assert fetch.call_args.kwargs["timeout"] == 5.0
    assert fetch.call_args.kwargs["max_bytes"] == 1_000_000
    assert fetch.call_args.kwargs["max_attempts"] == 1


@pytest.mark.parametrize("endpoint, getter, method, payload", [
    (agents.brandshield_scan, "get_brandshield_agent", "scan", agents.BrandShieldScanRequest(brand_name="Example")),
    (agents.analyze_stock_live, "get_scout_agent", "analyze_stock", agents.ScoutAnalyzeRequest(ticker="NVDA")),
    (agents.trending_scan, "get_trending_agent", "scan", agents.TrendingScanRequest(query="Example")),
])
def test_agent_scan_does_not_block_event_loop(monkeypatch, endpoint, getter, method, payload):
    event_loop_thread = threading.get_ident()
    completed = []
    heartbeat = []

    def blocking_scan(*args, **kwargs):
        assert threading.get_ident() != event_loop_thread
        time.sleep(0.08)
        completed.append(True)
        return {"stock": {"current_price": 1}}

    monkeypatch.setattr(agents, getter, lambda: SimpleNamespace(**{method: blocking_scan}))

    async def run():
        async def beat():
            await asyncio.sleep(0.01)
            heartbeat.append(not completed)
        await asyncio.gather(endpoint(payload), beat())
    asyncio.run(run())
    assert heartbeat == [True]


def test_personal_scan_does_not_block_event_loop(monkeypatch):
    from backend.agents import personal_agent
    event_loop_thread = threading.get_ident()
    completed = []
    heartbeat = []

    def blocking_scan(profile):
        assert threading.get_ident() != event_loop_thread
        time.sleep(0.08)
        completed.append(True)
        return {"status": "success"}

    monkeypatch.setattr(personal_agent, "process_personal_watch", blocking_scan)
    async def run():
        async def beat():
            await asyncio.sleep(0.01)
            heartbeat.append(not completed)
        await asyncio.gather(agents.personal_watch_scan(agents.PersonalScanRequest(name="Example")), beat())
    asyncio.run(run())
    assert heartbeat == [True]


@pytest.mark.parametrize("agent_name", ["brandshield", "personal"])
def test_parallel_scans_are_bounded_and_cannot_share_session_state(monkeypatch, agent_name):
    started = threading.Event()
    release = threading.Event()
    calls = []

    def blocking_scan(*args, **kwargs):
        calls.append(True)
        started.set()
        assert release.wait(timeout=2)
        return {"status": "success"}

    if agent_name == "brandshield":
        monkeypatch.setattr(agents, "get_brandshield_agent", lambda: SimpleNamespace(scan=blocking_scan))
        endpoint = agents.brandshield_scan
        payload = agents.BrandShieldScanRequest(brand_name="Example")
    else:
        from backend.agents import personal_agent
        monkeypatch.setattr(personal_agent, "process_personal_watch", blocking_scan)
        endpoint = agents.personal_watch_scan
        payload = agents.PersonalScanRequest(name="Example")

    async def run():
        accepted = asyncio.create_task(endpoint(payload))
        try:
            assert await asyncio.to_thread(started.wait, 1)
            with pytest.raises(HTTPException) as rejected:
                await endpoint(payload)
            assert rejected.value.status_code == 429
            assert rejected.value.headers["Retry-After"] == "3"
            assert len(calls) == 1
        finally:
            release.set()
            await accepted
        # Completed scans release admission, including the agent session state.
        assert (await endpoint(payload))["status"] == "success"
    asyncio.run(run())


def test_scan_admission_releases_after_failure():
    def failing_scan():
        raise RuntimeError("Controlled scan failure")
    with pytest.raises(RuntimeError):
        agents._run_bounded_scan("brandshield", failing_scan)
    assert agents._run_bounded_scan("brandshield", lambda: "accepted") == "accepted"


def test_sync_acquisition_runs_in_asgi_worker_thread(monkeypatch):
    finished = []
    def health():
        time.sleep(0.08)
        finished.append(True)
        return {"status": "ok"}
    monkeypatch.setattr(agent_reach.agent_reach_service, "health", health)
    app = FastAPI()
    app.include_router(agent_reach.router)
    app.include_router(system.router)

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            task = asyncio.create_task(client.get("/api/agent-reach/health"))
            await asyncio.sleep(0.01)
            response = await client.get("/api/healthz")
            assert response.status_code == 200
            assert not finished
            assert (await task).status_code == 200
    asyncio.run(run())
