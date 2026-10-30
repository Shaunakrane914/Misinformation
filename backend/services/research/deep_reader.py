"""
Aegis Protocol — Diversity-Aware Deep Reader
============================================
Selects and executes deep reading across diverse, high-value candidate URLs.
Avoids consuming read budgets on syndicated duplicates, uses bounded concurrency,
preserves original snippets, and enriches evidence to FULL_ARTICLE depth.
"""

import concurrent.futures
import logging
import re
import time
import uuid
from contextvars import copy_context
from urllib.parse import urlsplit
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.research.research_models import ContentDepth, EvidenceItem, SourceRole, SourceTier
from backend.infrastructure.acquisition.network.budget import acquisition_deadline, remaining_timeout
from backend.infrastructure.acquisition.network.http import ProviderHTTPError, transport_failure_kind
from backend.infrastructure.acquisition.security.url_validator import validation_failure_kind
from backend.infrastructure.acquisition.adapters.web.search_matching import headline_overlap

logger = logging.getLogger(__name__)

# Skip domains where direct text article reading is strictly blocked / requires closed auth
UNSUPPORTED_AUTH_DOMAINS = {
    "instagram.com", "tiktok.com", "facebook.com", "threads.net", "linkedin.com", "weibo.com"
}


def _diagnostic_url(url):
    """Bounded public locator; never copy credentials/query tokens into errors."""
    try:
        parsed = urlsplit(url or "")
        return f"{parsed.scheme}://{parsed.hostname or ''}{parsed.path}"[:500]
    except ValueError:
        return "INVALID_URL"


def _challenge_body(body):
    return bool(re.match(r"\s*(?:#{1,3}\s*)?(?:just a moment|verify (?:that )?you are human|checking your browser|access denied|attention required)", body[:200], re.I))


def _read_failure_kind(result, transport_success, body):
    status = str(result.get("status", "")).lower()
    error = str(result.get("error", "")).lower()
    if result.get("failure_kind") in {"ROBOTS_DENIED", "ROBOTS_UNVERIFIED", "ROBOTS_CRAWL_DELAY_REVIEW_REQUIRED", "PERMISSION_REQUIRED", "UNVERIFIED", "BLOCKED", "TIMEOUT", "ACCESS_REJECTED", "HTTP_FAILURE", "CHALLENGE_PAGE", "EMPTY_EXTRACTION", "PROVIDER_FAILURE", "PUBLISHER_UNRESOLVED",
                                     "DNS_ERROR", "DNS_TIMEOUT", "DNS_CAPACITY", "SSRF_BLOCKED", "CONNECTION_FAILURE", "BUDGET_EXHAUSTED", "RATE_LIMITED", "AUTH_REQUIRED", "ACCESS_DENIED"}:
        return result["failure_kind"]
    if "dns resolution failed" in error:
        return validation_failure_kind(error)
    if status == "blocked_ssrf" or result.get("runtime_decision"):
        return "ACCESS_REJECTED"
    if "timed out" in error or "timeout" in error or "deadline" in error:
        return "TIMEOUT"
    if _challenge_body(body):
        return "CHALLENGE_PAGE"
    if transport_success and len(body) < 30:
        return "EMPTY_EXTRACTION"
    if re.search(r"\bhttp(?:\s+(?:error|status))?\s*:?[ ]*[45]\d\d|\bforbidden\b", error) or _http_status(result) in {400, 401, 403, 404, 429, 500, 502, 503, 504}:
        return "HTTP_FAILURE"
    return "PROVIDER_FAILURE"


def _http_status(result):
    value = result.get("status_code") or (result.get("transport") or {}).get("http_status")
    if type(value) is int and 100 <= value <= 599:
        return value
    match = re.search(r"\bhttp(?:\s+(?:error|status))?\s*:?[ ]*([45]\d\d)", str(result.get("error", "")), re.I)
    return int(match.group(1)) if match else None


