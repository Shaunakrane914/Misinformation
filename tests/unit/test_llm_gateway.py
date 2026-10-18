"""
Aegis Protocol — Unit Tests for Centralized LLM Gateway & Providers
===================================================================
ADR 0004 Verification: Tests LLMGateway, GeminiProvider, MockLLMProvider,
and clean_json_markdown parsing utilities.
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch
import pytest
from pydantic import BaseModel

from backend.core.settings import Settings
from backend.infrastructure.llm.gateway import (
    DefaultLLMGateway,
    clean_json_markdown,
    get_llm_gateway,
    llm_gateway,
)
from backend.infrastructure.llm.protocol import LLMGateway, LLMProvider, LLMResponse, LLMUsage
from backend.infrastructure.llm.providers.gemini import GeminiProvider
from backend.infrastructure.llm.advisory_policy import MODEL, advisory_run, investigation_scope, AdvisoryPolicyError


@pytest.fixture(autouse=True)
def offline_advisory_authorization(tmp_path):
    # All transport is blocked by conftest; these are explicit offline doubles.
    with advisory_run(verified_models=[MODEL], database=tmp_path / "advisory.db"), investigation_scope():
        yield


def advisory(provider, prompt, **kwargs):
    return provider.generate(prompt, **{"model": MODEL, "purpose": "search_suggestion", **kwargs})
from backend.infrastructure.llm.providers.mock import MockLLMProvider


class SampleVerdictSchema(BaseModel):
    verdict: str
    confidence: float
    severity: str
    reasoning: str


def test_clean_json_markdown_variations():
    """Verify markdown code block wrappers are stripped properly."""
    raw_1 = "```json\n{\"key\": \"val\"}\n```"
    assert clean_json_markdown(raw_1) == '{"key": "val"}'

    raw_2 = "```JSON\n{\"key\": \"val\"}\n```"
    assert clean_json_markdown(raw_2) == '{"key": "val"}'

    raw_3 = "```\n{\"key\": \"val\"}\n```"
    assert clean_json_markdown(raw_3) == '{"key": "val"}'

    raw_4 = "  {\"key\": \"val\"}  "
    assert clean_json_markdown(raw_4) == '{"key": "val"}'


def test_gateway_initialization_and_mock_mode_toggle(monkeypatch):
    """Verify DefaultLLMGateway initialization, mock_mode toggle, and provider resolution."""
    # 1. Under test session, mock_mode defaults to True for safety
    gateway = DefaultLLMGateway()
    assert gateway.mock_mode is True
    assert isinstance(gateway.active_provider, MockLLMProvider)

    # 2. Manual override to False enables GeminiProvider
    settings = Settings(
        environment="production",
        aegis_mock_llm=False,
        gemini_api_keys=["AIzaSyFakeKey123"],
        gemini_models=["gemini-2.5-flash"],
    )
    prod_gateway = DefaultLLMGateway(settings_instance=settings)
    prod_gateway.mock_mode = False
    assert prod_gateway.mock_mode is False
    assert isinstance(prod_gateway.active_provider, GeminiProvider)

    # 3. In production environment without test flags, defaults to False
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    non_test_gateway = DefaultLLMGateway(settings_instance=settings)
    assert non_test_gateway.mock_mode is False
    assert isinstance(non_test_gateway.active_provider, GeminiProvider)


def test_gateway_singleton_identity():
    """Verify get_llm_gateway() returns authoritative singleton."""
    gw1 = get_llm_gateway()
    gw2 = get_llm_gateway()
    assert gw1 is gw2
    assert gw1 is llm_gateway
    assert isinstance(llm_gateway, LLMGateway)


def test_production_runtime_mock_override_and_fallback_are_forbidden():
    production = Settings(environment="production", aegis_mock_llm=False, gemini_api_keys=[])
    gateway = DefaultLLMGateway(settings_instance=production)
    with pytest.raises(ValueError, match="forbidden in production"):
        gateway.mock_mode = True
    with pytest.raises(ValueError, match="forbidden in production"):
        gateway.generate_text("production request", allow_mock=True)
    with pytest.raises(RuntimeError, match="unavailable"):
        gateway.generate_text("production request")


def test_gateway_generate_text_with_mock_provider():
    """Verify text generation through mock provider."""
    gateway = DefaultLLMGateway()
    gateway.mock_mode = True

    resp = gateway.generate_text("Explain quantum computing")
    assert isinstance(resp, str)
    assert len(resp) > 0


def test_gateway_generate_structured_pydantic():
    """Verify generate_structured parses into validated Pydantic model."""
    gateway = DefaultLLMGateway()
    gateway.mock_mode = True

    prompt = (
        "Determine the verdict.\n"
        "GATHERED SUPPORTING EVIDENCE:\n"
        '{"claim_supported": true, "text": "NASA confirms Earth orbits the Sun."}\n'
        "GATHERED REFUTING EVIDENCE:\n"
        "EVIDENCE RETRIEVAL CONFIDENCE SCORE: 0.95"
    )

    result = gateway.generate_structured(prompt, schema=SampleVerdictSchema)
    assert isinstance(result, SampleVerdictSchema)
    assert result.verdict == "True"
    assert result.confidence >= 0.8
    assert result.severity == "Low"


def test_gateway_generate_structured_dict_and_invalid_json():
    """Verify generate_structured with raw dict and invalid JSON handling."""
    gateway = DefaultLLMGateway()
    gateway.mock_mode = True

    prompt = "search and summarize evidence for lemon cures diabetes"
    data = gateway.generate_structured(prompt, schema=dict)
    assert isinstance(data, dict)
    assert "refuting_evidence" in data

    # Test invalid JSON handling
    mock_bad_provider = MagicMock(spec=LLMProvider)
    mock_bad_provider.generate.return_value = LLMResponse(
        content="THIS IS NOT JSON AT ALL",
        model="mock",
        provider="mock"
    )

    bad_gateway = DefaultLLMGateway(mock_provider=mock_bad_provider)
    bad_gateway.mock_mode = True

    with pytest.raises(ValueError, match="LLM returned invalid JSON"):
        bad_gateway.generate_structured("bad prompt", schema=dict)


@pytest.mark.parametrize(
    ("schema", "payload"),
    [(dict, '[1, 2]'), (list, '{"item": 1}')],
)
def test_gateway_rejects_wrong_builtin_container(schema, payload):
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.generate.return_value = LLMResponse(
        content=payload, model="test", provider="test"
    )
    gateway = DefaultLLMGateway(mock_provider=provider)
    gateway.mock_mode = True

    with pytest.raises(ValueError, match="does not match requested schema"):
        gateway.generate_structured("prompt", schema=schema)


def test_gateway_rejects_missing_pydantic_fields():
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.generate.return_value = LLMResponse(
        content='{"verdict": "False"}', model="test", provider="test"
    )
    gateway = DefaultLLMGateway(gemini_provider=provider)
    gateway.mock_mode = False

    with pytest.raises(Exception):
        gateway.generate_structured("prompt", schema=SampleVerdictSchema)


def test_mock_llm_provider_scenarios():
    """Verify deterministic mock response branches for all agent domain queries."""
    provider = MockLLMProvider()

    # Evidence: refuting
    resp_lemon = provider.generate("search and summarize evidence for lemon cures diabetes")
    data_lemon = json.loads(resp_lemon.content)
    assert resp_lemon.synthetic is True
    assert resp_lemon.metadata["evidence_eligible"] is False
    assert data_lemon["_aegis_provenance"]["synthetic"] is True
    assert len(data_lemon["refuting_evidence"]) > 0
    assert data_lemon["overall_evidence_confidence"] < 0.2

    # Evidence: supporting
    resp_nasa = provider.generate("search and summarize evidence for NASA Europa water")
    data_nasa = json.loads(resp_nasa.content)
    assert len(data_nasa["supporting_evidence"]) > 0
    assert data_nasa["overall_evidence_confidence"] > 0.8

    # Sentiment / Crisis
    resp_sent = provider.generate("Act as a crisis intelligence analyst: analyze_sentiment")
    data_sent = json.loads(resp_sent.content)
    assert isinstance(data_sent, list)
    assert data_sent[0]["is_threat"] is True

    # Corporate PR Defense
    resp_defense = provider.generate("corporate defense statement for crisis")
    assert resp_defense.content.startswith("[SYNTHETIC MOCK OUTPUT — NOT EVIDENCE]")

    # Threat detection
    resp_threat = provider.generate("threat detection is_threat")
    data_threat = json.loads(resp_threat.content)
    assert data_threat["threat_detected"] is True

    # Usage and latency
    assert resp_lemon.usage.prompt_tokens > 0
    assert resp_lemon.usage.completion_tokens > 0
    assert resp_lemon.latency_ms >= 0.0


def test_gemini_provider_availability_and_key_filtering():
    """Empty credentials are unavailable; opaque credentials need upstream validation."""
    settings_no_keys = Settings(gemini_api_keys=["", "  "])
    provider_no_keys = GeminiProvider(settings_instance=settings_no_keys)
    assert provider_no_keys.is_available() is False

    with pytest.raises(RuntimeError, match="GeminiProvider unavailable"):
        provider_no_keys.generate("test prompt")

    settings_with_keys = Settings(gemini_api_keys=["AIzaSyFixtureKey1", "opaque-authorization-fixture"])
    provider_with_keys = GeminiProvider(settings_instance=settings_with_keys)
    assert provider_with_keys.is_available() is True
    assert len(provider_with_keys.api_keys) == 2


@patch("requests.post")
def test_opaque_gemini_credential_is_header_only_and_upstream_rejection_fails_closed(mock_post):
    mock_post.return_value = MagicMock(status_code=401)
    settings = Settings(environment="production", aegis_mock_llm=False,
                        gemini_api_keys=["opaque-authorization-fixture"],
                        default_model="fixture", gemini_models=["fixture"], llm_max_retries=1)
    assert settings.has_gemini
    with pytest.raises(RuntimeError, match="HTTP 401") as failure:
        advisory(GeminiProvider(settings), "Minimal suggestion")
    assert "opaque-authorization-fixture" not in str(failure.value)
    assert "params" not in mock_post.call_args.kwargs
    assert mock_post.call_args.kwargs["headers"]["x-goog-api-key"] == "opaque-authorization-fixture"


@patch("time.sleep", return_value=None)
@patch("requests.post")
def test_gemini_provider_never_uses_configured_model_fallback(mock_post, _mock_sleep):
    failed = MagicMock(status_code=404)
    succeeded = MagicMock(status_code=200)
    succeeded.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "fallback success"}]}}]
    }
    mock_post.side_effect = [failed, succeeded]
    settings = Settings(
        environment="production",
        aegis_mock_llm=False,
        gemini_api_keys=["AIzaSyFallbackKey"],
        default_model="gemini-primary",
        gemini_models=["gemini-fallback", "gemini-primary"],
        llm_max_retries=1,
    )

    with pytest.raises(RuntimeError, match="HTTP 404"):
        advisory(GeminiProvider(settings), "prompt")

    attempted_urls = [call.args[0] for call in mock_post.call_args_list]
    assert attempted_urls == [
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",
    ]
    assert mock_post.call_count == 1


@patch("time.sleep", return_value=None)
@patch("requests.post")
def test_gemini_provider_explicit_model_is_strict(mock_post, _mock_sleep):
    mock_post.return_value = MagicMock(status_code=404)
    settings = Settings(
        environment="production",
        aegis_mock_llm=False,
        gemini_api_keys=["AIzaSyStrictKey"],
        default_model="gemini-primary",
        gemini_models=["gemini-primary", "gemini-fallback"],
        llm_max_retries=1,
    )

    with pytest.raises(AdvisoryPolicyError):
        GeminiProvider(settings).generate("prompt", model="gemini-strict")

    assert mock_post.call_count == 0


def test_gateway_scientific_call_blocks_configured_mock():
    settings = Settings(environment="test", aegis_mock_llm=True, gemini_api_keys=[])
    gateway = DefaultLLMGateway(settings_instance=settings)

    with pytest.raises(RuntimeError, match="Live Gemini provider unavailable"):
        gateway.generate_text("scientific verdict", allow_mock=False)


def test_gateway_scientific_call_bypasses_mock_mode_when_live_is_available():
    live_provider = MagicMock(spec=LLMProvider)
    live_provider.is_available.return_value = True
    live_provider.generate.return_value = LLMResponse(
        content="live result", model="gemini-live", provider="gemini"
    )
    gateway = DefaultLLMGateway(
        settings_instance=Settings(environment="test", aegis_mock_llm=True),
        gemini_provider=live_provider,
    )

    with pytest.raises(AdvisoryPolicyError):
        gateway.generate_text("scientific verdict", allow_mock=False)
    live_provider.generate.assert_not_called()


def test_gateway_last_response_is_isolated_between_concurrent_calls():
    barrier = threading.Barrier(2)

    class EchoProvider:
        def is_available(self):
            return True

        def generate(self, prompt, model=None, **kwargs):
            return LLMResponse(content=prompt, model="echo", provider="echo")

    gateway = DefaultLLMGateway(
        settings_instance=Settings(environment="test", aegis_mock_llm=True),
        mock_provider=EchoProvider(),
    )

    def execute(label):
        gateway.generate_text(label, allow_mock=True)
        barrier.wait(timeout=2)
        return gateway.last_response.content

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, ["first", "second"]))

    assert results == ["first", "second"]


@patch("requests.post")
def test_gemini_provider_success_flow(mock_post):
    """Verify successful Gemini inference execution and usage calculation."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Gemini generated verification analysis"}]
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    settings = Settings(gemini_api_keys=["AIzaSyKeySuccess1"])
    provider = GeminiProvider(settings_instance=settings)

    resp = advisory(provider, "Suggest a passage")
    assert resp.content == "Gemini generated verification analysis"
    assert resp.provider == "gemini"
    assert resp.model == MODEL
    assert resp.usage.total_tokens > 0
    assert resp.usage.is_estimated is True
    assert mock_post.called


