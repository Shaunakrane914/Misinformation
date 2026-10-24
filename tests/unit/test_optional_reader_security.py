"""Offline injected-provider controls; never live reader/monitoring acceptance."""
import asyncio
import json
import sqlite3
import threading
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from backend.api import events
from backend.infrastructure.acquisition.adapters.events import huginn
from backend.infrastructure.acquisition.adapters.web import firecrawl, jina
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse, ProviderHTTPError


@pytest.fixture
def ingestor(monkeypatch):
    monkeypatch.setenv("HUGINN_WEBHOOK_SECRET", "offline-auth-token")
    monkeypatch.setattr(huginn, "is_safe_url", lambda _url: (True, "safe"))
    instance = huginn.HuginnMonitoringIngestor(db_path=":memory:")
    monkeypatch.setattr(events, "huginn_ingestor", instance)
    return instance


def _event(event_id="one", **changes):
    return {"huginn_event_id": event_id, "source_url": "https://publisher.example/story-" + event_id,
            "content_text": "Captured feed text, not independent confirmation. " * 5, **changes}


def _client():
    app = FastAPI()
    app.include_router(events.router)
    return TestClient(app)


def _ingest(instance, payload):
    return instance.ingest(payload, auth_secret="offline-auth-token")


def _reader_response(payload):
    return BoundedHTTPResponse(body=json.dumps(payload).encode(), endpoint="https://api.firecrawl.dev/v1/scrape",
                               status_code=200, content_type="application/json", headers={}, latency_ms=1, attempts=1)


def test_optional_webhook_auth_before_consuming_any_body(ingestor):
    async def receive():
        pytest.fail("Unauthenticated webhook consumed the body")
    request = Request({"type": "http", "headers": []}, receive)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as failure:
        asyncio.run(events.receive_huginn_event(request, None, None))
    assert failure.value.status_code == 401


def test_optional_event_reads_require_authentication(ingestor):
    _ingest(ingestor, _event())
    client = _client()
    assert client.get("/api/events/huginn").status_code == 401
    assert client.get("/api/events/huginn", headers={"Authorization": "Bearer wrong"}).status_code == 401
    response = client.get("/api/events/huginn", headers={"Authorization": "Bearer offline-auth-token"})
    assert response.status_code == 200 and response.json()["count"] == 1


def test_authenticated_webhook_rejects_oversized_declared_body(ingestor):
    response = _client().post("/api/events/huginn", content=b"{}", headers={
        "X-Huginn-Secret": "offline-auth-token", "content-type": "application/json",
        "content-length": str(huginn.MAX_HUGINN_PAYLOAD_BYTES + 1)})
    assert response.status_code == 413 and ingestor.get_events() == []


def test_authenticated_chunked_webhook_has_actual_byte_limit(ingestor):
    payload = [b"x" * 70_000, b"x" * 70_000]
    async def receive():
        return {"type": "http.request", "body": payload.pop(0), "more_body": bool(payload)}
    request = Request({"type": "http", "headers": [(b"content-type", b"application/json")]}, receive)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as failure:
        asyncio.run(events.receive_huginn_event(request, "offline-auth-token", None))
    assert failure.value.status_code == 413


def test_webhook_offloads_blocking_ingestion(ingestor, monkeypatch):
    caller = threading.get_ident()
    def ingest(*args, **kwargs):
        assert threading.get_ident() != caller
        return {"status": "success"}
    monkeypatch.setattr(ingestor, "ingest", ingest)
    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}
    request = Request({"type": "http", "headers": [(b"content-type", b"application/json")]}, receive)
    assert asyncio.run(events.receive_huginn_event(request, "offline-auth-token", None))["status"] == "success"


@pytest.mark.parametrize("changes", [
    {"source_url": ["https://publisher.example/"]}, {"content_text": {"not": "text"}},
    {"metadata": []}, {"metadata": {"large": "x" * 9000}}, {"agent_target": "unknown"},
    {"content_text": "x" * (huginn.MAX_HUGINN_CONTENT_BYTES + 1)}, {"observed_published_at": "not-a-date"},
    {"content_hash": "not-a-sha256"}, {"metadata": {"nested": [[[[[[[[1]]]]]]]]}},
])
def test_monitoring_rejects_bad_types_and_bounds(ingestor, changes):
    assert _ingest(ingestor, _event(**changes))["reason"] == "INVALID_PAYLOAD"
    assert ingestor.get_events() == []


