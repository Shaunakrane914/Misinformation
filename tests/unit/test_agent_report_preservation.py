"""Native agent-shaped payloads must survive real routes and the shared renderer.

Only acquisition is stubbed. These are synthetic contract fixtures, not live
evidence or research-accuracy labels. No tracked evaluation output is written.
"""
import copy
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.api import agents
from backend.services.report_builder import ReportBuilder


BUILDERS = [
    ("scout", "from_scout_result", "scout_data", "/api/scout/analyze", {"ticker": "Example"}),
    ("trending", "from_trending_result", "trend_data", "/api/trending/scan", {"query": "Example"}),
    ("brandshield", "from_brandshield_result", "brand_data", "/api/brandshield/scan", {"brand_name": "Example"}),
    ("personal", "from_personal_result", "personal_data", "/api/personal/scan", {"name": "Example"}),
]


@pytest.fixture
def native_payload():
    source = {"evidence_id": "ev_read", "title": "Captured source",
              "url": "https://example.org/read", "content": "Exact acquired passage.",
              "channel": "web", "content_depth": "PARTIAL_CONTENT"}
    candidate = {"id": "ev_discovery", "title": "Discovered source",
                 "canonical_url": "https://example.org/discovered", "snippet": "Exact index snippet.",
                 "channel": "web", "content_depth": "SNIPPET", "read_status": "FAILED"}
    return {"findings": [{"finding_id": "f_1", "title": "Reported observation",
                          "statement": "A captured observation requires contextual review.",
                          "epistemic_state": "SUPPORTED", "supporting_evidence_ids": ["ev_discovery"]}],
            "sources": [source], "evidence": [source], "news": {}, "social": {},
            "research_corpus": {"ranked_candidates": [candidate]},
            "deep_research_trace": {"queries_planned": 2, "query_records": [
                {"query_id": "q1", "channel": "web", "status": "SUCCESS"},
                {"query_id": "q2", "channel": "reddit", "status": "SKIPPED"}]},
            "timeline": [{"time": "2026-10-15", "title": "Observed dated event"}],
            "stock": {"current_price": None}}


@pytest.mark.parametrize("agent,method,key,path,request_payload", BUILDERS)
def test_canonical_observations_survive_adapter(native_payload, agent, method, key, path, request_payload):
    original = copy.deepcopy(native_payload)
    report = getattr(ReportBuilder, method)(query="Example", **{key: native_payload}).to_dict()
    assert report["findings"] == [native_payload["findings"][0]["statement"]]
    assert report["finding_details"][0]["supporting_evidence_ids"] == ["ev_discovery"]
    assert report["trust"]["query_telemetry"]["queries_submitted"] == 1
    assert report["trust"]["query_telemetry"]["queries_skipped"] == 1
    assert report["trust"]["query_telemetry"]["queries_succeeded"] == 1
    assert report["timeline"][0] == {"timestamp": "2026-10-15", "description": "Observed dated event"}
    assert report["discovery"][0]["evidence_id"] == "ev_discovery"
    assert report["discovery"][0]["extraction"]["evidentiary_use"] == "DISCOVERY_ONLY"
    evidence = [item for items in report["evidence"].values() for item in items]
    assert len(evidence) == 1 and evidence[0]["evidence_id"] == "ev_read"
    assert native_payload == original


@pytest.mark.parametrize("agent,method,key,path,request_payload", BUILDERS)
@pytest.mark.parametrize("stream", [False, True])
def test_actual_agent_route_reaches_renderer(api_client, monkeypatch, native_payload,
                                            agent, method, key, path, request_payload, stream):
    def result(*args, **kwargs):
        return copy.deepcopy(native_payload)

    monkeypatch.setattr(agents, "get_scout_agent", lambda: SimpleNamespace(analyze_stock=result))
    monkeypatch.setattr(agents, "get_trending_agent", lambda: SimpleNamespace(scan=result))
    monkeypatch.setattr(agents, "get_brandshield_agent", lambda: SimpleNamespace(scan=result))
    monkeypatch.setattr(agents, "get_stock_quote", lambda *args: None)
    monkeypatch.setattr("backend.agents.personal_agent.process_personal_watch", result)
    monkeypatch.setattr("backend.services.alerts.check_critical_threats", lambda *args: [])
    response = api_client.post(path + ("/stream" if stream else ""), json=request_payload)
    assert response.status_code == 200
    if stream:
        events = [json.loads(block.split("data: ", 1)[1]) for block in response.text.strip().split("\n\n")]
        report = events[-1]["result"]["unified_report"]
    else:
        report = response.json()["unified_report"]
    assert report is not None
    assert report["findings"] == [native_payload["findings"][0]["statement"]]
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable: actual shared renderer check not performed")
    root = Path(__file__).resolve().parents[2]
    script = """
      const fs=require('fs');
      const {renderUnifiedReport}=require('./frontend/unified-report-renderer.js');
      const target={innerHTML:'',querySelectorAll:()=>[]};
      renderUnifiedReport(target,JSON.parse(fs.readFileSync(0,'utf8')));
      process.stdout.write(target.innerHTML);
    """
    rendered = subprocess.run([node, "-e", script], input=json.dumps(report), text=True,
                              encoding="utf-8", capture_output=True, cwd=root, check=True).stdout
    assert native_payload["findings"][0]["statement"] in rendered
    assert "Exact index snippet." in rendered
    assert "Exact acquired passage." in rendered
    assert "Observed dated event" in rendered
    assert "ev_discovery" in rendered
    assert "Discovery only" in rendered
    assert "No significant findings." not in rendered
    assert "No query execution log is available" not in rendered


