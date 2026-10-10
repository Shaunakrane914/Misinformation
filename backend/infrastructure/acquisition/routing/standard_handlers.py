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
        if platform in self.AUTH_ENVIRONMENT:
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
        try:
            result = self.router.executor.execute_github_search(query, limit=limit)
            fragments = self.router.normalizer.normalize_github_repos(
                result.get("items", []), query_id=query_id, query_class=query_class, query_text=query_text
            )
            if not fragments:
                raise NativeReachError("Native gh CLI returned no items")
            self.router._tag_fragments(fragments, "github", "github", RetrievalMode.DIRECT_API.value, "gh-cli", None, True)
            telemetry["status"] = "SUCCESS"
            return fragments
        except Exception:
            fragments = self.router._fallback_github_rest(query, limit, query_id, query_class, query_text)
            self.router._tag_fragments(fragments, "github", "github", RetrievalMode.DIRECT_API.value, "GitHub REST API", "GH_CLI_UNAVAILABLE", False)
            self._fallback(telemetry, "GitHub REST API", "GH_CLI_UNAVAILABLE", RetrievalMode.DIRECT_API.value, fragments)
            return fragments

    def _execute_youtube(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        try:
            result = self.router.executor.execute_youtube_search(query, limit=limit)
            fragments = self.router.normalizer.normalize_youtube_search(
                result.get("items", []), query_id=query_id, query_class=query_class, query_text=query_text
            )
            if not fragments:
                raise NativeReachError("Native yt-dlp returned no items")
            self.router._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.DIRECT_API.value, "yt-dlp", None, False)
            telemetry["status"] = "SUCCESS"
            return fragments
        except Exception:
            fragments = self.router._fallback_youtube_scraper(query, limit, query_id, query_class, query_text)
            self.router._tag_fragments(fragments, "youtube", "youtube", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, "Legacy YouTube Scraper", "YT_DLP_UNAVAILABLE", False)
            self._fallback(telemetry, "Legacy YouTube Scraper", "YT_DLP_UNAVAILABLE", RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, fragments)
            return fragments

    def _execute_v2ex(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        items = self.router.executor.execute_v2ex_hot().get("items", [])
        if query.strip():
            needle = query.lower()
            matches = [item for item in items if needle in item.get("title", "").lower() or needle in (item.get("content") or "").lower()]
            items = matches or items[:limit]
        fragments = self.router.normalizer.normalize_v2ex_topics(items[:limit], query_id=query_id, query_class=query_class, query_text=query_text)
        self.router._tag_fragments(fragments, "v2ex", "v2ex", RetrievalMode.DIRECT_API.value, "v2ex-public-api", None, False)
        telemetry["status"] = "SUCCESS"
        return fragments

    def _execute_bilibili(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        result = self.router.executor.execute_bilibili_search(query, limit=limit)
        fragments = self.router.normalizer.normalize_bilibili_videos(result.get("items", []), query_id=query_id, query_class=query_class, query_text=query_text)
        self.router._tag_fragments(fragments, "bilibili", "bilibili", RetrievalMode.DIRECT_API.value, "bilibili-public-api", None, False)
        telemetry["status"] = "SUCCESS"
        return fragments

    def _execute_rss(self, query, limit, query_id, query_class, query_text, telemetry, **_):
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
            backend = "feedparser-google-rss" if channel == "rss" else "feedparser-google-news"
            self.router._tag_fragments(fragments, channel, channel, RetrievalMode.DIRECT_API.value, backend, None, False)
            telemetry["status"] = "SUCCESS"
            return fragments
        except Exception:
            reason = "RSS_UNAVAILABLE" if channel == "rss" else "NEWS_FEED_UNAVAILABLE"
            fragments = self.router._fallback_news_scraper(query, limit, channel, query_id, query_class, query_text)
            self.router._tag_fragments(fragments, channel, channel, RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, "Legacy News Scraper", reason, False)
            self._fallback(telemetry, "Legacy News Scraper", reason, RetrievalMode.LEGACY_SCRAPER_FALLBACK.value, fragments)
            return fragments

    def _execute_web(self, query, limit, query_id, query_class, query_text, telemetry, **_):
        try:
            fragments = self.router._execute_web_search(query, limit, query_id, query_class, query_text)
            if fragments:
                self.router._tag_fragments(fragments, "web", "web", RetrievalMode.DIRECT_API.value, "bing-search-rss", None, False)
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
            raw_metadata={"backend": result.get("backend", "Jina Reader"), "char_count": len(content)},
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
        self.router._tag_fragments(fragments, platform, "web_search", RetrievalMode.WEB_SEARCH_INDEX.value, "bing-search-index", reason, False)
        for fragment in fragments:
            fragment.platform = f"{platform.capitalize()} (Web Index Fallback)"
            fragment.retrieval_method = f"{platform}_web_index"
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
        fragments = self.router._execute_web_search(query, limit, query_id, query_class, query_text)
        self.router._tag_fragments(fragments, platform, platform, RetrievalMode.DIRECT_API.value, telemetry["backend"] or "generic-search", None, False)
        telemetry["status"] = "SUCCESS" if fragments else "DEGRADED"
        return fragments

    @staticmethod
    def _fallback(telemetry, backend, reason, mode, fragments):
        telemetry.update(
            fallback_used=True,
            fallback_backend=backend,
            fallback_reason=reason,
            retrieval_mode=mode,
            status="SUCCESS" if fragments else "DEGRADED",
        )

