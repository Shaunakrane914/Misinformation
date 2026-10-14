"""Malformed legacy nested records fail honestly before playback or refetch."""

from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import replay
from backend.services.research.replay_ledger import ReplayLedger, _payload_hash, verify_dossier_integrity
from backend.services.agent_reach import agent_reach_service


def legacy_dossier():
    return {
        "session_id": "R-2026-STRUCTURE", "target": "A legacy investigation", "domain": "general",
        "queries_executed": [{"channel": "web", "query_text": "A legacy investigation"}],
        "candidate_hashes": {"ev": "abcdef0123456789"},
        "decision_log": [{"stage": "QueryPlanning", "rationale": "Research", "decision_type": "QUERY_GENERATION"}],
        "source_lineage": {"nodes": [{"id": "ev", "url": "https://example.org/article"}]},
        "findings_provenance": [{"primary_sources": ["https://example.org/article"]}],
    }


MALFORMED = [
    ("queries_executed", ["bad nested query"]),
    ("queries_executed", {"channel": "web"}),
    ("queries_executed", None),
    ("queries_executed", [{"channel": {"bad": "value"}}]),
    ("queries_executed", [{"query_text": ["bad"]}]),
    ("decision_log", [None]),
    ("decision_log", {"stage": "QueryPlanning"}),
    ("decision_log", [{"rationale": ["bad"]}]),
    ("decision_log", [{"evidence_ids_affected": [None]}]),
    ("candidate_hashes", []),
    ("candidate_hashes", {"ev": "not-a-hash"}),
    ("candidate_hashes", {"ev": ""}),
    ("candidate_hashes", {"ev": ["abcdef0123456789"]}),
    ("candidate_snapshots", {"ev": []}),
    ("candidate_snapshots", {"ev": {"content": {}, "sha256": "a" * 64}}),
    ("source_lineage", None),
    ("source_lineage", {"nodes": ["bad node"]}),
    ("source_lineage", {"nodes": [{"id": {"bad": "value"}}]}),
    ("source_lineage", {"nodes": [{"url": ["https://example.org"]}]}),
    ("source_lineage", {"edges": ["bad edge"]}),
    ("findings_provenance", ["bad finding"]),
    ("findings_provenance", [{"primary_sources": [17]}]),
    ("findings_provenance", [{"primary_sources": "https://example.org"}]),
    ("findings_provenance", [{"supporting_evidence_ids": None}]),
    ("findings_provenance", [{"quality_tensor": []}]),
    ("saturation_summary", []),
    ("capability_graph", ["bad capability"]),
    ("integrity", []),
]


@pytest.mark.parametrize("field_name, invalid", MALFORMED)
@pytest.mark.parametrize("mode", ["trace_playback", "refetch_verification"])
def test_malformed_nested_shapes_fail_before_any_walk_or_network(tmp_path, monkeypatch, field_name, invalid, mode):
    data = legacy_dossier()
    data[field_name] = deepcopy(invalid)
    check = verify_dossier_integrity(data)
    assert check["status"] == "FAILED"
    assert not check["valid"]
    assert field_name in check["reason"]
    ledger = ReplayLedger(str(tmp_path))
    ledger._memory_cache[data["session_id"]] = data
    read = MagicMock()
    monkeypatch.setattr(agent_reach_service, "read", read)
    result = ledger.replay_investigation(data["session_id"], mode=mode)
    assert result["status"] == "failed"
    assert result["integrity_status"] == "FAILED"
    assert result["candidates_integrity_verified"] == 0
    assert result["findings_verified"] == 0
    assert result["total_queries_replayed"] == 0
    assert result["sources_checked"] == 0
    assert result["playback_steps"] == []
    assert not list(tmp_path.rglob("*.json")), "Validation must not repair or rewrite stored dossiers"
    read.assert_not_called()


def test_valid_unsealed_legacy_with_missing_modern_fields_stays_readable(tmp_path):
    data = legacy_dossier()
    ledger = ReplayLedger(str(tmp_path))
    ledger._memory_cache[data["session_id"]] = data
    result = ledger.replay_investigation(data["session_id"])
    assert result["status"] == "success"
    assert result["integrity_status"] == "LEGACY_UNSEALED"
    assert result["total_queries_replayed"] == 1
    assert result["candidates_integrity_verified"] == 0
    minimal = {"session_id": "R-2026-MINIMAL"}
    ledger._memory_cache[minimal["session_id"]] = minimal
    assert ledger.replay_investigation(minimal["session_id"])["integrity_status"] == "LEGACY_UNSEALED"
    # Unavailable historical quality metrics are represented honestly as null.
    data["findings_provenance"][0]["quality_tensor"] = None
    assert verify_dossier_integrity(data)["status"] == "LEGACY_UNSEALED"


def test_structural_failure_cannot_be_hidden_by_matching_payload_checksum():
    data = legacy_dossier()
    data["queries_executed"] = ["bad nested query"]
    data["integrity"] = {"version": 1, "algorithm": "sha256", "payload_sha256": _payload_hash(data)}
    check = verify_dossier_integrity(data)
    assert check["status"] == "FAILED"
    assert "queries_executed" in check["reason"]


@pytest.mark.parametrize("prefix", ["/api/replay", "/api/research/replay"])
@pytest.mark.parametrize("mode", ["trace_playback", "refetch_verification"])
def test_replay_api_reports_malformed_existing_dossier_not_missing(tmp_path, monkeypatch, prefix, mode):
    data = legacy_dossier()
    data["queries_executed"] = ["bad nested query"]
    ledger = ReplayLedger(str(tmp_path))
    ledger._memory_cache[data["session_id"]] = data
    monkeypatch.setattr(replay, "replay_ledger", ledger)
    app = FastAPI()
    app.include_router(replay.router)
    app.include_router(replay.alias_router)
    response = TestClient(app).post(f"{prefix}/reexecute/{data['session_id']}?mode={mode}")
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["integrity_status"] == "FAILED"
    assert "queries_executed" in response.json()["integrity_check"]["reason"]


@pytest.mark.parametrize("data", [None, [], "not a dossier"])
def test_nonobject_integrity_input_fails_without_exception(data):
    assert verify_dossier_integrity(data)["status"] == "FAILED"


def test_writer_rejects_bad_nested_query_before_publishing_any_file(tmp_path):
    ledger = ReplayLedger(str(tmp_path / "writer"))
    with pytest.raises(ValueError, match="queries_executed"):
        ledger.record_investigation(
            target="Rejected query", domain="general", summary="Invalid",
            candidates=[], findings=[], queries=["bad nested query"],
            telemetry={}, lineage_graph={},
        )
    assert not ledger._memory_cache
    assert not list((tmp_path / "writer").iterdir())