def test_checksum_mismatch_is_rejected_not_relabelled(ingestor):
    result = _ingest(ingestor, _event(content_hash="0" * 64))
    assert result["reason"] == "CONTENT_HASH_MISMATCH" and ingestor.get_events() == []


def test_event_id_retries_are_idempotent_and_changes_conflict(ingestor):
    payload = _event()
    assert _ingest(ingestor, payload)["status"] == "success"
    assert _ingest(ingestor, payload)["idempotent"] is True
    assert _ingest(ingestor, _event(content_text="different"))["reason"] == "EVENT_ID_CONFLICT"
    rows = ingestor.get_events()
    assert len(rows) == 1 and rows[0].content_text == payload["content_text"].strip()
    assert rows[0].independent_confirmation is False


def test_duplicates_persist_without_deleting_original_and_restart_stays_bounded(ingestor, tmp_path):
    path = str(tmp_path / "events.db")
    store = huginn.HuginnMonitoringIngestor(max_capacity=3, db_path=path)
    _ingest(store, _event("original"))
    _ingest(store, _event("copy"))
    restored = huginn.HuginnMonitoringIngestor(max_capacity=3, db_path=path)
    assert {e.huginn_event_id for e in restored.get_events()} == {"original", "copy"}
    copied = next(e for e in restored.get_events() if e.huginn_event_id == "copy")
    assert copied.is_duplicate and copied.duplicate_reference == "original"
    _ingest(restored, _event("new", content_text="new content"))
    _ingest(restored, _event("later"))  # Original evicted; retained copy still knows lineage.
    _ingest(restored, _event("last"))
    assert restored.get_events()[0].duplicate_reference == "original"
    restarted = huginn.HuginnMonitoringIngestor(max_capacity=3, db_path=path)
    assert [e.huginn_event_id for e in restarted.get_events()] == ["last", "later", "new"]
    assert len(restarted._seen_hashes) <= 3 and len(restarted._seen_urls) <= 3
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM huginn_events_v2").fetchone()[0] == 3


def test_storage_failure_is_not_acknowledged_as_durable_success(ingestor, monkeypatch):
    monkeypatch.setattr(ingestor, "_save_to_db", lambda *a: False)
    assert _ingest(ingestor, _event())["reason"] == "PERSISTENCE_FAILED"
    assert ingestor.get_events() == []


def test_legacy_storage_migration_preserves_original_table_and_conservative_state(ingestor, tmp_path):
    template = str(tmp_path / "schema-template.db")
    store = huginn.HuginnMonitoringIngestor(db_path=template)
    _ingest(store, _event("legacy"))
    with sqlite3.connect(template) as conn:
        schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='huginn_events_v2'").fetchone()[0]
        row = list(conn.execute("SELECT * FROM huginn_events_v2").fetchone())
    row[14] = 1  # The historical implementation asserted independence wrongly.
    legacy_path = str(tmp_path / "legacy.db")
    with sqlite3.connect(legacy_path) as conn:
        conn.execute(schema.replace("huginn_events_v2", "huginn_events"))
        conn.execute("INSERT INTO huginn_events VALUES (" + ",".join("?" for _ in row) + ")", row)
    migrated = huginn.HuginnMonitoringIngestor(db_path=legacy_path)
    assert migrated.get_events()[0].huginn_event_id == "legacy"
    assert migrated.get_events()[0].independent_confirmation is False
    with sqlite3.connect(legacy_path) as conn:
        assert conn.execute("SELECT independent_confirmation FROM huginn_events").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM huginn_events_v2").fetchone()[0] == 1


def test_missing_monitoring_tags_do_not_match_every_investigation(ingestor):
    _ingest(ingestor, _event())
    assert ingestor.get_events(agent_target="scout") == []
    assert ingestor.get_events(target_entity="A different entity") == []


@pytest.mark.parametrize("endpoint", [
    "https://user:password@provider.example", "https://provider.example/?token=secret",
    "https://provider.example/#credential", "https://provider.example:not-a-port", "https://127.0.0.1",
    "https://[::1]", "https://provider.internal", "https://localhost",
])
def test_unsafe_provider_endpoint_is_not_configured_or_echoed(endpoint):
    adapter = firecrawl.FirecrawlAdapter(base_url=endpoint, api_key="offline-placeholder")
    assert adapter.health()["endpoint"] is None
    assert not adapter.is_configured()


def test_health_hides_even_path_embedded_secret_without_dns():
    adapter = firecrawl.FirecrawlAdapter(base_url="https://provider.example/secret-path", api_key="offline-placeholder")
    assert adapter.health()["endpoint"] == "https://provider.example"


