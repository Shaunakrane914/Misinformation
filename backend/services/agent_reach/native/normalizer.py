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


def _extract_text_links(text: str, max_links: int = 5, tag: str = "UNVERIFIED_REFERENCED_LINK") -> List[Dict[str, str]]:
    """Extract bounded external URLs observed within text bodies."""
    if not text:
        return []
    found = re.findall(r'https?://[^\s)\]>"\'\\]+', text)
    links: List[Dict[str, str]] = []
    seen = set()
    for link in found:
        clean_link = link.rstrip(".,;:!?")
        if clean_link not in seen and len(clean_link) <= 500:
            seen.add(clean_link)
            links.append({"url": clean_link, "verification": tag})
            if len(links) >= max_links:
                break
    return links


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
            desc = repo.get("description") or ""
            url = repo.get("url", "")
            stars_val = repo.get("stargazers")
            if isinstance(stars_val, dict):
                stars = stars_val.get("totalCount")
            else:
                stars = repo.get("stargazerCount")
                if stars is None:
                    stars = repo.get("stargazersCount")
            updated = repo.get("updatedAt", "")

            content = "\n".join(part for part in (
                f"GitHub Repository: {full_name}" if full_name else "",
                f"Description: {desc}" if desc else "",
                f"Stars: {stars}" if stars is not None else "",
                f"Updated: {updated}" if updated else "",
            ) if part)
            frag = EvidenceFragment(
                platform="GitHub",
                title=full_name,
                content=content,
                url=url,
                author="",
                published="",
                snippet=desc[:300],
                score=float(min(stars, 100)) if isinstance(stars, (int, float)) else 0.0,
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
                    "updated_at": updated or None,
                    "owner_login": full_name.split("/")[0] if "/" in full_name else None,
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
            uploader = v.get("uploader") or v.get("channel") or ""
            url = v.get("webpage_url") or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
            view_count = v.get("view_count")

            snippet = desc[:300] if desc else title[:300]
            content = "\n\n".join(part for part in (
                title,
                f"Uploader: {uploader}" if uploader else "",
                f"Views: {view_count:,}" if isinstance(view_count, int) else "",
                desc[:1000],
            ) if part)
            frag = EvidenceFragment(
                platform="YouTube",
                title=title,
                content=content,
                url=url,
                author=uploader,
                published=v.get("upload_date") or "",
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
            member = (t.get("member") or {}).get("username") or ""
            url = t.get("url") or (f"https://www.v2ex.com/t/{tid}" if tid is not None else "")
            replies = t.get("replies")

            frag = EvidenceFragment(
                platform="V2EX",
                title=title,
                content="\n\n".join(part for part in (title, content) if part),
                url=url,
                author=member,
                published=str(t.get("created")) if t.get("created") is not None else "",
                snippet=content[:300] if content else title,
                score=40.0 + min(replies, 40) if isinstance(replies, int) and replies >= 0 else 40.0,
                retrieval_method="v2ex_public_api",
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id="v2ex-public-api",
                channel_name="v2ex",
                content_depth="PARTIAL_CONTENT" if content else "METADATA",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                raw_metadata={
                    "backend": "V2EX API (public)",
                    "topic_id": tid,
                    "replies": replies,
                    "node": (t.get("node") or {}).get("title"),
                    "node_name": (t.get("node") or {}).get("name"),
                    "created": t.get("created"),
                    "last_modified": t.get("last_modified"),
                    "last_touched": t.get("last_touched"),
                    "last_reply_by": t.get("last_reply_by"),
                    "deleted": t.get("deleted"),
                    "observed_links": _extract_text_links(content, max_links=5, tag="UNVERIFIED_TOPIC_LINK"),
                }
            )
            fragments.append(frag)
        return fragments

    @staticmethod
    def normalize_v2ex_replies(
        raw_items: List[Dict[str, Any]],
        topic_id: str,
        query_id: str = "",
        query_class: str = "",
        query_text: str = "",
    ) -> List[EvidenceFragment]:
        """Keep reply IDs distinct from topic IDs and preserve observed chronology."""
        fragments: List[EvidenceFragment] = []
        indexed = list(enumerate(raw_items))
        indexed.sort(key=lambda pair: (
            pair[1].get("created") is None,
            pair[1].get("created") if isinstance(pair[1].get("created"), (int, float)) else float("inf"),
            pair[0],
        ))
        for _index, reply in indexed:
            body = reply.get("content") or ""
            author = (reply.get("member") or {}).get("username") or ""
            fragments.append(EvidenceFragment(
                platform="V2EX", title=f"Reply in topic {topic_id}", content=body,
                url=f"https://www.v2ex.com/t/{topic_id}", author=author,
                published=str(reply.get("created")) if reply.get("created") is not None else "",
                snippet=body[:300], score=40.0,
                retrieval_method="v2ex_public_api", retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id="v2ex-public-api", channel_name="v2ex", content_depth="COMMENT",
                query_id=query_id, query_class=query_class, query_text=query_text,
                raw_metadata={
                    "backend": "V2EX API (public)", "topic_id": topic_id,
                    "reply_id": reply.get("id"), "last_modified": reply.get("last_modified"),
                    "thanks": reply.get("thanks"),
                    "observed_links": _extract_text_links(body, max_links=5, tag="UNVERIFIED_REPLY_LINK"),
                },
            ))
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
            feed_content = _clean_html_text(e.get("feed_content", ""))
            excerpt = feed_content or summary

            frag = EvidenceFragment(
                platform="PR Wire / RSS",
                title=title,
                content="\n\n".join(part for part in (title, excerpt) if part),
                url=link,
                author=e.get("author") or "",
                published=published,
                snippet=excerpt[:300],
                score=60.0,
                retrieval_method="feedparser",
                retrieval_mode=RetrievalMode.RSS_FEED.value,
                native_backend_id="feedparser",
                channel_name=channel_name,
                content_depth=("FEED_ENTRY_CONTENT" if feed_content else
                               "FEED_ENTRY_SUMMARY" if summary else "METADATA"),
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                raw_metadata={
                    "backend": "feedparser",
                    "feed_title": e.get("feed_title"),
                    "feed_publisher": e.get("feed_publisher"),
                    "guid": e.get("guid"),
                    "updated": e.get("updated"),
                    "categories": e.get("categories", []),
                    "enclosures": e.get("enclosures", []),
                    "summary": summary,
                    "feed_content_present": bool(feed_content),
                    "linked_article_retrieved": False,
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
        content_parts = [text]

        # Extract Quoted Tweet if present
        quote = tw.get("quote") or {}
        if quote and isinstance(quote, dict):
            q_author_obj = quote.get("author", {})
            q_handle = q_author_obj.get("screen_name", "") or "user"
            q_text = quote.get("text", "")
            if q_text:
                content_parts.append(f"\n\n[Quoted Tweet from @{q_handle}]:\n{q_text}")

        # Extract Community Note / Fact-Check context if present
        comm_note = tw.get("community_note") or {}
        if comm_note and isinstance(comm_note, dict):
            cn_text = comm_note.get("text") or comm_note.get("raw_text", {}).get("text", "")
            if cn_text:
                content_parts.append(f"\n\n[Community Note / Fact Check]:\n{cn_text}")

        full_content = "".join(content_parts)
        tid = tw.get("id", "")
        url = tw.get("url") or f"https://x.com/{screen_name}/status/{tid}"
        created = str(tw.get("created_at") or tw.get("created_timestamp") or "")

        likes = tw.get("likes")
        retweets = tw.get("retweets")
        replies = tw.get("replies")
        views = tw.get("views")
        media_list = [m.get("url") for m in tw.get("media", {}).get("all", []) if m.get("url")]

        raw_meta = {
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
        if quote and isinstance(quote, dict):
            raw_meta["has_quote"] = True
            raw_meta["quote_text"] = quote.get("text")
        if comm_note and isinstance(comm_note, dict):
            raw_meta["has_community_note"] = True
            raw_meta["community_note"] = comm_note.get("text") or comm_note.get("raw_text", {}).get("text")

        return EvidenceFragment(
            platform="twitter",
            title=f"Post by {name} ({author})",
            content=full_content,
            url=url,
            author=author,
            published=created,
            snippet=full_content[:300],
            score=float(likes) if isinstance(likes, (int, float)) and not isinstance(likes, bool) else 0.0,
            retrieval_method="fxtwitter",
            retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
            native_backend_id="fxtwitter",
            channel_name="twitter",
            content_depth="TWEET_STATUS" if full_content else "METADATA",
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            requested_channel="twitter",
            actual_retrieval_channel="twitter",
            is_authenticated=False,
            raw_metadata=raw_meta,
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
        screen_name = u.get("screen_name") or ""
        if not isinstance(screen_name, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,15}", screen_name):
            return None
        name = u.get("name", "") or screen_name
        author = f"@{screen_name}"
        desc = u.get("description") or ""
        url = f"https://x.com/{screen_name}"
        joined = str(u.get("joined", ""))
        followers = u.get("followers")
        tweets_count = u.get("tweets")

        return EvidenceFragment(
            platform="twitter",
            title=f"Profile: {name} ({author})",
            content=desc,
            url=url,
            author=author,
            # Account creation is not a publication date for this observation.
            published="",
            snippet=desc[:300],
            score=float(followers) if isinstance(followers, (int, float)) and not isinstance(followers, bool) else 0.0,
            retrieval_method="fxtwitter",
            retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value,
            native_backend_id="fxtwitter",
            channel_name="twitter",
            content_depth="PROFILE_METADATA",
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            requested_channel="twitter",
            actual_retrieval_channel="twitter",
            is_authenticated=False,
            raw_metadata={
                "backend": "fxtwitter",
                "screen_name": screen_name,
                "account_created_at": joined or None,
                "followers": followers,
                "tweets_count": tweets_count,
                "source_tier": "SPECIALIST_MIRROR",
                "mirror_backend": "fxtwitter",
            }
        )

    @staticmethod
    def normalize_xueqiu_items(
        raw_items: List[Dict[str, Any]],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize Xueqiu quotes, searches, and discussions from visitor session API."""
        fragments: List[EvidenceFragment] = []
        for item in raw_items:
            item_type = item.get("type", "quote")
            if item_type == "quote":
                symbol = item.get("symbol", "")
                name = item.get("name", "")
                curr = item.get("current", 0)
                pct = item.get("percent", 0)
                title = f"雪球行情: {name} ({symbol}) - {curr} ({pct}%)"
                content = (
                    f"股票代码: {symbol}\n名称: {name}\n当前价格: {curr}\n"
                    f"今日涨跌幅: {pct}%\n最高: {item.get('high')}\n最低: {item.get('low')}\n"
                    f"成交量: {item.get('volume')}"
                )
                depth = "FULL_ARTICLE"
            elif item_type == "stock_search":
                symbol = item.get("symbol", "")
                name = item.get("name", "")
                title = f"雪球标的匹配: {name} ({symbol})"
                content = f"搜索匹配股票: {name} (代码: {symbol})"
                depth = "SNIPPET"
            else:
                title = item.get("title") or "雪球社区讨论"
                content = item.get("text") or title
                depth = "FULL_ARTICLE" if len(content) > 200 else "SNIPPET"

            frag = EvidenceFragment(
                platform="Xueqiu",
                title=title,
                content=content,
                url=item.get("url") or "https://xueqiu.com",
                author=item.get("author") or "雪球行情",
                published="Live / Recent",
                snippet=content[:300],
                score=75.0,
                retrieval_method="xueqiu_visitor_api",
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id="xueqiu-visitor-api",
                channel_name="xueqiu",
                content_depth=depth,
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                requested_channel="xueqiu",
                actual_retrieval_channel="xueqiu",
                is_authenticated=False,
                raw_metadata={
                    "backend": "xueqiu-visitor-api",
                    "item_type": item_type,
                    "symbol": item.get("symbol"),
                    "source_tier": "SPECIALIST_API",
                }
            )
            fragments.append(frag)
        return fragments

    @staticmethod
    def normalize_xiaoyuzhou_episodes(
        raw_items: List[Dict[str, Any]],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize official public Xiaoyuzhou podcast and episode metadata."""
        fragments: List[EvidenceFragment] = []
        for ep in raw_items:
            podcast = ep.get("podcast") or ""
            title = ep.get("title") or ""
            published = ep.get("published") or ""
            audio_url = ep.get("audio_url") or ""
            summary = ep.get("summary") or ""
            item_type = ep.get("item_type", "episode")

            content = "\n".join(part for part in (
                f"Podcast: {podcast}" if podcast else "",
                f"Episode: {title}" if title else "",
                f"Published: {published}" if published else "",
                f"Audio URL: {audio_url}" if audio_url else "",
                f"Description: {summary}" if summary else "",
            ) if part)
            frag = EvidenceFragment(
                platform="Xiaoyuzhou",
                title=f"[{podcast}] {title}" if podcast and title else title or podcast,
                content=content,
                url=ep.get("link") or audio_url or "",
                author=podcast,
                published=published,
                snippet=summary[:300] if summary else title,
                score=70.0,
                retrieval_method="xiaoyuzhou_public_web",
                retrieval_mode=RetrievalMode.WEB_READER.value,
                native_backend_id="xiaoyuzhou-public-web",
                channel_name="xiaoyuzhou",
                content_depth="PARTIAL_CONTENT" if item_type == "episode" and summary else "METADATA",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                requested_channel="xiaoyuzhou",
                actual_retrieval_channel="xiaoyuzhou",
                is_authenticated=False,
                raw_metadata={
                    "backend": "xiaoyuzhou-public-web",
                    "item_type": item_type,
                    "podcast": podcast,
                    "audio_url": audio_url,
                    "has_audio": bool(audio_url),
                    "transcript_available": bool(ep.get("transcript_available")),
                    "duration": ep.get("duration"),
                    "play_count": ep.get("play_count"),
                    "comment_count": ep.get("comment_count"),
                    "episode_count": ep.get("episode_count"),
                    "subscription_count": ep.get("subscription_count"),
                    "source_contract": ep.get("source_contract"),
                    "source_tier": "SPECIALIST_PUBLIC_WEB",
                    "observed_links": _extract_text_links(summary, max_links=5, tag="UNVERIFIED_SHOW_NOTES_LINK"),
                }
            )
            fragments.append(frag)
        return fragments

    @staticmethod
    def normalize_linkedin_jobs(
        raw_items: List[Dict[str, Any]],
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize LinkedIn public guest job postings."""
        fragments: List[EvidenceFragment] = []
        for j in raw_items:
            title = j.get("title", "Job Posting")
            company = j.get("company", "Company")
            location = j.get("location", "Location")
            url = j.get("url", "https://www.linkedin.com/jobs")

            content = f"Job Title: {title}\nCompany: {company}\nLocation: {location}\nListing URL: {url}"
            frag = EvidenceFragment(
                platform="LinkedIn",
                title=f"{title} at {company} ({location})",
                content=content,
                url=url,
                author=company,
                published="Recent",
                snippet=f"{title} - {company} ({location})",
                score=65.0,
                retrieval_method="linkedin_guest_jobs_api",
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id="linkedin-guest-jobs-api",
                channel_name="linkedin",
                content_depth="SNIPPET",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                requested_channel="linkedin",
                actual_retrieval_channel="linkedin",
                is_authenticated=False,
                raw_metadata={
                    "backend": "linkedin-guest-jobs-api",
                    "company": company,
                    "location": location,
                    "source_tier": "SPECIALIST_API",
                }
            )
            fragments.append(frag)
        return fragments

    @staticmethod
    def normalize_youtube_comments(
        raw_items: List[Dict[str, Any]],
        video_url: str = "",
        query_id: str = "",
        query_class: str = "",
        query_text: str = ""
    ) -> List[EvidenceFragment]:
        """Normalize YouTube video comments extracted via yt-dlp."""
        fragments: List[EvidenceFragment] = []
        for c in raw_items:
            author = c.get("author") or ""
            text = c.get("text") or ""
            likes = c.get("like_count")
            cid = c.get("id") or ""
            timestamp = c.get("timestamp")
            try:
                published = datetime.fromtimestamp(
                    float(timestamp), tz=timezone.utc
                ).isoformat() if timestamp is not None else ""
            except (TypeError, ValueError, OverflowError, OSError):
                published = ""

            frag = EvidenceFragment(
                platform="YouTube",
                title=f"Comment by {author}" if author else "",
                content=text,
                url=video_url,
                author=author,
                published=published,
                snippet=text[:300],
                score=40.0 + min(likes, 50) if isinstance(likes, (int, float)) else 40.0,
                retrieval_method="yt_dlp_comments",
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id="yt-dlp",
                channel_name="youtube",
                content_depth="COMMENT",
                query_id=query_id,
                query_class=query_class,
                query_text=query_text,
                requested_channel="youtube",
                actual_retrieval_channel="youtube",
                is_authenticated=False,
                raw_metadata={
                    "backend": "yt-dlp",
                    "comment_id": cid,
                    "likes": likes,
                    "source_timestamp": timestamp,
                }
            )
            fragments.append(frag)
        return fragments


# Global singleton instance
native_normalizer = NativeNormalizer()
