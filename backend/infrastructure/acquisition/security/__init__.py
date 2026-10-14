"""
Aegis Protocol — Acquisition Security Module
=============================================
SSRF defense, IP range validation, and safe URL verification.
"""

from backend.infrastructure.acquisition.security.url_validator import (
    ALLOWED_PORTS,
    ALLOWED_SCHEMES,
    APPROVED_SOCIAL_MIRROR_HOSTNAMES,
    BLOCKED_HOSTNAMES,
    BLOCKED_NETWORKS,
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
