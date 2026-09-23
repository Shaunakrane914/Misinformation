"""
Aegis Protocol — Native Agent Reach Evidence Normalizer
=======================================================
Transforms raw outputs from upstream tools (gh CLI, yt-dlp, Jina, V2EX, Bilibili, RSS)
into strongly typed Aegis EvidenceFragment and EvidenceItem objects with full provenance.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.agent_reach.channels import EvidenceFragment


def _clean_html_text(text: str) -> str:
    """Strip tags and decode entities for clean plain text snippets."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    return " ".join(clean.split()).strip()


class NativeNormalizer:
    """Normalizes raw upstream platform outputs into canonical evidence representations."""

    @staticmethod
    def normalize_github_repos(
        raw_items: List[Dict[str, Any]],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize gh search repos JSON items."""
        fragments: List[EvidenceFragment] = []
        for repo in raw_items:
            full_name = repo.get("nameWithOwner") or repo.get("fullName") or repo.get("name", "")
            desc = repo.get("description") or "No description provided."
            url = repo.get("url", "")
            stars_val = repo.get("stargazers")
            if isinstance(stars_val, dict):
                stars = stars_val.get("totalCount", 0)
            else:
                stars = repo.get("stargazerCount") or repo.get("stargazersCount") or 0
            updated = repo.get("updatedAt", "")

            content = f"GitHub Repository: {full_name}\nDescription: {desc}\nStars: {stars} | Updated: {updated}"
            frag = EvidenceFragment(
                platform="GitHub",
                title=f"{full_name} ({stars} stars)" if stars else full_name,
                content=content,
                url=url,
                author=full_name.split("/")[0] if "/" in full_name else "GitHub",
                published=updated,
                snippet=desc[:300],
                score=float(min(stars, 100)),
                retrieval_method="gh_cli",
                channel_name="github",
                content_depth="SNIPPET",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                raw_metadata={
                    "backend": "gh CLI",
                    "stars": stars,
                    "full_name": full_name,
                }
            )
            fragments.append(frag)
        return fragments

    @classmethod
    def normalize_youtube_video(
        cls,
        video: Dict[str, Any],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> EvidenceFragment:
        """Normalize a single yt-dlp video item."""
        frags = cls.normalize_youtube_search([video], query_id=query_id, query_class=query_class, query_text=query_text)
        return frags[0] if frags else EvidenceFragment(platform="YouTube", title="")

    @staticmethod
    def normalize_youtube_search(
        raw_items: List[Dict[str, Any]],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize yt-dlp dump-json video items."""
        fragments: List[EvidenceFragment] = []
        for v in raw_items:
            vid = v.get("id", "")
            title = v.get("title", "")
            desc = v.get("description") or ""
            uploader = v.get("uploader") or v.get("channel") or "YouTube"
            url = v.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}"
            view_count = v.get("view_count") or 0

            snippet = desc[:300] if desc else f"Video by {uploader} with {view_count:,} views"
            frag = EvidenceFragment(
                platform="YouTube",
                title=title,
                content=f"{title}\n\nUploader: {uploader}\nViews: {view_count:,}\n\n{desc[:1000]}",
                url=url,
                author=uploader,
                published=v.get("upload_date") or "Recent",
                snippet=snippet,
                score=50.0,
                retrieval_method="yt_dlp",
                channel_name="youtube",
                content_depth="VIDEO_METADATA",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                raw_metadata={
                    "backend": "yt-dlp",
                    "video_id": vid,
                    "view_count": view_count,
                    "duration": v.get("duration"),
                }
            )
            fragments.append(frag)
        return fragments

    @staticmethod
    def normalize_v2ex_topics(
        raw_items: List[Dict[str, Any]],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize V2EX API topic JSON objects."""
        fragments: List[EvidenceFragment] = []
        for t in raw_items:
            tid = t.get("id")
            title = t.get("title", "")
            content = t.get("content") or ""
            member = t.get("member", {}).get("username", "V2EX User")
            url = t.get("url") or f"https://www.v2ex.com/t/{tid}"
            replies = t.get("replies", 0)

            frag = EvidenceFragment(
                platform="V2EX",
                title=title,
                content=f"{title}\n\nAuthor: @{member} | Replies: {replies}\n\n{content}",
                url=url,
                author=member,
                published=str(t.get("created", "")),
                snippet=content[:300] if content else title,
                score=40.0 + min(replies, 40),
                retrieval_method="v2ex_public_api",
                channel_name="v2ex",
                content_depth="FULL_ARTICLE" if len(content) > 300 else "SNIPPET",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                raw_metadata={
                    "backend": "V2EX API (public)",
                    "topic_id": tid,
                    "replies": replies,
                    "node": t.get("node", {}).get("title"),
                }
            )
            fragments.append(frag)
        return fragments

    @staticmethod
    def normalize_bilibili_videos(
        raw_items: List[Dict[str, Any]],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize Bilibili public search video results."""
        fragments: List[EvidenceFragment] = []
        for v in raw_items:
            title = _clean_html_text(v.get("title", ""))
            author = v.get("author", "UP主")
            bvid = v.get("bvid", "")
            arcurl = v.get("arcurl") or f"https://www.bilibili.com/video/{bvid}"
            desc = v.get("description", "")
            play = v.get("play", 0)

            frag = EvidenceFragment(
                platform="Bilibili",
                title=title,
                content=f"{title}\n\nUP主: {author} | 播放: {play}\n\n{desc}",
                url=arcurl,
                author=author,
                published="Recent",
                snippet=desc[:300] if desc else f"Bilibili video by {author}",
                score=45.0,
                retrieval_method="bilibili_search_api",
                channel_name="bilibili",
                content_depth="VIDEO_METADATA",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                raw_metadata={
                    "backend": "B站搜索 API",
                    "bvid": bvid,
                    "play_count": play,
                }
            )
            fragments.append(frag)
        return fragments

    @staticmethod
    def normalize_rss_entries(
        raw_items: List[Dict[str, Any]],
        channel_name: str = "rss",
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize feedparser RSS/Atom entries."""
        fragments: List[EvidenceFragment] = []
        for e in raw_items:
            title = e.get("title", "")
            link = e.get("link", "")
            published = e.get("published", "")
            summary = _clean_html_text(e.get("summary", ""))

            frag = EvidenceFragment(
                platform="PR Wire / RSS",
                title=title,
                content=f"{title}\n\n{summary}",
                url=link,
                author="RSS Wire",
                published=published,
                snippet=summary[:300],
                score=60.0,
                retrieval_method="feedparser",
                channel_name=channel_name,
                content_depth="SNIPPET",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                raw_metadata={
                    "backend": "feedparser",
                }
            )
            fragments.append(frag)
        return fragments


# Global singleton instance
native_normalizer = NativeNormalizer()
