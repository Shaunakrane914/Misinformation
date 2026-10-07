"""
Aegis Protocol — Unit Tests for Zero-Auth Source Discovery & URL Identification
================================================================================
Validates exact URL parsing, query extraction, search discovery deduplication,
scoring, mirror routing, and provenance attribution for Reddit and X/Twitter.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode
from backend.services.agent_reach.native.router import NativeRouter
from backend.services.agent_reach.native.source_discovery import (
    SourceDiscoveryResult,
    calculate_candidate_score,
    discover_sources_from_search,
    extract_reddit_source,
    extract_x_source,
)


@pytest.fixture
def router():
    return NativeRouter()


# ==============================================================================
# Reddit URL & Query Extraction Tests
# ==============================================================================

def test_reddit_exact_post_url():
    url = "https://www.reddit.com/r/technology/comments/1b09bqu/openai_releases_new_model/"
    res = extract_reddit_source(url)
    assert res is not None
    assert res.platform == "reddit"
    assert res.source_type == "post"
    assert res.external_id == "1b09bqu"
    assert res.subreddit == "technology"
    assert res.canonical_url == "https://www.reddit.com/r/technology/comments/1b09bqu"


def test_reddit_post_url_with_query_params():
    url = "https://reddit.com/r/science/comments/z1c9z/ama_post/?utm_source=share&utm_medium=web2x&context=3"
    res = extract_reddit_source(url)
    assert res is not None
    assert res.external_id == "z1c9z"
    assert res.subreddit == "science"
    assert "utm_source" not in res.canonical_url


def test_reddit_short_comments_url():
    url = "https://www.reddit.com/comments/abc123z"
    res = extract_reddit_source(url)
    assert res is not None
    assert res.external_id == "abc123z"
    assert res.source_type == "post"
    assert res.canonical_url == "https://www.reddit.com/comments/abc123z"


def test_reddit_short_domain_url():
    url = "https://redd.it/1b09bqu"
    res = extract_reddit_source(url)
    assert res is not None
    assert res.external_id == "1b09bqu"
    assert res.canonical_url == "https://www.reddit.com/comments/1b09bqu"


def test_reddit_comment_permalink():
    url = "https://www.reddit.com/r/technology/comments/1b09bqu/title_slug/ks67890"
    res = extract_reddit_source(url)
    assert res is not None
    assert res.source_type == "comment"
    assert res.external_id == "ks67890"
    assert res.parent_id == "1b09bqu"


def test_reddit_subreddit_url():
    url = "https://www.reddit.com/r/technology"
    res = extract_reddit_source(url)
    assert res is not None
    assert res.source_type == "subreddit"
    assert res.external_id == "technology"
    assert res.subreddit == "technology"


def test_reddit_rejects_non_content_pages():
    assert extract_reddit_source("https://www.reddit.com/search?q=test") is None
    assert extract_reddit_source("https://www.reddit.com/user/someone") is None
    assert extract_reddit_source("https://www.reddit.com/settings") is None
    assert extract_reddit_source("https://www.reddit.com/") is None
    assert extract_reddit_source("not a url") is None


def test_reddit_malformed_url():
    assert extract_reddit_source("https://www.reddit.com/r//comments//") is None
    assert extract_reddit_source("https://otherdomain.com/r/tech/comments/123") is None


# ==============================================================================
# X / Twitter URL & Query Extraction Tests
# ==============================================================================

def test_x_exact_status_url_x_domain():
    url = "https://x.com/BarackObama/status/266031293945503744"
    res = extract_x_source(url)
    assert res is not None
    assert res.platform == "twitter"
    assert res.source_type == "status"
    assert res.external_id == "266031293945503744"
    assert res.handle == "BarackObama"
    assert res.canonical_url == "https://x.com/BarackObama/status/266031293945503744"


def test_x_exact_status_url_twitter_domain():
    url = "https://twitter.com/jack/status/20?s=20"
    res = extract_x_source(url)
    assert res is not None
    assert res.external_id == "20"
    assert res.handle == "jack"
    assert "s=20" not in res.canonical_url


def test_x_status_url_with_i_path():
    url = "https://x.com/i/status/1765050868884930606"
    res = extract_x_source(url)
    assert res is not None
    assert res.external_id == "1765050868884930606"
    assert res.source_type == "status"


def test_x_profile_url():
    url = "https://x.com/WHO"
    res = extract_x_source(url)
    assert res is not None
    assert res.source_type == "profile"
    assert res.external_id == "WHO"
    assert res.handle == "WHO"


def test_x_profile_does_not_default_to_nasa():
    res_who = extract_x_source("https://x.com/WHO")
    assert res_who.handle == "WHO"
    assert res_who.handle != "NASA"

    res_custom = extract_x_source("https://twitter.com/custom_analyst")
    assert res_custom.handle == "custom_analyst"
    assert res_custom.handle != "NASA"


def test_x_rejects_reserved_pages():
    assert extract_x_source("https://x.com/explore") is None
    assert extract_x_source("https://x.com/home") is None
    assert extract_x_source("https://twitter.com/search?q=test") is None
    assert extract_x_source("https://x.com/settings") is None
    assert extract_x_source("https://x.com/") is None


def test_x_malformed_url():
    assert extract_x_source("https://x.com/status/notanumber") is None
    assert extract_x_source("https://x.com/user/status/") is None


# ==============================================================================
# Search URL Discovery & Deduplication Tests
# ==============================================================================

def test_search_discovery_reddit_extraction_and_deduplication():
    frags = [
        EvidenceFragment(
            platform="Web",
            title="OpenAI releases new model - Reddit",
            snippet="Discussion on r/technology about the new release.",
            url="https://www.reddit.com/r/technology/comments/1b09bqu/openai_releases_new_model/",
        ),
        EvidenceFragment(
            platform="Web",
            title="Duplicate link with tracking parameters",
            snippet="Same post with tracking params.",
            url="https://old.reddit.com/r/technology/comments/1b09bqu/openai_releases_new_model/?utm_source=bing",
        ),
        EvidenceFragment(
            platform="Web",
            title="Another Reddit Post",
            snippet="A different thread.",
            url="https://www.reddit.com/r/science/comments/z1c9z/another_discussion/",
        ),
        EvidenceFragment(
            platform="Web",
            title="Reddit search page (should be rejected)",
            snippet="Search results on reddit.",
            url="https://www.reddit.com/search?q=openai",
        ),
    ]

    candidates = discover_sources_from_search(frags, platform="reddit", query="openai new model")
    # Should deduplicate 1b09bqu and reject search page -> exactly 2 distinct post candidates
    assert len(candidates) == 2
    post_ids = [c.external_id for c in candidates]
    assert "1b09bqu" in post_ids
    assert "z1c9z" in post_ids
    assert all(c.discovered_from == "search_url_discovery" for c in candidates)


def test_search_discovery_x_extraction_and_deduplication():
    frags = [
        EvidenceFragment(
            platform="Web",
            title="Jack on Twitter: 'just setting up my twttr'",
            snippet="Jack Dorsey first tweet.",
            url="https://twitter.com/jack/status/20",
        ),
        EvidenceFragment(
            platform="Web",
            title="Jack tweet duplicate on x.com",
            snippet="Duplicate tweet.",
            url="https://x.com/jack/status/20?ref=share",
        ),
        EvidenceFragment(
            platform="Web",
            title="Barack Obama post",
            snippet="Four more years.",
            url="https://x.com/BarackObama/status/266031293945503744",
        ),
        EvidenceFragment(
            platform="Web",
            title="X explore page (should be rejected)",
            snippet="Explore trending.",
            url="https://x.com/explore",
        ),
    ]

    candidates = discover_sources_from_search(frags, platform="twitter", query="jack tweet")
    assert len(candidates) == 2
    status_ids = [c.external_id for c in candidates]
    assert "20" in status_ids
    assert "266031293945503744" in status_ids


def test_candidate_ranking_prefers_specific_matches():
    c_post = SourceDiscoveryResult(
        platform="reddit",
        canonical_url="https://reddit.com/r/tech/comments/123",
        source_type="post",
        external_id="123",
        raw_title="OpenAI releases GPT-5 in surprise announcement",
        raw_snippet="The tech community reacts to GPT-5 release.",
    )
    c_sub = SourceDiscoveryResult(
        platform="reddit",
        canonical_url="https://reddit.com/r/technology",
        source_type="subreddit",
        external_id="technology",
        raw_title="Technology Subreddit",
        raw_snippet="All about technology.",
    )

    score_post = calculate_candidate_score(
        c_post, target_entity="OpenAI", target_topic="GPT-5", target_claim="surprise release"
    )
    score_sub = calculate_candidate_score(
        c_sub, target_entity="OpenAI", target_topic="GPT-5", target_claim="surprise release"
    )

    assert score_post > score_sub


# ==============================================================================
# End-to-End Routing & Provenance Verification Tests
# ==============================================================================

def test_reddit_discovery_to_mirror_provenance(router):
    """
    Search discovery -> Arctic Shift batch post lookup -> verified zero-auth public mirror provenance.
    """
    mock_search_results = [
        EvidenceFragment(
            platform="Web",
            title="Reddit Discussion on Deep Learning",
            snippet="Users discuss latest breakthroughs.",
            url="https://www.reddit.com/r/MachineLearning/comments/1b09bqu/deep_learning/",
        )
    ]
    mock_post_data = {
        "data": [
            {
                "id": "1b09bqu",
                "title": "Deep Learning Breakthroughs",
                "selftext": "Comprehensive analysis of modern deep learning architectures.",
                "author": "researcher_42",
                "subreddit": "MachineLearning",
                "score": 520,
                "num_comments": 45,
                "created_utc": 1708890000,
            }
        ]
    }

    with patch.object(router, "_execute_web_search", return_value=mock_search_results):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_post_data).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            frags, telem = router.execute_channel_query(
                platform="reddit",
                query="deep learning breakthroughs",
                limit=5
            )

            assert len(frags) >= 1
            primary = frags[0]
            # Verify Provenance
            assert primary.retrieval_mode == RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
            assert primary.native_backend_id == "arctic_shift"
            assert primary.is_authenticated is False
            assert primary.raw_metadata["discovered_from"] == "search_url_discovery"
            assert primary.raw_metadata["post_id"] == "1b09bqu"
            assert telem["backend"] == "arctic_shift"
            assert telem["discovered_from"] == "search_url_discovery"


def test_x_discovery_to_mirror_provenance(router):
    """
    Search discovery -> FxTwitter status lookup -> verified zero-auth public mirror provenance.
    """
    mock_search_results = [
        EvidenceFragment(
            platform="Web",
            title="Jack Dorsey on Twitter",
            snippet="First ever tweet.",
            url="https://x.com/jack/status/20",
        )
    ]
    mock_tweet_data = {
        "code": 200,
        "tweet": {
            "id": "20",
            "text": "just setting up my twttr",
            "author": {"name": "jack", "screen_name": "jack"},
            "created_at": "Tue Mar 21 20:50:14 +0000 2006",
            "likes": 180000,
            "retweets": 120000,
            "replies": 10000,
        }
    }

    with patch.object(router, "_execute_web_search", return_value=mock_search_results):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_tweet_data).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            frags, telem = router.execute_channel_query(
                platform="twitter",
                query="jack first tweet ever",
                limit=5
            )

            assert len(frags) >= 1
            primary = frags[0]
            assert primary.retrieval_mode == RetrievalMode.ZERO_AUTH_PUBLIC_MIRROR.value
            assert primary.native_backend_id == "fxtwitter"
            assert primary.is_authenticated is False
            assert primary.raw_metadata["discovered_from"] == "search_url_discovery"
            assert primary.raw_metadata["external_id"] == "20"
            assert telem["backend"] == "fxtwitter"
            assert telem["discovered_from"] == "search_url_discovery"


def test_mirror_failure_falls_back_to_search_with_honest_disclosure(router):
    """
    When search discovery yields no valid IDs or mirror fails, router cleanly
    falls back to search index with honest non-direct disclosure.
    """
    # Web search for discovery returns empty or non-social pages
    fallback_frag = EvidenceFragment(
        platform="Web",
        title="News Article referencing Twitter statement",
        snippet="A news site quoting a tweet.",
        url="https://news.example.com/article/1",
        retrieval_mode=RetrievalMode.WEB_SEARCH_INDEX.value
    )
    with patch.object(router, "_execute_web_search") as mock_search:
        mock_search.side_effect = lambda q, *args, **kwargs: (
            [fallback_frag] if "site:twitter.com OR site:x.com obscure" in q else []
        )
        frags, telem = router.execute_channel_query(
            platform="twitter",
            query="obscure unindexed statement",
            limit=5
        )

        assert len(frags) >= 1
        primary = frags[0]
        # Must NOT claim direct mirror
        assert primary.retrieval_mode == RetrievalMode.WEB_SEARCH_INDEX.value
        assert telem["fallback_used"] is True
        assert primary.is_authenticated is False
        assert "Twitter (Web Index Fallback)" in primary.platform


def test_anti_token_cheat_entity_matching():
    """
    Ensure single-token overlap does NOT cheat semantic relevance.
    """
    from backend.services.agent_reach.native.source_discovery import (
        check_entity_semantic_match,
        evaluate_content_relevance,
        BlindSecondaryAdjudicator,
    )

    # 1. 'Satya Nadella': reject incense
    incense_text = "I love Satya Sai Baba blue box agarbatti incense sticks for meditation."
    match, weight = check_entity_semantic_match(incense_text, "Satya Nadella")
    assert match is False
    assert weight == 0

    # 2. 'Satya Nadella': accept real tech context
    tech_text = "Satya Nadella announced Microsoft's new Copilot and OpenAI compute strategy."
    match, weight = check_entity_semantic_match(tech_text, "Satya Nadella")
    assert match is True
    assert weight == 2

    # 3. 'Sam Altman': reject Lord of the Rings
    lotr_text = "Frodo and Samwise journeyed to Mordor to destroy the One Ring."
    match, weight = check_entity_semantic_match(lotr_text, "Sam Altman")
    assert match is False
    assert weight == 0

    # 4. 'Sam Altman': accept Altman OpenAI
    openai_text = "Altman emphasized the need for nuclear power to feed OpenAI data center clusters."
    match, weight = check_entity_semantic_match(openai_text, "Sam Altman")
    assert match is True
    assert weight == 2

    # 5. 'Jensen Huang': reject League of Legends Jensen
    lol_text = "Jensen played mid lane for Cloud9 in the LCS championship."
    match, weight = check_entity_semantic_match(lol_text, "Jensen Huang")
    assert match is False
    assert weight == 0


def test_platform_scope_hard_reject():
    """
    Hard platform scope rule: requested r/investing but candidate is in r/privacy -> HARD REJECT.
    """
    from backend.services.agent_reach.native.source_discovery import evaluate_content_relevance

    content = "Discussion on portfolio diversification, index funds, and stock returns."
    res = evaluate_content_relevance(
        content=content,
        target_entity="stocks",
        target_topic="Portfolio allocation",
        target_claim="Long term market returns",
        requested_scope="r/investing",
        candidate_metadata={"subreddit": "privacy"}
    )
    assert res["platform_scope"] == 0
    assert res["source_correctness"] == 0
    assert res["accepted"] is False
    assert res["semantic_score"] == -1000.0


def test_blind_secondary_adjudicator():
    """
    Verify blind secondary adjudicator evaluates content independently.
    """
    from backend.services.agent_reach.native.source_discovery import BlindSecondaryAdjudicator

    adjudicator = BlindSecondaryAdjudicator()
    res = adjudicator.evaluate(
        query="AMD MI350 AI accelerator demand",
        target_entity="AMD",
        target_topic="Hardware",
        target_claim="Discussions of AMD MI350 GPU demand",
        content="AMD MI350 accelerators are seeing massive demand from hyperscalers looking for alternatives to Nvidia H100 and Blackwell GPUs with competitive HBM3e capacity."
    )
    assert res["source_correctness"] == 2
    assert res["content_relevance"] == 2
    assert res["claim_support"] >= 1
    assert res["accepted"] is True

