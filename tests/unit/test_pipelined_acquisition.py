"""Experimental pipelined scheduler: scheduling properties, caps, safety and honest accounting.

Offline: a deterministic fake world serves leads and pages with controllable latency, outcomes and
hosts through the real HarvestingEngine. No network, model or provider call. Performance is NOT asserted
here beyond structure (overlap, no round barrier); measured throughput lives in the replay benchmark.
"""
import threading
import time
from collections import Counter
from types import SimpleNamespace

import pytest

from backend.infrastructure.acquisition.network.budget import PublicRequestBudget, public_request_budget, reserve_public_request
from backend.services.agent_reach.channels import EvidenceFragment, QueryExecutionRecord, RetrievalResult
from backend.services.research.candidate_selection import SelectionContext, YieldMemory, article_shaped, is_index_like, score_candidate
from backend.services.research.harvesting import HarvestingEngine, _is_index, _is_wrapper
from backend.services.research.research_models import EvidenceItem

ARTICLE_TEXT = ("Acme Corp reported quarterly earnings revenue of $5 billion and said guidance improved for the next quarter. "
                "The company's chief executive said demand remained strong across all regions this year. ") * 3


class FakeWorld:
    """Leads come from a cursor over ``leads``; pages from ``pages`` keyed by URL."""

    def __init__(self, leads, pages, per_query=3, search_latency=0.01, admissions_per_call=0):
        self.leads, self.pages, self.per_query = list(leads), pages, per_query
        self.search_latency, self.admissions_per_call = search_latency, admissions_per_call
        self.registry = SimpleNamespace(channel_names=("web", "news", "rss"))
        self.lock = threading.Lock()
        self.cursor = 0
        self.reads, self.searches = [], []
        self.active, self.max_active = 0, 0
        self.active_hosts, self.max_host = Counter(), 0

    def retrieve_many(self, channel_queries, **kwargs):
        started = time.monotonic()
        rows = [(channel, row) for channel, rs in channel_queries.items() for row in rs]
        if self.admissions_per_call:
            for _ in range(self.admissions_per_call):
                reserve_public_request("https://search.example/q")
        time.sleep(self.search_latency)
        fragments, records = [], []
        with self.lock:
            for channel, row in rows:
                chosen = self.leads[self.cursor:self.cursor + self.per_query]
                self.cursor += len(chosen)
                for lead in chosen:
                    fragments.append(EvidenceFragment(
                        platform="web", title=lead["title"], url=lead["url"], snippet=lead.get("snippet", lead["title"]),
                        published=lead.get("published", ""), channel_name=channel, query_id=row["query_id"],
                        query_class=row.get("query_class", "general"), query_text=row["query_text"],
                        content_depth="FEED_ENTRY_SUMMARY", evidence_id="up_" + lead["url"][-12:]))
                records.append(QueryExecutionRecord(query_id=row["query_id"], channel=channel, query_text=row["query_text"],
                                                    status="SUCCESS", result_count_raw=len(chosen), result_count_normalized=len(chosen)))
            self.searches.append((tuple(r["query_id"] for _, r in rows), started, time.monotonic()))
        return RetrievalResult(query="", domain=kwargs.get("domain", ""), fragments=fragments, query_records=records)

    def read(self, url, max_chars=12_000):
        host = url.split("/")[2]
        with self.lock:
            self.active += 1
            self.active_hosts[host] += 1
            self.max_active = max(self.max_active, self.active)
            self.max_host = max(self.max_host, self.active_hosts[host])
        started = time.monotonic()
        try:
            page = self.pages.get(url, {"latency": 0.02, "ok": False})
            if self.admissions_per_call:
                reserve_public_request(url)
            time.sleep(page["latency"])
            if not page["ok"]:
                return {"status": "error", "error": "HTTP 403 Forbidden", "failure_kind": "ACCESS_DENIED"}
            kind = "ARTICLE_BODY" if page.get("article", True) else "UNCLASSIFIED_PAGE"
            return {"status": "success", "markdown": page.get("text", ARTICLE_TEXT), "content": page.get("text", ARTICLE_TEXT),
                    "page_metadata": {"title": page.get("title", ""), "body_kind": kind, "body_quality": {"body_kind": kind}},
                    "transport": {"endpoint": url, "redirect_chain": [url], "http_status": 200}, "backend": "fake"}
        finally:
            with self.lock:
                self.active -= 1
                self.active_hosts[host] -= 1
                self.reads.append((url, started, time.monotonic()))


