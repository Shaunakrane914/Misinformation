"""Aegis Protocol — Wikipedia & Wikimedia Encyclopedic Adapter.

Provides deep encyclopedic profile intelligence for all domain agents:
- Corporate history, parent company hierarchy, and subsidiary trees
- Executive biographies and historical timelines
- Major controversy documentation and encyclopedic references
- Clean plain-text extraction up to 25,000 characters per document
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.adapters.expansion_safety import GuardedExpansionAdapter as PlatformAdapter
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

WIKIPEDIA_API_BASE = "https://en.wikipedia.org/w/api.php"
DEFAULT_WIKI_HEADERS = {
    "User-Agent": "AegisProtocol/1.0 (https://github.com/Shaunakrane914/Misinformation; bounded research)",
    "Accept": "application/json",
}


class WikipediaAdapter(PlatformAdapter):
    """Acquires comprehensive encyclopedic intelligence from Wikipedia & Wikimedia."""

    @property
    def platform(self) -> str:
        return "wikipedia"

    @property
    def backend_id(self) -> str:
        return "wikipedia_api"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("wikipedia", "wikimedia", "wiki", "encyclopedia"):
            return True
        return "wikipedia.org" in url or "wikimedia.org" in url

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Search Wikipedia for pages matching the query."""
        candidates: List[CandidateSource] = []
        clean_q = query.strip()
        if not clean_q:
            return candidates

        params = {
            "action": "query",
            "list": "search",
            "srsearch": clean_q,
            "format": "json",
            "utf8": "1",
            "srlimit": str(min(limit, 10)),
        }
        api_url = f"{WIKIPEDIA_API_BASE}?{urllib.parse.urlencode(params)}"
        if not validate_url_safe(api_url)[0]:
            logger.warning("[WikipediaAdapter] Blocked unsafe discovery URL: %s", api_url)
            return candidates

        try:
            resp = fetch_public_http(api_url, headers=DEFAULT_WIKI_HEADERS, timeout=5.0)
            if resp.status_code != 200:
                logger.warning("[WikipediaAdapter] Search HTTP %d for '%s'", resp.status_code, clean_q)
                return candidates

            data = json.loads(resp.body.decode("utf-8", errors="replace"))
            search_results = data.get("query", {}).get("search", [])

            for item in search_results:
                title = item.get("title", "")
                pageid = item.get("pageid", 0)
                wordcount = item.get("wordcount", 0)
                snippet_raw = item.get("snippet", "")
                # Clean html tags from snippet
                snippet = re.sub(r"<[^>]+>", "", snippet_raw).strip()
                page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

                candidates.append(
                    CandidateSource(
                        url=page_url,
                        canonical_url=page_url,
                        platform="wikipedia",
                        title=f"{title} — Wikipedia",
                        snippet=snippet,
                        metadata={
                            "pageid": pageid,
                            "wordcount": wordcount,
                            "timestamp": item.get("timestamp"),
                            "wiki_title": title,
                            "primary_source": False,
                            "official_source": False,
                        },
                    )
                )
        except Exception as exc:
            logger.warning("[WikipediaAdapter] Discovery failed for '%s': %s", clean_q, type(exc).__name__)

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """Fetch complete plaintext extract for the candidate Wikipedia article."""
        url = candidate.canonical_url or candidate.url
        wiki_title = candidate.metadata.get("wiki_title")

        if not wiki_title:
            # Extract title from URL path
            parsed = urllib.parse.urlparse(url)
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) >= 2 and path_parts[0] == "wiki":
                wiki_title = urllib.parse.unquote(path_parts[1].replace("_", " "))
            else:
                wiki_title = candidate.title.replace(" — Wikipedia", "").strip()

        params = {
            "action": "query",
            "prop": "extracts|pageprops|info|revisions",
            "explaintext": "1",
            "exsectionformat": "wiki",
            "titles": wiki_title,
            "format": "json",
            "inprop": "url",
            "rvprop": "ids|timestamp",
            "utf8": "1",
        }
        api_url = f"{WIKIPEDIA_API_BASE}?{urllib.parse.urlencode(params)}"
        if not validate_url_safe(api_url)[0]:
            return FetchedDocument(
                url=url,
                status="BLOCKED_SSRF",
                failure_reason="Wikipedia API URL failed SSRF check",
                backend_id=self.backend_id,
            )

        try:
            resp = fetch_public_http(api_url, headers=DEFAULT_WIKI_HEADERS, timeout=6.0, max_bytes=2_000_000)
            if resp.status_code != 200:
                return FetchedDocument(
                    url=url,
                    status="FAILED",
                    failure_reason=f"HTTP {resp.status_code}",
                    backend_id=self.backend_id,
                )

            data = json.loads(resp.body.decode("utf-8", errors="replace"))
            pages = data.get("query", {}).get("pages", {})
            page_data = next(iter(pages.values())) if pages else {}

            extract = page_data.get("extract", "")
            if not extract.strip():
                return FetchedDocument(url=url, status="EMPTY_CONTENT", backend_id=self.backend_id)
            title = page_data.get("title", wiki_title)
            pageprops = page_data.get("pageprops", {})
            from backend.infrastructure.acquisition.adapters.expansion_safety import matches_host
            if not matches_host(page_data.get("fullurl", url), ("en.wikipedia.org",)):
                return FetchedDocument(url=url, status="IDENTITY_MISMATCH", backend_id=self.backend_id)
            if title.casefold() != str(wiki_title).casefold():
                return FetchedDocument(url=url, status="ENTITY_REDIRECT_REVIEW_REQUIRED", backend_id=self.backend_id)
            if "disambiguation" in pageprops:
                return FetchedDocument(url=url, status="AMBIGUOUS_ENTITY", backend_id=self.backend_id)
            description = pageprops.get("wikibase-shortdesc", "")

            # Formulate structured encyclopedic document
            content = f"# {title}\n\n"
            if description:
                content += f"**Description**: {description}\n\n"
            content += extract

            # Cap to 25,000 characters
            capped_content = content[:25000]

            return FetchedDocument(
                url=url,
                status="SUCCESS",
                raw_content=capped_content,
                backend_id=self.backend_id,
                raw_metadata={
                    "pageid": page_data.get("pageid"),
                    "title": title,
                    "description": description,
                    "wordcount": len(capped_content.split()),
                    "canonical_url": page_data.get("fullurl", url),
                    "revisions": page_data.get("revisions", [])[:1],
                },
            )
        except Exception as exc:
            logger.warning("[WikipediaAdapter] Acquisition error for '%s': %s", url, type(exc).__name__)
            return FetchedDocument(
                url=url,
                status="FAILED",
                failure_reason=type(exc).__name__,
                backend_id=self.backend_id,
            )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """Normalize into rich EvidenceFragment."""
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        title = document.raw_metadata.get("title") or candidate.title or "Wikipedia Article"
        canonical_url = document.raw_metadata.get("canonical_url") or candidate.url
        content = document.raw_content
        char_len = len(content)
        word_count = len(content.split())
        depth = ContentDepth.FULL_ARTICLE.value if char_len > 1500 else ContentDepth.PARTIAL_CONTENT.value

        fragment = EvidenceFragment(
            platform="wikipedia",
            channel_name="wikipedia",
            url=canonical_url,
            title=f"{title} (Encyclopedic Entry)",
            content=content,
            snippet=content[:400] + ("..." if len(content) > 400 else ""),
            author="Wikipedia Contributors",
            content_depth=depth,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            retrieval_lineage=[{
                "platform": "wikipedia",
                "backend": self.backend_id,
                "url": canonical_url,
                "title": title,
                "retrieval_mode": RetrievalMode.DIRECT_API.value,
                "pageid": document.raw_metadata.get("pageid"),
            }],
            raw_metadata={
                "source_role": "secondary",
                "source_tier": "tier_2_established",
                "source_domain": "wikipedia.org",
                "source_independence_group": "wikipedia.org",
                "char_count": char_len,
                "word_count": word_count,
                "description": document.raw_metadata.get("description", ""),
                "source_permission": {"author": "Wikipedia contributors",
                    "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                    "source_url": canonical_url, "adapted": False},
                "reference_revision": document.raw_metadata.get("revisions", []),
            },
        )
        return [fragment]
