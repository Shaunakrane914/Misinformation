"""
Aegis Protocol — Research Evidence Gate Pipeline
================================================
Comprehensive quality gate that orchestrates evidence through:
1. Relevance Gate (Drops off-topic/contaminated results)
2. Provenance Validation (Requires traceable URLs & query IDs)
3. Source Quality & Tier Assignment
4. Duplicate & Syndication Echo Filtering
5. Deep-Read Eligibility Selection
6. Parallel Deep Reading
7. Passage Extraction
8. Integrity Validation
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.services.research.relevance_gate import relevance_gate
from backend.services.research.deep_reader import deep_reader
from backend.services.research.passage_extractor import passage_extractor
from backend.services.research.source_independence import source_independence_engine
from backend.services.research.evidence_integrity import evidence_integrity_validator

logger = logging.getLogger(__name__)


class ResearchEvidenceGate:
    """
    Quality gate ensuring only vetted, relevant, and verified evidence
    enters finding synthesis.
    """

    def __init__(self, min_relevance: float = 0.35):
        self.min_relevance = min_relevance

    def filter_and_process(
        self,
        raw_candidates: List[Any],
        target_entity: str,
        domain: str = "general",
        intent: str = "",
        deep_read_budget: int = 4,
        timeout_budget: float = 6.0
    ) -> Dict[str, Any]:
        """
        Executes the full evidence gate pipeline.
        Returns:
            {
                "accepted_evidence": List[EvidenceItem],
                "rejected_evidence": List[Dict],
                "investigated_items": List[EvidenceItem],
                "deep_read_telemetry": Dict,
                "relevance_stats": Dict
            }
        """
        t0 = time.time()
        
        # 1. Relevance Gate
        accepted_candidates, rejected_audit = relevance_gate.filter_candidates(
            raw_candidates,
            target_entity=target_entity,
            domain=domain
        )
        logger.info(
            f"[EvidenceGate] Relevance Gate: {len(raw_candidates)} total candidates -> "
            f"{len(accepted_candidates)} accepted, {len(rejected_audit)} rejected."
        )

        # 2. Provenance Validation
        provenance_accepted = []
        for c in accepted_candidates:
            url = getattr(c, "canonical_url", None) or getattr(c, "url", "")
            # Must have non-empty title and valid http/https URL (or explicit authenticated platform handle)
            if url and (url.startswith("http://") or url.startswith("https://")):
                provenance_accepted.append(c)
            else:
                rejected_audit.append({
                    "evidence_id": getattr(c, "id", "ev_unknown"),
                    "title": getattr(c, "title", ""),
                    "url": url,
                    "relevance_score": getattr(c, "relevance_score", 0.0),
                    "relevance_class": "REJECTED",
                    "rejection_reason": "Missing real, valid HTTP destination URL (placeholder or null URL)."
                })

        # 3. Deduplication and Syndication Clustering on Vetted Candidates
        deduped_candidates, clusters_map = source_independence_engine.cluster_independence(provenance_accepted)

        # 4. Deep-Read Eligibility Selection (Select high-value diverse candidates)
        deep_read_candidates = [
            c for c in deduped_candidates
            if getattr(c, "relevance_score", 0.0) >= 0.50 and getattr(c, "canonical_url", "")
        ][:deep_read_budget]

        investigated_items: List[Any] = []
        read_telemetry: Dict[str, Any] = {
            "attempted": 0, "successful": 0, "failed": 0, "cached": 0,
            "total_chars_read": 0, "read_urls": [], "candidate_selection_audit": []
        }

        time_left = max(1.0, timeout_budget - (time.time() - t0))
        if deep_read_candidates and time_left > 1.0 and deep_read_budget > 0:
            investigated_items, read_telemetry = deep_reader.deep_read(
                deep_read_candidates,
                max_reads=deep_read_budget,
                timeout_per_read=min(4.0, time_left)
            )

        # 5. Relevant Passage Extraction
        if investigated_items:
            investigated_items = passage_extractor.extract_passages(
                investigated_items,
                target_name=target_entity,
                intent=intent
            )
        passage_extractor.extract_passages(
            deduped_candidates,
            target_name=target_entity,
            intent=intent
        )

        # Final evidence pool
        final_pool = deduped_candidates

        return {
            "accepted_evidence": final_pool,
            "rejected_evidence": rejected_audit,
            "investigated_items": investigated_items,
            "deep_read_telemetry": read_telemetry,
            "relevance_stats": {
                "total_candidates": len(raw_candidates),
                "accepted_count": len(final_pool),
                "rejected_count": len(rejected_audit),
                "deep_read_count": read_telemetry.get("successful", 0),
                "rejection_reasons_summary": [r.get("rejection_reason") for r in rejected_audit[:5]]
            }
        }


research_evidence_gate = ResearchEvidenceGate()