def article(n, host=None, latency=0.02, ok=True):
    host = host or f"news{n}.example"
    url = f"https://{host}/2026/05/acme-corp-reports-record-quarterly-earnings-{n}"
    return {"url": url, "title": f"Acme Corp reports record quarterly earnings {n}"}, {"latency": latency, "ok": ok}


def junk(n, latency=0.02):
    url = f"https://spam{n}.example/world-acme-market-report-forecast-{n}"
    return {"url": url, "title": f"Acme Corp market report {n}"}, {"latency": latency, "ok": False}


def build(articles=12, junks=0, latencies=None, per_query=3, **kw):
    leads, pages = [], {}
    for n in range(articles):
        lead, page = article(n, latency=(latencies[n] if latencies else 0.02))
        leads.append(lead); pages[lead["url"]] = page
    for n in range(junks):
        lead, page = junk(n)
        leads.append(lead); pages[lead["url"]] = page
    return FakeWorld(leads, pages, per_query=per_query, **kw)


def run(world, controller="pipelined_v1", monkeypatch=None, env=None, deadline_seconds=20.0):
    for key, value in (env or {}).items():
        monkeypatch.setenv(key, value)
    return HarvestingEngine(world).run(target="Acme Corp", domain="financial", agent_name="scout", profile="DEEP",
                                       deadline=time.monotonic() + deadline_seconds, controller=controller)


def controller_trace(result):
    return result.metrics["acquisition_controller"]


# ── Structure: no round barrier, overlap, caps ───────────────────────────────────────────────

def test_runs_end_to_end_with_no_duplicate_reads_and_cap_respected(monkeypatch):
    world = build(articles=40, per_query=3)
    result = run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "3"})
    urls = [u for u, _, _ in world.reads]
    assert len(urls) == len(set(urls))                                  # no URL read twice
    assert result.read_telemetry["attempted"] <= 24                     # DEEP profile cap, unchanged
    assert controller_trace(result)["mode"] == "pipelined_v1"
    assert result.metrics["article_bodies"] > 0
    assert world.max_active <= 3                                        # configured worker bound


def test_reads_do_not_wait_for_a_round_barrier(monkeypatch):
    """With two workers, a fast read finishing frees its worker while the slow read still runs."""
    latencies = [0.4, 0.02, 0.02, 0.02, 0.02, 0.02] + [0.02] * 10

    def late_starts(world):
        slow = next(row for row in world.reads if row[2] - row[1] >= 0.35)
        # Reads that start after the initial dispatch burst but before the slow read ends.
        return [r for r in world.reads if slow[1] + 0.1 < r[1] < slow[2]]

    legacy_world = build(articles=16, latencies=latencies, per_query=4)
    run(legacy_world, controller="legacy")
    assert late_starts(legacy_world) == []                              # the legacy round waits for its slowest read

    world = build(articles=16, latencies=latencies, per_query=4)
    run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "2"})
    assert len(late_starts(world)) >= 3                                 # pipelined reads keep flowing past the slow one


def test_discovery_and_reading_overlap(monkeypatch):
    world = build(articles=30, per_query=2, search_latency=0.15)
    run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "2"})
    first_read_start = min(start for _, start, _ in world.reads)
    last_search_end = max(end for _, _, end in world.searches)
    assert first_read_start < last_search_end                           # reading began before discovery finished


def test_never_two_simultaneous_reads_on_one_host(monkeypatch):
    leads, pages = [], {}
    for n in range(10):
        url = f"https://same.example/2026/05/acme-corp-quarterly-earnings-report-{n}"
        leads.append({"url": url, "title": f"Acme Corp quarterly earnings report {n}"})
        pages[url] = {"latency": 0.05, "ok": True}
    world = FakeWorld(leads, pages, per_query=5)
    run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "4"})
    assert world.max_host <= 1                                          # profile.host_concurrency honoured


# ── Selection: article URLs before hubs and wrappers; no snippet becomes an article ───────────

