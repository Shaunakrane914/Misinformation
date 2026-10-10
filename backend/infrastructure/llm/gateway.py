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
from contextvars import ContextVar
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError

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
        self._last_response: ContextVar[Optional[LLMResponse]] = ContextVar(
            f"aegis_llm_last_response_{id(self)}", default=None
        )

    @property
    def last_response(self) -> Optional[LLMResponse]:
        """Most recent response in the current execution context."""
        return self._last_response.get()

    @property
    def mock_mode(self) -> bool:
        """True only if mock execution is explicitly configured."""
        if self._mock_mode_override is not None:
            return self._mock_mode_override
        return self.settings.is_mock_llm

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
        """Generate text with explicit mock authorization and model semantics.

        Omitting ``model`` activates the configured provider fallback chain.
        Supplying a model requests strict identity and therefore does not fall
        through to a different model. ``allow_mock=False`` is fail-closed even
        if the gateway itself was configured in mock mode.
        """
        allow_mock = kwargs.pop("allow_mock", None)
        mock_authorized = self.mock_mode if allow_mock is None else bool(allow_mock)

        if not mock_authorized:
            # Scientific mode bypasses a process/test-level mock preference and
            # selects the live provider directly. It still fails closed when
            # live credentials are unavailable.
            provider = self.gemini_provider
            if not provider.is_available():
                raise RuntimeError("Live Gemini provider unavailable: no valid API key configured")
        elif self.mock_mode:
            provider = self.mock_provider
        else:
            provider = self.gemini_provider
            if not provider.is_available():
                provider = self.mock_provider

        try:
            response = provider.generate(prompt, model=model, **kwargs)
        except Exception:
            if provider is self.mock_provider or not mock_authorized:
                raise
            logger.warning(
                "[LLMGateway] Live provider failed; using explicitly authorized synthetic mock output"
            )
            response = self.mock_provider.generate(prompt, model=None, **kwargs)

        if response.synthetic and not mock_authorized:
            raise RuntimeError("Synthetic LLM output blocked by fail-closed policy")
        self._last_response.set(response)
        return response.content

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
            logger.error(
                "[LLMGateway] Failed to parse provider JSON response at character %s",
                exc.pos,
            )
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

        # Pydantic models preserve their native validation/error behavior.
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            if hasattr(schema, "model_validate"):
                return schema.model_validate(parsed_data)  # Pydantic v2
            return schema.parse_obj(parsed_data)  # Pydantic v1 fallback

        if schema is Any:
            return parsed_data  # type: ignore[return-value]

        try:
            return TypeAdapter(schema).validate_python(parsed_data)  # type: ignore[return-value]
        except (ValidationError, TypeError) as exc:
            raise ValueError(
                f"LLM output does not match requested schema {schema!r}"
            ) from exc


# Global singleton gateway
_gateway_instance: Optional[DefaultLLMGateway] = None


def get_llm_gateway() -> DefaultLLMGateway:
    """Return the singleton DefaultLLMGateway instance."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = DefaultLLMGateway()
    return _gateway_instance


llm_gateway: DefaultLLMGateway = get_llm_gateway()
