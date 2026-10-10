"""
Aegis Protocol — Phase 6 Validated Settings Test Suite
======================================================
ADR 0004 Verification: Tests Pydantic-based configuration model, dynamic key discovery,
backward compatibility with AppConfig, and offline test invariants.
"""

import os
from unittest.mock import patch
import pytest

from backend.core.settings import Settings, get_settings, settings as core_settings
from backend.config import AppConfig, settings as legacy_settings


def test_settings_default_instantiation():
    """Verify Settings initializes with type-safe defaults."""
    cfg = Settings()
    assert cfg.app_name == "Aegis Protocol"
    assert isinstance(cfg.port, int)
    assert isinstance(cfg.allowed_origins, list)
    assert isinstance(cfg.gemini_models, list)
    assert len(cfg.gemini_models) >= 1
    assert cfg.default_model in cfg.gemini_models


def test_settings_gemini_key_discovery():
    """Verify dynamic discovery of all configured GEMINI_API_KEY* variants."""
    with patch.dict(os.environ, {
        "GEMINI_API_KEY": "AIzaSy_Primary_Test_Key",
        "GEMINI_API_KEY_2": "AIzaSy_Secondary_Test_Key",
        "GEMINI_KEY_EXTRA": "AIzaSy_Tertiary_Test_Key",
    }, clear=False):
        cfg = Settings()
        assert "AIzaSy_Primary_Test_Key" in cfg.gemini_api_keys
        assert "AIzaSy_Secondary_Test_Key" in cfg.gemini_api_keys
        assert "AIzaSy_Tertiary_Test_Key" in cfg.gemini_api_keys
        assert cfg.has_gemini is True


def test_settings_offline_mock_detection():
    """Verify aegis_mock_llm is automatically true when test environment or empty keys."""
    # Test environment explicitly active
    with patch.dict(os.environ, {"ENVIRONMENT": "test"}, clear=False):
        cfg = Settings()
        assert cfg.is_test_environment is True
        assert cfg.is_mock_llm is True

    # Empty keys force mock mode
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "AEGIS_MOCK_LLM": "false"}, clear=False):
        with patch("backend.core.settings._discover_gemini_api_keys", return_value=[]):
            cfg = Settings()
            assert cfg.has_gemini is False
            assert cfg.is_mock_llm is True


def test_settings_supabase_introspection():
    """Verify has_supabase introspection reflects configuration presence."""
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_KEY": "test_anon_key_secret"
    }, clear=False):
        cfg = Settings()
        assert cfg.has_supabase is True

    with patch.dict(os.environ, {"SUPABASE_URL": ""}, clear=False):
        cfg = Settings()
        assert cfg.has_supabase is False


def test_legacy_appconfig_backward_compatibility():
    """Verify legacy backend.config.AppConfig matches core.settings values and properties."""
    assert legacy_settings.app_name == core_settings.app_name
    assert legacy_settings.version == core_settings.version
    assert legacy_settings.port == core_settings.port
    assert legacy_settings.has_supabase == core_settings.has_supabase
    assert legacy_settings.has_gemini == core_settings.has_gemini
    assert legacy_settings.has_apify == core_settings.has_apify
    assert isinstance(legacy_settings, AppConfig)
