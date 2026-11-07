"""Completed reports in the existing SQLite store; links identify actual saved results.

Recent lists require caller-held IDs rather than exposing other users' queries.
No jobs are restarted by a read, and a failed write never produces a saved link.
"""
import asyncio
from datetime import datetime, timezone
import json
import logging
import sqlite3
import uuid

logger = logging.getLogger(__name__)
MAX_REPORT_BYTES = 16 * 1024 * 1024


def _connection():
    from backend.db import database
    if database.SQLITE_DB_PATH == ":memory:":
        raise ValueError("Report history requires persistent SQLite storage")
    connection = sqlite3.connect(database.SQLITE_DB_PATH, timeout=5)
    connection.execute("""CREATE TABLE IF NOT EXISTS investigation_reports (
        id TEXT PRIMARY KEY, agent TEXT NOT NULL, query TEXT NOT NULL,
        created_at TEXT NOT NULL, report_json TEXT NOT NULL)""")
    return connection


def save_report(report):
    if not isinstance(report, dict) or not isinstance(report.get("_meta"), dict):
        raise ValueError("A structured report is required")
    identifier = str(uuid.uuid4())
    saved = {**report, "_meta": {**report["_meta"], "investigation_id": identifier,
        "permalink": f"/status.html?report={identifier}", "history_status": "SAVED"}}
    if isinstance(saved.get("misinformation_dossier"), dict):
        saved["misinformation_dossier"] = {**saved["misinformation_dossier"], "investigation_id": identifier}
    encoded = json.dumps(saved, ensure_ascii=True, allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_REPORT_BYTES:
        raise ValueError("Report exceeds the bounded history record size")
    with _connection() as connection:
        connection.execute("INSERT INTO investigation_reports VALUES (?, ?, ?, ?, ?)",
            (identifier, str(report["_meta"].get("agent") or "claim_verifier"),
             str(report["_meta"].get("query") or "")[:1000],
             datetime.now(timezone.utc).isoformat(), encoded))
    return saved


def get_report(identifier):
    try:
        identifier = str(uuid.UUID(identifier))
    except (ValueError, TypeError, AttributeError):
        return None
    with _connection() as connection:
        row = connection.execute("SELECT report_json FROM investigation_reports WHERE id = ?", (identifier,)).fetchone()
    return json.loads(row[0]) if row else None


def recent_reports(identifiers):
    records = []
    for identifier in list(dict.fromkeys(identifiers))[:50]:
        report = get_report(identifier)
        if report:
            meta = report["_meta"]
            records.append({"id": meta["investigation_id"], "agent": meta.get("agent"),
                "query": meta.get("query"), "created_at": meta.get("generated_at"),
                "summary": report.get("summary"), "status": report.get("investigation_status"),
                "permalink": meta["permalink"],
                "passage_words": report.get("evidence_workbench", {}).get("accounting", {}).get("published_unique_words", 0)})
    return sorted(records, key=lambda item: item.get("created_at") or "", reverse=True)


def record_result_sync(payload):
    report = payload.get("unified_report") if isinstance(payload, dict) else None
    if not isinstance(report, dict):
        return payload
    try:
        payload["unified_report"] = save_report(report)
        payload["investigation_id"] = payload["unified_report"]["_meta"]["investigation_id"]
    except (OSError, sqlite3.Error, ValueError, TypeError):
        logger.warning("Completed report could not be saved to investigation history")
        report.setdefault("_meta", {})["history_status"] = "UNAVAILABLE"
    return payload


async def record_result(payload):
    return await asyncio.to_thread(record_result_sync, payload)
