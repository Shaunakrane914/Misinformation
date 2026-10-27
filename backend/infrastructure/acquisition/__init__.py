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
    if name in ("PinnedAsyncHTTPTransport", "PinnedNetworkBackend", "fetch_public_async_http"):
        from backend.infrastructure.acquisition.network.async_http import (
            PinnedAsyncHTTPTransport,
            PinnedNetworkBackend,
            fetch_public_async_http,
        )
        if name == "PinnedAsyncHTTPTransport":
            return PinnedAsyncHTTPTransport
        elif name == "PinnedNetworkBackend":
            return PinnedNetworkBackend
        return fetch_public_async_http
    if name == "DomainRateLimiter":
        from backend.infrastructure.acquisition.network.rate_limiter import DomainRateLimiter
        return DomainRateLimiter
    if name == "FactCheckAdapter":
        from backend.infrastructure.acquisition.adapters.factcheck.factcheck_adapter import FactCheckAdapter
        return FactCheckAdapter
    if name == "NewswireAdapter":
        from backend.infrastructure.acquisition.adapters.news.wires_adapter import NewswireAdapter
        return NewswireAdapter
    if name == "UniversalFeedDiscovery":
        from backend.infrastructure.acquisition.adapters.news.feed_discovery import UniversalFeedDiscovery
        return UniversalFeedDiscovery
    if name == "BlueskyAdapter":
        from backend.infrastructure.acquisition.adapters.social.bluesky import BlueskyAdapter
        return BlueskyAdapter
    if name == "HackerNewsAdapter":
        from backend.infrastructure.acquisition.adapters.social.hackernews import HackerNewsAdapter
        return HackerNewsAdapter
    if name == "TelegramPublicAdapter":
        from backend.infrastructure.acquisition.adapters.social.telegram import TelegramPublicAdapter
        return TelegramPublicAdapter
    if name == "SecEdgarAdapter":
        from backend.infrastructure.acquisition.adapters.regulatory.sec_edgar import SecEdgarAdapter
        return SecEdgarAdapter
    if name == "WikipediaAdapter":
        from backend.infrastructure.acquisition.adapters.encyclopedia.wikipedia import WikipediaAdapter
        return WikipediaAdapter
    if name == "SecFilingsFullAdapter":
        from backend.infrastructure.acquisition.adapters.regulatory.sec_filings_full import SecFilingsFullAdapter
        return SecFilingsFullAdapter
    if name == "ArxivAdapter":
        from backend.infrastructure.acquisition.adapters.academic.arxiv import ArxivAdapter
        return ArxivAdapter
    if name == "SubstackAdapter":
        from backend.infrastructure.acquisition.adapters.news.substack import SubstackAdapter
        return SubstackAdapter
    if name == "YahooFinanceAdapter":
        from backend.infrastructure.acquisition.adapters.financial.yahoo_finance import YahooFinanceAdapter
        return YahooFinanceAdapter
    if name == "ConsumerReviewAdapter":
        from backend.infrastructure.acquisition.adapters.consumer.trustpilot import ConsumerReviewAdapter
        return ConsumerReviewAdapter
    if name == "RedditDeepAdapter":
        from backend.infrastructure.acquisition.adapters.social.reddit_deep import RedditDeepAdapter
        return RedditDeepAdapter
    if name == "WikidataExecutiveAdapter":
        from backend.infrastructure.acquisition.adapters.governance.wikidata_exec import WikidataExecutiveAdapter
        return WikidataExecutiveAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AcquisitionService",
    "AgentReachService",
    "ArxivAdapter",
    "BlueskyAdapter",
    "ConsumerReviewAdapter",
    "DomainRateLimiter",
    "FactCheckAdapter",
    "HackerNewsAdapter",
    "JinaWebReaderAdapter",
    "NativeRouter",
    "NewswireAdapter",
    "PinnedAsyncHTTPTransport",
    "PinnedNetworkBackend",
    "RedditAdapter",
    "RedditDeepAdapter",
    "SecEdgarAdapter",
    "SecFilingsFullAdapter",
    "SubstackAdapter",
    "TelegramPublicAdapter",
    "TwitterAdapter",
    "UniversalFeedDiscovery",
    "WikidataExecutiveAdapter",
    "WikipediaAdapter",
    "YahooFinanceAdapter",
    "fetch_public_async_http",
    "is_safe_url",
    "native_router",
    "validate_url_safe",
]
