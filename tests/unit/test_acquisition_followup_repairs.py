"""Four-prompt failure controls. Synthetic/offline; not research truth labels."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch
import pytest

from tests.unit.test_p0_acquisition_reliability import make_service
from backend.infrastructure.acquisition import service as acquisition
from backend.services.agent_reach.channels import EvidenceFragment


def test_stale_social_workers_do_not_starve_next_investigation(monkeypatch):
    release = threading.Event()
    blocked = MagicMock()
    blocked.search.side_effect = lambda *a, **k: (release.wait(5) and [])
    fast = MagicMock()
    fast.search.return_value = [EvidenceFragment(platform="news", title="Attributable report",
                                               url="https://publisher.example/report")]
    service = make_service(monkeypatch, {"reddit": blocked, "news": fast})
    monkeypatch.setattr(acquisition.native_doctor, "peek_channel_status", lambda *a: {})
    # Bound the reproduction and release every synthetic orphan, even on failure.
    pools = []
    if hasattr(acquisition, "_CHANNEL_SEARCH_POOLS"):
        pools = [ThreadPoolExecutor(max_workers=2), ThreadPoolExecutor(max_workers=2)]
        monkeypatch.setattr(acquisition, "_CHANNEL_SEARCH_POOLS", dict(zip(("reddit", "news"), pools)))
    try:
        traces = []
        for n in range(3):
            first = service.retrieve_many({"reddit": [f"query-{n}-{i}" for i in range(3)]},
                                          timeout=0.15, perform_reads=False)
            traces.extend(first.query_records)
        assert any(record.status == "TIMEOUT" for record in traces)
        second = service.retrieve_many({"news": ["Tim Cook public report"]},
                                       timeout=0.5, perform_reads=False)
        assert len(second.fragments) == 1
        assert second.query_records[0].provider_started is True
    finally:
        release.set()
        for pool in pools:
            pool.shutdown(wait=True)


def test_financial_careers_landing_is_not_selected_as_financial_evidence():
    from backend.services.research.relevance_gate import relevance_gate
    from backend.services.research.research_models import EvidenceItem
    item = EvidenceItem(id="career", title="Infosys Careers", snippet="Explore opportunities at Infosys",
                        canonical_url="https://digitalcareers.infosys.com/infosys/global-careers")
    assert not relevance_gate.evaluate_item(item, "Infosys", domain="financial").is_accepted


def test_brand_objective_outweighs_primary_storefront():
    from backend.services.research.deep_reader import DeepReader
    from backend.services.research.research_models import EvidenceItem
    # Selection metadata is applied by the shared stage before the primary pass.
    store = EvidenceItem(id="store", title="Nike store", canonical_url="https://nike.com/",
                         primary_source=True, relevance_score=0.9, source_quality_score=0.92,
                         metadata={"read_exclusion_reason": "background_not_agent_objective"})
    allegation = EvidenceItem(id="report", title="Nike impersonation allegation",
                              canonical_url="https://publisher.example/report", relevance_score=0.7,
                              source_quality_score=0.8)
    selected, _ = DeepReader()._select_read_candidates([store, allegation], max_reads=1)
    assert [item.id for item in selected] == ["report"]


def test_compact_issuer_release_precedes_large_auditor_pack():
    from backend.infrastructure.acquisition.adapters.web.page_extraction import document_link_priority
    release = {"url": "https://issuer.example/q1/ifrs-usd-press-release.pdf", "text": "IFRS USD"}
    audit = {"url": "https://issuer.example/q1/financial-results-auditorsreports.pdf", "text": "Standalone consolidated results and auditors reports"}
    assert document_link_priority(release) < document_link_priority(audit)


def test_nested_chain_deadlines_cannot_reset_timeout(monkeypatch):
    from backend.infrastructure.acquisition.network import budget
    clock = [100.0]
    monkeypatch.setattr(budget.time, "monotonic", lambda: clock[0])
    with budget.acquisition_deadline(102.0):
        assert budget.remaining_timeout(5) == 2
        clock[0] = 101.0
        with budget.acquisition_deadline(200.0):
            assert budget.remaining_timeout(5) == 1
        clock[0] = 103.0
        with pytest.raises(TimeoutError):
            budget.remaining_timeout(5)
    assert budget.remaining_timeout(5) == 5


def test_expired_chain_never_opens_another_http_request(monkeypatch):
    from backend.infrastructure.acquisition.network import budget, http
    clock = [100.0]
    monkeypatch.setattr(budget.time, "monotonic", lambda: clock[0])
    opener = MagicMock()
    monkeypatch.setattr(http.urllib.request, "build_opener", opener)
    with budget.acquisition_deadline(101):
        clock[0] = 102
        with pytest.raises(TimeoutError):
            http.fetch_public_http("https://public.example/article")
    opener.assert_not_called()


@pytest.mark.parametrize("matching", [True, False])
def test_wrapper_lookup_requires_matching_observed_publisher_and_keeps_lineage(monkeypatch, matching):
    from backend.services.research.deep_reader import DeepReader
    from backend.services.research.research_models import EvidenceItem
    from backend.services.agent_reach.channels import RetrievalResult
    from backend.services import agent_reach
    wrapper = "https://news.google.com/rss/articles/opaque-token"
    observed = "https://publisher.example/public-report"
    title = "Public Person denies fabricated investment recommendation"
    lead = EvidenceFragment(platform="web", url=observed,
                            title=title if matching else "Public Person launches a product")
    lookup = MagicMock(return_value=RetrievalResult(query=title, domain="general", fragments=[lead]))
    read = MagicMock(return_value={"status": "success", "markdown": title + ". An attributable statement, not an independently verified denial.",
                                  "page_metadata": {"author": "Body author"}})
    item = EvidenceItem(id="canonical", title=title, canonical_url=wrapper, channel="news",
                        relevance_score=0.8, source_quality_score=0.7, source_name="Feed attribution")
    # patch.object removes temporary instance overrides on exit. setattr/undo
    # would leave a bound method shadowing later class-level compatibility mocks.
    with patch.object(agent_reach.agent_reach_service, "retrieve_many", lookup), \
            patch.object(agent_reach.agent_reach_service, "read", read):
        items, telemetry = DeepReader().deep_read([item], max_reads=1, timeout_per_read=2)
    lookup.assert_called_once()
    if matching:
        assert items == [item] and item.id == "canonical"
        assert item.canonical_url == observed and item.metadata["discovery_url"] == wrapper
        assert item.metadata["attribution_conflict"] is True
        assert telemetry["acquisition_attempts"][0]["wrapper_resolution"]["selected_url"] == observed
        read.assert_called_once_with(observed, max_chars=12_000)
    else:
        assert not items and telemetry["successful"] == 0
        read.assert_not_called()


def test_real_hiring_claim_still_accepts_employment_source():
    from backend.services.research.relevance_gate import relevance_gate
    from backend.services.research.research_models import EvidenceItem
    item = EvidenceItem(id="career", title="Infosys hiring announcement", snippet="Infosys recruitment policy",
                        canonical_url="https://digitalcareers.infosys.com/infosys/global-careers")
    assert relevance_gate.evaluate_item(item, "Infosys", domain="financial", intent="Verify Infosys hiring policy").is_accepted


def test_brand_news_slots_target_reports_not_generic_stock_news():
    from backend.services.agent_reach.source_planner import SourcePlanningEngine
    plan = SourcePlanningEngine().plan("Nike", entity="Nike", domain="brand", agent="brandshield", use_llm=False)
    news = plan.to_channel_queries()["news"]
    assert news[0]["query_text"] == '"Nike" counterfeit'
    assert news[1]["query_text"] == '"Nike" phishing'


def test_legacy_feed_parser_receives_bytes_never_a_network_url(monkeypatch):
    from backend.services import agent_reach_scraper as module
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
    body = b"<rss><channel><title>Captured feed</title></channel></rss>"
    fetch = MagicMock(return_value=BoundedHTTPResponse(body=body, endpoint="https://publisher.example/feed",
        status_code=200, content_type="application/xml", headers={}, latency_ms=1, attempts=1))
    parse = MagicMock(return_value={"entries": []})
    monkeypatch.setattr(module, "fetch_public_http", fetch)
    monkeypatch.setattr(module.feedparser, "parse", parse)
    module.AgentReachScraper()._read_feed("https://publisher.example/feed")
    parse.assert_called_once_with(body)
    assert fetch.call_args.kwargs["timeout"] <= 5
    assert fetch.call_args.kwargs["max_bytes"] == 1_000_000


def test_swallowed_provider_deadline_is_not_success(monkeypatch):
    slow = MagicMock()
    def caught_timeout(*args, **kwargs):
        time.sleep(0.1)
        return []
    slow.search.side_effect = caught_timeout
    service = make_service(monkeypatch, {"web": slow})
    monkeypatch.setattr(acquisition.native_doctor, "peek_channel_status", lambda *a: {})
    result = service.retrieve_many({"web": ["subject"]}, perform_reads=False,
                                   timeout=1.0, budget={"channel_timeout": 0.02})
    assert result.query_records[0].status == "TIMEOUT"
    assert result.query_records[0].provider_started is True