def test_article_urls_are_read_before_hubs_and_wrappers(monkeypatch):
    leads, pages = [], {}
    hub = {"url": "https://hub.example/tag/acme-corp", "title": "Acme Corp tag archive"}
    wrapper = {"url": "https://news.google.com/rss/articles/CBMiAcmeOpaque", "title": "Acme Corp earnings - Some Outlet"}
    leads += [hub, wrapper]
    pages[hub["url"]] = {"latency": 0.02, "ok": True, "article": False}
    for n in range(6):
        lead, page = article(n)
        leads.append(lead); pages[lead["url"]] = page
    world = FakeWorld(leads, pages, per_query=10)
    run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "1"})
    order = [u for u, _, _ in sorted(world.reads, key=lambda row: row[1])]
    article_positions = [i for i, u in enumerate(order) if "/2026/05/" in u]
    other_positions = [i for i, u in enumerate(order) if "/2026/05/" not in u]
    assert article_positions and (not other_positions or max(article_positions) < min(other_positions))


def test_a_search_snippet_is_never_an_acquired_article(monkeypatch):
    world = build(articles=30, per_query=3)
    result = run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "2"})
    read_urls = {u for u, _, _ in world.reads}
    unread = [c for c in result.candidates if c.canonical_url not in read_urls]
    assert unread, "the scenario must leave some leads unread"
    for lead in unread:
        assert not lead.metadata.get("read_success") and not lead.content and not lead.acquired_id
        assert lead.metadata.get("raw_source_type") in {"DISCOVERY_LEAD", "FEED_ENTRY"}
    assert all(c.metadata.get("read_success") for c in result.captures)


# ── Budgeted discovery: supply gating, no extra requests, HTTP cap respected ─────────────────

def test_discovery_pauses_when_read_side_supply_is_sufficient(monkeypatch):
    world = build(articles=80, per_query=6, search_latency=0.01)
    result = run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "2"})
    trace = controller_trace(result)
    assert trace["queries_never_dispatched"] > 0                        # unneeded searches were not sent
    assert trace["counters"].get("discovery_holds", 0) > 0
    legacy_world = build(articles=80, per_query=6, search_latency=0.01)
    legacy = run(legacy_world, controller="legacy")
    assert sum(len(ids) for ids, _, _ in world.searches) < sum(len(ids) for ids, _, _ in legacy_world.searches)
    assert legacy.read_telemetry["attempted"] <= 24


def test_discovery_continues_when_supply_is_poor(monkeypatch):
    world = build(articles=2, junks=30, per_query=2)
    result = run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "2"})
    assert controller_trace(result)["queries_dispatched"] >= 6          # the floor of core queries always runs


def test_native_http_admission_cap_is_never_exceeded(monkeypatch):
    budget = PublicRequestBudget(total=30, per_host=24)
    world = build(articles=40, per_query=3, admissions_per_call=2)
    with public_request_budget(budget):
        run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "3"})
    assert budget.snapshot()["native_http_admissions"] <= 30
    assert budget.rejected >= 0


# ── Failure handling, cancellation, honest accounting ────────────────────────────────────────

def test_all_failures_are_recorded_and_the_run_terminates(monkeypatch):
    world = build(articles=0, junks=40, per_query=4)
    result = run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "2"})
    assert result.captures == []
    assert result.metrics["reads_attempted"] >= 1
    assert sum(result.metrics["failure_categories"].values()) >= 1
    assert controller_trace(result)["stop_reason"] is not None


def test_deadline_cancels_pending_work_without_late_merges(monkeypatch):
    world = build(articles=30, latencies=[0.5] * 30, per_query=4, search_latency=0.05)
    started = time.monotonic()
    result = run(world, monkeypatch=monkeypatch, env={"AEGIS_PIPELINE_READ_WORKERS": "2"}, deadline_seconds=2.0)
    assert time.monotonic() - started < 6.0
    assert result.metrics["deadline_exhausted"] or controller_trace(result)["stop_reason"]
    count = len(result.captures)
    time.sleep(0.7)                                                     # late workers must not append afterwards
    assert len(result.captures) == count


def test_legacy_and_interleaved_controllers_are_unchanged(monkeypatch):
    for controller in ("legacy", "interleaved_v1"):
        result = run(build(articles=14, per_query=3), controller=controller)
        assert result.metrics["article_bodies"] > 0
        assert ("acquisition_controller" in result.metrics) == (controller == "interleaved_v1")
    with pytest.raises(ValueError):
        run(build(articles=2), controller="nonsense")


