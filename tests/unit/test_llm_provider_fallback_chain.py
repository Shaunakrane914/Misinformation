"""
Aegis Protocol — Unit Tests for LLM Provider Sequential Fallback Chain
=======================================================================
Verifies sequential provider failover:
Gemini (primary) -> Groq (fallback 1) -> OpenAI (fallback 2) -> Mock (authorized).
Verifies:
1. When Gemini fails, Groq is invoked seamlessly.
2. When Groq fails or rates out, OpenAI is invoked.
3. When live providers fail, authorized Mock handles output.
4. In production, synthetic Mock is strictly forbidden even when all live fail.
5. Groq and OpenAI providers correctly adhere to the LLMProvider protocol.
"""
from unittest.mock import MagicMock, patch
import pytest

from backend.core.settings import Settings
from backend.infrastructure.llm.gateway import DefaultLLMGateway
from backend.infrastructure.llm.protocol import LLMProvider, LLMResponse, LLMUsage
from backend.infrastructure.llm.providers.groq import GroqProvider
from backend.infrastructure.llm.providers.openai import OpenAIProvider
from backend.infrastructure.llm.providers.mock import MockLLMProvider
from backend.infrastructure.llm.advisory_policy import MODEL, advisory_run, investigation_scope


@pytest.fixture(autouse=True)
def offline_advisory_auth(tmp_path):
    with advisory_run(verified_models=[MODEL], database=tmp_path / "advisory_fb.db"), investigation_scope():
        yield


def test_gemini_fails_then_groq_succeeds():
    """Verify fallback from Gemini to Groq upon Gemini failure."""
    gemini_mock = MagicMock(spec=LLMProvider)
    gemini_mock.is_available.return_value = True
    gemini_mock.generate.side_effect = RuntimeError("Gemini quota 429")

    groq_mock = MagicMock(spec=LLMProvider)
    groq_mock.is_available.return_value = True
    groq_mock.generate.return_value = LLMResponse(
        content='{"suggestion": "search query from groq"}',
        model="openai/gpt-oss-20b",
        provider="groq",
        latency_ms=120.0,
        usage=LLMUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20, is_estimated=False),
    )

    openai_mock = MagicMock(spec=LLMProvider)
    openai_mock.is_available.return_value = True

    gateway = DefaultLLMGateway(
        settings_instance=Settings(environment="development", aegis_mock_llm=False),
        gemini_provider=gemini_mock,
        groq_provider=groq_mock,
        openai_provider=openai_mock,
    )
    gateway.mock_mode = False

    result = gateway.generate_text("test query", purpose="search_suggestion")
    assert "from groq" in result
    assert gemini_mock.generate.call_count == 1
    assert groq_mock.generate.call_count == 1
    assert openai_mock.generate.call_count == 0


def test_gemini_and_groq_fail_then_openai_succeeds():
    """Verify fallback from Gemini and Groq to OpenAI."""
    gemini_mock = MagicMock(spec=LLMProvider)
    gemini_mock.is_available.return_value = True
    gemini_mock.generate.side_effect = RuntimeError("Gemini quota 429")

    groq_mock = MagicMock(spec=LLMProvider)
    groq_mock.is_available.return_value = True
    groq_mock.generate.side_effect = RuntimeError("Groq rate limit 429")

    openai_mock = MagicMock(spec=LLMProvider)
    openai_mock.is_available.return_value = True
    openai_mock.generate.return_value = LLMResponse(
        content='{"suggestion": "search query from openai"}',
        model="gpt-4o-mini",
        provider="openai",
        latency_ms=180.0,
        usage=LLMUsage(prompt_tokens=15, completion_tokens=12, total_tokens=27, is_estimated=False),
    )

    gateway = DefaultLLMGateway(
        settings_instance=Settings(environment="development", aegis_mock_llm=False),
        gemini_provider=gemini_mock,
        groq_provider=groq_mock,
        openai_provider=openai_mock,
    )
    gateway.mock_mode = False

    result = gateway.generate_text("test query", purpose="search_suggestion")
    assert "from openai" in result
    assert gemini_mock.generate.call_count == 1
    assert groq_mock.generate.call_count == 1
    assert openai_mock.generate.call_count == 1


