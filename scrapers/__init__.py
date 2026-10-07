"""
Aegis Protocol — Scraper Laboratory Package
===========================================
Offline / CI website testing, canary benchmarking, and schema drift detection.
CRITICAL ARCHITECTURE INVARIANT:
This package is strictly for testing, benchmarking, and health monitoring.
Production agents (BrandShield, Trending, Scout, Personal Watch) MUST NOT import this package.
"""

from scrapers.base import ScraperErrorClass, ScraperLabResult, WebsiteScraperTest
from scrapers.registry import scraper_test_registry
from scrapers.runner import ScraperLabRunner
from scrapers.reporters import format_health_report, format_summary_table

__all__ = [
    "ScraperErrorClass",
    "ScraperLabResult",
    "WebsiteScraperTest",
    "scraper_test_registry",
    "ScraperLabRunner",
    "format_health_report",
    "format_summary_table",
]
