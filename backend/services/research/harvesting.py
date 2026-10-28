"""Acquisition-first harvesting using the existing policy-checked adapters.

Candidate eligibility here is deliberately not final evidence qualification.
No date, truth verdict, primary-source label or excerpt is invented. Captures
are returned before downstream entity/objective/temporal/passage qualification.
The engine is synchronous: call it from the existing agent worker, not an event
loop. All mutable budget state belongs to one run and closes before returning.
"""
import copy
import hashlib
import math
import os
import re
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from urllib.parse import urlsplit

from backend.infrastructure.acquisition.network.budget import (
    acquisition_deadline, remaining_timeout, reserve_reading_capacity, public_request_phase, discovery_http_remaining,
)
from backend.services.research.content_roles import document_role, matches_objective
from backend.services.research.research_models import EvidenceItem
from backend.services.research.research_profiles import get_research_profile
from backend.services.research.source_identity import source_url_key


_ASSET = re.compile(r"\.(?:svg|png|jpe?g|gif|webp|ico|css|js|woff2?|mp[34]|zip|exe)$", re.I)
_PRIVATE_PATH = re.compile(r"(?:^|/)(?:login|signin|sign-in|logout|checkout|cart|privacy|terms)(?:/|$)", re.I)
_OBJECTIVES = {
    "financial": ("quarterly earnings", "investor disclosure", "financial statements",
                  "company guidance", "financial analysis", "regulatory filing"),
    "brand": ("counterfeit enforcement", "impersonation phishing", "consumer complaints",
              "fraud warning", "unauthorized sellers", "complaints response"),
    "personal": ("interview", "impersonation allegation", "identity deepfake",
                 "interview transcript", "official statement", "false quotation"),
    "trending": ("recent developments", "research update", "industry announcement",
                 "institution announcement", "latest news", "project deployment"),
}

# Routing hints only. A match can prioritize a read, never qualify a body,
# authenticate an actor or establish the truth of the headline.
_SPECIALIST_SIGNALS = {
    "COUNTERFEIT": r"counterfeit|knockoff|replica|trademark",
    "PHISHING": r"phishing|credential|password|spoof",
    "COMPLAINT": r"complaint|refund|delivery|customer service|never received",
    "PRODUCT_SAFETY": r"recall|defect|safety|hazard|injur",
    "PUBLIC_STATEMENT": r"statement|interview|speech|transcript|said|wrote",
    "FALSE_QUOTE": r"false quote|fake quote|fabricat|misattribut|never said|did not say|fact.check|debunk",
    "IMPERSONATION": r"impersonat|fake account|fake profile|identity theft",
    "DEEPFAKE": r"deepfake|synthetic media|manipulated video",
    "BRAND_ABUSE": r"counterfeit|phishing|impersonat|fraud|scam",
    "IDENTITY_THREAT": r"impersonat|deepfake|fake account|false quote|misattribut|scam",
}
_TASK_ANGLES = {
    "COUNTERFEIT": ("counterfeit listing report", "counterfeit enforcement", "unauthorized seller allegation"),
    "PHISHING": ("phishing incident report", "credential theft warning", "phishing allegation response"),
    "COMPLAINT": ("consumer complaint response", "refund complaint report", "consumer dispute investigation"),
    "PRODUCT_SAFETY": ("product safety recall notice", "recall company response", "product safety investigation"),
    "PUBLIC_STATEMENT": ("interview", "speech transcript", "public statement"),
    "FALSE_QUOTE": ("quotation original transcript", "misattributed quote fact check", "quotation denial correction"),
    "IMPERSONATION": ("impersonation allegation report", "fake account warning", "impersonation company response"),
    "DEEPFAKE": ("deepfake allegation report", "synthetic media original source", "manipulated video verification"),
    "BRAND_ABUSE": ("brand abuse allegation", "fraud warning response", "brand impersonation report"),
    "IDENTITY_THREAT": ("identity abuse allegation", "impersonation report response", "false quotation investigation"),
}


def _merge_task_lineage(destination, source):
    """Merge bounded routing metadata without changing source identity/body."""
    for key, allowed in (("specialist_tasks", set(_SPECIALIST_SIGNALS)),
                         ("requested_specialist_tasks", set(_SPECIALIST_SIGNALS)),
                         ("acquisition_objectives", {"PUBLIC_STATEMENT", "IDENTITY_THREAT"})):
        values = source.get(key, [])
        if not isinstance(values, (list, tuple)):
            values = []
        singular = source.get("specialist_task" if key == "specialist_tasks" else "acquisition_objective")
        if key != "requested_specialist_tasks" and isinstance(singular, str) and singular in allowed:
            values = [*values, singular]
        prior = destination.get(key, [])
        merged = [value for value in prior if isinstance(value, str) and value in allowed] if isinstance(prior, (list, tuple)) else []
        merged.extend(value for value in values if isinstance(value, str) and value in allowed and value not in merged)
        if merged:
            destination[key] = list(dict.fromkeys(merged))[:16]
        else:
            destination.pop(key, None)
    prior_ids = destination.get("source_plan_action_ids", [])
    action_ids = [value for value in prior_ids if isinstance(value, str)
                  and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value)] if isinstance(prior_ids, (list, tuple)) else []
    values = source.get("source_plan_action_ids", [])
    values = list(values) if isinstance(values, (list, tuple)) else []
    if source.get("source_plan_action_id"):
        values.append(source["source_plan_action_id"])
    action_ids.extend(value for value in values if isinstance(value, str)
                      and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value) and value not in action_ids)
    if action_ids:
        destination["source_plan_action_ids"] = list(dict.fromkeys(action_ids))[:16]
    else:
        destination.pop("source_plan_action_ids", None)


def diversified_queries(target, domain="general", intent="", aliases=(), reference_time=None, specialist_tasks=(), window_hours=48.0):
    """General subject/angle queries, no test-subject or publisher URL special cases."""
    target = re.sub(r"\s+", " ", str(target)).strip()[:180]
    if not target:
        return []
    names = [target] + [str(alias).strip()[:180] for alias in aliases if str(alias).strip()]
    names = list(dict.fromkeys(names))[:3]  # only caller-validated aliases
    angles = _OBJECTIVES.get(domain, ("recent reporting", "official statement report", "research news analysis",
                                      "public source investigation", "documented developments", "independent reporting"))
    task_angles = ([(angle, task) for task in specialist_tasks if task in _TASK_ANGLES
                    for angle in _TASK_ANGLES[task]][:6] if domain in {"brand", "personal"} else [])
    if task_angles:
        angles = tuple(angle for angle, _ in task_angles)
    specs = []
    reference = reference_time or datetime.now(timezone.utc)
    # Search hints improve provider recall only. The requested time boundary is
    # checked against captured publication declarations after acquisition.
    window_hours = window_hours if isinstance(window_hours, (int, float)) and 1 <= window_hours <= 168 else 48.0
    recent_hint = (" when:" + str(max(1, math.ceil(window_hours / 24))) + "d after:" + (reference - timedelta(hours=window_hours)).date().isoformat()
                   + " before:" + (reference + timedelta(days=1)).date().isoformat())
    for index, angle in enumerate(angles):
        subject = names[index % len(names)]
        if domain == 'personal' and len(subject.split()) >= 2 and '"' not in subject:
            subject = '"' + subject + '"'
        # Multiple source categories, without sending every case to social media.
        for channel in ("news", "web", "rss"):
            text = f"{subject} {angle}"
            if domain == "trending":
                text += recent_hint
            specs.append({"channel": channel, "query_id": f"harvest_{len(specs) + 1:03d}",
                          "query_class": "harvest_" + angle.split()[0], "query_text": text,
                          "operation": "search", "basis": "DETERMINISTIC_OBJECTIVE",
                          "acquisition_objective": ("PUBLIC_STATEMENT" if domain == "personal" and index in {0, 3, 4}
                                                    else "IDENTITY_THREAT" if domain == "personal" else domain.upper())})
            if task_angles:
                task = task_angles[index][1]
                specs[-1].update(specialist_task=task, requested_specialist_tasks=list(specialist_tasks),
                    acquisition_objective=("PUBLIC_STATEMENT" if task == "PUBLIC_STATEMENT" else "IDENTITY_THREAT")
                    if domain == "personal" else task)
    # A concrete caller objective diversifies one existing angle, never raises caps.
    objective = re.sub(r"\s+", " ", str(intent)).strip()[:140]
    if not task_angles and objective and objective.casefold() not in {"general", "research", "investigate", domain}:
        # An internal agent instruction is not a useful verbatim search query.
        # Preserve concise explicit user objectives; do not replace the first
        # useful angle with a long sentence about the pipeline's own job.
        if len(objective.split()) <= 8 and target.casefold() not in objective.casefold():
            specs[0]["query_text"] = f"{target} {objective}" + (recent_hint if domain == "trending" else "")
            if domain == "personal":
                # Change the task only when that intent actually replaces the
                # query. Internal agent prose must not relabel an unchanged
                # public-statement query as identity-threat discovery. Otherwise
                # duplicate news/RSS completion order changes qualification.
                statement = bool(re.search(r"\b(?:statement|interview|speech|transcript)\b", objective, re.I))
                threat = bool(re.search(r"impersonat|deepfake|scam|false.quote|identity.threat|identity.misuse", objective, re.I))
                specs[0]["acquisition_objective"] = "PUBLIC_STATEMENT" if statement and not threat else "IDENTITY_THREAT"
    return specs


