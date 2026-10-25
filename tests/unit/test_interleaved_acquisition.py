"""Synthetic offline controller controls; live recall is measured separately."""
import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import time

import pytest

from backend.infrastructure.acquisition.network.budget import PublicRequestBudget, public_request_budget
from backend.services.agent_reach.channels import EvidenceFragment, QueryExecutionRecord, RetrievalResult
from backend.services.research.adaptive_acquisition import InterleavedController, inspect_capture
from backend.services.research.harvesting import HarvestingEngine
from backend.services.research.research_models import EvidenceItem
from backend.services.research.research_profiles import QUICK


def captured(text=None, *, domain="financial", published=None, kind="ARTICLE_BODY", host="publisher.example"):
    text = text or ("Orion Devices reported quarterly revenue of USD 40 million, an increase of 8 percent from the prior year. "
                    "Operating profit reached USD 6 million, according to the company's published earnings statement. "
                    "Management said the figures cover the fiscal quarter ending in June and remain subject to audit.")
    return EvidenceItem(id="captured", canonical_url="https://" + host + "/orion-results", title="Orion Devices quarterly earnings",
        content=text, content_depth="DEEP_READ", acquired_id="native-capture", metadata={"read_success": True,
            "acquisition_objective": "PUBLIC_STATEMENT", "page_metadata": {"body_kind": kind, "published": published or ""}})


class SourceReplay:
    def __init__(self, *, fail=False, fixed_host=None, read_delay=0):
        self.events = []
        self.wave = 0
        self.fail = fail
        self.fixed_host = fixed_host
        self.read_delay = read_delay

    def retrieve_many(self, plan, **kwargs):
        self.wave += 1
        self.events.append("DISCOVERY")
        rows = [(channel, row) for channel, queries in plan.items() for row in queries]
        channel, first = rows[0]
        lead = EvidenceFragment(platform=channel, title="Orion Devices quarterly earnings",
            url="https://" + (self.fixed_host or "publisher" + str(self.wave) + ".example") + "/orion-results-" + str(self.wave), query_id=first["query_id"],
            query_text=first["query_text"], query_class=first.get("query_class", "general"))
        return RetrievalResult(query="Orion Devices", domain="financial", fragments=[lead], query_records=[
            QueryExecutionRecord(query_id=row["query_id"], channel=channel, query_text=row["query_text"],
                query_class=row.get("query_class", "general"), status="SUCCESS") for channel, row in rows])

    def read(self, url, max_chars=12_000):
        self.events.append("READ")
        if self.read_delay:
            time.sleep(self.read_delay)
        if self.fail:
            return {"status": "failed", "error": "HTTP403", "status_code": 403}
        text = captured().content + " The captured report identifies " + url.split("/")[2] + " as its publication."
        return {"status": "success", "markdown": text,
                "page_metadata": {"body_kind": "ARTICLE_BODY", "title": "Orion Devices quarterly earnings"}}


def profile():
    return replace(QUICK, max_queries=6, max_reads=6, concurrency=1, host_spacing_seconds=0)


def test_legacy_discovers_before_reading_and_has_no_experimental_diagnostics():
    service = SourceReplay()
    result = HarvestingEngine(service).run("Orion Devices", "financial", profile=profile())
    assert service.events[:2] == ["DISCOVERY", "DISCOVERY"]
    assert "acquisition_controller" not in result.metrics


def test_interleaves_real_shared_reader_and_preserves_one_attempt_counter():
    service = SourceReplay()
    with public_request_budget(PublicRequestBudget()):
        result = HarvestingEngine(service).run("Orion Devices", "financial", profile=profile(), controller="interleaved_v1")
    assert service.events == ["DISCOVERY", "READ", "DISCOVERY", "READ"]
    assert result.metrics["reads_attempted"] == 2
    assert len(result.captures) == 2
    feedback = result.metrics["acquisition_controller"]["feedback"]
    assert all(row["usable_passage"] for row in feedback)
    # Routing feedback must not pre-accept or rewrite a raw capture.
    assert all(item.metadata["qualification_status"] == "PENDING" for item in result.captures)
    assert all(not item.relevant_excerpt for item in result.captures)
    assert len({row.query_id for row in result.query_records}) == 6


def test_failed_reader_does_not_end_all_remaining_discovery():
    service = SourceReplay(fail=True)
    result = HarvestingEngine(service).run("Orion Devices", "financial", profile=profile(), controller="interleaved_v1")
    assert service.events == ["DISCOVERY", "READ", "DISCOVERY", "READ"]
    assert result.metrics["reads_attempted"] == 2 and not result.captures


def test_host_counters_survive_between_discovery_and_read_rounds():
    service = SourceReplay(fixed_host="same.example")
    result = HarvestingEngine(service).run("Orion Devices", "financial",
        profile=replace(profile(), max_host_reads=1), controller="interleaved_v1")
    assert service.events == ["DISCOVERY", "READ", "DISCOVERY"]
    assert result.metrics["reads_attempted"] == 1
    assert result.metrics["source_diversity"]["read_publisher_reservations"] == {"same.example": 1}
    assert result.metrics["unread_by_reason"] == {"HOST_READ_BUDGET_EXHAUSTED": 1}


def test_expired_parent_deadline_never_starts_a_search_or_read():
    service = SourceReplay()
    result = HarvestingEngine(service).run("Orion Devices", "financial", profile=profile(),
        deadline=time.monotonic() - 1, controller="interleaved_v1")
    assert not service.events
    assert result.metrics["reads_attempted"] == 0
    assert all(row.status == "NOT_SUBMITTED" for row in result.query_records)


