"""Fail-closed, explicit advisory runs; shared accounting/cooldown, no secrets.

SQLite transactions serialize reservations across gateway/provider instances and
processes. A crashed in-flight reservation stays blocked (owner intervention),
not silently retried. Timeouts consume the reserved request.
"""
from contextlib import contextmanager
from contextlib import closing
from contextvars import ContextVar
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid

MODEL = "gemini-3.5-flash-lite"
PURPOSES = {"search_suggestion", "passage_suggestion"}
_run = ContextVar("aegis_advisory_run", default=None)
_investigation = ContextVar("aegis_advisory_investigation", default=None)


class AdvisoryPolicyError(RuntimeError):
    pass


def _connect(path):
    connection = sqlite3.connect(path, timeout=2, isolation_level=None)
    connection.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, calls INTEGER NOT NULL)")
    connection.execute("CREATE TABLE IF NOT EXISTS investigations (run TEXT, id TEXT, PRIMARY KEY(run,id))")
    connection.execute("CREATE TABLE IF NOT EXISTS provider (id INTEGER PRIMARY KEY, cooldown REAL, busy TEXT)")
    connection.execute("INSERT OR IGNORE INTO provider VALUES (1,0,NULL)")
    return connection


@contextmanager
def advisory_run(*, verified_models=(), database=None):
    """Explicitly authorized development run. Model support must be established
    separately without generation; tests supply offline account observations.
    Nesting cannot reset an existing run's hard three-request budget.
    """
    if _run.get() is not None:
        yield _run.get()
        return
    if MODEL not in verified_models:
        raise AdvisoryPolicyError("Advisory model support has not been verified")
    path = Path(database or os.getenv("AEGIS_AI_POLICY_DB", str(Path(tempfile.gettempdir()) / "aegis-advisory-policy.sqlite3")))
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {"id": uuid.uuid4().hex, "database": str(path), "closed": False}
    with closing(_connect(path)) as connection:
        connection.execute("INSERT INTO runs VALUES (?,0)", (state["id"],))
    token = _run.set(state)
    try:
        yield state
    finally:
        state["closed"] = True
        _run.reset(token)


@contextmanager
def investigation_scope(identity=None):
    token = _investigation.set(_investigation.get() or identity or uuid.uuid4().hex)
    try:
        yield
    finally:
        _investigation.reset(token)


def require_advisory(purpose):
    state = _run.get()
    if purpose not in PURPOSES or not state or state["closed"] or not _investigation.get():
        raise AdvisoryPolicyError("Live AI disabled: explicit advisory run, investigation and permitted purpose required")
    return state


@contextmanager
def reserve_request(purpose):
    state = require_advisory(purpose)
    reservation = uuid.uuid4().hex
    connection = _connect(state["database"])
    try:
        connection.execute("BEGIN IMMEDIATE")
        cooldown, busy = connection.execute("SELECT cooldown,busy FROM provider WHERE id=1").fetchone()
        calls = connection.execute("SELECT calls FROM runs WHERE id=?", (state["id"],)).fetchone()[0]
        used = connection.execute("SELECT 1 FROM investigations WHERE run=? AND id=?", (state["id"], _investigation.get())).fetchone()
        if cooldown > time.time() or busy or calls >= 3 or used:
            raise AdvisoryPolicyError("Advisory cooldown, in-flight reservation or hard request budget blocks this call")
        connection.execute("UPDATE runs SET calls=calls+1 WHERE id=?", (state["id"],))
        connection.execute("INSERT INTO investigations VALUES (?,?)", (state["id"], _investigation.get()))
        connection.execute("UPDATE provider SET busy=? WHERE id=1", (reservation,))
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        raise
    try:
        yield
    finally:
        connection.execute("UPDATE provider SET busy=NULL WHERE id=1 AND busy=?", (reservation,))
        connection.close()


def set_cooldown(seconds):
    state = _run.get()
    if state:
        with closing(_connect(state["database"])) as connection:
            connection.execute("UPDATE provider SET cooldown=MAX(cooldown,?) WHERE id=1", (time.time() + max(30, seconds),))


def call_count():
    state = _run.get()
    if not state:
        return 0
    with closing(_connect(state["database"])) as connection:
        return connection.execute("SELECT calls FROM runs WHERE id=?", (state["id"],)).fetchone()[0]
