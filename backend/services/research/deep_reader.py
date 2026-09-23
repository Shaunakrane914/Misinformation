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
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.research.research_models import ContentDepth, EvidenceItem, SourceRole, SourceTier

logger = logging.getLogger(__name__)

# Skip domains where direct text article reading is not applicable or blocked
SKIP_READ_DOMAINS = {
    "youtube.com", "youtu.be", "twitter.com", "x.com", "reddit.com",
    "instagram.com", "tiktok.com", "facebook.com"
}


class DeepReader:
    """Performs diversity-aware deep source acquisition and full-content extraction."""

    def __init__(self, cache_ttl_seconds: int = 900):
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}  # url -> (result_dict, timestamp)
        self.cache_ttl = cache_ttl_seconds

    def _select_read_candidates(
        self,
        ranked_candidates: List[EvidenceItem],
        max_reads: int = 8
    ) -> Tuple[List[EvidenceItem], List[Dict[str, Any]]]:
        """
        Selects top candidate sources prioritizing:
        1. Primary and official documents
        2. Domain diversity (up to 2 per domain, or 3 if covering novel query class/entity)
        3. Syndication diversity (max 1 per wire family)
        
        Audits every candidate with:
        - candidate_id
        - rank
        - score
        - eligible_for_read
        - selected
        - rejection_reason
        """
        selected: List[EvidenceItem] = []
        domain_items: Dict[str, List[EvidenceItem]] = {}
        seen_wire_families: Set[str] = set()
        primary_satisfied_count = 0
        audit: List[Dict[str, Any]] = []

        # Step 1: Preliminary Eligibility Assessment
        for rank, item in enumerate(ranked_candidates, 1):
            url = item.canonical_url or ""
            score = item.metadata.get("candidate_score", item.relevance_score)

            if not url or not url.startswith("http"):
                item.eligible_for_read = False
                item.selected_for_read = False
                item.rejection_reason = "unsupported_read"
            elif any(sd in url.lower() for sd in ["twitter.com", "x.com", "reddit.com", "instagram.com", "facebook.com", "threads.net"]):
                item.eligible_for_read = False
                item.selected_for_read = False
                item.rejection_reason = "social_only"
            elif any(sd in url.lower() for sd in ["youtube.com", "youtu.be", "bilibili.com"]):
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

            domain = item.source_domain.lower() if item.source_domain else "other"
            if item.primary_source or item.source_role == SourceRole.PRIMARY.value or item.official_source:
                if primary_satisfied_count >= 3:
                    item.rejection_reason = "primary_already_satisfied"
                    continue
                selected.append(item)
                item.selected_for_read = True
                item.rejection_reason = None
                primary_satisfied_count += 1
                domain_items.setdefault(domain, []).append(item)
                if item.source_family_id:
                    seen_wire_families.add(item.source_family_id)

        # Step 3: Diverse Secondary and Investigative Selection
        for item in ranked_candidates:
            if not item.eligible_for_read:
                continue
            if item in selected:
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
            domain_items.setdefault(domain, []).append(item)
            if item.source_family_id:
                seen_wire_families.add(item.source_family_id)

        # Build audit list for all candidates
        for rank, item in enumerate(ranked_candidates, 1):
            if item.selected_for_read:
                item.rejection_reason = None
            elif item.eligible_for_read and not item.rejection_reason:
                item.rejection_reason = "read_budget_exhausted"

            audit.append({
                "candidate_id": item.id,
                "rank": rank,
                "score": round(float(item.metadata.get("candidate_score", item.relevance_score)), 3),
                "eligible_for_read": item.eligible_for_read,
                "selected": item.selected_for_read,
                "rejection_reason": item.rejection_reason,
            })

        return selected, audit

    def deep_read(
        self,
        ranked_candidates: List[EvidenceItem],
        max_reads: int = 8,
        timeout_per_read: float = 6.0
    ) -> Tuple[List[EvidenceItem], Dict[str, Any]]:
        """
        Deep-reads top diverse candidates using bounded concurrency and caching.

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
        }

        def _fetch_url(item: EvidenceItem) -> Tuple[EvidenceItem, Dict[str, Any]]:
            url = item.canonical_url
            # Check cache
            if url in self._cache:
                cached_res, ts = self._cache[url]
                if (now - ts) < self.cache_ttl:
                    return item, cached_res

            try:
                res = agent_reach_service.read(url, max_chars=4000)
                if res.get("status") in ("success", "fallback_soup") and res.get("markdown"):
                    self._cache[url] = (res, now)
                return item, res
            except Exception as e:
                logger.debug(f"[DeepReader] Failed reading {url}: {e}")
                return item, {"status": "error", "error": str(e), "url": url}

        # Execute bounded concurrent reading
        max_workers = min(len(candidates_to_read) or 1, 5)
        completed_futures = set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {executor.submit(_fetch_url, item): item for item in candidates_to_read}
            try:
                for fut in concurrent.futures.as_completed(future_to_item, timeout=max(4.0, timeout_per_read * 1.5)):
                    completed_futures.add(fut)
                    orig_item = future_to_item[fut]
                    try:
                        item, read_res = fut.result(timeout=0.1)
                        orig_item.read_status = read_res.get("status", "FAILED").upper()
                        
                        if read_res.get("status") in ("success", "fallback_soup") and read_res.get("markdown"):
                            md = read_res["markdown"].strip()
                            if len(md) > 200:
                                orig_item.content = md
                                orig_item.metadata["read_success"] = True
                                orig_item.metadata["char_count"] = len(md)
                                
                                # Upgrade content depth
                                if orig_item.primary_source:
                                    orig_item.content_depth = ContentDepth.PRIMARY_DOCUMENT.value
                                elif len(md) > 1000:
                                    orig_item.content_depth = ContentDepth.FULL_ARTICLE.value
                                else:
                                    orig_item.content_depth = ContentDepth.PARTIAL_CONTENT.value

                                telemetry["successful"] += 1
                                telemetry["total_chars_read"] += len(md)
                                telemetry["read_urls"].append(orig_item.canonical_url)
                            else:
                                orig_item.read_status = "EMPTY_CONTENT"
                                telemetry["failed"] += 1
                        else:
                            telemetry["failed"] += 1

                    except Exception as ex:
                        orig_item.read_status = "TIMEOUT"
                        telemetry["failed"] += 1
                        logger.debug(f"[DeepReader] Task error on {orig_item.canonical_url}: {ex}")

            except concurrent.futures.TimeoutError:
                logger.info("[DeepReader] Bounded deep-reading deadline reached; preserving existing reads.")
                for fut, orig_item in future_to_item.items():
                    if fut not in completed_futures:
                        orig_item.read_status = "TIMEOUT"
                        telemetry["failed"] += 1

        # Non-read items retain their status
        for c in ranked_candidates:
            if c not in candidates_to_read:
                c.read_status = "SKIPPED"

        return candidates_to_read, telemetry


deep_reader = DeepReader()
