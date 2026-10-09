"""Passage analysis, grounded finding synthesis, and evidence graphs."""

from typing import Any, Dict, List

from backend.application.research.contracts import Analysis, RankedEvidence, ReadEvidence
from backend.services.research.contradiction_detector import contradiction_detector
from backend.services.research.corroboration import corroboration_engine
from backend.services.research.evidence_graph import evidence_graph_builder
from backend.services.research.evidence_integrity import evidence_integrity_validator
from backend.services.research.passage_extractor import passage_extractor
from backend.services.research.research_models import (
    ContentDepth, EpistemicState, EvidenceItem, Finding, FindingType,
    QualityTensor, ResearchRequest, SourceRole, TemporalStatus,
)
from backend.services.research.source_lineage import source_lineage_engine


def synthesize_grounded_findings(
    target_name: str,
    domain: str,
    investigated_items: List[EvidenceItem],
    contradictions: List[Dict[str, Any]],
    intent: str = ""
) -> List[Finding]:
    """
    Synthesizes 3-6 concrete, evidence-grounded findings from deeply read passages.
    Every finding strictly maps to supporting evidence IDs.
    """
    findings: List[Finding] = []
    if not investigated_items:
        return findings

    # Group items by query_class
    class_map: Dict[str, List[EvidenceItem]] = {}
    for item in investigated_items:
        qc = item.query_class or "general"
        class_map.setdefault(qc, []).append(item)

    # Generate findings per significant query class
    for q_class, items_in_class in class_map.items():
        if len(findings) >= 6:
            break

        top_item = items_in_class[0]
        sup_ids = [it.id for it in items_in_class]
        
        # Find any contradictions matching these items
        matched_cont_ids = []
        for c in contradictions:
            if c.get("source_a_id") in sup_ids or c.get("source_b_id") in sup_ids:
                matched_cont_ids.append(c.get("source_b_id") if c.get("source_a_id") in sup_ids else c.get("source_a_id"))

        # Evaluate corroboration
        corrob = corroboration_engine.evaluate_corroboration(items_in_class)

        # Determine finding type based on domain & class
        f_type = FindingType.FACT.value
        if domain == "financial":
            if any(w in q_class for w in ["earnings", "financial", "filing"]):
                f_type = FindingType.CATALYST.value
            elif "risk" in q_class or "investigation" in q_class:
                f_type = FindingType.RISK.value
        elif domain == "trending":
            f_type = FindingType.TREND.value
        elif "scam" in q_class or "counterfeit" in q_class:
            f_type = FindingType.RISK.value

        # Format finding title and statement
        clean_class_title = q_class.replace("_", " ").title()
        title = f"{clean_class_title}: {top_item.title[:70]}"
        statement = top_item.relevant_excerpt or top_item.snippet or top_item.title
        
        # Identify primary sources among items
        prim_sources = [it.source_name for it in items_in_class if it.primary_source or it.source_role == SourceRole.PRIMARY.value]

        # Derive 6D Multidimensional Quality Tensor (Empirical Heuristic Model)
        total_items = max(1, len(items_in_class))
        avg_rel = sum(it.relevance_score for it in items_in_class) / total_items
        avg_sq = sum(it.source_quality_score for it in items_in_class) / total_items
        avg_rec = sum(it.recency_score for it in items_in_class) / total_items

        # Calibrated independence axis: ratio of independent clusters to total citations
        # Penalizes syndication echoes: 5 articles from 1 group = 1/5 = 0.20
        group_count = max(1, corrob.get("independent_group_count", 1))
        indep_ratio = min(1.0, group_count / total_items)
        indep_axis = max(0.15, min(1.0, 0.20 + 0.80 * indep_ratio))

        # Calibrated primary axis: proportion of citations that are verified primary filings
        prim_ratio = len(prim_sources) / total_items
        prim_axis = max(0.10, min(1.0, 0.30 + 0.70 * prim_ratio))
        cont_axis = 0.85 if matched_cont_ids else 0.05

        q_tensor = QualityTensor(
            relevance=round(avg_rel, 3),
            source_quality=round(avg_sq, 3),
            independence=round(indep_axis, 3),
            primary_weight=round(prim_axis, 3),
            freshness=round(avg_rec, 3),
            contradiction_level=round(cont_axis, 3),
            is_heuristic=True,
            scoring_model="aegis_heuristic_6d"
        )

        # Evaluate 6-State Epistemic Status
        if matched_cont_ids:
            ep_state = EpistemicState.CONTESTED.value
        elif prim_sources or corrob["independent_group_count"] >= 2:
            ep_state = EpistemicState.KNOWN_FACT.value
        elif len(items_in_class) >= 1:
            ep_state = EpistemicState.SUPPORTED.value
        else:
            ep_state = EpistemicState.UNVERIFIED.value

        f = Finding(
            finding_id=f"fnd_{domain[:2]}_{len(findings) + 1:03d}",
            title=title,
            statement=statement,
            type=f_type,
            importance="HIGH" if len(prim_sources) > 0 or corrob["independent_group_count"] >= 2 else "MEDIUM",
            confidence=corrob["confidence"],
            epistemic_state=ep_state,
            quality_tensor=q_tensor,
            supporting_evidence_ids=sup_ids,
            contradicting_evidence_ids=matched_cont_ids,
            independence_groups=corrob["independent_groups"],
            primary_sources=prim_sources,
            explanation=f"Substantiated across {corrob['independent_group_count']} independent source group(s) with {len(items_in_class)} citations.",
            temporal_status=TemporalStatus.NEW_EVENT.value,
            invalidation_criteria=f"Rebuttal or retraction issued by primary official channels ({', '.join(prim_sources) if prim_sources else 'official portal'})."
        )
        findings.append(f)

    return findings



class PassageAnalysisStage:
    def run(self, request: ResearchRequest, ranked: RankedEvidence, read: ReadEvidence) -> ReadEvidence:
        read.investigated = passage_extractor.extract_passages(
            read.investigated, target_name=request.target, intent=request.intent
        )
        passage_extractor.extract_passages(
            ranked.ranked, target_name=request.target, intent=request.intent
        )
        return read


class GroundedSynthesisStage:
    def run(self, request: ResearchRequest, ranked: RankedEvidence, read: ReadEvidence) -> Analysis:
        contradictions = contradiction_detector.detect_contradictions(
            read.investigated or ranked.ranked[:12], target_name=request.target
        )
        findings = synthesize_grounded_findings(
            target_name=request.target,
            domain=request.domain,
            investigated_items=read.investigated or ranked.ranked[:8],
            contradictions=contradictions,
            intent=request.intent,
        )
        valid_findings, integrity_report = evidence_integrity_validator.validate(
            findings=findings, evidence_pool=ranked.ranked, fail_on_invalid=True
        )
        return Analysis(contradictions, valid_findings, integrity_report, {}, {})


class EvidenceGraphStage:
    def run(self, ranked: RankedEvidence, analysis: Analysis) -> Analysis:
        analysis.graph = evidence_graph_builder.build_graph(
            findings=analysis.findings, evidence=ranked.ranked
        )
        analysis.lineage_graph = source_lineage_engine.build_lineage_graph(ranked.ranked)
        return analysis


# Canonical 10-stage architectural aliases
PassageExtractionStage = PassageAnalysisStage
SynthesisStage = GroundedSynthesisStage
GraphConstructionStage = EvidenceGraphStage

