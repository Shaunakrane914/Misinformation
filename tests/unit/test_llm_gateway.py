"""
Aegis Protocol — Unit Tests for Centralized LLM Gateway & Providers
===================================================================
ADR 0004 Verification: Tests LLMGateway, GeminiProvider, MockLLMProvider,
and clean_json_markdown parsing utilities.
"""

import json
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


def test_mock_llm_provider_scenarios():
    """Verify deterministic mock response branches for all agent domain queries."""
    provider = MockLLMProvider()

    # Evidence: refuting
    resp_lemon = provider.generate("search and summarize evidence for lemon cures diabetes")
    data_lemon = json.loads(resp_lemon.content)
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
    assert "Official Corporate Statement" in resp_defense.content

    # Threat detection
    resp_threat = provider.generate("threat detection is_threat")
    data_threat = json.loads(resp_threat.content)
    assert data_threat["threat_detected"] is True

    # Usage and latency
    assert resp_lemon.usage.prompt_tokens > 0
    assert resp_lemon.usage.completion_tokens > 0
    assert resp_lemon.latency_ms >= 0.0


def test_gemini_provider_availability_and_key_filtering():
    """Verify GeminiProvider filters only AIzaSy keys and reports availability correctly."""
    settings_no_keys = Settings(gemini_api_keys=["invalid_key_1", "invalid_key_2"])
    provider_no_keys = GeminiProvider(settings_instance=settings_no_keys)
    assert provider_no_keys.is_available() is False

    with pytest.raises(RuntimeError, match="GeminiProvider unavailable"):
        provider_no_keys.generate("test prompt")

    settings_with_keys = Settings(gemini_api_keys=["AIzaSyValidKey1", "AIzaSyValidKey2"])
    provider_with_keys = GeminiProvider(settings_instance=settings_with_keys)
    assert provider_with_keys.is_available() is True
    assert len(provider_with_keys.api_keys) == 2


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

    resp = provider.generate("verify this claim", model="gemini-2.5-flash")
    assert resp.content == "Gemini generated verification analysis"
    assert resp.provider == "gemini"
    assert resp.model == "gemini-2.5-flash"
    assert resp.usage.total_tokens > 0
    assert mock_post.called


@patch("time.sleep", return_value=None)
@patch("requests.post")
def test_gemini_provider_rate_limit_backoff_and_retry(mock_post, mock_sleep):
    """Verify HTTP 429 rate limit triggers exponential backoff and retries."""
    # First attempt: 429 rate limit; Second attempt: 200 success
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

    resp = provider.generate("test prompt", model="gemini-2.5-flash")
    assert resp.content == "Recovered after backoff"
    assert mock_post.call_count == 2
    assert mock_sleep.called
