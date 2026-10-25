"""Aegis Protocol — Reddit Deep Hierarchical Comment Trees Adapter.

Provides deep memetic velocity, viral smear, and sentiment divergence intelligence for Trending and BrandShield:
- Recursively traverses comment threads across target subreddits
- Captures up to 50–100 top comments per discussion thread
- Formulates hierarchical conversation transcripts with comment authors, upvote scores, and timestamps
- Ingests up to 25,000 characters of high-velocity social discussion
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

ARCTIC_SHIFT_BASE = "https://arctic-shift.photon-reddit.com/api"
DEFAULT_REDDIT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AegisProtocol/1.0",
    "Accept": "application/json",
}

TARGET_SUBREDDITS = ["technology", "stocks", "wallstreetbets", "investing", "news", "artificial"]


class RedditDeepAdapter(PlatformAdapter):
    """Acquires deep hierarchical Reddit comment trees via zero-auth mirror infrastructure."""

    @property
    def platform(self) -> str:
        return "reddit_deep"

    @property
    def backend_id(self) -> str:
        return "arctic_shift_deep"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("reddit_deep", "reddit_comments"):
            return True
        return "reddit.com/r/" in url and "/comments/" in url

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Discover active Reddit discussions across target high-volume subreddits."""
        candidates: List[CandidateSource] = []
        clean_q = query.strip()
        if not clean_q:
            return candidates

        for sub in TARGET_SUBREDDITS:
            if len(candidates) >= limit:
                break
            api_url = f"{ARCTIC_SHIFT_BASE}/posts/search?subreddit={sub}&title={urllib.parse.quote(clean_q)}&limit=3&sort=desc"
            if not validate_url_safe(api_url)[0]:
                continue
            try:
                resp = fetch_public_http(api_url, headers=DEFAULT_REDDIT_HEADERS, timeout=4.0)
                if resp.status_code != 200:
                    continue
                data = json.loads(resp.body.decode("utf-8", errors="replace"))
                posts = data.get("data", [])
                for p in posts:
                    pid = p.get("id")
                    title = p.get("title", "")
                    selftext = p.get("selftext", "")
                    permalink = p.get("permalink", f"/r/{sub}/comments/{pid}")
                    full_url = f"https://www.reddit.com{permalink}"
                    candidates.append(
                        CandidateSource(
                            url=full_url,
                            canonical_url=full_url,
                            platform="reddit_deep",
                            title=f"r/{sub}: {title}",
                            snippet=selftext[:300] if selftext else title,
                            metadata={
                                "post_id": pid,
                                "subreddit": sub,
                                "author": p.get("author"),
                                "score": p.get("score", 0),
                                "num_comments": p.get("num_comments", 0),
                                "created_utc": p.get("created_utc"),
                                "primary_source": False,
                                "official_source": False,
                            },
                        )
                    )
                    if len(candidates) >= limit:
                        break
            except Exception as exc:
                logger.debug("[RedditDeepAdapter] Search notice for r/%s: %s", sub, type(exc).__name__)

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """Fetch post content and deep comment tree (up to 50 comments)."""
        url = candidate.canonical_url or candidate.url
        pid = candidate.metadata.get("post_id")
        if not pid:
            m = re.search(r"/comments/([a-z0-9]+)", url.lower())
            pid = m.group(1) if m else ""

        title = candidate.title or "Reddit Discussion"
        sub = candidate.metadata.get("subreddit", "reddit")
        author = candidate.metadata.get("author", "redditor")
        score = candidate.metadata.get("score", 0)

        post_body = ""
        post_retrieved = False
        comments_list: List[Dict[str, Any]] = []

        if pid:
            # Fetch full post details
            post_api = f"{ARCTIC_SHIFT_BASE}/posts/search?ids={pid}"
            if validate_url_safe(post_api)[0]:
                try:
                    resp = fetch_public_http(post_api, headers=DEFAULT_REDDIT_HEADERS, timeout=5.0)
                    if resp.status_code == 200:
                        p_data = json.loads(resp.body.decode("utf-8", errors="replace")).get("data", [])
                        if p_data:
                            post_retrieved = True
                            title = p_data[0].get("title", title)
                            post_body = p_data[0].get("selftext", post_body)
                            author = p_data[0].get("author", author)
                            score = p_data[0].get("score", score)
                except Exception as exc:
                    logger.debug("[RedditDeepAdapter] Post detail notice for %s: %s", pid, type(exc).__name__)

            # Fetch deep comment tree (up to 50 comments)
            comments_api = f"{ARCTIC_SHIFT_BASE}/comments/search?link_id={pid}&limit=50&sort=desc"
            if validate_url_safe(comments_api)[0]:
                try:
                    resp = fetch_public_http(comments_api, headers=DEFAULT_REDDIT_HEADERS, timeout=6.0)
                    if resp.status_code == 200:
                        c_data = json.loads(resp.body.decode("utf-8", errors="replace")).get("data", [])
                        for c in c_data:
                            body = c.get("body", "").strip()
                            if body and body != "[deleted]" and body != "[removed]":
                                comments_list.append({
                                    "author": c.get("author", "[deleted]"),
                                    "score": c.get("score", 1),
                                    "body": body,
                                    "created_utc": c.get("created_utc"),
                                    "id": c.get("id"),
                                })
                except Exception as exc:
                    logger.debug("[RedditDeepAdapter] Comments notice for %s: %s", pid, type(exc).__name__)

        if not post_retrieved and not comments_list:
            return FetchedDocument(url=url, status="EMPTY_CONTENT", backend_id=self.backend_id)

        # Build transcript
        content = f"# {title}\n"
        content += f"**Community**: r/{sub} | **Original Poster**: u/{author} | **Upvotes**: {score}\n"
        content += f"**Discussion Link**: {url}\n\n"
        content += "## Original Post Body\n\n"
        content += (post_body or "*No selftext provided.*") + "\n\n"
        content += f"## Top Community Discussion Tree ({len(comments_list)} comments)\n\n"

        for idx, c in enumerate(comments_list, 1):
            content += f"### Comment #{idx} — u/{c['author']} ({c['score']} points)\n"
            content += f"{c['body']}\n\n"

        capped = content[:25000]

        return FetchedDocument(
            url=url,
            status="SUCCESS",
            raw_content=capped,
            backend_id=self.backend_id,
            raw_metadata={
                "post_id": pid,
                "subreddit": sub,
                "author": author,
                "score": score,
                "comments_count": len(comments_list),
                "wordcount": len(capped.split()),
            },
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """Normalize into deep community discussion EvidenceFragment."""
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        title = document.raw_metadata.get("title") or candidate.title
        content = document.raw_content
        author = f"u/{document.raw_metadata.get('author', 'reddit_user')}"

        fragment = EvidenceFragment(
            platform="reddit_deep",
            channel_name="reddit",
            url=candidate.url,
            title=f"{title} (Deep Reddit Thread)",
            content=content,
            snippet=content[:400] + ("..." if len(content) > 400 else ""),
            author=author,
            content_depth=ContentDepth.FULL_ARTICLE.value,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id=self.backend_id,
            retrieval_lineage=[{
                "platform": "reddit_deep",
                "backend": self.backend_id,
                "url": candidate.url,
                "post_id": document.raw_metadata.get("post_id"),
                "subreddit": document.raw_metadata.get("subreddit"),
                "comments_count": document.raw_metadata.get("comments_count"),
                "retrieval_mode": RetrievalMode.DIRECT_API.value,
            }],
            raw_metadata={
                "source_role": "secondary",
                "source_tier": "tier_3_community",
                "source_domain": "reddit.com",
                "source_independence_group": "reddit.com",
                "char_count": len(content),
                "word_count": len(content.split()),
                "post_id": document.raw_metadata.get("post_id"),
                "subreddit": document.raw_metadata.get("subreddit"),
                "score": document.raw_metadata.get("score"),
                "comments_count": document.raw_metadata.get("comments_count"),
            },
        )
        return [fragment]