def test_worker_settings_are_bounded(monkeypatch):
    from backend.services.research.pipelined_acquisition import PipelineConfig
    from backend.services.research.research_profiles import get_research_profile
    config = PipelineConfig(get_research_profile("DEEP"), {"AEGIS_PIPELINE_READ_WORKERS": "99", "AEGIS_PIPELINE_DISCOVERY_WORKERS": "99",
                                                            "AEGIS_PIPELINE_SELECTOR": "bogus"})
    assert (config.read_workers, config.discovery_workers, config.selector) == (4, 2, "ranked_v2")
    low = PipelineConfig(get_research_profile("DEEP"), {"AEGIS_PIPELINE_READ_WORKERS": "-5", "AEGIS_PIPELINE_DISCOVERY_WORKERS": "x"})
    assert (low.read_workers, low.discovery_workers) == (1, 1)


# ── Ranker properties ────────────────────────────────────────────────────────────────────────

def item(url, title, **meta):
    return EvidenceItem(id="x_" + url[-8:], canonical_url=url, title=title, snippet=title, metadata=dict(meta))


def test_article_shape_and_index_detection():
    assert article_shaped("https://a.example/recovery-process-enters-commercial-production/")
    assert article_shaped("https://a.example/2026/05/acme-corp-reports-record-earnings")
    assert article_shaped("https://a.example/news/acme-corp-reports-record-quarterly-earnings.html")
    assert not article_shaped("https://a.example/tag/acme")
    assert not article_shaped("https://a.example/")
    assert is_index_like("https://a.example/category/finance") and is_index_like("https://a.example/")


def test_exact_title_match_outranks_a_generic_lead():
    ctx = SelectionContext("Acme Corp", "financial")
    strong = item("https://a.example/2026/05/acme-corp-quarterly-earnings-report", "Acme Corp quarterly earnings report")
    weak = item("https://b.example/2026/05/regional-markets-weekly-roundup-update", "Regional markets weekly roundup")
    s_strong, parts = score_candidate(strong, ctx, is_wrapper=False, is_index=False)
    s_weak, _ = score_candidate(weak, ctx, is_wrapper=False, is_index=False)
    assert s_strong > s_weak + 3 and "target_in_title" in parts and "article_url" in parts


def test_wrapper_and_hub_are_penalized_but_never_excluded():
    ctx = SelectionContext("Acme Corp", "financial")
    wrapper = item("https://news.google.com/rss/articles/CBMabc", "Acme Corp earnings - Outlet")
    hub = item("https://a.example/tag/acme", "Acme Corp archive")
    for lead, flags in ((wrapper, {"is_wrapper": True, "is_index": False}), (hub, {"is_wrapper": False, "is_index": True})):
        score, parts = score_candidate(lead, ctx, **flags)
        assert any(v < 0 for v in parts.values()) and score > -10          # a soft penalty, not a ban


def test_repeated_zero_yield_is_a_bounded_recoverable_penalty_not_a_ban():
    memory = YieldMemory()
    ctx = SelectionContext("Acme Corp", "financial", memory)
    strong = item("https://spammy.example/2026/05/acme-corp-quarterly-earnings-report", "Acme Corp quarterly earnings report")
    fresh = score_candidate(strong, ctx, is_wrapper=False, is_index=False)[0]
    for _ in range(6):
        memory.record("spammy.example", False)
    penalized, parts = score_candidate(strong, ctx, is_wrapper=False, is_index=False)
    assert penalized < fresh and fresh - penalized <= 2.0 + 0.5 + 1e-9        # streak penalty is capped at 2.0 (+/-0.5 history)
    weak_elsewhere = item("https://other.example/news/market-wrap", "Markets wrap")
    assert penalized > score_candidate(weak_elsewhere, ctx, is_wrapper=False, is_index=False)[0]
    memory.record("spammy.example", True)                                    # one usable read clears the streak
    assert memory.streak_penalty("spammy.example") == 0.0


def test_trending_publication_window_moves_stale_leads_down_and_fresh_up():
    ctx = SelectionContext("battery recycling", "trending")
    base = "https://a.example/2026/10/battery-recycling-plant-opens-in-texas"
    scores = {p: score_candidate(item(base, "Battery recycling plant opens in Texas", harvest_temporal_priority=p), ctx,
                                 is_wrapper=False, is_index=False)[0] for p in (0, 1, 2, 3)}
    assert scores[0] > scores[1] > scores[2] > scores[3]


