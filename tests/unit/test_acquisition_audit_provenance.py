"""Offline audit controls: estimates cannot become original live measurements."""
import sys
from types import SimpleNamespace

import pytest

from backend.infrastructure.acquisition.network.budget import PublicRequestBudget, public_request_budget
from scripts.audits.acquisition_replay import ReplayService, label_replay_costs
from scripts.audits.resource_sampler import ResourceSampler


@pytest.mark.parametrize("record,expected,basis", [
    ({"status": "TIMEOUT"}, 2, "ESTIMATED_UNKNOWN_QUERY_COST"),
    ({"status": "FAILED"}, 2, "ESTIMATED_UNKNOWN_QUERY_COST"),
    ({"status": "NOT_SUBMITTED", "provider_started": False}, 0, "RECORDED_NOT_STARTED"),
    ({"status": "FAILED", "native_http_admissions": 1}, 1, "RECORDED_QUERY_ADMISSIONS"),
])
def test_search_cost_includes_failed_or_unknown_transports(record, expected, basis):
    world = SimpleNamespace(channels=["news"], scale=0, median_read=0, wrapper_resolutions={},
        query_index={("news", "acme"): "q1"}, query_rows={"q1": record}, by_query={})
    service = ReplayService(world)
    budget = PublicRequestBudget(total=120, per_host=40)
    with public_request_budget(budget):
        result = service.retrieve_many({"news": [{"query_id": "q1", "query_text": "acme"}]})
    assert budget.snapshot()["native_http_admissions"] == expected
    assert service.counts[basis] == 1
    assert result.fragments == []


def test_modeled_costs_are_separate_from_measured_values():
    row = {"MEASURED": {"http_admissions": 52, "http_admissions_by_phase": {"reading": 30}},
           "DERIVED": {"evidence_words_per_100_admissions": 100, "qualified_sources_per_100_admissions": 2}}
    label_replay_costs(row)
    assert row["MEASURED"]["http_admissions"] == "NOT_RECORDED"
    assert row["MODELED"]["http_admissions"] == 52
    assert "evidence_words_per_100_admissions" not in row["DERIVED"]


def test_missing_resource_dependency_does_not_abort_investigation(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", None)
    with ResourceSampler() as sampler:
        sum(range(100))
    result = sampler.result()
    assert result["memory_measurement_status"] == "UNAVAILABLE"
    assert result["peak_rss_mb"] is None
    assert result["render_free_projection_ESTIMATE"]["peak_rss_within_ram_limit"] is None
    assert result["process_cpu_seconds"] >= 0
