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
from typing import Any, Dict, List, Optional

from backend.core.settings import settings
from backend.infrastructure.llm.gateway import get_llm_gateway, llm_gateway
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
    ):
        self.gateway = get_llm_gateway()
        self.models = models or list(settings.gemini_models)
        self.timeout = timeout or settings.llm_request_timeout
        self.mock_provider = MockGeminiProvider()

        if api_keys is not None:
            self.api_keys = [k.strip().strip('"').strip("'") for k in api_keys if k and k.strip()]
        else:
            self.api_keys = list(settings.gemini_api_keys)

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
        allow_mock_fallback: bool = True,
    ) -> str:
        """
        Generate text completion with model and key fallback via LLMGateway.
        If allow_mock_fallback is False and live keys are missing, raises RuntimeError.
        """
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt

        if not allow_mock_fallback and not settings.has_gemini and not self.api_keys:
            raise RuntimeError(
                "Live Gemini provider unavailable and mock fallback disabled (scientific mode)"
            )

        try:
            return self.gateway.generate_text(full_prompt, model=self.models[0] if self.models else None)
        except Exception as exc:
            if not allow_mock_fallback:
                raise RuntimeError(
                    f"All live Gemini calls failed ({exc}). Mock fallback disabled for scientific evaluation."
                ) from exc
            logger.warning(f"[GeminiService] Live call failed ({exc}); falling back to local mock.")
            return self.mock_provider.generate_content(prompt, self.models[0] if self.models else "mock")

    def generate_content(self, prompt: str, model: Optional[str] = None) -> str:
        """Alias for generate_text matching Google GenAI SDK method name."""
        return self.gateway.generate_text(prompt, model=model or (self.models[0] if self.models else None))

    async def generate_text_async(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> str:
        """Asynchronous execution delegating in-thread to gateway."""
        return await asyncio.to_thread(
            self.generate_text,
            prompt,
            system_instruction,
            True
        )


# Global singleton instance
gemini_service = GeminiService()


def get_gemini_service() -> GeminiService:
    """Return singleton instance of GeminiService."""
    return gemini_service