@patch("requests.post")
def test_gemini_provider_prefers_provider_reported_usage(mock_post):
    response = MagicMock(status_code=200)
    response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "answer"}]}}],
        "usageMetadata": {
            "promptTokenCount": 11,
            "candidatesTokenCount": 7,
            "totalTokenCount": 18,
        },
    }
    mock_post.return_value = response
    provider = GeminiProvider(Settings(gemini_api_keys=["AIzaSyUsageKey"]))

    result = advisory(provider, "prompt")

    assert result.usage.total_tokens == 18
    assert result.usage.is_estimated is False
    assert result.metadata["usage_source"] == "provider"


@patch("time.sleep", return_value=None)
@patch("requests.post")
def test_gemini_provider_malformed_response_and_errors_do_not_leak_secrets(
    mock_post, _mock_sleep, caplog
):
    malformed = MagicMock(status_code=200)
    malformed.json.return_value = {
        "unexpected": "sensitive provider payload must not be logged"
    }
    mock_post.return_value = malformed
    secret_key = "AIzaSy_SUPER_SECRET_VALUE"
    provider = GeminiProvider(Settings(
        environment="production",
        aegis_mock_llm=False,
        gemini_api_keys=[secret_key],
        gemini_models=["gemini-test"],
        default_model="gemini-test",
        llm_max_retries=1,
    ))

    with pytest.raises(ValueError, match="Unexpected response") as exc_info:
        advisory(provider, "sensitive prompt")

    combined = str(exc_info.value) + caplog.text
    assert secret_key not in combined
    assert "sensitive prompt" not in combined
    assert "sensitive provider payload" not in combined


@patch("time.sleep", return_value=None)
@patch("requests.post")
def test_gemini_provider_rate_limit_stops_immediate_retry(mock_post, mock_sleep):
    """Cost policy: a 429 starts cooldown, not a retry/model/key waterfall."""
    resp_429 = MagicMock()
    resp_429.status_code = 429

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Recovered after backoff"}]}}]
    }

    mock_post.side_effect = [resp_429, resp_200]

    settings = Settings(gemini_api_keys=["AIzaSyKeyRetry1"], llm_max_retries=3)
    provider = GeminiProvider(settings_instance=settings)

    from backend.infrastructure.llm.providers.rate_limit import GeminiRateLimitError
    with pytest.raises(GeminiRateLimitError):
        advisory(provider, "test prompt")
    assert mock_post.call_count == 1
    assert not mock_sleep.called
