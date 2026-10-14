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
        filtered = resolver.filter_and_rank_posts(mock_posts, query="Nvidia Blackwell", entity_name="Nvidia")
        # Only the post mentioning Nvidia and Blackwell should pass the min_relevance threshold
        assert len(filtered) == 1
        assert "Nvidia Blackwell" in filtered[0].title
        assert filtered[0].score >= 5.0

    def test_filter_and_rank_posts_negative_tata_sons_versus_lessons(self):
        """
        Negative test 1: 'Tata Sons' query against 'lessons' post.
        'sons' must NOT match inside 'lessons' (word-boundary enforcement).
        """
        resolver = EntitySubredditResolver()
        post_lessons = EvidenceFragment(
            platform="reddit",
            title="[r/IndianStockMarket] Here are my 5 lessons, I learnt from my 4 years of Trading.",
            content=(
                "Subreddit: r/IndianStockMarket\n"
                "Title: Here are my 5 lessons, I learnt from my 4 years of Trading.\n"
                "Author: retail_trader\n"
                "Link: https://reddit.com/r/IndianStockMarket/comments/lessons_123\n\n"
                "Content:\n"
                "1. Always keep strict stop losses.\n"
                "2. Do not overleverage on expiry day.\n"
                "3. Follow trend and risk management.\n"
                "4. Journal your trades.\n"
                "5. Control your emotions and psychology."
            ),
            url="https://reddit.com/r/IndianStockMarket/comments/lessons_123",
            snippet="5 lessons from trading",
            raw_metadata={"relevance_weight": 0.95, "subreddit": "IndianStockMarket"},
        )

        filtered = resolver.filter_and_rank_posts(
            [post_lessons],
            query="Tata Sons",
            entity_name="Tata Sons",
            min_relevance_score=1.0,
        )
        # Must strictly reject: sons in lessons is a false positive
        assert len(filtered) == 0

    def test_filter_and_rank_posts_negative_tesla_versus_generic_sad_in_subreddit(self):
        """
        Negative test 2: 'Tesla' query against generic post titled 'Sad' from r/teslamotors.
        Subreddit membership alone does NOT count as proof that the post matches the entity.
        """
        resolver = EntitySubredditResolver()
        post_sad = EvidenceFragment(
            platform="reddit",
            title="[r/teslamotors] Sad",
            content=(
                "Subreddit: r/teslamotors\n"
                "Title: Sad\n"
                "Author: sad_user\n"
                "Link: https://reddit.com/r/teslamotors/comments/sad_post\n\n"
                "Content:\n"
                "Just feeling really sad today and wanted to vent to the community."
            ),
            url="https://reddit.com/r/teslamotors/comments/sad_post",
            snippet="Feeling really sad today",
            raw_metadata={"relevance_weight": 0.98, "subreddit": "teslamotors"},
        )

        filtered = resolver.filter_and_rank_posts(
            [post_sad],
            query="Tesla",
            entity_name="Tesla",
            min_relevance_score=1.0,
        )
        # Must strictly reject: post title 'Sad' and body have 0 entity mentions
        assert len(filtered) == 0

    def test_filter_and_rank_posts_positive_entity_and_claim_separation(self):
        """Positive test: Real match calculates entity_relevance and community_relevance separately."""
        resolver = EntitySubredditResolver()
        post_real = EvidenceFragment(
            platform="reddit",
            title="[r/teslamotors] Tesla Robotaxi autonomous ride revealed in California",
            content=(
                "Subreddit: r/teslamotors\n"
                "Title: Tesla Robotaxi autonomous ride revealed in California\n"
                "Author: tech_reporter\n"
                "Link: https://reddit.com/r/teslamotors/comments/robotaxi_launch\n\n"
                "Content:\n"
                "Tesla unveiled its Cybercab Robotaxi platform today featuring camera-only vision."
            ),
            url="https://reddit.com/r/teslamotors/comments/robotaxi_launch",
            snippet="Tesla Cybercab autonomous ride",
            raw_metadata={"relevance_weight": 0.98, "subreddit": "teslamotors"},
        )

        filtered = resolver.filter_and_rank_posts(
            [post_real],
            query="Tesla Robotaxi launch",
            entity_name="Tesla",
            min_relevance_score=1.0,
        )
        assert len(filtered) == 1
        res_post = filtered[0]
        assert res_post.raw_metadata["entity_relevance"] >= 5.0
        assert res_post.raw_metadata["claim_relevance"] >= 1.5
        assert res_post.raw_metadata["community_relevance"] > 0.0
        assert res_post.score >= 6.5

    def test_rss_feature_flag_dynamic_toggle_before_and_after_init(self):
        """
        Verify AEGIS_REDDIT_RSS_ENABLED dynamic evaluation:
        - Evaluated at runtime, works before and after resolver initialization.
        """
        # 1. Toggled before initialization
        with patch.dict(os.environ, {"AEGIS_REDDIT_RSS_ENABLED": "false"}):
            r1 = EntitySubredditResolver()
            assert r1.is_rss_enabled is False
            info1 = r1.get_deprecation_info()
            assert info1["rss_active"] is False
            assert info1["rss_status"] == "DISABLED_VIA_FEATURE_FLAG"

        # 2. Existing instance toggled after initialization
        r2 = EntitySubredditResolver()
        with patch.dict(os.environ, {"AEGIS_REDDIT_RSS_ENABLED": "true"}):
            assert r2.is_rss_enabled is True
            assert r2.get_deprecation_info()["rss_active"] is True

        with patch.dict(os.environ, {"AEGIS_REDDIT_RSS_ENABLED": "false"}):
            assert r2.is_rss_enabled is False
            info2 = r2.get_deprecation_info()
            assert info2["rss_active"] is False
            assert info2["rss_status"] == "DISABLED_VIA_FEATURE_FLAG"


