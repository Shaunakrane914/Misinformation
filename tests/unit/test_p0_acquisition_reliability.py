"""P0 calibration: no provider or model calls; slow diagnostics are injected."""
import time
import threading
import copy
from unittest.mock import MagicMock, patch

import pytest

from backend.infrastructure.acquisition import service as module
from backend.services.agent_reach.channels import ChannelStatus, EvidenceFragment


def make_service(monkeypatch, searches):
    service = module.AgentReachService()
    registry = MagicMock()
    registry.channel_names = list(searches)
    registry.get_status.return_value = ChannelStatus.AVAILABLE
    registry.get_channel.side_effect = lambda channel: searches[channel]
    service.registry = registry
    monkeypatch.setattr(type(module.runtime_operation_capabilities), "assess", lambda *a: {"decision": "ALLOW"})
    return service


@pytest.mark.parametrize("agent", ["scout", "trending", "brandshield", "personal_watch"])
def test_slow_doctor_cannot_starve_search(monkeypatch, agent):
    search = MagicMock()
    search.search.return_value = [EvidenceFragment(platform="web", title="Lenovo results", url="https://example.com/results", snippet="Reported results")]
    service = make_service(monkeypatch, {"web": search})

    def expensive_status(*args):
        time.sleep(0.06)
        return {"active_backend": "diagnostic"}

    doctor = MagicMock(side_effect=expensive_status)
    monkeypatch.setattr(module.native_doctor, "get_channel_status", doctor)
    result = service.retrieve_many({"web": ["Lenovo results"]}, agent_name=agent, perform_reads=False, timeout=0.04)
    assert len(result.fragments) == 1
    assert search.search.call_count == 1
    assert doctor.call_count == 0


def test_timeout_isolated_and_late_completion_cannot_change_result(monkeypatch):
    release = threading.Event()
    slow, fast = MagicMock(), MagicMock()
    slow.search.side_effect = lambda *a, **k: (release.wait(1) or [])
    fast.search.return_value = [EvidenceFragment(platform="rss", url="https://example.com/news", title="Lenovo revenue")]
    service = make_service(monkeypatch, {"web": slow, "rss": fast})
    monkeypatch.setattr(module.native_doctor, "peek_channel_status", lambda *a: {})
    try:
        before = time.monotonic()
        result = service.retrieve_many({"web": ["Lenovo"], "rss": ["Lenovo"]}, timeout=0.06, perform_reads=False)
        assert time.monotonic() - before < 0.3
        assert len(result.fragments) == 1
        records = {r.channel: r for r in result.query_records}
        assert records["web"].status == "TIMEOUT"
        assert records["web"].provider_started is True
        assert records["web"].provider_duration_censored is True
        assert records["rss"].status == "SUCCESS"
        assert records["rss"].queue_wait_ms >= 0
        assert records["rss"].provider_duration_censored is False
        snapshot = copy.deepcopy(result.to_dict())
    finally:
        release.set()
    time.sleep(0.02)
    assert result.to_dict() == snapshot


def test_zero_budget_never_claims_provider_started(monkeypatch):
    search = MagicMock()
    service = make_service(monkeypatch, {"web": search})
    monkeypatch.setattr(module.native_doctor, "peek_channel_status", lambda *a: {})
    result = service.retrieve_many({"web": ["Lenovo"]}, timeout=0, perform_reads=False)
    assert result.query_records[0].status == "NOT_SUBMITTED"
    assert result.query_records[0].provider_started is False
    search.search.assert_not_called()


