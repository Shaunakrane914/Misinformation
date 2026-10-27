"""Newswire & Universal Feed Discovery Adapters."""

from backend.infrastructure.acquisition.adapters.news.feed_discovery import UniversalFeedDiscovery
from backend.infrastructure.acquisition.adapters.news.wires_adapter import NewswireAdapter

__all__ = ["UniversalFeedDiscovery", "NewswireAdapter"]
