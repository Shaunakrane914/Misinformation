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
    results = runner.run_all()
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
    Verify ScraperLabRunner evaluates whether website extraction supports
    production domain contracts (Section 46).
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
    }
    compat = runner.evaluate_production_contract_support("reddit", extracted_reddit)
    assert compat["brandshield_compatible"] is True
    assert compat["trending_compatible"] is True


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
