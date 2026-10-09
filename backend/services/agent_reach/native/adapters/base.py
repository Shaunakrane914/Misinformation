"""
[LEGACY_COMPATIBILITY_SHIM]
Aegis Protocol — Base Platform Adapter Contract Shim
======================================================
Re-exports canonical PlatformAdapter from:
backend.infrastructure.acquisition.adapters.base
"""

from backend.infrastructure.acquisition.adapters.base import PlatformAdapter

__all__ = ["PlatformAdapter"]
