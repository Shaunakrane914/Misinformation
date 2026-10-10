"""
Aegis Protocol — Centralized Gemini Intelligence Service (Shim & Adapter)
========================================================================
ADR 0004 Implementation: Delegates inference execution to `backend.infrastructure.llm.llm_gateway`
and configuration to `backend.core.settings.settings`.
Preserves historical class interfaces, singleton identity, and test fixture hooks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from backend.core.settings import Settings, settings
from backend.infrastructure.llm.gateway import DefaultLLMGateway, get_llm_gateway
from backend.infrastructure.llm.providers.mock import MockLLMProvider

logger = logging.getLogger(__name__)

# Validated production Google Gemini model hierarchy
DEFAULT_MODELS: List[str] = list(settings.gemini_models)


class MockGeminiProvider:
    """Backward-compatible MockGeminiProvider delegating to MockLLMProvider."""

    def __init__(self):
        self._provider = MockLLMProvider()

    def generate_content(self, prompt: str, model: str = "mock-model") -> str:
        return self._provider.generate(prompt, model=model).content


class GeminiService:
    """
    Centralized service for interacting with Google Gemini API models.
    Delegates to the authoritative LLMGateway and validated Settings.
    """

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        models: Optional[List[str]] = None,
        use_mock: Optional[bool] = None,
        timeout: Optional[float] = None,
        gateway: Optional[DefaultLLMGateway] = None,
    ):
        if gateway is not None:
            self.gateway = gateway
        else:
            # Each constructed compatibility service owns its provider state.
            # This prevents a test/helper instance from reconfiguring the
            # process-wide singleton used by unrelated agents.
            settings_data = settings.model_dump()
            if api_keys is not None:
                settings_data["gemini_api_keys"] = [
                    key.strip().strip('"').strip("'")
                    for key in api_keys if key and key.strip()
                ]
            if models is not None:
                settings_data["gemini_models"] = list(models)
                if models:
                    settings_data["default_model"] = models[0]
            if timeout is not None:
                settings_data["llm_request_timeout"] = timeout
            if use_mock is not None:
                settings_data["aegis_mock_llm"] = use_mock
            self.gateway = DefaultLLMGateway(Settings(**settings_data))

        self.models = list(self.gateway.settings.gemini_models)
        self.timeout = self.gateway.settings.llm_request_timeout
        self.mock_provider = MockGeminiProvider()

        self.api_keys = list(getattr(self.gateway.gemini_provider, "api_keys", []))

        if use_mock is not None:
            self.gateway.mock_mode = use_mock

        logger.info(
            f"[GeminiService] Initialized (keys={len(self.api_keys)}, primary_model={self.models[0] if self.models else 'None'}, mock_mode={self.mock_mode})"
        )

    @property
    def use_mock(self) -> bool:
        return self.gateway.mock_mode

    @use_mock.setter
    def use_mock(self, val: bool) -> None:
        self.gateway.mock_mode = val

    @property
    def mock_mode(self) -> bool:
        return self.gateway.mock_mode

    @mock_mode.setter
    def mock_mode(self, val: bool) -> None:
        self.gateway.mock_mode = val

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        allow_mock_fallback: Optional[bool] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Generate text completion with model and key fallback via LLMGateway.
        If allow_mock_fallback is False and live keys are missing, raises RuntimeError.
        """
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt

        mock_authorized = (
            self.gateway.mock_mode
            if allow_mock_fallback is None
            else bool(allow_mock_fallback)
        )

        try:
            # No explicit model: use the configured preferred model followed by
            # the provider's permitted fallback chain.
            return self.gateway.generate_text(
                full_prompt,
                model=model,
                allow_mock=mock_authorized,
            )
        except Exception as exc:
            if not mock_authorized:
                raise RuntimeError(
                    "Live Gemini provider unavailable and mock fallback disabled (scientific mode)."
                ) from exc
            raise

    def generate_content(self, prompt: str, model: Optional[str] = None) -> str:
        """Alias for generate_text matching Google GenAI SDK method name."""
        return self.gateway.generate_text(prompt, model=model)

    async def generate_text_async(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        allow_mock_fallback: Optional[bool] = None,
        model: Optional[str] = None,
    ) -> str:
        """Asynchronous execution delegating in-thread to gateway."""
        return await asyncio.to_thread(
            self.generate_text,
            prompt,
            system_instruction,
            allow_mock_fallback,
            model,
        )


# Global singleton instance
gemini_service = GeminiService(gateway=get_llm_gateway())


def get_gemini_service() -> GeminiService:
    """Return singleton instance of GeminiService."""
    return gemini_service
