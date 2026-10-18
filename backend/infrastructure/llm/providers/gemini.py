"""
Aegis Protocol — Google Gemini LLM Provider
============================================
Explicit advisory-only provider: one strict model, first configured key, one
attempt, no rotation/fallback, and persisted run budgets/cooldown. Ordinary
research and native verdict/report synthesis never receive live generation.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List, Optional
import requests

from backend.core.settings import Settings, get_settings
from backend.infrastructure.llm.protocol import LLMProvider, LLMResponse, LLMUsage
from backend.infrastructure.llm.providers.rate_limit import GeminiRateLimitError, quota_diagnostics

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Fail-closed, strictly bounded optional suggestions, not native reasoning."""

    def __init__(self, settings_instance: Optional[Settings] = None):
        self.settings = settings_instance or get_settings()
        self.api_keys: List[str] = [k.strip() for k in self.settings.gemini_api_keys if k.strip()]

    def is_available(self) -> bool:
        """True if a credential is configured, not proof of upstream acceptance."""
        return bool(self.api_keys)

    def generate(self, prompt: str, model: Optional[str] = None, **kwargs: Any) -> LLMResponse:
        """Only explicit, serial, budgeted advisory generation is permitted."""
        from backend.infrastructure.llm.advisory_policy import MODEL, reserve_request, set_cooldown, AdvisoryPolicyError
        if not self.is_available():
            raise RuntimeError("GeminiProvider unavailable: No API keys configured.")
        if model != MODEL or len(prompt) > 6000 or kwargs.get("max_attempts", 1) != 1:
            raise AdvisoryPolicyError("Only bounded strict-identity Flash-Lite advice is permitted")
        tokens = kwargs.get("max_output_tokens", 160)
        if type(tokens) is not int or not 1 <= tokens <= 160:
            raise AdvisoryPolicyError("Advisory output limit is 160 tokens")
        timeout = min(2.0, float(kwargs.get("timeout", 2.0)))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("LLM timeout must be finite and positive")
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"maxOutputTokens": tokens, "responseMimeType": "application/json"}}
        started = time.perf_counter()
        with reserve_request(kwargs.get("purpose")):
            # Exactly the first configured credential; never rotate or fallback.
            try:
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                    headers={"Content-Type": "application/json", "x-goog-api-key": self.api_keys[0]},
                    json=payload, timeout=timeout)
            except Exception as error:
                raise RuntimeError("Advisory transport failed: " + type(error).__name__) from None
            if response.status_code == 429:
                diagnostics = quota_diagnostics(response)
                set_cooldown(diagnostics["retry_after_seconds"] or 60)
                raise GeminiRateLimitError(diagnostics)
            if response.status_code != 200:
                raise RuntimeError(f"Gemini advisory returned HTTP {response.status_code}")
            data = response.json()
            content = self._extract_content(data)
            usage = self._usage_from_response(data, prompt, content)
            logger.info("Advisory completed; usage_source=%s total_tokens=%s",
                        "estimated" if usage.is_estimated else "provider", usage.total_tokens)
            return LLMResponse(content=content, model=MODEL, provider="gemini",
                latency_ms=(time.perf_counter()-started)*1000, usage=usage, raw_response=data,
                metadata={"usage_source": "heuristic_estimate" if usage.is_estimated else "provider"})

    def _extract_content(self, data: Dict[str, Any]) -> str:
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts and "text" in parts[0]:
                return parts[0]["text"]
        raise ValueError("Unexpected response structure from Gemini API")

    def _estimate_usage(self, prompt: str, content: str) -> LLMUsage:
        prompt_tokens = int(len(prompt.split()) * 1.3)
        completion_tokens = int(len(content.split()) * 1.3)
        return LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=(prompt_tokens * 0.075 + completion_tokens * 0.3) / 1_000_000
        )

    def _usage_from_response(
        self, data: Dict[str, Any], prompt: str, content: str
    ) -> LLMUsage:
        """Prefer provider token counts; clearly mark local heuristics as estimates."""
        usage = data.get("usageMetadata") or {}
        prompt_tokens = usage.get("promptTokenCount")
        completion_tokens = usage.get("candidatesTokenCount")
        total_tokens = usage.get("totalTokenCount")
        if all(isinstance(value, int) for value in (
            prompt_tokens, completion_tokens, total_tokens
        )):
            return LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=0.0,
                is_estimated=False,
            )
        return self._estimate_usage(prompt, content)
