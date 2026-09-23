"""
Unit Tests for Aegis Protocol Multi-Query Retrieval & Full Lifecycle Telemetry Tracing
======================================================================================
Verifies:
1. RetrievalTrace and ChannelTelemetry structures across all lifecycle stages:
   PLANNED -> EXECUTED -> RETURNED -> NORMALIZED -> DEDUPED -> ANALYZED -> DISPLAYED
2. Multi-channel query distribution without query collapse
3. Query provenance tracking (query_id, query_class, query_text, content_depth)
4. Source independence clustering and deduplication tracking
5. POST /api/agent-reach/debug endpoint functionality
6. Integration with domain agents (BrandShield, Scout, Trending, PersonalWatch)
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.agent_reach.channels import (
    ChannelStatus,
    ChannelTelemetry,
    EvidenceFragment,
    RetrievalResult,
    RetrievalTrace,
)
from backend.services.agent_reach.planner import RetrievalPlanner
from backend.services.agent_reach.adapter import AgentReachService


class TestRetrievalTraceAndTelemetry:
    """Tests for retrieval tracing and channel telemetry models."""

    def test_channel_telemetry_defaults_and_serialization(self):
        tel = ChannelTelemetry(
            channel="news",
            status=ChannelStatus.AVAILABLE.value,
            queries_attempted=["Nike latest news", "Nike counterfeit shoes"],
            requests_attempted=2,
            successful_requests=2,
            latency_ms=150,
            raw_results=8,
            normalized_results=8,
            duplicates_removed=2,
            final_results=6,
        )
        data = tel.to_dict()
        assert data["channel"] == "news"
        assert data["status"] == "AVAILABLE"
        assert len(data["queries_attempted"]) == 2
        assert data["raw_results"] == 8
        assert data["duplicates_removed"] == 2
        assert data["final_results"] == 6
        assert data["latency_ms"] == 150

    def test_retrieval_trace_ascii_table_generation(self):
        tel_news = ChannelTelemetry(
            channel="news",
            status="AVAILABLE",
            requests_attempted=2,
            successful_requests=2,
            latency_ms=120,
            raw_results=6,
            normalized_results=6,
            duplicates_removed=1,
            final_results=5,
        )
        tel_reddit = ChannelTelemetry(
            channel="reddit",
            status="AVAILABLE",
            requests_attempted=2,
            successful_requests=2,
            latency_ms=210,
            raw_results=5,
            normalized_results=5,
            duplicates_removed=0,
            final_results=5,
        )

        trace = RetrievalTrace(
            scan_id="scan_test_001",
            agent="brandshield",
            query="Nike",
            domain="brand",
            planned_query_classes=6,
            planned_queries_count=12,
            executed_queries_count=10,
            channel_stats={"news": tel_news.to_dict(), "reddit": tel_reddit.to_dict()},
            total_raw=11,
            total_normalized=11,
            total_duplicates=1,
            total_final=10,
            unique_domains=6,
            independent_groups=5,
            readable_sources=3,
            total_latency_ms=350,
        )

        ascii_table = trace.to_ascii_table()
        assert "scan_test_001" in ascii_table
        assert "brandshield" in ascii_table
        assert "news" in ascii_table
        assert "reddit" in ascii_table
        assert "TOTALS" in ascii_table
        assert "Unique Domains: 6" in ascii_table
        assert "Independent Groups: 5" in ascii_table
        assert "Readable Sources: 3" in ascii_table

    def test_planner_generates_multi_queries_for_all_domains(self):
        planner = RetrievalPlanner()

        domains = ["brand", "financial", "trending", "personal", "technical", "general"]
        for d in domains:
            multi_q, q_classes = planner.build_multi_channel_queries("TestTarget", domain=d)
            assert len(multi_q) > 0, f"Domain {d} produced empty channel map"
            assert len(q_classes) > 0, f"Domain {d} produced empty query classes"

            # Check that queries contain query_id, query_class, and query_text
            for ch, q_list in multi_q.items():
                for item in q_list:
                    assert "query_id" in item
                    assert "query_class" in item
                    assert "query_text" in item
                    assert len(item["query_text"]) > 0

    def test_retrieve_many_executes_queries_and_preserves_provenance(self):
        service = AgentReachService()

        # Mock channels to avoid live network requests in unit test
        mock_frag1 = EvidenceFragment(
            platform="MockNews",
            title="Nike reports quarterly earnings beat",
            content="Full content about earnings",
            url="https://news.example.com/nike-earnings-123",
            snippet="Earnings beat expectations",
            channel_name="news",
        )
        mock_frag2 = EvidenceFragment(
            platform="MockReddit",
            title="Nike counterfeit shoes discussion",
            content="Counterfeit thread details",
            url="https://reddit.com/r/sneakers/nike-fake",
            snippet="How to spot fake Nike dunks",
            channel_name="reddit",
        )

        with patch.object(service.registry.get_channel("news"), "search", return_value=[mock_frag1]), \
             patch.object(service.registry.get_channel("reddit"), "search", return_value=[mock_frag2]):

            channel_queries = {
                "news": [
                    {"query_id": "ne_01", "query_class": "earnings", "query_text": "Nike earnings"},
                ],
                "reddit": [
                    {"query_id": "re_01", "query_class": "counterfeit", "query_text": "Nike counterfeit"},
                ],
            }

            result = service.retrieve_many(
                channel_queries=channel_queries,
                domain="brand",
                agent_name="test_agent",
                target_name="Nike",
                perform_reads=False,
                timeout=5.0,
            )

            assert isinstance(result, RetrievalResult)
            assert len(result.fragments) == 2
            assert result.retrieval_trace is not None

            trace = result.retrieval_trace
            assert trace["agent"] == "test_agent"
            assert trace["planning"]["queries_generated"] == 2
            assert trace["planning"]["queries_executed"] == 2
            assert trace["total"]["final_evidence"] == 2

            # Check provenance attached to fragments
            frag_news = next(f for f in result.fragments if f.channel_name == "news")
            assert frag_news.query_id == "ne_01"
            assert frag_news.query_class == "earnings"
            assert frag_news.query_text == "Nike earnings"


class TestAgentReachDebugApi:
    """Tests for POST /api/agent-reach/debug endpoint."""

    def test_debug_endpoint_payload_structure(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        response = client.post(
            "/api/agent-reach/debug",
            json={
                "query": "Tesla",
                "domain": "financial",
                "max_queries_per_channel": 1,
                "limit_per_query": 2,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "scan" in data
        assert data["scan"]["query"] == "Tesla"
        assert data["scan"]["domain"] == "financial"
        assert "scan_id" in data["scan"]
        assert "planning" in data
        assert "execution" in data
        assert "channels" in data
        assert "total" in data
        assert "formatted_telemetry" in data
        assert "raw_evidence_sample" in data
        assert isinstance(data["raw_evidence_sample"], list)

        # Check all lifecycle stages are reported truthfully
        assert data["planning"]["query_classes_count"] == 6
        assert data["planning"]["queries_executed"] > 0
        assert "raw_results" in data["total"]
        assert "duplicates_removed" in data["total"]
        assert "final_evidence" in data["total"]
        assert "readable_sources" in data["total"]


class TestSentinelIntegrationWithRetrievalTrace:
    """Verifies that the domain sentinels populate retrieval traces."""

    def test_brandshield_search_populates_trace(self):
        from backend.agents.brandshield_agent import brandshield_agent

        mock_frag = EvidenceFragment(
            platform="Web",
            title="Nike Brand Overview",
            content="Official details",
            url="https://nike.com/overview",
            snippet="Overview snippet",
            channel_name="web",
        )

        with patch("backend.services.agent_reach.adapter.AgentReachService.retrieve_many") as mock_retrieve:
            mock_retrieve.return_value = RetrievalResult(
                query="Nike",
                domain="brand",
                fragments=[mock_frag],
                channel_health={"web": "AVAILABLE"},
                total_signals=1,
                retrieval_trace={"scan_id": "test_trace_bs", "total_final": 1}
            )

            evidence, health, plan, syndicated = brandshield_agent.search_brand_evidence(
                {"brand": "Nike", "resolved_entity": "Nike"}
            )
            assert len(evidence) >= 1
            assert "trace" in plan
            assert plan["trace"]["scan_id"] == "test_trace_bs"

    def test_scout_stock_analysis_populates_trace(self):
        from backend.agents.scout_agent import scout_agent

        mock_frag = EvidenceFragment(
            platform="News",
            title="Tata Motors Q3 Results",
            content="Quarterly performance",
            url="https://reuters.com/tata-motors",
            snippet="Strong revenues",
            channel_name="news",
        )

        with patch("backend.services.agent_reach.adapter.AgentReachService.retrieve_many") as mock_retrieve, \
             patch.object(scout_agent, "check_stock_impact", return_value={"current_price": 950.0, "drop_percent": 1.2, "z_score": 0.5}):

            mock_retrieve.return_value = RetrievalResult(
                query="TATAMOTORS.NS",
                domain="financial",
                fragments=[mock_frag],
                channel_health={"news": "AVAILABLE"},
                total_signals=1,
                retrieval_trace={"scan_id": "test_trace_scout", "total_final": 1}
            )

            result = scout_agent.analyze_stock("TATAMOTORS.NS")
            assert "retrieval_trace" in result
            assert result["retrieval_trace"]["scan_id"] == "test_trace_scout"
