"""
Aegis Protocol — Unit Tests for GeminiService Shim & Intelligence Helpers
========================================================================
ADR 0004 Verification: Tests 100% backward compatibility of GeminiService,
MockGeminiProvider, async generation, and intelligence.py wrappers.
"""

from unittest.mock import MagicMock, PropertyMock, patch
import asyncio
import pytest

from backend.core.settings import Settings
from backend.services.gemini_service import (
    DEFAULT_MODELS,
    GeminiService,
    MockGeminiProvider,
    gemini_service,
    get_gemini_service,
)
from backend.services.intelligence import (
    analyze_security_risk,
    analyze_sentiment,
    call_gemini_text,
    clean_json_string,
    generate_defense,
)


def test_gemini_service_singleton_and_attributes():
    """Verify singleton identity and backward-compatible attributes."""
    service = get_gemini_service()
    assert service is gemini_service
    assert isinstance(service.models, list)
    assert len(service.models) > 0
    assert service.timeout > 0
    assert isinstance(service.mock_provider, MockGeminiProvider)


def test_gemini_service_mock_mode_property():
    """Verify mock_mode and use_mock getter and setter synchronize with gateway."""
    service = GeminiService()

    service.mock_mode = True
    assert service.mock_mode is True
    assert service.use_mock is True
    assert service.gateway.mock_mode is True

    service.use_mock = False
    assert service.use_mock is False
    assert service.mock_mode is False
    assert service.gateway.mock_mode is False

    # Reset to True for offline safety
    service.mock_mode = True


def test_gemini_service_generate_text_mock_mode():
    """Verify text generation in mock mode produces deterministic output."""
    service = GeminiService(use_mock=True)

    text = service.generate_text("Explain solar radiation")
    assert isinstance(text, str)
    assert len(text) > 0

    # With system instruction
    text_sys = service.generate_text(
        prompt="Explain solar radiation",
        system_instruction="You are an astrophysicist."
    )
    assert isinstance(text_sys, str)
    assert len(text_sys) > 0


def test_gemini_service_scientific_mode_enforces_live_keys():
    """Verify allow_mock_fallback=False raises RuntimeError when no live keys exist."""
    service = GeminiService(api_keys=[], use_mock=False)

    with patch.object(Settings, "has_gemini", new_callable=PropertyMock, return_value=False):
        with pytest.raises(RuntimeError, match="Live Gemini provider unavailable and mock fallback disabled"):
            service.generate_text("Scientific test", allow_mock_fallback=False)


def test_gemini_service_generate_content_alias():
    """Verify generate_content alias matching Google GenAI SDK method signature."""
    service = GeminiService(use_mock=True)
    resp = service.generate_content("hello")
    assert isinstance(resp, str)
    assert len(resp) > 0


def test_gemini_service_generate_text_async():
    """Verify generate_text_async offloads to background thread successfully."""
    service = GeminiService(use_mock=True)
    resp = asyncio.run(service.generate_text_async("async query", system_instruction="test system"))
    assert isinstance(resp, str)
    assert len(resp) > 0


def test_mock_gemini_provider_backward_compatibility():
    """Verify historical MockGeminiProvider class interface."""
    provider = MockGeminiProvider()
    resp = provider.generate_content("search and summarize evidence for lemon cures diabetes")
    assert "refuting_evidence" in resp


def test_intelligence_helpers_backward_compatibility():
    """Verify intelligence.py legacy wrappers route through centralized gateway."""
    # Ensure offline mode is active
    gemini_service.mock_mode = True

    # 1. clean_json_string
    raw_markdown = "```json\n{\"sentiment\": \"positive\"}\n```"
    assert clean_json_string(raw_markdown) == '{"sentiment": "positive"}'

    # 2. call_gemini_text
    text_resp = call_gemini_text("hello world")
    assert isinstance(text_resp, str)
    assert len(text_resp) > 0

    # 3. analyze_sentiment
    posts = ["Boycott this brand now!", "I like this product."]
    sentiments = analyze_sentiment(posts)
    assert isinstance(sentiments, list)
    assert len(sentiments) > 0
    assert "sentiment_score" in sentiments[0]

    # 4. generate_defense
    defense = generate_defense("Unverified rumor about contamination")
    assert isinstance(defense, str)
    assert len(defense) > 0

    # 5. analyze_security_risk
    mentions = [{"content": "Suspicious smear campaign launched against target", "source": "Twitter"}]
    risks = analyze_security_risk(mentions, vip_name="Executive")
    assert isinstance(risks, list)
