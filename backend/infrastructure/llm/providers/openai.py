"""
Aegis Protocol — OpenAI LLM Provider
====================================
Secondary sequential fallback provider using OpenAI's API.
Handles quota exhaustion (HTTP 429) gracefully to prevent blocking agent workflows.
"""
from __future__ import annotations

import logging
import math
import os
import time
from typing import Any, Dict, Optional
import requests

from backend.core.settings import Settings, get_settings
from backend.infrastructure.llm.protocol import LLMProvider, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class OpenAIProvider(LLMProvider):
    """OpenAI inference provider for secondary fallback."""

    def __init__(self, settings_instance: Optional[Settings] = None, api_key: Optional[str] = None):
        self.settings = settings_instance or get_settings()
        self.api_key = (
            api_key
            or getattr(self.settings, "openai_api_key", None)
            or os.getenv("OPENAI_API_KEY", "")
        ).strip()
        self.default_model = getattr(self.settings, "openai_model", DEFAULT_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL

    def is_available(self) -> bool:
        """True if a valid OpenAI API key is present."""
        return bool(self.api_key)

    def generate(self, prompt: str, model: Optional[str] = None, **kwargs: Any) -> LLMResponse:
        """Execute text or structured generation via OpenAI API under unified advisory governance."""
        from backend.infrastructure.llm.advisory_policy import (
            reserve_request, set_cooldown, AdvisoryPolicyError,
        )

        if not self.is_available():
            raise RuntimeError("OpenAIProvider unavailable: No API key configured.")

        if len(prompt) > 6000 or kwargs.get("max_attempts", 1) != 1:
            raise AdvisoryPolicyError("Advisory generation prompt exceeds 6000 chars or max_attempts != 1")

        tokens = kwargs.get("max_output_tokens", 160)
        if type(tokens) is not int or not 1 <= tokens <= 250:
            raise AdvisoryPolicyError("Advisory output limit is 160-250 tokens")

        selected_model = model if (model and not model.startswith("gemini-") and not "/" in model) else self.default_model
        timeout = min(2.5, float(kwargs.get("timeout", 2.0)))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("LLM timeout must be finite and positive")

        payload: Dict[str, Any] = {
            "model": selected_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(kwargs.get("temperature", 0.0)),
            "max_tokens": tokens,
        }
        if kwargs.get("json_mode", False) or "schema" in kwargs or "json" in prompt.lower():
            payload["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AegisProtocol/1.0",
        }

        with reserve_request(kwargs.get("purpose"), provider_name="openai"):
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
            except Exception as error:
                latency = (time.perf_counter() - started) * 1000
                logger.warning("[OpenAIProvider] Transport failed: %s after %.1fms", type(error).__name__, latency)
                raise RuntimeError(f"OpenAI transport failed: {type(error).__name__}") from None

            latency_ms = (time.perf_counter() - started) * 1000
            if response.status_code == 429:
                set_cooldown(60, "openai")
                err_data = {}
                try:
                    err_data = response.json().get("error", {})
                except Exception:
                    pass
                code = err_data.get("code", "rate_limit_or_quota_exhausted")
                msg = err_data.get("message", "Quota exhausted or rate limit reached")
                raise RuntimeError(f"OpenAI returned HTTP 429 ({code}): {msg}")

            if response.status_code != 200:
                raise RuntimeError(f"OpenAI advisory returned HTTP {response.status_code}: {response.text[:200]}")

            data = response.json()
            content = self._extract_content(data)
            usage = self._usage_from_response(data, prompt, content)

            logger.info(
                "[OpenAIProvider] Generation succeeded; model=%s tokens=%d latency=%.1fms",
                selected_model, usage.total_tokens, latency_ms
            )
            return LLMResponse(
                content=content,
                model=selected_model,
                provider="openai",
                latency_ms=latency_ms,
                usage=usage,
                raw_response=data,
                metadata={"provider_model": selected_model, "usage_source": "provider" if not usage.is_estimated else "estimated"},
            )

    def _extract_content(self, data: Dict[str, Any]) -> str:
        choices = data.get("choices", [])
        if choices and "message" in choices[0]:
            content = choices[0]["message"].get("content", "")
            if content:
                return content
        raise ValueError("Unexpected response structure from OpenAI API")

    def _usage_from_response(self, data: Dict[str, Any], prompt: str, content: str) -> LLMUsage:
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        if all(isinstance(v, int) for v in (prompt_tokens, completion_tokens, total_tokens)):
            return LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=0.0,
                is_estimated=False,
            )
        p_tok = int(len(prompt.split()) * 1.3)
        c_tok = int(len(content.split()) * 1.3)
        return LLMUsage(prompt_tokens=p_tok, completion_tokens=c_tok, total_tokens=p_tok + c_tok, is_estimated=True)