class DeepReader:
    """Performs diversity-aware deep source acquisition and full-content extraction."""

    def __init__(self, cache_ttl_seconds: int = 900):
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}  # url -> (result_dict, timestamp)
        self.cache_ttl = cache_ttl_seconds

    def _resolve_wrapper(self, item, service):
        """One bounded headline lookup, never treat a search snippet as a body.

        Encrypted Google News tokens are not publisher URLs. Record the extra
        lookup separately from initial discovery; only observed matching leads
        can be read. Normal service.read still enforces SSRF/access policy.
        """
        title = (item.title or "").rsplit(" - ", 1)[0].strip()[:180]
        terms = set(re.findall(r"[a-z0-9]+", title.casefold()))
        trace = {"status": "UNRESOLVED", "discovery_url": item.canonical_url,
                 # Feed titles can be truncated mid-word. An exact full-title
                 # phrase suppresses real publisher variants; the independent
                 # 75% title-token join below remains unchanged.
                 "query": title.replace(chr(34), ""), "query_records": [], "candidates": []}
        if len(terms) < 4:
            return None, trace
        from backend.services.research.source_quality import canonical_hostname
        publisher = canonical_hostname(item.metadata.get("publisher_source_url") or "")
        if publisher and publisher != "google.com" and not publisher.endswith(".google.com"):
            # Use a publisher observed in the actual feed, never a guessed
            # outlet/domain. Replace the one existing lookup, not an extra retry.
            trace["publisher_scope"] = publisher
            trace["query_basis"] = "FEED_DECLARED_PUBLISHER_UNVERIFIED"
            trace["query"] = f"site:{publisher} {trace['query']}"
        # Resolution is a multi-provider chain, not one HTTP call. Reserve a
        # third of the remaining read window for the actual publisher body.
        # Each transport remains capped at five seconds; never extend a parent.
        resolution_timeout = min(10.0, remaining_timeout(15.0) * (2.0 / 3.0))
        result = service.retrieve_many(
            {"web": [{"query_id": f"wr_{item.id}", "query_class": "publisher_url_resolution",
                      "query_text": trace["query"]}]}, perform_reads=False,
            timeout=resolution_timeout, agent_name="source_resolution",
            budget={"max_queries_per_channel": 1, "max_results_per_query": 3,
                    "max_total_evidence": 3, "channel_timeout": resolution_timeout})
        trace["query_records"] = [record.to_dict() for record in result.query_records]
        for candidate in result.fragments[:3]:
            try:
                parsed = urlsplit(candidate.url or "")
                host = (parsed.hostname or "").lower()
            except ValueError:
                parsed, host = None, ""
            overlap = headline_overlap(title, candidate.title)
            reason = ("INVALID_URL" if not parsed or parsed.scheme not in {"http", "https"} or not host
                      else "URL_CREDENTIALS" if parsed.username or parsed.password
                      else "WRAPPER_URL" if host == "google.com" or host.endswith(".google.com")
                      else "TITLE_MISMATCH" if overlap < 0.75 else None)
            trace["candidates"].append({"url": _diagnostic_url(candidate.url), "title": (candidate.title or "")[:180],
                                        "title_token_overlap": round(overlap, 3), "rejection_reason": reason})
            if reason is None:
                trace.update(status="OBSERVED_PUBLISHER_LEAD", selected_url=candidate.url,
                             selected_title=candidate.title, claim_support_verified=False)
                return candidate.url, trace
        return None, trace

    @staticmethod
    def _selection_domain(item):
        # An opaque transport wrapper is not publisher identity. Separate read
        # opportunities within the existing attempt cap; do NOT rewrite source
        # domain/independence or assert that these leads are independent.
        try:
            host = (urlsplit(item.canonical_url or "").hostname or "").lower()
        except ValueError:
            host = "invalid-url"
        if host == "news.google.com":
            return "unresolved-wrapper:" + item.id
        return (item.source_domain or host or "other").lower()

    def _select_read_candidates(
        self,
        ranked_candidates: List[EvidenceItem],
        max_reads: int = 15
    ) -> Tuple[List[EvidenceItem], List[Dict[str, Any]]]:
        """
        Selects top candidate sources prioritizing:
        1. Primary and official documents
        2. Domain diversity (up to 2 per domain, or 3 if covering novel query class/entity)
        3. Syndication diversity (max 1 per wire family)
        
        Audits every candidate with:
        - candidate_id
        - ranked_candidate_id
        - accepted_candidate_id
        - rank
        - score
        - selection_decision (ACCEPTED | REJECTED)
        - selection_reason
        - eligible_for_read
        - selected
        - rejection_reason
        """
        selected: List[EvidenceItem] = []
        domain_items: Dict[str, List[EvidenceItem]] = {}
        seen_wire_families: Set[str] = set()
        seen_selected_ids: Set[str] = set()
        seen_selected_urls: Set[str] = set()
        from backend.services.research.source_identity import source_url_key
        primary_satisfied_count = 0
        audit: List[Dict[str, Any]] = []

        # Step 1: Preliminary Eligibility Assessment
        for rank, item in enumerate(ranked_candidates, 1):
            if not getattr(item, "ranked_id", None):
                item.ranked_id = f"cand_rank_{item.id}"
            if not getattr(item, "rank", None):
                item.rank = rank

            url = item.canonical_url or ""
            score = item.metadata.get("candidate_score", item.relevance_score)
            from backend.services.research.content_roles import document_role
            if document_role(item) == "BACKGROUND_REFERENCE":
                item.metadata["read_exclusion_reason"] = "REFERENCE_BACKGROUND_NOT_CURRENT_EVIDENCE"

            if item.metadata.get("defer_non_objective_read"):
                item.eligible_for_read = False
                item.selected_for_read = False
                item.rejection_reason = "deferred_not_agent_objective"
            elif item.metadata.get("read_exclusion_reason"):
                item.eligible_for_read = False
                item.selected_for_read = False
                item.rejection_reason = item.metadata["read_exclusion_reason"]
            elif not url or not url.startswith("http"):
                item.eligible_for_read = False
                item.selected_for_read = False
                item.rejection_reason = "unsupported_read"
            elif any(sd in url.lower() for sd in ["instagram.com", "facebook.com", "threads.net"]):
                item.eligible_for_read = False
                item.selected_for_read = False
                item.rejection_reason = "social_only"
            elif any(sd in url.lower() for sd in ["twitter.com", "x.com", "reddit.com"]) and item.content_depth == ContentDepth.SOCIAL_POST.value:
                item.eligible_for_read = False
                item.selected_for_read = False
                item.rejection_reason = "social_only"
            elif any(sd in url.lower() for sd in ["bilibili.com"]):
                item.eligible_for_read = False
                item.selected_for_read = False
                item.rejection_reason = "video_requires_transcript"
            elif item.source_quality_score < 0.15:
                item.eligible_for_read = False
                item.selected_for_read = False
                item.rejection_reason = "low_quality"
            elif item.relevance_score < 0.10 and item.metadata.get("discovery_kind") != "FEED_INDEX":
                item.eligible_for_read = False
                item.selected_for_read = False
                item.rejection_reason = "low_relevance"
            else:
                item.eligible_for_read = True
                item.selected_for_read = False
                item.rejection_reason = None

        # Step 2: Primary and Official Selection
        for item in ranked_candidates:
            if len(selected) >= max_reads:
                break
            if not item.eligible_for_read:
                continue
            if item.id in seen_selected_ids or (item.canonical_url and source_url_key(item.canonical_url) in seen_selected_urls):
                item.rejection_reason = "duplicate_candidate"
                continue

            domain = self._selection_domain(item)
            if ((item.primary_source or item.source_role == SourceRole.PRIMARY.value)
                    and item.metadata.get("authority_scope") != "CORPORATE_LANDING"
                    and item.metadata.get("objective_read_match") is not False):
                if primary_satisfied_count >= 5:
                    item.rejection_reason = "primary_already_satisfied"
                    continue
                selected.append(item)
                item.selected_for_read = True
                item.rejection_reason = None
                seen_selected_ids.add(item.id)
                if item.canonical_url:
                    seen_selected_urls.add(source_url_key(item.canonical_url))
                primary_satisfied_count += 1
                domain_items.setdefault(domain, []).append(item)
                if item.source_family_id:
                    seen_wire_families.add(item.source_family_id)

        # Step 3: Diverse Secondary and Investigative Selection
        for item in ranked_candidates:
            if not item.eligible_for_read:
                continue
            if item in selected or item.id in seen_selected_ids or (item.canonical_url and source_url_key(item.canonical_url) in seen_selected_urls):
                item.rejection_reason = "duplicate_candidate"
                continue

            domain = self._selection_domain(item)
            d_list = domain_items.get(domain, [])

            if len(selected) >= max_reads:
                item.rejection_reason = "domain_budget_exhausted" if len(d_list) >= 2 else "read_budget_exhausted"
                continue

            # Check wire family duplicate
            if item.source_family_id and item.source_family_id in seen_wire_families:
                item.rejection_reason = "same_source_family"
                continue

            # Diversity check: allow 2 per domain, or 3 if different query class
            if len(d_list) >= 2:
                existing_classes = {x.query_class for x in d_list}
                if item.query_class in existing_classes or len(d_list) >= 3:
                    item.rejection_reason = "same_domain_over_budget"
                    continue

            selected.append(item)
            item.selected_for_read = True
            item.rejection_reason = None
            seen_selected_ids.add(item.id)
            if item.canonical_url:
                seen_selected_urls.add(source_url_key(item.canonical_url))
            domain_items.setdefault(domain, []).append(item)
            if item.source_family_id:
                seen_wire_families.add(item.source_family_id)

        # Assign explicit 5-stage selection telemetry and build audit list
        for rank, item in enumerate(ranked_candidates, 1):
            if item.selected_for_read:
                item.accepted_id = f"cand_acc_{item.id}"
                item.selection_decision = "ACCEPTED"
                item.selection_reason = "PRIMARY_DOCUMENT" if item.primary_source else "DIVERSE_SOURCE"
                item.rejection_reason = None
            else:
                item.accepted_id = None
                item.selection_decision = "REJECTED"
                if item.eligible_for_read and not item.rejection_reason:
                    item.rejection_reason = "read_budget_exhausted"
                item.selection_reason = item.rejection_reason or "read_budget_exhausted"

            audit.append({
                "candidate_id": item.id,
                "ranked_candidate_id": item.ranked_id,
                "accepted_candidate_id": item.accepted_id,
                "rank": rank,
                "score": round(float(item.metadata.get("candidate_score", item.relevance_score)), 3),
                "selection_decision": item.selection_decision,
                "selection_reason": item.selection_reason,
                "eligible_for_read": item.eligible_for_read,
                "selected": item.selected_for_read,
                "rejection_reason": item.rejection_reason,
            })

        return selected, audit

    def deep_read(
        self,
        ranked_candidates: List[EvidenceItem],
        max_reads: int = 15,
        timeout_per_read: float = 6.0,
        *, service=None, max_concurrency: Optional[int] = None, attempt_ids=None,
    ) -> Tuple[List[EvidenceItem], Dict[str, Any]]:
        """
        Deep-reads top diverse candidates using bounded concurrency and caching.
        Emits observed acquisition attempts with explicit attempt IDs and lineage.

        Returns:
            Tuple of (investigated_items, deep_read_telemetry)
        """
        from backend.services.agent_reach import agent_reach_service
        read_service = service if service is not None else agent_reach_service

        max_reads = max(0, int(max_reads)) if timeout_per_read > 0 else 0
        candidates_to_read, audit = self._select_read_candidates(ranked_candidates, max_reads=max_reads)
        now = time.time()
        read_deadline = time.monotonic() + max(0.0, timeout_per_read)
        telemetry = {
            "attempted": len(candidates_to_read),
            "successful": 0,
            "failed": 0,
            "cached": 0,
            "total_chars_read": 0,
            "read_urls": [],
            "candidate_selection_audit": audit,
            "acquisition_attempts": [],
        }

        def _fetch_url(item: EvidenceItem, attempt_id: str) -> Tuple[EvidenceItem, Dict[str, Any], str, float]:
            url = item.canonical_url
            t0 = time.perf_counter()
            from backend.services.research.source_registry import source_registry, source_body_scope, paced_source_request
            permission = source_registry.body_decision(url)
            if not permission['eligible']:
                return item, {'status': 'failed', 'failure_kind': permission['status'],
                    'source_permission': permission, 'network_observed': False}, attempt_id, 0.0
            # Check cache
            if url in self._cache:
                cached_res, ts = self._cache[url]
                if (now - ts) < self.cache_ttl:
                    cached_final = (cached_res.get('transport') or {}).get('endpoint')
                    if cached_final and not source_registry.body_decision(cached_final)['eligible']:
                        return item, {'status': 'failed', 'failure_kind': 'PERMISSION_REQUIRED',
                                      'network_observed': False}, attempt_id, 0.0
                    dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                    return item, cached_res, attempt_id, dur_ms

            try:
                # The transport is already byte/time bounded. Select the body
                # first, then retain a larger bounded research window rather
                # than discarding later financial/contextual paragraphs.
                with acquisition_deadline(read_deadline):
                    resolution = None
                    if (urlsplit(url).hostname or "").lower() == "news.google.com":
                        url, resolution = self._resolve_wrapper(item, read_service)
                        if not url:
                            return item, {"status": "failed", "error": "Publisher URL unresolved; wrapper is not article evidence",
                                          "failure_kind": "PUBLISHER_UNRESOLVED", "wrapper_resolution": resolution}, attempt_id, round((time.perf_counter() - t0) * 1000, 2)
                    permission = source_registry.body_decision(url)
                    if not permission['eligible']:
                        return item, {'status': 'failed', 'failure_kind': permission['status'],
                            'source_permission': permission, 'network_observed': False}, attempt_id, 0.0
                    robots = source_registry.robots_decision(url)
                    if not robots['eligible']:
                        return item, {'status': 'failed', 'failure_kind': robots['status'],
                            'robots_access': robots}, attempt_id, round((time.perf_counter()-t0)*1000, 2)
                    # Resolution above is discovery-only (perform_reads=False).
                    # Apply publisher body policy to actual body transport, not
                    # to the search engine used to locate its observed URL.
                    with source_body_scope(), paced_source_request(url):
                        res = read_service.read(url, max_chars=20_000 if service is not None else 12_000)
                    if permission.get('source_family') and permission['status'] != 'EXISTING_ROUTE_POLICY':
                        res = {**res, 'source_registry_managed': True}
                    if resolution:
                        res = {**res, "wrapper_resolution": resolution}
                dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                if res.get("status") in ("success", "fallback_soup") and res.get("markdown") and not _challenge_body(res["markdown"]):
                    self._cache[url] = (res, now)
                return item, res, attempt_id, dur_ms
            except Exception as e:
                dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                kind = transport_failure_kind(e)
                logger.debug("[DeepReader] Read failed (%s)", kind)
                observation = {"status": "error", "failure_kind": kind}
                if isinstance(e, ProviderHTTPError):
                    from backend.infrastructure.acquisition.adapters.web.response_diagnostics import safe_diagnostics
                    diagnostic = safe_diagnostics(e.response_diagnostics)
                    if diagnostic:
                        observation['native_response_diagnostics'] = diagnostic
                    observation.update(network_observed=e.network_observed,
                        transport={'http_status': e.status_code,
                                   'network_observed_this_attempt': e.network_observed})
                if isinstance(getattr(e, 'provider_failures', None), list):
                    observation['provider_failures'] = e.provider_failures[:3]
                return item, observation, attempt_id, dur_ms

        # Prepare attempt IDs
        candidate_attempts = []
        for item in candidates_to_read:
            # A scheduler may reserve the identity before worker submission so
            # interrupted work retains the same lifecycle record.
            att_id = (attempt_ids or {}).get(item.id) or f"acq_att_{uuid.uuid4().hex[:10]}"
            candidate_attempts.append((item, att_id))

        # Execute bounded concurrent reading
        # Wrapper resolution uses the shared two-worker web bulkhead. Do not
        # queue six short-lived resolver searches behind those same two slots.
        wrappers_only = bool(candidate_attempts) and all(
            (urlsplit(item.canonical_url).hostname or "").lower() == "news.google.com"
            for item, _ in candidate_attempts)
        max_workers = min(len(candidate_attempts) or 1, 2 if wrappers_only else 6)
        if max_concurrency is not None:
            max_workers = min(max_workers, max(1, min(6, int(max_concurrency))))
        completed_futures = set()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_to_info = {
                executor.submit(copy_context().run, _fetch_url, item, att_id): (item, att_id)
                for item, att_id in candidate_attempts
            }
            try:
                for fut in concurrent.futures.as_completed(future_to_info, timeout=max(0.0, timeout_per_read)):
                    completed_futures.add(fut)
                    orig_item, att_id = future_to_info[fut]
                    try:
                        item, read_res, attempt_id, dur_ms = fut.result(timeout=0.1)
                        res_status = read_res.get("status", "FAILED")
                        orig_item.read_status = res_status.upper()
                        backend_used = read_res.get("backend") or read_res.get("backend_id") or "scrapling_http"
                        
                        transport_success = bool(read_res.get("status") in ("success", "fallback_soup"))
                        content_body = (read_res.get("markdown") or read_res.get("content") or "").strip()
                        content_extraction_success = bool(transport_success and len(content_body) >= 30)
                        useful = bool(transport_success and content_extraction_success and not _challenge_body(content_body))
                        failure_kind = None if useful else _read_failure_kind(read_res, transport_success, content_body)

                        attempt_record = {
                            "attempt_id": attempt_id,
                            "candidate_id": orig_item.id,
                            "ranked_candidate_id": getattr(orig_item, "ranked_id", f"cand_rank_{orig_item.id}"),
                            "accepted_candidate_id": orig_item.accepted_id,
                            "url": orig_item.canonical_url,
                            "channel": getattr(orig_item, "channel", "web"),
                            "status": "SUCCESS" if useful else "FAILED",
                            "backend": backend_used,
                            "fallback_used": bool(read_res.get("fallback_used")),
                            "fallback_backend": read_res.get("fallback_backend"),
                            "duration_ms": dur_ms,
                            "transport_success": transport_success,
                            **({'network_observed': read_res['network_observed']} if 'network_observed' in read_res else {}),
                            "content_extraction_success": content_extraction_success,
                            "useful_content_extracted": useful,
                            "char_count": len(content_body) if useful else 0,
                            "failure_kind": failure_kind,
                            "http_status": _http_status(read_res),
                            "rejection_layer": ("DNS" if failure_kind and failure_kind.startswith("DNS_") else
                                                "SSRF" if read_res.get("status") == "blocked_ssrf" else
                                                "RUNTIME_POLICY" if read_res.get("runtime_decision") else None),
                            "error_message": failure_kind.replace("_", " ").capitalize() if failure_kind else None,
                        }
                        if isinstance(read_res.get('provider_failures'), list):
                            attempt_record['provider_failures'] = read_res['provider_failures'][:3]
                        from backend.infrastructure.acquisition.adapters.web.response_diagnostics import safe_diagnostics
                        diagnostic = safe_diagnostics(read_res.get('native_response_diagnostics') or
                            (read_res.get('page_metadata') or {}).get('native_response_diagnostics'))
                        if diagnostic:
                            attempt_record['native_response_diagnostics'] = diagnostic
                        if read_res.get("wrapper_resolution"):
                            attempt_record["wrapper_resolution"] = read_res["wrapper_resolution"]
                        if isinstance(read_res.get('robots_access'), dict):
                            attempt_record['robots_access'] = read_res['robots_access']
                        if isinstance(read_res.get('source_permission'), dict):
                            attempt_record['source_permission'] = read_res['source_permission']

                        if useful:
                            if read_res.get('source_registry_managed'):
                                orig_item.metadata['topic_source_controlled'] = True
                            resolution = read_res.get("wrapper_resolution") or {}
                            if resolution.get("selected_url"):
                                orig_item.metadata["discovery_url"] = orig_item.canonical_url
                                orig_item.canonical_url = resolution["selected_url"]
                                orig_item.metadata["wrapper_resolution"] = resolution
                            orig_item.content = content_body
                            orig_item.metadata["read_success"] = True
                            orig_item.metadata["char_count"] = len(content_body)
                            for key in ("raw_capture", "page_metadata", "transport", "truncated"):
                                if key in read_res:
                                    orig_item.metadata[key] = read_res[key]
                            # A validated native redirect is observed publisher
                            # provenance. Never attribute its body to the search
                            # click tracker, or to the optional reader host.
                            transport = read_res.get("transport") or {}
                            endpoint = transport.get("endpoint") or ""
                            redirects = transport.get("redirect_chain") or []
                            endpoint_host = (urlsplit(endpoint).hostname or "").lower()
                            if (endpoint and endpoint in redirects and endpoint_host not in {"r.jina.ai", "news.google.com"}
                                    and urlsplit(endpoint).scheme in {"http", "https"}
                                    and not urlsplit(endpoint).username and not urlsplit(endpoint).password):
                                if endpoint != orig_item.canonical_url:
                                    orig_item.metadata.setdefault("discovery_url", orig_item.canonical_url)
                                    orig_item.canonical_url = endpoint
                                orig_item.source_domain = endpoint_host
                                orig_item.metadata["observed_final_endpoint"] = endpoint
                            body_author = (read_res.get("page_metadata") or {}).get("author")
                            if body_author and orig_item.source_name and body_author != orig_item.source_name:
                                orig_item.metadata["discovery_author_or_source"] = orig_item.source_name
                                orig_item.metadata["body_author"] = body_author
                                orig_item.metadata["attribution_conflict"] = True
                                orig_item.source_name = body_author
                            orig_item.acquisition_attempt_id = attempt_id
                            orig_item.acquired_id = f"cand_acq_{orig_item.id}"
                            attempt_record["acquired_candidate_id"] = orig_item.acquired_id
                            from backend.services.research.body_context import reconcile_captured_context
                            reconcile_captured_context(orig_item)
                            if orig_item.metadata.get("discovery_kind") == "FEED_INDEX":
                                page = orig_item.metadata.setdefault("page_metadata", {})
                                if page.get("content_scope") not in {"FEED_INDEX", "SITEMAP_INDEX"}:
                                    page["content_scope"] = "PUBLIC_DISCOVERY_INDEX"
                            
                            # Preserve metadata kinds; length and official
                            # ownership never establish full-document coverage.
                            reported_depth = read_res.get("content_depth")
                            if not reported_depth and isinstance(read_res.get("video_metadata"), dict):
                                reported_depth = read_res["video_metadata"].get("content_depth")
                            if reported_depth in {"PROFILE_METADATA", "VIDEO_METADATA", "METADATA", "DIRECT_METADATA", "SOCIAL_POST", "VIDEO_TRANSCRIPT"}:
                                orig_item.content_depth = reported_depth
                            elif orig_item.primary_source:
                                orig_item.content_depth = ContentDepth.PRIMARY_DOCUMENT.value
                            else:
                                orig_item.content_depth = ContentDepth.PARTIAL_CONTENT.value

                            # Reassess the acquired body: an issuer index must
                            # not retain a pre-read PRIMARY label, nor a deeper
                            # thread retain a stale feed-summary completeness.
                            from backend.services.research.content_roles import document_role
                            role = document_role(orig_item)
                            if role in {"DOCUMENT_INDEX", "NEWS_INDEX", "LANDING_PAGE", "PROFILE"}:
                                orig_item.metadata["content_role"] = role
                                orig_item.primary_source = False
                                orig_item.source_role = SourceRole.DISCOVERY.value
                                if orig_item.content_depth == ContentDepth.PRIMARY_DOCUMENT.value:
                                    orig_item.content_depth = ContentDepth.PARTIAL_CONTENT.value
                            if orig_item.metadata.get("content_completeness") == "feed_summary":
                                orig_item.metadata["content_completeness"] = "BOUNDED_CAPTURE"

                            telemetry["successful"] += 1
                            telemetry["total_chars_read"] += len(content_body)
                            telemetry["read_urls"].append(orig_item.canonical_url)
                        else:
                            orig_item.read_status = "EMPTY_CONTENT" if transport_success else "FAILED"
                            telemetry["failed"] += 1

                        telemetry["acquisition_attempts"].append(attempt_record)

                    except Exception as ex:
                        orig_item.read_status = "TIMEOUT"
                        telemetry["failed"] += 1
                        telemetry["acquisition_attempts"].append({
                            "attempt_id": att_id,
                            "candidate_id": orig_item.id,
                            "ranked_candidate_id": getattr(orig_item, "ranked_id", f"cand_rank_{orig_item.id}"),
                            "accepted_candidate_id": orig_item.accepted_id,
                            "url": orig_item.canonical_url,
                            "channel": getattr(orig_item, "channel", "web"),
                            "status": "FAILED",
                            "backend": "timeout",
                            "duration_ms": int(timeout_per_read * 1000),
                            "useful_content_extracted": False,
                            "char_count": 0,
                            "failure_kind": "PROVIDER_FAILURE",
                            "error_message": "Source processing failed",
                        })
                        logger.debug("[DeepReader] Source processing failed (%s)", type(ex).__name__)

            except concurrent.futures.TimeoutError:
                logger.info("[DeepReader] Bounded deep-reading deadline reached; preserving existing reads.")
                for fut, (orig_item, att_id) in future_to_info.items():
                    if fut not in completed_futures:
                        orig_item.read_status = "TIMEOUT"
                        telemetry["failed"] += 1
                        telemetry["acquisition_attempts"].append({
                            "attempt_id": att_id,
                            "candidate_id": orig_item.id,
                            "ranked_candidate_id": getattr(orig_item, "ranked_id", f"cand_rank_{orig_item.id}"),
                            "accepted_candidate_id": orig_item.accepted_id,
                            "url": orig_item.canonical_url,
                            "channel": getattr(orig_item, "channel", "web"),
                            "status": "FAILED",
                            "backend": "timeout",
                            "duration_ms": int(timeout_per_read * 1000),
                            "useful_content_extracted": False,
                            "char_count": 0,
                            "error_message": "ThreadPoolExecutor timeout",
                            "failure_kind": "TIMEOUT",
                        })
        finally:
            # Context-manager shutdown waits for running calls and defeats the
            # deadline. Late workers only return/cache responses; they cannot
            # mutate dossier items after this method has returned.
            executor.shutdown(wait=False, cancel_futures=True)

        # Non-read items retain their status
        for c in ranked_candidates:
            if c not in candidates_to_read:
                c.read_status = "SKIPPED"

        # Return only successfully investigated items for strict evidence lineage
        successful_investigated = [c for c in candidates_to_read if getattr(c, "acquired_id", None) and getattr(c, "acquisition_attempt_id", None)]
        return successful_investigated, telemetry


deep_reader = DeepReader()
