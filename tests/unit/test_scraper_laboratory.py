"""
Aegis Protocol — Scraper Laboratory Test Suite
==============================================
Validates the offline/benchmarking scraper laboratory:
  1. Canary execution across all 11 platforms
  2. Failure classification enum
  3. Schema drift detection
  4. Field completeness calculation
  5. Evaluation of production contract support (Section 46)
  6. Website capability registry coverage (Section 24)
"""

import os
import pytest
from scrapers import (
    ScraperErrorClass,
    ScraperLabResult,
    ScraperLabRunner,
    format_health_report,
    format_summary_table,
    scraper_test_registry,
)
from scrapers.base import SchemaDriftReport
from scrapers.fixtures.canaries import CANARY_FIXTURES, get_canary_fixture
from backend.services.agent_reach.native.channel_capabilities import website_capability_registry


def test_scraper_laboratory_registry_coverage():
    """Verify all 11 required website test scrapers are registered."""
    expected_platforms = {
        "reddit", "x", "youtube", "github", "web", "google_news",
        "instagram", "facebook", "tiktok", "linkedin", "bilibili"
    }
    registered = set(scraper_test_registry.list_platforms())
    assert expected_platforms.issubset(registered), f"Missing platforms: {expected_platforms - registered}"


def test_canary_execution_and_result_contract():
    """
    Verify each test scraper executes its canary and returns a compliant ScraperLabResult.
    """
    runner = ScraperLabRunner()
    results = runner.run_all(live_network=False)
    assert len(results) >= 11

    for res in results:
        assert isinstance(res, ScraperLabResult)
        assert res.platform != ""
        assert res.transport_success is True
        assert res.parse_success is True
        assert res.field_completeness > 0.0
        assert res.error_class == ScraperErrorClass.NONE.value
        assert res.health_status in ("HEALTHY", "DEGRADED", "UNHEALTHY")

        d = res.to_dict()
        assert "field_completeness" in d
        assert "latency_ms" in d
        assert "schema_drift" in d


def test_schema_drift_detection_missing_and_wrong_type():
    """
    Verify evaluate_schema_drift flags missing required fields and type mismatches.
    """
    from scrapers.websites.reddit import RedditScraperTest

    test_impl = RedditScraperTest()

    # Incomplete schema missing 'selftext' and wrong type for 'created_utc'
    bad_extracted = {
        "title": "Some title",
        "author": "user1",
        "created_utc": "not_an_int",  # Type mismatch
        "subreddit": "technology",
        # missing 'selftext'
    }

    drift = test_impl.evaluate_schema_drift(
        bad_extracted,
        expected_types={"created_utc": int, "title": str}
    )

    assert drift.detected is True
    assert "selftext" in drift.missing_required_fields
    assert any("created_utc" in m for m in drift.type_mismatches)


def test_failure_classification_categories():
    """
    Verify failure classification taxonomy enum includes all required categories (Section 8).
    """
    required_classes = [
        "TRANSPORT_ERROR", "TIMEOUT", "RATE_LIMITED", "AUTH_REQUIRED",
        "BLOCKED", "NOT_FOUND", "GONE", "CANARY_UNAVAILABLE", "SCHEMA_DRIFT",
        "PARSE_ERROR", "FIELD_MISSING", "CONTENT_TOO_SHORT", "WRONG_SOURCE",
        "WRONG_PLATFORM", "SSRF_BLOCKED", "UNKNOWN"
    ]
    all_enum_values = [e.value for e in ScraperErrorClass]
    for req in required_classes:
        assert req in all_enum_values, f"Missing error category: {req}"


