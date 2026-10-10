"""Controlled end-to-end acquisition traces through all four production agents.

These tests inject deterministic evidence at the shared acquisition boundary;
they do not claim to be live-provider tests.
"""

from copy import deepcopy
from unittest.mock import patch

import pytest

from backend.agents.brandshield.agent import BrandShieldAgent
from backend.agents.personal_watch.agent import PersonalWatchAgent
from backend.agents.scout.sources.engine import ScoutSourceEngine
from backend.agents.scout.sources.models import ScoutSourceRequest
from backend.agents.trending.agent import TrendingAgent
from backend.services.agent_reach import agent_reach_service
from backend.services.agent_reach.native import native_router
from backend.services.agent_reach.channels import (
    EvidenceFragment,
    QueryExecutionRecord,
    RetrievalResult,
)


def _fragment(entity: str = "Nvidia") -> EvidenceFragment:
    return EvidenceFragment(
        platform="news",
        title=f"{entity} official statement addresses the reported claim",
        content=(
            f"{entity} published an official statement with specific facts about the "
            "reported claim. Independent reporting distinguishes the allegation from the response."
        ),
        snippet=f"{entity} official statement and independent response",
        url=f"https://example.com/{entity.lower().replace(' ', '-')}-statement",
        author="Example Newsroom",
        channel_name="news",
        requested_channel="news",
        actual_retrieval_channel="news",
        retrieval_mode="rss_feed",
        content_depth="FEED_ENTRY_SUMMARY",
        query_id="fixture_q1",
        query_class="official_disclosure",
        query_text=f"{entity} official statement",
        raw_metadata={
            "source_role": "SECONDARY",
            "source_tier": "TIER_2_FINANCIAL_PRESS",
            "fixture_boundary": "shared_acquisition",
        },
    )


def _retrieval(entity: str = "Nvidia") -> RetrievalResult:
    fragment = _fragment(entity)
    record = QueryExecutionRecord(
        query_id="fixture_q1",
        channel="news",
        query_text=f"{entity} official statement",
        query_class="official_disclosure",
        status="SUCCESS",
        result_count_raw=1,
        result_count_normalized=1,
        retrieval_mode="fixture",
        backend_id="controlled-acquisition-boundary",
    )
    return RetrievalResult(
        query=entity,
        domain="general",
        fragments=[fragment],
        channel_health={"news": "DEGRADED"},
        total_signals=1,
        retrieval_trace={
            "scan_id": "fixture_shared_acquisition",
            "channel_health": {"news": "DEGRADED"},
            "total_latency_ms": 1,
        },
        query_records=[record],
    )


@pytest.mark.integration
def test_all_four_agents_invoke_real_entrypoints_through_shared_acquisition_boundary():
    retrieve_calls = []
    execute_calls = []

    def fake_retrieve_many(*args, **kwargs):
        retrieve_calls.append(kwargs.get("agent_name"))
        return deepcopy(_retrieval(kwargs.get("target_name") or "Nvidia"))

    def fake_router_execute(request):
        execute_calls.append(request)
        fragment = _fragment(request.entity or "Nvidia")
        fragment.raw_metadata["source_plan"] = request.metadata.get("source_plan")
        return [fragment]

    with patch.object(agent_reach_service, "retrieve_many", side_effect=fake_retrieve_many), \
         patch.object(native_router, "execute_retrieval_request", side_effect=fake_router_execute), \
         patch.object(agent_reach_service, "search_channel", return_value=[]), \
         patch.object(agent_reach_service, "read", return_value={"status": "failed", "error": "fixture: no deep read"}), \
         patch("backend.services.research.replay_ledger.replay_ledger.record_investigation", return_value="R-FIXTURE"):

        brand = BrandShieldAgent()
        _, _, brand_plan, _ = brand.search_brand_evidence({
            "brand": "Nvidia", "resolved_entity": "Nvidia"
        })

        personal = PersonalWatchAgent()
        _, _, personal_plan, _ = personal.search_personal_evidence({
            "name": "Sam Altman", "canonical_name": "Sam Altman"
        })

        trending = TrendingAgent()
        trending_result = trending.scan("Nvidia")

        scout_result = ScoutSourceEngine().execute(ScoutSourceRequest(
            query="Nvidia manipulated quarterly revenue",
            target_entity="Nvidia",
            max_candidates=3,
        ))

    assert {"brandshield", "personal_watch", "trending"}.issubset(set(retrieve_calls))
    scout_requests = [request for request in execute_calls if request.agent == "scout"]
    assert len(scout_requests) == 1
    assert scout_requests[0].metadata.get("source_plan"), "Scout must receive the shared source plan"
    assert all(request.metadata.get("source_plan") for request in execute_calls)
    assert brand_plan["trace"]["source_plan"]["agent"] == "brandshield"
    assert personal_plan["trace"]["source_plan"]["agent"] == "personal_watch"
    assert trending_result["retrieval_trace"]["source_plan"]["agent"] == "trending"
    assert scout_result.evidence_items
