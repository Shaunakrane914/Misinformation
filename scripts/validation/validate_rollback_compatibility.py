"""Offline persistence/restart validation; never implies a deployed rollback."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import types

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validation.isolated_runtime import (
    RESULT_PREFIX, block_live_network, run_worker, write_report_exclusively,
)

BASELINE_REF = "258cb4f1fc71c379d0e882d8804c2a9770fc7f60"
_REQUIRED_DOSSIER_FIELDS = {"session_id", "target", "domain", "created_at",
                            "candidate_hashes", "queries_executed", "decision_log",
                            "findings_provenance", "source_lineage"}


def inspect_dossier_archive(directory: Path) -> dict:
    """Read-only JSON/shape/integrity audit: legacy records are explicitly unsealed."""
    from backend.services.research.replay_ledger import verify_dossier_integrity
    counts = {"VERIFIED": 0, "LEGACY_UNSEALED": 0, "FAILED": 0}
    invalid = []
    for path in directory.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not _REQUIRED_DOSSIER_FIELDS <= data.keys():
                raise ValueError("Missing required dossier fields")
            if data["session_id"] != path.stem:
                raise ValueError("Session ID does not match filename")
            if not isinstance(data["candidate_hashes"], dict):
                raise ValueError("candidate_hashes must be an object")
            for field in ("queries_executed", "decision_log", "findings_provenance"):
                if not isinstance(data[field], list) or any(not isinstance(item, dict) for item in data[field]):
                    raise ValueError(f"{field} must be an array of objects")
            if not isinstance(data["source_lineage"], dict):
                raise ValueError("source_lineage must be an object")
            integrity = verify_dossier_integrity(data)
            counts[integrity["status"]] += 1
            if integrity["status"] == "FAILED":
                invalid.append(path.name)
        except (OSError, ValueError, TypeError, KeyError):
            counts["FAILED"] += 1
            invalid.append(path.name)
    status = "FAIL" if invalid else ("PASS" if sum(counts.values()) else "NOT_VERIFIED")
    return {"status": status, "counts": counts,
            "invalid_files": invalid,
            "disclosure": "Legacy JSON readability is not cryptographic integrity verification."}


def _producer() -> dict:
    from backend.db import database as db
    from backend.services.research.replay_ledger import replay_ledger
    claim = db.insert_claim("rollback-probe-hash", "Offline rollback probe", "offline rollback probe")
    db.update_claim_verdict(claim["id"], "Insufficient Evidence", 0.0, "Low", "Offline probe")
    db.insert_evidence(claim["id"], "Validation-only evidence", "https://example.com/probe",
                       "Probe", 0.0, "neutral")
    dossier_id = replay_ledger.record_investigation(
        target="Offline rollback probe", domain="general", summary="Validation-only record",
        candidates=[{"id": "ev_probe", "content": "Validation-only evidence"}],
        findings=[], queries=[], telemetry={}, lineage_graph={"nodes": []},
    )
    return {"claim_id": claim["id"], "dossier_id": dossier_id, "pid": os.getpid()}


def _consumer() -> dict:
    from backend.db import database as db
    from backend.services.research.replay_ledger import replay_ledger, verify_dossier_integrity
    from backend.main import app
    from starlette.testclient import TestClient
    claim = db.get_claim_by_hash("rollback-probe-hash")
    assert claim and claim["verdict"] == "Insufficient Evidence", "Persisted claim did not reload"
    evidence = db.get_evidence_by_claim_id(claim["id"])
    assert len(evidence) == 1 and evidence[0]["evidence_text"] == "Validation-only evidence"
    with sqlite3.connect(db.SQLITE_DB_PATH) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"claims", "evidence", "claim_research"} <= tables
    archive = inspect_dossier_archive(Path(replay_ledger.storage_dir))
    assert archive["status"] == "PASS" and archive["counts"]["VERIFIED"] == 1
    dossier_path = next(Path(replay_ledger.storage_dir).glob("*.json"))
    data = json.loads(dossier_path.read_text(encoding="utf-8"))
    assert replay_ledger.get_dossier(data["session_id"]) is not None
    tampered = dict(data, summary="tampered")
    assert verify_dossier_integrity(tampered)["status"] == "FAILED", "Tampering was not detected"
    legacy = {key: value for key, value in data.items() if key != "integrity"}
    assert verify_dossier_integrity(legacy)["status"] == "LEGACY_UNSEALED"
    with TestClient(app) as client:
        health = client.get("/api/healthz")
        ready = client.get("/api/readyz")
        assert health.status_code == ready.status_code == 200
    return {"pid": os.getpid(), "claim_id": claim["id"], "archive": archive,
            "tamper_detection": "PASS", "legacy_unsealed_disclosure": "PASS",
            "healthz": health.json()["status"], "readyz": ready.json()["status"]}


def _load_baseline_module(ref: str, path: str, name: str):
    source = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=REPO_ROOT,
                            check=True, text=True, encoding="utf-8", capture_output=True).stdout
    # Redirect only the historical reader's singleton construction to temp data.
    source = source.replace("replay_ledger = ReplayLedger()",
                            "replay_ledger = ReplayLedger(storage_dir=os.environ['AEGIS_DOSSIER_DIR'])")
    module = types.ModuleType(name)
    module.__file__ = str(REPO_ROOT / path)
    sys.modules[name] = module
    exec(compile(source, f"{ref}:{path}", "exec"), module.__dict__)
    return module


def _legacy_reader(ref: str) -> dict:
    database = _load_baseline_module(ref, "backend/db/database.py", "aegis_legacy_database_probe")
    ledger = _load_baseline_module(ref, "backend/services/research/replay_ledger.py", "aegis_legacy_ledger_probe")
    claim = database.get_claim_by_hash("rollback-probe-hash")
    assert claim and claim["claim_text"] == "Offline rollback probe"
    assert database.get_evidence_by_claim_id(claim["id"])
    path = next(Path(os.environ["AEGIS_DOSSIER_DIR"]).glob("*.json"))
    dossier = ledger.replay_ledger.get_dossier(path.stem)
    assert dossier and dossier["target"] == "Offline rollback probe"
    return {"status": "PASS", "baseline_commit": ref, "pid": os.getpid(),
            "scope": "Actual historical SQLite and JSON readers, not a full old-version deployment"}


def _resolve_baseline(ref: str) -> str | None:
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", ref):
        raise ValueError("Baseline must be a commit SHA (7-40 hex characters)")
    try:
        result = subprocess.run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
                                cwd=REPO_ROOT, text=True, capture_output=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else None
    except OSError:
        return None


def test_rollback_compatibility(baseline_ref: str = BASELINE_REF,
                              archive: Path = REPO_ROOT / "backend" / "data" / "dossiers") -> dict:
    with tempfile.TemporaryDirectory(prefix="aegis-rollback-") as directory:
        storage = Path(directory)
        producer = run_worker(Path(__file__), "producer", storage)
        consumer = run_worker(Path(__file__), "consumer", storage)
        assert producer["pid"] != consumer["pid"], "Restart must use a new OS process"
        assert producer["claim_id"] == consumer["claim_id"]
        before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in (storage / "dossiers").glob("*.json")}
        baseline = _resolve_baseline(baseline_ref)
        legacy = run_worker(Path(__file__), "legacy", storage, "--baseline-ref", baseline) if baseline else {
            "status": "NOT_VERIFIED", "reason": "Baseline commit or git unavailable locally"}
        after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in (storage / "dossiers").glob("*.json")}
        assert before == after, "Legacy reader changed persisted dossier bytes"
        historical = run_worker(Path(__file__), "archive", storage, "--archive", str(archive))
    return {"suite": "Offline persistence and rollback reader validation", "execution_mode": "OFFLINE_REGRESSION",
            "checks": {"fresh_process_reload": {"status": "PASS", "producer_pid": producer["pid"],
                                                 "consumer_pid": consumer["pid"]},
                       "persistent_state": consumer, "historical_readers": legacy,
                       "historical_archive_read_only": historical,
                       "preserved_dossier_bytes": "PASS",
                       "deployed_previous_version": {"status": "NOT_VERIFIED",
                                                      "reason": "Requires an owner-controlled staging rollback"}},
            "verdict": "HISTORICAL_ARCHIVE_FAIL" if historical["status"] == "FAIL" else "OFFLINE_PERSISTENCE_PASS"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default=BASELINE_REF)
    parser.add_argument("--output", type=Path, help="Create a new report without overwriting existing files")
    parser.add_argument("--archive", type=Path, default=REPO_ROOT / "backend" / "data" / "dossiers",
                        help="Read-only historical JSON archive audit; empty archives are NOT_VERIFIED")
    parser.add_argument("--worker", choices=["producer", "consumer", "legacy", "archive"], help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        block_live_network()
        result = {"producer": _producer, "consumer": _consumer,
                  "legacy": lambda: _legacy_reader(args.baseline_ref),
                  "archive": lambda: inspect_dossier_archive(args.archive)}[args.worker]()
        print(RESULT_PREFIX + json.dumps(result))
        return 0
    result = test_rollback_compatibility(args.baseline_ref, args.archive)
    if args.output:
        write_report_exclusively(args.output, result)
    print(json.dumps(result, indent=2))
    return 1 if result["verdict"] == "HISTORICAL_ARCHIVE_FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
