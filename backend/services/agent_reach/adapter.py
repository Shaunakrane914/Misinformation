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
    Channel,
    ChannelStatus,
    ChannelTelemetry,
    EvidenceFragment,
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
from backend.services.agent_reach.registry import CapabilityRegistry
from backend.services.url_validator import is_safe_url

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
        self.registry.register(AuthenticatedOptionalChannel("linkedin", "LinkedIn", "LINKEDIN_SESSION_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("xueqiu", "Xueqiu", "XUEQIU_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("xiaohongshu", "Xiaohongshu", "XIAOHONGSHU_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("instagram", "Instagram", "INSTAGRAM_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("facebook", "Facebook", "FACEBOOK_COOKIE"))
        self.registry.register(AuthenticatedOptionalChannel("boss", "Boss直聘", "BOSS_CDP_PORT"))

    # ── Diagnostics & Capabilities ──────────────────────────────────────────

    def capabilities(self) -> Dict[str, Any]:
        """Return the complete channel capability inventory and server compatibility status."""
        upstream = get_upstream_info()
        doctor_status = native_doctor.check_all()
        cap_map = self.registry.capability_map()
        available_count = sum(1 for c in cap_map.values() if c["status"] == ChannelStatus.AVAILABLE.value)

        native_channels = {}
        for plat, cap in CAPABILITY_MATRIX.items():
            doc_entry = doctor_status.get(plat, {})
            status_code = native_doctor.get_canonical_status_code(plat)
            active_b = doc_entry.get("active_backend") or (cap.backends[0] if cap.backends else "default")
            native_channels[plat] = {
                "status": status_code,
                "backend": active_b,
                "operations": sorted(list(cap.operations)),
                "tier": cap.tier,
                "cloud_safe": cap.cloud_safe,
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
                else:
                    q_id = f"{ch_name[:2]}_{idx+1:02d}"
                    q_class = "general"
                    q_text = str(q_item)

                if q_text.strip():
                    norm_list.append({"query_id": q_id, "query_class": q_class, "query_text": q_text.strip()})
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

        # Prepare execution tasks
        tasks = []  # (ch_name, channel_obj, query_spec)
        available_channels = {c.name: c for c in self.registry.get_available()}

        for ch_name, queries in normalized_channel_queries.items():
            telemetry = channel_telemetry_map.setdefault(ch_name, ChannelTelemetry(channel=ch_name))
            telemetry.queries_attempted = [q["query_text"] for q in queries]
            telemetry.requests_attempted = len(queries)

            if ch_name not in available_channels:
                telemetry.failure_reason = f"Channel {ch_name} status is {telemetry.status}"
                continue

            channel_obj = available_channels[ch_name]
            for q_spec in queries:
                tasks.append((ch_name, channel_obj, q_spec))

        # 4. Concurrent execution with bounded concurrency
        raw_fragments: List[EvidenceFragment] = []
        executed_queries_count = 0

        def _run_single_query(task_tuple) -> Tuple[str, List[EvidenceFragment], int, Optional[str]]:
            ch_n, ch_obj, q_sp = task_tuple
            t0 = time.time()
            try:
                frags = ch_obj.search(
                    q_sp["query_text"],
                    limit=max_res_per_q,
                    query_id=q_sp["query_id"],
                    query_class=q_sp["query_class"],
                    query_text=q_sp["query_text"],
                    domain=domain
                )
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
                return ch_n, frags or [], lat, None
            except Exception as e:
                lat = int((time.time() - t0) * 1000)
                return ch_n, [], lat, str(e)

        channel_raw_fragments: Dict[str, List[EvidenceFragment]] = {ch: [] for ch in normalized_channel_queries}

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_task = {executor.submit(_run_single_query, t): t for t in tasks}
            for fut in concurrent.futures.as_completed(future_to_task, timeout=timeout + 2.0):
                ch_n, ch_obj, q_sp = future_to_task[fut]
                executed_queries_count += 1
                try:
                    ch_ret, frags, lat, err = fut.result(timeout=task_timeout)
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
                tel.status = ChannelStatus.AVAILABLE.value
            elif tel.requests_attempted > 0:
                tel.status = "EMPTY"

        # 5. Deduplication & Normalization
        deduped_fragments, total_dupes_removed = self._deduplicate_fragments(raw_fragments)
        if len(deduped_fragments) > max_total_ev:
            deduped_fragments = deduped_fragments[:max_total_ev]

        # Calculate per-channel final and duplicates
        final_by_ch: Dict[str, int] = {}
        for f in deduped_fragments:
            ch_k = f.channel_name or "unknown"
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

        # 9. Build RetrievalTrace
        unique_domains = len(set(urllib.parse.urlparse(f.url).netloc.lower() for f in deduped_fragments if f.url))
        indep_groups_count = len(set(f.raw_metadata.get("source_independence_group", "independent") for f in deduped_fragments))
        total_latency_ms = int((time.time() - start_ts) * 1000)

        trace = RetrievalTrace(
            scan_id=f"scan_{int(start_ts)}_{abs(hash(target_name or domain)) % 10000:04d}",
            agent=agent_name,
            query=target_name or "multi_query",
            domain=domain,
            planned_query_classes=len(all_query_classes),
            planned_queries_count=total_planned_queries,
            executed_queries_count=executed_queries_count,
            channel_stats={ch: tel.to_dict() for ch, tel in channel_telemetry_map.items() if tel.requests_attempted > 0 or tel.raw_results > 0},
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
        )

    def retrieve(
        self,
        query: str,
        domain: str = "general",
        channels: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        limit_per_channel: int = 6,
        timeout: float = 12.0,
    ) -> RetrievalResult:
        """
        Execute domain-planned, concurrent internet evidence retrieval.
        Automatically leverages multi-query planning and bounded concurrent execution.
        """
        clean_q = query.strip()
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
                    "max_queries_per_channel": 3,
                    "max_results_per_query": limit_per_channel,
                    "max_total_evidence": 40,
                    "max_deep_reads": 4,
                },
                perform_reads=True,
                timeout=timeout
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
            perform_reads=True,
            timeout=timeout
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
        """Deduplicate fragments across multiple search providers and channels with fine-grained precision."""
        seen_urls: Set[str] = set()
        seen_titles: Set[str] = set()
        unique: List[EvidenceFragment] = []
        dupes_count = 0

        for f in fragments:
            norm_url = self._normalize_url(f.url)
            norm_title = re.sub(r'[^a-z0-9]', '', f.title.lower())

            # URL matching: exact normalized URL is an unequivocal duplicate
            if norm_url and norm_url in seen_urls:
                dupes_count += 1
                continue

            # Title matching: require full title match (> 25 characters) on the same domain or exact match
            domain = urllib.parse.urlparse(f.url).netloc.lower() if f.url else ""
            title_key = f"{domain}:{norm_title}" if domain else norm_title

            if norm_title and len(norm_title) > 25 and (title_key in seen_titles or norm_title in seen_titles):
                dupes_count += 1
                continue

            if norm_url:
                seen_urls.add(norm_url)
            if norm_title:
                seen_titles.add(norm_title)
                if domain:
                    seen_titles.add(title_key)

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


# Canonical singleton instances for Aegis
agent_reach_service = AgentReachService()
reach_adapter = agent_reach_service
