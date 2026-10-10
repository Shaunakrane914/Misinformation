"""
Aegis Protocol — Google Gemini LLM Provider
============================================
ADR 0004 Implementation: Unified Google Gemini provider featuring:
- Automated key rotation across configured GEMINI_API_KEY* environment variables
- Exponential backoff with random jitter on HTTP 429 rate limits
- Dynamic model fallback hierarchy
- Standardized LLMResponse containers with latency tracking
"""

from __future__ import annotations

import itertools
import logging
import random
import threading
import time
from typing import Any, Dict, List, Optional
import requests

from backend.core.settings import Settings, get_settings
from backend.infrastructure.llm.protocol import LLMProvider, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Production provider for Google Gemini models with key rotation and backoff."""

    def __init__(self, settings_instance: Optional[Settings] = None):
        self.settings = settings_instance or get_settings()
        self.api_keys: List[str] = [k for k in self.settings.gemini_api_keys if k.startswith("AIzaSy")]
        self._key_cycle = itertools.cycle(self.api_keys) if self.api_keys else None
        self._key_lock = threading.Lock()
        self.models: List[str] = list(self.settings.gemini_models)
        self.timeout: float = self.settings.llm_request_timeout
        self.max_retries: int = self.settings.llm_max_retries

    def is_available(self) -> bool:
        """True if at least one valid AIzaSy API key is available."""
        return bool(self.api_keys)

    def generate(self, prompt: str, model: Optional[str] = None, **kwargs: Any) -> LLMResponse:
        """Execute inference against Gemini with automatic key rotation and model fallback."""
        if not self.is_available():
            raise RuntimeError("GeminiProvider unavailable: No valid Google AIzaSy API keys configured.")

        # An explicit model is a strict identity request. With no explicit
        # model, Settings has already placed the preferred model first and the
        # provider walks the remaining permitted fallbacks in order.
        models_to_try = [model] if model else list(self.models)
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        last_error: Optional[Exception] = None

        t0 = time.perf_counter()

        for current_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent"

            for key_attempt in range(len(self.api_keys)):
                with self._key_lock:
                    api_key = next(self._key_cycle)  # type: ignore

                for retry in range(self.max_retries):
                    try:
                        resp = requests.post(
                            url,
                            headers=headers,
                            params={"key": api_key},
                            json=payload,
                            timeout=self.timeout
                        )

                        if resp.status_code == 200:
                            data = resp.json()
                            content = self._extract_content(data)
                            latency = (time.perf_counter() - t0) * 1000
                            return LLMResponse(
                                content=content,
                                model=current_model,
                                provider="gemini",
                                latency_ms=latency,
                                usage=self._usage_from_response(data, prompt, content),
                                raw_response=data,
                                metadata={"usage_source": (
                                    "provider" if data.get("usageMetadata") else "heuristic_estimate"
                                )},
                            )

                        elif resp.status_code == 429:
                            # Rate limit encountered: apply exponential backoff with jitter
                            backoff = (2 ** retry) * 0.5 + random.uniform(0.1, 0.4)
                            logger.warning(
                                f"[GeminiProvider] HTTP 429 on {current_model}. "
                                f"Backing off {backoff:.2f}s (retry {retry+1}/{self.max_retries})."
                            )
                            time.sleep(backoff)
                            continue

                        else:
                            last_error = RuntimeError(
                                f"Gemini model {current_model} returned HTTP {resp.status_code}"
                            )
                            break  # Try next key or model

                    except Exception as exc:
                        last_error = RuntimeError(
                            f"Gemini request failed for {current_model}: {type(exc).__name__}"
                        )
                        time.sleep(0.3)

        raise RuntimeError(
            f"All configured Gemini models and API keys were exhausted. Last error: {last_error}"
        )

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
