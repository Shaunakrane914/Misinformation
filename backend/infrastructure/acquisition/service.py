"""
Aegis Protocol — Agent Reach Service & Adapter
================================================
Central internet evidence-acquisition capability layer for Aegis.
Owns channel coordination, bounded concurrent retrieval, deduplication,
source independence clustering, and SSRF-hardened reading.
Preserves full backward compatibility with the legacy AgentReachScraper.
"""

import concurrent.futures
import logging
import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.agent_reach.channels import (
    CandidateSource,
    Channel,
    ChannelStatus,
    ChannelTelemetry,
    EvidenceFragment,
    FetchedDocument,
    QueryExecutionRecord,
    RetrievalRequest,
    RetrievalResult,
    RetrievalTrace,
)
from backend.services.agent_reach.channels_impl import (
    AuthenticatedOptionalChannel,
    BilibiliChannel,
    GitHubChannel,
    JinaReaderChannel,
    NewsChannel,
    RedditChannel,
    RssChannel,
    TwitterChannel,
    V2EXChannel,
    WebChannel,
    YouTubeChannel,
)
from backend.services.agent_reach.native import (
    CAPABILITY_MATRIX,
    get_runtime_profile,
    get_upstream_info,
    native_doctor,
    native_router,
)
from backend.services.agent_reach.planner import RetrievalPlan, RetrievalPlanner
from backend.services.agent_reach.source_planner import (
    EXECUTABLE_CAPABILITIES,
    SourcePlanningEngine,
)
from backend.services.agent_reach.registry import CapabilityRegistry
from backend.infrastructure.acquisition.security.url_validator import is_safe_url

logger = logging.getLogger(__name__)

# Known news wire syndication signatures for source-independence clustering
SYNDICATION_MARKERS = [
    "reuters", "associated press", "ap news", "bloomberg",
    "pr newswire", "business wire", "globe newswire", "afp",
]


