"""
Aegis Protocol — Native Agent Reach Evidence Normalizer
=======================================================
Transforms raw outputs from upstream tools (gh CLI, yt-dlp, Jina, V2EX, Bilibili, RSS)
into strongly typed Aegis EvidenceFragment and EvidenceItem objects with full provenance.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode


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
                retrieval_mode=RetrievalMode.NATIVE_TOOL_CLI.value,
                native_backend_id="gh-cli",
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
                retrieval_mode=RetrievalMode.NATIVE_TOOL_CLI.value,
                native_backend_id="yt-dlp",
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
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id="v2ex-public-api",
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
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id="bilibili-search-api",
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
                retrieval_mode=RetrievalMode.RSS_FEED.value,
                native_backend_id="feedparser",
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

    @staticmethod
    def normalize_arctic_shift_posts(
        raw_posts: List[Dict[str, Any]],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize Arctic Shift Reddit submissions."""
        fragments: List[EvidenceFragment] = []
        for p in raw_posts:
            post_id = p.get("id", "")
            title = p.get("title", "") or "Reddit Post"
            selftext = p.get("selftext", "") or ""
            link_url = p.get("url", "")
            is_self = p.get("is_self", True)
            
            # If link submission without selftext, document the link target honestly
            if not selftext and link_url and not is_self:
                content = f"[Reddit Link Submission]: {title}\nTarget URL: {link_url}"
            else:
                content = selftext if selftext else title

            author_raw = p.get("author") or "[deleted]"
            author = f"u/{author_raw}" if not author_raw.startswith("u/") else author_raw
            subreddit = p.get("subreddit", "")
            score = float(p.get("score", 0))
            num_comments = int(p.get("num_comments", 0))
            created_utc = str(p.get("created_utc", ""))
            permalink = f"https://reddit.com{p.get('permalink')}" if p.get("permalink") else (link_url or f"https://reddit.com/r/{subreddit}/comments/{post_id}")

            frag = EvidenceFragment(
                platform="reddit",
                title=f"{title} (r/{subreddit})" if subreddit else title,
                content=content,
                url=permalink,
                author=author,
                published=created_utc,
                snippet=content[:300],
                score=score,
                retrieval_method="arctic_shift",
                retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
                native_backend_id="arctic_shift",
                channel_name="reddit",
                content_depth="FULL_ARTICLE" if len(content) > 300 else ("PARTIAL_CONTENT" if len(content) > 50 else "SNIPPET"),
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                requested_channel="reddit",
                actual_retrieval_channel="reddit",
                is_authenticated=False,
                raw_metadata={
                    "backend": "arctic_shift",
                    "post_id": post_id,
                    "subreddit": subreddit,
                    "score": score,
                    "num_comments": num_comments,
                    "link_url": link_url,
                    "source_tier": "SPECIALIST_MIRROR",
                    "mirror_backend": "arctic-shift",
                }
            )
            fragments.append(frag)
        return fragments

    @staticmethod
    def normalize_arctic_shift_comments(
        raw_comments: List[Dict[str, Any]],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize Arctic Shift Reddit comments."""
        fragments: List[EvidenceFragment] = []
        for c in raw_comments:
            cid = c.get("id", "")
            body = c.get("body", "") or ""
            author_raw = c.get("author") or "[deleted]"
            author = f"u/{author_raw}" if not author_raw.startswith("u/") else author_raw
            link_id = str(c.get("link_id", "")).replace("t3_", "")
            subreddit = c.get("subreddit", "")
            score = float(c.get("score", 0))
            created_utc = str(c.get("created_utc", ""))
            permalink = f"https://reddit.com/comments/{link_id}/_/{cid}" if link_id else ""

            frag = EvidenceFragment(
                platform="reddit",
                title=f"Comment by {author} on Reddit post {link_id}",
                content=body,
                url=permalink,
                author=author,
                published=created_utc,
                snippet=body[:300],
                score=score,
                retrieval_method="arctic_shift",
                retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
                native_backend_id="arctic_shift",
                channel_name="reddit",
                content_depth="FULL_ARTICLE" if len(body) > 300 else "SNIPPET",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                requested_channel="reddit",
                actual_retrieval_channel="reddit",
                is_authenticated=False,
                raw_metadata={
                    "backend": "arctic_shift",
                    "comment_id": cid,
                    "link_id": link_id,
                    "parent_id": c.get("parent_id", ""),
                    "subreddit": subreddit,
                    "score": score,
                    "source_tier": "SPECIALIST_MIRROR",
                }
            )
            fragments.append(frag)
        return fragments

    @staticmethod
    def normalize_fxtwitter_tweet(
        tw: Dict[str, Any],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> Optional[EvidenceFragment]:
        """Normalize FxTwitter public status JSON object."""
        if not tw:
            return None
        author_obj = tw.get("author", {})
        screen_name = author_obj.get("screen_name", "") or "user"
        name = author_obj.get("name", "") or screen_name
        author = f"@{screen_name}"
        text = tw.get("text", "") or ""
        tid = tw.get("id", "")
        url = tw.get("url") or f"https://x.com/{screen_name}/status/{tid}"
        created = str(tw.get("created_at") or tw.get("created_timestamp") or "")

        likes = tw.get("likes", 0)
        retweets = tw.get("retweets", 0)
        replies = tw.get("replies", 0)
        views = tw.get("views")
        media_list = [m.get("url") for m in tw.get("media", {}).get("all", []) if m.get("url")]

        return EvidenceFragment(
            platform="twitter",
            title=f"Post by {name} ({author})",
            content=text,
            url=url,
            author=author,
            published=created,
            snippet=text[:300],
            score=float(likes),
            retrieval_method="fxtwitter",
            retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
            native_backend_id="fxtwitter",
            channel_name="twitter",
            content_depth="FULL_ARTICLE" if len(text) > 0 else "SNIPPET",
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            requested_channel="twitter",
            actual_retrieval_channel="twitter",
            is_authenticated=False,
            raw_metadata={
                "backend": "fxtwitter",
                "tweet_id": tid,
                "likes": likes,
                "retweets": retweets,
                "replies": replies,
                "views": views,
                "media_urls": media_list,
                "source_tier": "SPECIALIST_MIRROR",
                "mirror_backend": "fxtwitter",
            }
        )

    @staticmethod
    def normalize_fxtwitter_profile(
        u: Dict[str, Any],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> Optional[EvidenceFragment]:
        """Normalize FxTwitter public profile JSON object."""
        if not u:
            return None
        screen_name = u.get("screen_name", "") or "user"
        name = u.get("name", "") or screen_name
        author = f"@{screen_name}"
        desc = u.get("description", "") or f"Public profile of {author}"
        url = f"https://x.com/{screen_name}"
        joined = str(u.get("joined", ""))
        followers = u.get("followers", 0)
        tweets_count = u.get("tweets", 0)

        return EvidenceFragment(
            platform="twitter",
            title=f"Profile: {name} ({author})",
            content=desc,
            url=url,
            author=author,
            published=joined,
            snippet=desc[:300],
            score=float(followers),
            retrieval_method="fxtwitter",
            retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
            native_backend_id="fxtwitter",
            channel_name="twitter",
            content_depth="PARTIAL_CONTENT",
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            requested_channel="twitter",
            actual_retrieval_channel="twitter",
            is_authenticated=False,
            raw_metadata={
                "backend": "fxtwitter",
                "screen_name": screen_name,
                "followers": followers,
                "tweets_count": tweets_count,
                "source_tier": "SPECIALIST_MIRROR",
                "mirror_backend": "fxtwitter",
            }
        )


# Global singleton instance
native_normalizer = NativeNormalizer()
