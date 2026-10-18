"""No network: exact accounting, cooldown and non-advisory denial controls."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from backend.infrastructure.llm.advisory_policy import (
    MODEL, AdvisoryPolicyError, advisory_run, investigation_scope, call_count,
)
from backend.infrastructure.llm.providers.gemini import GeminiProvider
from backend.core.settings import Settings


def provider():
    return GeminiProvider(Settings(gemini_api_keys=["fixture-one", "fixture-two"]))


def advice(instance):
    return instance.generate("Suggest one query", model=MODEL, purpose="search_suggestion", max_output_tokens=160)


@pytest.fixture
def transport(monkeypatch):
    post = Mock(return_value=SimpleNamespace(status_code=200, json=lambda: {
        "candidates": [{"content": {"parts": [{"text": '{"actions": []}'}]}}],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15}}))
    monkeypatch.setattr("requests.post", post)
    return post


def test_default_and_non_advisory_calls_never_reach_transport(transport, tmp_path):
    with pytest.raises(AdvisoryPolicyError):
        advice(provider())
    with advisory_run(verified_models=[MODEL], database=tmp_path / "policy.db"), investigation_scope():
        with pytest.raises(AdvisoryPolicyError):
            provider().generate("Certify this claim", model=MODEL)
    transport.assert_not_called()


def test_one_per_investigation_three_per_run_across_instances(transport, tmp_path):
    with advisory_run(verified_models=[MODEL], database=tmp_path / "policy.db"):
        for _ in range(3):
            with investigation_scope():
                result = advice(provider())
                assert result.usage.total_tokens == 15
                with pytest.raises(AdvisoryPolicyError):
                    advice(provider())
        with investigation_scope(), pytest.raises(AdvisoryPolicyError):
            advice(provider())
        assert call_count() == 3
    assert transport.call_count == 3
    assert all(call.kwargs["headers"]["x-goog-api-key"] == "fixture-one" for call in transport.call_args_list)


def test_429_cooldown_shared_by_instances_and_new_runs(transport, tmp_path):
    transport.return_value = SimpleNamespace(status_code=429, headers={}, json=lambda: {"error": {"details": [
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "3600s"}]}})
    path = tmp_path / "policy.db"
    with advisory_run(verified_models=[MODEL], database=path):
        with investigation_scope(), pytest.raises(RuntimeError):
            advice(provider())
        with investigation_scope(), pytest.raises(AdvisoryPolicyError):
            advice(provider())
    with advisory_run(verified_models=[MODEL], database=path), investigation_scope(), pytest.raises(AdvisoryPolicyError):
        advice(provider())
    assert transport.call_count == 1


def test_timeout_is_counted_and_not_retried(transport, tmp_path):
    transport.side_effect = TimeoutError("uncertain whether provider processed it")
    with advisory_run(verified_models=[MODEL], database=tmp_path / "policy.db"), investigation_scope():
        with pytest.raises(RuntimeError):
            advice(provider())
        assert call_count() == 1
        with pytest.raises(AdvisoryPolicyError):
            advice(provider())
    assert transport.call_count == 1


def test_no_concurrent_or_nested_budget_reset(transport, tmp_path):
    def nested(*args, **kwargs):
        with advisory_run(verified_models=[MODEL]), investigation_scope("second"):
            with pytest.raises(AdvisoryPolicyError):
                advice(provider())
        return SimpleNamespace(status_code=200, json=lambda: {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})
    transport.side_effect = nested
    with advisory_run(verified_models=[MODEL], database=tmp_path / "policy.db"), investigation_scope():
        advice(provider())
        assert call_count() == 1
    assert transport.call_count == 1


def test_verified_model_and_bounded_payload_required(transport, tmp_path):
    with pytest.raises(AdvisoryPolicyError):
        with advisory_run(database=tmp_path / "policy.db"):
            pass
    with advisory_run(verified_models=[MODEL], database=tmp_path / "policy.db"), investigation_scope():
        for kwargs in ({"model": "other"}, {"max_output_tokens": 161}, {"max_attempts": 2}):
            options = {"model": MODEL, "purpose": "search_suggestion", **kwargs}
            with pytest.raises(AdvisoryPolicyError):
                provider().generate("Suggest", **options)
    transport.assert_not_called()