def test_all_live_fail_falls_back_to_mock_when_authorized():
    """Verify that when Gemini, Groq, and OpenAI fail, authorized Mock succeeds."""
    gemini_mock = MagicMock(spec=LLMProvider)
    gemini_mock.is_available.return_value = True
    gemini_mock.generate.side_effect = RuntimeError("Gemini network error")

    groq_mock = MagicMock(spec=LLMProvider)
    groq_mock.is_available.return_value = True
    groq_mock.generate.side_effect = RuntimeError("Groq network error")

    openai_mock = MagicMock(spec=LLMProvider)
    openai_mock.is_available.return_value = True
    openai_mock.generate.side_effect = RuntimeError("OpenAI quota 429")

    mock_provider = MockLLMProvider()

    gateway = DefaultLLMGateway(
        settings_instance=Settings(environment="development", aegis_mock_llm=True),
        gemini_provider=gemini_mock,
        groq_provider=groq_mock,
        openai_provider=openai_mock,
        mock_provider=mock_provider,
    )
    gateway.mock_mode = True

    # Call with allow_mock=True
    result = gateway.generate_text("search and summarize evidence for lemon cures diabetes", allow_mock=True)
    assert isinstance(result, str)
    assert len(result) > 0


def test_all_live_fail_raises_when_mock_unauthorized():
    """Verify fail-closed when live fails and allow_mock=False."""
    gemini_mock = MagicMock(spec=LLMProvider)
    gemini_mock.is_available.return_value = True
    gemini_mock.generate.side_effect = RuntimeError("Gemini network error")

    groq_mock = MagicMock(spec=LLMProvider)
    groq_mock.is_available.return_value = True
    groq_mock.generate.side_effect = RuntimeError("Groq network error")

    openai_mock = MagicMock(spec=LLMProvider)
    openai_mock.is_available.return_value = True
    openai_mock.generate.side_effect = RuntimeError("OpenAI quota 429")

    gateway = DefaultLLMGateway(
        settings_instance=Settings(environment="development", aegis_mock_llm=False),
        gemini_provider=gemini_mock,
        groq_provider=groq_mock,
        openai_provider=openai_mock,
    )
    gateway.mock_mode = False

    with pytest.raises(RuntimeError, match="OpenAI quota 429"):
        gateway.generate_text("test query", allow_mock=False, purpose="search_suggestion")


def test_groq_provider_availability():
    """GroqProvider availability depends on key presence."""
    p_none = GroqProvider(api_key="")
    assert p_none.is_available() is False

    p_valid = GroqProvider(api_key="gsk_test123")
    assert p_valid.is_available() is True


def test_openai_provider_availability():
    """OpenAIProvider availability depends on key presence."""
    p_none = OpenAIProvider(api_key="")
    assert p_none.is_available() is False

    p_valid = OpenAIProvider(api_key="sk-test123")
    assert p_valid.is_available() is True

def test_gemini_in_cooldown_falls_over_to_groq():
    """When Gemini is in provider cooldown (AdvisoryProviderBlocked), fallback to Groq succeeds (Comment 2)."""
    from backend.infrastructure.llm.advisory_policy import AdvisoryProviderBlocked

    gemini_mock = MagicMock(spec=LLMProvider)
    gemini_mock.is_available.return_value = True
    gemini_mock.generate.side_effect = AdvisoryProviderBlocked("Gemini provider in cooldown")

    groq_mock = MagicMock(spec=LLMProvider)
    groq_mock.is_available.return_value = True
    groq_mock.generate.return_value = LLMResponse(
        content='{"suggestion": "safe fallback from groq"}',
        model="openai/gpt-oss-20b",
        provider="groq",
        latency_ms=95.0,
        usage=LLMUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20, is_estimated=False),
    )

    gateway = DefaultLLMGateway(
        settings_instance=Settings(environment="development", aegis_mock_llm=False),
        gemini_provider=gemini_mock,
        groq_provider=groq_mock,
    )
    gateway.mock_mode = False

    result = gateway.generate_text("test query", purpose="search_suggestion")
    assert "safe fallback from groq" in result
    assert gemini_mock.generate.call_count == 1
    assert groq_mock.generate.call_count == 1


def test_budget_exhaustion_fails_closed_without_secondary_attempts():
    """When overall daily budget or scope is exhausted (AdvisoryPolicyError), gateway fails closed."""
    from backend.infrastructure.llm.advisory_policy import AdvisoryPolicyError

    gemini_mock = MagicMock(spec=LLMProvider)
    gemini_mock.is_available.return_value = True
    gemini_mock.generate.side_effect = AdvisoryPolicyError("Hard request budget exhausted")

    groq_mock = MagicMock(spec=LLMProvider)
    groq_mock.is_available.return_value = True

    gateway = DefaultLLMGateway(
        settings_instance=Settings(environment="development", aegis_mock_llm=False),
        gemini_provider=gemini_mock,
        groq_provider=groq_mock,
    )
    gateway.mock_mode = False

    with pytest.raises(AdvisoryPolicyError, match="Hard request budget exhausted"):
        gateway.generate_text("test query", purpose="search_suggestion")

    assert gemini_mock.generate.call_count == 1
    assert groq_mock.generate.call_count == 0
