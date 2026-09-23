"""
Aegis Protocol — Corroboration Engine
=====================================
Calculates true independent corroboration across distinct source families.
Prevents wire service repetitions from inflating confirmation metrics,
and calibrates institutional confidence levels (HIGH, MEDIUM, LOW, INSUFFICIENT).
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services.research.research_models import ConfidenceLevel, EvidenceItem, SourceRole


class CorroborationEngine:
    """Evaluates independent confirmation without syndication bias."""

    def __init__(self):
        pass

    def evaluate_corroboration(
        self,
        supporting_items: List[EvidenceItem],
        contradicting_items: Optional[List[EvidenceItem]] = None
    ) -> Dict[str, Any]:
        """
        Calculates independent groups confirming a claim or finding.
        """
        contradicting_items = contradicting_items or []
        
        independent_groups: Set[str] = set()
        primary_sources: List[str] = []
        wire_repetitions: int = 0

        for item in supporting_items:
            # Check if primary
            if item.primary_source or item.source_role == SourceRole.PRIMARY.value:
                primary_sources.append(item.source_name or item.canonical_url)

            # Determine group
            group = item.independence_group or f"indep_{item.id}"
            if group in independent_groups:
                wire_repetitions += 1
            else:
                independent_groups.add(group)

        group_count = len(independent_groups)
        has_primary = len(primary_sources) > 0
        has_contradictions = len(contradicting_items) > 0

        # Calibrate confidence
        if has_primary and group_count >= 1:
            confidence = ConfidenceLevel.HIGH.value
        elif group_count >= 3:
            confidence = ConfidenceLevel.HIGH.value
        elif group_count == 2:
            confidence = ConfidenceLevel.MEDIUM.value if not has_contradictions else ConfidenceLevel.LOW.value
        elif group_count == 1:
            confidence = ConfidenceLevel.MEDIUM.value if not has_contradictions else ConfidenceLevel.LOW.value
        else:
            confidence = ConfidenceLevel.INSUFFICIENT.value

        return {
            "independent_group_count": group_count,
            "independent_groups": list(independent_groups),
            "primary_sources": list(set(primary_sources)),
            "primary_source_count": len(set(primary_sources)),
            "syndicated_repetition_count": wire_repetitions,
            "has_contradiction": has_contradictions,
            "contradiction_count": len(contradicting_items),
            "confidence": confidence,
        }


corroboration_engine = CorroborationEngine()
