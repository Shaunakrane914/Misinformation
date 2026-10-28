"""Experimental feature-flagged pipelined acquisition (``AEGIS_ACQUISITION_CONTROLLER=pipelined_v1``).

The legacy controller discovers in blocking waves, then reads in blocking rounds of at most
``profile.concurrency`` candidates: each round waits for its slowest read. This scheduler runs one
coordinator loop that keeps small, bounded pools of discovery and read workers busy, and decides
from live evidence what to do next:

* small bounded discovery tasks, dispatched only while read-side supply needs them;
* candidate ranking with the explainable score in ``candidate_selection``;
* one candidate per read worker, released as soon as a worker is free (no round barrier);
* immediate deterministic capture feedback (routing only, never final qualification);
* budget reallocation (adaptive discovery credit) and cancellation at caps/deadlines.

It retains every existing control: the same ``_BudgetedService`` (operation and per-host read caps,
host spacing, deadlines), the same ``PublicRequestBudget`` admissions, SSRF and redirect rules in the
reader, source provenance, and the later unchanged Layer 2 qualification. It adds no request class
and never treats a search snippet as an acquired article: only the reader sets captured content.
Concurrency is conservative by default and capped by the profile; more workers are a measurement,
not an assumption.
"""
import logging
import copy
import os
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextvars import copy_context

from backend.services.research.candidate_selection import (
    READ_FLOOR, SelectionContext, YieldMemory, article_shaped, group_of_url, score_candidate,
)
from backend.services.research.publisher_read_policy import PublisherReadPolicy, discovery_kind

logger = logging.getLogger(__name__)
GOOD_LEAD = 4.0        # score at/above which a lead is a strong candidate (observed ~48% hit rate)
FUTILITY_WINDOW = 8
FUTILITY_MIN_READS = 10


class PipelineConfig:
    """Conservative defaults; every value is bounded and logged in the trace."""

    def __init__(self, profile, environ=None):
        env = os.environ if environ is None else environ

        def bounded(name, default, low, high):
            try:
                value = int(env.get(name, default))
            except (TypeError, ValueError):
                value = default
            return max(low, min(high, value))

        self.read_workers = bounded("AEGIS_PIPELINE_READ_WORKERS", 2, 1, max(1, min(4, profile.concurrency)))
        self.discovery_workers = bounded("AEGIS_PIPELINE_DISCOVERY_WORKERS", 1, 1, 2)
        self.queries_per_task = bounded("AEGIS_PIPELINE_QUERIES_PER_TASK", 2, 1, 3)
        self.min_queries = bounded("AEGIS_PIPELINE_MIN_QUERIES", 6, 1, 18)
        self.selector = env.get("AEGIS_PIPELINE_SELECTOR", "ranked_v2")
        if self.selector not in {"ranked_v2", "legacy_priority"}:
            self.selector = "ranked_v2"
        self.futility = str(env.get("AEGIS_PIPELINE_FUTILITY", "on")).lower() not in {"off", "0", "false"}
        self.supply_factor = 1.5
        self.tick_seconds = 0.05

    def to_dict(self):
        return {key: getattr(self, key) for key in ("read_workers", "discovery_workers", "queries_per_task",
                "min_queries", "selector", "futility", "supply_factor", "tick_seconds")}


