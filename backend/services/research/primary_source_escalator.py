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
    (re.compile(r'\b(?:according to a filing|in a regulatory filing|sec filing|regulatory notice|exchange disclosure)\b', re.I), "regulatory_filing"),
    (re.compile(r'\b(?:court documents show|lawsuit filed|court filing|complaint filed|consent decree)\b', re.I), "court_document"),
    (re.compile(r'\b(?:official statement|company said|spokesperson said|company announced|press release)\b', re.I), "official_statement"),
    (re.compile(r'\b(?:form 10-k|form 10-q|form 8-k|quarterly report|earnings release)\b', re.I), "financial_report"),
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

        # Build escalation query specs preserving originating evidence and trigger
        escalation_specs = []
        for r in refs:
            ref_type = r["ref_type"]
            item_id = r["item_id"]
            if ref_type in ("regulatory_filing", "financial_report"):
                escalation_specs.append({
                    "query": f'"{clean_target}" regulatory filing annual report exchange disclosure',
                    "ref_type": ref_type,
                    "originating_id": item_id
                })
            elif ref_type == "court_document":
                escalation_specs.append({
                    "query": f'"{clean_target}" court documents lawsuit legal complaint',
                    "ref_type": ref_type,
                    "originating_id": item_id
                })
            elif ref_type == "official_statement":
                escalation_specs.append({
                    "query": f'"{clean_target}" official announcement press release statement',
                    "ref_type": ref_type,
                    "originating_id": item_id
                })

        seen_queries = set()
        unique_specs = []
        for spec in escalation_specs:
            if spec["query"] not in seen_queries:
                seen_queries.add(spec["query"])
                unique_specs.append(spec)

        for spec in unique_specs[:max_escalations]:
            eq = spec["query"]
            originating_id = spec["originating_id"]
            ref_type = spec["ref_type"]
            q_id = f"q_esc_{len(telemetry['queries']) + 1:03d}"

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

                    # Create typed EvidenceItem with Requirement 16 provenance
                    item_id = f"esc_prim_{len(candidates) + len(discovered_primaries) + 1:03d}"
                    prim_item = EvidenceItem.from_evidence_fragment(f, item_id=item_id, target_name=clean_target)
                    prim_item.primary_source = True
                    prim_item.source_role = SourceRole.PRIMARY.value
                    prim_item.source_tier = SourceTier.TIER_1_OFFICIAL_FILING.value if "filing" in eq else SourceTier.TIER_1_ORIGINAL_DOCUMENT.value
                    
                    prim_item.metadata["originating_evidence_id"] = originating_id
                    prim_item.metadata["escalation_reason"] = ref_type
                    prim_item.metadata["primary_query_id"] = q_id
                    prim_item.metadata["primary_source_candidate"] = True
                    prim_item.metadata["escalation_query"] = eq
                    prim_item.metadata["discovered_via"] = "primary_escalator"
                    discovered_primaries.append(prim_item)
                    telemetry["primary_sources_found"] += 1

            except Exception as e:
                logger.debug(f"[PrimarySourceEscalator] Escalation query error for '{eq}': {e}")

        return discovered_primaries, telemetry


primary_source_escalator = PrimarySourceEscalator()
