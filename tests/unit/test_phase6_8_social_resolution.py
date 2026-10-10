"""
Unit and integration tests for Phase 6.8: Entity-to-Social-Source Resolution.
Verifies:
1. Wikidata ambiguity resolution and candidate ranking
2. Relationship labeling (OFFICIAL, PARENT_COMPANY, SUBSIDIARY)
3. Entity-to-subreddit community mapping & post relevance filtering
4. Reddit RSS shutdown governance & feature flag degradation
5. Strict platform URL validation preventing fake search fallback leakage
6. Accurate content depth classification
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from backend.infrastructure.acquisition.resolution.social_resolver import (
    EntitySocialResolver,
    EntitySubredditResolver,
    REDDIT_RSS_SUNSET_DATE,
    ResolvedXCandidate,
    SubredditCandidate,
    WikidataXResolver,
    entity_social_resolver,
)
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode
from backend.infrastructure.acquisition.routing.social_handlers import SocialChannelHandlers


class TestWikidataXResolver:
    """Test entity ambiguity handling and candidate ranking in WikidataXResolver."""

    def test_curated_enterprise_benchmark_entities(self):
        resolver = WikidataXResolver()

        # Tata Sons -> Parent company & subsidiary handles
        tata_res = resolver.resolve("Tata Sons")
        assert len(tata_res) >= 2
        handles = [c.handle for c in tata_res]
        assert "TataCompanies" in handles
        assert "TataMotors" in handles
        assert any(c.relationship == "PARENT_COMPANY" for c in tata_res)
        assert any(c.relationship == "SUBSIDIARY" for c in tata_res)

        # Nvidia -> Official handle
        nvda_res = resolver.resolve("Nvidia")
        assert len(nvda_res) >= 1
        assert nvda_res[0].handle == "nvidia"
        assert nvda_res[0].relationship == "OFFICIAL"
        assert nvda_res[0].confidence >= 0.95

        # OpenAI -> Official handle
        openai_res = resolver.resolve("OpenAI")
        assert len(openai_res) >= 1
        assert openai_res[0].handle == "OpenAI"
        assert openai_res[0].relationship == "OFFICIAL"

        # Tesla -> Official handle
        tesla_res = resolver.resolve("Tesla")
        assert len(tesla_res) >= 1
        assert tesla_res[0].handle in ("Tesla", "TeslaMotors")

        # Reliance Industries -> Official handle
        ril_res = resolver.resolve("Reliance Industries")
        assert len(ril_res) >= 1
        assert ril_res[0].handle == "RIL_Updates"
        assert ril_res[0].relationship == "OFFICIAL"

    def test_ambiguity_filtering_rejects_unrelated_types(self):
        resolver = WikidataXResolver()

        # Mock a search response containing a musical band, a unit of measurement, and a company
        mock_search_data = {
            "search": [
                {"id": "Q163343", "label": "tesla", "description": "SI unit of magnetic flux density"},
                {"id": "Q1428953", "label": "Tesla", "description": "American musical group; hard rock band"},
                {"id": "Q478214", "label": "Tesla", "description": "American multinational automotive and clean energy company"},
            ]
        }
        mock_claims_data = {
            "entities": {
                "Q478214": {
                    "labels": {"en": {"value": "Tesla, Inc."}},
                    "descriptions": {"en": {"value": "automotive and clean energy company"}},
                    "claims": {
                        "P2002": [{"mainsnak": {"datavalue": {"value": "Tesla"}}, "rank": "preferred"}],
                        "P856": [{"mainsnak": {"datavalue": {"value": "https://www.tesla.com"}}}],
                    },
                }
            }
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            resp_search = MagicMock()
            resp_search.__enter__.return_value.read.return_value = json_bytes(mock_search_data)
            resp_claims = MagicMock()
            resp_claims.__enter__.return_value.read.return_value = json_bytes(mock_claims_data)
            mock_urlopen.side_effect = [resp_search, resp_claims]

            candidates = resolver._query_wikidata_live("Tesla Custom Test")
            assert len(candidates) == 1
            assert candidates[0].handle == "Tesla"
            assert candidates[0].entity_id == "Q478214"
            assert "TeslaBand" not in [c.handle for c in candidates]


class TestEntitySubredditResolver:
    """Test community taxonomy mapping, query filtering, and deprecation."""

    def test_brand_and_sector_resolution(self):
        resolver = EntitySubredditResolver()

        # Indian financial entities
        sector, subs = resolver.resolve("Tata Sons")
        assert sector == "indian_markets"
        sub_names = [s.subreddit for s in subs]
        assert "IndianStockMarket" in sub_names

        # Hardware / GPU
        sector, subs = resolver.resolve("Nvidia")
        assert sector == "semiconductor_hardware"
        sub_names = [s.subreddit for s in subs]
        assert "nvidia" in sub_names

        # AI Tech
        sector, subs = resolver.resolve("OpenAI")
        assert sector == "ai_tech"
        assert "OpenAI" in [s.subreddit for s in subs]

        # Automotive EV
        sector, subs = resolver.resolve("Tesla")
        assert sector == "automotive_ev"
        assert "teslamotors" in [s.subreddit for s in subs]

    def test_deprecation_governance_info(self):
        resolver = EntitySubredditResolver()
        info = resolver.get_deprecation_info()
        assert info["rss_sunset_announced"] == REDDIT_RSS_SUNSET_DATE
        assert "rss_active" in info
        assert info["feature_flag"] == "AEGIS_REDDIT_RSS_ENABLED"

    def test_filter_and_rank_posts_relevance(self):
        resolver = EntitySubredditResolver()
        mock_posts = [
            EvidenceFragment(
                platform="reddit",
                title="Generic discussion about market indices",
                content="Nothing about the target company here.",
                url="https://reddit.com/r/stocks/1",
                snippet="Nothing here",
            ),
            EvidenceFragment(
                platform="reddit",
                title="Nvidia Blackwell B200 delivery timelines confirmed",
                content="Detailed report on Nvidia data center GPUs and revenue guidance.",
                url="https://reddit.com/r/stocks/2",
                snippet="Nvidia Blackwell B200 delivery timelines",
            ),
            EvidenceFragment(
                platform="reddit",
                title="Weekend casual chat thread",
                content="How was your week everyone?",
                url="https://reddit.com/r/stocks/3",
                snippet="Casual chat",
            ),
        ]

        filtered = resolver.filter_and_rank_posts(mock_posts, query="Nvidia Blackwell", entity_name="Nvidia")
        # Only the post mentioning Nvidia and Blackwell should pass the min_relevance threshold
        assert len(filtered) == 1
        assert "Nvidia Blackwell" in filtered[0].title
        assert filtered[0].score >= 5.0


class TestSocialChannelHandlersIntegration:
    """Test full integration with SocialChannelHandlers and fallback safety."""

    def test_strict_url_validation_rejects_non_social_urls(self):
        router_mock = MagicMock()
        # Mock Bing returning a mix of genuine reddit and non-reddit URLs
        router_mock._execute_web_search.return_value = [
            EvidenceFragment(
                platform="Web",
                title="Tata Motors Official Site",
                url="https://www.tatamotors.com/about-us",
                content="Automotive manufacturer site",
                snippet="Tata Motors snippet",
            ),
            EvidenceFragment(
                platform="Web",
                title="CarWale Tata Review",
                url="https://www.carwale.com/tata-cars",
                content="Car reviews",
                snippet="CarWale snippet",
            ),
            EvidenceFragment(
                platform="Web",
                title="Reddit Discussion on Tata",
                url="https://www.reddit.com/r/IndianStockMarket/comments/12345/tata_discussion/",
                content="Real reddit discussion",
                snippet="Reddit snippet",
            ),
        ]

        handlers = SocialChannelHandlers(router_mock)
        telemetry = {}
        results = handlers._indexed_fallback("reddit", "Tata Sons", 5, "q1", "class1", "query text", telemetry)

        # Only the reddit.com URL should be retained! Non-reddit URLs MUST be filtered out.
        assert len(results) == 1
        assert "reddit.com" in results[0].url
        assert results[0].content_depth == "INDEX_SNIPPET"
        assert telemetry["valid_social_urls_retained"] == 1

    def test_strict_url_validation_zero_matches_reports_clean_degraded(self):
        router_mock = MagicMock()
        # All returned URLs are non-platform (e.g. Bing completely dropped the site filter)
        router_mock._execute_web_search.return_value = [
            EvidenceFragment(
                platform="Web",
                title="Random Company",
                url="https://www.example.com",
                content="Some web page",
            ),
            EvidenceFragment(
                platform="Web",
                title="Another Page",
                url="https://www.wikipedia.org",
                content="Wikipedia article",
            ),
        ]

        handlers = SocialChannelHandlers(router_mock)
        telemetry = {}
        results = handlers._indexed_fallback("twitter", "Some Entity", 5, "q1", "class1", "query text", telemetry)

        # Non-direct URLs must NEVER claim direct platform status
        assert telemetry["valid_social_urls_retained"] == 0
        assert all(f.raw_metadata.get("is_direct_platform_url") is False for f in results)
        assert all(f.content_depth == "INDEX_SNIPPET" for f in results)
        assert all("Fallback" in f.platform for f in results)
        assert all(f.content_depth != "TWEET_STATUS" for f in results)

    def test_content_depth_preservation_for_profiles_and_feed(self):
        router_mock = MagicMock()
        prof_frag = EvidenceFragment(
            platform="twitter",
            title="Profile: OpenAI (@OpenAI)",
            content="AI Research org bio",
            url="https://x.com/OpenAI",
            author="@OpenAI",
        )
        router_mock._fetch_fxtwitter_profile.return_value = prof_frag
        router_mock._execute_web_search.return_value = []
        router_mock.use_fxtwitter = True

        handlers = SocialChannelHandlers(router_mock)
        telemetry = {}
        results = handlers._execute_twitter("OpenAI", 5, "q1", "class1", "OpenAI", telemetry, {})

        assert len(results) >= 1
        assert results[0].content_depth == "PROFILE_METADATA"
        assert results[0].raw_metadata.get("content_completeness") in ("profile", "profile_metadata")


def json_bytes(data: dict) -> bytes:
    import json
    return json.dumps(data).encode("utf-8")
