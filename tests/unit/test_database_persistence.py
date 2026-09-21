"""
Aegis Protocol — Unit Tests: Database Persistence & SQLite Fallback
===================================================================
Tests resilient local SQLite persistence when Supabase is disconnected:
- Claim insertion and idempotent retrieval
- source_url preservation
- Claim status and verdict lifecycle updates
- Evidence insertion and relationship retrieval
"""

import os
import tempfile
import pytest
from backend.db import database as db


@pytest.fixture(autouse=True)
def isolated_sqlite_db(monkeypatch):
    """Ensure tests run against a clean isolated temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db_path = tf.name
    
    monkeypatch.setattr(db, "SQLITE_DB_PATH", temp_db_path)
    monkeypatch.setattr(db, "supabase", None)  # Force offline fallback
    db._mem_claims.clear()
    db._mem_hash_index.clear()
    db._mem_evidence.clear()
    db._init_sqlite_db()
    
    yield temp_db_path
    
    try:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
    except Exception:
        pass


def test_sqlite_insert_and_retrieve_claim():
    claim_hash = "testhash1234567890abcdef"
    claim_text = "Mars has liquid water oceans on its surface."
    norm_text = "mars has liquid water oceans on its surface"
    src_url = "https://example.com/mars-news"

    row = db.insert_claim(
        claim_hash=claim_hash,
        claim_text=claim_text,
        normalized_text=norm_text,
        source_url=src_url
    )
    assert row["id"] is not None
    assert row["claim_hash"] == claim_hash
    assert row["source_url"] == src_url
    assert row["status"] == "pending"

    # Retrieve by ID
    by_id = db.get_claim_by_id(row["id"])
    assert by_id is not None
    assert by_id["claim_text"] == claim_text
    assert by_id["source_url"] == src_url

    # Retrieve by Hash
    by_hash = db.get_claim_by_hash(claim_hash)
    assert by_hash is not None
    assert by_hash["id"] == row["id"]


def test_sqlite_status_and_verdict_lifecycle():
    row = db.insert_claim(
        claim_hash="hash_lifecycle_test",
        claim_text="Test claim for status transition.",
        normalized_text="test claim for status transition"
    )
    cid = row["id"]

    # Update to in_progress
    up1 = db.update_claim_status(cid, "in_progress")
    assert up1["status"] == "in_progress"
    assert db.get_claim_by_id(cid)["status"] == "in_progress"

    # Update verdict
    up2 = db.update_claim_verdict(
        claim_id=cid,
        verdict="False",
        confidence=0.95,
        severity="High",
        reasoning="Debunked by empirical planetary science records."
    )
    assert up2["status"] == "completed"
    assert up2["verdict"] == "False"
    assert up2["confidence"] == 0.95

    # Verify reload from SQLite into clean memory
    db._mem_claims.clear()
    db._mem_hash_index.clear()
    db._init_sqlite_db()

    reloaded = db.get_claim_by_id(cid)
    assert reloaded is not None
    assert reloaded["verdict"] == "False"
    assert reloaded["confidence"] == 0.95


def test_sqlite_evidence_persistence():
    row = db.insert_claim(
        claim_hash="hash_evidence_test",
        claim_text="Test claim for evidence relationship.",
        normalized_text="test claim for evidence relationship"
    )
    cid = row["id"]

    ev1 = db.insert_evidence(
        claim_id=cid,
        evidence_text="Astronomical telescope spectroscopic data contradicts the claim.",
        source_url="https://nasa.gov/mars-observations",
        source_name="NASA Mars Program",
        credibility_score=0.98,
        stance="refuting"
    )
    assert ev1["id"] is not None
    assert ev1["stance"] == "refuting"

    ev_list = db.get_evidence_by_claim_id(cid)
    assert len(ev_list) == 1
    assert ev_list[0]["source_name"] == "NASA Mars Program"

    # Clear memory and reload from SQLite
    db._mem_evidence.clear()
    db._init_sqlite_db()

    reloaded_ev = db.get_evidence_by_claim_id(cid)
    assert len(reloaded_ev) == 1
    assert reloaded_ev[0]["source_url"] == "https://nasa.gov/mars-observations"
