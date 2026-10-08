"""
Aegis Protocol — Shared Social Target Resolver & Canonicalization Engine
=========================================================================
Transforms raw search results, syndication feeds, and web snippets into
validated, concrete platform-native targets (status IDs, post IDs, video IDs).
Strictly separates authentic social targets from generic mentions or search pages.
"""

import re
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

# Reserved paths on X / Twitter that do not represent profiles
TWITTER_RESERVED = {
    "about", "explore", "hashtag", "help", "home", "i", "intent",
    "jobs", "login", "logout", "messages", "notifications", "privacy",
    "search", "settings", "share", "tos", "widgets", "x", "account",
    "download", "personalization", "safety", "rules", "developer", "status"
}

# Reserved subpaths on Reddit
REDDIT_RESERVED = {
    "about", "advertising", "api", "contact", "gold", "help", "login",
    "message", "mod", "notifications", "prefs", "premium", "register",
    "rules", "search", "settings", "submit", "user", "users", "wiki", "comments"
}


@dataclass
class ResolvedSocialTarget:
    """
    Validated concrete social target ready for specialist mirror acquisition.
    """
    platform: str                             # "twitter" | "reddit" | "youtube"
    canonical_url: str
    target_type: str                          # "status" | "profile" | "post" | "comment" | "video"
    external_id: str                          # status_id, post_id, video_id, or handle
    handle: Optional[str] = None
    container: Optional[str] = None           # subreddit or channel
    parent_id: Optional[str] = None           # Parent post ID for comments
    is_concrete: bool = True
    confidence: float = 1.0
    raw_title: str = ""
    raw_snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SocialTargetResolver:
    """
    Authoritative canonicalization engine for social platform URLs.
    """

    @classmethod
    def resolve_url_or_text(
        cls,
        url_or_text: str,
        platform_hint: Optional[str] = None
    ) -> Optional[ResolvedSocialTarget]:
        """
        Inspect a URL or snippet text and extract a concrete social target if valid.
        """
        if not url_or_text or not isinstance(url_or_text, str):
            return None

        clean_str = url_or_text.strip()

        # Unwrap markdown links: [title](https://...)
        md_match = re.search(r"\((https?://[^\s)]+)\)", clean_str)
        if md_match:
            clean_str = md_match.group(1)

        # 1. Check YouTube
        if platform_hint == "youtube" or "youtube.com" in clean_str or "youtu.be" in clean_str:
            yt_target = cls.resolve_youtube(clean_str)
            if yt_target:
                return yt_target

        # 2. Check X / Twitter
        if platform_hint in ("twitter", "x") or "x.com" in clean_str or "twitter.com" in clean_str:
            x_target = cls.resolve_twitter(clean_str)
            if x_target:
                return x_target

        # 3. Check Reddit
        if platform_hint == "reddit" or "reddit.com" in clean_str or "redd.it" in clean_str:
            reddit_target = cls.resolve_reddit(clean_str)
            if reddit_target:
                return reddit_target

        return None

    @classmethod
    def resolve_twitter(cls, text: str) -> Optional[ResolvedSocialTarget]:
        """
        Extract canonical X/Twitter status or profile from URL or snippet text.
        """
        # Look for status URL pattern: (x.com|twitter.com)/(handle|i)/status/<digits>
        status_match = re.search(
            r"https?://(?:www\.)?(?:x|twitter)\.com/(?:([a-zA-Z0-9_]{1,25})|i)/status/(\d+)",
            text,
            re.IGNORECASE
        )
        if status_match:
            handle = status_match.group(1)
            clean_handle = handle if handle and handle.lower() not in ("i", "status") else None
            sid = status_match.group(2)
            return ResolvedSocialTarget(
                platform="twitter",
                canonical_url=f"https://x.com/{clean_handle or 'i'}/status/{sid}",
                target_type="status",
                external_id=sid,
                handle=clean_handle,
                is_concrete=True,
                confidence=1.0
            )

        # Look for short status pattern: /status/<digits>
        short_status = re.search(r"https?://(?:www\.)?(?:x|twitter)\.com/status/(\d+)", text, re.IGNORECASE)
        if short_status:
            sid = short_status.group(1)
            return ResolvedSocialTarget(
                platform="twitter",
                canonical_url=f"https://x.com/i/status/{sid}",
                target_type="status",
                external_id=sid,
                handle=None,
                is_concrete=True,
                confidence=0.95
            )

        # If URL contains /status, it is an attempted tweet/status URL
        if "/status" in text.lower():
            return None

        # Look for profile URL: x.com/<handle>
        profile_match = re.search(
            r"https?://(?:www\.)?(?:x|twitter)\.com/([a-zA-Z0-9_]{1,20})(?:$|[/?#])",
            text,
            re.IGNORECASE
        )
        if profile_match:
            handle = profile_match.group(1)
            if handle.lower() not in TWITTER_RESERVED:
                return ResolvedSocialTarget(
                    platform="twitter",
                    canonical_url=f"https://x.com/{handle}",
                    target_type="profile",
                    external_id=handle,
                    handle=handle,
                    is_concrete=True,
                    confidence=0.85
                )

        return None

    @classmethod
    def resolve_reddit(cls, text: str) -> Optional[ResolvedSocialTarget]:
        """
        Extract canonical Reddit post or comment from URL or snippet text.
        """
        # Post format: reddit.com/r/<sub_name>/comments/<post_id>/...
        post_match = re.search(
            r"https?://(?:www\.|old\.)?reddit\.com/r/([a-zA-Z0-9_]+)/comments/([a-z0-9]+)(?:/[^/]+/([a-z0-9]+))?",
            text,
            re.IGNORECASE
        )
        if post_match:
            sub_name = post_match.group(1)
            pid = post_match.group(2)
            cid = post_match.group(3)
            if cid:
                return ResolvedSocialTarget(
                    platform="reddit",
                    canonical_url=f"https://www.reddit.com/r/{sub_name}/comments/{pid}/_/{cid}",
                    target_type="comment",
                    external_id=cid,
                    container=sub_name,
                    parent_id=pid,
                    is_concrete=True,
                    confidence=1.0
                )
            return ResolvedSocialTarget(
                platform="reddit",
                canonical_url=f"https://www.reddit.com/r/{sub_name}/comments/{pid}",
                target_type="post",
                external_id=pid,
                container=sub_name,
                is_concrete=True,
                confidence=1.0
            )

        # Short comments URL: reddit.com/comments/<post_id>
        comments_match = re.search(
            r"https?://(?:www\.|old\.)?reddit\.com/comments/([a-z0-9]+)",
            text,
            re.IGNORECASE
        )
        if comments_match:
            pid = comments_match.group(1)
            return ResolvedSocialTarget(
                platform="reddit",
                canonical_url=f"https://www.reddit.com/comments/{pid}",
                target_type="post",
                external_id=pid,
                is_concrete=True,
                confidence=1.0
            )

        # Short URL: redd.it/<post_id>
        short_match = re.search(r"https?://redd\.it/([a-z0-9]+)", text, re.IGNORECASE)
        if short_match:
            pid = short_match.group(1)
            return ResolvedSocialTarget(
                platform="reddit",
                canonical_url=f"https://www.reddit.com/comments/{pid}",
                target_type="post",
                external_id=pid,
                is_concrete=True,
                confidence=0.95
            )

        # Subreddit feed format: reddit.com/r/<sub_name>
        sub_match = re.search(r"https?://(?:www\.|old\.)?reddit\.com/r/([a-zA-Z0-9_]+)(?:$|[/?#])", text, re.IGNORECASE)
        if sub_match:
            sub_name = sub_match.group(1)
            if sub_name.lower() not in REDDIT_RESERVED:
                return ResolvedSocialTarget(
                    platform="reddit",
                    canonical_url=f"https://www.reddit.com/r/{sub_name}",
                    target_type="subreddit",
                    external_id=sub_name,
                    container=sub_name,
                    is_concrete=True,
                    confidence=0.85
                )

        return None

    @classmethod
    def resolve_youtube(cls, text: str) -> Optional[ResolvedSocialTarget]:
        """
        Extract canonical YouTube video ID from URL or snippet text.
        """
        # Standard: youtube.com/watch?v=<11 chars>
        watch_match = re.search(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})", text)
        if watch_match:
            vid = watch_match.group(1)
            return ResolvedSocialTarget(
                platform="youtube",
                canonical_url=f"https://www.youtube.com/watch?v={vid}",
                target_type="video",
                external_id=vid,
                is_concrete=True,
                confidence=1.0
            )

        # Short: youtu.be/<11 chars>
        short_match = re.search(r"https?://youtu\.be/([a-zA-Z0-9_-]{11})", text)
        if short_match:
            vid = short_match.group(1)
            return ResolvedSocialTarget(
                platform="youtube",
                canonical_url=f"https://www.youtube.com/watch?v={vid}",
                target_type="video",
                external_id=vid,
                is_concrete=True,
                confidence=1.0
            )

        return None


# Global singleton
social_target_resolver = SocialTargetResolver()
