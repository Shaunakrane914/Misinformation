"""
Aegis Protocol — Core System Infrastructure
===========================================
Defines centralized configuration, application settings, and domain invariants.
"""

from backend.core.settings import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
