"""Deterministic handlers for non-social acquisition channels."""

from __future__ import annotations

import os
import urllib.parse
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode
from backend.services.agent_reach.native.errors import AuthRequiredError, NativeReachError

if TYPE_CHECKING:
    from backend.infrastructure.acquisition.routing.router import NativeRouter


class StandardChannelHandlers:
    """Own native, feed, web-search, reader, and credential-gated execution."""

    AUTH_ENVIRONMENT = {
        "linkedin": "LINKEDIN_COOKIE",
        "xueqiu": "XUEQIU_COOKIE",
        "xiaohongshu": "XIAOHONGSHU_COOKIE",
        "instagram": "INSTAGRAM_COOKIE",
        "facebook": "FACEBOOK_COOKIE",
        "boss": "BOSS_CDP_PORT",
        "xiaoyuzhou": "GROQ_API_KEY",
    }

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
        if platform == "web_search":
            return self._execute_web(query, limit, query_id, query_class, query_text, telemetry, **kwargs)
        if platform in self.AUTH_ENVIRONMENT:
            public_operations = {
                ("linkedin", "jobs"),
                ("xiaoyuzhou", "podcast"),
                ("xiaoyuzhou", "episodes"),
            }
            if (
                (platform, operation) in public_operations
                or
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
                operation, query, limit, query_id, query_class, query_text, telemetry
            )
        try:
            result = self.router.executor.execute_github_search(query, limit=limit)
            fragments = self.router.normalizer.normalize_github_repos(
                result.get("items", []), query_id=query_id, query_class=query_class, query_text=query_text
            )
            if not fragments:
                raise NativeReachError("Native gh CLI returned no items")
            self._attach_transport(fragments, result.get("transport"))
            self.router._tag_fragments(fragments, "github", "github", RetrievalMode.DIRECT_API.value, "gh-cli", None, True)
            telemetry["status"] = "SUCCESS"
            return fragments
        except Exception:
            fragments = self.router._fallback_github_rest(query, limit, query_id, query_class, query_text)
            self.router._tag_fragments(fragments, "github", "github", RetrievalMode.DIRECT_API.value, "GitHub REST API", "GH_CLI_UNAVAILABLE", False)
            self._fallback(telemetry, "GitHub REST API", "GH_CLI_UNAVAILABLE", RetrievalMode.DIRECT_API.value, fragments)
            return fragments

    def _execute_github_operation(
        self, operation, query, limit, query_id, query_class, query_text, telemetry
    ):
        result = self.router.executor.execute_github_rest_operation(
            query, operation, limit=limit
        )
        fragments: List[EvidenceFragment] = []
        repo = result.get("repo", query)
        for item in result.get("items", []):
            if operation == "read":
                title = item.get("full_name") or repo
                body = item.get("readme") or item.get("description") or ""
                url = item.get("html_url") or f"https://github.com/{repo}"
                author = (item.get("owner") or {}).get("login") or repo.split("/")[0]
                published = item.get("updated_at") or ""
                depth = "FULL_ARTICLE" if item.get("readme") else "METADATA"
            elif operation in {"issues", "prs"}:
                title = item.get("title") or f"GitHub {operation[:-1]}"
                body = item.get("body") or title
                url = item.get("html_url") or ""
                author = (item.get("user") or {}).get("login") or "GitHub"
                published = item.get("created_at") or ""
                depth = "FULL_ARTICLE" if item.get("body") else "METADATA"
            elif operation == "releases":
                title = item.get("name") or item.get("tag_name") or "GitHub release"
                body = item.get("body") or title
                url = item.get("html_url") or ""
                author = ((item.get("author") or {}).get("login") or repo.split("/")[0])
                published = item.get("published_at") or item.get("created_at") or ""
                depth = "FULL_ARTICLE" if item.get("body") else "METADATA"
            else:
                commit = item.get("commit") or {}
                title = (commit.get("message") or "GitHub commit").splitlines()[0]
                body = commit.get("message") or title
                url = item.get("html_url") or ""
                author = ((item.get("author") or {}).get("login") or
                          (commit.get("author") or {}).get("name") or "GitHub")
                published = (commit.get("author") or {}).get("date") or ""
                depth = "FULL_ARTICLE"
            fragments.append(EvidenceFragment(
                platform="GitHub", title=title, content=body, url=url,
                author=author, published=published, snippet=body[:300], score=70.0,
                retrieval_method="github_rest", retrieval_mode=RetrievalMode.DIRECT_API.value,
                native_backend_id="github-rest", channel_name="github",
                content_depth=depth, query_id=query_id, query_class=query_class,
                query_text=query_text,
                raw_metadata={"backend": "GitHub REST API", "operation": operation},
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
            if result.get("status") != "success":
                raise NativeReachError(result.get("error", "YouTube read failed"))
            content = result.get("content", "")
            fragments = [EvidenceFragment(
                platform="YouTube", title=result.get("title", "YouTube video"),
                content=content, url=query, author="YouTube", snippet=content[:300],
                score=55.0, retrieval_method="yt_dlp", channel_name="youtube",
                retrieval_mode=RetrievalMode.NATIVE_TOOL_CLI.value,
                native_backend_id="yt-dlp", content_depth="VIDEO_METADATA",
                query_id=query_id, query_class=query_class, query_text=query_text,
                raw_metadata={"backend": result.get("backend", "yt-dlp"),
                              "transport": result.get("transport", {})},
            )]
            self.router._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.NATIVE_TOOL_CLI.value, "yt-dlp", None, False)
            telemetry.update(status="SUCCESS", backend="yt-dlp")
            return fragments
        if operation == "transcript":
            result = self.router.executor.execute_youtube_transcript(query)
            content = result.get("content", "")
            fragments = [] if not content else [EvidenceFragment(
                platform="YouTube", title="YouTube transcript", content=content,
                url=query, author="YouTube", snippet=content[:300], score=75.0,
                retrieval_method="yt_dlp_transcript", channel_name="youtube",
                retrieval_mode=RetrievalMode.NATIVE_TOOL_CLI.value,
                native_backend_id="yt-dlp", content_depth="VIDEO_TRANSCRIPT",
                query_id=query_id, query_class=query_class, query_text=query_text,
                raw_metadata={"backend": "yt-dlp", "transport": result.get("transport", {})},
            )]
            self.router._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.NATIVE_TOOL_CLI.value, "yt-dlp", None, False)
            telemetry.update(status="SUCCESS", backend="yt-dlp")
            return fragments
        if operation == "comments":
            result = self.router.executor.execute_youtube_comments(query, limit=limit)
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
        items = result.get("items", [])
        if operation == "hot" and query.strip():
            needle = query.lower()
            matches = [item for item in items if needle in item.get("title", "").lower() or needle in (item.get("content") or "").lower()]
            items = matches or items[:limit]
        fragments = self.router.normalizer.normalize_v2ex_topics(items[:limit], query_id=query_id, query_class=query_class, query_text=query_text)
        self._attach_transport(fragments, result.get("transport"))
        self.router._tag_fragments(fragments, "v2ex", "v2ex", RetrievalMode.DIRECT_API.value, "v2ex-public-api", None, False)
        if operation == "replies":
            for fragment in fragments:
                fragment.content_depth = "COMMENT"
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
            fragments = self.router.normalizer.normalize_rss_entries(
                result.get("items", []), channel_name="rss", query_id=query_id,
                query_class=query_class, query_text=query_text,
            )
            self._attach_transport(fragments, result.get("transport"))
            self.router._tag_fragments(fragments, "rss", "rss", RetrievalMode.RSS_FEED.value, "feedparser", None, False)
            for fragment in fragments:
                fragment.content_depth = "FEED_ENTRY_SUMMARY"
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
                query, limit, query_id, query_class, query_text, telemetry, url=query
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
        result = self.router.execute_channel_read(target_url, max_chars=kwargs.get("max_chars", 4000))
        if result.get("status") != "success":
            telemetry.update(status="FAILED", error=result.get("error", "Failed to read content"))
            return []
        content = result.get("markdown", "") or result.get("content", "")
        fragment = EvidenceFragment(
            platform="Web", title=result.get("title") or f"Article from {urllib.parse.urlparse(target_url).netloc}",
            content=content, url=target_url, author=urllib.parse.urlparse(target_url).netloc or "Web",
            published="Recent", snippet=content[:300], score=85.0, retrieval_method="jina_reader",
            retrieval_mode=RetrievalMode.WEB_READER.value, native_backend_id="jina-reader",
            channel_name="jina_reader", requested_channel="jina_reader", actual_retrieval_channel="jina_reader",
            content_depth="FULL_ARTICLE" if len(content) > 500 else "SNIPPET", query_id=query_id,
            query_class=query_class, query_text=query_text,
            raw_metadata={
                "backend": result.get("backend", "Jina Reader"),
                "char_count": len(content),
                "transport": result.get("transport"),
            },
        )
        self.router._tag_fragments(
            [fragment], "jina_reader", "jina_reader", RetrievalMode.WEB_READER.value,
            "jina-reader", None, False,
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
        if operation not in {"podcast", "episodes"}:
            raise NativeReachError(f"Unsupported Xiaoyuzhou operation: {operation}")
        try:
            result = self.router.executor.execute_xiaoyuzhou_podcast(query, limit=limit)
            items = result.get("items", [])
            fragments = self.router.normalizer.normalize_xiaoyuzhou_episodes(
                items, query_id=query_id, query_class=query_class, query_text=query_text
            )
            if not fragments:
                raise NativeReachError("Xiaoyuzhou podcast syndication returned no items")
            self.router._tag_fragments(fragments, "xiaoyuzhou", "xiaoyuzhou", RetrievalMode.DIRECT_API.value, "podcast-rss-syndication", None, False)
            telemetry["status"] = "SUCCESS"
            telemetry["backend"] = "podcast-rss-syndication"
            return fragments
        except Exception:
            return self._indexed_fallback("xiaoyuzhou", query, limit, query_id, query_class, query_text, telemetry, site_filter="site:xiaoyuzhoufm.com")

    def _execute_linkedin(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        try:
            result = self.router.executor.execute_linkedin_jobs(query, limit=limit)
            items = result.get("items", [])
            fragments = self.router.normalizer.normalize_linkedin_jobs(
                items, query_id=query_id, query_class=query_class, query_text=query_text
            )
            if fragments:
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

    def _execute_authenticated(self, platform: str, telemetry: Dict[str, Any]) -> List[EvidenceFragment]:
        env_var = self.AUTH_ENVIRONMENT[platform]
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
    def _fallback(telemetry, backend, reason, mode, fragments):
        telemetry.update(
            fallback_used=True,
            fallback_backend=backend,
            fallback_reason=reason,
            retrieval_mode=mode,
            status="SUCCESS" if fragments else "DEGRADED",
        )

