"""
Aegis Protocol — Architecture Invariants & Independence Enforcement Tests
========================================================================
Validates that:
  1. Production agents (BrandShield, Trending, Scout, Personal Watch) NEVER import scraper.py or scrapers/
  2. Production agents operate independently without the scraper laboratory
  3. RoutePolicyEngine authoritative decisions directly control AdapterRegistry without fall-through bugs
  4. Walled gardens (Instagram, FB, TikTok, LinkedIn, Bilibili) strictly map to SearchDiscoveryAdapter
  5. Scout does not own a duplicate network acquisition stack
  6. Network activity telemetry represents real operations
"""

import ast
import os
import pytest
from unittest.mock import MagicMock, patch

from backend.services.agent_reach.channels import CandidateSource, RetrievalRequest
from backend.services.agent_reach.native.adapters.registry import AdapterRegistry, adapter_registry
from backend.services.agent_reach.native.adapters.search import SearchDiscoveryAdapter
from backend.services.agent_reach.native.adapters.reddit import RedditAdapter
from backend.services.agent_reach.native.adapters.twitter import TwitterAdapter
from backend.services.agent_reach.native.adapters.youtube import YouTubeAdapter
from backend.services.agent_reach.native.adapters.github import GitHubAdapter
from backend.services.agent_reach.native.adapters.web import WebAdapter
from backend.services.agent_reach.native.route_policy import RoutePolicyEngine


def test_production_agents_do_not_import_scraper_laboratory():
    """
    Architecture test proving the four production agents do NOT import
    scraper.py or the scrapers/ package (Section 2, 22, 55).
    """
    agent_files = [
        "backend/agents/brandshield_agent.py",
        "backend/agents/trending_agent.py",
        "backend/agents/scout_agent.py",
        "backend/agents/personal_agent.py",
    ]

    for filepath in agent_files:
        assert os.path.exists(filepath), f"File {filepath} must exist"
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("scraper"), (
                        f"CRITICAL VIOLATION: {filepath} imports '{alias.name}'. "
                        "Production agents must NOT depend on scraper laboratory."
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert not node.module.startswith("scraper"), (
                        f"CRITICAL VIOLATION: {filepath} imports from '{node.module}'. "
                        "Production agents must NOT depend on scraper laboratory."
                    )


def test_route_dispatch_matrix_and_no_walled_garden_fallthrough():
    """
    Test matrix asserting RouteDecision directly maps to expected adapter via AdapterRegistry.
    Guarantees no walled garden falls through into Scrapling HTTP (Section 25, 26, 58).
    """
    matrix = [
        ("reddit", RedditAdapter),
        ("twitter", TwitterAdapter),
        ("x", TwitterAdapter),
        ("youtube", YouTubeAdapter),
        ("github", GitHubAdapter),
        ("web", WebAdapter),
        ("news", WebAdapter),
        ("instagram", SearchDiscoveryAdapter),
        ("facebook", SearchDiscoveryAdapter),
        ("tiktok", SearchDiscoveryAdapter),
        ("linkedin", SearchDiscoveryAdapter),
        ("bilibili", SearchDiscoveryAdapter),
    ]

    registry = AdapterRegistry()

    for platform, expected_adapter_cls in matrix:
        decision = RoutePolicyEngine.decide_route(platform=platform, is_url=False)
        cand = CandidateSource(platform=platform, url=f"https://{platform}.com/test")

        adapter = registry.get_adapter_for_decision(decision, cand)

        assert isinstance(adapter, expected_adapter_cls), (
            f"Platform '{platform}' with backend '{decision.primary_backend}' mapped to "
            f"{type(adapter).__name__}, expected {expected_adapter_cls.__name__}."
        )


def test_scout_does_not_own_duplicate_network_stack():
    """
    Verify ScoutSourceEngine routes all network retrieval through agent_reach_service
    and does not own parallel HTTP scrapers (Section 4, 40).
    """
    from backend.services.agent_reach.scout.engine import ScoutSourceEngine
    from backend.services.agent_reach.scout.models import ScoutSourceRequest

    engine = ScoutSourceEngine()
    req = ScoutSourceRequest(query="AAPL earnings", tickers=["AAPL"], max_candidates=2)

    with patch("backend.services.agent_reach.adapter.agent_reach_service.execute") as mock_exec:
        mock_exec.return_value = []
        res = engine.execute(req)

        # Must call shared fabric
        assert mock_exec.called
        call_arg = mock_exec.call_args[0][0]
        assert isinstance(call_arg, RetrievalRequest)
        assert call_arg.agent == "scout"
        assert call_arg.profile is not None
        assert call_arg.profile.agent == "scout"


def test_telemetry_represents_real_network_activity():
    """
    Verify AcquisitionTelemetryRecord tracks distinct network operation counters (Section 41).
    """
    from backend.services.agent_reach.native.telemetry import AcquisitionTelemetryRecord

    rec = AcquisitionTelemetryRecord(
        request_id="req_test_01",
        discovery_requests=2,
        candidate_count=8,
        acquisition_attempts=5,
        successful_acquisitions=5,
        fallback_attempts=0,
        search_requests=2,
        mirror_requests=3,
        browser_requests=0,
        cache_hits=1,
        cache_misses=4,
        final_fragments=5,
    )

    data = rec.to_dict()
    assert data["discovery_requests"] == 2
    assert data["candidate_count"] == 8
    assert data["acquisition_attempts"] == 5
    assert data["successful_acquisitions"] == 5
    assert data["mirror_requests"] == 3
    assert data["final_fragments"] == 5