@pytest.mark.parametrize("error", ["Bearer secret-value api_key=private", {"token": "private", "message": "unavailable"}])
def test_provider_failure_never_echoes_error_content(monkeypatch, error):
    monkeypatch.setattr(firecrawl, "is_safe_url", lambda _url: (True, "safe"))
    adapter = firecrawl.FirecrawlAdapter(api_key="offline-placeholder", http_fetcher=lambda *a, **k:
        _reader_response({"success": False, "error": error}))
    result = adapter.scrape_article("https://publisher.example/article")
    assert "private" not in json.dumps(result) and "secret-value" not in json.dumps(result)


@pytest.mark.parametrize("failure", [
    {"statusCode": 429}, {"error": {"status_code": 403}}, {"error": "ROBOTS_BLOCKED"},
    {"error": "Rate limit exceeded"},
])
def test_embedded_provider_denial_or_429_stops_all_alternate_readers(monkeypatch, failure):
    monkeypatch.setattr(firecrawl, "is_safe_url", lambda _url: (True, "safe"))
    monkeypatch.setattr(jina, "is_safe_url", lambda _url: (True, "safe"))
    monkeypatch.setattr(jina, "read_article_via_jina", lambda *a, **k: pytest.fail("Denial bypass"))
    adapter = firecrawl.FirecrawlAdapter(api_key="offline-placeholder", http_fetcher=lambda *a, **k:
        _reader_response({"success": False, **failure}))
    result = jina.execute_web_read("https://publisher.example/article", firecrawl_adapter=adapter)
    assert result["failure_kind"] in {"ACCESS_DENIED", "RATE_LIMITED"}


@pytest.mark.parametrize("status", [404, 500, 503])
def test_failed_publisher_status_cannot_become_acquired_content(monkeypatch, status):
    monkeypatch.setattr(firecrawl, "is_safe_url", lambda _url: (True, "safe"))
    adapter = firecrawl.FirecrawlAdapter(api_key="offline-placeholder", http_fetcher=lambda *a, **k:
        _reader_response({"success": True, "data": {"markdown": "Not a usable article " * 40,
                                                    "metadata": {"statusCode": status}}}))
    result = adapter.scrape_article("https://publisher.example/article")
    assert result["status"] == "failed" and not result.get("content")
    assert result["transport"]["http_status"] == status


def test_native_exception_error_and_logs_do_not_echo_credentials(monkeypatch, caplog):
    monkeypatch.setattr(jina, "is_safe_url", lambda _url: (True, "safe"))
    def fail(_url):
        raise ProviderHTTPError("Authorization: Bearer secret-value", endpoint="https://user:pass@provider.example",
                                status_code=403)
    result = jina.execute_web_read("https://publisher.example/article", executor=SimpleNamespace(execute_web_read=fail))
    assert "secret-value" not in json.dumps(result) + caplog.text
    assert "user:pass" not in json.dumps(result) + caplog.text


def test_bad_optional_transport_metadata_cannot_hide_explicit_denial(monkeypatch):
    monkeypatch.setattr(jina, "is_safe_url", lambda _url: (True, "safe"))
    monkeypatch.setattr(jina, "read_article_via_jina", lambda *a, **k: pytest.fail("Denial bypass"))
    executor = SimpleNamespace(execute_web_read=lambda _url: {
        "status": "failed", "failure_kind": "ACCESS_DENIED", "transport": "invalid metadata"})
    adapter = SimpleNamespace(is_configured=lambda: True,
                              scrape_article=lambda *a, **k: pytest.fail("Denial bypass"))
    assert jina.execute_web_read("https://publisher.example/article", executor=executor,
                                 firecrawl_adapter=adapter)["failure_kind"] == "ACCESS_DENIED"


@pytest.mark.parametrize("status", [401, 403, 429])
def test_reader_http200_upstream_denial_is_not_article(monkeypatch, status):
    monkeypatch.setattr(jina, "is_safe_url", lambda _url: (True, "safe"))
    text = f"Title: Publisher\nURL Source: https://publisher.example/article\nWarning: Target URL returned error {status}\n" + "retry later " * 40
    response = BoundedHTTPResponse(body=text.encode(), endpoint="https://r.jina.ai/article", status_code=200,
                                   content_type="text/plain", headers={}, latency_ms=1, attempts=1)
    monkeypatch.setattr(jina, "fetch_public_http", lambda *a, **k: response)
    result = jina.read_article_via_jina("https://publisher.example/article")
    assert result["status"] == "failed" and result["transport"]["http_status"] == status
