"""
Aegis Protocol — Native Platform Adapters Package
"""

from backend.services.agent_reach.native.adapters.base import PlatformAdapter
from backend.services.agent_reach.native.adapters.github import GitHubAdapter
from backend.services.agent_reach.native.adapters.reddit import RedditAdapter
from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
from backend.services.agent_reach.native.adapters.twitter import TwitterAdapter
from backend.services.agent_reach.native.adapters.web import WebAdapter
from backend.services.agent_reach.native.adapters.youtube import YouTubeAdapter

__all__ = [
    "PlatformAdapter",
    "GitHubAdapter",
    "RedditAdapter",
    "SearchDiscoveryAdapter",
    "TwitterAdapter",
    "WebAdapter",
    "YouTubeAdapter",
]
