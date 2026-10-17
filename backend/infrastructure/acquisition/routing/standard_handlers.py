"""Deterministic handlers for non-social acquisition channels."""

from __future__ import annotations

import os
import re
import urllib.parse
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode
from backend.services.agent_reach.native.errors import AuthRequiredError, NativeReachError
from backend.services.agent_reach.native.operation_capabilities import (
    required_auth_environment,
)

if TYPE_CHECKING:
    from backend.infrastructure.acquisition.routing.router import NativeRouter


class StandardChannelHandlers:
    """Own native, feed, web-search, reader, and credential-gated execution."""

    def __init__(self, router: "NativeRouter") -> None:
        self.router = router

    def execute(
        self,
        platform: str,
        query: str,
        limit: int,
        query_id: str,
        query_class: str,
        query_text: str,
        telemetry: Dict[str, Any],
        **kwargs: Any,
    ) -> List[EvidenceFragment]:
        operation = str(kwargs.get("operation", "search")).lower()
        auth_environment = required_auth_environment(platform, operation)
        if platform == "web_search":
            return self._execute_web(query, limit, query_id, query_class, query_text, telemetry, **kwargs)
        if auth_environment:
            if (
                kwargs.get("public_mode")
                or kwargs.get("allow_unauthenticated")
                or kwargs.get("prefer_public")
                or os.getenv("AEGIS_PUBLIC_ACQUISITION", "false").lower() in ("true", "1", "yes")
            ):
                handler = getattr(self, f"_execute_{platform}", None)
                if handler is not None:
                    return handler(query, limit, query_id, query_class, query_text, telemetry, **kwargs)
            return self._execute_authenticated(platform, telemetry)
        handler = getattr(self, f"_execute_{platform}", None)
        if handler is not None:
            return handler(query, limit, query_id, query_class, query_text, telemetry, **kwargs)
        return self._execute_generic(platform, query, limit, query_id, query_class, query_text, telemetry)

    def _execute_github(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        operation = str(_.get("operation", "search")).lower()
        if operation != "search":
            return self._execute_github_operation(
                operation, query, limit, query_id, query_class, query_text, telemetry,
                page=_.get("page", 1),
                include_comments=_.get("include_comments", False),
                comment_limit=_.get("comment_limit", 3),
                include_files=_.get("include_files", False),
                file_limit=_.get("file_limit", 5),
            )
        try:
            result = self.router.executor.execute_github_search(query, limit=limit)
            self._record_transport(telemetry, result)
            fragments = self.router.normalizer.normalize_github_repos(
                result.get("items", []), query_id=query_id, query_class=query_class, query_text=query_text
            )
            if not fragments:
                raise NativeReachError("Native gh CLI returned no items")
            self._attach_transport(fragments, result.get("transport"))
            self.router._tag_fragments(fragments, "github", "github", RetrievalMode.DIRECT_API.value, "gh-cli", None, True)
            telemetry["status"] = "SUCCESS"
            for fragment in fragments:
                fragment.content_depth = "METADATA"
            return fragments
        except Exception:
            fragments = self.router._fallback_github_rest(query, limit, query_id, query_class, query_text)
            self.router._tag_fragments(fragments, "github", "github", RetrievalMode.DIRECT_API.value, "GitHub REST API", "GH_CLI_UNAVAILABLE", False)
            self._fallback(telemetry, "GitHub REST API", "GH_CLI_UNAVAILABLE", RetrievalMode.DIRECT_API.value, fragments)
            return fragments

    def _execute_github_operation(
        self, operation, query, limit, query_id, query_class, query_text, telemetry,
        page=1, include_comments=False, comment_limit=3,
        include_files=False, file_limit=5,
    ):
        # Keep the default call shape compatible with existing executor shims.
        pagination_kwargs = {"page": page} if page != 1 else {}
        if include_comments:
            pagination_kwargs.update(include_comments=True, comment_limit=comment_limit)
        if include_files:
            pagination_kwargs.update(include_files=True, file_limit=file_limit)
        result = self.router.executor.execute_github_rest_operation(
            query, operation, limit=limit, **pagination_kwargs
        )
        self._record_transport(telemetry, result)
        if include_comments:
            telemetry["follow_up_requests"] = result.get("follow_up_requests", 0)
        elif include_files:
            telemetry["follow_up_requests"] = result.get("follow_up_requests", 0)
        fragments: List[EvidenceFragment] = []
        repo = result.get("repo", query)
        for item in result.get("items", []):
            detail: Dict[str, Any] = {}
            if operation == "read":
                title = item.get("full_name") or repo
                body = item.get("readme") or item.get("description") or ""
                url = item.get("html_url") or f"https://github.com/{repo}"
                # The repository owner and last update are not the author and
                # publication date of the README or repository contents.
                author = ""
                published = ""
                # A README is content from one document, not the entire repository.
                depth = "PARTIAL_CONTENT" if item.get("readme") else "METADATA"
                detail = {
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                    "pushed_at": item.get("pushed_at"),
                    "default_branch": item.get("default_branch"),
                    "license_spdx_id": (item.get("license") or {}).get("spdx_id"),
                    "open_issues_count": item.get("open_issues_count"),
                    "owner_login": (item.get("owner") or {}).get("login"),
                }
            elif operation in {"issues", "prs"}:
                title = item.get("title") or ""
                body = item.get("body") or title
                url = item.get("html_url") or ""
                author = (item.get("user") or {}).get("login") or ""
                published = item.get("created_at") or ""
                # The list body does not include comments, events or PR review.
                depth = "PARTIAL_CONTENT" if item.get("body") else "METADATA"
                detail = {
                    "number": item.get("number"),
                    "state": item.get("state"),
                    "state_reason": item.get("state_reason"),
                    "labels": [label.get("name") for label in item.get("labels", [])
                               if isinstance(label, dict) and label.get("name")],
                    "assignees": [user.get("login") for user in item.get("assignees", [])
                                  if isinstance(user, dict) and user.get("login")],
                    "comment_count": item.get("comments"),
                    "updated_at": item.get("updated_at"),
                    "closed_at": item.get("closed_at"),
                    "author_association": item.get("author_association"),
                }
                if operation == "prs":
                    file_samples = item.get("sampled_files") or []
                    observed_files = []
                    for f in file_samples:
                        fname = f.get("filename") or "unknown"
                        fstatus = f.get("status") or "changed"
                        adds = f.get("additions")
                        dels = f.get("deletions")
                        stat_str = f"+{adds}/-{dels}" if adds is not None and dels is not None else ""
                        observed_files.append(f"- {fname} ({fstatus}{', ' + stat_str if stat_str else ''})")
                    if observed_files:
                        body = body + "\n\nObserved changed files (bounded sample):\n" + "\n".join(observed_files)
                        depth = "PARTIAL_CONTENT"
                    detail.update(
                        merged_at=item.get("merged_at"), draft=item.get("draft"),
                        base_ref=(item.get("base") or {}).get("ref"),
                        head_ref=(item.get("head") or {}).get("ref"),
                        file_samples=file_samples,
                        file_lookup_status=item.get("file_lookup_status", "NOT_REQUESTED"),
                        file_transport=item.get("file_transport"),
                        file_failure_class=item.get("file_failure_class"),
                        file_http_status=item.get("file_http_status"),
                    )
                else:
                    samples = item.get("sampled_comments") or []
                    observed_bodies = []
                    for sample in samples:
                        if not sample.get("body"):
                            continue
                        attribution = "Comment"
                        if sample.get("author"):
                            attribution += f" by {sample['author']}"
                        if sample.get("created_at"):
                            attribution += f" at {sample['created_at']}"
                        if sample.get("url"):
                            attribution += f" ({sample['url']})"
                        observed_bodies.append(f"{attribution}:\n{sample['body']}")
                    if observed_bodies:
                        body = body + "\n\nObserved issue comments (bounded sample):\n" + "\n\n".join(observed_bodies)
                        depth = "PARTIAL_CONTENT"
                    detail.update(
                        comment_samples=samples,
                        comment_lookup_status=item.get("comment_lookup_status", "NOT_REQUESTED"),
                        comment_has_next_page=item.get("comment_has_next_page"),
                        comment_transport=item.get("comment_transport"),
                        comment_failure_class=item.get("comment_failure_class"),
                        comment_http_status=item.get("comment_http_status"),
                    )
            elif operation == "releases":
                title = item.get("name") or item.get("tag_name") or "GitHub release"
                body = item.get("body") or title
                url = item.get("html_url") or ""
                author = (item.get("author") or {}).get("login") or ""
                published = item.get("published_at") or ""
                depth = "PARTIAL_CONTENT" if item.get("body") else "METADATA"
                detail = {
                    "tag_name": item.get("tag_name"),
                    "target_commitish": item.get("target_commitish"),
                    "draft": item.get("draft"),
                    "prerelease": item.get("prerelease"),
                    "created_at": item.get("created_at"),
                    "published_at": item.get("published_at"),
                    "assets": [
                        {"name": asset.get("name"), "url": asset.get("browser_download_url"),
                         "size": asset.get("size"), "content_type": asset.get("content_type"),
                         "digest": asset.get("digest"), "download_count": asset.get("download_count"),
                         "created_at": asset.get("created_at"), "updated_at": asset.get("updated_at")}
                        for asset in item.get("assets", [])[:20] if isinstance(asset, dict)
                    ],
                }
            else:
                commit = item.get("commit") or {}
                title = (commit.get("message") or "").splitlines()[0] if commit.get("message") else ""
                body = commit.get("message") or title
                url = item.get("html_url") or ""
                author = ((item.get("author") or {}).get("login") or
                          (commit.get("author") or {}).get("name") or "")
                published = (commit.get("author") or {}).get("date") or ""
                depth = "METADATA"
                file_samples = item.get("sampled_files") or []
                stats = item.get("stats")
                observed_files = []
                if stats:
                    observed_files.append(f"Stats: +{stats.get('additions', 0)}/-{stats.get('deletions', 0)}")
                for f in file_samples:
                    fname = f.get("filename") or "unknown"
                    fstatus = f.get("status") or "changed"
                    adds = f.get("additions")
                    dels = f.get("deletions")
                    stat_str = f"+{adds}/-{dels}" if adds is not None and dels is not None else ""
                    observed_files.append(f"- {fname} ({fstatus}{', ' + stat_str if stat_str else ''})")
                if observed_files:
                    body = body + "\n\nObserved commit changes (bounded sample):\n" + "\n".join(observed_files)
                    depth = "PARTIAL_CONTENT"
                detail = {
                    "sha": item.get("sha"),
                    "parents": [parent.get("sha") for parent in item.get("parents", [])[:20]
                                if isinstance(parent, dict) and parent.get("sha")],
                    "commit_author_date": (commit.get("author") or {}).get("date"),
                    "commit_committer_date": (commit.get("committer") or {}).get("date"),
                    "commit_committer_name": (commit.get("committer") or {}).get("name"),
                    "verification": {
                        "verified": (commit.get("verification") or {}).get("verified"),
                        "reason": (commit.get("verification") or {}).get("reason"),
                    },
                    "stats": stats,
                    "file_samples": file_samples,
                    "file_lookup_status": item.get("file_lookup_status", "NOT_REQUESTED"),
                    "file_transport": item.get("file_transport"),
                    "file_failure_class": item.get("file_failure_class"),
                    "file_http_status": item.get("file_http_status"),
                }
            fragments.append(EvidenceFragment(
                platform="GitHub", title=title, content=body, url=url,
                author=author, published=published, snippet=body[:300], score=70.0,
                retrieval_method="github_rest", retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id="github-rest", channel_name="github",
                content_depth=depth, query_id=query_id, query_class=query_class,
                query_text=query_text,
                raw_metadata={
                    "backend": "GitHub REST API", "operation": operation,
                    "repository": repo,
                    "repository_description": item.get("description") if operation == "read" else None,
                    "stars": item.get("stargazers_count") if operation == "read" else None,
                    "forks": item.get("forks_count") if operation == "read" else None,
                    "watchers": item.get("subscribers_count") if operation == "read" else None,
                    "language": item.get("language") if operation == "read" else None,
                    "topics": item.get("topics") if operation == "read" else None,
                    "readme_path": item.get("readme_path") if operation == "read" else None,
                    "readme_sha": item.get("readme_sha") if operation == "read" else None,
                    "readme_source_url": item.get("readme_source_url") if operation == "read" else None,
                    "readme_transport": item.get("readme_transport") if operation == "read" else None,
                    "provider_fields": detail,
                    "pagination": result.get("pagination", {}),
                },
            ))
        self._attach_transport(fragments, result.get("transport"))
        self.router._tag_fragments(
            fragments, "github", "github", RetrievalMode.DIRECT_API.value,
            "GitHub REST API", None, bool(os.getenv("GITHUB_TOKEN")),
        )
        telemetry.update(status="SUCCESS", backend="GitHub REST API")
        return fragments

    def _execute_youtube(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        operation = str(_.get("operation", "search")).lower()
        if operation == "read":
            result = self.router.execute_channel_read(query)
            self._record_transport(telemetry, result)
            if result.get("status") != "success":
                raise NativeReachError(result.get("error", "YouTube read failed"))
            content = result.get("content", "")
            video_metadata = result.get("video_metadata") or {}
            fragments = [EvidenceFragment(
                platform="YouTube", title=result.get("title") or "",
                content=content, url=query, author=video_metadata.get("channel") or "",
                published=video_metadata.get("upload_date") or "", snippet=content[:300],
                score=55.0, retrieval_method="yt_dlp", channel_name="youtube",
                retrieval_mode=RetrievalMode.NATIVE_TOOL_CLI.value,
                native_backend_id="yt-dlp", content_depth="VIDEO_METADATA",
                query_id=query_id, query_class=query_class, query_text=query_text,
                raw_metadata={"backend": result.get("backend", "yt-dlp"),
                              "transport": result.get("transport", {}),
                              "video_metadata": video_metadata},
            )]
            self.router._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.NATIVE_TOOL_CLI.value, "yt-dlp", None, False)
            telemetry.update(status="SUCCESS", backend="yt-dlp")
            return fragments
        if operation == "transcript":
            result = self.router.executor.execute_youtube_transcript(query)
            self._record_transport(telemetry, result)
            content = result.get("content", "")
            fragments = [] if not content else [EvidenceFragment(
                platform="YouTube", title="", content=content,
                url=query, author="", snippet=content[:300], score=75.0,
                retrieval_method="yt_dlp_transcript", channel_name="youtube",
                retrieval_mode=RetrievalMode.NATIVE_TOOL_CLI.value,
                native_backend_id="yt-dlp", content_depth="VIDEO_TRANSCRIPT",
                query_id=query_id, query_class=query_class, query_text=query_text,
                raw_metadata={
                    "backend": "yt-dlp", "transport": result.get("transport", {}),
                    "segments": result.get("segments", []),
                    "segments_truncated": result.get("segments_truncated", False),
                    "caption_language": result.get("caption_language"),
                    "caption_origin": result.get("caption_origin", "UNVERIFIED"),
                },
            )]
            self.router._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.NATIVE_TOOL_CLI.value, "yt-dlp", None, False)
            telemetry.update(status="SUCCESS", backend="yt-dlp")
            return fragments
        if operation == "comments":
            result = self.router.executor.execute_youtube_comments(query, limit=limit)
            self._record_transport(telemetry, result)
            fragments = self.router.normalizer.normalize_youtube_comments(
                result.get("items", []), video_url=query, query_id=query_id,
                query_class=query_class, query_text=query_text,
            )
            self._attach_transport(fragments, result.get("transport"))
            self.router._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.DIRECT_API.value, "yt-dlp", None, False)
            telemetry.update(status="SUCCESS", backend="yt-dlp")
            return fragments
        try:
            result = self.router.executor.execute_youtube_search(query, limit=limit)
            self._record_transport(telemetry, result)
            fragments = self.router.normalizer.normalize_youtube_search(
                result.get("items", []), query_id=query_id, query_class=query_class, query_text=query_text
            )
            if not fragments:
                raise NativeReachError("Native yt-dlp returned no items")
            self._attach_transport(fragments, result.get("transport"))
            self.router._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.DIRECT_API.value, "yt-dlp", None, False)
            for fragment in fragments:
                fragment.content_depth = "VIDEO_METADATA"
            telemetry["status"] = "SUCCESS"
            return fragments
        except Exception:
            fragments = self.router._fallback_youtube_scraper(query, limit, query_id, query_class, query_text)
            self.router._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, "Legacy YouTube Scraper", "YT_DLP_UNAVAILABLE", False)
            self._fallback(telemetry, "Legacy YouTube Scraper", "YT_DLP_UNAVAILABLE", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, fragments)
            return fragments

    def _execute_v2ex(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        operation = str(_.get("operation", "hot")).lower()
        if operation == "hot":
            result = self.router.executor.execute_v2ex_hot()
        elif operation == "search":
            result = self.router.executor.execute_v2ex_search(query)
        else:
            result = self.router.executor.execute_v2ex_operation(operation, query)
        self._record_transport(telemetry, result)
        items = result.get("items", [])
        if operation == "hot" and query.strip():
            needle = query.lower()
            matches = [item for item in items if needle in item.get("title", "").lower() or needle in (item.get("content") or "").lower()]
            items = matches or items[:limit]
        if operation == "replies":
            topic_id = query.strip() if query.strip().isdigit() else ""
            if not topic_id:
                match = re.search(r"/t/(\d+)(?:/|$)", urllib.parse.urlsplit(query).path)
                topic_id = match.group(1) if match else ""
            fragments = self.router.normalizer.normalize_v2ex_replies(
                items[:limit], topic_id=topic_id, query_id=query_id,
                query_class=query_class, query_text=query_text,
            )
        else:
            fragments = self.router.normalizer.normalize_v2ex_topics(
                items[:limit], query_id=query_id, query_class=query_class,
                query_text=query_text,
            )
        self._attach_transport(fragments, result.get("transport"))
        self.router._tag_fragments(fragments, "v2ex", "v2ex", RetrievalMode.DIRECT_API.value, "v2ex-public-api", None, False)
        telemetry["status"] = "SUCCESS"
        return fragments

    def _execute_bilibili(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        result = self.router.executor.execute_bilibili_search(query, limit=limit)
        fragments = self.router.normalizer.normalize_bilibili_videos(result.get("items", []), query_id=query_id, query_class=query_class, query_text=query_text)
        self._attach_transport(fragments, result.get("transport"))
        self.router._tag_fragments(fragments, "bilibili", "bilibili", RetrievalMode.DIRECT_API.value, "bilibili-public-api", None, False)
        for fragment in fragments:
            fragment.content_depth = "VIDEO_METADATA"
        telemetry["status"] = "SUCCESS"
        return fragments

    def _execute_rss(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        if str(_.get("operation", "search")).lower() == "read":
            if not query.strip().lower().startswith(("http://", "https://")):
                raise NativeReachError("rss.read requires an explicit feed URL")
            result = self.router.executor.execute_rss_read(query, limit=limit)
            self._record_transport(telemetry, result)
            follow_linked = bool(_.get("follow_linked_article", False))
            items = result.get("items", [])
            fragments = self.router.normalizer.normalize_rss_entries(
                items, channel_name="rss", query_id=query_id,
                query_class=query_class, query_text=query_text,
            )
            if follow_linked and fragments and items:
                # Follow up at most 1 linked article with safe SSRF check
                first_link = (items[0].get("link") or "").strip()
                if first_link and first_link.startswith(("http://", "https://")):
                    try:
                        read_res = self.router.execute_channel_read(first_link, max_chars=3000)
                        if read_res.get("status") == "success":
                            art_content = read_res.get("content") or ""
                            if art_content:
                                fragments[0].content += f"\n\nObserved linked article ({first_link}):\n{art_content[:2000]}"
                                fragments[0].content_depth = "FEED_ENTRY_WITH_LINKED_ARTICLE"
                                fragments[0].raw_metadata["linked_article"] = {
                                    "url": first_link,
                                    "title": read_res.get("title"),
                                    "author": read_res.get("author"),
                                    "char_count": len(art_content),
                                    "status": "SUCCESS",
                                }
                                telemetry["follow_up_requests"] = 1
                    except Exception:
                        pass
            self._attach_transport(fragments, result.get("transport"))
            self.router._tag_fragments(fragments, "rss", "rss", RetrievalMode.RSS_FEED.value, "feedparser", None, False)
            telemetry.update(status="SUCCESS", backend="feedparser")
            return fragments
        wire_terms = ("press release", "filing", "statement", "announcement", "regulatory", "wire")
        wire_query = query if any(term in query.lower() for term in wire_terms) else f"{query} (press release OR official statement OR filing OR wire)"
        return self._execute_feed("rss", wire_query, limit, query_id, query_class, wire_query, telemetry)

    def _execute_news(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        return self._execute_feed("news", query, limit, query_id, query_class, query_text, telemetry)

    def _execute_feed(self, channel, query, limit, query_id, query_class, query_text, telemetry):
        try:
            encoded = urllib.parse.quote_plus(query.strip())
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
            result = self.router.executor.execute_rss_read(url, limit=limit)
            self._record_transport(telemetry, result)
            fragments = self.router.normalizer.normalize_rss_entries(
                result.get("items", []), channel_name=channel, query_id=query_id, query_class=query_class, query_text=query_text
            )
            if not fragments:
                raise NativeReachError(f"{channel} returned no entries")
            self._attach_transport(fragments, result.get("transport"))
            backend = "feedparser-google-rss" if channel == "rss" else "feedparser-google-news"
            self.router._tag_fragments(fragments, channel, channel, RetrievalMode.RSS_FEED.value, backend, None, False)
            for fragment in fragments:
                fragment.content_depth = "FEED_ENTRY_SUMMARY"
            telemetry["status"] = "SUCCESS"
            return fragments
        except Exception:
            reason = "RSS_UNAVAILABLE" if channel == "rss" else "NEWS_FEED_UNAVAILABLE"
            fragments = self.router._fallback_news_scraper(query, limit, channel, query_id, query_class, query_text)
            self.router._tag_fragments(fragments, channel, channel, RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, "Legacy News Scraper", reason, False)
            self._fallback(telemetry, "Legacy News Scraper", reason, RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, fragments)
            return fragments

    def _execute_web(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        if str(_.get("operation", "search")).lower() == "read":
            return self._execute_jina_reader(
                query, limit, query_id, query_class, query_text, telemetry,
                url=query, requested_channel="web",
                max_chars=min(20_000, max(0, int(_.get("max_chars", 4000)))),
            )
        try:
            fragments = self.router._execute_web_search(query, limit, query_id, query_class, query_text)
            if fragments:
                self.router._tag_fragments(fragments, "web", "web_search", RetrievalMode.WEB_SEARCH_INDEX.value, "bing-search-rss", None, False)
                for fragment in fragments:
                    fragment.content_depth = "INDEX_SNIPPET"
                telemetry["status"] = "SUCCESS"
                return fragments
        except Exception:
            pass
        fragments = self.router._fallback_web_scraper(query, limit, query_id, query_class, query_text)
        self.router._tag_fragments(fragments, "web", "web", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, "Legacy Web Scraper", "BING_SEARCH_UNAVAILABLE", False)
        self._fallback(telemetry, "Legacy Web Scraper", "BING_SEARCH_UNAVAILABLE", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, fragments)
        return fragments

    def _execute_jina_reader(self, query, limit, query_id, query_class, query_text, telemetry, **kwargs):
        target_url = kwargs.get("url") or query
        requested_channel = kwargs.get("requested_channel", "jina_reader")
        actual_channel = "jina_reader"
        max_chars = min(20_000, max(0, int(kwargs.get("max_chars", 4000))))
        result = self.router.execute_channel_read(target_url, max_chars=max_chars)
        self._record_transport(telemetry, result)
        if result.get("status") != "success":
            telemetry.update(status="FAILED", error=result.get("error", "Failed to read content"))
            return []
        content = result.get("markdown", "") or result.get("content", "")
        backend_id = result.get("backend") or "jina-reader"
        reported_depth = result.get("content_depth") or (result.get("video_metadata") or {}).get("content_depth")
        depth = reported_depth if reported_depth in {"PROFILE_METADATA", "VIDEO_METADATA", "SOCIAL_POST", "VIDEO_TRANSCRIPT"} else "PARTIAL_CONTENT"
        fragment = EvidenceFragment(
            platform="Web", title=result.get("title") or "",
            content=content, url=target_url, author=result.get("author") or "",
            published=result.get("published") or "", snippet=content[:300], score=85.0,
            retrieval_method=backend_id,
            retrieval_mode=RetrievalMode.WEB_READER.value, native_backend_id=backend_id,
            channel_name=actual_channel, requested_channel=requested_channel,
            actual_retrieval_channel=actual_channel,
            # Generic page text may contain navigation or omit dynamic sections;
            # length alone cannot prove a complete underlying article.
            content_depth=depth, query_id=query_id,
            query_class=query_class, query_text=query_text,
            raw_metadata={
                "backend": result.get("backend", "Jina Reader"),
                "char_count": len(content),
                "page_metadata": result.get("page_metadata") or {},
                "raw_capture": result.get("raw_capture") or {},
                "truncated": result.get("truncated"),
                "observed_final_endpoint": (result.get("transport") or {}).get("endpoint"),
                "transport": result.get("transport"),
            },
        )
        self.router._tag_fragments(
            [fragment], requested_channel, actual_channel, RetrievalMode.WEB_READER.value,
            backend_id, None, False,
        )
        telemetry["status"] = "SUCCESS"
        return [fragment]

    def _execute_xueqiu(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        try:
            result = self.router.executor.execute_xueqiu(query, limit=limit)
            items = result.get("items", [])
            fragments = self.router.normalizer.normalize_xueqiu_items(
                items, query_id=query_id, query_class=query_class, query_text=query_text
            )
            if not fragments:
                raise NativeReachError("Xueqiu visitor API returned no items")
            self.router._tag_fragments(fragments, "xueqiu", "xueqiu", RetrievalMode.DIRECT_API.value, "xueqiu-visitor-api", None, False)
            telemetry["status"] = "SUCCESS"
            telemetry["backend"] = "xueqiu-visitor-api"
            return fragments
        except Exception:
            return self._indexed_fallback("xueqiu", query, limit, query_id, query_class, query_text, telemetry, site_filter="site:xueqiu.com")

    def _execute_xiaoyuzhou(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        operation = str(_.get("operation", "podcast")).lower()
        if operation not in {"search", "podcast", "episodes"}:
            raise NativeReachError(f"Unsupported Xiaoyuzhou operation: {operation}")
        if operation == "search":
            return self._indexed_fallback(
                "xiaoyuzhou", query, limit, query_id, query_class, query_text,
                telemetry, site_filter="site:xiaoyuzhoufm.com/podcast/",
            )
        clean_query = query.strip().lower()
        is_explicit_public_target = (
            "xiaoyuzhoufm.com/podcast/" in clean_query
            or bool(re.fullmatch(r"[a-f0-9]{24}", clean_query))
        )
        try:
            result = self.router.executor.execute_xiaoyuzhou_podcast(
                query, limit=limit, operation=operation,
            )
            self._record_transport(telemetry, result)
            items = result.get("items", [])
            fragments = self.router.normalizer.normalize_xiaoyuzhou_episodes(
                items, query_id=query_id, query_class=query_class, query_text=query_text
            )
            if not fragments:
                raise NativeReachError("Xiaoyuzhou podcast syndication returned no items")
            self._attach_transport(fragments, result.get("transport"))
            self.router._tag_fragments(
                fragments, "xiaoyuzhou", "xiaoyuzhou", RetrievalMode.WEB_READER.value,
                "xiaoyuzhou-public-web", None, False,
            )
            telemetry["status"] = "SUCCESS"
            telemetry["backend"] = "xiaoyuzhou-public-web"
            return fragments
        except Exception:
            if is_explicit_public_target:
                raise
            return self._indexed_fallback("xiaoyuzhou", query, limit, query_id, query_class, query_text, telemetry, site_filter="site:xiaoyuzhoufm.com")

    def _execute_linkedin(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        try:
            result = self.router.executor.execute_linkedin_jobs(query, limit=limit)
            items = result.get("items", [])
            fragments = self.router.normalizer.normalize_linkedin_jobs(
                items, query_id=query_id, query_class=query_class, query_text=query_text
            )
            if fragments:
                self._attach_transport(fragments, result.get("transport"))
                self.router._tag_fragments(fragments, "linkedin", "linkedin", RetrievalMode.DIRECT_API.value, "linkedin-guest-jobs-api", None, False)
                telemetry["status"] = "SUCCESS"
                telemetry["backend"] = "linkedin-guest-jobs-api"
                return fragments
        except Exception:
            pass
        return self._indexed_fallback("linkedin", query, limit, query_id, query_class, query_text, telemetry, site_filter="site:linkedin.com/in/ OR site:linkedin.com/company/")

    def _execute_instagram(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        clean_q = query.strip()
        if "instagram.com/p/" in clean_q or "instagram.com/reel/" in clean_q:
            frag = self._fetch_meta_oembed("instagram", clean_q)
            if frag:
                frag.query_id = query_id
                frag.query_class = query_class
                frag.query_text = query_text
                self.router._tag_fragments([frag], "instagram", "instagram", RetrievalMode.DIRECT_API.value, "instagram-oembed", None, False)
                telemetry["status"] = "SUCCESS"
                telemetry["backend"] = "instagram-oembed"
                return [frag]
        return self._indexed_fallback("instagram", query, limit, query_id, query_class, query_text, telemetry, site_filter="site:instagram.com")

    def _execute_facebook(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        clean_q = query.strip()
        if "facebook.com/" in clean_q and ("/posts/" in clean_q or "/videos/" in clean_q):
            frag = self._fetch_meta_oembed("facebook", clean_q)
            if frag:
                frag.query_id = query_id
                frag.query_class = query_class
                frag.query_text = query_text
                self.router._tag_fragments([frag], "facebook", "facebook", RetrievalMode.DIRECT_API.value, "facebook-oembed", None, False)
                telemetry["status"] = "SUCCESS"
                telemetry["backend"] = "facebook-oembed"
                return [frag]
        return self._indexed_fallback("facebook", query, limit, query_id, query_class, query_text, telemetry, site_filter="site:facebook.com")

    def _execute_xiaohongshu(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        return self._indexed_fallback("xiaohongshu", query, limit, query_id, query_class, query_text, telemetry, site_filter="site:xiaohongshu.com")

    def _execute_boss(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        return self._indexed_fallback("boss", query, limit, query_id, query_class, query_text, telemetry, site_filter="site:zhipin.com")

    def _fetch_meta_oembed(self, platform: str, url: str) -> Optional[EvidenceFragment]:
        endpoint = "instagram_oembed" if platform == "instagram" else "oembed_post"
        req_url = f"https://graph.facebook.com/v20.0/{endpoint}?url={urllib.parse.quote(url.strip())}"
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                r = client.get(req_url)
                if r.status_code == 200:
                    data = r.json()
                    author = data.get("author_name") or platform.capitalize()
                    html_snippet = data.get("html") or ""
                    title = data.get("title") or f"{platform.capitalize()} post by {author}"
                    return EvidenceFragment(
                        platform=platform.capitalize(),
                        title=title,
                        content=html_snippet,
                        url=url,
                        author=author,
                        published="Recent",
                        snippet=html_snippet[:300],
                        score=60.0,
                        retrieval_method=f"{platform}_oembed",
                        retrieval_mode=RetrievalMode.DIRECT_API.value,
                        native_backend_id=f"{platform}-oembed",
                        channel_name=platform,
                        content_depth="SNIPPET",
                        raw_metadata={"backend": f"{platform}-oembed", "tokenless": True}
                    )
        except Exception:
            pass
        return None

    def _indexed_fallback(self, platform: str, query: str, limit: int, query_id: str, query_class: str, query_text: str, telemetry: Dict[str, Any], site_filter: str) -> List[EvidenceFragment]:
        search_query = f"{site_filter} {query}"
        reason = f"{platform.upper()}_DIRECT_UNAVAILABLE_FALLBACK"
        fragments = self.router._execute_web_search(search_query, limit, query_id, query_class, query_text)
        allowed_domains = {
            "xueqiu": {"xueqiu.com", "www.xueqiu.com"},
            "linkedin": {"linkedin.com", "www.linkedin.com"},
            "instagram": {"instagram.com", "www.instagram.com"},
            "facebook": {"facebook.com", "www.facebook.com", "m.facebook.com"},
            "xiaohongshu": {"xiaohongshu.com", "www.xiaohongshu.com"},
            "boss": {"zhipin.com", "www.zhipin.com"},
            "xiaoyuzhou": {"xiaoyuzhoufm.com", "www.xiaoyuzhoufm.com"},
        }.get(platform, set())
        if allowed_domains:
            fragments = [
                fragment for fragment in fragments
                if (urllib.parse.urlparse(fragment.url or "").hostname or "").lower() in allowed_domains
            ]
        self.router._tag_fragments(fragments, platform, "web_search", RetrievalMode.WEB_SEARCH_INDEX.value, "bing-search-index", reason, False)
        for fragment in fragments:
            fragment.platform = f"{platform.capitalize()} (Web Index Fallback)"
            fragment.retrieval_method = f"{platform}_web_index"
            fragment.content_depth = "INDEX_SNIPPET"
            fragment.raw_metadata.update(
                source_tier="TIER_3_AGGREGATE",
                honest_disclosure=f"Direct {platform} API requires session authentication; retrieved through public search index."
            )
        telemetry.update(
            status="SUCCESS" if fragments else "DEGRADED",
            fallback_used=True,
            fallback_backend="Bing Search Index",
            fallback_reason=reason,
            retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
        )
        return fragments

    def _execute_authenticated(
        self, platform: str, telemetry: Dict[str, Any]
    ) -> List[EvidenceFragment]:
        operation = str(telemetry.get("operation", "search")).split(".", 1)[-1]
        env_var = required_auth_environment(platform, operation)
        if not env_var:
            raise NativeReachError(f"No authentication contract registered for {platform}")
        try:
            self.router.executor.guard_authenticated_channel(platform=platform, backend=telemetry["backend"], env_var=env_var)
            telemetry.update(status="NO_DATA", error="Credential verified but no execution adapter configured")
        except AuthRequiredError as error:
            telemetry.update(status="AUTH_REQUIRED", error=str(error))
        return []

    def _execute_generic(self, platform, query, limit, query_id, query_class, query_text, telemetry):
        telemetry.update(
            status="UNSUPPORTED",
            outcome="UNAVAILABLE_NOT_IMPLEMENTED",
            error=f"No executable handler is registered for channel '{platform}'",
        )
        return []

    @staticmethod
    def _attach_transport(fragments: List[EvidenceFragment], transport: Optional[Dict[str, Any]]) -> None:
        if not transport:
            return
        for fragment in fragments:
            fragment.raw_metadata["transport"] = dict(transport)

    @staticmethod
    def _record_transport(telemetry: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Keep provider observations even when normalization yields no fragments."""
        transport = result.get("transport") if isinstance(result, dict) else None
        if isinstance(result, dict) and result.get("status"):
            telemetry["provider_status"] = str(result["status"]).upper()
        if isinstance(result, dict):
            telemetry["adapter_result_field_names"] = sorted(
                str(key) for key in result
                if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", str(key))
            )[:100]
            # Names only: preserve observed adapter-item shape for extraction
            # audits without persisting copyrighted bodies or credentials.
            items = result.get("items")
            if isinstance(items, list):
                names = set()
                for item in items[:3]:
                    if not isinstance(item, dict):
                        continue
                    for key, value in item.items():
                        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", str(key)):
                            continue
                        names.add(str(key))
                        if isinstance(value, dict):
                            names.update(
                                f"{key}.{child}" for child in value
                                if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", str(child))
                            )
                telemetry["adapter_item_field_names"] = sorted(names)[:150]
        if transport:
            telemetry.setdefault("transport_observations", []).append(dict(transport))

    @staticmethod
    def _fallback(telemetry, backend, reason, mode, fragments):
        telemetry.update(
            fallback_used=True,
            fallback_backend=backend,
            fallback_reason=reason,
            retrieval_mode=mode,
            status="SUCCESS" if fragments else "DEGRADED",
        )

    def _execute_community(self, platform, query, limit, query_id, query_class, query_text, telemetry, **kwargs):
        from backend.infrastructure.acquisition.adapters.community import acquire_community
        fragments, observed = acquire_community(
            platform, query, limit, operation=kwargs.get("operation", "search"), page=kwargs.get("page", 1),
            include_comments=kwargs.get("include_comments", False),
            include_answers=kwargs.get("include_answers", False),
        )
        telemetry.update(observed)
        for fragment in fragments:
            fragment.query_id = query_id
            fragment.query_class = query_class
            fragment.query_text = query_text
            if not fragment.raw_metadata.get("transport") and observed.get("transport_observations"):
                fragment.raw_metadata["transport"] = dict(observed["transport_observations"][-1])
        self.router._tag_fragments(fragments, platform, platform, RetrievalMode.DIRECT_API.value,
                                   "hn-firebase-api" if platform == "hackernews" else "stackexchange-api", None, False)
        return fragments

    def _execute_hackernews(self, *args, **kwargs):
        return self._execute_community("hackernews", *args, **kwargs)

    def _execute_stackexchange(self, *args, **kwargs):
        return self._execute_community("stackexchange", *args, **kwargs)

    def _execute_sec_edgar(self, query, limit, query_id, query_class, query_text, telemetry, **kwargs):
        from backend.infrastructure.acquisition.adapters.authoritative.sec_edgar import (
            fetch_sec_submissions, normalize_sec_items,
        )
        form_filter = kwargs.get("form") or kwargs.get("form_filter")
        result = fetch_sec_submissions(query, limit=limit, form_filter=form_filter)
        self._record_transport(telemetry, result)
        items = result.get("items", [])
        if not items:
            telemetry.update(status="EMPTY_RESULT" if result.get("status") == "SUCCESS" else result.get("status", "FAILED"))
            return []
        fragments = normalize_sec_items(items, query_id=query_id, query_class=query_class, query_text=query_text)
        self._attach_transport(fragments, result.get("transport"))
        self.router._tag_fragments(fragments, "sec_edgar", "sec_edgar", RetrievalMode.DIRECT_API.value, "sec-edgar-data-api", None, False)
        telemetry.update(status="SUCCESS", backend="sec-edgar-data-api")
        return fragments

    def _execute_nist_cve(self, query, limit, query_id, query_class, query_text, telemetry, **kwargs):
        from backend.infrastructure.acquisition.adapters.authoritative.nist_nvd import (
            fetch_nist_cve, normalize_nist_items,
        )
        result = fetch_nist_cve(query, limit=limit)
        self._record_transport(telemetry, result)
        items = result.get("items", [])
        if not items:
            telemetry.update(status="EMPTY_RESULT" if result.get("status") == "SUCCESS" else "FAILED")
            return []
        fragments = normalize_nist_items(items, query_id=query_id, query_class=query_class, query_text=query_text)
        self._attach_transport(fragments, result.get("transport"))
        self.router._tag_fragments(fragments, "nist_cve", "nist_cve", RetrievalMode.DIRECT_API.value, "nist-nvd-cve-api", None, False)
        telemetry.update(status="SUCCESS", backend="nist-nvd-cve-api")
        return fragments

    def _execute_arxiv(self, query, limit, query_id, query_class, query_text, telemetry, **kwargs):
        from backend.infrastructure.acquisition.adapters.authoritative.arxiv_preprints import (
            fetch_arxiv_preprints, normalize_arxiv_items,
        )
        result = fetch_arxiv_preprints(query, limit=limit)
        self._record_transport(telemetry, result)
        items = result.get("items", [])
        if not items:
            telemetry.update(status="EMPTY_RESULT" if result.get("status") == "SUCCESS" else "FAILED")
            return []
        fragments = normalize_arxiv_items(items, query_id=query_id, query_class=query_class, query_text=query_text)
        self._attach_transport(fragments, result.get("transport"))
        self.router._tag_fragments(fragments, "arxiv", "arxiv", RetrievalMode.DIRECT_API.value, "arxiv-export-api", None, False)
        telemetry.update(status="SUCCESS", backend="arxiv-export-api")
        return fragments

    def _execute_fact_check(self, query, limit, query_id, query_class, query_text, telemetry, **kwargs):
        from backend.infrastructure.acquisition.adapters.authoritative.fact_check import (
            fetch_fact_check_claims, normalize_fact_check_items,
        )
        api_key = kwargs.get("api_key")
        result = fetch_fact_check_claims(query, limit=limit, api_key=api_key)
        self._record_transport(telemetry, result)
        items = result.get("items", [])
        if not items:
            telemetry.update(status="EMPTY_RESULT" if result.get("status") == "SUCCESS" else result.get("status", "FAILED"))
            return []
        fragments = normalize_fact_check_items(items, query_id=query_id, query_class=query_class, query_text=query_text)
        self._attach_transport(fragments, result.get("transport"))
        self.router._tag_fragments(fragments, "fact_check", "fact_check", RetrievalMode.DIRECT_API.value, "factcheck-tools-api", None, False)
        telemetry.update(status="SUCCESS", backend="factcheck-tools-api")
        return fragments


