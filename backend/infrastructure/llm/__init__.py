"""
Aegis Protocol — Centralized LLM Gateway Package
=================================================
Exposes LLM protocols, providers, and gateway singleton.
"""

from backend.infrastructure.llm.gateway import (
    DefaultLLMGateway,
    clean_json_markdown,
    get_llm_gateway,
    llm_gateway,
)
from backend.infrastructure.llm.protocol import (
    LLMGateway,
    LLMProvider,
    LLMResponse,
    LLMUsage,
)
from backend.infrastructure.llm.providers.gemini import GeminiProvider
from backend.infrastructure.llm.providers.mock import MockLLMProvider

__all__ = [
    "LLMGateway",
    "LLMProvider",
    "LLMResponse",
    "LLMUsage",
    "DefaultLLMGateway",
    "GeminiProvider",
    "MockLLMProvider",
    "clean_json_markdown",
    "get_llm_gateway",
    "llm_gateway",
]