def _locator(url):
    """Diagnostics exclude credentials, query-string secrets and fragments."""
    try:
        p = urlsplit(url)
        return f"{p.scheme}://{p.hostname or ''}{p.path}"[:500]
    except ValueError:
        return "INVALID_URL"


def _host(url):
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _is_wrapper(item):
    return _host(item.canonical_url) == "news.google.com"


def _observed_publisher(item):
    """A routing diversity hint, not verified ownership or independence.

    Feed wrappers all share a transport host. Their explicitly observed source
    URLs allow us to avoid spending the entire wrapper allowance on one declared
    publisher. Never derive an article address or grant access from this hint.
    """
    if not _is_wrapper(item):
        return _host(item.canonical_url)
    url = item.metadata.get("publisher_source_url") or ""
    try:
        parsed = urlsplit(url)
        if parsed.scheme in {"http", "https"} and not parsed.username and not parsed.password:
            return (parsed.hostname or "").lower().removeprefix("www.")
    except ValueError:
        pass
    return _host(item.canonical_url)


def _source_body_admissible(item):
    """Cached/configuration-only policy preflight; never spend a reader slot on denial.

    Keep the lead inspectable. DeepReader and the transport still recheck rights,
    robots and redirects immediately before actual access.
    """
    from backend.services.research.source_registry import source_registry
    decision = source_registry.body_decision(item.canonical_url)
    item.metadata['source_body_admission'] = decision
    return decision['eligible']


def _read_priority(item, target, domain, host_counts, publisher_counts):
    """Order observed leads; final body, subject and publication gates are later."""
    ordinary = (item.metadata.get("harvest_temporal_priority", 0),
                not bool(item.metadata.get("source_citation")),
                not matches_objective(item.title + " " + item.snippet, domain),
                _is_index(item), _is_wrapper(item), publisher_counts[_observed_publisher(item)],
                host_counts[_host(item.canonical_url)], item.id)
    if domain in {"brand", "personal"}:
        tasks = item.metadata.get("requested_specialist_tasks") or item.metadata.get("specialist_tasks") or []
        context = " ".join((item.title or "", item.snippet or "", urlsplit(item.canonical_url).path))
        matched = any(re.search(_SPECIALIST_SIGNALS[task], context, re.I)
                      for task in tasks if task in _SPECIALIST_SIGNALS)
        return (bool(tasks) and not matched, *ordinary)
    if domain != "trending":
        return ordinary
    target_words = set(re.findall(r"[^\W_]+", str(target).casefold(), re.UNICODE))
    # The query text, feed source label and opaque wrapper path must not make
    # an otherwise off-topic headline appear to discuss the subject.
    lead_words = set(re.findall(r"[^\W_]+", str(item.title).casefold(), re.UNICODE))
    hits = len(target_words & lead_words)
    return (ordinary[0], publisher_counts[_observed_publisher(item)], -hits, *ordinary[1:])


def _unread_wrapper_hubs(candidates, seen_urls, limit=2):
    """Use observed feed source hubs after opaque-wrapper slots are spent.

    This is a public discovery-index read, not an article acquisition or an
    asserted failed wrapper. The normal reader still applies access and SSRF
    checks. The caller reserves existing discovery/read slots, including one
    potential article continuation, rather than enlarging its budgets.
    """
    from backend.services.research.publisher_links import is_publisher_hub
    hubs, seen = [], {source_url_key(url) for url in seen_urls}
    for candidate in candidates:
        if not _is_wrapper(candidate):
            continue
        url = candidate.metadata.get("publisher_source_url") or ""
        try:
            parsed = urlsplit(url)
            valid = (parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username
                     and not parsed.password and not parsed.query and not parsed.fragment and is_publisher_hub(url))
        except ValueError:
            valid = False
        key = source_url_key(url)
        if not valid or key in seen:
            continue
        seen.add(key)
        hubs.append(EvidenceItem(id="ev_hub_" + hashlib.sha256(key.encode()).hexdigest()[:12],
            canonical_url=url, title="Feed-declared publisher hub: " + (parsed.hostname or ""),
            channel="web", source_domain=parsed.hostname or "", query_class="observed_feed_publisher_hub",
            query_text=candidate.query_text, query_id=candidate.query_id,
            metadata={"discovered_on_candidate_id": candidate.id, "publisher_hop": 0,
                      "publisher_basis": "FEED_DECLARED_PUBLISHER_UNVERIFIED",
                      "hub_read_basis": "UNREAD_WRAPPER_ALLOWANCE_EXHAUSTED"}))
        hubs[-1].query_id = candidate.query_id
        _merge_task_lineage(hubs[-1].metadata, candidate.metadata)
        if len(hubs) >= limit:
            break
    return hubs


def _is_index(item):
    from backend.services.research.publisher_links import is_publisher_hub
    return (item.metadata.get("discovery_kind") == "FEED_INDEX"
            or is_publisher_hub(item.canonical_url)
            or document_role(item) in {"NEWS_INDEX", "DOCUMENT_INDEX", "LANDING_PAGE"})


