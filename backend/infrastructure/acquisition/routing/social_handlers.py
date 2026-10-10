"""
Aegis Protocol — Phase 6.8: Reddit and X Social Acquisition Handlers
====================================================================
Integrates:
1. Direct permalink / explicit entity fetching (status permalink, subreddit, handle)
2. Phase 6.8 Entity-to-Social-Source Resolution (Wikidata X handles & Sector/Regional Subreddits)
3. Zero-auth public mirrors (FxTwitter, Subreddit RSS with sunset governance)
4. Scoped search discovery for concrete tweet status IDs
5. Honest, strictly validated search index fallback (strictly rejects non-platform URLs)
"""

from __future__ import annotations

import logging
import os
import re
import urllib.parse
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
from backend.infrastructure.acquisition.resolution import entity_social_resolver

if TYPE_CHECKING:
    from backend.infrastructure.acquisition.routing.router import NativeRouter

logger = logging.getLogger(__name__)


class SocialChannelHandlers:
    """Own platform-aware discovery -> resolution -> mirror -> strict search-index fallback policy."""

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

    def _execute_reddit(self, query: str, limit: int, query_id: str, query_class: str, query_text: str, telemetry: Dict[str, Any], context: Dict[str, Any]) -> List[EvidenceFragment]:
        fragments: List[EvidenceFragment] = []

        # 1. Direct input parsing (explicit r/<subname> or reddit.com post URL)
        source = extract_reddit_source(query.strip(), query=query.strip())
        if source:
            fragments = self._fetch_direct_reddit(source, limit, query_id, query_class, query_text)
            if fragments:
                backend = fragments[0].native_backend_id if fragments else "reddit-rss"
                self._mark_mirror_success(fragments, "reddit", backend, telemetry)

        # 2. Explicit keyword pattern (e.g. "r/wallstreetbets" or "post 1x1ve6y")
        if not fragments:
            fragments = self._fetch_explicit_reddit_query(query, limit, query_id, query_class, query_text)
            if fragments:
                backend = fragments[0].native_backend_id if fragments else "reddit-rss"
                self._mark_mirror_success(fragments, "reddit", backend, telemetry)

        # 3. Phase 6.8: Entity-to-Subreddit Community Resolution
        if not fragments:
            resolution = entity_social_resolver.resolve(query)
            dep_info = resolution.rss_deprecation_info
            telemetry.update(
                resolved_entity=resolution.normalized_entity,
                entity_sector=resolution.sector,
                subreddit_candidate_count=len(resolution.subreddit_candidates),
                rss_deprecation_info=dep_info,
            )

            is_rss_active = dep_info.get("rss_active", True)
            if is_rss_active and resolution.subreddit_candidates:
                target_fetch = max(limit or 15, 20)
                for sub_cand in resolution.subreddit_candidates:
                    try:
                        raw_entries = self.router._fetch_reddit_subreddit_rss(
                            sub_cand.subreddit, limit=target_fetch,
                            query_id=query_id, query_class=query_class, query_text=query_text
                        )
                        if raw_entries:
                            ranked_entries = entity_social_resolver.subreddit_resolver.filter_and_rank_posts(
                                raw_entries, query, entity_name=resolution.normalized_entity
                            )
                            for p in ranked_entries:
                                p.content_depth = "FEED_ENTRY_SUMMARY"
                                p.raw_metadata.update(
                                    resolved_entity=resolution.normalized_entity,
                                    candidate_subreddit=sub_cand.subreddit,
                                    community_category=sub_cand.category,
                                    relevance_weight=sub_cand.relevance_weight,
                                    rss_sunset_warning=dep_info.get("rss_sunset_announced"),
                                )
                                self._annotate([p], "entity_subreddit_resolution", "feed_summary", sub_cand.subreddit)
                                if not any(f.url == p.url for f in fragments):
                                    fragments.append(p)
                                if len(fragments) >= (limit or 15):
                                    break
                    except Exception as e_sub:
                        logger.debug(f"[SocialHandlers] Subreddit resolution attempt for r/{sub_cand.subreddit}: {e_sub}")
                    if len(fragments) >= (limit or 15):
                        break

                if fragments:
                    self._mark_mirror_success(fragments, "reddit", "reddit-rss", telemetry)
                    telemetry.update(discovered_from="entity_subreddit_resolution", mirror_result="SUCCESS")
                    return fragments[:limit] if limit else fragments
                else:
                    telemetry["resolution_rss_result"] = "NO_RELEVANT_FEED_POSTS"
            else:
                telemetry["resolution_rss_result"] = "RSS_DEPRECATED_OR_DISABLED"

        # 4. Search Discovery via Arctic Shift mirror (if reachable)
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

        # 5. Strict Verified Web Index Fallback
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

    def _execute_twitter(self, query: str, limit: int, query_id: str, query_class: str, query_text: str, telemetry: Dict[str, Any], context: Dict[str, Any]) -> List[EvidenceFragment]:
        fragments: List[EvidenceFragment] = []

        # 1. Direct input parsing (explicit status URL or @handle)
        source = extract_x_source(query.strip(), query=query.strip())
        if source and self.router.use_fxtwitter:
            fragment = self._fetch_x_source(source)
            if fragment:
                completeness = "profile" if source.source_type == "profile" else "full_status"
                self._annotate([fragment], "direct_input", completeness, source.external_id)
                fragments = [fragment]
                self._mark_mirror_success(fragments, "twitter", "fxtwitter", telemetry)

        # 2. Plain handle query (e.g. "@OpenAI" or "OpenAI" if clean handle)
        if not fragments and self.router.use_fxtwitter:
            handle = re.fullmatch(r"@?([A-Za-z0-9_]{1,15})", query.strip())
            if handle and handle.group(1).lower() not in TWITTER_RESERVED_PATHS:
                fragment = self.router._fetch_fxtwitter_profile(handle.group(1))
                if fragment:
                    fragment.content_depth = "PROFILE_METADATA"
                    self._annotate([fragment], "direct_input", "profile", handle.group(1))
                    fragments = [fragment]
                    self._mark_mirror_success(fragments, "twitter", "fxtwitter", telemetry)

        # 3. Phase 6.8: Entity-to-Social-Source Resolution for X
        if not fragments and self.router.use_fxtwitter:
            resolution = entity_social_resolver.resolve(query)
            telemetry.update(
                resolved_entity=resolution.normalized_entity,
                entity_sector=resolution.sector,
                x_candidate_count=len(resolution.x_candidates),
            )
            for cand in resolution.x_candidates:
                prof_frag = self.router._fetch_fxtwitter_profile(cand.handle)
                if prof_frag and prof_frag.content:
                    prof_frag.content_depth = "PROFILE_METADATA"
                    prof_frag.raw_metadata.update(
                        resolved_entity=resolution.normalized_entity,
                        relationship=cand.relationship,
                        confidence=cand.confidence,
                        verification_evidence=cand.verification_evidence,
                        entity_id=cand.entity_id,
                        official_website=cand.official_website,
                    )
                    self._annotate([prof_frag], "entity_resolution", "profile_metadata", cand.handle)
                    fragments.append(prof_frag)

                # Attempt discovery of concrete status permalinks for this verified handle
                try:
                    scoped_q = f"site:x.com/{cand.handle}/status"
                    status_frags = self.router._execute_web_search(scoped_q, 5, query_id, query_class, query_text)
                    for sf in status_frags:
                        m_stat = re.search(r"status/([0-9]{5,25})", sf.url)
                        if m_stat:
                            sid = m_stat.group(1)
                            st_frag = self.router._fetch_fxtwitter_status(cand.handle, sid)
                            if st_frag and st_frag.content:
                                st_frag.content_depth = "TWEET_STATUS"
                                st_frag.raw_metadata.update(
                                    resolved_entity=resolution.normalized_entity,
                                    handle=cand.handle,
                                    entity_id=cand.entity_id,
                                )
                                self._annotate([st_frag], "entity_status_discovery", "full_status", sid)
                                if not any(f.url == st_frag.url for f in fragments):
                                    fragments.append(st_frag)
                except Exception as e_status:
                    logger.debug(f"[SocialHandlers] Scoped status discovery notice for @{cand.handle}: {e_status}")

                if len(fragments) >= (limit or 10):
                    break

            if fragments:
                self._mark_mirror_success(fragments, "twitter", "fxtwitter", telemetry)
                telemetry.update(discovered_from="entity_resolution", mirror_result="SUCCESS")
                return fragments[:limit] if limit else fragments

        # 4. Search Discovery for Tweet Status URLs
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

        # 5. Strict Verified Web Index Fallback
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
        """
        Execute search index fallback with strict platform-domain validation.
        Rejects non-platform URLs (e.g. corporate websites) from masquerading as social.
        """
        if platform == "reddit":
            search_query, reason, label, method = f"site:reddit.com {query}", "ARCTIC_SHIFT_UNAVAILABLE", "Reddit", "reddit_web_index"
            allowed_domains = ("reddit.com", "old.reddit.com", "redd.it")
        else:
            search_query, reason, label, method = f"site:twitter.com OR site:x.com {query}", "FXTWITTER_SEARCH_INDEX_FALLBACK", "Twitter", "twitter_web_index"
            allowed_domains = ("twitter.com", "x.com", "mobile.twitter.com")

        effective_limit = max(limit, 25) if limit else 25
        raw_fragments = self.router._execute_web_search(search_query, effective_limit, query_id, query_class, query_text)

        # STRICT URL VALIDATION: Prioritize genuine platform URLs if present
        platform_fragments = [
            f for f in raw_fragments
            if any(
                urllib.parse.urlparse(f.url).netloc.lower() == d
                or urllib.parse.urlparse(f.url).netloc.lower().endswith(f".{d}")
                for d in allowed_domains
            )
        ]
        fragments = platform_fragments if platform_fragments else raw_fragments

        if fragments:
            self.router._tag_fragments(fragments, platform, "web_search", RetrievalMode.WEB_SEARCH_INDEX.value, "bing-search-index", reason, False)
            for fragment in fragments:
                fragment.platform = f"{label} (Web Index Fallback)"
                fragment.retrieval_method = method
                fragment.content_depth = "INDEX_SNIPPET"
                fragment.raw_metadata.update(
                    source_tier="TIER_3_AGGREGATE",
                    honest_disclosure="Public mirror returned no usable item; retrieved through a public search index",
                    is_direct_platform_url=bool(platform_fragments),
                )
            telemetry.update(
                status="SUCCESS", fallback_used=True,
                fallback_backend="Bing Search Index", fallback_reason=reason,
                retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                valid_social_urls_retained=len(platform_fragments),
            )
        else:
            telemetry.update(
                status="DEGRADED", fallback_used=True,
                fallback_backend="Bing Search Index",
                fallback_reason=f"{reason}: ZERO_INDEX_RESULTS",
                retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value,
                valid_social_urls_retained=0,
            )

        return fragments[:limit] if limit else fragments

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
