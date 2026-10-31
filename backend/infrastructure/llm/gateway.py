"""
Aegis Protocol — Centralized LLM Gateway
=========================================
ADR 0004 Implementation: Centralized gateway managing LLM providers, structured output
parsing, offline mock enforcement, key rotation, and sequential provider failover
(Gemini -> Groq -> OpenAI -> Mock/Fail).
"""

from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from typing import Any, List, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError

from backend.core.settings import Settings, get_settings
from backend.infrastructure.llm.protocol import LLMGateway, LLMProvider, LLMResponse
from backend.infrastructure.llm.providers.gemini import GeminiProvider
from backend.infrastructure.llm.providers.groq import GroqProvider
from backend.infrastructure.llm.providers.mock import MockLLMProvider
from backend.infrastructure.llm.providers.openai import OpenAIProvider

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
    """Authoritative centralized LLM gateway with sequential provider failover."""

    def __init__(
        self,
        settings_instance: Optional[Settings] = None,
        gemini_provider: Optional[LLMProvider] = None,
        groq_provider: Optional[LLMProvider] = None,
        openai_provider: Optional[LLMProvider] = None,
        mock_provider: Optional[LLMProvider] = None,
    ):
        self.settings = settings_instance or get_settings()
        self.gemini_provider = gemini_provider or GeminiProvider(self.settings)
        self.groq_provider = groq_provider or GroqProvider(self.settings)
        self.openai_provider = openai_provider or OpenAIProvider(self.settings)
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
        if value and self.settings.environment == "production":
            raise ValueError("Synthetic LLM execution is forbidden in production")
        self._mock_mode_override = value

    @property
    def active_provider(self) -> LLMProvider:
        """Resolve active provider based on configuration and availability."""
        if self.mock_mode:
            return self.mock_provider
        if self.gemini_provider.is_available():
            return self.gemini_provider
        if self.groq_provider.is_available():
            return self.groq_provider
        if self.openai_provider.is_available():
            return self.openai_provider
        return self.gemini_provider

    def _get_live_fallback_chain(self) -> List[Tuple[str, LLMProvider]]:
        """Ordered sequential failover chain: Gemini -> Groq -> OpenAI."""
        return [
            ("gemini", self.gemini_provider),
            ("groq", self.groq_provider),
            ("openai", self.openai_provider),
        ]

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Generate text with explicit mock authorization and sequential failover.

        Sequential Fallback Chain:
        1. Gemini (primary)
        2. Groq (first live fallback)
        3. OpenAI (second live fallback)
        4. Mock (authorized synthetic fallback, never allowed in production)
        """
        allow_mock = kwargs.pop("allow_mock", None)
        mock_authorized = self.mock_mode if allow_mock is None else bool(allow_mock)
        if self.settings.environment == "production":
            if mock_authorized:
                raise ValueError("Synthetic LLM fallback is forbidden in production")
            mock_authorized = False

        # If mock mode is explicitly configured and authorized, run mock directly
        if self.mock_mode and mock_authorized:
            response = self.mock_provider.generate(prompt, model=None, **kwargs)
            self._last_response.set(response)
            return response.content

        # Scientific mode or standard mode with mock disabled: attempt live provider chain
        live_chain = self._get_live_fallback_chain()
        available_live = [(name, p) for name, p in live_chain if p.is_available()]

        if not available_live:
            if not mock_authorized:
                raise RuntimeError("Live Gemini provider unavailable: no valid API key configured")
            response = self.mock_provider.generate(prompt, model=None, **kwargs)
            self._last_response.set(response)
            return response.content

        last_error: Optional[Exception] = None
        for name, provider in available_live:
            try:
                purpose = kwargs.get("purpose")
                kwargs["purpose"] = purpose

                # Enforce Aegis advisory governance across all live providers
                from backend.infrastructure.llm.advisory_policy import (
                    require_advisory, _run, _investigation, investigation_scope,
                    AdvisoryPolicyError, AdvisoryProviderBlocked,
                )
                import os, uuid
                is_live = os.getenv("AEGIS_LIVE_ADVISORY_ENABLED", "false").lower() in {"1", "true", "yes"}
                if _run.get() is None and is_live and self.settings.environment != "test":
                    from backend.infrastructure.llm.runtime_advisory import runtime_advisory_scope
                    with runtime_advisory_scope():
                        inv_id = _investigation.get() or f"live-advisory-{uuid.uuid4().hex[:8]}"
                        with investigation_scope(inv_id):
                            require_advisory(purpose)
                            response = provider.generate(prompt, model=model, **kwargs)
                else:
                    require_advisory(purpose)
                    response = provider.generate(prompt, model=model, **kwargs)

                if response.synthetic and not mock_authorized:
                    raise RuntimeError("Synthetic LLM output blocked by fail-closed policy")
                self._last_response.set(response)
                return response.content
            except AdvisoryProviderBlocked as exc:
                last_error = exc
                logger.warning(
                    "[LLMGateway] Provider '%s' blocked (%s); trying next provider in fallback chain",
                    name, exc
                )
                continue
            except AdvisoryPolicyError:
                # Governance policy violation (unscoped, daily budget exhausted, per-investigation limit) must fail closed
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "[LLMGateway] Provider '%s' failed (%s); trying next provider in fallback chain",
                    name, exc
                )
                continue

        # All live providers in the chain failed
        if mock_authorized:
            logger.warning(
                "[LLMGateway] All live providers failed; using explicitly authorized synthetic mock output"
            )
            response = self.mock_provider.generate(prompt, model=None, **kwargs)
            if response.synthetic and not mock_authorized:
                raise RuntimeError("Synthetic LLM output blocked by fail-closed policy")
            self._last_response.set(response)
            return response.content

        if last_error:
            raise last_error
        raise RuntimeError("All configured live providers failed in fallback chain")

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
