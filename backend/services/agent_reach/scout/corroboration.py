"""
Aegis Protocol — Scout Corroboration & Contradiction Detection
==============================================================
Validates factual consistency across sources.
Identifies and preserves conflicting statements (e.g., deal value $2B vs $3B)
without destructive merging.
"""

from typing import List, Tuple
from backend.services.agent_reach.scout.models import (
    ContradictionRecord,
    EpistemicStatus,
    FinancialFact,
    ScoutEvidence,
    StoryCluster,
)


class ScoutCorroborationEngine:
    """
    Evaluates evidence corroboration across clusters and detects factual contradictions.
    """

    def analyze_corroboration(
        self,
        evidence_items: List[ScoutEvidence],
        clusters: List[StoryCluster]
    ) -> List[ContradictionRecord]:
        """
        Cross-checks financial facts across independent sources to find discrepancies.
        """
        contradictions: List[ContradictionRecord] = []
        if len(evidence_items) < 2:
            return contradictions

        # Group facts by metric and period
        metric_groups = {}
        for ev in evidence_items:
            for fact in ev.financial_facts:
                key = (fact.metric, fact.period or "all", fact.currency)
                if key not in metric_groups:
                    metric_groups[key] = []
                metric_groups[key].append((ev, fact))

        # Check for numeric contradictions within the same metric
        for (metric, period, curr), entries in metric_groups.items():
            if len(entries) < 2:
                continue

            # Compare pairs
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    ev_a, fact_a = entries[i]
                    ev_b, fact_b = entries[j]

                    # If normalized values differ by > 15% on the same metric and period
                    val_a = fact_a.normalized_value
                    val_b = fact_b.normalized_value

                    if val_a > 0 and val_b > 0 and metric != "general_financial":
                        ratio = max(val_a, val_b) / min(val_a, val_b)
                        if ratio > 1.20:  # >20% discrepancy
                            contradiction = ContradictionRecord(
                                metric_or_aspect=f"{metric} ({period})",
                                source_a_url=ev_a.url,
                                source_a_claim=f"{ev_a.author}: {fact_a.raw_value} ({fact_a.context_sentence[:100]})",
                                source_b_url=ev_b.url,
                                source_b_claim=f"{ev_b.author}: {fact_b.raw_value} ({fact_b.context_sentence[:100]})",
                                discrepancy_description=f"Conflicting values reported for {metric}: {fact_a.raw_value} vs {fact_b.raw_value}"
                            )
                            contradictions.append(contradiction)

        # Update cluster epistemic status if contradictions are present
        if contradictions:
            for cluster in clusters:
                cluster.epistemic_status = EpistemicStatus.CONTRADICTED
                cluster.contradictions.extend(contradictions)

        return contradictions


scout_corroboration_engine = ScoutCorroborationEngine()
