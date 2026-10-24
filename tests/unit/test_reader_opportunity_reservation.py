"""Offline capacity controls. These are not live article-yield assertions."""
import threading
import time
from contextvars import copy_context
from dataclasses import replace

import pytest

from backend.infrastructure.acquisition.network.budget import (
    PublicRequestBudget, public_request_budget, public_request_phase, reserve_public_request,
    reserve_reading_capacity, discovery_http_remaining,
)
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalResult
from backend.services.research.harvesting import HarvestingEngine, _BudgetedService
from backend.services.research.research_profiles import QUICK


def test_discovery_does_not_spend_reserved_reader_allowance():
    budget = PublicRequestBudget(total=8, per_host=8)
    with public_request_budget(budget):
        reserve_reading_capacity(4)
        with public_request_phase("discovery"):
            for _ in range(4):
                reserve_public_request("https://search.example/query")
            with pytest.raises(TimeoutError, match="reserved for reading"):
                reserve_public_request("https://search.example/query")
        assert discovery_http_remaining() == 0
        for _ in range(4):
            reserve_public_request("https://publisher.example/article")
        with pytest.raises(TimeoutError):
            reserve_public_request("https://publisher.example/extra")
    snapshot = budget.snapshot()
    assert snapshot["native_http_admissions"] == 8
    assert snapshot["native_http_by_phase"] == {"discovery": 4, "reading": 4}