def test_slow_read_does_not_spend_remaining_active_discovery_allowance():
    service = SourceReplay(read_delay=.07)
    result = HarvestingEngine(service).run("Orion Devices", "financial",
        profile=replace(profile(), discovery_seconds=.05), controller="interleaved_v1")
    assert service.events == ["DISCOVERY", "READ", "DISCOVERY", "READ"]
    assert result.metrics["reads_attempted"] == 2


def test_better_discovery_date_alias_can_reconsider_deferred_url():
    now = datetime.now(timezone.utc)

    class DateAliases(SourceReplay):
        def retrieve_many(self, plan, **kwargs):
            result = super().retrieve_many(plan, **kwargs)
            result.fragments[0].url = "https://publisher.example/ocean-carbon-removal"
            result.fragments[0].title = "Ocean carbon removal study announced"
            result.fragments[0].published = (now - timedelta(hours=200 if self.wave == 1 else 1)).isoformat()
            return result

        def read(self, url, max_chars=12_000):
            self.events.append("READ")
            return {"status": "success", "markdown": "Ocean carbon removal research was announced by the institute after a controlled field study. The report describes observed measurements, limitations and planned follow-up experiments. The team said these results do not establish general environmental safety.",
                "page_metadata": {"body_kind": "ARTICLE_BODY", "published": (now - timedelta(hours=1)).isoformat()}}

    service = DateAliases()
    result = HarvestingEngine(service).run("ocean carbon removal", "trending", profile=profile(), controller="interleaved_v1")
    assert service.events == ["DISCOVERY", "DISCOVERY", "READ"]
    assert result.metrics["acquisition_controller"]["feedback"][0]["usable_passage"]
    assert result.captures[0].metadata["temporal_routing_basis"] == "BEST_OBSERVED_DISCOVERY_ALIAS_NOT_BODY_VERIFICATION"


def test_feedback_uses_existing_body_gates_on_a_copy():
    item = captured()
    before = copy.deepcopy(item.to_dict())
    result = inspect_capture(item, "Orion Devices", "financial", "financial performance", datetime.now(timezone.utc))
    assert result["usable_passage"] and result["selected_excerpt_words"] > 10
    assert item.to_dict() == before
    index = captured(kind="UNCLASSIFIED_PAGE")
    assert not inspect_capture(index, "Orion Devices", "financial", "", datetime.now(timezone.utc))["usable_passage"]


@pytest.mark.parametrize("hours,expected", [(1, True), (240, False), (-24, False), (None, False)])
def test_unknown_discovery_dates_require_captured_fresh_publication(hours, expected):
    now = datetime.now(timezone.utc)
    published = (now - timedelta(hours=hours)).isoformat() if hours is not None else ""
    item = captured("Ocean carbon removal research was announced by the institute after a controlled field study. "
        "The report describes the observed measurements, limitations and planned follow-up experiments. "
        "The team said the findings do not establish deployment readiness or general environmental safety.", published=published)
    item.title = "Ocean carbon removal study"
    item.published_at = now.isoformat()  # A favorable discovery date cannot replace a missing body date.
    result = inspect_capture(item, "ocean carbon removal", "trending", "", now)
    assert result["usable_passage"] is expected


def test_stale_hints_are_deferred_but_unknown_dates_keep_read_opportunity():
    control = InterleavedController("ocean carbon removal", "trending", "", datetime.now(timezone.utc))
    item = captured()
    assert control.defer_reason(item) is None
    item.metadata["discovery_temporal_observation"] = "STALE"
    assert control.defer_reason(item) == "DEFERRED_DISCOVERY_DATE_STALE"
    item.metadata["discovery_temporal_observation"] = "MISSING_TIMESTAMP"
    assert control.defer_reason(item) is None


def test_two_zero_yield_articles_defer_more_of_same_publisher_tree():
    control = InterleavedController("Orion Devices", "financial", "", datetime.now(timezone.utc))
    for suffix in ("first", "second"):
        item = captured("Completely unrelated garden plants grow in spring. The report describes seasonal rainfall and soil conditions. " + suffix)
        control.observe(item)
    assert control.defer_reason(captured()) == "DEFERRED_ZERO_YIELD_PUBLISHER_TREE"
    assert control.defer_reason(captured(host="different.example")) is None


def test_identical_bodies_do_not_establish_two_source_coverage():
    control = InterleavedController("Orion Devices", "financial", "", datetime.now(timezone.utc))
    control.observe(captured())
    control.observe(captured(host="other.example"))
    assert not control.enough_for_discovery_pause()
    assert control.feedback[-1]["duplicate_body_observation"]


def test_useful_article_resets_failure_streak_and_fresh_hint_can_test_a_stale_tree():
    now = datetime.now(timezone.utc)
    control = InterleavedController("Orion Devices", "financial", "", now)
    bad = "Unrelated garden plants grow in spring. The report describes rainfall and soil conditions. "
    control.observe(captured(bad + "First unrelated report."))
    control.observe(captured())
    control.observe(captured(bad + "Second unrelated report."))
    assert control.defer_reason(captured()) is None
    control.observe(captured(bad + "Third unrelated report."))
    assert control.defer_reason(captured()) == "DEFERRED_ZERO_YIELD_PUBLISHER_TREE"
    control.domain = "trending"
    fresh = captured()
    fresh.metadata["discovery_temporal_observation"] = "FRESH"
    assert control.defer_reason(fresh) is None


def test_unrecognized_controller_fails_explicitly():
    with pytest.raises(ValueError, match="Unknown acquisition controller"):
        HarvestingEngine(SourceReplay()).run("Orion Devices", controller="unbounded")
