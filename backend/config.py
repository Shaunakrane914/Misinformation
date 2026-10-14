"""
Aegis Protocol — Configuration (Backward Compatibility Shim)
============================================================
Canonical configuration relocated to `backend.core.settings.Settings`.
Preserves historical import paths, `AppConfig` class identity, and properties.
"""

from typing import List, Optional
from backend.core.settings import Settings, get_settings, settings as core_settings
from backend import __version__


class AppConfig:
    """Backward-compatible AppConfig wrapper delegating to backend.core.settings.Settings."""

    def __init__(self, settings_instance: Optional[Settings] = None):
        self._s = settings_instance or core_settings

    @property
    def app_name(self) -> str:
        return self._s.app_name

    @property
    def version(self) -> str:
        return self._s.version

    @property
    def environment(self) -> str:
        return self._s.environment

    @property
    def port(self) -> int:
        return self._s.port

    @property
    def allowed_origins(self) -> List[str]:
        return self._s.allowed_origins

    @property
    def gemini_api_key(self) -> Optional[str]:
        return self._s.gemini_api_key

    @property
    def gemini_api_key_2(self) -> Optional[str]:
        return self._s.gemini_api_key_2

    @property
    def gemini_api_key_3(self) -> Optional[str]:
        return self._s.gemini_api_key_3

    @property
    def supabase_url(self) -> Optional[str]:
        return self._s.supabase_url

    @property
    def supabase_key(self) -> Optional[str]:
        return self._s.supabase_key

    @property
    def supabase_service_role_key(self) -> Optional[str]:
        return self._s.supabase_service_role_key

    @property
    def supabase_anon_key(self) -> Optional[str]:
        return self._s.supabase_anon_key

    @property
    def apify_token(self) -> Optional[str]:
        return self._s.apify_token

    @property
    def yf_api_key(self) -> Optional[str]:
        return self._s.yf_api_key

    @property
    def agent_reach_enabled(self) -> bool:
        return self._s.agent_reach_enabled

    @property
    def agent_reach_timeout(self) -> float:
        return self._s.agent_reach_timeout

    @property
    def agent_reach_max_channels(self) -> int:
        return self._s.agent_reach_max_channels

    @property
    def agent_reach_max_results(self) -> int:
        return self._s.agent_reach_max_results

    @property
    def twilio_account_sid(self) -> Optional[str]:
        return self._s.twilio_account_sid

    @property
    def twilio_auth_token(self) -> Optional[str]:
        return self._s.twilio_auth_token

    @property
    def twilio_phone_number(self) -> Optional[str]:
        return self._s.twilio_phone_number

    @property
    def has_supabase(self) -> bool:
        return self._s.has_supabase

    @property
    def has_gemini(self) -> bool:
        return self._s.has_gemini

    @property
    def has_apify(self) -> bool:
        return self._s.has_apify


# Singleton global configuration instances
settings = AppConfig(core_settings)

__all__ = ["AppConfig", "settings", "get_settings"]