def test_phase_reservation_is_shared_by_copied_worker_contexts():
    budget = PublicRequestBudget(total=20, per_host=20)
    failures = []
    def admit():
        try:
            reserve_public_request("https://search.example/query")
        except TimeoutError:
            failures.append(True)
    with public_request_budget(budget):
        reserve_reading_capacity(10)
        with public_request_phase("discovery"):
            workers = [threading.Thread(target=copy_context().run, args=(admit,)) for _ in range(20)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()
        reserve_public_request("https://publisher.example/article")
    assert len(failures) == 10
    assert budget.snapshot()["native_http_admissions"] == 11


def test_search_phase_preserves_host_slots_and_closed_budget_stays_closed():
    budget = PublicRequestBudget(total=20, per_host=6)
    with public_request_budget(budget):
        reserve_reading_capacity(6)
        with public_request_phase("discovery"):
            for _ in range(2):
                reserve_public_request("https://shared.example/search")
            with pytest.raises(TimeoutError):
                reserve_public_request("https://shared.example/search")
        for _ in range(4):
            reserve_public_request("https://shared.example/article")
        with pytest.raises(TimeoutError):
            reserve_public_request("https://shared.example/article")
        budget.close()
        with pytest.raises(TimeoutError):
            reserve_public_request("https://other.example/article")


def test_starved_discovery_yields_to_actual_article_reading():
    class Service:
        def __init__(self):
            self.calls, self.reads = 0, []
        def retrieve_many(self, plan, **kwargs):
            self.calls += 1
            # Simulate provider fanout trying to consume the complete run.
            for _ in range(50):
                try:
                    reserve_public_request("https://search.example/query")
                except TimeoutError:
                    break
            return RetrievalResult(query="Willow Devices", domain="financial", fragments=[EvidenceFragment(
                platform="web", title="Willow Devices quarterly earnings", url="https://publisher.example/willow-earnings")])
        def read(self, url, max_chars):
            reserve_public_request(url)
            self.reads.append(max_chars)
            return {"status": "success", "content": "Willow Devices reported revenue of USD 12 million. " * 400,
                    "page_metadata": {"title": "Willow Devices quarterly earnings", "content_scope": "article",
                                      "body_quality": {"body_kind": "ARTICLE_BODY"}}}
    service = Service()
    budget = PublicRequestBudget(total=12, per_host=24)
    with public_request_budget(budget):
        result = HarvestingEngine(service).run("Willow Devices", "financial", profile=QUICK)
    assert service.calls == 1 and service.reads == [20_000]
    assert result.metrics["article_bodies"] == 1
    assert result.retrieval_trace["discovery_stop_reason"] == "DISCOVERY_HTTP_RESERVE_FOR_READING"
    unsubmitted = [row for row in result.query_records if row.status == "NOT_SUBMITTED"]
    assert unsubmitted and {row.error for row in unsubmitted} == {"DISCOVERY_HTTP_RESERVE_FOR_READING"}
    assert budget.snapshot()["native_http_admissions"] == 7


def test_reader_requests_larger_bounded_capture_without_new_network_fetch():
    class Service:
        sizes = []
        def read(self, url, max_chars):
            self.sizes.append(max_chars)
            return {"content": "x" * max_chars}
    service = Service()
    bounded = _BudgetedService(service, replace(QUICK, host_spacing_seconds=0), time.monotonic() + 5)
    assert len(bounded.read("https://publisher.example/article", max_chars=100_000)["content"]) == 20_000
    assert service.sizes == [20_000]


@pytest.mark.parametrize("domain,target", [("financial", "Willow Devices"), ("brand", "Willow Devices"),
                                          ("personal", "Elena Rivera")])
def test_observed_hub_continuation_is_shared_by_nontrending_agents(domain, target):
    class Service:
        reads = []
        def retrieve_many(self, plan, **kwargs):
            return RetrievalResult(query=target, domain=domain, fragments=[EvidenceFragment(platform="news",
                title=target + " public statement earnings", url="https://news.google.com/articles/opaque",
                raw_metadata={"publisher_source_url": "https://publisher.example"})])
        def read(self, url, max_chars):
            self.reads.append(url)
            hub = url == "https://publisher.example"
            return {"status": "success", "content": (target + " reported a public statement and earnings. ") * 30,
                "page_metadata": {"title": target + " public statement earnings", "content_scope": "NEWS_INDEX" if hub else "article",
                    "body_quality": {"body_kind": "UNCLASSIFIED_PAGE" if hub else "ARTICLE_BODY"},
                    "observed_links": [{"url": "https://publisher.example/observed-story", "text": target + " public statement earnings"}] if hub else []}}
    service = Service()
    profile = replace(QUICK, max_queries=1, max_wrapper_reads=0, host_spacing_seconds=0)
    result = HarvestingEngine(service).run(target, domain, profile=profile)
    assert service.reads == ["https://publisher.example", "https://publisher.example/observed-story"]
    assert result.metrics["article_bodies"] == 1
    assert result.metrics["reads_attempted"] == 2


def test_pipeline_legacy_rejections_do_not_count_unsubmitted_navigation_links():
    from unittest.mock import patch
    from backend.application.research.harvest_pipeline import run_harvest_pipeline
    from backend.services.research.harvesting import HarvestResult
    from backend.services.research.research_models import EvidenceItem, ResearchRequest
    from backend.services.research.research_budget import ResearchBudget
    candidate = EvidenceItem(id="actual-lead", canonical_url="https://publisher.example/story", title="Willow Devices report")
    rejected = [{"candidate_id": "actual-lead", "url": candidate.canonical_url, "reason": "NOT_READ"}]
    rejected += [{"parent_id": "observed-homepage", "url": f"https://publisher.example/navigation-{i}",
                  "discard_reason": "OFF_OBJECTIVE"} for i in range(110)]
    saved = HarvestResult(candidates=[candidate], rejected=rejected,
        metrics={"candidates_accepted_for_read": 1}, read_telemetry={"attempted": 0, "successful": 0, "total_chars_read": 0})
    with patch("backend.services.research.harvesting.HarvestingEngine.run", return_value=saved), \
         patch("backend.application.research.assembly.DossierRegistrationStage.run"):
        result = run_harvest_pipeline(ResearchRequest(target="Willow Devices", domain="financial"),
                                     ResearchBudget(timeout_seconds=30), "QUICK")
    assert result.research_corpus["funnel"]["candidates_rejected"] == 1
    assert result.research_corpus["funnel"]["publisher_link_decision_count"] == 110
    assert result.telemetry["candidates_rejected"] == 1
