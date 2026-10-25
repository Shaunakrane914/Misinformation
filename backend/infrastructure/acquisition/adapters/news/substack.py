"""Aegis Protocol — Substack Investigative Newsletters Adapter.

Provides independent investigative analysis and deep-dive domain journalism:
- Independent financial analysts, investigative tech journalists, and industry whistleblowers
- Publication metadata, author bylines, subtitles, and long-form analytical bodies
- Ingests up to 25,000 characters per investigative piece
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

DEFAULT_SUBSTACK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html",
}

# Known high-frequency tech/finance investigative Substacks
NOTABLE_SUBSTACKS = [
    "thediff", "stratechery", "doomberg", "pragmaticengineer",
    "semianalysis", "piratewires", "chinatalk", "astralcodexten",
]


class SubstackAdapter(PlatformAdapter):
    """Acquires long-form investigative analysis from Substack publications."""

    @property
    def platform(self) -> str:
        return "substack"

    @property
    def backend_id(self) -> str:
        return "substack_reader"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("substack", "newsletters"):
            return True
        return ".substack.com" in url or "substack.com/@" in url

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Discover recent investigative posts across target publications."""
        candidates: List[CandidateSource] = []
        clean_q = query.lower().strip()
        if not clean_q:
            return candidates

        # Check notable publications for relevant posts
        for pub in NOTABLE_SUBSTACKS:
            if len(candidates) >= limit:
                break
            api_url = f"https://{pub}.substack.com/api/v1/posts?limit=5&sort=top"
            if not validate_url_safe(api_url)[0]:
                continue
            try:
                resp = fetch_public_http(api_url, headers=DEFAULT_SUBSTACK_HEADERS, timeout=4.0)
                if resp.status_code != 200:
                    continue
                posts = json.loads(resp.body.decode("utf-8", errors="replace"))
                if not isinstance(posts, list):
                    continue

                for p in posts:
                    title = p.get("title", "")
                    subtitle = p.get("subtitle", "")
                    post_url = p.get("canonical_url") or f"https://{pub}.substack.com/p/{p.get('slug', '')}"
                    text_match = clean_q in title.lower() or clean_q in subtitle.lower()

                    if text_match or (set(re.findall(r"\w{3,}", clean_q)) and set(re.findall(r"\w{3,}", clean_q)) <= set(re.findall(r"\w{3,}", (title + " " + subtitle).casefold()))):
                        candidates.append(
                            CandidateSource(
                                url=post_url,
                                canonical_url=post_url,
                                platform="substack",
                                title=f"{title} — {pub}.substack.com",
                                snippet=subtitle or title,
                                metadata={
                                    "publication": pub,
                                    "slug": p.get("slug"),
                                    "post_date": p.get("post_date"),
                                    "subtitle": subtitle,
                                    "audience": p.get("audience"),
                                    "primary_source": False,
                                    "official_source": False,
                                },
                            )
                        )
                        if len(candidates) >= limit:
                            break
            except Exception as exc:
                logger.debug("[SubstackAdapter] Discovery notice for pub %s: %s", pub, type(exc).__name__)

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """Fetch and extract clean long-form newsletter article body."""
        url = candidate.canonical_url or candidate.url
        if not validate_url_safe(url)[0]:
            return FetchedDocument(url=url, status="BLOCKED_SSRF", failure_reason="Substack URL failed SSRF check", backend_id=self.backend_id)

        # Attempt to fetch post via Substack REST endpoint if slug exists
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc
        slug_match = re.search(r"/p/([^/?#]+)", parsed.path)
        slug = slug_match.group(1) if slug_match else candidate.metadata.get("slug")

        body_text = ""
        title = candidate.title or "Substack Post"
        subtitle = candidate.metadata.get("subtitle", "")
        author = ""

        if slug and "." in netloc:
            post_api = f"https://{netloc}/api/v1/posts/{slug}"
            if validate_url_safe(post_api)[0]:
                try:
                    resp = fetch_public_http(post_api, headers=DEFAULT_SUBSTACK_HEADERS, timeout=6.0)
                    if resp.status_code in {401, 403, 429}:
                        return FetchedDocument(url=url, status="ACCESS_DENIED" if resp.status_code != 429 else "RATE_LIMITED",
                            failure_reason="Provider denied the post read", backend_id=self.backend_id)
                    if resp.status_code == 200:
                        post_json = json.loads(resp.body.decode("utf-8", errors="replace"))
                        title = post_json.get("title", title)
                        subtitle = post_json.get("subtitle", subtitle)
                        body_html = post_json.get("body_html", "")
                        # Clean html
                        cleaned = re.sub(r"<(?:p|div|h[1-6]|li)[^>]*>", "\n\n", body_html, flags=re.I)
                        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
                        body_text = re.sub(r"[ \t]+", " ", cleaned).strip()
                        bylines = post_json.get("publishedBylines", [])
                        if bylines and isinstance(bylines, list):
                            author = bylines[0].get("name", "")
                except Exception as exc:
                    logger.debug("[SubstackAdapter] Post API notice for %s: %s", slug, type(exc).__name__)

        # Fallback to direct HTML scrape if API not available or empty
        if not body_text:
            try:
                resp = fetch_public_http(url, headers=DEFAULT_SUBSTACK_HEADERS, timeout=6.0, max_bytes=2_000_000)
                if resp.status_code == 200:
                    raw_html = resp.body.decode("utf-8", errors="replace")
                    cleaned = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", raw_html, flags=re.IGNORECASE)
                    cleaned = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r"<(?:p|div|h[1-6]|li)[^>]*>", "\n\n", cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
                    body_text = re.sub(r"[ \t]+", " ", cleaned).strip()
            except Exception as exc:
                return FetchedDocument(url=url, status="FAILED", failure_reason=type(exc).__name__, backend_id=self.backend_id)

        if not body_text.strip():
            return FetchedDocument(url=url, status="EMPTY_CONTENT", backend_id=self.backend_id)
        content = f"# {title}\n"
        if subtitle:
            content += f"**{subtitle}**\n\n"
        if author:
            content += f"**Author**: {author} | **Source**: {url}\n\n"
        content += body_text

        capped = content[:25000]

        return FetchedDocument(
            url=url,
            status="SUCCESS",
            raw_content=capped,
            backend_id=self.backend_id,
            raw_metadata={
                "title": title,
                "source_html": locals().get("raw_html") or locals().get("body_html") or "",
                "source_html_basis": "CAPTURED_POST_BODY_HTML" if locals().get("body_html") else "HTTP_HTML",
                "subtitle": subtitle,
                "author": author,
                "publication": netloc,
                "wordcount": len(capped.split()),
            },
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """Normalize into secondary investigative evidence fragment."""
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        title = document.raw_metadata.get("title") or candidate.title
        content = document.raw_content
        author = document.raw_metadata.get("author") or candidate.metadata.get("publication") or "Substack Author"

        fragment = EvidenceFragment(
            platform="substack",
            channel_name="substack",
            url=candidate.url,
            title=f"{title} (Substack Newsletter)",
            content=content,
            snippet=content[:400] + ("..." if len(content) > 400 else ""),
            author=author,
            content_depth=ContentDepth.FULL_ARTICLE.value,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id=self.backend_id,
            retrieval_lineage=[{
                "platform": "substack",
                "backend": self.backend_id,
                "url": candidate.url,
                "publication": document.raw_metadata.get("publication"),
                "retrieval_mode": RetrievalMode.DIRECT_API.value,
            }],
            raw_metadata={
                "source_role": "secondary",
                "source_tier": "tier_2_established",
                "source_domain": "substack.com",
                "source_independence_group": "substack.com",
                "char_count": len(content),
                "word_count": len(content.split()),
                "subtitle": document.raw_metadata.get("subtitle"),
                "publication": document.raw_metadata.get("publication"),
            },
        )
        return [fragment]
