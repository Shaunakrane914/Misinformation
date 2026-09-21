"""
Aegis Protocol — Unit Tests: Scout 2.0 Financial Research Terminal
===================================================================
Tests:
- Ticker symbol and corporate entity name resolution
- Multi-class financial query planning
- Primary source escalation (SEC, BSE, NSE, Investor Relations)
- Wire syndication clustering and source independence
- URL preservation and refusal to invent fake links
- Grounded reasoning without synthetic hallucination on empty sources
"""

import pytest
from backend.agents.scout_agent import ScoutAgent
from backend.services.agent_reach.planner import RetrievalPlanner
from backend.services.agent_reach.channels import EvidenceFragment
from backend.services.agent_reach.adapter import AgentReachService


def test_resolve_ticker_and_company():
    scout = ScoutAgent()
    sym1, comp1 = scout.resolve_ticker_and_company("TATAMOTORS.NS")
    assert sym1 == "TATAMOTORS.NS"
    assert comp1 == "Tata Motors"

    sym2, comp2 = scout.resolve_ticker_and_company("NVDA")
    assert sym2 == "NVDA"
    assert comp2 == "Nvidia"

    sym3, comp3 = scout.resolve_ticker_and_company("reliance")
    assert sym3 == "RELIANCE.NS"
    assert comp3 == "Reliance Industries"


def test_financial_query_classes():
    planner = RetrievalPlanner()
    classes = planner.build_financial_query_classes("TATAMOTORS.NS", "Tata Motors")

    assert "general_news" in classes
    assert "financial" in classes
    assert "corporate_filings" in classes
    assert "risk_investigation" in classes
    assert "market_narrative" in classes
    assert "contradictions" in classes

    assert any("Tata Motors" in q for q in classes["general_news"])
    assert any("earnings" in q for q in classes["financial"])
    assert any("regulatory filing" in q for q in classes["corporate_filings"])
    assert any("investigation" in q for q in classes["risk_investigation"])


def test_primary_source_tagging():
    service = AgentReachService()

    fragments = [
        EvidenceFragment(
            platform="web article",
            title="Tata Motors Q4 Financial Results and Investor Presentation",
            url="https://investor.tatamotors.com/results/q4-fy25.pdf",
            snippet="Official disclosure of quarterly revenues."
        ),
        EvidenceFragment(
            platform="news",
            title="Reuters Market Report on Auto Industry",
            url="https://www.reuters.com/business/autos/tata-motors-2026-09-20/",
            snippet="Auto sector wire analysis."
        ),
        EvidenceFragment(
            platform="reddit",
            title="Is Tata Motors a good buy at current levels?",
            url="https://www.reddit.com/r/stocks/comments/xyz123/",
            snippet="Discussion thread on valuation."
        ),
        EvidenceFragment(
            platform="youtube",
            title="Tata Motors Comprehensive Fundamental Stock Analysis",
            url="https://www.youtube.com/watch?v=sample123",
            snippet="Video breakdown of debt and EV strategy."
        )
    ]

    service._assign_source_roles(fragments)

    assert fragments[0].raw_metadata.get("source_role") == "PRIMARY"
    assert fragments[0].raw_metadata.get("source_tier") == "TIER_1_OFFICIAL_FILING"

    assert fragments[1].raw_metadata.get("source_role") == "SECONDARY"
    assert fragments[1].raw_metadata.get("source_tier") == "TIER_2_FINANCIAL_PRESS"

    assert fragments[2].raw_metadata.get("source_role") == "COMMUNITY"
    assert fragments[2].raw_metadata.get("source_tier") == "TIER_3_INVESTOR_COMMUNITY"

    assert fragments[3].raw_metadata.get("source_role") == "DIRECT_MEDIA"
    assert fragments[3].raw_metadata.get("source_tier") == "TIER_2_VIDEO_ANALYSIS"


def test_syndication_clustering():
    service = AgentReachService()
    fragments = [
        EvidenceFragment(
            platform="news",
            title="Tata Motors Reports Record EV Deliveries",
            snippet="According to Reuters, the company achieved milestone production.",
            url="https://outlet-a.com/article1"
        ),
        EvidenceFragment(
            platform="news",
            title="Tata Motors Hits EV Production Milestone",
            snippet="Reuters reports that EV output surged 25% year-over-year.",
            url="https://outlet-b.com/article2"
        ),
        EvidenceFragment(
            platform="news",
            title="Independent Analysis of Commercial Vehicle Demand",
            snippet="Proprietary analysis indicates steady fleet replacement cycles.",
            url="https://independent-blog.org/analysis"
        )
    ]

    groups = service._cluster_source_independence(fragments)
    assert "syndicated_reuters" in groups
    assert len(groups["syndicated_reuters"]) == 2
    assert "independent" in groups
    assert len(groups["independent"]) == 1


def test_url_preservation_and_no_fake_links():
    scout = ScoutAgent()
    res = scout.analyze_stock("DEMO.NS")

    assert "sources" in res
    for s in res["sources"]:
        assert "url" in s
        assert "has_url" in s
        if not s["url"]:
            assert s["has_url"] is False


def test_empty_retrieval_no_synthetic_hallucination():
    scout = ScoutAgent()
    empty_intel = scout._synthesize_financial_intelligence(
        company_name="NonExistentCorp",
        ticker="FAKE.XX",
        stock_data={"current_price": 0.0},
        sources=[]
    )

    assert empty_intel["catalysts"]["positive"] == []
    assert empty_intel["catalysts"]["negative"] == []
    assert empty_intel["catalysts"]["unresolved"] == []
    assert empty_intel["narratives"] == []
    assert empty_intel["misinformation"]["status"] == "NOMINAL"
