"""
Aegis Protocol — Centralized LLM Gateway
=========================================
ADR 0004 Implementation: Centralized gateway managing LLM providers, structured output
parsing, offline mock enforcement, key rotation, and telemetry.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

from backend.core.settings import Settings, get_settings
from backend.infrastructure.llm.protocol import LLMGateway, LLMProvider, LLMResponse
from backend.infrastructure.llm.providers.gemini import GeminiProvider
from backend.infrastructure.llm.providers.mock import MockLLMProvider

logger = logging.getLogger(__name__)
T = TypeVar("T")


def clean_json_markdown(text: str) -> str:
    """Clean markdown code block wrappers (```json ... ```) from LLM output."""
    cleaned = text.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    return cleaned.strip()


class DefaultLLMGateway(LLMGateway):
    """Authoritative centralized LLM gateway."""

    def __init__(
        self,
        settings_instance: Optional[Settings] = None,
        gemini_provider: Optional[LLMProvider] = None,
        mock_provider: Optional[LLMProvider] = None
    ):
        self.settings = settings_instance or get_settings()
        self.gemini_provider = gemini_provider or GeminiProvider(self.settings)
        self.mock_provider = mock_provider or MockLLMProvider()
        self._mock_mode_override: Optional[bool] = None

    @property
    def mock_mode(self) -> bool:
        """True if mock provider is actively forced or required."""
        if self._mock_mode_override is not None:
            return self._mock_mode_override
        return self.settings.is_mock_llm or not self.gemini_provider.is_available()

    @mock_mode.setter
    def mock_mode(self, value: bool) -> None:
        """Allow runtime override for test harnesses."""
        self._mock_mode_override = value

    @property
    def active_provider(self) -> LLMProvider:
        """Resolve active provider based on configuration and availability."""
        if self.mock_mode:
            return self.mock_provider
        return self.gemini_provider

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Generate unstructured text from active provider."""
        resp: LLMResponse = self.active_provider.generate(prompt, model=model or self.settings.default_model, **kwargs)
        return resp.content

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        model: Optional[str] = None,
        **kwargs: Any
    ) -> T:
        """Generate and validate structured output matching the provided schema."""
        raw_text = self.generate_text(prompt, model=model, **kwargs)
        cleaned = clean_json_markdown(raw_text)

        try:
            parsed_data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(f"[LLMGateway] Failed to parse JSON response: {exc}. Raw: {cleaned[:300]}")
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

        # If schema is a Pydantic model
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            if hasattr(schema, "model_validate"):
                return schema.model_validate(parsed_data)  # Pydantic v2
            return schema.parse_obj(parsed_data)  # Pydantic v1 fallback

        # If schema is dict, list, or primitive type
        if schema in (dict, list, Any) or getattr(schema, "__origin__", None) in (dict, list):
            return parsed_data  # type: ignore

        return parsed_data  # type: ignore


# Global singleton gateway
_gateway_instance: Optional[DefaultLLMGateway] = None


def get_llm_gateway() -> DefaultLLMGateway:
    """Return the singleton DefaultLLMGateway instance."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = DefaultLLMGateway()
    return _gateway_instance


llm_gateway: DefaultLLMGateway = get_llm_gateway()