def test_production_contract_support_evaluation():
    """
    Verify ScraperLabRunner evaluates whether website extraction satisfies
    production domain contracts with exact completeness and missing fields.
    """
    runner = ScraperLabRunner()
    extracted_reddit = {
        "title": "Product counterfeit alert",
        "author": "buyer_1",
        "created_utc": 1728000000,
        "subreddit": "technology",
        "selftext": "Found fake seller on marketplace",
        "brand": "Nike",
        "seller": "unknown_shop",
        "product": "Air Max",
        "price": "$90",
        "url": "https://reddit.com/r/technology/comments/fake",
        "domain": "reddit.com",
    }
    compat = runner.evaluate_production_contract_support("reddit", extracted_reddit)
    assert compat["brandshield_compatible"] is True
    assert compat["brandshield"]["completeness_pct"] >= 70.0
    assert "brand" in compat["brandshield"]["present_fields"]
    assert "seller" in compat["brandshield"]["present_fields"]
    # Distinguishes that counterfeit post does NOT satisfy Trending contract
    assert compat["trending_compatible"] is False

    extracted_trending = {
        "title": "Breaking Tech Trend",
        "author": "viral_user",
        "timestamp": "2026-10-07T12:00:00Z",
        "platform": "twitter",
        "content": "Full viral thread discussion",
        "engagement": 45000,
        "narrative": "AI breakthrough",
        "claim": "Major efficiency leap",
    }
    compat_tr = runner.evaluate_production_contract_support("twitter", extracted_trending)
    assert compat_tr["trending_compatible"] is True
    assert compat_tr["trending"]["completeness_pct"] == 100.0


def test_website_capability_registry_fields():
    """
    Verify WebsiteCapabilityRegistry implements the full Section 24 contract.
    """
    rec = website_capability_registry.get("reddit")
    assert rec is not None
    assert rec.platform == "reddit"
    assert rec.primary_backend == "arctic_shift"
    assert rec.zero_auth_supported is True
    assert rec.discovery_supported is True
    assert rec.comments_supported is True
    assert rec.health_status == "HEALTHY"

    walled_rec = website_capability_registry.get("instagram")
    assert walled_rec is not None
    assert walled_rec.auth_required is True
    assert walled_rec.primary_backend == "search_discovery"


def test_production_removal_isolation():
    """
    Verify production acquisition fabric functions cleanly even if scraper.py
    and scrapers/ are completely unreferenced (Section 18).
    """
    import sys
    from backend.services.agent_reach.native.router import NativeRouter
    from backend.services.agent_reach.channels import RetrievalRequest

    router = NativeRouter()
    assert router is not None
    # Verify no scraper modules were imported into production packages
    for mod in list(sys.modules.keys()):
        if mod.startswith("backend."):
            mod_obj = sys.modules[mod]
            if mod_obj and hasattr(mod_obj, "__file__") and mod_obj.__file__:
                assert "scraper.py" not in mod_obj.__file__
                assert "scrapers" not in mod_obj.__file__


def test_backend_truthfulness_and_adapter_coupling():
    """
    Verify reported backend corresponds to actual tested backend and production adapter (Section 3).
    """
    from scrapers.websites.youtube import YouTubeScraperTest
    from scrapers.websites.reddit import RedditScraperTest
    from scrapers.websites.x import TwitterScraperTest
    from scrapers.websites.generic_web import GenericWebScraperTest
    from scrapers.websites.github import GitHubScraperTest

    yt = YouTubeScraperTest()
    assert yt.primary_backend == "yt_dlp_in_process"
    assert yt.adapter.__class__.__name__ == "YouTubeAdapter"

    rd = RedditScraperTest()
    assert rd.primary_backend == "arctic_shift"
    assert rd.adapter.__class__.__name__ == "RedditAdapter"

    tw = TwitterScraperTest()
    assert tw.primary_backend == "fxtwitter"
    assert tw.adapter.__class__.__name__ == "TwitterAdapter"

    web = GenericWebScraperTest()
    assert web.primary_backend == "scrapling_http"
    assert web.adapter.__class__.__name__ == "WebAdapter"

    gh = GitHubScraperTest()
    assert gh.primary_backend == "github_api"
    assert gh.adapter.__class__.__name__ == "GitHubAdapter"


def test_live_vs_offline_separation_and_truthful_failure():
    """
    Verify that live network failure produces UNHEALTHY status and is NOT disguised
    by fixture schema success (Section 8).
    """
    from unittest.mock import patch
    from scrapers.websites.reddit import RedditScraperTest
    from backend.services.agent_reach.channels import FetchedDocument

    test_impl = RedditScraperTest()
    # Mock production adapter to return a failed document
    with patch.object(
        test_impl.adapter,
        "acquire",
        return_value=FetchedDocument(
            url="https://reddit.com/r/technology/comments/bad_id",
            status="FAILED",
            backend_id="arctic_shift",
            failure_reason="HTTP 404: Not Found",
        )
    ):
        res = test_impl.run_canary({"target_url": "https://reddit.com/r/technology/comments/bad_id", "post_id": "bad_id"}, live_network=True)
        assert res.probe_mode == "live"
        assert res.live_transport_success is False
        assert res.health_status == "UNHEALTHY"
        assert res.error_class == ScraperErrorClass.CANARY_UNAVAILABLE.value
        # Fixture contract remains valid, but does not overwrite live health
        assert res.fixture_contract_valid is True


