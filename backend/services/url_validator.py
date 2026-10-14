"""
[LEGACY_COMPATIBILITY_SHIM]
Aegis Protocol — SSRF Defense Service Shim
===========================================
Re-exports canonical security primitives from:
backend.infrastructure.acquisition.security.url_validator
"""

from backend.infrastructure.acquisition.security.url_validator import (
    ALLOWED_PORTS,
    ALLOWED_SCHEMES,
    APPROVED_SOCIAL_MIRROR_HOSTNAMES,
    BLOCKED_HOSTNAMES,
    BLOCKED_NETWORKS,
    _DNS_CACHE,
    _DNS_CACHE_TTL,
    clear_dns_cache,
    is_ip_blocked,
    is_safe_url,
    validate_url_safe,
)

__all__ = [
    "ALLOWED_PORTS",
    "ALLOWED_SCHEMES",
    "APPROVED_SOCIAL_MIRROR_HOSTNAMES",
    "BLOCKED_HOSTNAMES",
    "BLOCKED_NETWORKS",
    "clear_dns_cache",
    "is_ip_blocked",
    "is_safe_url",
    "validate_url_safe",
]
