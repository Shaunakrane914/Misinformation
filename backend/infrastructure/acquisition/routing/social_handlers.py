"""Reddit and X discovery, mirror acquisition, and honest indexed fallbacks."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode
from backend.services.agent_reach.native.source_discovery import (
    TWITTER_RESERVED_PATHS,
    SourceDiscoveryResult,
    discover_sources_from_search,
    extract_reddit_source,
    extract_x_source,
    generate_discovery_queries,
)

if TYPE_CHECKING:
    from backend.infrastructure.acquisition.routing.router import NativeRouter


class SocialChannelHandlers:
    """Own platform-aware discovery -> mirror -> search-index fallback policy."""

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
        if platform == "reddit":
            return self._execute_reddit(query, limit, query_id, query_class, query_text, telemetry, kwargs)
        return self._execute_twitter(query, limit, query_id, query_class, query_text, telemetry, kwargs)

    def _execute_reddit(self, query, limit, query_id, query_class, query_text, telemetry, context):
        fragments: List[EvidenceFragment] = []
        source = extract_reddit_source(query.strip(), query=query.strip())
        if source:
            fragments = self._fetch_direct_reddit(source, limit, query_id, query_class, query_text)
            if fragments:
                backend = fragments[0].native_backend_id if fragments else "reddit-rss"
                self._mark_mirror_success(fragments, "reddit", backend, telemetry)

        if not fragments:
            fragments = self._fetch_explicit_reddit_query(query, limit, query_id, query_class, query_text)
            if fragments:
                backend = fragments[0].native_backend_id if fragments else "reddit-rss"
                self._mark_mirror_success(fragments, "reddit", backend, telemetry)

        if not fragments and self.router.use_arctic_shift and self.router.use_social_url_discovery:
            candidates = self._discover(query, "reddit", query_id, query_class, query_text, telemetry, context, limit=limit)
            post_ids = [candidate.external_id for candidate in candidates if candidate.source_type == "post" and candidate.external_id]
            if post_ids:
                telemetry.update(selected_source_url=candidates[0].canonical_url, selected_external_id=post_ids[0], mirror_attempted=True, mirror_provider="arctic_shift")
                fragments = self.router._fetch_arctic_shift_posts_batch(post_ids, query_id, query_class, query_text)
                if fragments:
                    comments = self.router._fetch_arctic_shift_comments(post_ids[0], 3, query_id, query_class, query_text)
                    fragments.extend(comments)
                    self._annotate(fragments, "search_url_discovery", "full_submission_plus_comments" if comments else "full_submission")
                    self._mark_mirror_success(fragments, "reddit", "arctic_shift", telemetry)
                    telemetry.update(discovered_from="search_url_discovery", mirror_result="SUCCESS")
                else:
                    telemetry["mirror_result"] = "FALLBACK"

        if fragments:
            return fragments[:limit] if limit else fragments
        return self._indexed_fallback("reddit", query, limit, query_id, query_class, query_text, telemetry)

    def _fetch_direct_reddit(self, source, limit, query_id, query_class, query_text):
        if source.source_type == "comment" and source.parent_id:
            if not self.router.use_arctic_shift:
                return []
            post = self.router._fetch_arctic_shift_post(source.parent_id)
            comments = self.router._fetch_arctic_shift_comments(source.parent_id, limit, query_id, query_class, query_text)
            fragments = ([post] if post else []) + comments
            self._annotate(fragments, "direct_input", "full_submission_plus_comments", source.external_id)
            return fragments
        if source.source_type == "post" and source.external_id:
            if not self.router.use_arctic_shift:
                return []
            post = self.router._fetch_arctic_shift_post(source.external_id)
            if not post:
                return []
            comments = self.router._fetch_arctic_shift_comments(source.external_id, 3, query_id, query_class, query_text)
            fragments = [post] + comments
            self._annotate(fragments, "direct_input", "full_submission_plus_comments" if comments else "full_submission", source.external_id)
            return fragments
        if source.source_type == "subreddit" and source.subreddit:
            # First try public Subreddit RSS feed (zero auth, open syndication)
            rss_frags = self.router._fetch_reddit_subreddit_rss(source.subreddit, limit or 25, query_id, query_class, query_text)
            if rss_frags:
                self._annotate(rss_frags, "direct_input", "subreddit_feed", source.subreddit)
                return rss_frags
            if self.router.use_arctic_shift:
                fragments = self.router._fetch_arctic_shift_search("", source.subreddit, "", limit, query_id, query_class, query_text)
                self._annotate(fragments, "direct_input", "subreddit_feed")
                return fragments
        return []

    def _fetch_explicit_reddit_query(self, query, limit, query_id, query_class, query_text):
        match = re.search(r"(?:comments(?:\s+for\s+|\s+in\s+|:\s*)|^post\s+)([a-z0-9]+)", query.strip(), re.IGNORECASE)
        if match:
            if not self.router.use_arctic_shift:
                return []
            post_id = match.group(1)
            if query.lower().startswith("post "):
                post = self.router._fetch_arctic_shift_post(post_id)
                fragments = ([post] if post else []) + self.router._fetch_arctic_shift_comments(post_id, limit, query_id, query_class, query_text)
                completeness = "full_submission_plus_comments"
            else:
                fragments = self.router._fetch_arctic_shift_comments(post_id, limit, query_id, query_class, query_text)
                completeness = "comments"
            self._annotate(fragments, "direct_input", completeness, post_id)
            return fragments
        subreddit = re.fullmatch(r"r/([A-Za-z0-9_]+)", query.strip())
        if subreddit:
            rss_frags = self.router._fetch_reddit_subreddit_rss(subreddit.group(1), limit or 25, query_id, query_class, query_text)
            if rss_frags:
                self._annotate(rss_frags, "direct_input", "subreddit_feed", subreddit.group(1))
                return rss_frags
            if self.router.use_arctic_shift:
                fragments = self.router._fetch_arctic_shift_search("", subreddit.group(1), "", limit, query_id, query_class, query_text)
                self._annotate(fragments, "direct_input", "subreddit_feed")
                return fragments
        return []

    def _execute_twitter(self, query, limit, query_id, query_class, query_text, telemetry, context):
        fragments: List[EvidenceFragment] = []
        source = extract_x_source(query.strip(), query=query.strip())
        if source and self.router.use_fxtwitter:
            fragment = self._fetch_x_source(source)
            if fragment:
                completeness = "profile" if source.source_type == "profile" else "full_status"
                self._annotate([fragment], "direct_input", completeness, source.external_id)
                fragments = [fragment]
                self._mark_mirror_success(fragments, "twitter", "fxtwitter", telemetry)

        if not fragments and self.router.use_fxtwitter:
            handle = re.fullmatch(r"@?([A-Za-z0-9_]{1,15})", query.strip())
            if handle and handle.group(1).lower() not in TWITTER_RESERVED_PATHS:
                fragment = self.router._fetch_fxtwitter_profile(handle.group(1))
                if fragment:
                    self._annotate([fragment], "direct_input", "profile", handle.group(1))
                    fragments = [fragment]
                    self._mark_mirror_success(fragments, "twitter", "fxtwitter", telemetry)

        if not fragments and self.router.use_fxtwitter and self.router.use_social_url_discovery:
            target_limit = limit or 20
            candidates = self._discover(query, "twitter", query_id, query_class, query_text, telemetry, context, limit=target_limit)
            if candidates:
                telemetry.update(selected_source_url=candidates[0].canonical_url, selected_external_id=candidates[0].external_id, mirror_attempted=True, mirror_provider="fxtwitter")
                for candidate in candidates:
                    fragment = self._fetch_x_source(candidate)
                    if fragment and fragment.content:
                        completeness = "profile" if candidate.source_type == "profile" else "full_status"
                        self._annotate([fragment], "search_url_discovery", completeness, candidate.external_id)
                        fragments.append(fragment)
                        if len(fragments) >= (limit or 20):
                            break
                if fragments:
                    self._mark_mirror_success(fragments, "twitter", "fxtwitter", telemetry)
                    telemetry.update(discovered_from="search_url_discovery", mirror_result="SUCCESS")
                else:
                    telemetry["mirror_result"] = "FALLBACK"

        if fragments:
            return fragments[:limit] if limit else fragments
        return self._indexed_fallback("twitter", query, limit, query_id, query_class, query_text, telemetry)

    def _fetch_x_source(self, source) -> Optional[EvidenceFragment]:
        if source.source_type == "profile" and source.handle:
            return self.router._fetch_fxtwitter_profile(source.handle)
        if source.source_type == "status" and source.external_id:
            return self.router._fetch_fxtwitter_status(source.handle or "status", source.external_id)
        return None

    def _discover(self, query, platform, query_id, query_class, query_text, telemetry, context, limit: int = 10):
        candidates: List[SourceDiscoveryResult] = []
        candidate_urls: List[str] = []
        attempted = 0
        target_max = max(limit, int(os.getenv("AEGIS_DISCOVERY_MAX_CANDIDATES", "20")))
        for discovery_query in generate_discovery_queries(platform, query, entity=context.get("entity", ""), task_type=context.get("task_type", "SEARCH")):
            attempted += 1
            try:
                search_fragments = self.router._execute_web_search(discovery_query, min(target_max * 2, 40), query_id, query_class, query_text)
            except Exception:
                search_fragments = []
            candidate_urls.extend(fragment.url for fragment in search_fragments if fragment.url not in candidate_urls)
            for candidate in discover_sources_from_search(
                search_fragments, platform=platform, query=discovery_query,
                target_entity=context.get("entity", ""), target_topic=context.get("topic", ""),
                target_claim=context.get("claim", ""), task_type=context.get("task_type", "SEARCH"), max_candidates=target_max,
            ):
                if candidate.external_id and not any(existing.external_id == candidate.external_id for existing in candidates):
                    candidates.append(candidate)
            if len(candidates) >= target_max:
                break
        telemetry.update(
            discovery_attempted=True, discovery_engine="bing_search", queries_attempted=attempted,
            candidate_urls_count=len(candidate_urls), social_candidate_count=len(candidates),
        )
        telemetry["reddit_url_count" if platform == "reddit" else "x_status_url_count"] = len(candidates)
        if not candidates:
            telemetry.update(mirror_attempted=False, mirror_result="NO_VALID_URLS")
        return candidates

    def _indexed_fallback(self, platform, query, limit, query_id, query_class, query_text, telemetry):
        if platform == "reddit":
            search_query, reason, label, method = f"site:reddit.com {query}", "ARCTIC_SHIFT_UNAVAILABLE", "Reddit", "reddit_web_index"
        else:
            search_query, reason, label, method = f"site:twitter.com OR site:x.com {query}", "FXTWITTER_SEARCH_INDEX_FALLBACK", "Twitter", "twitter_web_index"
        # Deep indexing: scale limit to caller limit or up to 25-50
        effective_limit = max(limit, 25) if limit else 25
        fragments = self.router._execute_web_search(search_query, effective_limit, query_id, query_class, query_text)
        self.router._tag_fragments(fragments, platform, "web_search", RetrievalMode.WEB_SEARCH_INDEX.value, "bing-search-index", reason, False)
        for fragment in fragments:
            fragment.platform = f"{label} (Web Index Fallback)"
            fragment.retrieval_method = method
            fragment.raw_metadata.update(source_tier="TIER_3_AGGREGATE", honest_disclosure="Public mirror returned no usable item; retrieved through a public search index")
        telemetry.update(
            status="SUCCESS" if fragments else "DEGRADED", fallback_used=True,
            fallback_backend="Bing Search Index", fallback_reason=reason,
            retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
        )
        return fragments

    def _mark_mirror_success(self, fragments, channel, backend, telemetry):
        self.router._tag_fragments(fragments, channel, channel, RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, backend, None, False)
        telemetry.update(status="SUCCESS", backend=backend, retrieval_mode=RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value, authenticated=False)

    @staticmethod
    def _annotate(fragments, discovered_from, completeness, external_id=None):
        for fragment in fragments:
            fragment.raw_metadata["discovered_from"] = discovered_from
            fragment.raw_metadata["content_completeness"] = completeness
            if external_id:
                fragment.raw_metadata["external_id"] = external_id
