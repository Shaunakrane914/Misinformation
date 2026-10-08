"""
Aegis Protocol — Diversity-Aware Deep Reader
============================================
Selects and executes deep reading across diverse, high-value candidate URLs.
Avoids consuming read budgets on syndicated duplicates, uses bounded concurrency,
preserves original snippets, and enriches evidence to FULL_ARTICLE depth.
"""

import concurrent.futures
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.research.research_models import ContentDepth, EvidenceItem, SourceRole, SourceTier

logger = logging.getLogger(__name__)

# Skip domains where direct text article reading is strictly blocked / requires closed auth
UNSUPPORTED_AUTH_DOMAINS = {
    "instagram.com", "tiktok.com", "facebook.com", "threads.net", "linkedin.com", "weibo.com"
}


class DeepReader:
    """Performs diversity-aware deep source acquisition and full-content extraction."""

    def __init__(self, cache_ttl_seconds: int = 900):
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}  # url -> (result_dict, timestamp)
        self.cache_ttl = cache_ttl_seconds

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

            if not url or not url.startswith("http"):
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
            elif item.relevance_score < 0.10:
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
            if item.id in seen_selected_ids or (item.canonical_url and item.canonical_url in seen_selected_urls):
                item.rejection_reason = "duplicate_candidate"
                continue

            domain = item.source_domain.lower() if item.source_domain else "other"
            if item.primary_source or item.source_role == SourceRole.PRIMARY.value or item.official_source:
                if primary_satisfied_count >= 5:
                    item.rejection_reason = "primary_already_satisfied"
                    continue
                selected.append(item)
                item.selected_for_read = True
                item.rejection_reason = None
                seen_selected_ids.add(item.id)
                if item.canonical_url:
                    seen_selected_urls.add(item.canonical_url)
                primary_satisfied_count += 1
                domain_items.setdefault(domain, []).append(item)
                if item.source_family_id:
                    seen_wire_families.add(item.source_family_id)

        # Step 3: Diverse Secondary and Investigative Selection
        for item in ranked_candidates:
            if not item.eligible_for_read:
                continue
            if item in selected or item.id in seen_selected_ids or (item.canonical_url and item.canonical_url in seen_selected_urls):
                item.rejection_reason = "duplicate_candidate"
                continue

            domain = item.source_domain.lower() if item.source_domain else "other"
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
                seen_selected_urls.add(item.canonical_url)
            domain_items.setdefault(domain, []).append(item)
            if item.source_family_id:
                seen_wire_families.add(item.source_family_id)

        # Assign explicit 5-stage selection telemetry and build audit list
        for rank, item in enumerate(ranked_candidates, 1):
            if item.selected_for_read:
                item.accepted_id = f"cand_acc_{item.id}"
                item.selection_decision = "ACCEPTED"
                item.selection_reason = "PRIMARY_DOCUMENT" if (item.primary_source or item.official_source) else "DIVERSE_SOURCE"
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
        timeout_per_read: float = 6.0
    ) -> Tuple[List[EvidenceItem], Dict[str, Any]]:
        """
        Deep-reads top diverse candidates using bounded concurrency and caching.
        Emits observed acquisition attempts with explicit attempt IDs and lineage.

        Returns:
            Tuple of (investigated_items, deep_read_telemetry)
        """
        from backend.services.agent_reach import agent_reach_service

        candidates_to_read, audit = self._select_read_candidates(ranked_candidates, max_reads=max_reads)
        now = time.time()
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
            # Check cache
            if url in self._cache:
                cached_res, ts = self._cache[url]
                if (now - ts) < self.cache_ttl:
                    dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                    return item, cached_res, attempt_id, dur_ms

            try:
                res = agent_reach_service.read(url, max_chars=4000)
                dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                if res.get("status") in ("success", "fallback_soup") and res.get("markdown"):
                    self._cache[url] = (res, now)
                return item, res, attempt_id, dur_ms
            except Exception as e:
                dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                logger.debug(f"[DeepReader] Failed reading {url}: {e}")
                return item, {"status": "error", "error": str(e), "url": url}, attempt_id, dur_ms

        # Prepare attempt IDs
        candidate_attempts = []
        for item in candidates_to_read:
            att_id = f"acq_att_{uuid.uuid4().hex[:10]}"
            candidate_attempts.append((item, att_id))

        # Execute bounded concurrent reading
        max_workers = min(len(candidate_attempts) or 1, 6)
        completed_futures = set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_info = {
                executor.submit(_fetch_url, item, att_id): (item, att_id)
                for item, att_id in candidate_attempts
            }
            try:
                for fut in concurrent.futures.as_completed(future_to_info, timeout=max(5.0, timeout_per_read * 2.0)):
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
                        useful = bool(transport_success and content_extraction_success)

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
                            "content_extraction_success": content_extraction_success,
                            "useful_content_extracted": useful,
                            "char_count": len(content_body) if useful else 0,
                            "error_message": read_res.get("error") if not useful else None,
                        }

                        if useful:
                            orig_item.content = content_body
                            orig_item.metadata["read_success"] = True
                            orig_item.metadata["char_count"] = len(content_body)
                            orig_item.acquisition_attempt_id = attempt_id
                            orig_item.acquired_id = f"cand_acq_{orig_item.id}"
                            attempt_record["acquired_candidate_id"] = orig_item.acquired_id
                            
                            # Upgrade content depth
                            if orig_item.primary_source:
                                orig_item.content_depth = ContentDepth.PRIMARY_DOCUMENT.value
                            elif len(content_body) > 1000:
                                orig_item.content_depth = ContentDepth.FULL_ARTICLE.value
                            else:
                                orig_item.content_depth = ContentDepth.PARTIAL_CONTENT.value

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
                            "error_message": str(ex),
                        })
                        logger.debug(f"[DeepReader] Task error on {orig_item.canonical_url}: {ex}")

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
                        })

        # Non-read items retain their status
        for c in ranked_candidates:
            if c not in candidates_to_read:
                c.read_status = "SKIPPED"

        # Return only successfully investigated items for strict evidence lineage
        successful_investigated = [c for c in candidates_to_read if getattr(c, "acquired_id", None) and getattr(c, "acquisition_attempt_id", None)]
        return successful_investigated, telemetry


deep_reader = DeepReader()