def test_queued_search_is_not_reported_as_started(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(max_workers=1)
    release = threading.Event()
    search = MagicMock()
    def blocked(*a, **kw):
        release.wait(1)
        return []
    search.search.side_effect = blocked
    service = make_service(monkeypatch, {"web": search})
    monkeypatch.setattr(module, "_SEARCH_POOL", pool)
    monkeypatch.setattr(module, "_SEARCH_CAPACITY", threading.BoundedSemaphore(2))
    monkeypatch.setattr(module.native_doctor, "peek_channel_status", lambda *a: {})
    try:
        result = service.retrieve_many({"web": ["first", "queued"]}, timeout=0.04, perform_reads=False)
        by_query = {row.query_text: row for row in result.query_records}
        assert by_query["queued"].status == "QUEUE_TIMEOUT"
        assert by_query["queued"].provider_started is False
        assert by_query["queued"].started_at is None
        assert by_query["queued"].submitted_at
        assert by_query["queued"].queue_wait_ms >= 0
    finally:
        release.set()
        pool.shutdown(wait=True)


@pytest.mark.parametrize("value,symbol,company", [
    ("Lenovo", "", "Lenovo"), ("Infosys", "INFY.NS", "Infosys"),
    ("Tata Motors", "TATAMOTORS.NS", "Tata Motors"), ("Microsoft", "MSFT", "Microsoft"),
    ("Unfamiliar Widgets Limited", "", "Unfamiliar Widgets Limited"), ("ABC", "", "ABC"),
])
def test_names_do_not_invent_listings(value, symbol, company):
    from backend.agents.scout.financial import resolve_ticker_and_company
    actual_symbol, actual_company = resolve_ticker_and_company(value)
    assert actual_symbol == symbol
    assert actual_company.casefold() == company.casefold()


def test_lenovo_listing_ambiguity_and_quote_validation():
    from backend.agents.scout.financial import resolve_company_identity, validated_quote_metadata
    identity = resolve_company_identity("Lenovo")
    assert identity["status"] == "AMBIGUOUS_LISTING"
    assert identity["proposed_symbol"] is None and identity["currency"] is None
    assert resolve_company_identity("0992.HK")["currency"] == "HKD"
    assert validated_quote_metadata({"chart": {"result": [{"meta": {"symbol": "MSFT", "currency": "USD"}}]}}, "0992.HK") is None
    assert validated_quote_metadata({"chart": {"result": [{"meta": {"symbol": "0992.HK", "currency": "HKD"}}]}}, "0992.HK")["currency"] == "HKD"


def test_quote_validation_uses_bounded_shared_transport(monkeypatch):
    import json
    from backend.agents.scout import financial
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    payload = {"chart": {"result": [{"meta": {"symbol": "0992.HK", "currency": "HKD"}}]}}
    fetch = MagicMock(return_value=BoundedHTTPResponse(body=json.dumps(payload).encode(),
        endpoint="https://query1.finance.yahoo.com", status_code=200, content_type="application/json",
        headers={}, latency_ms=1, attempts=1))
    monkeypatch.setattr(financial, "fetch_public_http", fetch)
    assert financial.fetch_stock_data("0992.HK") == payload
    assert fetch.call_args.kwargs["max_bytes"] == 1_000_000
    assert fetch.call_args.kwargs["max_attempts"] == 1
    assert fetch.call_args.kwargs["max_redirects"] == 0


def test_acquisition_failure_is_not_a_negative_research_result():
    from backend.services.research.acquisition_status import acquisition_outcome
    assert acquisition_outcome([{"status": "TIMEOUT"}] * 9)["status"] == "ACQUISITION_FAILED"
    assert acquisition_outcome([{"status": "SKIPPED"}])["status"] == "ACQUISITION_FAILED"
    assert acquisition_outcome([{"status": "SUCCESS"}])["status"] == "INSUFFICIENT_EVIDENCE"
    assert acquisition_outcome([{"status": "SUCCESS"}], 0, 1)["status"] == "ACQUISITION_FAILED"
    assert acquisition_outcome([{"status": "SUCCESS"}], 1, 1)["status"] == "COMPLETED"


@pytest.mark.parametrize("agent", ["scout", "trending", "brandshield", "personal_watch"])
def test_shared_report_prominently_preserves_transport_failure(agent):
    from backend.services.report_builder import _complete_agent_report
    from backend.schemas.unified_report import UnifiedReport
    from backend.services.research.acquisition_status import acquisition_outcome
    data = {"deep_research_trace": {"acquisition": acquisition_outcome([{"status": "TIMEOUT"}] * 9)}, "sources": []}
    report = UnifiedReport(agent=agent, summary="Normal financial conclusions", findings=["Should not survive failure"])
    result = _complete_agent_report(report, data, None, 0)
    assert result.investigation_status == "ACQUISITION_FAILED"
    assert not result.findings and not result.agent_intelligence
    assert "Unable to retrieve evidence" in result.summary


def test_discovered_candidate_reaches_read_and_publication(monkeypatch, tmp_path):
    from backend.application.research.pipeline import ResearchPipeline
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.research.research_models import ResearchRequest
    from backend.services import agent_reach
    from backend.services.research.replay_ledger import replay_ledger
    from backend.services.agent_reach.channels import RetrievalResult, QueryExecutionRecord
    fragment = EvidenceFragment(platform="web", channel_name="web", title="Lenovo quarterly results",
        url="https://investor.lenovo.com/en/financial/test-results.html",
        snippet="Lenovo reported quarterly revenue of USD 12 billion for fiscal Q1 2026.")
    retrieval = RetrievalResult(query="Lenovo", domain="financial", fragments=[fragment],
        query_records=[QueryExecutionRecord(query_id="q1", channel="web", query_text="Lenovo results", status="SUCCESS")])
    reader = MagicMock(return_value={"status": "success", "markdown": "Lenovo reported quarterly revenue of USD 12 billion for fiscal Q1 2026. " * 25})
    monkeypatch.setattr(replay_ledger, "storage_dir", str(tmp_path))
    from backend.services.research.deep_reader import deep_reader
    with patch.object(agent_reach.agent_reach_service, "retrieve_many", return_value=retrieval), \
            patch.object(agent_reach.agent_reach_service, "read", reader), patch.object(deep_reader, "_cache", {}):
        result = ResearchPipeline(ResearchBudget(timeout_seconds=2, follow_up_budget=0, primary_escalation_budget=0, deep_read_budget=1)).run(
            ResearchRequest(target="Lenovo", domain="financial", deep_read_budget=1, corroboration_budget=0))
    assert reader.call_count == 1
    assert len(result.evidence) == 1
    assert result.telemetry["acquisition"]["status"] == "COMPLETED"
    assert result.telemetry["stage_timings_ms"]["Candidate qualification"] >= 0


@pytest.mark.parametrize("agent,domain", [("scout", "financial"), ("trending", "trending"),
                                         ("brandshield", "brand"), ("personal_watch", "personal")])
def test_pipeline_all_timeout_preserves_failure_in_dossier(monkeypatch, tmp_path, agent, domain):
    from backend.application.research.pipeline import ResearchPipeline
    from backend.application.research.acquisition import BroadDiscoveryStage
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.research.research_models import ResearchRequest
    from backend.services.research.replay_ledger import replay_ledger
    from backend.services.agent_reach.channels import RetrievalResult, QueryExecutionRecord
    retrieval = RetrievalResult(query="Example company", domain=domain, fragments=[], query_records=[
        QueryExecutionRecord(query_id=f"q{n}", channel="web", query_text="Example company",
                             status="TIMEOUT", provider_started=True) for n in range(9)])
    monkeypatch.setattr(BroadDiscoveryStage, "run", lambda *a: retrieval)
    monkeypatch.setattr(replay_ledger, "storage_dir", str(tmp_path))
    result = ResearchPipeline(ResearchBudget(timeout_seconds=0.5, follow_up_budget=0, primary_escalation_budget=0)).run(
        ResearchRequest(target="Example company", domain=domain, agent_name=agent, corroboration_budget=0))
    assert not result.evidence and not result.findings
    assert result.telemetry["acquisition"]["status"] == "ACQUISITION_FAILED"
    assert result.investigation_status == "ACQUISITION_FAILED"
    assert "Unable to retrieve evidence" in result.summary
    assert result.telemetry["acquisition"]["query_counts"]["TIMEOUT"] == 9
    dossier = replay_ledger.get_dossier(result.telemetry["dossier_id"])
    assert dossier["status"] == "ACQUISITION_FAILED"
    assert len(dossier["queries_executed"]) == 9