def test_helpers_agree_with_the_engines_own_predicates():
    assert _is_wrapper(item("https://news.google.com/rss/articles/X", "t"))
    assert _is_index(item("https://a.example/tag/acme", "t")) and not _is_index(item("https://a.example/2026/05/a-long-article-slug-here", "t"))


def test_slow_processing_cannot_mutate_returned_candidates(monkeypatch):
    """Real reader processing continues after closure, but owns only private copies."""
    import copy
    import importlib
    from backend.services.research.pipelined_acquisition import PipelinedAcquisition
    module = importlib.import_module("backend.services.research.deep_reader")
    original = module._challenge_body
    entered, release, done = threading.Event(), threading.Event(), threading.Event()
    finished = []
    worker = PipelinedAcquisition._read_worker

    def slow_processing(body):
        if threading.current_thread().name.startswith("pipeline-read"):
            entered.set()
            assert release.wait(4)
        return original(body)

    def tracked_worker(self, *args):
        try:
            return worker(self, *args)
        finally:
            finished.append(True)
            if len(finished) >= 2:
                done.set()

    monkeypatch.setattr(module, "_challenge_body", slow_processing)
    monkeypatch.setattr(PipelinedAcquisition, "_read_worker", tracked_worker)
    try:
        result = run(build(articles=6), deadline_seconds=0.6)
        assert entered.is_set()
        before = copy.deepcopy([c.__dict__ for c in result.candidates])
        attempts_before = copy.deepcopy(result.read_telemetry)
    finally:
        release.set()
    assert done.wait(4)
    assert [c.__dict__ for c in result.candidates] == before
    assert result.read_telemetry == attempts_before
    assert result.captures == []
    attempts = result.read_telemetry["acquisition_attempts"]
    assert len(attempts) == result.read_telemetry["attempted"] == 2
    assert all(a["status"] == "INTERRUPTED" and a["worker_started"] for a in attempts)
    assert all(a["provider_started"] is None and a["http_status"] is None for a in attempts)


def test_completed_read_keeps_reserved_identity_and_one_record():
    result = run(build(articles=8))
    attempts = result.read_telemetry["acquisition_attempts"]
    ids = {a["attempt_id"] for a in attempts}
    assert len(ids) == len(attempts) == result.read_telemetry["attempted"]
    assert all(c.acquisition_attempt_id in ids for c in result.captures)
    assert all(a["status"] != "SUBMITTED" for a in attempts)
    assert sum(a["status"] == "SUCCESS" for a in attempts) == result.read_telemetry["successful"]


def test_worker_exception_finalizes_reserved_attempt(monkeypatch):
    from backend.services.research.deep_reader import DeepReader

    def fail(*args, **kwargs):
        raise ValueError("synthetic processing failure")

    monkeypatch.setattr(DeepReader, "deep_read", fail)
    result = run(build(articles=6))
    attempts = result.read_telemetry["acquisition_attempts"]
    assert len(attempts) == result.read_telemetry["attempted"] > 0
    assert result.read_telemetry["failed"] == len(attempts)
    assert all(a["failure_kind"] == "READ_WORKER_ERROR" for a in attempts)


def test_pipeline_invokes_optional_advice_once_on_weak_yield(monkeypatch):
    from backend.services.research import search_advice
    calls = []

    def advice(request, candidates, service, timeout, *, capture_feedback):
        calls.append((timeout, capture_feedback))
        return None, {"status": "MOCKED_UNAVAILABLE", "advisory_only": True}

    monkeypatch.setenv("AEGIS_SEARCH_ADVISOR_ENABLED", "true")
    monkeypatch.setattr(search_advice, "expand_with_advice", advice)
    result = HarvestingEngine(build(articles=0, junks=12)).run(
        target="Acme Corp", domain="financial", profile="DEEP", controller="pipelined_v1",
        request=SimpleNamespace(target="Acme Corp"), deadline=time.monotonic() + 20)
    assert len(calls) == 1
    assert result.metrics["ai_search_advice"]["status"] == "MOCKED_UNAVAILABLE"
    assert calls[0][0] > 0


