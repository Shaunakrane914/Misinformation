"""Offline admission controls for opt-in cumulative discovery credit release."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import time

import pytest

from backend.infrastructure.acquisition.network.budget import (
    PublicRequestBudget, acquisition_deadline, configure_interleaved_discovery,
    discovery_http_remaining, public_request_budget, public_request_phase,
    release_adaptive_discovery, reserve_public_request, reserve_reading_capacity,
)


def admit(count):
    # Separate fixture hosts isolate the cumulative cap from the stricter host cap.
    for index in range(count):
        reserve_public_request("https://source" + str(index) + ".example/article")


@pytest.mark.parametrize("total,initial,adaptive,legacy", [(120, 35, 25, 60), (80, 23, 17, 40), (40, 12, 8, 20)])
def test_scaled_release_retains_reading_reserve_and_total_cap(total, initial, adaptive, legacy):
    budget = PublicRequestBudget(total=total, per_host=24)
    with public_request_budget(budget):
        reserve_reading_capacity(total)
        configure_interleaved_discovery()
        with public_request_phase("discovery"):
            admit(initial)
            assert discovery_http_remaining() == 0
            with pytest.raises(TimeoutError):
                reserve_public_request("https://initial-overflow.example/article")
        with public_request_phase("reading"):
            admit(total - legacy)
        assert release_adaptive_discovery(2) == 2
        assert release_adaptive_discovery(1000) == adaptive - 2
        assert release_adaptive_discovery() == 0
        with public_request_phase("discovery"):
            admit(adaptive)
        assert budget.snapshot()["native_http_admissions"] == total
        assert budget.snapshot()["discovery_http_cap"] == legacy
        with pytest.raises(TimeoutError):
            reserve_public_request("https://total-overflow.example/article")


def test_default_snapshot_and_allowance_unchanged_without_opt_in():
    budget = PublicRequestBudget(total=8, per_host=8)
    with public_request_budget(budget):
        reserve_reading_capacity(4)
        assert release_adaptive_discovery() == 0
        assert "interleaved_discovery_budget" not in budget.snapshot()
        with public_request_phase("discovery"):
            admit(4)
            with pytest.raises(TimeoutError):
                reserve_public_request("https://overflow.example/article")
        assert budget.snapshot()["discovery_http_cap"] == 4


def test_release_cannot_reset_spent_credit_or_expand_host_allowance():
    budget = PublicRequestBudget(total=120, per_host=6)
    with public_request_budget(budget):
        reserve_reading_capacity(60)
        configure_interleaved_discovery()
        with public_request_phase("discovery"):
            reserve_public_request("https://same.example/one")
            reserve_public_request("https://same.example/two")
            with pytest.raises(TimeoutError):
                reserve_public_request("https://same.example/three")
        assert release_adaptive_discovery() == 25
        assert configure_interleaved_discovery()["adaptive_released"] == 25
        assert release_adaptive_discovery() == 0
        with public_request_phase("discovery"):
            with pytest.raises(TimeoutError):
                reserve_public_request("https://same.example/after-release")
        assert budget.snapshot()["native_http_by_host"]["same.example"] == 2


def test_concurrent_copied_contexts_share_one_cumulative_discovery_cap():
    budget = PublicRequestBudget(total=120, per_host=24)
    def reserve_one(index):
        try:
            reserve_public_request("https://parallel" + str(index) + ".example/article")
            return True
        except TimeoutError:
            return False
    with public_request_budget(budget), public_request_phase("discovery"):
        reserve_reading_capacity(60)
        configure_interleaved_discovery()
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = [executor.submit(copy_context().run, reserve_one, index) for index in range(80)]
            assert sum(result.result() for result in results) == 35
        assert release_adaptive_discovery() == 25
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = [executor.submit(copy_context().run, reserve_one, index) for index in range(80, 160)]
            assert sum(result.result() for result in results) == 25
    assert budget.snapshot()["native_http_by_phase"] == {"discovery": 60}


def test_stronger_later_reading_fence_and_closed_budget_cannot_be_reopened():
    budget = PublicRequestBudget()
    with public_request_budget(budget):
        reserve_reading_capacity(60)
        configure_interleaved_discovery()
        budget.reserve_reading_capacity(100)
        assert release_adaptive_discovery() == 0
        assert budget.snapshot()["discovery_http_cap"] == 20
        budget.close()
        with pytest.raises(TimeoutError):
            configure_interleaved_discovery()
        with pytest.raises(TimeoutError):
            release_adaptive_discovery()
        with pytest.raises(TimeoutError):
            reserve_public_request("https://closed.example/article")


def test_expired_deadline_does_not_release_or_reconfigure():
    budget = PublicRequestBudget()
    with public_request_budget(budget):
        reserve_reading_capacity(60)
        configure_interleaved_discovery()
        with acquisition_deadline(time.monotonic() + 10):
            import backend.infrastructure.acquisition.network.budget as module
            original = module.time.monotonic
            try:
                module.time.monotonic = lambda: original() + 20
                with pytest.raises(TimeoutError):
                    release_adaptive_discovery()
                with pytest.raises(TimeoutError):
                    configure_interleaved_discovery()
            finally:
                module.time.monotonic = original
        assert budget.snapshot()["discovery_http_cap"] == 35


@pytest.mark.parametrize("initial,adaptive", [(-1, 25), (35, -1), (36, 25), (True, 25), (35.0, 25)])
def test_invalid_configuration_cannot_expand_budget(initial, adaptive):
    budget = PublicRequestBudget()
    with pytest.raises(ValueError):
        budget.configure_interleaved_discovery(initial, adaptive)
    assert budget.snapshot()["discovery_http_cap"] == 120
