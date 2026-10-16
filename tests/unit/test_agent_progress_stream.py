"""Offline stream contracts, truthful progress and retained scan admission."""

import asyncio
import json
import threading
import time
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.api import agents, research_stream
from backend.application.research.progress import progress_observer, report_progress


ROUTES = [
    ("scout", "/api/scout/analyze", "analyze_stock_live", {"ticker": "Infosys"}),
    ("trending", "/api/trending/scan", "trending_scan", {"query": "Example"}),
    ("brandshield", "/api/brandshield/scan", "brandshield_scan", {"brand_name": "Example"}),
    ("personal", "/api/personal/scan", "personal_watch_scan", {"name": "Example"}),
]


def records(text):
    return [(block.splitlines()[0][7:], json.loads(block.split("data: ", 1)[1]))
            for block in text.strip().split("\n\n")]


@pytest.mark.parametrize("agent,path,handler,payload", ROUTES)
def test_all_four_routes_stream_observed_stages_without_changing_results(api_client, monkeypatch, agent, path, handler, payload):
    result = {"status": "INSUFFICIENT_EVIDENCE", "sources": [], "unified_report": None}

    async def fake_endpoint(request):
        assert request.model_dump(exclude_none=True).items() >= payload.items()

        def scan():
            report_progress(pipeline_pass="test-pass", pipeline_completed=3, pipeline_total=13, pipeline_step="Qualification")
            return dict(result)
        return await asyncio.to_thread(agents._run_bounded_scan, agent, scan)

    monkeypatch.setattr(agents, handler, fake_endpoint)
    response = api_client.post(path + "/stream", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    schema = api_client.get("/openapi.json").json()
    assert "text/event-stream" in schema["paths"][path + "/stream"]["post"]["responses"]["200"]["content"]
    assert response.headers.get("content-encoding") != "gzip"
    assert "no-store" in response.headers["cache-control"]
    events = records(response.text)
    assert events[-1][0] == "result"
    assert events[-1][1]["result"] == result
    assert events[-1][1]["completed"] == 3
    assert len({data["analysis_id"] for _, data in events}) == 1
    assert [data["phase"] for _, data in events if "phase" in data] == ["accepted", "analysis", "report"]
    assert any(data.get("pipeline_completed") == 3 for _, data in events)


@pytest.mark.parametrize("agent,path,handler,payload", ROUTES)
def test_busy_and_invalid_requests_never_start_another_scan(api_client, monkeypatch, agent, path, handler, payload):
    called = []

    async def unexpected(request):
        called.append(True)
        return {}

    monkeypatch.setattr(agents, handler, unexpected)
    lock = agents._scan_locks[agent]
    lock.acquire()
    try:
        response = api_client.post(path + "/stream", json=payload)
        assert response.status_code == 429
        assert response.headers["retry-after"] == "3"
        assert called == []
    finally:
        lock.release()
    assert api_client.post(path + "/stream", json={"ticker": "x" * 100, "name": "x" * 300, "brand_name": "x" * 300, "query": []}).status_code == 422


def test_failed_stream_never_claims_complete_or_leaks_exception(api_client, monkeypatch):
    async def fail(request):
        raise RuntimeError("SUPER_SECRET_PROVIDER_COOKIE")
    monkeypatch.setattr(agents, "analyze_stock_live", fail)
    response = api_client.post("/api/scout/analyze/stream", json={"ticker": "Example"})
    assert "SUPER_SECRET" not in response.text
    assert records(response.text)[-1][0] == "error"
    assert all(event != "result" for event, _ in records(response.text))


@pytest.mark.parametrize("disconnect", [True, False])
def test_disconnect_or_deadline_does_not_unlock_running_worker(monkeypatch, disconnect):
    started, release = threading.Event(), threading.Event()
    lock = agents._scan_locks["scout"]
    monkeypatch.setattr(research_stream, "HEARTBEAT_SECONDS", 0.005)
    monkeypatch.setattr(research_stream, "STREAM_TIMEOUT_SECONDS", 1 if disconnect else 0.02)

    async def callback():
        def scan():
            started.set()
            assert release.wait(timeout=3)
            return {"sources": []}
        return await asyncio.to_thread(agents._run_bounded_scan, "scout", scan)

    async def exercise():
        stream = research_stream.analysis_stream("scout", callback, lock)
        try:
            messages = []
            async for message in stream.body_iterator:
                messages.append(message)
                if disconnect and "event: heartbeat" in message:
                    break
            await stream.body_iterator.aclose()
            assert started.is_set() and lock.locked()
            if not disconnect:
                assert '"status": 504' in messages[-1]
            with pytest.raises(HTTPException) as error:
                research_stream.analysis_stream("scout", callback, lock)
            assert error.value.status_code == 429
        finally:
            release.set()
            await asyncio.gather(*tuple(research_stream._running))
        assert not lock.locked()
        assert progress_observer.get() is None
    asyncio.run(exercise())


def test_pipeline_observations_preserve_reviewed_research_serialization():
    from tests.unit.test_research_pipeline_golden import capture_scenario
    baseline = capture_scenario("relevant")
    observed = []
    token = progress_observer.set(observed.append)
    try:
        assert capture_scenario("relevant") == baseline
    finally:
        progress_observer.reset(token)
    assert [item["pipeline_completed"] for item in observed] == [value for n in range(13) for value in (n, n + 1)]
    assert len({item["pipeline_pass"] for item in observed}) == 1
    with patch("backend.application.research.progress.progress_observer") as observer:
        observer.get.return_value.side_effect = RuntimeError("observer unavailable")
        report_progress(phase="analysis")


def test_concurrent_agents_keep_progress_request_local():
    async def exercise():
        async def collect(agent):
            async def callback():
                def scan():
                    report_progress(pipeline_pass=agent, pipeline_completed=0, pipeline_total=13, pipeline_step="Planning")
                    time.sleep(0.01)
                    return {"agent": agent}
                return await asyncio.to_thread(agents._run_bounded_scan, agent, scan)
            response = research_stream.analysis_stream(agent, callback, agents._scan_locks[agent])
            messages = [message async for message in response.body_iterator]
            events = records("".join(messages))
            assert {data.get("pipeline_pass") for _, data in events if "pipeline_pass" in data} == {agent}
            return events[-1][1]["analysis_id"]
        ids = await asyncio.gather(collect("scout"), collect("brandshield"))
        assert len(set(ids)) == 2
        assert progress_observer.get() is None
    asyncio.run(exercise())


def test_immediate_result_cannot_overtake_scheduled_progress():
    async def exercise():
        async def immediate():
            report_progress(phase="analysis", completed=1, total=3)
            report_progress(phase="report", completed=2, total=3)
            return {"sources": []}
        response = research_stream.analysis_stream("scout", immediate, threading.Lock())
        events = records("".join([message async for message in response.body_iterator]))
        assert [event for event, _ in events] == ["progress", "progress", "progress", "result"]
        assert [data["phase"] for _, data in events[:-1]] == ["accepted", "analysis", "report"]
    asyncio.run(exercise())


def test_failed_pipeline_step_is_not_counted_as_completed(monkeypatch):
    from backend.application.research import pipeline
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.research.research_models import ResearchRequest
    observed = []

    def fail(*args):
        raise RuntimeError("synthetic failure")
    monkeypatch.setattr(pipeline.QueryPlanningStage, "run", fail)
    token = progress_observer.set(observed.append)
    try:
        with pytest.raises(RuntimeError):
            pipeline.ResearchPipeline(ResearchBudget()).run(ResearchRequest(target="Example", domain="financial"))
    finally:
        progress_observer.reset(token)
    assert [event["pipeline_completed"] for event in observed] == [0, 0]
    assert observed[-1]["pipeline_failed"] is True
