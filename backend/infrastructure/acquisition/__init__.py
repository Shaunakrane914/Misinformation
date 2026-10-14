"""
Aegis Protocol — Acquisition Layer
===================================
Authoritative internet evidence acquisition infrastructure.
Houses security gates, specialized platform adapters, and unified routing.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.infrastructure.acquisition.security.url_validator import is_safe_url, validate_url_safe
    from backend.infrastructure.acquisition.routing.router import NativeRouter, native_router
    from backend.infrastructure.acquisition.service import AcquisitionService, AgentReachService
    from backend.infrastructure.acquisition.adapters.social.reddit import RedditAdapter
    from backend.infrastructure.acquisition.adapters.social.twitter import TwitterAdapter
    from backend.infrastructure.acquisition.adapters.web.jina import JinaWebReaderAdapter


def __getattr__(name: str):
    if name in ("is_safe_url", "validate_url_safe"):
        from backend.infrastructure.acquisition.security.url_validator import is_safe_url, validate_url_safe
        return is_safe_url if name == "is_safe_url" else validate_url_safe
    if name in ("NativeRouter", "native_router"):
        from backend.infrastructure.acquisition.routing.router import NativeRouter, native_router
        return NativeRouter if name == "NativeRouter" else native_router
    if name in ("AcquisitionService", "AgentReachService"):
        from backend.infrastructure.acquisition.service import AcquisitionService, AgentReachService
        return AcquisitionService if name == "AcquisitionService" else AgentReachService
    if name == "RedditAdapter":
        from backend.infrastructure.acquisition.adapters.social.reddit import RedditAdapter
        return RedditAdapter
    if name == "TwitterAdapter":
        from backend.infrastructure.acquisition.adapters.social.twitter import TwitterAdapter
        return TwitterAdapter
    if name == "JinaWebReaderAdapter":
        from backend.infrastructure.acquisition.adapters.web.jina import JinaWebReaderAdapter
        return JinaWebReaderAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AcquisitionService",
    "AgentReachService",
    "JinaWebReaderAdapter",
    "NativeRouter",
    "RedditAdapter",
    "TwitterAdapter",
    "is_safe_url",
    "native_router",
    "validate_url_safe",
]