class AgentReachService:
    """
    Canonical internet evidence acquisition service.

    Orchestrates retrieval across heterogeneous channels (web, news, social,
    video, code repositories), enforces timeout budgets, sanitizes external
    inputs, normalizes fragments, and detects syndication clusters.
    """

    def __init__(self):
        self.registry = CapabilityRegistry()
        self.planner = RetrievalPlanner()
        self.source_planner = SourcePlanningEngine()
        self._register_default_channels()
        logger.info("[AgentReachService] Initialized with Native Agent Reach 3.0 capability backbone")

    def _register_default_channels(self) -> None:
        """Register primary zero-config channels and optional authenticated channels."""
        # Core zero-config channels (cloud-ready & native tools)
        self.registry.register(NewsChannel())
        self.registry.register(WebChannel())
        self.registry.register(RssChannel())
        self.registry.register(V2EXChannel())
        self.registry.register(BilibiliChannel())
        self.registry.register(GitHubChannel())
        self.registry.register(YouTubeChannel())
        self.registry.register(JinaReaderChannel())
        self.registry.register(RedditChannel())
        self.registry.register(TwitterChannel())

        # Optional / authenticated channels (gracefully report status)
        self.registry.register(AuthenticatedOptionalChannel("linkedin", "LinkedIn", "LINKEDIN_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("xueqiu", "Xueqiu", "XUEQIU_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("xiaohongshu", "Xiaohongshu", "XIAOHONGSHU_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("instagram", "Instagram", "INSTAGRAM_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("facebook", "Facebook", "FACEBOOK_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("boss", "Boss直聘", "BOSS_CDP_PORT"))
        self.registry.register(AuthenticatedOptionalChannel("xiaoyuzhou", "Xiaoyuzhou", "GROQ_API_KEY"))

    # ── Diagnostics & Capabilities ──────────────────────────────────────────

    def capabilities(self) -> Dict[str, Any]:
        """Return the complete channel capability inventory and server compatibility status."""
        upstream = get_upstream_info()
        doctor_status = native_doctor.check_all()
        cap_map = self.registry.capability_map()
        available_count = sum(1 for c in cap_map.values() if c["status"] == ChannelStatus.AVAILABLE.value)

        native_channels = {}
        for plat, cap in CAPABILITY_MATRIX.items():
            doc_entry = native_doctor.get_channel_status(plat)
            registered = plat in self.registry.channel_names
            status_code = native_doctor.get_canonical_status_code(plat) if registered else "UNAVAILABLE"
            active_b = doc_entry.get("active_backend")
            native_channels[plat] = {
                "status": status_code,
                "backend": active_b,
                "operations": sorted(EXECUTABLE_CAPABILITIES.get(plat, set())) if registered else [],
                "declared_operations": sorted(list(cap.operations)),
                "registered": registered,
                "implementation_status": "IMPLEMENTED" if registered else "NOT_IMPLEMENTED",
                "tier": cap.tier,
                "cloud_safe": cap.cloud_safe,
                "health_class": doc_entry.get("health_class", "UNVERIFIED"),
                "last_operation_outcome": doc_entry.get("outcome"),
                "last_verified_at": doc_entry.get("last_verified_at"),
            }

        # Runtime aliases are part of the actual service even though they are
        # absent from the upstream 16-platform declaration.
        for plat in ("news", "jina_reader"):
            doc_entry = native_doctor.get_channel_status(plat)
            native_channels[plat] = {
                "status": native_doctor.get_canonical_status_code(plat),
                "backend": doc_entry.get("active_backend"),
                "operations": sorted(EXECUTABLE_CAPABILITIES.get(plat, set())),
                "declared_operations": [],
                "registered": True,
                "implementation_status": "IMPLEMENTED_RUNTIME_ALIAS",
                "tier": 0,
                "cloud_safe": True,
                "health_class": doc_entry.get("health_class", "UNVERIFIED"),
                "last_operation_outcome": doc_entry.get("outcome"),
                "last_verified_at": doc_entry.get("last_verified_at"),
            }

        return {
            "runtime": upstream["runtime"],
            "agent_reach": {
                "installed": upstream["installed"],
                "version": upstream["version"],
                "commit": upstream["commit"],
                "doctor_timestamp": datetime.utcnow().isoformat(),
            },
            "channels": native_channels,
            # Backwards compatibility keys
            "service": "AgentReachService",
            "version": upstream["version"],
            "total_channels": len(native_channels),
            "available_channels": available_count,
            "legacy_channels_map": cap_map,
            "supported_domains": list(self.planner.DOMAIN_PRIORITIES.keys()),
        }

    def health(self) -> Dict[str, Any]:
        """Probe all registered channels and return a structured health report."""
        discovery = self.registry.discover()
        healthy = sum(1 for s in discovery.values() if s == ChannelStatus.AVAILABLE.value)
        degraded = sum(1 for s in discovery.values() if s == ChannelStatus.DEGRADED.value)
        auth_req = sum(1 for s in discovery.values() if s == ChannelStatus.AUTH_REQUIRED.value)
        unavail = sum(1 for s in discovery.values() if s == ChannelStatus.UNAVAILABLE.value)
        return {
            "status": "HEALTHY" if healthy >= 3 else "DEGRADED",
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "healthy": healthy,
                "degraded": degraded,
                "auth_required": auth_req,
                "unavailable": unavail,
            },
            "channels": discovery,
        }

    # ── Safe Content Reading ────────────────────────────────────────────────

    def read(self, url: str, max_chars: int = 4000) -> Dict[str, Any]:
        """
        Safely fetch and parse a web document into clean markdown.
        Routes through native_router with SSRF validation and structured fallback.
        """
        return native_router.execute_channel_read(url, max_chars=max_chars)

    # ── Core Retrieval Pipeline ─────────────────────────────────────────────

    def search_channel(self, channel_name: str, query: str, limit: int = 6) -> List[EvidenceFragment]:
        """Execute a targeted search on a single channel through native_router."""
        channel = self.registry._channels.get(channel_name)
        if not channel:
            logger.warning(f"[AgentReachService] Channel '{channel_name}' not registered")
            return []
        try:
            frags, _ = native_router.execute_channel_query(channel_name, query, limit=limit)
            return frags
        except Exception as e:
            logger.warning(f"[AgentReachService] Channel '{channel_name}' search failed: {e}")
            self.registry.mark_degraded(channel_name)
            return []

    def execute(self, request: RetrievalRequest) -> List[EvidenceFragment]:
        """
        Canonical acquisition entrypoint for domain agents.
        Acquires evidence through the unified acquisition fabric.
        """
        claim = " ".join(
            part for part in (request.query, request.intent) if part
        )
        source_plan = self.source_planner.plan(
            claim,
            entity=request.entity,
            domain=request.metadata.get("domain", request.agent or "general"),
            agent=request.agent,
            allowed_channels=request.allowed_channels or None,
        )
        request.metadata["source_plan"] = source_plan.to_dict()
        if source_plan.channels:
            if request.allowed_channels:
                planned = [ch for ch in source_plan.channels if ch in request.allowed_channels]
                request.allowed_channels = planned or request.allowed_channels
            else:
                request.allowed_channels = source_plan.channels
        return native_router.execute_retrieval_request(request)

    def retrieve(
        self,
        request_or_query: Any = None,
        query: Optional[str] = None,
        domain: str = "general",
        channels: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        limit_per_channel: int = 6,
        timeout: float = 12.0,
        **kwargs: Any,
    ) -> RetrievalResult:
        """
        Universal, domain-planned evidence retrieval entrypoint.
        Polymorphic: Accepts either a typed RetrievalRequest or query string.
        """
        target = request_or_query if request_or_query is not None else query
        if isinstance(target, RetrievalRequest):
            frags = self.execute(target)
            return RetrievalResult(
                query=target.query or target.entity,
                domain=target.agent,
                fragments=frags,
                total_signals=len(frags),
            )

        clean_q = str(target or "").strip()
        plan = self.planner.plan(clean_q, domain=domain, include_channels=channels)
        logger.info(f"[AgentReachService] Executing retrieve for '{clean_q[:40]}...' (domain={domain}): channels={plan.channels_to_query}")

        # If multi_channel_queries are available from plan, use retrieve_many
        if plan.multi_channel_queries:
            active_queries = plan.multi_channel_queries
            if channels:
                active_queries = {ch: q_list for ch, q_list in active_queries.items() if ch in channels}

            return self.retrieve_many(
                channel_queries=active_queries,
                domain=domain,
                agent_name="agent_reach",
                target_name=clean_q,
                source_url=source_url,
                budget={
                    "max_queries_per_channel": kwargs.get("max_queries_per_channel", 3),
                    "max_results_per_query": limit_per_channel,
                    "max_total_evidence": kwargs.get("max_total_evidence", 40),
                    "max_deep_reads": kwargs.get("max_deep_reads", 4),
                },
                perform_reads=kwargs.get("perform_reads", True),
                timeout=timeout,
            )

        # Fallback to single-query per channel
        single_query_matrix = {
            ch: [{"query_id": f"{ch}_01", "query_class": "general", "query_text": plan.domain_queries.get(ch, clean_q)}]
            for ch in plan.channels_to_query
        }
        return self.retrieve_many(
            channel_queries=single_query_matrix,
            domain=domain,
            agent_name="agent_reach",
            target_name=clean_q,
            source_url=source_url,
            budget={
                "max_queries_per_channel": 1,
                "max_results_per_query": limit_per_channel,
                "max_total_evidence": 30,
                "max_deep_reads": 3,
            },
            perform_reads=kwargs.get("perform_reads", True),
            timeout=timeout,
        )

    def retrieve_many(
        self,
        channel_queries: Dict[str, List[Any]],
        domain: str = "general",
        agent_name: str = "agent",
        target_name: str = "",
        source_url: Optional[str] = None,
        budget: Optional[Dict[str, Any]] = None,
        perform_reads: bool = True,
        timeout: float = 12.0,
    ) -> RetrievalResult:
        """
        Execute bounded concurrent multi-query retrieval across channels with full tracing.

        Enforces:
        - Query planning metrics (classes created, queries generated, queries executed)
        - Bounded concurrent worker execution across (channel_name, query_spec)
        - Per-channel telemetry (queries attempted, requests attempted, successful, raw,
          normalized, duplicates, final, latency_ms, status, failure_reason)
        - Non-destructive deduplication preserving distinct evidence angles
        - Deep reading pass for top high-value primary URLs
        - Source independence clustering & semantic role attribution
        - Full RetrievalTrace telemetry construction
        """
        import time
        start_ts = time.time()
        budget = budget or {}
        max_q_per_ch = budget.get("max_queries_per_channel", 3)
        max_res_per_q = budget.get("max_results_per_query", 5)
        max_total_ev = budget.get("max_total_evidence", 40)
        max_deep_reads = budget.get("max_deep_reads", 4)
        task_timeout = budget.get("channel_timeout", min(timeout, 8.0))

        # 1. Normalize query specs
        normalized_channel_queries: Dict[str, List[Dict[str, str]]] = {}
        all_query_classes: Set[str] = set()
        total_planned_queries = 0

        for ch_name, q_list in channel_queries.items():
            norm_list = []
            for idx, q_item in enumerate(q_list):
                if isinstance(q_item, dict):
                    q_id = q_item.get("query_id", f"{ch_name[:2]}_{idx+1:02d}")
                    q_class = q_item.get("query_class", "general")
                    q_text = q_item.get("query_text", "")
                    operation = q_item.get("operation", "search")
                else:
                    q_id = f"{ch_name[:2]}_{idx+1:02d}"
                    q_class = "general"
                    q_text = str(q_item)
                    operation = "search"

                if q_text.strip():
                    norm_list.append({
                        "query_id": q_id,
                        "query_class": q_class,
                        "query_text": q_text.strip(),
                        "operation": operation,
                    })
                    all_query_classes.add(q_class)
                    total_planned_queries += 1

            if norm_list:
                normalized_channel_queries[ch_name] = norm_list[:max_q_per_ch]

        # 2. Source Article Reading (if provided)
        source_doc = None
        if source_url:
            source_doc = self.read(source_url)

        # 3. Channel Telemetry Setup
        channel_telemetry_map: Dict[str, ChannelTelemetry] = {}
        for ch_name in self.registry.channel_names:
            ch_status = self.registry.get_status(ch_name).value
            channel_telemetry_map[ch_name] = ChannelTelemetry(
                channel=ch_name,
                status=ch_status,
                queries_attempted=[],
            )

        # Prepare execution tasks and query execution records
        tasks = []  # (ch_name, channel_obj, query_spec)
        available_channels = {c.name: c for c in self.registry.get_available()}
        query_records_map: Dict[str, QueryExecutionRecord] = {}

        for ch_name, queries in normalized_channel_queries.items():
            telemetry = channel_telemetry_map.setdefault(ch_name, ChannelTelemetry(channel=ch_name))
            telemetry.queries_attempted = [q["query_text"] for q in queries]
            telemetry.requests_attempted = len(queries)

            st_info = native_doctor.get_channel_status(ch_name)
            backend_id = st_info.get("active_backend") or ch_name

            if ch_name not in available_channels:
                telemetry.failure_reason = f"Channel {ch_name} status is {telemetry.status}"
                for q_spec in queries:
                    rec = QueryExecutionRecord(
                        query_id=q_spec["query_id"],
                        channel=ch_name,
                        query_text=q_spec["query_text"],
                        query_class=q_spec["query_class"],
                        phase="initial",
                        status="SKIPPED",
                        started_at=datetime.utcnow().isoformat(),
                        completed_at=datetime.utcnow().isoformat(),
                        latency_ms=0,
                        result_count_raw=0,
                        result_count_normalized=0,
                        error=f"Channel {ch_name} status is {telemetry.status}",
                        retrieval_mode="skipped",
                        backend_id=backend_id,
                    )
                    query_records_map[q_spec["query_id"]] = rec
                continue

            channel_obj = available_channels[ch_name]
            for q_spec in queries:
                tasks.append((ch_name, channel_obj, q_spec))

        # 4. Concurrent execution with bounded concurrency
        raw_fragments: List[EvidenceFragment] = []
        executed_queries_count = 0

        def _run_single_query(task_tuple) -> Tuple[str, List[EvidenceFragment], int, Optional[str], QueryExecutionRecord]:
            ch_n, ch_obj, q_sp = task_tuple
            started_at = datetime.utcnow().isoformat()
            t0 = time.time()
            st_info = native_doctor.get_channel_status(ch_n)
            backend_id = st_info.get("active_backend") or ch_n
            try:
                frags = ch_obj.search(
                    q_sp["query_text"],
                    limit=max_res_per_q,
                    query_id=q_sp["query_id"],
                    query_class=q_sp["query_class"],
                    query_text=q_sp["query_text"],
                    domain=domain,
                    operation=q_sp.get("operation", "search"),
                )
                completed_at = datetime.utcnow().isoformat()
                lat = int((time.time() - t0) * 1000)
                for f in frags or []:
                    if not getattr(f, "query_id", "") and q_sp.get("query_id"):
                        f.query_id = q_sp["query_id"]
                    if not getattr(f, "query_class", "") and q_sp.get("query_class"):
                        f.query_class = q_sp["query_class"]
                    if not getattr(f, "query_text", "") and q_sp.get("query_text"):
                        f.query_text = q_sp["query_text"]
                    if not getattr(f, "channel_name", ""):
                        f.channel_name = ch_n
                    if not getattr(f, "requested_channel", ""):
                        f.requested_channel = ch_n
                    if not getattr(f, "actual_retrieval_channel", ""):
                        f.actual_retrieval_channel = f.channel_name or ch_n
                    # Update initial lineage record if needed
                    for lin in getattr(f, "retrieval_lineage", []):
                        if not lin.get("query_id"):
                            lin["query_id"] = q_sp["query_id"]
                        if not lin.get("requested_channel"):
                            lin["requested_channel"] = ch_n
                        if not lin.get("channel"):
                            lin["channel"] = f.actual_retrieval_channel

                q_rec = QueryExecutionRecord(
                    query_id=q_sp["query_id"],
                    channel=ch_n,
                    query_text=q_sp["query_text"],
                    query_class=q_sp["query_class"],
                    phase="initial",
                    status="SUCCESS",
                    started_at=started_at,
                    completed_at=completed_at,
                    latency_ms=lat,
                    result_count_raw=len(frags or []),
                    result_count_normalized=0,
                    error=None,
                    retrieval_mode="direct",
                    backend_id=backend_id,
                )
                return ch_n, frags or [], lat, None, q_rec
            except Exception as e:
                completed_at = datetime.utcnow().isoformat()
                lat = int((time.time() - t0) * 1000)
                err_str = str(e)
                err_lower = err_str.lower()
                if "timeout" in err_lower:
                    q_status = "TIMEOUT"
                elif any(auth_kw in err_lower for auth_kw in ("auth", "login", "401", "403", "credential")):
                    q_status = "AUTH_REQUIRED"
                else:
                    q_status = "FAILED"

                q_rec = QueryExecutionRecord(
                    query_id=q_sp["query_id"],
                    channel=ch_n,
                    query_text=q_sp["query_text"],
                    query_class=q_sp["query_class"],
                    phase="initial",
                    status=q_status,
                    started_at=started_at,
                    completed_at=completed_at,
                    latency_ms=lat,
                    result_count_raw=0,
                    result_count_normalized=0,
                    error=err_str,
                    retrieval_mode="direct",
                    backend_id=backend_id,
                )
                return ch_n, [], lat, err_str, q_rec

        channel_raw_fragments: Dict[str, List[EvidenceFragment]] = {ch: [] for ch in normalized_channel_queries}

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        try:
            future_to_task = {executor.submit(_run_single_query, t): t for t in tasks}
            try:
                for fut in concurrent.futures.as_completed(future_to_task, timeout=timeout + 2.0):
                    ch_n, ch_obj, q_sp = future_to_task[fut]
                    executed_queries_count += 1
                    try:
                        ch_ret, frags, lat, err, q_rec = fut.result(timeout=task_timeout)
                        query_records_map[q_rec.query_id] = q_rec
                        tel = channel_telemetry_map[ch_ret]
                        tel.latency_ms = max(tel.latency_ms, lat)
                        if err:
                            tel.failure_reason = err
                        else:
                            tel.successful_requests += 1
                        if frags:
                            channel_raw_fragments.setdefault(ch_ret, []).extend(frags)
                            raw_fragments.extend(frags)
                    except Exception as ex:
                        tel = channel_telemetry_map[ch_n]
                        tel.failure_reason = f"Timeout/Error: {ex}"
                        query_records_map[q_sp["query_id"]] = QueryExecutionRecord(
                            query_id=q_sp["query_id"],
                            channel=ch_n,
                            query_text=q_sp["query_text"],
                            query_class=q_sp["query_class"],
                            phase="initial",
                            status="TIMEOUT" if isinstance(ex, concurrent.futures.TimeoutError) else "FAILED",
                            started_at=datetime.utcnow().isoformat(),
                            completed_at=datetime.utcnow().isoformat(),
                            latency_ms=int(task_timeout * 1000),
                            result_count_raw=0,
                            result_count_normalized=0,
                            error=str(ex),
                            retrieval_mode="direct",
                            backend_id=native_doctor.get_channel_status(ch_n).get("active_backend") or ch_n,
                        )
            except concurrent.futures.TimeoutError:
                logger.warning(f"[AgentReachService] Retrieval timeout reached after {timeout + 2.0}s; collecting partial results")
                for fut, (ch_n, _, q_sp) in future_to_task.items():
                    if not fut.done():
                        channel_telemetry_map[ch_n].failure_reason = "Retrieval budget timeout"
                        if q_sp["query_id"] not in query_records_map:
                            query_records_map[q_sp["query_id"]] = QueryExecutionRecord(
                                query_id=q_sp["query_id"],
                                channel=ch_n,
                                query_text=q_sp["query_text"],
                                query_class=q_sp["query_class"],
                                phase="initial",
                                status="TIMEOUT",
                                started_at=datetime.utcnow().isoformat(),
                                completed_at=datetime.utcnow().isoformat(),
                                latency_ms=int(task_timeout * 1000),
                                result_count_raw=0,
                                result_count_normalized=0,
                                error="Retrieval budget timeout",
                                retrieval_mode="direct",
                                backend_id=native_doctor.get_channel_status(ch_n).get("active_backend") or ch_n,
                            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        # Update per-channel raw counts
        for ch_n, tel in channel_telemetry_map.items():
            ch_raw = channel_raw_fragments.get(ch_n, [])
            tel.raw_results = len(ch_raw)
            tel.normalized_results = len(ch_raw)
            st_info = native_doctor.get_channel_status(ch_n)
            tel.active_backend = st_info.get("active_backend") or ch_n
            if tel.failure_reason:
                tel.status = ChannelStatus.UNAVAILABLE.value
                self.registry.mark_degraded(ch_n)
            elif tel.raw_results > 0:
                depths = {str(getattr(f, "content_depth", "")).upper() for f in ch_raw}
                modes = {str(getattr(f, "retrieval_mode", "")).lower() for f in ch_raw}
                if "INDEX_SNIPPET" in depths or "web_search_index" in modes:
                    tel.status = ChannelStatus.DEGRADED.value
                    tel.content_class = "SEARCH_INDEX"
                elif "FEED_ENTRY_SUMMARY" in depths:
                    tel.status = ChannelStatus.DEGRADED.value
                    tel.content_class = "SYNDICATED"
                elif depths and depths <= {"PROFILE_METADATA", "VIDEO_METADATA", "HEADLINE_ONLY", "METADATA"}:
                    tel.status = ChannelStatus.DEGRADED.value
                    tel.content_class = "METADATA"
                else:
                    tel.status = ChannelStatus.AVAILABLE.value
                    tel.content_class = "DIRECT_OR_PARTIAL_CONTENT"
                tel.usable_results = sum(1 for f in ch_raw if (getattr(f, "content", "") or getattr(f, "snippet", "")).strip())
            elif tel.requests_attempted > 0:
                tel.status = "EMPTY"

        # 5. Deduplication & Normalization
        deduped_fragments, total_dupes_removed = self._deduplicate_fragments(raw_fragments)
        if len(deduped_fragments) > max_total_ev:
            deduped_fragments = deduped_fragments[:max_total_ev]

        # Calculate per-query normalized result counts
        for f in deduped_fragments:
            frag_qids = set()
            if getattr(f, "query_id", None):
                frag_qids.add(f.query_id)
            for lin in getattr(f, "retrieval_lineage", []):
                if lin.get("query_id"):
                    frag_qids.add(lin["query_id"])
            for qid in frag_qids:
                if qid in query_records_map:
                    query_records_map[qid].result_count_normalized += 1

        # Calculate per-channel final and duplicates
        final_by_ch: Dict[str, int] = {}
        for f in deduped_fragments:
            ch_k = getattr(f, "requested_channel", None) or f.channel_name or "unknown"
            final_by_ch[ch_k] = final_by_ch.get(ch_k, 0) + 1

        for ch_n, tel in channel_telemetry_map.items():
            tel.final_results = final_by_ch.get(ch_n, 0)
            tel.duplicates_removed = max(0, tel.raw_results - tel.final_results)

        # 6. Deep Reading Phase
        readable_sources = 0
        if perform_reads and deduped_fragments:
            read_candidates = []
            for f in deduped_fragments:
                u = f.url or ""
                if u.startswith("http") and not any(skip in u.lower() for skip in ["youtube.com", "youtu.be", "twitter.com", "x.com", "reddit.com", ".pdf"]):
                    read_candidates.append(f)

            for cand in read_candidates[:max_deep_reads]:
                try:
                    read_res = self.read(cand.url, max_chars=2500)
                    if read_res.get("status") in ("success", "fallback_soup") and read_res.get("markdown"):
                        md = read_res["markdown"].strip()
                        if len(md) > 200:
                            cand.content = md
                            cand.snippet = md[:350] + ("..." if len(md) > 350 else "")
                            cand.content_depth = "FULL_ARTICLE" if len(md) > 1000 else "PARTIAL_CONTENT"
                            readable_sources += 1
                except Exception as r_err:
                    logger.debug(f"[AgentReachService] Deep reading pass error for {cand.url}: {r_err}")

        # 7. Source Independence & Syndication Grouping
        independence_groups = self._cluster_source_independence(deduped_fragments)

        # 8. Assign semantic source roles
        self._assign_source_roles(deduped_fragments)

        # 9. Build Capability-Aware Execution Graph & RetrievalTrace
        unique_domains = len(set(urllib.parse.urlparse(f.url).netloc.lower() for f in deduped_fragments if f.url))
        indep_groups_count = len(set(f.raw_metadata.get("source_independence_group", "independent") for f in deduped_fragments))
        total_latency_ms = int((time.time() - start_ts) * 1000)

        execution_graph: List[Dict[str, Any]] = []
        native_backends_used: Set[str] = set()
        fallbacks_used_count = 0
        step_id = 1

        for ch_n, tel in channel_telemetry_map.items():
            if tel.requests_attempted == 0 and tel.raw_results == 0:
                continue
            st_info = native_doctor.get_channel_status(ch_n)
            backend_name = st_info.get("active_backend") or tel.active_backend or ch_n
            fallback_chain = ["Playwright", "RSS", "Direct HTML"] if ch_n == "web" else ["Jina Web", "Meta API"]
            is_fallback = bool(tel.fallback_used or "fallback" in str(backend_name).lower())
            if is_fallback:
                fallbacks_used_count += 1
            native_backends_used.add(str(backend_name))

            execution_graph.append({
                "step_id": step_id,
                "platform": ch_n,
                "backend": backend_name,
                "operation": "multi_channel_search",
                "fallback_chain": fallback_chain,
                "fallback_used": is_fallback,
                "result_count": tel.raw_results,
                "read_depth": "SNIPPET",
                "failure_reason": tel.failure_reason,
                "latency_ms": tel.latency_ms,
                "status": "SUCCESS" if tel.raw_results > 0 else ("FAILED" if tel.failure_reason else "EMPTY"),
            })
            step_id += 1

        capability_summary = {
            "total_queries": total_planned_queries,
            "platforms_queried": len(channel_telemetry_map),
            "native_backends_count": len(native_backends_used),
            "fallbacks_invoked": fallbacks_used_count,
            "raw_candidates_found": len(raw_fragments),
            "unique_candidates": len(deduped_fragments),
            "deeply_investigated": readable_sources,
        }

        trace = RetrievalTrace(
            scan_id=f"scan_{int(start_ts)}_{abs(hash(target_name or domain)) % 10000:04d}",
            agent=agent_name,
            query=target_name or "multi_query",
            domain=domain,
            planned_query_classes=len(all_query_classes),
            planned_queries_count=total_planned_queries,
            executed_queries_count=executed_queries_count,
            channel_stats={ch: tel.to_dict() for ch, tel in channel_telemetry_map.items() if tel.requests_attempted > 0 or tel.raw_results > 0},
            execution_graph=execution_graph,
            capability_summary=capability_summary,
            total_raw=len(raw_fragments),
            total_normalized=len(raw_fragments),
            total_duplicates=total_dupes_removed,
            total_final=len(deduped_fragments),
            unique_domains=unique_domains,
            independent_groups=indep_groups_count,
            readable_sources=readable_sources,
            total_latency_ms=total_latency_ms,
        )

        channel_health_map = {
            ch: tel.status for ch, tel in channel_telemetry_map.items()
        }

        return RetrievalResult(
            query=target_name or "multi_query",
            domain=domain,
            fragments=deduped_fragments,
            channel_health=channel_health_map,
            total_signals=len(deduped_fragments),
            retrieval_plan={
                "domain": domain,
                "target": target_name,
                "planned_queries": total_planned_queries,
                "executed_queries": executed_queries_count,
                "channels": list(normalized_channel_queries.keys()),
            },
            source_article=source_doc,
            retrieval_trace=trace.to_dict(),
            trace_obj=trace,
            query_records=list(query_records_map.values()),
        )

    # ── Deduplication & Independence Logic ──────────────────────────────────

    def _normalize_url(self, raw_url: str) -> str:
        """Strip tracking parameters (utm_*, ref, etc.) and normalize URL for dedup."""
        if not raw_url:
            return ""
        try:
            parsed = urllib.parse.urlparse(raw_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            # Remove tracking params
            filtered = {k: v for k, v in query_params.items() if not k.startswith("utm_") and k not in ("ref", "fbclid", "gclid")}
            clean_query = urllib.parse.urlencode(filtered, doseq=True)
            return urllib.parse.urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip("/"),
                parsed.params,
                clean_query,
                ""  # drop fragment
            ))
        except Exception:
            return raw_url.strip().lower()

    def _deduplicate_fragments(
        self,
        fragments: List[EvidenceFragment]
    ) -> Tuple[List[EvidenceFragment], int]:
        """Deduplicate fragments across multiple search providers and channels with fine-grained precision while preserving lineage."""
        seen_urls: Dict[str, EvidenceFragment] = {}
        seen_titles: Dict[str, EvidenceFragment] = {}
        unique: List[EvidenceFragment] = []
        dupes_count = 0

        def _merge_into_canonical(canonical: EvidenceFragment, incoming: EvidenceFragment):
            # 1. Merge retrieval_lineage
            incoming_lineage = getattr(incoming, "retrieval_lineage", []) or []
            existing_lineage = getattr(canonical, "retrieval_lineage", []) or []
            for item in incoming_lineage:
                if not any(
                    e.get("channel") == item.get("channel") and
                    e.get("requested_channel") == item.get("requested_channel") and
                    e.get("query_id") == item.get("query_id") and
                    e.get("backend_id") == item.get("backend_id")
                    for e in existing_lineage
                ):
                    existing_lineage.append(item)
            canonical.retrieval_lineage = existing_lineage

            # 2. Retain richer snippet/content
            if len(incoming.content or "") > len(canonical.content or ""):
                canonical.content = incoming.content
                canonical.content_depth = incoming.content_depth
            if len(incoming.snippet or "") > len(canonical.snippet or ""):
                canonical.snippet = incoming.snippet

        for f in fragments:
            norm_url = self._normalize_url(f.url)
            norm_title = re.sub(r'[^a-z0-9]', '', f.title.lower())

            matched_canonical: Optional[EvidenceFragment] = None

            # URL matching: exact normalized URL is an unequivocal duplicate
            if norm_url and norm_url in seen_urls:
                matched_canonical = seen_urls[norm_url]
            else:
                # Title matching: require full title match (> 25 characters) on the same domain or exact match
                domain = urllib.parse.urlparse(f.url).netloc.lower() if f.url else ""
                title_key = f"{domain}:{norm_title}" if domain else norm_title

                if norm_title and len(norm_title) > 25:
                    if title_key in seen_titles:
                        matched_canonical = seen_titles[title_key]
                    elif norm_title in seen_titles:
                        matched_canonical = seen_titles[norm_title]

            if matched_canonical is not None:
                dupes_count += 1
                _merge_into_canonical(matched_canonical, f)
                continue

            if norm_url:
                seen_urls[norm_url] = f
            if norm_title:
                seen_titles[norm_title] = f
                domain = urllib.parse.urlparse(f.url).netloc.lower() if f.url else ""
                if domain:
                    seen_titles[f"{domain}:{norm_title}"] = f

            unique.append(f)

        return unique, dupes_count

    def _cluster_source_independence(
        self,
        fragments: List[EvidenceFragment]
    ) -> Dict[str, List[str]]:
        """
        Group syndicated stories to prevent duplicate confirmation counting.
        E.g., 4 outlets republishing the same AP wire are clustered into 1 group.
        """
        groups: Dict[str, List[str]] = {}

        for f in fragments:
            assigned_group = "independent"
            content_lower = (f.title + " " + f.snippet).lower()

            for marker in SYNDICATION_MARKERS:
                if marker in content_lower:
                    assigned_group = f"syndicated_{marker.replace(' ', '_')}"
                    break

            f.raw_metadata["source_independence_group"] = assigned_group
            groups.setdefault(assigned_group, []).append(f.url or f.title)

        return groups

    def _assign_source_roles(self, fragments: List[EvidenceFragment]) -> None:
        """Tag fragments with their forensic source role (PRIMARY, SECONDARY, etc.)."""
        primary_markers = [
            "sec.gov", "bseindia.com", "nseindia.com", "investor", "ir.",
            "tatamotors.com", "nvidia.com", "apple.com", "tesla.com",
            "regulatory filing", "investor relations", "annual report",
            "exchange filing", "press release", "official statement",
            "form 10-k", "form 10-q", "sebi.gov"
        ]
        financial_press = [
            "reuters", "bloomberg", "moneycontrol", "economictimes",
            "livemint", "business-standard", "financialexpress", "cnbc",
            "wsj", "ft.com", "apnews"
        ]

        for f in fragments:
            platform = f.platform.lower()
            method = f.retrieval_method.lower()
            url_lower = (f.url or "").lower()
            title_lower = (f.title or "").lower()
            combined_text = f"{url_lower} {title_lower}"

            if any(pm in combined_text for pm in primary_markers):
                f.raw_metadata["source_role"] = "PRIMARY"
                f.raw_metadata["source_tier"] = "TIER_1_OFFICIAL_FILING"
            elif "github" in platform or "github" in method:
                f.raw_metadata["source_role"] = "PRIMARY"
                f.raw_metadata["source_tier"] = "TIER_1_CODE_METADATA"
            elif any(fp in combined_text for fp in financial_press) or "news" in platform or "wire" in platform:
                f.raw_metadata["source_role"] = "SECONDARY"
                f.raw_metadata["source_tier"] = "TIER_2_FINANCIAL_PRESS"
            elif "reddit" in platform:
                f.raw_metadata["source_role"] = "COMMUNITY"
                f.raw_metadata["source_tier"] = "TIER_3_INVESTOR_COMMUNITY"
            elif "twitter" in platform:
                f.raw_metadata["source_role"] = "COMMENTARY"
                f.raw_metadata["source_tier"] = "TIER_3_SOCIAL_SIGNALS"
            elif "youtube" in platform:
                f.raw_metadata["source_role"] = "DIRECT_MEDIA"
                f.raw_metadata["source_tier"] = "TIER_2_VIDEO_ANALYSIS"
            elif "web article" in platform or "jina" in method:
                f.raw_metadata["source_role"] = "PRIMARY"
                f.raw_metadata["source_tier"] = "TIER_1_ORIGINAL_DOCUMENT"
            else:
                f.raw_metadata["source_role"] = "DISCOVERY"
                f.raw_metadata["source_tier"] = "TIER_3_AGGREGATE"

    # ── Backward Compatibility with legacy AgentReachScraper ───────────────

    def omni_scan(
        self,
        query: str = "",
        claim_text: str = "",
        domain: str = "general",
        target_company: str = None,
        include_platforms: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        limit_per_channel: int = 6,
    ) -> Dict[str, Any]:
        """
        Legacy omni_scan compatibility method.
        Accepts both 'query' and 'claim_text', returns identical dictionary shape
        with enhanced retrieval metadata.
        """
        target_q = query or claim_text
        res = self.retrieve(
            query=target_q,
            domain=domain,
            channels=include_platforms,
            source_url=source_url,
            limit_per_channel=limit_per_channel,
        )

        output = res.to_dict()
        # Add legacy top-level keys expected by existing agents and endpoints
        output["channels"] = res.channels
        output["items"] = res.items
        output["total_signals"] = len(res.fragments)
        output["retrieval_trace"] = res.retrieval_trace
        output["trace"] = res.retrieval_trace
        return output

    def unified_scan(
        self,
        query: str,
        platforms: Optional[List[str]] = None,
        max_results_per_platform: int = 5,
    ) -> Dict[str, Any]:
        """Legacy unified_scan compatibility method."""
        return self.omni_scan(
            query=query,
            domain="general",
            include_platforms=platforms,
            limit_per_channel=max_results_per_platform,
        )

    def doctor(self) -> Dict[str, Any]:
        """Legacy doctor compatibility method."""
        return self.health()

    def read_article_markdown(self, url: str, max_chars: int = 4000) -> Dict[str, Any]:
        """Legacy read_article_markdown compatibility method."""
        return self.read(url, max_chars=max_chars)

    def search_reddit(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.search_channel("reddit", query, limit=limit)]

    def search_twitter(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.search_channel("twitter", query, limit=limit)]

    def search_youtube(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.search_channel("youtube", query, limit=limit)]

    def search_news(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.search_channel("news", query, limit=limit)]


# Canonical class name retained from the original infrastructure facade.
AcquisitionService = AgentReachService

# Canonical singleton instances for Aegis
agent_reach_service = AgentReachService()
reach_adapter = agent_reach_service

__all__ = [
    "AcquisitionService",
    "AgentReachService",
    "agent_reach_service",
    "reach_adapter",
]