def acquisition_reason(item, target, domain="general", aliases=()):
    """Reject clearly unrelated/unsafe locators, not undated or unproven leads.

    DNS/SSRF/access authorization is still performed by the native read adapter.
    A publisher/feed continuation has observed-parent context; generic external
    links and fabricated article addresses never receive that exception.
    """
    try:
        p = urlsplit(item.canonical_url)
        if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
            return "INVALID_OR_CREDENTIAL_URL"
        if _ASSET.search(p.path):
            return "NON_DOCUMENT_ASSET"
        if _PRIVATE_PATH.search(p.path):
            return "NON_RESEARCH_DESTINATION"
    except ValueError:
        return "INVALID_URL"
    if document_role(item) == "BACKGROUND_REFERENCE":
        return "BACKGROUND_REFERENCE_NOT_CURRENT_ACQUISITION"
    if document_role(item) == "PROFILE" or item.content_depth in {"SOCIAL_POST", "VIDEO_METADATA"}:
        return "NON_ARTICLE_METADATA"
    if item.metadata.get("source_kind") == "USER_SUPPLIED_SOURCE":
        return None  # explicit read scope, not autonomous discovery or evidence acceptance
    if item.metadata.get("observed_parent_id") or item.metadata.get("publisher_basis"):
        return None
    context = " ".join((item.title or "", item.snippet or "", p.path)).casefold()
    names = [target] + list(aliases)
    for name in names:
        words = re.findall(r"[^\W_]+", str(name).casefold(), re.UNICODE)
        if not words:
            continue
        matches = sum(bool(re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", context)) for word in words)
        # Topic phrases can reorder words. People require both name tokens;
        # single entity names never match arbitrary embedded substrings.
        required = len(words) if domain == "personal" else max(1, math.ceil(len(words) * 0.5))
        if matches >= required:
            return None
    return "SUBJECT_NOT_OBSERVED_IN_LEAD"


def raw_source_type(item):
    """An extraction category, not a claim-support or independence judgment."""
    if not item.metadata.get("read_success") or not item.acquired_id:
        return "BLOCKED_OR_FAILED" if item.read_status in {"FAILED", "TIMEOUT", "EMPTY_CONTENT"} else "DISCOVERY_LEAD"
    role = document_role(item)
    if role == "BACKGROUND_REFERENCE":
        return "BACKGROUND_REFERENCE"
    if role == "LANDING_PAGE":
        return "PUBLISHER_HOMEPAGE"
    if role in {"NEWS_INDEX", "DOCUMENT_INDEX"} or item.metadata.get("discovery_kind") == "FEED_INDEX":
        return "SOURCE_INDEX"
    if item.content_depth in {"SOCIAL_POST", "VIDEO_METADATA", "PROFILE_METADATA", "DIRECT_METADATA"}:
        return "COMMUNITY_POST" if item.content_depth == "SOCIAL_POST" else "STRUCTURED_PUBLIC_DATA"
    if item.primary_source and item.content_depth in {"PRIMARY_DOCUMENT", "REGULATORY_FILING", "OFFICIAL_STATEMENT"}:
        return "OFFICIAL_DOCUMENT"
    page = item.metadata.get("page_metadata") or {}
    # A long HTML page or an official label alone does not establish an article.
    kind = page.get("body_kind") or (page.get("body_quality") or {}).get("body_kind")
    return "ARTICLE_BODY" if kind == "ARTICLE_BODY" else "DISCOVERY_LEAD"


@dataclass
class HarvestResult:
    candidates: List[EvidenceItem] = field(default_factory=list)
    captures: List[EvidenceItem] = field(default_factory=list)
    query_records: List[Any] = field(default_factory=list)
    read_telemetry: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    profile: Dict[str, Any] = field(default_factory=dict)
    channel_queries: Dict[str, Any] = field(default_factory=dict)
    channel_health: Dict[str, Any] = field(default_factory=dict)
    retrieval_trace: Dict[str, Any] = field(default_factory=dict)


class _BudgetedService:
    """Shared operation/host quota for reads and wrapper-resolution searches.

    It counts service operations, not hidden HTTP steps inside native adapters.
    Running native calls remain bounded by their existing cooperative deadline.
    No late result is allowed to append to the closed investigation output.
    """
    def __init__(self, service, profile, deadline):
        self.service, self.profile, self.deadline = service, profile, deadline
        self.lock = threading.Lock()
        self.closed = False
        self.operations = 0
        self.host_reads = Counter()
        self.host_locks = {}
        self.last_host_start = {}
        self.host_wait_ms = 0.0
        self.actual_read_starts = 0
        self.search_query_reservations = 0

    def _reserve(self, count):
        with self.lock:
            if self.closed or time.monotonic() >= self.deadline:
                raise TimeoutError("Harvesting deadline exhausted")
            if self.operations + count > self.profile.max_operations:
                raise RuntimeError("HARVEST_OPERATION_BUDGET_EXHAUSTED")
            self.operations += count

    def retrieve_many(self, channel_queries, **kwargs):
        count = sum(len(rows) for rows in channel_queries.values())
        self._reserve(count)
        with self.lock:
            self.search_query_reservations += count
        timeout = min(float(kwargs.get("timeout", 15.0)), max(0.0, self.deadline - time.monotonic()))
        if timeout <= 0:
            raise TimeoutError("Harvesting deadline exhausted")
        kwargs["timeout"] = timeout
        kwargs["perform_reads"] = False
        with acquisition_deadline(min(self.deadline, time.monotonic() + timeout)):
            return self.service.retrieve_many(channel_queries, **kwargs)

    def read(self, url, max_chars=12_000):
        self._reserve(1)
        host = _host(url)
        with self.lock:
            if self.host_reads[host] >= self.profile.max_host_reads:
                return {"status": "failed", "failure_kind": "PROVIDER_FAILURE", "error": "HOST_READ_BUDGET_EXHAUSTED"}
            self.host_reads[host] += 1
            guard = self.host_locks.setdefault(host, threading.BoundedSemaphore(self.profile.host_concurrency))
        started = time.monotonic()
        wait = max(0.0, min(self.deadline - started, remaining_timeout(self.profile.read_window_seconds)))
        if not guard.acquire(timeout=wait):
            return {"status": "failed", "failure_kind": "TIMEOUT", "error": "Host queue deadline exhausted"}
        try:
            with self.lock:
                spacing = max(0.0, self.profile.host_spacing_seconds - (time.monotonic() - self.last_host_start.get(host, 0)))
            if spacing:
                # Short host politeness delay is bounded by the active deadline.
                time.sleep(min(spacing, max(0.0, self.deadline - time.monotonic())))
            with self.lock:
                if self.closed or time.monotonic() >= self.deadline:
                    return {"status": "failed", "failure_kind": "TIMEOUT", "error": "Harvest closed before read start"}
                self.host_wait_ms += (time.monotonic() - started) * 1000
                self.last_host_start[host] = time.monotonic()
                self.actual_read_starts += 1
            with acquisition_deadline(self.deadline):
                return self.service.read(url, max_chars=min(20_000, max_chars))
        finally:
            guard.release()

    def close(self):
        with self.lock:
            self.closed = True


class HarvestingEngine:
    def __init__(self, service, reader=None):
        from backend.services.research.deep_reader import DeepReader
        self.service = service
        self.reader = reader or DeepReader()

    def run(self, target, domain="general", intent="", agent_name="research", profile="STANDARD",
            deadline=None, initial_candidates=(), query_plan=None, progress=None, aliases=(), request=None,
            source_url=None, specialist_tasks=(), specialist_task_explicit=False, controller="legacy", source_plan=None):
        if controller not in {"legacy", "interleaved_v1", "pipelined_v1"}:
            raise ValueError("Unknown acquisition controller")
        profile = get_research_profile(profile)
        started = time.monotonic()
        deadline = min(float(deadline), started + profile.timeout_seconds) if deadline is not None else started + profile.timeout_seconds
        discovery_deadline = min(deadline, started + profile.discovery_seconds)
        # Leave downstream deterministic filtering/report assembly a real slice.
        reading_deadline = min(deadline, started + max(0.0, (deadline - started) * 0.9))
        service = _BudgetedService(self.service, profile, reading_deadline)
        # A broad search may fan out to several providers for every query.
        # Preserve up to half of the same total HTTP budget (and host slots)
        # for actual bodies, redirects and observed publisher continuation.
        reserve_reading_capacity(profile.max_reads * 3)
        output = HarvestResult(profile=profile.to_dict())
        telemetry = output.read_telemetry = {"attempted": 0, "successful": 0, "failed": 0, "cached": 0,
            "total_chars_read": 0, "read_urls": [], "acquisition_attempts": [], "candidate_selection_audit": []}
        known, attempted, captured = {}, set(), set()
        upstream_ids, submitted_query_ids = {}, set()
        reference_time = datetime.now(timezone.utc)
        from backend.services.research.topic_context import infer_context
        params = getattr(request, 'extra_params', {}) or {}
        routing_context = infer_context(params.get('claim_text') or target, target, domain=domain,
            agent=agent_name, hints={**params, 'time_scope': getattr(request, 'time_scope', 'unspecified')})
        output.retrieval_trace['research_context'] = routing_context.to_dict()
        discarded = Counter()
        discovery_publishers = Counter()
        discovery_capacity = max(1, profile.max_candidates - profile.max_reads)
        generated = diversified_queries(target, domain, intent, aliases,
            specialist_tasks=specialist_tasks if specialist_task_explicit else (),
            window_hours=params.get("trending_window_hours", 48.0))
        registered = set(getattr(getattr(self.service, "registry", None), "channel_names", ()) or ())
        core_channels = {"web", "news", "rss"}
        extra_queries = []
        if query_plan:
            provided_core = [row for row in query_plan if row.get("channel", "web") in core_channels]
            generated = provided_core + generated
            # Only explicitly planned, already registered source categories.
            # Native capability/access assessment still authorizes each action.
            extra_queries = [row for row in query_plan if row.get("channel") in registered
                             and row.get("channel") not in core_channels][:2]
        if extra_queries:
            generated = generated[:max(0, profile.max_queries - len(extra_queries))] + extra_queries
        from backend.services.research.source_diversity import diversify_search_plan
        # Registered optional actions remain in their original reserved slots.
        core_limit = max(0, profile.max_queries - len(extra_queries))
        generated = diversify_search_plan([row for row in generated if row not in extra_queries],
                                         target, domain, core_limit, context=routing_context) + extra_queries
        queries, seen_queries = [], set()
        for row in generated:
            channel, text = row.get("channel", "web"), str(row.get("query_text", "")).strip()
            allowed_channels = params.get('allowed_channels')
            if allowed_channels is not None and channel not in allowed_channels:
                continue
            if channel not in core_channels | registered or not text or (channel, text.casefold()) in seen_queries:
                continue
            seen_queries.add((channel, text.casefold()))
            queries.append({**row, "channel": channel, "query_id": f"hv_q_{len(queries) + 1:03d}"})
            if len(queries) >= profile.max_queries:
                break
        for row in queries:
            output.channel_queries.setdefault(row["channel"], []).append({k: v for k, v in row.items() if k != "channel"})

        def refine_topics():
            if source_plan is None:
                return
            from backend.services.agent_reach.source_planner import source_planning_engine
            pending = [row.get('source_plan_action_id') for row in queries
                       if row['query_id'] not in submitted_query_ids]
            updates = source_planning_engine.refine_topics(source_plan, domain=domain,
                observed_titles=[item.title for item in list(known.values())[:8]], pending_action_ids=pending)
            for old, action in updates:
                row = next((r for r in queries if r.get('source_plan_action_id') == old.action_id), None)
                if row is None or row['query_id'] in submitted_query_ids:
                    continue
                # Preserve the row object/order/id held by the active scheduler.
                before = dict(row)
                row.update(query_text=action.query, query_class=action.source_category,
                    source_plan_action_id=action.action_id, source_family=action.source_family)
                output.retrieval_trace.setdefault('topic_refinement', []).append({
                    'query_id': row['query_id'], 'old_action_id': old.action_id,
                    'new_action_id': action.action_id, 'replaced_before_submission': True,
                    'source_family': action.source_family, 'network_calls': 0})
                projected = next((r for r in output.channel_queries.get(row['channel'], [])
                                  if r['query_id'] == before['query_id']), None)
                if projected is not None:
                    projected.update({k: v for k, v in row.items() if k != 'channel'})
            output.retrieval_trace['research_context'] = source_plan.research_context
            seed_publisher_directories()
        advice_trace = {"status": "DISABLED", "advisory_only": True}
        advice_checked = False

        def emit(stage):
            if progress:
                # A UI callback failure must not erase acquired evidence.
                try:
                    progress({"stage": stage, "queries_generated": len(queries), "query_records": len(output.query_records),
                              "candidate_urls": len(known), "reads_attempted": telemetry["attempted"],
                              "captures": len(output.captures), "article_bodies": sum(raw_source_type(i) == "ARTICLE_BODY" for i in output.captures)})
                except Exception:
                    pass

        def add(item):
            nonlocal raw_chars
            # Some legacy fragments strip query strings when building IDs. News
            # redirect endpoints then give unrelated articles the same ID.
            # Establish a canonical full-resource ID before any finding exists.
            from backend.services.agent_reach.native.source_discovery import resolve_bing_redirect
            original_url = item.canonical_url
            query_row = next((row for row in queries if row["query_id"] == item.query_id), {})
            query_objective = query_row.get("acquisition_objective")
            if query_row.get('source_family'):
                item.metadata['source_family'] = query_row['source_family']
                item.metadata['routing_topics'] = list(routing_context.topics)
            _merge_task_lineage(item.metadata, query_row)
            _merge_task_lineage(item.metadata, {"requested_specialist_tasks": specialist_tasks})
            parent_id = item.metadata.get("discovered_on_candidate_id")
            parent = next((candidate for candidate in known.values() if candidate.id == parent_id), None)
            if parent:
                _merge_task_lineage(item.metadata, parent.metadata)
                query_objective = query_objective or parent.metadata.get("acquisition_objective")
            if query_objective in {"PUBLIC_STATEMENT", "IDENTITY_THREAT"}:
                item.metadata["acquisition_objective"] = query_objective
            observed_url = resolve_bing_redirect(original_url)
            if observed_url != original_url:
                item.canonical_url = observed_url
                item.source_domain = _host(observed_url)
                item.metadata["observed_discovery_url"] = original_url
                item.metadata["discovery_url"] = original_url
                item.metadata["publisher_url_basis"] = "DECODED_OBSERVED_BING_REDIRECT"
            key = source_url_key(item.canonical_url)
            if item.metadata.get('read_success'):
                from backend.services.research.source_registry import source_registry
                source_registry.observe(item.canonical_url, body_acquired=raw_source_type(item) in {'ARTICLE_BODY', 'OFFICIAL_DOCUMENT'})
            if domain == "trending":
                from backend.services.research.temporal_guard import temporal_guard
                temporal = temporal_guard.evaluate(item, reference_time=reference_time,
                    window_hours=params.get("trending_window_hours", 48.0))
                item.metadata["harvest_temporal_priority"] = (0 if temporal.is_eligible else
                    1 if temporal.status == "MISSING_TIMESTAMP" else 3 if temporal.status == "FUTURE_DATED" else 2)
                item.metadata["discovery_temporal_observation"] = temporal.status
            if key in known:
                discarded["DUPLICATE_URL"] += 1
                known[key].metadata.setdefault("discovery_query_aliases", []).append(item.query_id)
                _merge_task_lineage(known[key].metadata, item.metadata)
                if (controller in {"interleaved_v1", "pipelined_v1"} and domain == "trending"
                        and item.metadata.get("harvest_temporal_priority", 9) < known[key].metadata.get("harvest_temporal_priority", 9)):
                    known[key].metadata.update(harvest_temporal_priority=item.metadata["harvest_temporal_priority"],
                        discovery_temporal_observation=item.metadata["discovery_temporal_observation"],
                        temporal_routing_basis="BEST_OBSERVED_DISCOVERY_ALIAS_NOT_BODY_VERIFICATION")
                    known[key].metadata.pop("adaptive_read_deferral", None)
                    known[key].metadata.setdefault("temporal_routing_aliases", []).append({
                        "query_id": item.query_id, "published_at": item.published_at,
                        "status": item.metadata["discovery_temporal_observation"]})
                    known[key].metadata["temporal_routing_aliases"] = known[key].metadata["temporal_routing_aliases"][-8:]
                return
            continuation = bool(item.metadata.get("observed_parent_id") or item.metadata.get("publisher_basis")
                                or item.metadata.get("discovered_on_candidate_id"))
            publisher = _observed_publisher(item)
            share_limit = max(4, discovery_capacity // 3)
            if not continuation and discovery_publishers[publisher] >= share_limit:
                discarded["PUBLISHER_DISCOVERY_SHARE_LIMIT"] += 1
                output.rejected.append({"candidate_id": item.id, "url": _locator(item.canonical_url),
                    "reason": "PUBLISHER_DISCOVERY_SHARE_LIMIT", "stage": "CANDIDATE_ADMISSION"})
                return
            limit = profile.max_candidates if continuation else discovery_capacity
            if len(known) >= limit:
                discarded["CANDIDATE_CAP" if continuation else "DISCOVERY_RESERVED_CONTINUATION_CAP"] += 1
                return
            upstream_id = item.id
            upstream_discovered_id = item.discovered_id
            item.id = "ev_hv_" + hashlib.sha256(key.encode()).hexdigest()[:20]
            item.discovered_id = "cand_disc_" + item.id
            if upstream_discovered_id and upstream_discovered_id != item.discovered_id:
                item.metadata["upstream_discovered_ids"] = [upstream_discovered_id]
                item.metadata["upstream_ids_are_citation_aliases"] = False
            if upstream_id and upstream_id != item.id:
                item.metadata["upstream_evidence_ids"] = [upstream_id]
                # These are provenance observations, never citation aliases:
                # one legacy ID can refer to several distinct resources.
                item.metadata["upstream_ids_are_citation_aliases"] = False
                previous = upstream_ids.setdefault(upstream_id, set())
                previous.add(key)
                if len(previous) > 1:
                    item.metadata["upstream_id_ambiguous"] = True
                    for previous_key in previous:
                        if previous_key in known:
                            known[previous_key].metadata["upstream_id_ambiguous"] = True
            if _is_wrapper(item) and not item.acquired_id:
                # A feed's declared publisher is an inspectable locator hint,
                # not proof that this unacquired redirect is an official filing.
                # Captured publisher bodies receive normal classification later.
                item.metadata["discovery_source_claims"] = {
                    "source_role": item.source_role, "primary_source": item.primary_source,
                    "official_source": item.official_source, "verified": False}
                item.source_role = "DISCOVERY"
                item.source_tier = "TIER_3_AGGREGATE"
                item.primary_source = item.official_source = False
                item.source_quality_score = min(item.source_quality_score, 0.5)
                item.metadata.update(source_role=item.source_role, source_tier=item.source_tier,
                    primary_source=False, official_source=False, authority_scope="DISCOVERY_ONLY",
                    publisher_identity_verified=False)
                if item.content_depth in {"PRIMARY_DOCUMENT", "REGULATORY_FILING", "OFFICIAL_STATEMENT"}:
                    item.content_depth = "INDEX_SNIPPET"
            known[key] = item
            transport = item.metadata.get('transport') or {}
            # Body-inclusive official community API responses were already read
            # during discovery. Preserve those bytes, rather than re-reading a
            # search card as an article or discarding it as social-only.
            owned = ((item.channel == 'hackernews' and _host(item.canonical_url) == 'news.ycombinator.com'
                      and item.native_backend_id == 'hn-firebase-api') or
                     (item.channel == 'stackexchange' and _host(item.canonical_url) == 'stackoverflow.com'
                      and item.native_backend_id == 'stackexchange-api'))
            observed = transport.get('http_status') == 200 or transport.get('cache_status') == 'HIT'
            if (owned and observed and item.content and item.content_depth in {'PARTIAL_CONTENT', 'COMMENT', 'SOCIAL_POST'}
                    and raw_chars + len(item.content) <= profile.max_capture_chars):
                item.content_depth = 'COMMENT' if item.content_depth == 'COMMENT' else 'SOCIAL_POST'
                item.metadata.update(read_success=True, source_role='COMMUNITY',
                    body_acquired_during_discovery=True, virality_measured=False)
                item.acquired_id = 'capture_' + hashlib.sha256(item.content.encode()).hexdigest()[:20]
                captured.add(key)
                attempted.add(key)
                raw_chars += len(item.content)
                output.captures.append(item)
            if (item.channel == 'expanded_sources' and item.native_backend_id == 'cpsc_recall_api'
                    and item.content_depth == 'STRUCTURED_PUBLIC_DATA' and item.content
                    and item.metadata.get('body_acquired_during_discovery') is True
                    and _host(item.canonical_url) == 'www.cpsc.gov'
                    and raw_chars + len(item.content) <= profile.max_capture_chars):
                item.metadata.update(read_success=True, virality_measured=False)
                item.acquired_id = 'capture_' + hashlib.sha256(item.content.encode()).hexdigest()[:20]
                captured.add(key)
                attempted.add(key)
                raw_chars += len(item.content)
                output.captures.append(item)
            item.metadata["raw_source_type"] = "FEED_ENTRY" if _is_wrapper(item) else "DISCOVERY_LEAD"
            reason = acquisition_reason(item, target, domain, aliases)
            item.metadata["harvest_acquisition_eligible"] = reason is None
            if reason:
                discarded[reason] += 1
                output.rejected.append({"candidate_id": item.id, "url": _locator(item.canonical_url), "reason": reason})
            else:
                # No pre-read date/claim/primary/quality proof is required.
                if not continuation:
                    discovery_publishers[publisher] += 1
                item.relevance_score = max(0.25, item.relevance_score)
                item.source_quality_score = max(0.25, item.source_quality_score)
                item.relevant_excerpt = ""
                for name in ("read_exclusion_reason", "defer_non_objective_read"):
                    item.metadata.pop(name, None)


        def seed_publisher_directories():
            if source_plan is None or params.get('allowed_channels') is not None and 'web' not in params['allowed_channels']:
                return
            from backend.services.research.source_registry import source_registry
            families = list(dict.fromkeys(action.source_family for action in source_plan.actions if action.source_family))[:2]
            for family in families:
                for url in source_registry.discovery_entrypoints(family)[:1]:
                    if source_url_key(url) in known:
                        continue
                    add(EvidenceItem(id='publisher_directory_' + family, canonical_url=url,
                        title='Publisher discovery directory: ' + source_registry.by_id[family]['name'],
                        channel='web', content_depth='METADATA', query_class='reviewed_publisher_directory',
                        metadata={'source_family': family, 'publisher_basis': 'VERSIONED_PUBLISHER_DIRECTORY',
                                  'discovery_kind': 'FEED_INDEX', 'publisher_hop': 0,
                                  'authority_scope': 'DISCOVERY_ONLY', 'publisher_identity_verified': False}))
                    output.retrieval_trace.setdefault('publisher_directories', []).append({
                        'source_family': family, 'url': _locator(url), 'network_calls': 0,
                        'basis': 'VERSIONED_PUBLISHER_DIRECTORY', 'not_article_evidence': True})

        seed_publisher_directories()
        wrapper_count, discovery_count, raw_chars = 0, 0, 0
        read_host_counts, read_publisher_counts = Counter(), Counter()
        adaptive_controller = None
        if controller == "interleaved_v1":
            from backend.services.research.adaptive_acquisition import InterleavedController
            from backend.infrastructure.acquisition.network.budget import configure_interleaved_discovery
            adaptive_controller = InterleavedController(target, domain, intent, reference_time)
            allocation = configure_interleaved_discovery()
            adaptive_controller.record("CONFIGURED", allocation=allocation)
        pipeline = None
        if controller == "pipelined_v1":
            # Experimental scheduler: same budgeted service, deadlines, caps and gates; see the module docstring.
            from backend.services.research.pipelined_acquisition import PipelinedAcquisition
            pipeline = PipelinedAcquisition(
                target=target, domain=domain, intent=intent, agent_name=agent_name, profile=profile, queries=queries,
                known=known, attempted=attempted, captured=captured, telemetry=telemetry, output=output,
                service=service, reader=self.reader, add=add, emit=emit, observed_children=self._observed_children,
                discarded=discarded, reference_time=reference_time, discovery_capacity=discovery_capacity,
                discovery_deadline=discovery_deadline, reading_deadline=reading_deadline,
                read_host_counts=read_host_counts, read_publisher_counts=read_publisher_counts,
                submitted_query_ids=submitted_query_ids, request=request, refine_topics=refine_topics)

        def read_available(max_additional_reads=None):
            nonlocal wrapper_count, discovery_count, raw_chars
            read_cutoff = (profile.max_reads if max_additional_reads is None else
                           min(profile.max_reads, telemetry["attempted"] + max_additional_reads))
            while time.monotonic() < reading_deadline and telemetry["attempted"] < read_cutoff:
                pending = [item for key, item in known.items() if key not in attempted
                           and item.metadata.get("harvest_acquisition_eligible") and _source_body_admissible(item)]
                # Concrete task-appropriate titles, then article-shaped paths;
                # hostname is never treated as entity/independence evidence.
                pending.sort(key=lambda item: _read_priority(item, target, domain,
                                                           read_host_counts, read_publisher_counts))
                selected, round_hosts = [], Counter()
                for item in pending:
                    if adaptive_controller:
                        deferred = adaptive_controller.defer_reason(item)
                        if deferred and item.metadata.get("source_kind") != "USER_SUPPLIED_SOURCE":
                            item.metadata["adaptive_read_deferral"] = deferred
                            continue
                        item.metadata.pop("adaptive_read_deferral", None)
                    host = _host(item.canonical_url)
                    if read_host_counts[host] >= profile.max_host_reads or round_hosts[host] >= profile.host_concurrency:
                        continue
                    if _is_wrapper(item) and wrapper_count >= profile.max_wrapper_reads:
                        continue
                    index = _is_index(item)
                    if index and discovery_count >= profile.max_discovery_reads:
                        continue
                    if len(selected) >= min(profile.concurrency, read_cutoff - telemetry["attempted"]):
                        break
                    attempted.add(source_url_key(item.canonical_url))
                    selected.append(item)
                    round_hosts[host] += 1
                    read_host_counts[host] += 1
                    read_publisher_counts[_observed_publisher(item)] += 1
                    wrapper_count += int(_is_wrapper(item))
                    discovery_count += int(index)
                if not selected:
                    # Three opaque redirect attempts must not prevent an
                    # already observed alternate publisher from receiving a
                    # bounded hub/feed opportunity. Reserve one remaining slot
                    # for an article found there; never guess an article URL.
                    remaining_reads = profile.max_reads - telemetry["attempted"]
                    remaining_indexes = profile.max_discovery_reads - discovery_count
                    if (wrapper_count >= profile.max_wrapper_reads
                            and remaining_reads > 1 and remaining_indexes > 0):
                        hubs = _unread_wrapper_hubs(pending, [i.canonical_url for i in known.values()],
                                                   min(2, remaining_indexes, remaining_reads - 1))
                        previous_count = len(known)
                        for hub in hubs:
                            add(hub)
                        if len(known) > previous_count:
                            continue
                    break
                window = min(profile.read_window_seconds, max(0.0, reading_deadline - time.monotonic()))
                if adaptive_controller:
                    adaptive_controller.record("READ_BATCH", candidate_ids=[item.id for item in selected],
                        attempt_count_before=telemetry["attempted"], attempt_cap=profile.max_reads)
                captures, observed = self.reader.deep_read(selected, max_reads=len(selected), timeout_per_read=window,
                                                         service=service, max_concurrency=profile.concurrency)
                for name in ("attempted", "successful", "failed", "cached", "total_chars_read"):
                    telemetry[name] += observed.get(name, 0)
                for name in ("read_urls", "acquisition_attempts", "candidate_selection_audit"):
                    telemetry[name].extend(observed.get(name, []))
                for item in captures:
                    key = source_url_key(item.canonical_url)
                    if key in captured:
                        continue
                    if raw_chars + len(item.content) > profile.max_capture_chars:
                        discarded["RAW_CAPTURE_STORAGE_CAP"] += 1
                        continue
                    captured.add(key)
                    raw_chars += len(item.content)
                    item.metadata["raw_source_type"] = raw_source_type(item)
                    item.metadata["qualification_status"] = "PENDING"
                    output.captures.append(item)
                    if adaptive_controller:
                        adaptive_controller.observe(item)
                    for child in self._observed_children(item, target, domain, output.rejected):
                        add(child)
                # Feed-declared hubs are observed fallbacks after failed opaque
                # wrapper resolution, never guessed /news or article slugs.
                from backend.services.research.publisher_links import failed_feed_publisher_hubs
                for hub in failed_feed_publisher_hubs(selected, observed.get("acquisition_attempts", []),
                                                       {i.canonical_url for i in known.values()}):
                    add(hub)
                emit("HARVEST_READING")
                if raw_chars >= profile.max_capture_chars or not observed.get("attempted"):
                    break

        if source_url:
            add(EvidenceItem(id="explicit_source", canonical_url=str(source_url), title="User-supplied source",
                channel="web", query_id="user_source", query_class="explicit_source", query_text=str(target),
                metadata={"source_kind": "USER_SUPPLIED_SOURCE", "acquisition_scope": "EXTERNALLY_SUPPLIED_SOURCE",
                          "autonomously_discovered": False}))
        for item in initial_candidates:
            add(copy.deepcopy(item))
        emit("HARVEST_DISCOVERY")
        try:
            # Small provider-bulkheaded waves rather than one giant worker queue.
            wave_size = 3 if adaptive_controller else min(6, max(3, profile.max_queries // 2))
            for offset in (range(0, len(queries), wave_size) if pipeline is None else ()):
                if time.monotonic() >= discovery_deadline or len(known) >= discovery_capacity:
                    if adaptive_controller:
                        output.retrieval_trace["discovery_stop_reason"] = ("DISCOVERY_DEADLINE_EXHAUSTED"
                            if time.monotonic() >= discovery_deadline else "DISCOVERY_CANDIDATE_CAP_REACHED")
                    break
                pending_opportunities = ([item for key, item in known.items() if key not in attempted
                    and item.metadata.get("harvest_acquisition_eligible") and not adaptive_controller.defer_reason(item)]
                    if adaptive_controller else [])
                remaining_planned_actions = any(row.get("source_plan_action_id") for row in queries[offset:])
                if (adaptive_controller and offset > 0 and adaptive_controller.enough_for_discovery_pause()
                        and not remaining_planned_actions
                        and len(pending_opportunities) >= profile.max_reads - telemetry["attempted"]):
                    output.retrieval_trace["discovery_stop_reason"] = "USABLE_CAPTURED_PASSAGES_PAUSE_DISCOVERY"
                    adaptive_controller.record("PAUSE_DISCOVERY_FOR_CAPTURED_COVERAGE")
                    break
                if discovery_http_remaining() == 0:
                    if adaptive_controller and offset > 0:
                        from backend.infrastructure.acquisition.network.budget import release_adaptive_discovery
                        granted = release_adaptive_discovery()
                        adaptive_controller.record("RELEASE_ADAPTIVE_DISCOVERY", admissions_granted=granted,
                            after_read_attempts=telemetry["attempted"],
                            scope="Released cumulative credit after bounded read selection; not provider success")
                    if discovery_http_remaining() == 0:
                        output.retrieval_trace["discovery_stop_reason"] = "DISCOVERY_HTTP_RESERVE_FOR_READING"
                        break
                if offset > 0:
                    task_covered_publishers = {
                        _host(item.canonical_url) for item in known.values()
                        if item.metadata.get("harvest_acquisition_eligible")
                        and matches_objective((item.title or "") + " " + (item.snippet or ""), domain)
                        and (str(target).casefold() in (item.title or "").casefold() or str(target).casefold() in item.canonical_url.casefold())
                    }
                    task_covered_publishers.discard("")
                    task_covered_publishers.discard("news.google.com")
                    if len(task_covered_publishers) >= 2:
                        output.retrieval_trace["staged_query_planning"] = {
                            "reason": "LEADS_ONLY_CONTINUE_BOUNDED_DISCOVERY",
                            "covered_publishers": sorted(task_covered_publishers),
                            "waves_executed": offset // wave_size,
                            "waves_skipped_for_lead_coverage": 0,
                            "acquired_evidence_coverage_established": False,
                        }
                        # These are title/snippet observations, not acquired
                        # articles. Both may later be blocked or irrelevant.
                        # Continue the original bounded discovery allocation;
                        # never let attractive leads suppress all alternatives.
                plan = {}
                for row in queries[offset:offset + wave_size]:
                    plan.setdefault(row["channel"], []).append({k: v for k, v in row.items() if k != "channel"})
                if adaptive_controller:
                    adaptive_controller.record("DISCOVERY_WAVE", query_ids=[row["query_id"] for row in queries[offset:offset + wave_size]],
                        read_attempts_before=telemetry["attempted"], remaining_http_discovery=discovery_http_remaining())
                remaining = discovery_deadline - time.monotonic()
                wave_timeout = min(20.0, remaining)
                try:
                    submitted_query_ids.update(row["query_id"] for rows in plan.values() for row in rows)
                    with public_request_phase("discovery"):
                        result = service.retrieve_many(plan, domain=domain, agent_name=agent_name,
                            target_name=target, timeout=wave_timeout, budget={"max_queries_per_channel": max(len(rows) for rows in plan.values()),
                            "max_results_per_query": profile.results_per_query,
                            "max_total_evidence": min(profile.max_candidates, 6 * profile.results_per_query),
                            "max_deep_reads": 0, "channel_timeout": min(15.0, wave_timeout)})
                    output.query_records.extend(result.query_records)
                    output.channel_health.update(result.channel_health)
                    output.retrieval_trace.setdefault("discovery_waves", []).append(result.retrieval_trace or {})
                    for fragment in result.fragments:
                        url = getattr(fragment, "url", "") or ""
                        item_id = getattr(fragment, "evidence_id", "") or "ev_" + hashlib.sha256(source_url_key(url).encode()).hexdigest()[:16]
                        add(EvidenceItem.from_evidence_fragment(fragment, item_id=item_id, target_name=target))
                except Exception as exc:
                    discarded["SEARCH_" + type(exc).__name__.upper()] += 1
                    # Preserve each generated query's transport failure, rather
                    # than leaving an empty record list that resembles no-results.
                    from backend.services.agent_reach.channels import QueryExecutionRecord
                    for channel, rows in plan.items():
                        for row in rows:
                            output.query_records.append(QueryExecutionRecord(query_id=row["query_id"],
                                channel=channel, query_text=row["query_text"], query_class=row.get("query_class", "general"),
                                status="TIMEOUT" if isinstance(exc, TimeoutError) else "FAILED",
                                error="Harvester transport exception: " + type(exc).__name__,
                                result_count_raw=0, result_count_normalized=0))
                refine_topics()
                emit("HARVEST_DISCOVERY")
                if adaptive_controller:
                    before_reads = telemetry["attempted"]
                    reading_started = time.monotonic()
                    read_available(min(4, profile.max_reads - telemetry["attempted"]))
                    # Time spent reading must not silently consume the active
                    # discovery allowance. The original overall/read deadline
                    # remains fixed and a final read slice stays reserved.
                    discovery_deadline = min(reading_deadline - min(10.0, max(0.0, reading_deadline - started) * .1),
                        discovery_deadline + max(0.0, time.monotonic() - reading_started))
                    adaptive_controller.record("READ_OPPORTUNITY_COMPLETE",
                        attempted=telemetry["attempted"] - before_reads,
                        deferrals=dict(Counter(item.metadata["adaptive_read_deferral"] for item in known.values()
                            if item.metadata.get("adaptive_read_deferral"))))
                    if (request is not None and not advice_checked
                            and os.getenv("AEGIS_SEARCH_ADVISOR_ENABLED", "false").lower() in {"1", "true"}
                            and reading_deadline - time.monotonic() >= 3):
                        advice_checked = True
                        from backend.services.research.search_advice import expand_with_advice
                        if discovery_http_remaining() == 0:
                            from backend.infrastructure.acquisition.network.budget import release_adaptive_discovery
                            granted = release_adaptive_discovery()
                            adaptive_controller.record("RELEASE_ADAPTIVE_DISCOVERY", admissions_granted=granted,
                                after_read_attempts=telemetry["attempted"], purpose="BOUNDED_SEARCH_ADVICE")
                        if discovery_http_remaining() != 0:
                            with public_request_phase("discovery"):
                                advice_result, advice_trace = expand_with_advice(request,
                                    [item for item in known.values() if item.metadata.get("harvest_acquisition_eligible")],
                                    service, min(6.0, reading_deadline - time.monotonic()),
                                    capture_feedback=adaptive_controller.feedback)
                            adaptive_controller.record("SEARCH_ADVICE", status=advice_trace.get("status"),
                                query_count=advice_trace.get("query_count", 0))
                            if advice_result is not None:
                                output.query_records.extend(advice_result.query_records)
                                output.channel_health.update(advice_result.channel_health)
                                for fragment in advice_result.fragments:
                                    url = getattr(fragment, "url", "") or ""
                                    item_id = getattr(fragment, "evidence_id", "") or "ev_" + hashlib.sha256(source_url_key(url).encode()).hexdigest()[:16]
                                    add(EvidenceItem.from_evidence_fragment(fragment, item_id=item_id, target_name=target))
                    if telemetry["attempted"] >= profile.max_reads:
                        output.retrieval_trace["discovery_stop_reason"] = "SHARED_READ_ATTEMPT_CAP"
                        break

            if (adaptive_controller is None and pipeline is None and request is not None
                    and discovery_deadline - time.monotonic() >= 2 and discovery_http_remaining() != 0):
                from backend.services.research.search_advice import expand_with_advice
                with public_request_phase("discovery"):
                    advice_result, advice_trace = expand_with_advice(request,
                        [item for item in known.values() if item.metadata.get("harvest_acquisition_eligible")],
                        service, discovery_deadline - time.monotonic())
                if advice_result is not None:
                    output.query_records.extend(advice_result.query_records)
                    output.channel_health.update(advice_result.channel_health)
                    for fragment in advice_result.fragments:
                        url = getattr(fragment, "url", "") or ""
                        item_id = getattr(fragment, "evidence_id", "") or "ev_" + hashlib.sha256(source_url_key(url).encode()).hexdigest()[:16]
                        add(EvidenceItem.from_evidence_fragment(fragment, item_id=item_id, target_name=target))

            if pipeline is not None:
                try:
                    pipeline.run()
                finally:
                    wrapper_count, discovery_count, raw_chars = pipeline.wrapper_count, pipeline.index_count, pipeline.raw_chars
            else:
                read_available()

        finally:
            service.close()

        # Every admitted but unread lead needs a concrete disposition. An
        # exhausted wrapper allowance is not a failed publisher request, nor
        # evidence that the source has no relevant content.
        unread_reasons = Counter()
        for key, item in known.items():
            if key in attempted or not item.metadata.get("harvest_acquisition_eligible"):
                continue
            permission = item.metadata.get('source_body_admission') or {}
            policy_blocked = permission.get('eligible') is False
            reason = (permission.get('reason') or permission.get('status') if policy_blocked else
                      "READ_DEADLINE_EXHAUSTED" if time.monotonic() >= reading_deadline else
                      "READ_ATTEMPT_BUDGET_EXHAUSTED" if telemetry["attempted"] >= profile.max_reads else
                      "HOST_READ_BUDGET_EXHAUSTED" if read_host_counts[_host(item.canonical_url)] >= profile.max_host_reads else
                      "WRAPPER_READ_BUDGET_EXHAUSTED" if _is_wrapper(item) and wrapper_count >= profile.max_wrapper_reads else
                      "DISCOVERY_READ_BUDGET_EXHAUSTED" if _is_index(item) and discovery_count >= profile.max_discovery_reads else
                      item.metadata.get("adaptive_read_deferral") or "NO_READER_PROGRESS")
            unread_reasons[reason] += 1
            item.metadata["harvest_unread_reason"] = reason
            telemetry["candidate_selection_audit"].append({"candidate_id": item.id,
                "selected": False, "eligible_for_read": not policy_blocked, "selection_decision": "NOT_SELECTED",
                "selection_reason": reason, "rejection_reason": reason if policy_blocked else None})

        # Planning, submission and transport observations are distinct states.
        # Do not silently omit generated queries when an early cap/deadline wins.
        from backend.services.agent_reach.channels import QueryExecutionRecord
        recorded_ids = {getattr(row, "query_id", None) if not isinstance(row, dict) else row.get("query_id")
                        for row in output.query_records}
        for row in queries:
            if row["query_id"] in recorded_ids:
                continue
            submitted = row["query_id"] in submitted_query_ids
            reason = ("DISPATCHED_QUERY_RECORD_UNAVAILABLE" if submitted else output.retrieval_trace.get("discovery_stop_reason") or (
                      "DISCOVERY_HTTP_RESERVE_FOR_READING" if discovery_http_remaining() == 0 else
                      "DISCOVERY_CANDIDATE_CAP_REACHED" if len(known) >= discovery_capacity else
                      "DISCOVERY_DEADLINE_EXHAUSTED"))
            output.query_records.append(QueryExecutionRecord(query_id=row["query_id"], channel=row["channel"],
                query_text=row["query_text"], query_class=row.get("query_class", "general"), phase="harvesting",
                status="UNRECORDED" if submitted else "NOT_SUBMITTED", provider_started=None if submitted else False,
                error=reason, result_count_raw=0, result_count_normalized=0))

        output.candidates = list(known.values())
        failures = Counter(row.get("failure_kind") or "UNKNOWN" for row in telemetry["acquisition_attempts"] if row.get("status") != "SUCCESS")
        bodies = [item for item in output.captures if raw_source_type(item) in {"ARTICLE_BODY", "OFFICIAL_DOCUMENT"}]
        output.metrics = {"profile": profile.name, "queries_generated": len(queries),
            "query_records": len(output.query_records), "search_query_reservations": service.search_query_reservations,
            "candidate_urls_discovered": len(known), "candidates_accepted_for_read": sum(bool(i.metadata.get("harvest_acquisition_eligible")) for i in known.values()),
            "discarded_by_reason": dict(discarded), "reads_attempted": telemetry["attempted"],
            "read_service_starts": service.actual_read_starts, "captures": len(output.captures),
            "article_bodies": len(bodies), "raw_article_words": sum(len(i.content.split()) for i in bodies),
            "raw_capture_chars": sum(len(i.content) for i in output.captures),
            "observed_publisher_hosts": len({_host(i.canonical_url) for i in bodies}),
            "independence_verified": False, "failure_categories": dict(failures),
            "eligible_candidates_unread": sum(unread_reasons.values()), "unread_by_reason": dict(unread_reasons),
            "service_operations_reserved": service.operations, "service_operation_cap": profile.max_operations,
            "host_read_reservations": dict(service.host_reads), "host_queue_wait_ms": round(service.host_wait_ms, 2),
            "duration_seconds": round(time.monotonic() - started, 3), "deadline_exhausted": time.monotonic() >= reading_deadline,
            "qualification_status": "PENDING_SECOND_LAYER", "provider_http_request_count": None,
            "ai_search_advice": advice_trace}
        output.metrics["user_supplied_source_count"] = sum(item.metadata.get("source_kind") == "USER_SUPPLIED_SOURCE" for item in known.values())
        output.metrics["source_diversity"] = {
            "planned_families": list(dict.fromkeys(row["source_family"] for row in queries if row.get("source_family"))),
            "submitted_families": list(dict.fromkeys(row["source_family"] for row in queries
                if row.get("source_family") and row["query_id"] in submitted_query_ids)),
            "observed_candidate_hosts": sorted({_observed_publisher(item) for item in known.values()} - {""})[:120],
            "read_publisher_reservations": dict(read_publisher_counts),
            "scope": "Discovery hints and host groups, not authenticated publishers or independent confirmation",
            "catalog_live_health": "UNVERIFIED",
            "discovery_publisher_share_limit": max(4, discovery_capacity // 3),
            "eligible_discovery_by_observed_publisher": dict(discovery_publishers),
        }
        output.metrics["autonomously_discovered_article_bodies"] = sum(item.metadata.get("acquisition_scope") != "EXTERNALLY_SUPPLIED_SOURCE" for item in bodies)
        specialist_rows = [row for row in queries if row.get("source_plan_action_id")]
        if specialist_rows:
            output.metrics["specialist_action_admission"] = {
                "planned_action_ids": [row["source_plan_action_id"] for row in specialist_rows],
                "submitted_action_ids": [row["source_plan_action_id"] for row in specialist_rows
                                         if row["query_id"] in submitted_query_ids],
                "scope": "Submission is not provider start, acquisition success or evidence qualification",
            }
        if adaptive_controller:
            output.metrics["acquisition_controller"] = adaptive_controller.snapshot()
        elif pipeline is not None:
            output.metrics["acquisition_controller"] = pipeline.snapshot()
            output.metrics["ai_search_advice"] = pipeline.advice_trace
        emit("HARVEST_COMPLETE")
        return output

    @staticmethod
    def _observed_children(parent, target, domain, audit):
        """Use one admission path for observed index links and source citations."""
        page = parent.metadata.get("page_metadata") or {}
        kind = page.get("body_kind") or (page.get("body_quality") or {}).get("body_kind")
        if (not parent.metadata.get("read_success") or parent.metadata.get("publisher_hop", 0) >= 3
                or not (_is_index(parent) or kind == "ARTICLE_BODY")):
            return []
        from backend.services.research.publisher_links import observed_publisher_articles
        observations = []
        children = observed_publisher_articles(parent, domain, observations, target=target,
                                                max_children=24, max_hops=3)
        audit.extend(row for row in observations if row.get("discard_reason"))
        for child in children:
            child.metadata["observed_parent_id"] = parent.id
            _merge_task_lineage(child.metadata, parent.metadata)
            if parent.metadata.get("acquisition_objective") == "PUBLIC_STATEMENT":
                child.metadata["acquisition_objective"] = "PUBLIC_STATEMENT"
            if parent.metadata.get("acquisition_scope") == "EXTERNALLY_SUPPLIED_SOURCE":
                child.metadata["acquisition_scope"] = "EXTERNALLY_SUPPLIED_SOURCE"
                child.metadata["autonomously_discovered"] = False
        return children
