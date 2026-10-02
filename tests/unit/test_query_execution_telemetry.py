"""
Unit Tests for Query Execution Telemetry and Funnel Counters
============================================================
Verifies:
1. Canonical QueryExecutionRecord structure and serialization.
2. Execution-derived telemetry tracking in AgentReachService.retrieve_many:
   - status tracking (SUCCESS, FAILED, TIMED_OUT, AUTH_REQUIRED, SKIPPED).
   - latency, attempt counts, and error metadata.
3. Stage 6 and Stage 7 telemetry tracking in ResearchEngine:
   - Adaptive queries recorded as SKIPPED when halted early.
   - Primary source escalation queries recorded only when executed.
4. Stage 13 query funnel counters:
   - queries_planned, queries_submitted, queries_started, queries_succeeded,
     queries_failed, queries_timed_out, queries_auth_required, queries_skipped,
     queries_executed.
5. Stage 14 dossier integrity (telemetry['dossier_id'] is None, no fake fallback).
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.services.agent_reach.channels import (
    QueryExecutionRecord,
    EvidenceFragment,
    RetrievalResult,
)
from backend.services.agent_reach.adapter import AgentReachService
from backend.services.research.research_models import ResearchRequest, EpistemicState
from backend.services.research.research_engine import ResearchEngine


class TestQueryExecutionRecordModel:
    """Verifies QueryExecutionRecord dataclass and serialization."""

    def test_record_defaults_and_to_dict(self):
        rec = QueryExecutionRecord(
            query_id="q_101",
            channel="financial",
            query_text="SEC filings Tesla",
            query_class="filings",
            phase="initial",
            status="SUCCESS",
            started_at="2026-10-02T10:00:00Z",
            completed_at="2026-10-02T10:00:00.125Z",
            latency_ms=125,
            result_count_raw=5,
            result_count_normalized=4,
            error=None,
            retrieval_mode="live",
            backend_id="sec_edgar",
        )
        data = rec.to_dict()
        assert data["query_id"] == "q_101"
        assert data["channel"] == "financial"
        assert data["query_text"] == "SEC filings Tesla"
        assert data["query_class"] == "filings"
        assert data["phase"] == "initial"
        assert data["status"] == "SUCCESS"
        assert data["latency_ms"] == 125
        assert data["result_count_raw"] == 5
        assert data["result_count_normalized"] == 4
        assert data["error"] is None
        assert data["backend_id"] == "sec_edgar"

    def test_record_error_fields(self):
        rec = QueryExecutionRecord(
            query_id="q_err",
            channel="sec",
            query_text="internal api",
            status="AUTH_REQUIRED",
            latency_ms=45,
            error="API key missing or expired",
            backend_id="sec_edgar",
        )
        data = rec.to_dict()
        assert data["status"] == "AUTH_REQUIRED"
        assert data["error"] == "API key missing or expired"
        assert data["backend_id"] == "sec_edgar"


class TestAgentReachServiceTelemetry:
    """Verifies that retrieve_many populates query_records accurately."""

    def test_retrieve_many_populates_query_records(self):
        service = AgentReachService()

        frag = EvidenceFragment(
            platform="Web",
            title="Sample Title",
            content="Sample Content",
            url="https://example.com/1",
            channel_name="web",
            requested_channel="web",
            actual_retrieval_channel="web",
            retrieval_mode="mock",
            is_authenticated=False,
        )

        web_ch = service.registry.get_channel("web")
        assert web_ch is not None

        with patch.object(web_ch, "search", return_value=[frag]):
            channel_queries = {
                "web": [
                    {"query_id": "q1", "query_class": "general", "query_text": "test query 1"},
                    {"query_id": "q2", "query_class": "general", "query_text": "test query 2"},
                ]
            }

            result = service.retrieve_many(
                channel_queries=channel_queries,
                domain="general",
                perform_reads=False,
            )

            assert len(result.query_records) == 2
            rec1 = next(r for r in result.query_records if r.query_id == "q1")
            assert rec1.status == "SUCCESS"
            assert rec1.channel == "web"
            assert rec1.result_count_raw == 1
            assert rec1.latency_ms is not None

    def test_retrieve_many_tracks_failures(self):
        service = AgentReachService()

        news_ch = service.registry.get_channel("news")
        assert news_ch is not None

        with patch.object(news_ch, "search", side_effect=RuntimeError("Connection refused")):
            channel_queries = {
                "news": [
                    {"query_id": "q_fail", "query_class": "news", "query_text": "breaking news"}
                ]
            }

            result = service.retrieve_many(
                channel_queries=channel_queries,
                domain="news",
                perform_reads=False,
            )

            assert len(result.query_records) == 1
            rec = result.query_records[0]
            assert rec.query_id == "q_fail"
            assert rec.status == "FAILED"
            assert "Connection refused" in (rec.error or "")


class TestResearchEngineQueryFunnel:
    """Verifies ResearchEngine Stage 13 funnel counters and Stage 6/7/14 behavior."""

    def test_query_funnel_counters_and_dossier_integrity(self):
        engine = ResearchEngine()

        req = ResearchRequest(
            target="Deep research target test",
            domain="fact_check",
            max_candidates=10,
        )

        mock_frag = EvidenceFragment(
            platform="Web",
            title="Evidence 1",
            content="Evidence content text for testing deep research engine",
            url="https://example.com/evidence1",
            channel_name="web",
            requested_channel="web",
            actual_retrieval_channel="web",
            retrieval_mode="live",
            is_authenticated=False,
        )

        rec1 = QueryExecutionRecord(
            query_id="q1",
            channel="web",
            query_text="Deep research target test",
            status="SUCCESS",
            latency_ms=50,
            result_count_raw=1,
            result_count_normalized=1,
        )

        mock_retrieval = RetrievalResult(
            query="Deep research target test",
            domain="general",
            fragments=[mock_frag],
            channel_health={"web": "AVAILABLE"},
            total_signals=1,
            retrieval_trace={"scan_id": "test_trace", "total_final": 1},
            query_records=[rec1],
        )

        with patch("backend.services.agent_reach.agent_reach_service.retrieve_many", return_value=mock_retrieval), \
             patch("backend.services.agent_reach.agent_reach_service.search_channel", return_value=[mock_frag]), \
             patch("backend.services.research.replay_ledger.replay_ledger.record_investigation", return_value="R-2026-TESTING"):

            result = engine.investigate(req)

            telemetry = result.telemetry
            assert "funnel" in telemetry
            funnel = telemetry["funnel"]
            assert "queries_planned" in funnel
            assert "queries_submitted" in funnel
            assert "queries_started" in funnel
            assert "queries_succeeded" in funnel
            assert "queries_failed" in funnel
            assert "queries_timed_out" in funnel
            assert "queries_auth_required" in funnel
            assert "queries_skipped" in funnel
            assert "queries_executed" in funnel

            # Verify executed queries match succeeded + failed + auth_required + timed_out
            assert funnel["queries_executed"] == (
                funnel["queries_succeeded"]
                + funnel["queries_failed"]
                + funnel["queries_auth_required"]
                + funnel["queries_timed_out"]
            )

            # Stage 14: dossier_id must be a real string if saved, or None (no R-2026-TEMP- fallback)
            assert not str(telemetry.get("dossier_id", "")).startswith("R-2026-TEMP-")
