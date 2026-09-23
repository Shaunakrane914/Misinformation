"""
Aegis Protocol — Native Agent Reach Error Hierarchy
===================================================
Provides strongly typed exceptions for the upstream capability layer.
"""

from typing import Any, Dict, Optional


class NativeReachError(Exception):
    """Base exception for all native Agent Reach capability operations."""
    def __init__(self, message: str, platform: str = "", backend: str = "", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.platform = platform
        self.backend = backend
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "platform": self.platform,
            "backend": self.backend,
            "details": self.details,
        }


class AuthRequiredError(NativeReachError):
    """Raised when a platform requires browser session, login credentials, or auth cookies."""
    def __init__(self, platform: str, backend: str = "", hint: str = ""):
        msg = f"Platform '{platform}' requires authentication/session on backend '{backend}'. {hint}".strip()
        super().__init__(msg, platform=platform, backend=backend, details={"hint": hint, "status": "AUTH_REQUIRED"})


class BackendExecutionError(NativeReachError):
    """Raised when an allowlisted upstream tool command fails or exits non-zero."""
    def __init__(self, platform: str, backend: str, command: str, exit_code: int, stderr: str = ""):
        msg = f"Backend '{backend}' for platform '{platform}' failed (exit code {exit_code}): {stderr[:300]}"
        super().__init__(
            msg,
            platform=platform,
            backend=backend,
            details={"command": command, "exit_code": exit_code, "stderr": stderr[:500]}
        )


class ChannelDegradedError(NativeReachError):
    """Raised when a channel is partially available or throttled."""
    pass


class FallbackTriggered(NativeReachError):
    """Notification when primary backend fails and a fallback backend is activated."""
    def __init__(self, platform: str, primary_backend: str, fallback_backend: str, reason: str = ""):
        msg = f"Platform '{platform}' falling back from '{primary_backend}' to '{fallback_backend}': {reason}"
        super().__init__(
            msg,
            platform=platform,
            backend=fallback_backend,
            details={"primary_backend": primary_backend, "fallback_backend": fallback_backend, "reason": reason}
        )


class SecurityPolicyViolation(NativeReachError):
    """Raised on SSRF attempts, non-allowlisted commands, or private IP resolution."""
    pass
