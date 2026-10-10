"""
Aegis Protocol — Centralized Validated Settings
================================================
ADR 0004 Implementation: Pydantic-based validated configuration model.
Eliminates ad-hoc `os.getenv` reads across agents and business logic.
Guarantees fail-fast startup validation and deterministic offline mock detection.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Ensure base .env is loaded into process
load_dotenv()

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _HAS_PYDANTIC_SETTINGS = True
except ImportError:
    from pydantic import BaseModel as BaseSettings  # type: ignore
    SettingsConfigDict = None
    _HAS_PYDANTIC_SETTINGS = False

from pydantic import Field


def _discover_gemini_api_keys() -> List[str]:
    """Scan environment for all configured GEMINI_API_KEY* variants."""
    discovered: List[str] = []
    for k, v in sorted(os.environ.items()):
        if k == "GEMINI_API_KEY" or k.startswith("GEMINI_API_KEY_") or k.startswith("GEMINI_KEY_"):
            cleaned = v.strip().strip('"').strip("'") if v else ""
            if cleaned and cleaned not in discovered:
                discovered.append(cleaned)
    return discovered


class Settings(BaseSettings):
    """Authoritative Aegis Protocol application configuration."""

    # 1. Application & Core Environment
    app_name: str = Field(default="Aegis Protocol", description="Application service name")
    version: str = Field(default="4.1.0", description="Semantic service version")
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", os.getenv("AEGIS_ENV", "development")).lower())
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    allowed_origins: List[str] = Field(default_factory=lambda: [os.getenv("ALLOWED_ORIGIN", "*")])

    # 2. Generative AI & LLM Gateway
    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    gemini_api_key_2: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY_2"))
    gemini_api_key_3: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY_3"))
    gemini_api_keys: List[str] = Field(default_factory=_discover_gemini_api_keys)
    gemini_models: List[str] = Field(default_factory=lambda: [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ])
    default_model: str = Field(default="gemini-2.5-flash")
    aegis_mock_llm: bool = Field(
        default_factory=lambda: (
            os.getenv("AEGIS_MOCK_LLM", "").lower() in ("true", "1", "yes")
            or os.getenv("ENVIRONMENT", "").lower() == "test"
            or os.getenv("AEGIS_ENV", "").lower() == "test"
            or not any(k.startswith("AIzaSy") for k in _discover_gemini_api_keys())
        )
    )
    llm_request_timeout: float = Field(default=25.0)
    llm_max_retries: int = Field(default=3)

    # 3. Persistence & Database (Supabase / Local SQLite)
    supabase_url: Optional[str] = Field(default_factory=lambda: os.getenv("SUPABASE_URL"))
    supabase_key: Optional[str] = Field(
        default_factory=lambda: (
            os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
        )
    )
    supabase_service_role_key: Optional[str] = Field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    supabase_anon_key: Optional[str] = Field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY"))
    sqlite_db_path: str = Field(default_factory=lambda: os.getenv("SQLITE_DB_PATH", "aegis_local.db"))

    # 4. Intelligence & External Telemetry APIs
    apify_token: Optional[str] = Field(default_factory=lambda: os.getenv("APIFY_TOKEN"))
    yf_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("YF_API_KEY"))

    # 5. Authoritative Shared Acquisition Runtime
    agent_reach_enabled: bool = Field(default_factory=lambda: os.getenv("AGENT_REACH_ENABLED", "true").lower() == "true")
    agent_reach_timeout: float = Field(default_factory=lambda: float(os.getenv("AGENT_REACH_TIMEOUT", "12.0")))
    agent_reach_max_channels: int = Field(default_factory=lambda: int(os.getenv("AGENT_REACH_MAX_CHANNELS", "6")))
    agent_reach_max_results: int = Field(default_factory=lambda: int(os.getenv("AGENT_REACH_MAX_RESULTS", "10")))

    # 6. Notifications & Dispatch Alerts
    twilio_account_sid: Optional[str] = Field(default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID"))
    twilio_auth_token: Optional[str] = Field(default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN"))
    twilio_phone_number: Optional[str] = Field(default_factory=lambda: os.getenv("TWILIO_PHONE_NUMBER"))

    if _HAS_PYDANTIC_SETTINGS and SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            case_sensitive=False,
        )

    # ── Convenience Introspection Properties ─────────────────────────────────

    @property
    def has_supabase(self) -> bool:
        """True if Supabase URL and at least one credentials key are present."""
        return bool(self.supabase_url and (self.supabase_key or self.supabase_service_role_key or self.supabase_anon_key))

    @property
    def has_gemini(self) -> bool:
        """True if at least one valid Gemini API key is configured."""
        return bool(any(k.startswith("AIzaSy") for k in self.gemini_api_keys))

    @property
    def has_apify(self) -> bool:
        """True if Apify API token is configured."""
        return bool(self.apify_token)

    @property
    def is_test_environment(self) -> bool:
        """True if running inside an automated test session."""
        return self.environment in ("test", "testing") or bool(os.getenv("PYTEST_CURRENT_TEST"))

    @property
    def is_mock_llm(self) -> bool:
        """True if live LLM network calls are intercepted with deterministic mock responses."""
        return self.aegis_mock_llm or self.is_test_environment or not self.has_gemini


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()


# Canonical global settings instance
settings: Settings = get_settings()
