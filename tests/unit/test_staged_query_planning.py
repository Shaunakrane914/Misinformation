"""Offline unit tests for Staged Query Planning and Task-Relevant Coverage Gates."""
from unittest.mock import MagicMock
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.research.research_models import ResearchRequest
from backend.services.research.research_profiles import get_research_profile
from backend.services.research.harvesting import HarvestingEngine


def test_staged_query_planning_does_not_stop_at_two_unacquired_leads():
    """Promising titles must not suppress fallback before their bodies are read."""
    mock_service = MagicMock()
    call_count = 0

    def mock_retrieve_many(plan, **kwargs):
        nonlocal call_count
        call_count += 1
        res = MagicMock()
        res.query_records = []
        res.channel_health = {}
        res.retrieval_trace = {"wave": call_count}
        if call_count == 1:
            # 2 distinct publishers matching 'Cedar Instruments' and domain 'financial'
            f1 = EvidenceFragment(
                platform="news",
                url="https://bloomberg.example/news/cedar-instruments-quarterly-earnings",
                title="Cedar Instruments reports quarterly earnings and revenue growth",
                snippet="Cedar Instruments revenue increased by 15% in Q3.",
                content="Cedar Instruments reported quarterly revenue of USD 14 million.",
                evidence_id="ev_frag_1",
            )
            f2 = EvidenceFragment(
                platform="web",
                url="https://reuters.example/business/cedar-instruments-financial-results",
                title="Cedar Instruments posts strong financial results",
                snippet="Operating profit at Cedar Instruments reached new highs.",
                content="Cedar Instruments operating profit reached USD 4 million.",
                evidence_id="ev_frag_2",
            )
            res.fragments = [f1, f2]
        else:
            res.fragments = []
        return res

    mock_service.retrieve_many.side_effect = mock_retrieve_many
    mock_service.registry.channel_names = ["news", "web", "rss"]

    engine = HarvestingEngine(mock_service)
    profile = get_research_profile("QUICK")
    req = ResearchRequest(target="Cedar Instruments", domain="financial")

    result = engine.run(
        target="Cedar Instruments",
        domain="financial",
        intent="quarterly earnings",
        agent_name="scout",
        profile=profile,
        deadline=1000000000.0,
        request=req,
    )

    assert call_count > 1
    trace = result.retrieval_trace.get("staged_query_planning", {})
    assert trace.get("reason") == "LEADS_ONLY_CONTINUE_BOUNDED_DISCOVERY"
    assert "bloomberg.example" in trace.get("covered_publishers", [])
    assert "reuters.example" in trace.get("covered_publishers", [])
    assert trace["waves_skipped_for_lead_coverage"] == 0
    assert trace["acquired_evidence_coverage_established"] is False


def test_staged_query_planning_continues_when_task_coverage_is_insufficient():
    """Verify that discovery adaptively proceeds to Wave 2 when Wave 1 has insufficient coverage."""
    mock_service = MagicMock()
    call_count = 0

    def mock_retrieve_many(plan, **kwargs):
        nonlocal call_count
        call_count += 1
        res = MagicMock()
        res.query_records = []
        res.channel_health = {}
        res.retrieval_trace = {"wave": call_count}
        # In Wave 1, only return 1 candidate (insufficient diversity for task coverage)
        if call_count == 1:
            f1 = EvidenceFragment(
                platform="news",
                url="https://single-source.example/cedar-instruments-update",
                title="Cedar Instruments overview",
                snippet="General overview of the firm.",
                content="Overview of Cedar Instruments business.",
                evidence_id="ev_frag_1",
            )
            res.fragments = [f1]
        else:
            res.fragments = []
        return res

    mock_service.retrieve_many.side_effect = mock_retrieve_many
    mock_service.registry.channel_names = ["news", "web", "rss"]

    engine = HarvestingEngine(mock_service)
    profile = get_research_profile("QUICK")
    req = ResearchRequest(target="Cedar Instruments", domain="financial")

    result = engine.run(
        target="Cedar Instruments",
        domain="financial",
        intent="quarterly earnings",
        agent_name="scout",
        profile=profile,
        deadline=1000000000.0,
        request=req,
    )

    # Insufficient coverage in Wave 1 means Wave 2 was executed
    assert call_count > 1