def test_canary_unavailable_vs_schema_drift():
    """
    Verify an unavailable/deleted canary is classified as CANARY_UNAVAILABLE,
    not confused with SCHEMA_DRIFT (Section 9).
    """
    from unittest.mock import patch
    from scrapers.websites.x import TwitterScraperTest
    from backend.services.agent_reach.channels import FetchedDocument

    test_impl = TwitterScraperTest()
    with patch.object(
        test_impl.adapter,
        "acquire",
        return_value=FetchedDocument(
            url="https://x.com/OpenAI/status/00000",
            status="FAILED",
            backend_id="fxtwitter",
            failure_reason="404 Not Found",
        )
    ):
        res = test_impl.run_canary({"target_url": "https://x.com/OpenAI/status/00000", "status_id": "00000"}, live_network=True)
        assert res.error_class == ScraperErrorClass.CANARY_UNAVAILABLE.value
        assert res.schema_drift.detected is False


def test_four_agent_strategies_runtime_execution():
    """
    Verify all 4 agent acquisition strategies are registered, distinct, and actively executed (Section 12, 13).
    """
    from backend.services.agent_reach.profile import get_agent_acquisition_strategy
    from backend.services.agent_reach.channels import CandidateSource, FetchedDocument, RetrievalRequest

    bs_strat = get_agent_acquisition_strategy("brandshield")
    tr_strat = get_agent_acquisition_strategy("trending")
    sc_strat = get_agent_acquisition_strategy("scout")
    pw_strat = get_agent_acquisition_strategy("personal")

    assert bs_strat is not None
    assert tr_strat is not None
    assert sc_strat is not None
    assert pw_strat is not None

    cand = CandidateSource(url="https://example.com/test", platform="web", title="Test")
    req = RetrievalRequest(request_id="test_req", agent="test", intent="verify")

    # 1. BrandShield extracts marketplace indicators
    bs_doc = FetchedDocument(url="https://amazon.com/item", status="SUCCESS", raw_content="Official seller shop price is $49.99 counterfeit warning")
    bs_frags = bs_strat.normalize(bs_doc, cand, req)
    assert len(bs_frags) > 0
    assert bs_frags[0].metadata.get("is_marketplace") is True
    assert bs_frags[0].metadata.get("price") == "$49.99"

    # 2. Trending tags wire syndication
    tr_doc = FetchedDocument(url="https://reuters.com/tech-news", status="SUCCESS", raw_content="Breaking tech announcement from official wire")
    tr_frags = tr_strat.normalize(tr_doc, cand, req)
    assert len(tr_frags) > 0
    assert tr_frags[0].metadata.get("is_wire_syndication") is True

    # 3. Scout forces FULL_ARTICLE
    sc_doc = FetchedDocument(url="https://sec.gov/edgar/filing", status="SUCCESS", raw_content="Corporate revenue was $5.4B with EBITDA expansion")
    sc_frags = sc_strat.normalize(sc_doc, cand, req)
    assert len(sc_frags) > 0
    assert sc_frags[0].content_depth == "FULL_ARTICLE"
    assert sc_frags[0].metadata.get("is_primary_source") is True

    # 4. Personal Watch redacts phone numbers, SSNs, and street addresses
    pw_doc = FetchedDocument(url="https://example.com/exec", status="SUCCESS", raw_content="Executive resides at 100 Main Street with phone 999-888-7777 and id 999-88-7777.")
    pw_frags = pw_strat.normalize(pw_doc, cand, req)
    assert len(pw_frags) > 0
    assert "[REDACTED_PHONE]" in pw_frags[0].content
    assert "[REDACTED_SSN]" in pw_frags[0].content
    assert "[REDACTED_RESIDENTIAL_ADDRESS]" in pw_frags[0].content
