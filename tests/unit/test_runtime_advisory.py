"""Offline runtime admission, capability lookup and persisted advisory controls."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import sqlite3
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from backend.infrastructure.llm import advisory_policy as policy
from backend.infrastructure.llm import runtime_advisory as runtime
from backend.infrastructure.llm.providers.gemini import GeminiProvider


class MetadataResponse:
    def __init__(self, status=200, body=None, headers=None, chunks=None):
        self.status_code = status
        self.headers = headers or {}
        self.body = body if body is not None else json.dumps({
            "name": "models/" + policy.MODEL,
            "supportedGenerationMethods": ["generateContent"],
        }).encode()
        self.chunks = chunks
        self.chunks_read = 0
        self.closed = False

    def iter_content(self, chunk_size):
        assert 0 < chunk_size <= runtime.MAX_METADATA_BYTES
        for chunk in self.chunks if self.chunks is not None else [self.body]:
            self.chunks_read += 1
            yield chunk

    def json(self):
        raise AssertionError("Metadata must be bounded before JSON parsing")

    def close(self):
        self.closed = True


@pytest.fixture
def transport(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("No real HTTP permitted by runtime advisory tests")
    monkeypatch.setattr(requests.Session, "request", forbidden)
    monkeypatch.setenv("AEGIS_LIVE_ADVISORY_ENABLED", "true")
    monkeypatch.setenv("AEGIS_AI_POLICY_DB", str(tmp_path / "policy.sqlite3"))
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AEGIS_ENV", "production")
    monkeypatch.setenv("AEGIS_MOCK_LLM", "false")
    get = Mock(return_value=MetadataResponse())
    post = Mock(return_value=SimpleNamespace(status_code=200, json=lambda: {
        "candidates": [{"content": {"parts": [{"text": '{"actions": []}'}]}}],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15},
    }))
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(requests, "post", post)
    with runtime._MODEL_CACHE_LOCK:
        runtime._MODEL_CACHE.clear()
    yield SimpleNamespace(get=get, post=post, database=tmp_path / "policy.sqlite3")
    with runtime._MODEL_CACHE_LOCK:
        runtime._MODEL_CACHE.clear()


@pytest.fixture
def settings():
    return SimpleNamespace(environment="production", aegis_mock_llm=False,
                           llm_advisory_model=policy.MODEL,
                           gemini_api_keys=["fixture-first", "fixture-second"])


def generate(settings, **kwargs):
    return GeminiProvider(settings).generate("Suggest one public search query", **{
        "model": policy.MODEL, "purpose": "search_suggestion", "max_output_tokens": 32, **kwargs,
    })


def test_disabled_default_does_not_load_settings_or_contact_provider(transport, monkeypatch):
    import sys
    monkeypatch.delenv("AEGIS_LIVE_ADVISORY_ENABLED")
    forbidden = Mock(side_effect=AssertionError("Disabled runtime must not inspect credentials"))
    monkeypatch.setattr(sys.modules["backend.core.settings"], "get_settings", forbidden)
    with runtime.runtime_advisory_scope() as summary:
        assert summary["status"] == "DISABLED"
        assert policy._run.get() is None
    forbidden.assert_not_called()
    transport.get.assert_not_called()
    transport.post.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"environment": "test"}, {"aegis_mock_llm": True}, {"is_mock_llm": True},
    {"is_test_environment": True}, {"llm_advisory_model": "gemini-2.5-flash-lite"},
    {"gemini_api_keys": []}, {"gemini_api_keys": ["", "   "]},
])
def test_mock_test_wrong_model_and_no_key_never_lookup_metadata(transport, settings, changes):
    for name, value in changes.items():
        setattr(settings, name, value)
    with runtime.runtime_advisory_scope(settings) as summary:
        assert summary["status"] == "DISABLED"
        assert policy._run.get() is None
    transport.get.assert_not_called()
    transport.post.assert_not_called()


def test_exact_model_lookup_uses_only_first_key_and_bounded_transport(transport, settings):
    with runtime.runtime_advisory_scope(settings) as summary:
        assert summary["status"] == "ENABLED"
        assert policy._run.get()["id"] == "runtime-utc-" + datetime.now(timezone.utc).date().isoformat()
        assert policy.call_count() == 0
        assert "fixture-first" not in json.dumps(summary)
        assert "fixture-second" not in json.dumps(summary)
    args, kwargs = transport.get.call_args
    assert args == ("https://generativelanguage.googleapis.com/v1beta/models/" + policy.MODEL,)
    assert kwargs == {"headers": {"x-goog-api-key": "fixture-first"}, "timeout": 2.0,
                      "allow_redirects": False, "stream": True}
    assert transport.get.return_value.closed
    assert "fixture-first" not in repr(runtime._MODEL_CACHE)
    assert "fixture-second" not in repr(runtime._MODEL_CACHE)
    transport.post.assert_not_called()


@pytest.mark.parametrize("available,ttl", [(True, 300), (False, 30)])
def test_capability_cache_reuses_lookup_until_bounded_ttl(transport, settings, monkeypatch, available, ttl):
    clock = [100.0]
    monkeypatch.setattr(runtime.time, "monotonic", lambda: clock[0])
    if not available:
        transport.get.return_value = MetadataResponse(status=401)
    expected = "ENABLED" if available else "UNAVAILABLE"
    for instant in [100.0, 100.0 + ttl - .1]:
        clock[0] = instant
        with runtime.runtime_advisory_scope(settings) as summary:
            assert summary["status"] == expected
    assert transport.get.call_count == 1
    clock[0] = 100.0 + ttl + .1
    with runtime.runtime_advisory_scope(settings) as summary:
        assert summary["status"] == expected
    assert transport.get.call_count == 2
    assert all(call.kwargs["headers"]["x-goog-api-key"] == "fixture-first"
               for call in transport.get.call_args_list)
    transport.post.assert_not_called()


@pytest.mark.parametrize("response", [
    MetadataResponse(status=302, headers={"Location": "https://other.invalid/model"}),
    MetadataResponse(body=b"malformed provider response fixture-private"),
    MetadataResponse(body=b"[]"),
    MetadataResponse(body=json.dumps({"name": "models/other", "supportedGenerationMethods": ["generateContent"]}).encode()),
    MetadataResponse(body=json.dumps({"name": "models/" + policy.MODEL, "supportedGenerationMethods": []}).encode()),
    MetadataResponse(headers={"Content-Length": "100001"}),
    MetadataResponse(chunks=[b"x" * 60_000, b"x" * 40_001, b"must-not-read"]),
])
def test_redirect_oversize_and_malformed_capabilities_fail_closed(transport, settings, response):
    transport.get.return_value = response
    with runtime.runtime_advisory_scope(settings) as summary:
        assert summary["status"] == "UNAVAILABLE"
        assert policy._run.get() is None
        assert "fixture-private" not in json.dumps(summary)
    assert response.closed
    if response.chunks is not None:
        assert response.chunks_read == 2
    assert transport.get.call_count == 1
    transport.post.assert_not_called()


def test_explicit_run_is_reused_without_lookup_or_budget_reset(transport, settings, monkeypatch):
    monkeypatch.setenv("AEGIS_LIVE_ADVISORY_ENABLED", "false")
    with policy.advisory_run(verified_models=[policy.MODEL], database=transport.database) as existing:
        with policy.investigation_scope("explicit"), runtime.runtime_advisory_scope(settings) as summary:
            assert summary["status"] == "REUSED_EXPLICIT_RUN"
            assert policy._run.get() is existing
            generate(settings)
        with runtime.runtime_advisory_scope(settings) as summary:
            assert summary["status"] == "REUSED_EXPLICIT_RUN"
            assert policy._run.get() is existing
            assert policy.call_count() == 1
    transport.get.assert_not_called()
    assert transport.post.call_count == 1


@pytest.mark.parametrize("worker", [False, True])
def test_three_daily_calls_persist_across_runtime_contexts_and_workers(transport, settings, worker):
    identities = []
    def attempt(index):
        with runtime.runtime_advisory_scope(settings) as summary:
            assert summary["status"] == "ENABLED"
            identities.append(policy._run.get()["id"])
            with policy.investigation_scope("case-" + str(index)):
                generate(settings)
                with pytest.raises(policy.AdvisoryPolicyError):
                    generate(settings)
            return policy.call_count()
    with ThreadPoolExecutor(max_workers=2) as executor:
        for index in range(3):
            calls = executor.submit(attempt, index).result() if worker else attempt(index)
            assert calls == index + 1
    assert len(set(identities)) == 1
    # Simulate a worker with no process capability cache: exhausted budget wins first.
    with runtime._MODEL_CACHE_LOCK:
        runtime._MODEL_CACHE.clear()
    with runtime.runtime_advisory_scope(settings) as summary:
        assert summary["status"] == "BUDGET_BLOCKED"
        assert policy._run.get() is None
    with sqlite3.connect(transport.database) as connection:
        assert connection.execute("SELECT id,calls FROM runs").fetchall() == [(identities[0], 3)]
    assert transport.get.call_count == 1
    assert transport.post.call_count == 3
    assert all(call.kwargs["headers"]["x-goog-api-key"] == "fixture-first"
               for call in transport.post.call_args_list)


def test_same_investigation_budget_blocks_before_another_metadata_lookup(transport, settings):
    with policy.investigation_scope("same-investigation"):
        with runtime.runtime_advisory_scope(settings) as summary:
            assert summary["status"] == "ENABLED"
            generate(settings)
        with runtime._MODEL_CACHE_LOCK:
            runtime._MODEL_CACHE.clear()
        with runtime.runtime_advisory_scope(settings) as summary:
            assert summary["status"] == "BUDGET_BLOCKED"
    assert transport.get.call_count == transport.post.call_count == 1


@pytest.mark.parametrize("restriction", ["cooldown", "busy"])
def test_shared_cooldown_or_busy_provider_blocks_before_metadata(transport, settings, restriction):
    with policy.advisory_run(verified_models=[policy.MODEL], database=transport.database):
        if restriction == "cooldown":
            policy.set_cooldown(3600)
    if restriction == "busy":
        with sqlite3.connect(transport.database) as connection:
            connection.execute("UPDATE provider SET busy='fixture-inflight' WHERE id=1")
    with runtime.runtime_advisory_scope(settings) as summary:
        assert summary["status"] == "BUDGET_BLOCKED"
        assert policy._run.get() is None
    transport.get.assert_not_called()
    transport.post.assert_not_called()


def test_runtime_does_not_authorize_general_generation_or_expired_day(transport, settings):
    with runtime.runtime_advisory_scope(settings) as summary, policy.investigation_scope("native-work"):
        assert summary["status"] == "ENABLED"
        with pytest.raises(policy.AdvisoryPolicyError):
            generate(settings, purpose=None)
        policy._run.get()["expires_at"] = time.time() - 1
        with pytest.raises(policy.AdvisoryPolicyError):
            generate(settings)
        assert policy.call_count() == 0
    transport.post.assert_not_called()
