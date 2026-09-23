"""
Aegis Protocol — Primary Source Escalator
=========================================
Identifies references to primary documentation (filings, press releases, court records)
within secondary articles and adaptively searches for the authoritative original source.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.services.research.research_models import ContentDepth, EvidenceItem, SourceRole, SourceTier

logger = logging.getLogger(__name__)

PRIMARY_REFERENCE_PATTERNS = [
    (re.compile(r'\b(?:in a|its|their)\s+(?:regulatory|exchange|securities|sec)\s+filing\b', re.I), "filing"),
    (re.compile(r'\b(?:press release|official statement|spokesperson said|company announced)\b', re.I), "official_statement"),
    (re.compile(r'\b(?:lawsuit filed|court document|complaint filed|consent decree)\b', re.I), "legal_filing"),
    (re.compile(r'\b(?:quarterly report|earnings release|form 10-k|form 10-q|form 8-k)\b', re.I), "financial_report"),
]


class PrimarySourceEscalator:
    """Detects secondary references to ground truth and escalates to primary sources."""

    def __init__(self):
        pass

    def detect_primary_references(self, candidates: List[EvidenceItem]) -> List[Dict[str, str]]:
        """Scans candidates for mentions of unretrieved primary documents."""
        detected = []
        for item in candidates:
            text = f"{item.title} {item.snippet} {item.relevant_excerpt}"
            for pattern, ref_type in PRIMARY_REFERENCE_PATTERNS:
                if pattern.search(text):
                    detected.append({
                        "item_id": item.id,
                        "ref_type": ref_type,
                        "source_title": item.title,
                        "canonical_url": item.canonical_url
                    })
                    break
        return detected

    def escalate(
        self,
        candidates: List[EvidenceItem],
        target_name: str,
        domain: str = "general",
        max_escalations: int = 2
    ) -> Tuple[List[EvidenceItem], Dict[str, Any]]:
        """
        If secondary candidates reference primary filings/statements and no primary
        source exists in candidates, issues targeted escalation queries.

        Returns:
            Tuple of (newly_discovered_primary_items, escalation_telemetry)
        """
        from backend.services.agent_reach import agent_reach_service

        telemetry = {
            "references_detected": 0,
            "escalation_queries_executed": 0,
            "primary_sources_found": 0,
            "queries": []
        }

        # Check if we already have strong primary sources
        existing_primary = [c for c in candidates if c.primary_source or c.source_role == SourceRole.PRIMARY.value]
        if len(existing_primary) >= 2:
            return [], telemetry

        refs = self.detect_primary_references(candidates)
        telemetry["references_detected"] = len(refs)

        if not refs:
            return [], telemetry

        discovered_primaries: List[EvidenceItem] = []
        clean_target = target_name.strip()

        # Build escalation query based on detected reference
        ref_types = set(r["ref_type"] for r in refs)
        escalation_queries = []
        if "filing" in ref_types or "financial_report" in ref_types:
            escalation_queries.append(f'"{clean_target}" regulatory filing annual report exchange disclosure')
        if "official_statement" in ref_types:
            escalation_queries.append(f'"{clean_target}" official announcement press release statement')

        for eq in escalation_queries[:max_escalations]:
            telemetry["escalation_queries_executed"] += 1
            telemetry["queries"].append(eq)
            try:
                # Query Web and RSS channels
                frags = agent_reach_service.search_channel("web", eq, limit=2)
                if not frags:
                    frags = agent_reach_service.search_channel("rss", eq, limit=2)

                for f in frags:
                    u = f.url or ""
                    # Ensure it's not already in candidates
                    if any(c.canonical_url == u for c in candidates if c.canonical_url):
                        continue

                    # Create typed EvidenceItem
                    item_id = f"esc_prim_{len(candidates) + len(discovered_primaries) + 1:03d}"
                    prim_item = EvidenceItem.from_evidence_fragment(f, item_id=item_id, target_name=clean_target)
                    prim_item.primary_source = True
                    prim_item.source_role = SourceRole.PRIMARY.value
                    prim_item.source_tier = SourceTier.TIER_1_OFFICIAL_FILING.value if "filing" in eq else SourceTier.TIER_1_ORIGINAL_DOCUMENT.value
                    prim_item.metadata["escalation_query"] = eq
                    prim_item.metadata["discovered_via"] = "primary_escalator"
                    discovered_primaries.append(prim_item)
                    telemetry["primary_sources_found"] += 1

            except Exception as e:
                logger.debug(f"[PrimarySourceEscalator] Escalation query error for '{eq}': {e}")

        return discovered_primaries, telemetry


primary_source_escalator = PrimarySourceEscalator()