class PipelinedAcquisition:
    def __init__(self, *, target, domain, intent, agent_name, profile, queries, known, attempted, captured,
                 telemetry, output, service, reader, add, emit, observed_children, discarded, reference_time,
                 discovery_capacity, discovery_deadline, reading_deadline, read_host_counts,
                 read_publisher_counts, submitted_query_ids, environ=None, request=None, refine_topics=None):
        self.target, self.domain, self.intent, self.agent_name = target, domain, intent, agent_name
        self.profile, self.queries, self.known, self.attempted, self.captured = profile, queries, known, attempted, captured
        self.telemetry, self.output, self.service, self.reader = telemetry, output, service, reader
        self.add, self.emit, self.observed_children, self.discarded = add, emit, observed_children, discarded
        self.reference_time = reference_time
        self.discovery_capacity = discovery_capacity
        self.discovery_deadline, self.reading_deadline = discovery_deadline, reading_deadline
        self.read_host_counts, self.read_publisher_counts = read_host_counts, read_publisher_counts
        self.submitted_query_ids = submitted_query_ids
        self.request = request
        self.refine_topics = refine_topics
        self.cfg = PipelineConfig(profile, environ)
        self.memory = YieldMemory()
        self.group_reads = Counter()
        self.inflight_search = {}      # future -> list of query rows
        self.inflight_read = {}        # future -> (item, started)
        self.inflight_hosts = Counter()
        self.reads_started = 0
        self.reads_completed = 0
        self.wrapper_count = 0
        self.index_count = 0
        self.raw_chars = 0
        self.next_query = 0
        self.order = self._order_queries()
        self.events, self.event_count = [], 0
        self.recent_usable = []
        self.stop_reason = None
        self.stats = Counter()
        self.busy_read_seconds = 0.0
        self.max_inflight_reads = 0
        self.max_inflight_searches = 0
        self.score_audit = []
        self.feedback = []
        self.seen_bodies = set()
        self._static = {}
        self._started = time.monotonic()
        self._lock = threading.Lock()
        self.read_lifecycle = {}
        self.advice_checked = False
        self.inflight_advice = None
        self.advice_trace = {"status": "DISABLED", "advisory_only": True}
        self.advice_queries = 0
        self.allocation = PublisherReadPolicy(profile.max_host_reads)

    # ── bookkeeping ───────────────────────────────────────────────────────────
    def record(self, action, **details):
        self.event_count += 1
        if len(self.events) < 200:
            self.events.append({"sequence": self.event_count, "t": round(time.monotonic() - self._started, 3),
                                "action": action, **details})

    def _order_queries(self):
        """Two core queries first, planned specialist actions next, remaining core queries last."""
        core = [row for row in self.queries if not row.get("source_plan_action_id")]
        planned = [row for row in self.queries if row.get("source_plan_action_id")]
        return core[:2] + planned + core[2:]

    # ── helpers shared with the legacy engine ────────────────────────────────
    def _h(self):
        from backend.services.research import harvesting
        return harvesting

    def _score(self, item):
        """Static components are computed once per lead; diversity/history are cheap and live."""
        h = self._h()
        ctx = SelectionContext(self.target, self.domain, self.memory, self.group_reads)
        return score_candidate(item, ctx, is_wrapper=h._is_wrapper(item), is_index=h._is_index(item))

    def _pending(self):
        return [item for key, item in self.known.items()
                if key not in self.attempted and item.metadata.get("harvest_acquisition_eligible")
                and self._h()._source_body_admissible(item)]

    def _remaining_read_slots(self):
        return max(0, self.profile.max_reads - self.reads_started)

    def _good_leads(self, pending):
        """Strong leads that the host/wrapper/hub caps would still let us read."""
        h = self._h()
        count = 0
        for item in pending:
            if h._is_wrapper(item) or h._is_index(item) or not self._within_caps(item):
                continue
            if self.domain == "trending" and item.metadata.get("harvest_temporal_priority", 1) not in {0, 1}:
                continue
            if self._score(item)[0] >= GOOD_LEAD:
                count += 1
        return count

    # ── discovery ────────────────────────────────────────────────────────────
    def _discovery_gate(self, pending):
        """Return None to dispatch the next queries, or a (kind, reason) hold/stop."""
        from backend.infrastructure.acquisition.network.budget import discovery_http_remaining, release_adaptive_discovery
        if self.next_query >= self._query_limit():
            return ("STOP", "ALL_PLANNED_QUERIES_DISPATCHED")
        if time.monotonic() >= self.discovery_deadline:
            return ("STOP", "DISCOVERY_DEADLINE_EXHAUSTED")
        if len(self.known) >= self.discovery_capacity:
            return ("STOP", "DISCOVERY_CANDIDATE_CAP_REACHED")
        if self._remaining_read_slots() == 0:
            return ("STOP", "SHARED_READ_ATTEMPT_CAP")
        if discovery_http_remaining() == 0:
            supply = self._good_leads(pending)
            if self.next_query > 0 and supply < self.cfg.supply_factor * max(1, self._remaining_read_slots()):
                granted = release_adaptive_discovery()
                self.record("RELEASE_ADAPTIVE_DISCOVERY", admissions_granted=granted, good_leads=supply,
                            read_slots_left=self._remaining_read_slots())
            if discovery_http_remaining() == 0:
                return ("STOP", "DISCOVERY_HTTP_RESERVE_FOR_READING")
        upcoming = self.order[self.next_query]
        if self.next_query >= self.cfg.min_queries and not upcoming.get("source_plan_action_id"):
            supply = self._good_leads(pending)
            if supply >= self.cfg.supply_factor * max(1, self._remaining_read_slots()):
                return ("HOLD", "READ_SIDE_SUPPLY_SUFFICIENT")
        return None

    def _query_limit(self):
        # A weak lead may require reading before advice can run. Preserve one
        # query slot instead of exhausting all planned queries while it waits.
        reserve = int(self.request is not None and not self.advice_checked
                      and os.getenv("AEGIS_SEARCH_ADVISOR_ENABLED", "false").lower() in {"1", "true"})
        return min(len(self.order), self.profile.max_queries - self.advice_queries - reserve)

    def _dispatch_discovery(self, pool):
        dispatched = False
        if self.inflight_advice is not None:
            return False
        while len(self.inflight_search) < self.cfg.discovery_workers:
            pending = self._pending()
            gate = self._discovery_gate(pending)
            if gate is not None:
                kind, reason = gate
                if kind == "HOLD":
                    self.stats["discovery_holds"] += 1
                elif reason not in (self.output.retrieval_trace.get("discovery_stop_reason"),):
                    self.output.retrieval_trace.setdefault("discovery_stop_reason", reason)
                    self.record("DISCOVERY_STOP", reason=reason)
                break
            rows = self.order[self.next_query:min(self.next_query + self.cfg.queries_per_task,
                                                self._query_limit())]
            self.next_query += len(rows)
            plan = {}
            for row in rows:
                plan.setdefault(row["channel"], []).append({k: v for k, v in row.items() if k != "channel"})
            self.submitted_query_ids.update(row["query_id"] for row in rows)
            context = copy_context()
            future = pool.submit(context.run, self._search_worker, plan, rows)
            self.inflight_search[future] = rows
            self.max_inflight_searches = max(self.max_inflight_searches, len(self.inflight_search))
            self.record("DISPATCH_SEARCH", query_ids=[row["query_id"] for row in rows], candidates_known=len(self.known))
            dispatched = True
        return dispatched

    def _search_worker(self, plan, rows):
        from backend.infrastructure.acquisition.network.budget import public_request_phase
        timeout = min(20.0, max(0.5, self.discovery_deadline - time.monotonic()))
        profile = self.profile
        with public_request_phase("discovery"):
            return self.service.retrieve_many(
                plan, domain=self.domain, agent_name=self.agent_name, target_name=self.target, timeout=timeout,
                budget={"max_queries_per_channel": max(len(r) for r in plan.values()),
                        "max_results_per_query": profile.results_per_query,
                        "max_total_evidence": min(profile.max_candidates, 6 * profile.results_per_query),
                        "max_deep_reads": 0, "channel_timeout": min(15.0, timeout)})

    def _complete_search(self, future, rows):
        import hashlib
        from backend.services.agent_reach.channels import QueryExecutionRecord
        from backend.services.research.research_models import EvidenceItem
        from backend.services.research.source_identity import source_url_key
        try:
            result = future.result()
            self.output.query_records.extend(result.query_records)
            self.output.channel_health.update(result.channel_health)
            self.output.retrieval_trace.setdefault("discovery_waves", []).append(result.retrieval_trace or {})
            for fragment in result.fragments:
                url = getattr(fragment, "url", "") or ""
                item_id = getattr(fragment, "evidence_id", "") or "ev_" + hashlib.sha256(source_url_key(url).encode()).hexdigest()[:16]
                self.add(EvidenceItem.from_evidence_fragment(fragment, item_id=item_id, target_name=self.target))
        except Exception as exc:
            self.discarded["SEARCH_" + type(exc).__name__.upper()] += 1
            for row in rows:
                self.output.query_records.append(QueryExecutionRecord(
                    query_id=row["query_id"], channel=row["channel"], query_text=row["query_text"],
                    query_class=row.get("query_class", "general"),
                    status="TIMEOUT" if isinstance(exc, TimeoutError) else "FAILED",
                    error="Harvester transport exception: " + type(exc).__name__,
                    result_count_raw=0, result_count_normalized=0))
        if self.refine_topics is not None:
            self.refine_topics()
        self.emit("HARVEST_DISCOVERY")

    # ── reading ──────────────────────────────────────────────────────────────
    def _within_caps(self, item):
        h = self._h()
        host = h._host(item.canonical_url)
        if self.read_host_counts[host] >= self.profile.max_host_reads:
            return False
        if h._is_wrapper(item) and self.wrapper_count >= self.profile.max_wrapper_reads:
            return False
        if h._is_index(item) and self.index_count >= self.profile.max_discovery_reads:
            return False
        return True

    def _selectable(self, item):
        """Caps plus the transient rule that a host with a read in flight waits its turn."""
        host = self._h()._host(item.canonical_url)
        if not self._within_caps(item) or self.inflight_hosts[host] >= self.profile.host_concurrency:
            return False
        kind = discovery_kind(item, self._h()._is_index(item))
        has_articles = any(self._h()._host(lead.canonical_url) == host and self._within_caps(lead)
            and discovery_kind(lead, self._h()._is_index(lead)) == "ARTICLE" for lead in self._pending())
        reason = self.allocation.reason(host, kind, has_articles, bool(self.inflight_hosts[host]))
        if reason:
            item.metadata["adaptive_read_deferral"] = reason
        else:
            item.metadata.pop("adaptive_read_deferral", None)
        return reason is None

    def _ranked(self, pending):
        h = self._h()
        if self.cfg.selector == "legacy_priority":
            ordered = sorted(pending, key=lambda i: h._read_priority(i, self.target, self.domain,
                                                                    self.read_host_counts, self.read_publisher_counts))
            return [(item, None, None) for item in ordered]
        scored = [(item, *self._score(item)) for item in pending]
        def priority(row):
            lead = row[0]
            host = h._host(lead.canonical_url)
            kind = discovery_kind(lead, h._is_index(lead))
            return (self.allocation.priority(host, kind, lead.metadata.get("harvest_temporal_priority")),
                    {"MAIN_FEED": 0, "SEARCH": 1, "SITEMAP": 2}.get(kind, 3), -row[1], lead.id)
        scored.sort(key=priority)
        return scored

    def _discovery_can_still_help(self):
        """True only while a search is actually running. A held or stopped gate cannot deliver
        candidates, so waiting on it would idle until the deadline."""
        return bool(self.inflight_search) or self.inflight_advice is not None

    def _next_read(self):
        pending = self._pending()
        ranked = self._ranked(pending)
        best_any = ranked[0][1] if ranked and ranked[0][1] is not None else None
        # Empty wrappers/indexes cannot prove that newly observed article links
        # are futile. Retain an actual read opportunity under the original caps.
        untested_articles = any(
            self._within_caps(lead) and not self._h()._is_wrapper(lead) and not self._h()._is_index(lead)
            and article_shaped(lead.canonical_url)
            and (self.domain != "trending" or lead.metadata.get("harvest_temporal_priority", 1) <= 1)
            for lead in pending)
        for item, score, components in ranked:
            if not self._selectable(item):
                continue
            if score is not None and score < READ_FLOOR and self._discovery_can_still_help():
                self.stats["reads_held_for_better_supply"] += 1
                return None, None, None
            if (score is not None and self.cfg.futility and self.reads_completed >= FUTILITY_MIN_READS
                    and len(self.recent_usable) >= FUTILITY_WINDOW and not any(self.recent_usable[-FUTILITY_WINDOW:])
                    and score < GOOD_LEAD and not self._discovery_can_still_help() and not untested_articles):
                self.stop_reason = self.stop_reason or "FUTILITY_STOP"
                self.record("FUTILITY_STOP", recent_zero_usable_reads=FUTILITY_WINDOW, next_best_score=score)
                return None, None, None
            return item, score, components
        return None, best_any, None

    def _dispatch_reads(self, pool):
        h = self._h()
        dispatched = False
        while (len(self.inflight_read) < self.cfg.read_workers and self.reads_started < self.profile.max_reads
               and time.monotonic() < self.reading_deadline and self.raw_chars < self.profile.max_capture_chars
               and not self.stop_reason):
            if self.inflight_advice is not None and self._remaining_read_slots() <= 1:
                break  # one remaining opportunity for the bounded suggested search
            item, score, components = self._next_read()
            if item is None:
                if not self.inflight_read and not self._discovery_can_still_help():
                    self.stats["idle_no_selectable_candidate"] += 1
                break
            key = h.source_url_key(item.canonical_url)
            self.attempted.add(key)
            host = h._host(item.canonical_url)
            self.read_host_counts[host] += 1
            self.read_publisher_counts[h._observed_publisher(item)] += 1
            self.inflight_hosts[host] += 1
            self.wrapper_count += int(h._is_wrapper(item))
            self.index_count += int(h._is_index(item))
            self.group_reads[group_of_url(item.canonical_url)] += 1
            self.reads_started += 1
            self.allocation.submit(host, discovery_kind(item, h._is_index(item)))
            item.metadata["pipeline_selection"] = {"selector": self.cfg.selector, "score": score,
                                                   "components": components, "read_ordinal": self.reads_started}
            if len(self.score_audit) < 60:
                self.score_audit.append({"candidate_id": item.id, "url": h._locator(item.canonical_url), "score": score,
                                         "components": components, "ordinal": self.reads_started})
            started = time.monotonic()
            attempt_id = "acq_att_" + uuid.uuid4().hex[:12]
            worker_started = threading.Event()
            attempt = {"attempt_id": attempt_id, "candidate_id": item.id,
                       "url": item.canonical_url, "channel": item.channel,
                       "status": "SUBMITTED", "worker_started": False,
                       "provider_started": None, "failure_kind": None, "http_status": None}
            self.telemetry["attempted"] += 1
            self.telemetry["acquisition_attempts"].append(attempt)
            # DeepReader mutates its input. Workers must never own objects
            # reachable from a returned investigation, even after cancellation.
            future = pool.submit(copy_context().run, self._read_worker,
                                 copy.deepcopy(item), attempt_id, worker_started)
            self.inflight_read[future] = (item, started)
            self.read_lifecycle[future] = (attempt, worker_started)
            self.max_inflight_reads = max(self.max_inflight_reads, len(self.inflight_read))
            self.record("DISPATCH_READ", candidate_id=item.id, score=score, in_flight=len(self.inflight_read),
                        read_ordinal=self.reads_started)
            dispatched = True
        return dispatched

    def _read_worker(self, item, attempt_id, worker_started):
        from backend.services.research.adaptive_acquisition import inspect_capture
        worker_started.set()
        window = min(self.profile.read_window_seconds, max(0.0, self.reading_deadline - time.monotonic()))
        captures, observed = self.reader.deep_read([item], max_reads=1, timeout_per_read=window,
                                                   service=self.service, max_concurrency=1,
                                                   attempt_ids={item.id: attempt_id})
        feedback = None
        if captures:
            try:
                feedback = inspect_capture(captures[0], self.target, self.domain, self.intent, self.reference_time)
            except Exception as error:      # routing feedback must never lose a capture
                feedback = {"source_id": captures[0].id, "usable_passage": False,
                            "reason": "FEEDBACK_ERROR_" + type(error).__name__, "scope": "ROUTING_FEEDBACK_UNKNOWN"}
        return item, captures, observed, feedback

    def _complete_read(self, future, item, started):
        from backend.services.research.publisher_links import failed_feed_publisher_hubs
        h = self._h()
        host = h._host(item.canonical_url)
        self.inflight_hosts[host] = max(0, self.inflight_hosts[host] - 1)
        self.busy_read_seconds += time.monotonic() - started
        self.reads_completed += 1
        attempt, worker_started = self.read_lifecycle.pop(future)
        attempt["worker_started"] = worker_started.is_set()
        try:
            worker_item, captures, observed, feedback = future.result()
        except Exception as error:
            attempt.update(status="FAILED", failure_kind="READ_WORKER_ERROR",
                           error_type=type(error).__name__)
            self.telemetry["failed"] += 1
            self.discarded["READ_WORKER_" + type(error).__name__.upper()] += 1
            self.memory.record(group_of_url(item.canonical_url), False)
            self.recent_usable.append(False)
            return
        # Merge only on this coordinator, while the investigation is open.
        # Preserve any task lineage discovered while this read was running.
        self._h()._merge_task_lineage(worker_item.metadata, item.metadata)
        for name in ("discovery_query_aliases", "upstream_evidence_ids", "upstream_discovered_ids", "temporal_routing_aliases"):
            observations = list(worker_item.metadata.get(name) or [])
            for value in item.metadata.get(name) or []:
                if value not in observations:
                    observations.append(copy.deepcopy(value))
            if observations:
                worker_item.metadata[name] = observations[-32:]
        item.__dict__.update(worker_item.__dict__)
        records = observed.get("acquisition_attempts", [])
        if records:
            attempt.update(records[0])
        else:
            attempt.update(status="SKIPPED", failure_kind="READER_NOT_SELECTED", provider_started=False)
        attempt["worker_started"] = worker_started.is_set()
        for name in ("successful", "failed", "cached", "total_chars_read"):
            self.telemetry[name] += observed.get(name, 0)
        for name in ("read_urls", "candidate_selection_audit"):
            self.telemetry[name].extend(observed.get(name, []))
        usable = False
        for captured_item in captures:
            key = h.source_url_key(captured_item.canonical_url)
            if key in self.captured:
                continue
            if self.raw_chars + len(captured_item.content) > self.profile.max_capture_chars:
                self.discarded["RAW_CAPTURE_STORAGE_CAP"] += 1
                continue
            self.captured.add(key)
            self.raw_chars += len(captured_item.content)
            captured_item.metadata["raw_source_type"] = h.raw_source_type(captured_item)
            captured_item.metadata["qualification_status"] = "PENDING"
            self.output.captures.append(captured_item)
            if feedback is not None:
                duplicate = feedback.get("body_sha256") in self.seen_bodies
                if feedback.get("body_sha256"):
                    self.seen_bodies.add(feedback["body_sha256"])
                usable = bool(feedback.get("usable_passage")) and not duplicate
                self.feedback.append({**feedback, "duplicate_body_observation": duplicate})
            for child in self.observed_children(captured_item, self.target, self.domain, self.output.rejected):
                self.add(child)
        # A failed or empty read is an honest zero-yield observation for that publisher group.
        actual_article = feedback and feedback.get("source_type") in {"ARTICLE_BODY", "OFFICIAL_DOCUMENT"}
        if actual_article:
            self.memory.record(group_of_url(item.canonical_url), usable)
            self.recent_usable.append(usable)
        self.allocation.observe(host, feedback)
        for hub in failed_feed_publisher_hubs([item], observed.get("acquisition_attempts", []),
                                              {i.canonical_url for i in self.known.values()}):
            self.add(hub)
        self.emit("HARVEST_READING")

    def _dispatch_advice(self, pool):
        """One optional suggestion after weak captured yield, within existing caps."""
        from backend.infrastructure.acquisition.network.budget import discovery_http_remaining, release_adaptive_discovery
        if (self.advice_checked or self.request is None or self.inflight_search
                or self._remaining_read_slots() == 0 or self.stop_reason
                or min(self.discovery_deadline, self.reading_deadline) - time.monotonic() < 3
                or os.getenv("AEGIS_SEARCH_ADVISOR_ENABLED", "false").lower() not in {"1", "true"}
                or self.next_query >= self.profile.max_queries
                or (self.reads_completed < 2 and self.next_query < self._query_limit())):
            return False
        self.advice_checked = True
        if discovery_http_remaining() == 0:
            release_adaptive_discovery()
        if discovery_http_remaining() == 0:
            self.advice_trace = {"status": "SKIPPED_DISCOVERY_BUDGET", "advisory_only": True}
            return False
        self.inflight_advice = pool.submit(copy_context().run, self._advice_worker,
            copy.deepcopy(list(self.known.values())), copy.deepcopy(self.feedback))
        return True

    def _advice_worker(self, candidates, feedback):
        from backend.services.research.search_advice import expand_with_advice
        from backend.infrastructure.acquisition.network.budget import public_request_phase
        with public_request_phase("discovery"):
            return expand_with_advice(self.request, candidates, self.service,
                min(self.discovery_deadline, self.reading_deadline) - time.monotonic(), capture_feedback=feedback)

    def _complete_advice(self, future):
        from concurrent.futures import Future
        try:
            result, self.advice_trace = future.result()
            if result is not None:
                self.advice_queries += len(result.query_records)
                wrapped = Future()
                wrapped.set_result(result)
                self._complete_search(wrapped, [])
        except Exception as error:
            self.advice_trace = {"status": "UNAVAILABLE", "error_type": type(error).__name__, "advisory_only": True}
        self.record("SEARCH_ADVICE", status=self.advice_trace.get("status"))

    # ── loop ─────────────────────────────────────────────────────────────────
    def _fallback_wrapper_hubs(self):
        """Parity with the legacy engine: observed feed hubs when wrapper reads are spent."""
        h = self._h()
        pending = self._pending()
        remaining = self.profile.max_reads - self.reads_started
        remaining_indexes = self.profile.max_discovery_reads - self.index_count
        if self.wrapper_count >= self.profile.max_wrapper_reads and remaining > 1 and remaining_indexes > 0:
            hubs = h._unread_wrapper_hubs(pending, [i.canonical_url for i in self.known.values()],
                                          min(2, remaining_indexes, remaining - 1))
            before = len(self.known)
            for hub in hubs:
                self.add(hub)
            return len(self.known) > before
        return False

    def run(self):
        from backend.infrastructure.acquisition.network.budget import configure_interleaved_discovery
        try:
            allocation = configure_interleaved_discovery()
        except Exception as error:      # budget optional in unit contexts
            allocation = {"unavailable": type(error).__name__}
        self.record("CONFIGURED", config=self.cfg.to_dict(), allocation=allocation)
        reads = ThreadPoolExecutor(max_workers=self.cfg.read_workers, thread_name_prefix="pipeline-read")
        searches = ThreadPoolExecutor(max_workers=self.cfg.discovery_workers, thread_name_prefix="pipeline-search")
        try:
            while True:
                if time.monotonic() >= self.reading_deadline:
                    self.stop_reason = self.stop_reason or "READ_DEADLINE_EXHAUSTED"
                    break
                for future in [f for f in self.inflight_search if f.done()]:
                    rows = self.inflight_search.pop(future)
                    self._complete_search(future, rows)
                for future in [f for f in self.inflight_read if f.done()]:
                    item, started = self.inflight_read.pop(future)
                    self._complete_read(future, item, started)
                if self.inflight_advice is not None and self.inflight_advice.done():
                    future, self.inflight_advice = self.inflight_advice, None
                    self._complete_advice(future)
                if time.monotonic() >= self.reading_deadline:
                    self.stop_reason = self.stop_reason or "READ_DEADLINE_EXHAUSTED"
                    break
                progressed = self._dispatch_advice(searches)
                progressed = self._dispatch_discovery(searches) or progressed
                progressed = self._dispatch_reads(reads) or progressed
                if self.stop_reason == "FUTILITY_STOP" and not self.inflight_read:
                    break
                if (self.reads_started >= self.profile.max_reads or self.raw_chars >= self.profile.max_capture_chars) \
                        and not self.inflight_read:
                    self.stop_reason = self.stop_reason or "SHARED_READ_ATTEMPT_CAP"
                    break
                waiting = list(self.inflight_search) + list(self.inflight_read)
                if self.inflight_advice is not None:
                    waiting.append(self.inflight_advice)
                if not waiting:
                    if progressed:
                        continue
                    if self._fallback_wrapper_hubs():
                        continue
                    if self._discovery_can_still_help():
                        time.sleep(self.cfg.tick_seconds)
                        continue
                    self.stop_reason = self.stop_reason or "NO_FURTHER_USEFUL_WORK"
                    break
                wait(waiting, timeout=self.cfg.tick_seconds, return_when=FIRST_COMPLETED)
        finally:
            cancelled_search = len(self.inflight_search)
            cancelled_read = len(self.inflight_read)
            for future, (attempt, worker_started) in self.read_lifecycle.items():
                cancelled = future.cancel()
                attempt.update(status="CANCELLED_BEFORE_START" if cancelled else "INTERRUPTED",
                    worker_started=worker_started.is_set(), provider_started=False if cancelled else None,
                    failure_kind="CANCELLED_BEFORE_START" if cancelled else "INVESTIGATION_CLOSED",
                    error_message="Investigation closed; no later result will be merged",
                    duration_ms=round((time.monotonic() - self.inflight_read[future][1]) * 1000, 2))
                self.telemetry["cancelled" if cancelled else "interrupted"] = self.telemetry.get(
                    "cancelled" if cancelled else "interrupted", 0) + 1
                item = self.inflight_read[future][0]
                item.read_status = attempt["status"]
                item.metadata["pipeline_attempt_id"] = attempt["attempt_id"]
            self.read_lifecycle.clear()
            if self.inflight_advice is not None:
                self.inflight_advice.cancel()
                self.advice_trace = {"status": "INTERRUPTED", "advisory_only": True}
            # Cancellation: queued work never starts; running calls end at their own bounded deadlines
            # and their late results are never merged into the closed investigation.
            reads.shutdown(wait=False, cancel_futures=True)
            searches.shutdown(wait=False, cancel_futures=True)
            self.stats["cancelled_in_flight_searches"] = cancelled_search
            self.stats["cancelled_in_flight_reads"] = cancelled_read
            self.record("STOP", reason=self.stop_reason or self.output.retrieval_trace.get("discovery_stop_reason"),
                        reads_started=self.reads_started, cancelled_reads=cancelled_read, cancelled_searches=cancelled_search)
        if self.stop_reason:
            self.output.retrieval_trace.setdefault("discovery_stop_reason", self.stop_reason)
        if self.stop_reason in {"FUTILITY_STOP", "NO_FURTHER_USEFUL_WORK"}:
            for item in self._pending():
                item.metadata["adaptive_read_deferral"] = "PIPELINE_" + self.stop_reason

    def snapshot(self):
        wall = max(1e-6, time.monotonic() - self._started)
        return {
            "mode": "pipelined_v1", "experimental": True, "config": self.cfg.to_dict(),
            "stop_reason": self.stop_reason, "wall_seconds": round(wall, 3),
            "reads_started": self.reads_started, "reads_completed": self.reads_completed,
            "queries_dispatched": self.next_query, "queries_planned": len(self.order),
            "advisory_queries_submitted": self.advice_queries,
            "queries_never_dispatched": len(self.order) - self.next_query,
            "max_inflight_reads": self.max_inflight_reads, "max_inflight_searches": self.max_inflight_searches,
            "read_worker_utilization": round(self.busy_read_seconds / (wall * self.cfg.read_workers), 3),
            "counters": dict(self.stats),
            "publisher_yield_memory": self.memory.snapshot(),
            "publisher_read_allocation": self.allocation.snapshot(),
            "ai_search_advice": self.advice_trace,
            "selection_audit_first_reads": self.score_audit,
            "capture_feedback": self.feedback[:60],
            "events": self.events, "event_count": self.event_count,
            "events_omitted_by_limit": max(0, self.event_count - len(self.events)),
            "scope": "Routing and scheduling decisions only; final qualification, dates, relevance and body checks are unchanged",
        }
