"""
Offline Unit & API Tests for Huginn Continuous Source Monitoring
================================================================
Tests secret verification, SSRF defense, SHA-256 integrity, deduplication,
anti-amplification (independent confirmation suppression), bounded retention,
PlatformAdapter normalization, and FastAPI webhook routing.
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.infrastructure.acquisition.adapters.events.huginn import (
    HUGINN_WEBHOOK_SECRET_ENV,
    HuginnEvent,
    HuginnMonitoringAdapter,
    HuginnMonitoringIngestor,
    huginn_ingestor,
)
from backend.main import app
from backend.services.agent_reach.channels import CandidateSource, RetrievalRequest


@pytest.fixture(autouse=True)
def clean_huginn_state(monkeypatch):
    huginn_ingestor.clear()
    monkeypatch.setenv(HUGINN_WEBHOOK_SECRET_ENV, "test-super-secret-key-42")
    yield
    huginn_ingestor.clear()


def test_huginn_auth_verification(monkeypatch):
    ingestor = HuginnMonitoringIngestor()
    monkeypatch.setenv(HUGINN_WEBHOOK_SECRET_ENV, "correct-secret")

    assert ingestor.verify_auth("correct-secret") is True
    assert ingestor.verify_auth("Bearer correct-secret") is True
    assert ingestor.verify_auth("wrong-secret") is False
    assert ingestor.verify_auth(None) is False

    # When no secret configured in env, reject all
    monkeypatch.delenv(HUGINN_WEBHOOK_SECRET_ENV, raising=False)
    assert ingestor.verify_auth("correct-secret") is False


def test_huginn_ssrf_blocking(monkeypatch):
    ingestor = HuginnMonitoringIngestor()
    monkeypatch.setenv(HUGINN_WEBHOOK_SECRET_ENV, "test-secret")

    payload = {
        "source_url": "http://169.254.169.254/latest/meta-data/",
        "content_text": "Sensitive AWS IAM data",
    }
    res = ingestor.ingest(payload, auth_secret="test-secret")
    assert res["status"] == "rejected"
    assert res["reason"] == "SSRF_BLOCKED"


def test_huginn_ingestion_and_content_hash(monkeypatch):
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.events.huginn.is_safe_url", lambda u: (True, "safe"))
    ingestor = HuginnMonitoringIngestor()
    monkeypatch.setenv(HUGINN_WEBHOOK_SECRET_ENV, "test-secret")

    payload = {
        "huginn_event_id": "evt_disclosure_001",
        "source_url": "https://sec.gov/edgar/data/12345/form8k.htm",
        "source_identity": "sec_edgar_rss",
        "event_type": "financial_disclosure",
        "title": "Form 8-K: Material Definitive Agreement",
        "content_text": "Acme Corp entered into an amended credit facility with primary syndicate lenders.",
        "observed_published_at": "2026-10-20T16:00:00Z",
        "target_entity": "Acme Corp",
        "agent_target": "scout",
    }

    res = ingestor.ingest(payload, auth_secret="test-secret")
    assert res["status"] == "success"
    assert res["event_id"] == "evt_disclosure_001"
    assert res["is_duplicate"] is False
    # First-seen is uniqueness, not source independence or corroboration.
    assert res["independent_confirmation"] is False
    assert len(res["content_hash"]) == 64

    # Verify retrieval
    events = ingestor.get_events(agent_target="scout")
    assert len(events) == 1
    assert events[0].huginn_event_id == "evt_disclosure_001"
    assert events[0].target_entity == "Acme Corp"


def test_huginn_deduplication_anti_amplification(monkeypatch):
    """
    Test that identical content or URL from multiple feed polls does NOT
    create multiple independent confirmations.
    """
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.events.huginn.is_safe_url", lambda u: (True, "safe"))
    ingestor = HuginnMonitoringIngestor()
    monkeypatch.setenv(HUGINN_WEBHOOK_SECRET_ENV, "test-secret")

    story_body = "Quarterly financial guidance revised upward following unexpected enterprise sales."

    # First event (original publication)
    res1 = ingestor.ingest(
        {
            "huginn_event_id": "evt_primary_01",
            "source_url": "https://wire.example.com/story-100",
            "content_text": story_body,
        },
        auth_secret="test-secret",
    )
    assert res1["is_duplicate"] is False
    assert res1["independent_confirmation"] is False

    # Second event: same URL re-polled
    res2 = ingestor.ingest(
        {
            "huginn_event_id": "evt_secondary_repolled",
            "source_url": "https://wire.example.com/story-100",
            "content_text": story_body,
        },
        auth_secret="test-secret",
    )
    assert res2["is_duplicate"] is True
    assert res2["independent_confirmation"] is False
    assert res2["duplicate_reference"] == "evt_primary_01"

    # Third event: syndicated wire copied to different URL with exact same body text
    res3 = ingestor.ingest(
        {
            "huginn_event_id": "evt_syndicated_copy",
            "source_url": "https://syndicate-partner.example.com/reprint-100",
            "content_text": story_body,
        },
        auth_secret="test-secret",
    )
    assert res3["is_duplicate"] is True
    assert res3["independent_confirmation"] is False
    assert res3["duplicate_reference"] == "evt_primary_01"


def test_huginn_bounded_capacity_eviction(monkeypatch):
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.events.huginn.is_safe_url", lambda u: (True, "safe"))
    ingestor = HuginnMonitoringIngestor(max_capacity=3)
    monkeypatch.setenv(HUGINN_WEBHOOK_SECRET_ENV, "test-secret")

    for i in range(5):
        ingestor.ingest(
            {
                "huginn_event_id": f"evt_{i}",
                "source_url": f"https://news.example.com/article_{i}",
                "content_text": f"Unique content body for event number {i}",
            },
            auth_secret="test-secret",
        )

    # Only 3 events should be retained
    events = ingestor.get_events(limit=10)
    assert len(events) == 3
    retained_ids = [e.huginn_event_id for e in events]
    # Evicted 0 and 1; retained 4, 3, 2
    assert "evt_0" not in retained_ids
    assert "evt_1" not in retained_ids
    assert "evt_4" in retained_ids
    assert "evt_3" in retained_ids
    assert "evt_2" in retained_ids


def test_huginn_platform_adapter_contract(monkeypatch):
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.events.huginn.is_safe_url", lambda u: (True, "safe"))
    ingestor = HuginnMonitoringIngestor()
    monkeypatch.setenv(HUGINN_WEBHOOK_SECRET_ENV, "test-secret")

    ingestor.ingest(
        {
            "huginn_event_id": "evt_cve_99",
            "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2026-9999",
            "source_identity": "cve_security_feed",
            "event_type": "security_advisory",
            "title": "CVE-2026-9999 Vulnerability Report",
            "content_text": "Zero-day vulnerability disclosed in open-source logging daemon.",
        },
        auth_secret="test-secret",
    )

    adapter = HuginnMonitoringAdapter(ingestor=ingestor)
    candidate = CandidateSource(
        candidate_id="cand_huginn_99",
        url="https://nvd.nist.gov/vuln/detail/CVE-2026-9999",
        title="CVE-2026-9999 Advisory",
        platform="huginn_events",
        metadata={"huginn_event_id": "evt_cve_99"},
    )
    request = RetrievalRequest(query="CVE-2026-9999 vulnerability")

    doc = adapter.acquire(candidate, request)
    assert doc.status == "SUCCESS"
    assert "Zero-day vulnerability disclosed" in doc.raw_content

    frags = adapter.normalize(doc, candidate, request)
    assert len(frags) == 1
    assert frags[0].content_depth == "FEED_ENTRY_CONTENT"
    assert frags[0].actual_retrieval_channel == "huginn"
    assert frags[0].raw_metadata["independent_confirmation"] is False


def test_fastapi_huginn_webhook_endpoints(monkeypatch):
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.events.huginn.is_safe_url", lambda u: (True, "safe"))
    # Optional adapter scaffold is tested in an explicitly constructed app;
    # the normal application deliberately does not enable Huginn by default.
    from fastapi import FastAPI
    from backend.api.events import router
    optional_app = FastAPI()
    optional_app.include_router(router)
    client = TestClient(optional_app)

    # 1. Reject without auth
    resp1 = client.post(
        "/api/events/huginn",
        json={"source_url": "https://trusted.org/item", "content_text": "sample text"},
    )
    assert resp1.status_code == 401

    # 2. Accept with valid X-Huginn-Secret
    resp2 = client.post(
        "/api/events/huginn",
        headers={"X-Huginn-Secret": "test-super-secret-key-42"},
        json={
            "huginn_event_id": "evt_api_test",
            "source_url": "https://trusted.org/item",
            "source_identity": "brand_monitor_agent",
            "event_type": "brand_threat_mention",
            "content_text": "Brand impersonation domain registered targeting banking customers.",
            "target_entity": "MegaBank",
            "agent_target": "brandshield",
        },
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] == "success"
    assert data["event_id"] == "evt_api_test"

    # 3. GET query endpoint filters correctly
    assert client.get("/api/events/huginn?agent_target=brandshield").status_code == 401
    resp3 = client.get("/api/events/huginn?agent_target=brandshield",
                       headers={"X-Huginn-Secret": "test-super-secret-key-42"})
    assert resp3.status_code == 200
    query_data = resp3.json()
    assert query_data["status"] == "success"
    assert query_data["count"] >= 1
    assert query_data["events"][0]["target_entity"] == "MegaBank"


def test_huginn_sqlite_persistence_and_restart(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.events.huginn.is_safe_url", lambda u: (True, "safe"))
    db_file = str(tmp_path / "test_huginn.db")

    # 1. Create first ingestor instance with temporary DB
    ingestor1 = HuginnMonitoringIngestor(max_capacity=5, db_path=db_file)
    res1 = ingestor1.ingest(
        {
            "huginn_event_id": "evt_durable_1",
            "source_url": "https://threatintel.org/report-101",
            "source_identity": "cert_feed",
            "content_text": "Critical zero-day advisory impacting enterprise mail servers.",
            "agent_target": "scout",
            "target_entity": "MailCo",
        },
        bypass_auth_for_testing=True,
    )
    assert res1["status"] == "success"
    assert res1["is_duplicate"] is False

    # 2. Simulate server restart: create new ingestor instance pointing to same DB
    ingestor2 = HuginnMonitoringIngestor(max_capacity=5, db_path=db_file)
    retained = ingestor2.get_events()
    assert len(retained) == 1
    assert retained[0].huginn_event_id == "evt_durable_1"
    assert retained[0].target_entity == "MailCo"

    # 3. Re-ingest exact same content into new ingestor: must detect duplicate across restarts
    res2 = ingestor2.ingest(
        {
            "huginn_event_id": "evt_durable_2",
            "source_url": "https://threatintel.org/report-101",
            "source_identity": "cert_feed",
            "content_text": "Critical zero-day advisory impacting enterprise mail servers.",
        },
        bypass_auth_for_testing=True,
    )
    assert res2["status"] == "success"
    assert res2["is_duplicate"] is True
    assert res2["independent_confirmation"] is False
    assert res2["duplicate_reference"] == "evt_durable_1"


def test_huginn_inject_into_raw_pool(tmp_path, monkeypatch):
    from backend.services.research.raw_pool import RawAcquisitionPool

    monkeypatch.setattr("backend.infrastructure.acquisition.adapters.events.huginn.is_safe_url", lambda u: (True, "safe"))
    db_file = str(tmp_path / "test_huginn_pool.db")
    ingestor = HuginnMonitoringIngestor(max_capacity=10, db_path=db_file)

    body_text_primary = (
        "Acme Corp earnings report shows unexpected revenue drop in quarterly disclosure "
        "filed with global securities regulators early this morning ahead of the opening bell."
    )
    body_text_trending = (
        "Viral meme circulating on social media regarding corporate product defect allegations "
        "sparking massive consumer boycotts across multiple online retail platforms."
    )

    # Ingest 2 distinct events and 1 duplicate
    ingestor.ingest(
        {
            "huginn_event_id": "evt_pool_1",
            "source_url": "https://finance-news.com/wire/1",
            "source_identity": "financial_wire",
            "content_text": body_text_primary,
            "agent_target": "scout",
            "target_entity": "Acme Corp",
        },
        bypass_auth_for_testing=True,
    )
    ingestor.ingest(
        {
            "huginn_event_id": "evt_pool_2",
            "source_url": "https://social-pulse.com/trend/2",
            "source_identity": "meme_tracker",
            "content_text": body_text_trending,
            "agent_target": "trending",
            "target_entity": "Acme Corp",
        },
        bypass_auth_for_testing=True,
    )
    # Duplicate of evt_pool_1
    ingestor.ingest(
        {
            "huginn_event_id": "evt_pool_3",
            "source_url": "https://syndicate-clone.com/wire/1",
            "source_identity": "syndicate_mirror",
            "content_text": body_text_primary,
            "agent_target": "scout",
            "target_entity": "Acme Corp",
        },
        bypass_auth_for_testing=True,
    )

    pool = RawAcquisitionPool("inv_test_huginn_inject")
    added = ingestor.inject_into_raw_pool(pool, agent_target="scout", target_entity="Acme Corp")
    assert len(added) == 2

    # Check that duplicate in pool has duplicate_of set and is marked
    sources = pool._sources
    primary_src = next((s for s in sources.values() if "finance-news.com" in s["source_url"]), None)
    assert primary_src is not None

    dup_src = next((s for s in sources.values() if "syndicate-clone" in s["source_url"]), None)
    assert dup_src is not None
    assert dup_src["duplicate_of"] is not None


