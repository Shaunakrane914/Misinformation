"""Aegis Protocol — Universal RSS/Atom Feed Discovery & Ingestion Engine.

Automatically discovers RSS, Atom, and RDF feeds for any target domain or publisher
via HTML <link> inspection and standard endpoint probes, and ingests syndicated news items.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import feedparser

from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch as fetch_public_http
from backend.services.agent_reach.channels import (
    CandidateSource,
    ContentDepth,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)

COMMON_FEED_PATHS = (
    "/feed",
    "/rss",
    "/rss.xml",
    "/atom.xml",
    "/feed.xml",
    "/index.xml",
    "/feeds/posts/default",
)


class UniversalFeedDiscovery:
    """Discovers and parses RSS/Atom feeds from any web publisher."""

    @classmethod
    def discover_feed_urls(cls, base_url: str, html_content: Optional[str] = None) -> List[str]:
        """Discover valid feed endpoints from HTML <link> tags or standard endpoints."""
        discovered: List[str] = []
        parsed = urllib.parse.urlsplit(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        # 1. Inspect HTML for link tags
        if html_content:
            feed_links = re.findall(
                r'<link[^>]+type=["\'](?:application/rss\+xml|application/atom\+xml|text/xml)["\'][^>]+href=["\']([^"\']+)["\']',
                html_content,
                re.IGNORECASE,
            )
            # Reverse order pattern: href before type
            feed_links_alt = re.findall(
                r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\'](?:application/rss\+xml|application/atom\+xml|text/xml)["\']',
                html_content,
                re.IGNORECASE,
            )
            for link in feed_links + feed_links_alt:
                full_url = urllib.parse.urljoin(base_url, link.strip())
                if full_url not in discovered:
                    discovered.append(full_url)

        # 2. Add standard candidate feed endpoints if none found
        if not discovered:
            for path in COMMON_FEED_PATHS:
                discovered.append(f"{origin}{path}")

        return discovered

    @classmethod
    def parse_feed_content(cls, raw_xml: str, feed_url: str, limit: int = 10) -> List[EvidenceFragment]:
        """Parse raw RSS/Atom XML using feedparser into EvidenceFragment records."""
        fragments: List[EvidenceFragment] = []
        if len(raw_xml.encode("utf-8")) > 1_000_000 or re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", raw_xml, re.I):
            return fragments
        try:
            parsed = feedparser.parse(raw_xml)
            publisher = getattr(parsed.feed, "title", urllib.parse.urlsplit(feed_url).netloc)

            for entry in parsed.entries[:limit]:
                title = getattr(entry, "title", "Syndicated News")
                link = getattr(entry, "link", feed_url)
                author = getattr(entry, "author", publisher)
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                content_list = getattr(entry, "content", [])
                full_content = content_list[0].value if content_list and hasattr(content_list[0], "value") else summary

                published = ""
                if hasattr(entry, "published"):
                    published = entry.published
                elif hasattr(entry, "updated"):
                    published = entry.updated

                # Clean HTML tags from summary
                clean_snippet = re.sub(r'<[^>]+>', ' ', summary)
                clean_snippet = re.sub(r'\s+', ' ', clean_snippet).strip()[:400]

                clean_text = re.sub(r'<[^>]+>', ' ', full_content)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()[:4000]

                fragments.append(
                    EvidenceFragment(
                        platform="rss",
                        title=title,
                        content=clean_text or clean_snippet,
                        url=link,
                        author=author or publisher,
                        published=published,
                        snippet=clean_snippet,
                        score=85.0,
                        content_depth="SYNDICATED_SUMMARY",
                        retrieval_mode=RetrievalMode.RSS_FEED.value,
                        native_backend_id="feedparser_universal",
                        channel_name="rss",
                        raw_metadata={
                            "publisher": publisher,
                            "feed_url": feed_url,
                            "is_syndicated": True,
                            "linked_article_retrieved": False,
                        },
                    )
                )
        except Exception as exc:
            logger.debug(f"[UniversalFeedDiscovery] Feed parse error for {feed_url}: {type(exc).__name__}")

        return fragments
