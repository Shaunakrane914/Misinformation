"""Deterministic offline replay of saved investigations through the real acquisition engine.

Both controllers run the production ``run_harvest_pipeline`` against the SAME recorded world: the
search results each query returned, and the page or failure each URL produced, with their recorded
latencies. Nothing touches the network (it is blocked before application imports) and no model runs.

What the replay can and cannot show
-----------------------------------
* It compares scheduling and selection over candidates whose outcomes were observed. A URL the
  original run never read has no recorded outcome: the replay returns an explicit failure and counts it
  as UNOBSERVED. It is never counted as a success, so replay cannot invent yield for new choices.
* Time is compressed by ``--time-scale`` (profile deadlines and host spacing are scaled the same way);
  reported seconds are divided back to nominal seconds and are ESTIMATES of the replayed schedule.
* Admissions are charged from recorded attempts (one per provider attempt, one per redirect hop, two per
  wrapper resolution). They approximate, and do not equal, the live accounting; compare controllers to
  each other, not to the live count.
* CPU and memory here cover scheduling and Python processing of saved text. Live HTML parsing is NOT
  exercised; take live resource numbers from the pilot.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import statistics
import sys
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.audits import acquisition_baseline as baseline   # noqa: E402  (shared definitions and isolation)
from scripts.audits.resource_sampler import ResourceSampler   # noqa: E402

DROP_METADATA = {"read_success", "page_metadata", "transport", "raw_capture", "char_count", "acquired_id",
                 "acquisition_attempt_id", "wrapper_resolution", "observed_final_endpoint", "discovery_title",
                 "qualification_status", "raw_source_type", "harvest_acquisition_eligible", "harvest_unread_reason",
                 "adaptive_read_deferral", "pipeline_selection", "discovery_query_aliases", "temporal_required",
                 "layer2_eligible", "temporal_eligible", "post_read_qualification_reason", "publication_time_basis",
                 "harvest_temporal_priority", "discovery_temporal_observation", "readable_word_count",
                 "readable_character_count", "readable_text_sha256", "temporal_assessment", "temporal_status",
                 "recency_score", "discovery_snippet", "selected_for_read"}


class _DatetimeMeta(type):
    """Let ``isinstance(real_datetime, FrozenDatetime)`` stay true inside patched modules."""

    def __instancecheck__(cls, obj):
        return isinstance(obj, datetime)

    def __subclasscheck__(cls, sub):
        return issubclass(sub, datetime)


def frozen_datetime(moment):
    """A ``datetime`` stand-in whose ``now()`` is the recorded run time (date-window queries depend on it)."""
    class FrozenDatetime(datetime, metaclass=_DatetimeMeta):
        @classmethod
        def now(cls, tz=None):
            return moment.astimezone(tz) if tz else moment.replace(tzinfo=None)
    return FrozenDatetime


class ReplayWorld:
    def __init__(self, report, *, time_scale=1.0):
        from backend.services.research.source_identity import source_url_key
        self.scale = time_scale
        corpus = report["research_corpus"]
        trace = report["deep_research_trace"]
        self.query_rows = {q["query_id"]: q for q in corpus["queries"]}
        self.candidates = corpus["raw_candidates"]
        by_id = {c["id"]: c for c in self.candidates}
        self.by_query = defaultdict(list)
        self.continuations_excluded = 0
        # Page links were not retained in the saved pool. Rebuild each parent's observed link list from the child
        # leads it produced live (children carry ``discovered_on_url``). Links the live engine did not select are
        # unknown, so the replay can only re-offer what the original run actually followed.
        self.links_by_parent = defaultdict(list)
        for candidate in self.candidates:
            meta = candidate.get("metadata") or {}
            if meta.get("discovered_on_url") and (meta.get("discovered_on_candidate_id") or meta.get("observed_parent_id")):
                self.links_by_parent[source_url_key(meta["discovered_on_url"])].append({
                    "url": meta.get("discovery_url") or candidate["canonical_url"], "text": candidate.get("title", ""),
                    "kind": meta.get("discovery_kind", "ARTICLE_LEAD"), "published": candidate.get("published_at") or "",
                    "summary": candidate.get("snippet", ""), "publisher": candidate.get("source_name", ""),
                    "publication_time_source": meta.get("publication_time_source", ""),
                    "publisher_source_url": meta.get("publisher_source_url", ""),
                    "feed_identity": meta.get("feed_identity", ""), "feed_url": meta.get("feed_url", "")})
        for candidate in self.candidates:
            meta = candidate.get("metadata") or {}
            # Continuations (publisher hubs, child links) are created by the engine while it reads. They inherit
            # a parent's query_id but were never search results, so they must not be served as search results.
            if meta.get("observed_parent_id") or meta.get("publisher_basis") or meta.get("discovered_on_candidate_id"):
                self.continuations_excluded += 1
                continue
            for query_id in [candidate.get("query_id")] + list(meta.get("discovery_query_aliases") or []):
                if query_id:
                    self.by_query[query_id].append(candidate)
        self.query_index = {}
        for row in corpus["queries"]:
            self.query_index[(row["channel"], " ".join(str(row["query_text"]).casefold().split()))] = row["query_id"]
        pool = corpus["raw_acquisition_pool"]
        records = {s["source_id"]: s for s in pool["sources"] if s.get("readable_text")}
        self.reads, durations = {}, []
        self.wrapper_resolutions = {}
        for attempt in trace.get("acquisition_attempts", []):
            key = source_url_key(attempt["url"])
            duration = (attempt.get("duration_ms") or 0) / 1000
            durations.append(duration)
            outcome = {"attempt": attempt, "duration": duration}
            if attempt.get("status") == "SUCCESS":
                candidate = by_id.get(attempt.get("candidate_id")) or {}
                record = records.get(attempt.get("candidate_id")) or next(
                    (r for r in records.values() if source_url_key(r["source_url"]) == source_url_key(candidate.get("canonical_url") or "")), None)
                outcome["record"] = record
            resolution = attempt.get("wrapper_resolution")
            if resolution:
                self.wrapper_resolutions[" ".join(str(resolution.get("query", "")).casefold().split())] = resolution
            self.reads[key] = outcome
        self.median_read = statistics.median(durations) if durations else 1.5
        self.channels = sorted({q["channel"] for q in corpus["queries"]} | {"web", "news", "rss"})


class ReplayService:
    """Duck-typed stand-in for AgentReachService."""

    def __init__(self, world):
        self.world = world
        self.registry = SimpleNamespace(channel_names=tuple(world.channels))
        self.lock = threading.Lock()
        self.counts = Counter()
        self.unobserved_urls = []
        self.unobserved_queries = []
        self.carry = 0.0
        self.query_log = []

    def _sleep(self, seconds):
        time.sleep(max(0.0, seconds) * self.world.scale)

    # Admission cost per operation, least-squares fitted on the 12 recorded runs (reading ~= 1.21 per
    # body, ~2.95 per unresolved wrapper lookup, ~1.41 per other failure; discovery ~= 2.65 per query).
    # A fractional carry keeps totals unbiased while every individual charge is a whole admission.
    COST = {"search": 2.65, "wrapper_search": 2.95, "read_failure": 1.41, "read_extra": 0.21}

    def _charge(self, url, cost):
        from backend.infrastructure.acquisition.network.budget import reserve_public_request
        with self.lock:
            self.carry += cost
            whole = int(self.carry + 1e-9)
            self.carry -= whole
        for _ in range(whole):
            reserve_public_request(url)
            with self.lock:
                self.counts["admissions_charged"] += 1

    def retrieve_many(self, channel_queries, **kwargs):
        from backend.services.agent_reach.channels import EvidenceFragment, QueryExecutionRecord, RetrievalResult
        from backend.services.research.source_identity import source_url_key
        world = self.world
        timeout_real = float(kwargs.get("timeout", 15.0))      # the engine's own real-clock bound
        max_per_query = int((kwargs.get("budget") or {}).get("max_results_per_query", 10))
        fragments, records = [], []
        longest = 0.0
        for channel, rows in channel_queries.items():
            workers = [0.0, 0.0]            # two workers per channel, as in the live service
            for row in rows:
                key = (channel, " ".join(str(row["query_text"]).casefold().split()))
                resolution = world.wrapper_resolutions.get(key[1]) if row.get("query_class") == "publisher_url_resolution" else None
                query_id = world.query_index.get(key)
                recorded = world.query_rows.get(query_id) if query_id else None
                latency = ((recorded or {}).get("latency_ms") or 0) / 1000
                if resolution is not None:
                    latency = max((r.get("latency_ms", 0) for r in resolution.get("query_records", [])), default=1500) / 1000
                observed = recorded is not None or resolution is not None
                with self.lock:
                    self.query_log.append([channel, row.get("query_class"), str(row["query_text"])[:120], observed])
                if not observed:
                    latency = world.median_read
                    with self.lock:
                        self.counts["searches_unobserved"] += 1
                        self.unobserved_queries.append([channel, str(row["query_text"])[:140]])
                slot = min(range(len(workers)), key=workers.__getitem__)
                workers[slot] += latency
                finish = workers[slot]
                longest = max(longest, finish)
                status, error, found = "SUCCESS", None, []
                # Failures can consume HTTP admissions too. Where no original
                # transport count exists, charge the explicit model rather than
                # treating an unknown failed-search cost as zero.
                explicit = (recorded or {}).get("native_http_admissions")
                not_started = (recorded or {}).get("provider_started") is False or (recorded or {}).get("status") in {
                    "NOT_SUBMITTED", "PLANNED", "SKIPPED", "CANCELLED_BEFORE_START"}
                if type(explicit) is int and explicit >= 0:
                    cost, basis = explicit, "RECORDED_QUERY_ADMISSIONS"
                elif not_started:
                    cost, basis = 0, "RECORDED_NOT_STARTED"
                else:
                    cost = self.COST["wrapper_search" if resolution is not None else "search"]
                    basis = "ESTIMATED_UNKNOWN_QUERY_COST"
                self.counts[basis] += 1
                try:
                    host = "bing.com" if channel in {"news", "web"} else (channel + ".example")
                    self._charge(f"https://{host}/replay-search", cost)
                except TimeoutError as exc:
                    status, error = "TIMEOUT", str(exc)
                if not observed:
                    status, error = "FAILED", "UNOBSERVED_IN_SAVED_CAPTURE"
                elif recorded is not None and recorded.get("status") != "SUCCESS":
                    status, error = recorded.get("status") or "FAILED", recorded.get("error") or "recorded failure"
                elif finish * world.scale > timeout_real:
                    status, error = "TIMEOUT", "Replay wave timeout"
                else:
                    if status == "SUCCESS":
                        if resolution is not None:
                            found = [{"canonical_url": c["url"], "title": c.get("title", ""), "snippet": "", "metadata": {}}
                                     for c in resolution.get("candidates", [])]
                        elif query_id:
                            found = world.by_query.get(query_id, [])[:max_per_query]
                        with self.lock:
                            self.counts["searches_replayed"] += 1
                for candidate in found:
                    meta = {k: v for k, v in (candidate.get("metadata") or {}).items() if k not in DROP_METADATA}
                    url = (candidate.get("metadata") or {}).get("observed_discovery_url") or candidate["canonical_url"]
                    depth = candidate.get("content_depth") if candidate.get("content_depth") in {"SNIPPET", "HEADLINE_ONLY", "INDEX_SNIPPET", "FEED_ENTRY_SUMMARY"} else "FEED_ENTRY_SUMMARY"
                    upstream = (candidate.get("metadata") or {}).get("upstream_evidence_ids") or [candidate.get("id", "")]
                    fragments.append(EvidenceFragment(
                        platform=candidate.get("platform") or candidate.get("channel") or channel, title=candidate.get("title", ""),
                        url=url, snippet=candidate.get("snippet", ""), published=candidate.get("published_at") or "",
                        channel_name=candidate.get("channel") or channel, query_id=row["query_id"],
                        query_class=row.get("query_class", "general"), query_text=row["query_text"], content_depth=depth,
                        evidence_id=upstream[0], raw_metadata=meta, retrieval_mode=candidate.get("retrieval_mode") or "direct_api"))
                records.append(QueryExecutionRecord(
                    query_id=row["query_id"], channel=channel, query_text=row["query_text"], query_class=row.get("query_class"),
                    status=status, error=error, result_count_raw=len(found), result_count_normalized=len(found),
                    latency_ms=int(latency * 1000)))
        time.sleep(max(0.0, min(longest * world.scale, timeout_real)))
        return RetrievalResult(query="", domain=kwargs.get("domain", ""), fragments=fragments, query_records=records,
                               channel_health={c: "AVAILABLE" for c in channel_queries})

    def read(self, url, max_chars=12_000):
        from backend.services.research.source_identity import source_url_key
        outcome = self.world.reads.get(source_url_key(url))
        record = (outcome or {}).get("record")
        chain = ((record or {}).get("transport") or {}).get("redirect_chain") or [url]
        failed = outcome is None or outcome["attempt"].get("status") != "SUCCESS" or not record
        try:
            self._charge(url, self.COST["read_failure"] if failed else len(chain) + self.COST["read_extra"])
        except TimeoutError as exc:
            with self.lock:
                self.counts["reads_refused_by_http_budget"] += 1
            return {"status": "failed", "failure_kind": "PROVIDER_FAILURE", "error": str(exc)}
        if outcome is None:
            with self.lock:
                self.counts["reads_unobserved"] += 1
                self.unobserved_urls.append(url)
            self._sleep(self.world.median_read)
            return {"status": "failed", "error": "UNOBSERVED_IN_SAVED_CAPTURE", "failure_kind": "PROVIDER_FAILURE"}
        attempt = outcome["attempt"]
        with self.lock:
            self.counts["reads_replayed"] += 1
        self._sleep(outcome["duration"])
        if attempt.get("status") == "SUCCESS" and record:
            page = dict(record.get("page_metadata") or {})
            keys = {source_url_key(u) for u in [url, record.get("source_url"), record.get("canonical_url"), *(record.get("source_urls") or [])] if u}
            links = [link for key in keys for link in self.world.links_by_parent.get(key, [])]
            if links and not page.get("observed_links"):
                page["observed_links"] = links
                with self.lock:
                    self.counts["observed_links_restored"] += len(links)
            return {"status": "success", "markdown": record["readable_text"], "content": record["readable_text"],
                    "page_metadata": page, "transport": record.get("transport") or {},
                    "raw_capture": {"text": record.get("raw_text") or record["readable_text"]}, "backend": attempt.get("backend"),
                    "title": record.get("title", "")}
        return {"status": "error", "error": attempt.get("error_message") or "recorded failure",
                "failure_kind": attempt.get("failure_kind") or "PROVIDER_FAILURE", "status_code": attempt.get("http_status")}


def scaled_profile(scale):
    from backend.services.research.research_profiles import PROFILES
    base = PROFILES["DEEP"]
    timeout = max(1.0, base.timeout_seconds * scale)
    return dataclasses.replace(base, timeout_seconds=timeout, discovery_seconds=min(base.discovery_seconds * scale, timeout * 0.5),
                               read_window_seconds=max(0.1, min(30.0, base.read_window_seconds * scale)),
                               host_spacing_seconds=base.host_spacing_seconds * scale)


def configure(spec):
    """``legacy`` | ``interleaved`` | ``pipelined:r2[:d1][:ranked|legacy_priority][:nofutility]``."""
    env = {"AEGIS_ACQUISITION_CONTROLLER": "legacy"}
    if spec == "legacy":
        return env
    if spec == "interleaved":
        return {"AEGIS_ACQUISITION_CONTROLLER": "interleaved_v1"}
    parts = spec.split(":")
    if parts[0] != "pipelined":
        raise ValueError("Unknown configuration " + spec)
    env["AEGIS_ACQUISITION_CONTROLLER"] = "pipelined_v1"
    env["AEGIS_PIPELINE_SELECTOR"] = "ranked_v2"
    for part in parts[1:]:
        if part.startswith("r") and part[1:].isdigit():
            env["AEGIS_PIPELINE_READ_WORKERS"] = part[1:]
        elif part.startswith("d") and part[1:].isdigit():
            env["AEGIS_PIPELINE_DISCOVERY_WORKERS"] = part[1:]
        elif part in {"ranked", "legacy_priority"}:
            env["AEGIS_PIPELINE_SELECTOR"] = "ranked_v2" if part == "ranked" else "legacy_priority"
        elif part == "nofutility":
            env["AEGIS_PIPELINE_FUTILITY"] = "off"
        else:
            raise ValueError("Unknown option " + part)
    return env


def label_replay_costs(row):
    """Simulator reservations are modeled costs, never original live measurements."""
    modeled = row.setdefault("MODELED", {})
    for name in ("http_admissions", "http_admissions_by_phase"):
        modeled[name] = row["MEASURED"].get(name)
        row["MEASURED"][name] = baseline.NOT_RECORDED
    for name in ("evidence_words_per_100_admissions", "qualified_sources_per_100_admissions"):
        modeled[name] = row["DERIVED"].pop(name, baseline.NOT_RECORDED)
    modeled["scope"] = "Replay cost model; failed/unknown search costs are estimated unless explicitly recorded"
    return row


def replay_one(report, *, agent, label, spec, scale, predicate="current", claim_text=None):
    import backend.services.agent_reach as agent_reach_module
    from backend.application.research.harvest_pipeline import run_harvest_pipeline
    from backend.services.research import research_profiles
    from backend.services.research.research_budget import ResearchBudget
    from backend.services.research.research_models import ResearchRequest

    target, domain = baseline.recorded_target_and_domain(report, agent)
    world = ReplayWorld(report, time_scale=scale)
    service = ReplayService(world)
    env = configure(spec)
    for key in ("AEGIS_PIPELINE_READ_WORKERS", "AEGIS_PIPELINE_DISCOVERY_WORKERS", "AEGIS_PIPELINE_SELECTOR", "AEGIS_PIPELINE_FUTILITY"):
        os.environ.pop(key, None)
    os.environ.update(env)
    request = ResearchRequest(target=target, domain=domain, agent_name=agent, timeout_seconds=max(1.0, 240 * scale),
                              research_profile="DEEP", extra_params={"claim_text": claim_text or target})
    budget = ResearchBudget(timeout_seconds=max(1.0, 240 * scale), deep_read_budget=24, discovery_budget=100)
    import importlib
    # ``import pkg.mod as name`` can resolve to a same-named package attribute (a singleton); load the module itself.
    harvesting_module = importlib.import_module("backend.services.research.harvesting")
    temporal_module = importlib.import_module("backend.services.research.temporal_guard")
    recorded_pool = report["research_corpus"]["raw_acquisition_pool"]
    recorded_now = datetime.fromisoformat(recorded_pool["created_at"])
    clock = frozen_datetime(recorded_now)
    original_profile, original_service = research_profiles.PROFILES["DEEP"], agent_reach_module.agent_reach_service
    original_clocks = (harvesting_module.datetime, temporal_module.datetime)
    research_profiles.PROFILES["DEEP"] = scaled_profile(scale)
    agent_reach_module.agent_reach_service = service
    harvesting_module.datetime = temporal_module.datetime = clock
    try:
        with ResourceSampler() as sampler:
            started = time.perf_counter()
            result = run_harvest_pipeline(request, budget, "DEEP")
            wall = time.perf_counter() - started
    finally:
        harvesting_module.datetime, temporal_module.datetime = original_clocks
        research_profiles.PROFILES["DEEP"] = original_profile
        agent_reach_module.agent_reach_service = original_service
        for key in ("AEGIS_ACQUISITION_CONTROLLER", "AEGIS_PIPELINE_READ_WORKERS", "AEGIS_PIPELINE_DISCOVERY_WORKERS",
                    "AEGIS_PIPELINE_SELECTOR", "AEGIS_PIPELINE_FUTILITY"):
            os.environ.pop(key, None)
    telemetry = result.telemetry
    harvest_ms = (telemetry.get("stage_timings_ms") or {}).get("Query planning and raw harvesting", wall * 1000)
    # Same definitions as the recorded rows: qualification is judged at the RECORDED run time.
    if isinstance(result.research_corpus.get("raw_acquisition_pool"), dict):
        result.research_corpus["raw_acquisition_pool"]["created_at"] = recorded_pool["created_at"]
    synthetic = {"research_corpus": result.research_corpus,
                 "deep_research_trace": {**telemetry, "discovery_waves": [{"query": target, "domain": domain}],
                                         "acquisition_attempts": telemetry.get("acquisition_attempts")
                                         or (result.retrieval_trace or {}).get("acquisition_attempts") or []}}
    row = baseline.measure_report(synthetic, agent=agent, label=f"{label}/{spec}", case_row={"input": target, "seconds": round(wall, 2)}, predicate=predicate)
    label_replay_costs(row)
    controller = (telemetry.get("harvesting") or {}).get("acquisition_controller") or {}
    row["REPLAY"] = {
        "configuration": spec, "time_scale": scale, "nominal_harvest_seconds_ESTIMATE": round(harvest_ms / 1000 / scale, 1),
        "nominal_total_seconds_ESTIMATE": round(wall / scale, 1), "counts": dict(service.counts),
        "continuations_regenerated_by_engine_not_served": world.continuations_excluded, "unobserved_read_urls": service.unobserved_urls[:10], "unobserved_queries": service.unobserved_queries[:12], "query_log": service.query_log, "resource": sampler.result(),
        "controller": {k: controller.get(k) for k in ("mode", "stop_reason", "reads_started", "reads_completed", "queries_dispatched",
                                                     "queries_planned", "max_inflight_reads", "read_worker_utilization", "counters", "config")}
        if controller else None,
        "unread_by_reason": (telemetry.get("harvesting") or {}).get("unread_by_reason"),
    }
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", action="append", required=True, metavar="LABEL=DIR")
    parser.add_argument("--config", action="append", required=True, help="legacy | interleaved | pipelined:r2[:d1][:ranked|legacy_priority][:nofutility]")
    parser.add_argument("--time-scale", type=float, default=0.25)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--only-agent", action="append", choices=sorted(baseline.DOMAINS))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)
    if not 0.02 <= args.time_scale <= 1.0:
        parser.error("--time-scale must be within 0.02..1.0")
    output = baseline._safe_output(args.output)
    markdown = baseline._safe_output(args.markdown) if args.markdown else None
    baseline._isolate()
    rows, before = [], {}
    for spec in args.batch:
        label, _, directory = spec.partition("=")
        for batch, case, path in baseline.load_batch(label, directory):
            if args.only_agent and case["agent"] not in args.only_agent:
                continue
            before[str(path)] = baseline.sha256_file(path)
            report = json.loads(path.read_text(encoding="utf-8"))
            for config in args.config:
                for repeat in range(args.repeat):
                    row = replay_one(report, agent=case["agent"], label=batch, spec=config, scale=args.time_scale)
                    row["REPLAY"]["repeat"] = repeat
                    rows.append(row)
                    print(json.dumps({"id": row["id"], "qualified": row["DERIVED"]["qualified_source_records"],
                                      "words": row["DERIVED"]["relevant_passage_words_unique"],
                                      "modeled_admissions": row["MODELED"]["http_admissions"], "nominal_s": row["REPLAY"]["nominal_total_seconds_ESTIMATE"],
                                      "unobserved_reads": row["REPLAY"]["counts"].get("reads_unobserved", 0)}), flush=True)
    unchanged = all(baseline.sha256_file(Path(p)) == digest for p, digest in before.items())
    payload = {"mode": "OFFLINE_REPLAY_COMPARISON", "network_calls": 0, "model_calls": 0, "inputs_unchanged": unchanged,
               "time_scale": args.time_scale, "configs": args.config, "runs": rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if markdown:
        lines = ["# Offline acquisition replay comparison", "",
                 "HTTP costs and nominal latency are modeled estimates, not live measurements.", "",
                 "| Case | Configuration | Qualified | Selected words | Modeled HTTP admissions |",
                 "| --- | --- | ---: | ---: | ---: |"]
        for row in rows:
            lines.append(f"| {row['id']} | {row['REPLAY']['configuration']} | {row['DERIVED']['qualified_source_records']} | "
                         f"{row['DERIVED']['relevant_passage_words_unique']} | {row['MODELED']['http_admissions']} |")
        markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"runs": len(rows), "inputs_unchanged": unchanged}))
    return 0 if unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
