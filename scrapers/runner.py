"""
Aegis Protocol — Scraper Laboratory Test Runner
===============================================
Orchestrates canary runs, calculates latency percentiles (P50/P95),
evaluates contract compatibility for the 4 production agents,
and records historical health snapshots.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from scrapers.base import ScraperLabResult
from scrapers.fixtures.canaries import get_canary_fixture
from scrapers.registry import scraper_test_registry


class ScraperLabRunner:
    """
    Test execution runner and metric aggregator for the scraper laboratory.
    """

    def __init__(self, history_file: str = ".scraper_health_history.json"):
        self.history_file = history_file

    def run_platform_test(self, platform: str) -> Optional[ScraperLabResult]:
        """Execute canary test for a single platform."""
        test_impl = scraper_test_registry.get_test(platform)
        if not test_impl:
            return None
        fixture = get_canary_fixture(test_impl.platform)
        result = test_impl.run_canary(fixture)
        self.record_history([result])
        return result

    def run_all(self) -> List[ScraperLabResult]:
        """Execute canary tests across all registered platforms."""
        results: List[ScraperLabResult] = []
        for test_impl in scraper_test_registry.list_all():
            fixture = get_canary_fixture(test_impl.platform)
            res = test_impl.run_canary(fixture)
            results.append(res)
        self.record_history(results)
        return results

    def calculate_percentiles(self, latencies: List[int]) -> Dict[str, int]:
        """Calculate P50 and P95 latencies."""
        if not latencies:
            return {"p50": 0, "p95": 0}
        sorted_lats = sorted(latencies)
        p50_idx = int(len(sorted_lats) * 0.50)
        p95_idx = min(int(len(sorted_lats) * 0.95), len(sorted_lats) - 1)
        return {
            "p50": sorted_lats[p50_idx],
            "p95": sorted_lats[p95_idx],
        }

    def evaluate_production_contract_support(
        self,
        platform: str,
        extracted: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Verify if the extracted fields from this website satisfy the required fields
        for each of the 4 production domain agents (Section 46).
        """
        from backend.services.agent_reach.profile import (
            BRANDSHIELD_PROFILE,
            PERSONAL_WATCH_PROFILE,
            SCOUT_PROFILE,
            TRENDING_PROFILE,
        )

        def _check_overlap(required: List[str]) -> bool:
            # Matches if at least core fields are present in extracted keys
            return any(k in extracted for k in required)

        return {
            "brandshield_compatible": _check_overlap(BRANDSHIELD_PROFILE.required_fields),
            "trending_compatible": _check_overlap(TRENDING_PROFILE.required_fields),
            "scout_compatible": _check_overlap(SCOUT_PROFILE.required_fields),
            "personal_watch_compatible": _check_overlap(PERSONAL_WATCH_PROFILE.required_fields),
        }

    def record_history(self, results: List[ScraperLabResult]) -> None:
        """Record historical health snapshot to disk."""
        snapshot = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "results": [r.to_dict() for r in results],
        }
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    if not isinstance(history, list):
                        history = []
            except Exception:
                history = []

        history.append(snapshot)
        # Keep latest 50 runs
        if len(history) > 50:
            history = history[-50:]

        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass

    def get_history(self) -> List[Dict[str, Any]]:
        """Load past health snapshots."""
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