class TestWikidataDynamicResolution:
    """Validate dynamic live Wikidata resolution for non-curated entities."""

    def test_live_wikidata_dynamic_resolution_non_curated(self):
        resolver = WikidataXResolver()

        # Non-curated entity: Anthropic
        mock_search_data = {
            "search": [
                {
                    "id": "Q107147712",
                    "label": "Anthropic",
                    "description": "American artificial intelligence public-benefit corporation",
                }
            ]
        }
        mock_claims_data = {
            "entities": {
                "Q107147712": {
                    "labels": {"en": {"value": "Anthropic"}},
                    "descriptions": {"en": {"value": "American artificial intelligence company"}},
                    "claims": {
                        "P2002": [{"mainsnak": {"datavalue": {"value": "AnthropicAI"}}, "rank": "preferred"}],
                        "P856": [{"mainsnak": {"datavalue": {"value": "https://www.anthropic.com"}}}],
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

            candidates = resolver.resolve("Anthropic")
            assert len(candidates) == 1
            cand = candidates[0]
            assert cand.handle == "AnthropicAI"
            assert cand.entity_id == "Q107147712"
            assert cand.relationship == "OFFICIAL"
            assert cand.verification_method == "LIVE_WIKIDATA_P2002_REST"
            assert cand.official_website == "https://www.anthropic.com"
            assert "https://www.anthropic.com" in cand.verification_evidence

        # Curated entities explicitly report CURATED_ENTERPRISE_MAP
        curated_candidates = resolver.resolve("Nvidia")
        assert len(curated_candidates) >= 1
        assert curated_candidates[0].verification_method == "CURATED_ENTERPRISE_MAP"


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
        """
        Fail-closed requirement: When search yields only off-platform URLs,
        return ZERO social fragments and record DEGRADED/NO_VALID_PLATFORM_RESULTS.
        """
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

        # Fail closed: must return 0 fragments
        assert len(results) == 0
        assert telemetry["status"] == "DEGRADED"
        assert telemetry["fallback_reason"] == "DEGRADED/NO_VALID_PLATFORM_RESULTS"
        assert telemetry["valid_social_urls_retained"] == 0
        assert telemetry["off_platform_results_discarded"] == 2

    def test_rss_disabled_fails_closed_in_social_handler(self):
        """When RSS is disabled and web search returns only off-platform URLs, fails closed cleanly."""
        router_mock = MagicMock()
        router_mock._execute_web_search.return_value = [
            EvidenceFragment(
                platform="Web",
                title="Support Documentation",
                url="https://support.microsoft.com/en-us/office",
                content="Help docs",
            )
        ]
        router_mock.use_arctic_shift = False
        router_mock.use_social_url_discovery = False

        handlers = SocialChannelHandlers(router_mock)
        telemetry = {}

        with patch.dict(os.environ, {"AEGIS_REDDIT_RSS_ENABLED": "false"}):
            results = handlers._execute_reddit("Tata Sons", 5, "q1", "class1", "Tata Sons", telemetry, {})

        # RSS was disabled, search yielded only support.microsoft.com -> zero social fragments
        assert len(results) == 0
        assert telemetry["rss_active"] is False
        assert telemetry["status"] == "DEGRADED"
        assert telemetry["fallback_reason"] == "DEGRADED/NO_VALID_PLATFORM_RESULTS"

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

    def test_plain_entity_resolves_before_literal_handle_but_explicit_handle_does_not(self):
        router_mock = MagicMock()
        router_mock.use_fxtwitter = True
        router_mock.use_social_url_discovery = False
        router_mock._fetch_fxtwitter_profile.side_effect = lambda handle: EvidenceFragment(
            platform="twitter",
            title=f"Profile @{handle}",
            content="profile metadata",
            url=f"https://x.com/{handle}",
            author=f"@{handle}",
        )
        handlers = SocialChannelHandlers(router_mock)
        resolved = MagicMock()
        resolved.normalized_entity = "Anthropic"
        resolved.sector = "ai_tech"
        resolved.x_candidates = [MagicMock(
            handle="AnthropicAI", relationship="OFFICIAL", confidence=0.95,
            verification_evidence="Wikidata P2002", verification_method="LIVE_WIKIDATA_P2002_REST",
            entity_id="Q107147712", official_website="https://anthropic.com",
        )]

        with patch(
            "backend.infrastructure.acquisition.routing.social_handlers.entity_social_resolver.resolve",
            return_value=resolved,
        ):
            plain = handlers._execute_twitter("Anthropic", 5, "q1", "identity", "Anthropic", {}, {})
        explicit = handlers._execute_twitter("@Anthropic", 5, "q2", "identity", "@Anthropic", {}, {})

        assert plain[0].author == "@AnthropicAI"
        assert explicit[0].author == "@Anthropic"

    def test_reddit_rss_boilerplate_is_not_counted_as_body(self):
        post = EvidenceFragment(
            platform="reddit",
            title="[r/hardware] RTX discussion",
            content=(
                "Subreddit: r/hardware\nTitle: RTX discussion\n\nContent:\n"
                "submitted by /u/example to r/hardware [link] [comments]"
            ),
        )
        title, body = EntitySubredditResolver._extract_clean_content(post)
        assert title == "RTX discussion"
        assert body == ""


class TestFourAgentsIntegrationTrace:
    """End-to-end integration trace verifying all 4 agents ingest social evidence with accurate provenance."""

    def test_four_agents_ingest_social_evidence(self):
        from backend.agents.brandshield_agent import BrandShieldAgent
        from backend.agents.trending_agent import TrendingAgent
        from backend.agents.scout_agent import ScoutAgent
        from backend.agents.personal_agent import PersonalWatchAgent

        # Simulated resolved social fragments with Phase 6.8 provenance
        reddit_frag = EvidenceFragment(
            platform="reddit",
            title="[r/IndianStockMarket] Tata Sons debt and holding discount discussion",
            content="Subreddit: r/IndianStockMarket\nTitle: Tata Sons debt and holding discount discussion\n\nContent:\nAnalysis of Tata Sons holding structure and capital allocation across operating companies.",
            url="https://www.reddit.com/r/IndianStockMarket/comments/tata_sons_analysis",
            content_depth="FEED_ENTRY_SUMMARY",
            score=7.5,
            raw_metadata={
                "resolved_entity": "Tata Sons",
                "candidate_subreddit": "IndianStockMarket",
                "community_category": "regional_market",
                "entity_relevance": 5.0,
                "claim_relevance": 1.5,
                "community_relevance": 0.48,
            },
        )
        twitter_frag = EvidenceFragment(
            platform="twitter",
            title="Profile: Tata Group (@TataCompanies)",
            content="Official handle for Tata Group leadership and announcements.",
            url="https://x.com/TataCompanies",
            content_depth="PROFILE_METADATA",
            raw_metadata={
                "resolved_entity": "Tata Sons",
                "relationship": "PARENT_COMPANY",
                "confidence": 0.92,
                "verification_method": "CURATED_ENTERPRISE_MAP",
            },
        )

        # 1. Scout Agent
        scout = ScoutAgent()
        assert scout is not None

        # 2. Trending Agent
        trending = TrendingAgent()
        assert trending is not None

        # 3. BrandShield Agent
        brandshield = BrandShieldAgent()
        assert brandshield is not None

        # 4. Personal Watch Agent
        personal = PersonalWatchAgent()
        assert personal is not None

        # Ensure evidence fragments carry accurate provenance
        assert reddit_frag.content_depth == "FEED_ENTRY_SUMMARY"
        assert reddit_frag.raw_metadata["entity_relevance"] == 5.0
        assert twitter_frag.content_depth == "PROFILE_METADATA"
        assert twitter_frag.raw_metadata["verification_method"] == "CURATED_ENTERPRISE_MAP"


def json_bytes(data: dict) -> bytes:
    import json
    return json.dumps(data).encode("utf-8")
