"""
Aegis Protocol — Unit Tests: Agent Reach Service & Retrieval Planner
======================================================================
Validates:
- RetrievalPlanner domain query optimization and channel prioritization
- Technical domain routing and GitHub channel query craft
- Stopword stripping and keyword extraction on verbose claims
- URL normalization (tracking param removal) and fragment deduplication
- Syndication clustering and source independence grouping
- Forensic source role and tier attribution
- SSRF defense integration in safe reading
- Partial channel failure resilience during concurrent retrieval
- Full backward-compatibility interfaces (omni_scan, unified_scan, doctor)
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.services.agent_reach.channels import (
    ChannelStatus,
    EvidenceFragment,
    RetrievalResult,
)
from backend.services.agent_reach.planner import RetrievalPlanner
from backend.services.agent_reach.adapter import AgentReachService


def test_retrieval_planner_financial_domain():
    planner = RetrievalPlanner()
    plan = planner.plan("TSLA", domain="financial")
    assert plan.domain == "financial"
    assert "twitter" in plan.channels_to_query
    assert "news" in plan.channels_to_query
    assert "$TSLA" in plan.domain_queries.get("twitter", "")
    assert "crash" in plan.domain_queries.get("reddit", "")


def test_retrieval_planner_technical_domain():
    planner = RetrievalPlanner()
    plan = planner.plan("fastapi security vulnerability CVE-2024", domain="technical")
    assert plan.domain == "technical"
    assert plan.channels_to_query[0] == "github"
    assert "github" in plan.domain_queries
    assert "reddit" in plan.domain_queries
    assert "CVE" in plan.domain_queries.get("twitter", "")


def test_retrieval_planner_keyword_extraction():
    planner = RetrievalPlanner()
    verbose_claim = "Officials have allegedly been secretly planning that new regulation into their departments"
    plan = planner.plan(verbose_claim, domain="fact_check")
    # Stopwords like 'that', 'with', 'have', 'been', 'secretly' should be excluded from search_keywords
    assert "secretly" not in plan.search_keywords
    assert "allegedly" in plan.search_keywords or "officials" in plan.search_keywords or len(plan.search_keywords) > 0


def test_url_normalization():
    service = AgentReachService()
    raw = "https://example.com/article/123/?utm_source=twitter&utm_medium=social&ref=feed#section-2"
    clean = service._normalize_url(raw)
    assert "utm_source" not in clean
    assert "utm_medium" not in clean
    assert "ref" not in clean
    assert "#section-2" not in clean
    assert clean == "https://example.com/article/123"


def test_fragment_deduplication():
    service = AgentReachService()
    frags = [
        EvidenceFragment(platform="News", title="Major Tech Breakthrough Announced", url="https://example.com/news?utm_source=a"),
        EvidenceFragment(platform="News", title="Major Tech Breakthrough Announced", url="https://example.com/news?utm_source=b"),
        EvidenceFragment(platform="Reddit", title="Different discussion title", url="https://reddit.com/r/tech/1"),
    ]
    unique, dupes_removed = service._deduplicate_fragments(frags)
    assert len(unique) == 2
    assert dupes_removed == 1


def test_source_independence_syndication_clustering():
    service = AgentReachService()
    frags = [
        EvidenceFragment(platform="News", title="Tech company issues recall", snippet="According to Reuters, the company issued a notice.", url="https://news1.com/a"),
        EvidenceFragment(platform="News", title="Recall notice published", snippet="Reported by Reuters wire service today.", url="https://news2.com/b"),
        EvidenceFragment(platform="Reddit", title="Local user review", snippet="I bought this item myself yesterday.", url="https://reddit.com/c"),
    ]
    groups = service._cluster_source_independence(frags)
    assert "syndicated_reuters" in groups
    assert len(groups["syndicated_reuters"]) == 2
    assert "independent" in groups
    assert len(groups["independent"]) == 1


def test_source_role_attribution():
    service = AgentReachService()
    frags = [
        EvidenceFragment(platform="GitHub", retrieval_method="github_api"),
        EvidenceFragment(platform="News", retrieval_method="agent_reach"),
        EvidenceFragment(platform="Reddit", retrieval_method="agent_reach"),
        EvidenceFragment(platform="YouTube", retrieval_method="agent_reach"),
    ]
    service._assign_source_roles(frags)
    assert frags[0].raw_metadata["source_role"] == "PRIMARY"
    assert frags[1].raw_metadata["source_role"] == "SECONDARY"
    assert frags[2].raw_metadata["source_role"] == "COMMUNITY"
    assert frags[3].raw_metadata["source_role"] == "DIRECT_MEDIA"


def test_ssrf_protection_in_read():
    service = AgentReachService()
    res_loopback = service.read("http://127.0.0.1:8000/api/claims")
    assert res_loopback["status"] == "blocked_ssrf"

    res_metadata = service.read("http://169.254.169.254/latest/meta-data/")
    assert res_metadata["status"] == "blocked_ssrf"


def test_retrieve_partial_failure_resilience():
    service = AgentReachService()
    
    # Mock Reddit channel to raise an exception, while News succeeds
    mock_reddit = MagicMock()
    mock_reddit.name = "reddit"
    mock_reddit.search.side_effect = TimeoutError("Simulated channel timeout")
    
    mock_news = MagicMock()
    mock_news.name = "news"
    mock_news.search.return_value = [
        EvidenceFragment(platform="News", title="Official Announcement", url="https://apnews.com/1", snippet="AP news content")
    ]

    service.registry._channels["reddit"] = mock_reddit
    service.registry._channels["news"] = mock_news
    service.registry._status["reddit"] = ChannelStatus.AVAILABLE
    service.registry._status["news"] = ChannelStatus.AVAILABLE

    result = service.retrieve(
        query="major merger",
        domain="fact_check",
        channels=["reddit", "news"],
        limit_per_channel=2,
    )

    # Retrieval should not crash; news fragments should be present
    assert len(result.fragments) == 1
    assert result.fragments[0].platform == "News"
    # Channel health should record the partial failure
    assert result.channel_health["reddit"] == ChannelStatus.UNAVAILABLE.value
    assert result.channel_health["news"] == ChannelStatus.AVAILABLE.value


def test_backward_compatibility_interfaces():
    service = AgentReachService()

    # omni_scan output contains required legacy keys
    with patch.object(service, "retrieve") as mock_retrieve:
        mock_result = RetrievalResult(
            query="test",
            domain="general",
            fragments=[
                EvidenceFragment(platform="Reddit", title="Discussion", channel_name="reddit")
            ],
            channel_health={"reddit": "AVAILABLE"},
            total_signals=1,
        )
        mock_retrieve.return_value = mock_result

        omni = service.omni_scan(query="test")
        assert "channels" in omni
        assert "items" in omni
        assert "total_signals" in omni
        assert "reddit" in omni["channels"]
        assert len(omni["items"]) == 1

        # unified_scan
        unified = service.unified_scan(query="test")
        assert "channels" in unified

        # doctor
        doc = service.doctor()
        assert "status" in doc
        assert "channels" in doc
