"""
Aegis Protocol — Channel Abstraction & Evidence Fragment
========================================================
Defines the Channel protocol, ChannelStatus enum, and EvidenceFragment
dataclass used across the entire Agent Reach capability layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ChannelStatus(str, Enum):
    """Health status of an internet evidence channel."""
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTH_REQUIRED = "AUTH_REQUIRED"


@dataclass
class EvidenceFragment:
    """
    Normalized retrieval output from any channel.
    Every piece of internet evidence goes through this representation
    before being consumed by Aegis agents.
    """
    platform: str
    title: str = ""
    content: str = ""
    url: str = ""
    author: str = ""
    published: str = ""
    snippet: str = ""
    score: float = 0.0
    retrieval_method: str = "agent_reach"
    retrieved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    channel_name: str = ""
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses and JSON storage."""
        return {
            "platform": self.platform,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "author": self.author,
            "published": self.published,
            "snippet": self.snippet,
            "score": self.score,
            "retrieval_method": self.retrieval_method,
            "retrieved_at": self.retrieved_at,
            "channel_name": self.channel_name,
            "raw_metadata": self.raw_metadata,
        }

    @classmethod
    def from_scraper_dict(cls, data: Dict[str, Any], channel_name: str) -> "EvidenceFragment":
        """
        Factory: convert a raw scraper result dict into an EvidenceFragment.
        Handles the varied field names across Reddit/Twitter/YouTube/News scrapers.
        """
        return cls(
            platform=data.get("platform", channel_name),
            title=data.get("title", ""),
            content=data.get("content", ""),
            url=data.get("url", ""),
            author=data.get("author", ""),
            published=data.get("published", ""),
            snippet=data.get("snippet", data.get("title", "")),
            score=float(data.get("score", 0)),
            retrieval_method="agent_reach",
            channel_name=channel_name,
            raw_metadata={
                k: v for k, v in data.items()
                if k not in ("platform", "title", "content", "url", "author",
                             "published", "snippet", "score")
            },
        )


@dataclass
class RetrievalResult:
    """Complete result from a retrieval operation across multiple channels."""
    query: str
    domain: str
    fragments: List[EvidenceFragment] = field(default_factory=list)
    channel_health: Dict[str, str] = field(default_factory=dict)
    total_signals: int = 0
    retrieval_plan: Optional[Dict[str, Any]] = None
    source_article: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API responses."""
        return {
            "query": self.query,
            "domain": self.domain,
            "fragments": [f.to_dict() for f in self.fragments],
            "channel_health": self.channel_health,
            "total_signals": self.total_signals,
            "retrieval_plan": self.retrieval_plan,
            "source_article": self.source_article,
        }

    # ── Backward-compatible accessors ─────────────────────────────────────
    # These let existing code that expects the old omni_scan dict shape
    # continue to work without changes.

    @property
    def items(self) -> List[Dict[str, Any]]:
        """Legacy accessor: return fragments as dicts (matches omni_scan output)."""
        return [f.to_dict() for f in self.fragments]

    @property
    def channels(self) -> Dict[str, List[Dict[str, Any]]]:
        """Legacy accessor: return fragments grouped by channel name."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for frag in self.fragments:
            key = frag.channel_name or frag.platform.lower().replace("/", "_").replace(" ", "_")
            grouped.setdefault(key, []).append(frag.to_dict())
        return grouped


class Channel(ABC):
    """
    Abstract base for an internet evidence channel.

    Each channel encapsulates one retrieval backend (Reddit, Twitter, etc.)
    and exposes a uniform search + health-check interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique channel identifier (e.g. 'reddit', 'twitter')."""

    @abstractmethod
    def search(self, query: str, limit: int = 6) -> List[EvidenceFragment]:
        """
        Search this channel for evidence matching the query.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of normalized EvidenceFragment objects
        """

    @abstractmethod
    def health_check(self) -> ChannelStatus:
        """
        Probe this channel's availability.

        Returns:
            Current ChannelStatus
        """

    def __repr__(self) -> str:
        return f"<Channel:{self.name}>"