def test_pipeline_advice_never_spends_after_read_slots_exhausted(monkeypatch):
    from backend.services.research import search_advice
    from backend.services.research.research_profiles import get_research_profile
    calls = []
    monkeypatch.setenv("AEGIS_SEARCH_ADVISOR_ENABLED", "true")
    monkeypatch.setattr(search_advice, "expand_with_advice", lambda *a, **k: calls.append(True))
    result = HarvestingEngine(build(articles=6)).run(target="Acme Corp", domain="financial",
        profile=get_research_profile("DEEP", max_reads=1), controller="pipelined_v1",
        request=SimpleNamespace(target="Acme Corp"))
    assert calls == []
    assert result.read_telemetry["attempted"] == 1


def test_suggested_search_lead_reaches_native_reading_within_query_cap(monkeypatch):
    """Synthetic suggestion transport: no model call or live acquisition."""
    from backend.services.research import search_advice
    lead, page = article(99, host="advised.example")
    world = build(articles=0, junks=40, per_query=2)
    world.pages[lead["url"]] = page
    calls = []

    def advice(*args, **kwargs):
        calls.append(True)
        return RetrievalResult(query="Acme Corp", domain="financial", fragments=[EvidenceFragment(
            platform="web", title=lead["title"], url=lead["url"], snippet=lead["title"],
            evidence_id="up_advised", query_id="ai_search_1", channel_name="web",
            content_depth="FEED_ENTRY_SUMMARY")], query_records=[QueryExecutionRecord(
                query_id="ai_search_1", query_text="Acme Corp quarterly earnings", channel="web", status="SUCCESS")]), {
                    "status": "SUGGESTED", "advisory_only": True}

    monkeypatch.setenv("AEGIS_SEARCH_ADVISOR_ENABLED", "true")
    monkeypatch.setattr(search_advice, "expand_with_advice", advice)
    result = HarvestingEngine(world).run(target="Acme Corp", domain="financial", profile="DEEP",
        controller="pipelined_v1", request=SimpleNamespace(target="Acme Corp"))
    assert len(calls) == 1
    assert any(c.canonical_url == lead["url"] and c.content for c in result.captures)
    trace = controller_trace(result)
    assert trace["queries_dispatched"] + trace["advisory_queries_submitted"] <= 18
    assert result.read_telemetry["attempted"] <= 24


def test_queued_read_cancellation_is_not_reported_as_provider_failure(monkeypatch):
    from concurrent.futures import Future, ThreadPoolExecutor
    from backend.services.research import pipelined_acquisition

    class DeferredReads:
        def submit(self, *args, **kwargs):
            return Future()  # deliberately never starts a worker

        def shutdown(self, **kwargs):
            pass

    def pool(*args, **kwargs):
        return DeferredReads() if kwargs.get("thread_name_prefix") == "pipeline-read" else ThreadPoolExecutor(*args, **kwargs)

    monkeypatch.setattr(pipelined_acquisition, "ThreadPoolExecutor", pool)
    result = run(build(articles=6), deadline_seconds=0.5)
    attempts = result.read_telemetry["acquisition_attempts"]
    assert len(attempts) == result.read_telemetry["attempted"] == 2
    assert all(a["status"] == "CANCELLED_BEFORE_START" and a["provider_started"] is False for a in attempts)
    assert all(a["worker_started"] is False and a["http_status"] is None for a in attempts)
    assert result.read_telemetry["failed"] == 0


def test_zero_yield_discovery_does_not_stop_an_observed_article_opportunity():
    world = build(articles=0, junks=10, per_query=5)
    url = "https://publisher.example/recovery-process-enters-commercial-production/"
    world.pages[url] = {"latency": 0.01, "ok": True}
    lead = EvidenceItem(id="observed_child", canonical_url=url, title="",
        metadata={"observed_parent_id": "saved_parent"})
    result = HarvestingEngine(world).run(target="Acme Corp", domain="financial", profile="DEEP",
        initial_candidates=[lead], controller="pipelined_v1")
    assert any(c.canonical_url == url and c.content for c in result.captures)
    assert result.read_telemetry["attempted"] <= 24


def test_worker_merge_preserves_discovery_alias_arriving_during_read():
    first, page = article(1, latency=0.4)
    other, other_page = article(2, latency=0.01)
    world = FakeWorld([first, other, first], {first["url"]: page, other["url"]: other_page},
        per_query=1, search_latency=0.08)
    result = run(world)
    captured = next(c for c in result.captures if c.canonical_url == first["url"])
    assert "hv_q_003" in captured.metadata.get("discovery_query_aliases", [])
