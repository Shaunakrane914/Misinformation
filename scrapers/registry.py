"""
Aegis Protocol — Scraper Laboratory Registry
============================================
Registry mapping supported platforms to their laboratory test scrapers.
Strictly part of the testing / benchmarking suite.
"""

from typing import Dict, List, Optional
from scrapers.base import WebsiteScraperTest
from scrapers.websites import (
    BilibiliScraperTest,
    FacebookScraperTest,
    GenericWebScraperTest,
    GitHubScraperTest,
    GoogleNewsScraperTest,
    InstagramScraperTest,
    LinkedInScraperTest,
    RedditScraperTest,
    TikTokScraperTest,
    TwitterScraperTest,
    YouTubeScraperTest,
)


class ScraperTestRegistry:
    """
    Central registry for website test scrapers.
    """

    def __init__(self):
        self._tests: Dict[str, WebsiteScraperTest] = {}
        self._register_defaults()

    def _register_defaults(self):
        tests: List[WebsiteScraperTest] = [
            RedditScraperTest(),
            TwitterScraperTest(),
            YouTubeScraperTest(),
            GitHubScraperTest(),
            GenericWebScraperTest(),
            GoogleNewsScraperTest(),
            InstagramScraperTest(),
            FacebookScraperTest(),
            TikTokScraperTest(),
            LinkedInScraperTest(),
            BilibiliScraperTest(),
        ]
        for t in tests:
            self._tests[t.platform.lower()] = t

    def get_test(self, platform: str) -> Optional[WebsiteScraperTest]:
        plat = (platform or "").lower().strip()
        if plat in ("x", "twitter"):
            return self._tests.get("x")
        return self._tests.get(plat)

    def list_platforms(self) -> List[str]:
        return sorted(list(self._tests.keys()))

    def list_all(self) -> List[WebsiteScraperTest]:
        return list(self._tests.values())


scraper_test_registry = ScraperTestRegistry()
