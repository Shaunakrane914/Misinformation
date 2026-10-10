"""
Aegis Protocol — LLM Gateway Protocol & Interfaces
===================================================
ADR 0004 Implementation: Abstract protocol definitions for LLM providers
and centralized inference gateway. Ensures agents depend on abstract protocols
rather than SDK internals or raw HTTP endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol, Type, TypeVar, runtime_checkable

T = TypeVar("T")


@dataclass
class LLMUsage:
    """Inference usage metrics for billing and observability."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class LLMResponse:
    """Standardized response container returned by LLM providers."""
    content: str
    model: str
    provider: str
    latency_ms: float = 0.0
    usage: LLMUsage = field(default_factory=LLMUsage)
    raw_response: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for underlying model providers (Gemini, Mock, Local, etc.)."""

    def generate(self, prompt: str, model: str, **kwargs: Any) -> LLMResponse:
        """Synchronously generate text response from LLM model."""
        ...

    def is_available(self) -> bool:
        """Check if provider credentials and network transport are ready."""
        ...


@runtime_checkable
class LLMGateway(Protocol):
    """Authoritative gateway interface consumed by agents and services."""

    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Generate unstructured text from primary model with fallback chain."""
        ...

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        model: Optional[str] = None,
        **kwargs: Any
    ) -> T:
        """Generate strictly validated structured output matching schema."""
        ...
