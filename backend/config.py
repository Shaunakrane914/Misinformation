"""
Aegis Protocol — Centralized Type-Safe Configuration & Environment Settings
===========================================================================
Provides dataclass-based environment configuration with defaults, type validation,
and status introspection for all services and agent dependencies.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv()

@dataclass(frozen=True)
class AppConfig:
    """Central configuration for Aegis Protocol."""
    app_name: str = "Aegis Protocol"
    version: str = "3.5.1"
    environment: str = os.getenv("ENVIRONMENT", "development")
    port: int = int(os.getenv("PORT", "8000"))
    allowed_origins: List[str] = field(default_factory=lambda: [os.getenv("ALLOWED_ORIGIN", "*")])

    # AI & Model APIs
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    gemini_api_key_2: Optional[str] = os.getenv("GEMINI_API_KEY_2")
    gemini_api_key_3: Optional[str] = os.getenv("GEMINI_API_KEY_3")

    # Supabase Database
    supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
    supabase_key: Optional[str] = os.getenv("SUPABASE_KEY")

    # Scrapers & Financial Intelligence
    apify_token: Optional[str] = os.getenv("APIFY_TOKEN")
    yf_api_key: Optional[str] = os.getenv("YF_API_KEY")

    # Notifications & Alerts
    twilio_account_sid: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = os.getenv("TWILIO_PHONE_NUMBER")

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key or self.gemini_api_key_2 or self.gemini_api_key_3)

    @property
    def has_apify(self) -> bool:
        return bool(self.apify_token)

# Singleton global configuration instance
settings = AppConfig()

if __name__ == "__main__":
    print(f"[{settings.app_name} v{settings.version}] Config Initialized")
    print(f"Supabase configured: {settings.has_supabase}")
    print(f"Gemini configured: {settings.has_gemini}")
    print(f"Apify configured: {settings.has_apify}")