def test_scout_positive_catalyst_and_explicit_empty_log_are_preserved():
    report = ReportBuilder.from_scout_result(query="Example", scout_data={
        "catalysts": {"positive": [{"catalyst": "Observed growth"}]},
        "deep_research_trace": {"query_records": [{"channel": "web", "status": "SUCCESS"}]}},
        execution_log=[]).to_dict()
    assert report["findings"] == ["positive: Observed growth"]
    assert report["trust"]["query_telemetry"]["execution_log"] == []


def test_scout_missing_quote_remains_unknown(monkeypatch):
    from backend.agents.scout.agent import ScoutAgent
    agent = ScoutAgent.__new__(ScoutAgent)
    monkeypatch.setattr(agent, "resolve_ticker_and_company", lambda *args: ("EXAMPLE.NS", "Example"))
    monkeypatch.setattr(agent, "check_stock_impact", lambda *args: None)
    monkeypatch.setattr("backend.services.research.research_engine.investigate", lambda *args: SimpleNamespace(
        evidence=[], findings=[], telemetry={}, research_corpus={}))
    result = agent.analyze_stock("Example")
    assert result["stock"]["current_price"] is None
    assert result["stock"]["z_score"] is None
    assert result["stock"]["is_crashing"] is None
    assert result["short_attack_correlation"]["is_anomalous"] is None
    assert result["misinformation"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_structured_findings_citations_and_canonical_body_are_not_silently_lost(native_payload):
    native_payload["findings_structured"] = [{"statement": "Structured observation", "supporting_evidence_ids": ["missing"]}]
    native_payload["findings"] *= 8  # preserve native records even if text projection is deduplicated
    native_payload["news"] = [{"url": "https://example.org/read", "summary": "Lossy legacy summary"}]
    report = ReportBuilder.from_brandshield_result(query="Example", brand_data=native_payload).to_dict()
    assert len(report["finding_details"]) == 9
    assert report["findings"][0] == "Structured observation"
    assert report["finding_details"][0]["citation_observations"] == [{"evidence_id": "missing", "availability": "UNAVAILABLE"}]
    assert report["finding_details"][1]["citation_observations"] == [{"evidence_id": "ev_discovery", "availability": "DISCOVERY_ONLY"}]
    assert sum(len(items) for items in report["evidence"].values()) == 1
    assert report["evidence"]["independent"][0]["extraction"]["passages"][0]["text"] == "Exact acquired passage."


def test_candidate_is_never_promoted_and_caller_log_takes_precedence(native_payload):
    native_payload["sources"] = native_payload["evidence"] = []
    report = ReportBuilder.from_scout_result(query="Example", scout_data=native_payload,
                                             execution_log=[{"channel": "web", "status": "TIMEOUT"}]).to_dict()
    assert sum(len(items) for items in report["evidence"].values()) == 0
    assert len(report["discovery"]) == 1
    assert report["trust"]["query_telemetry"]["queries_timed_out"] == 1
    assert report["trust"]["query_telemetry"]["queries_succeeded"] == 0


def test_zero_quality_value_and_structured_summary_remain_truthful():
    report = ReportBuilder.from_brandshield_result(query="Example", brand_data={
        "summary": {"total_findings": 0}, "quality_tensor": {"contradiction": 0}}).to_dict()
    assert report["trust"]["quality_tensor"]["contradiction"] == 0
    assert "{'total_findings'" not in report["summary"]
