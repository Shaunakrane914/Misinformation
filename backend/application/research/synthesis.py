"""Passage analysis, grounded finding synthesis, and evidence graphs."""

from typing import Any, Dict, List
import re
import os

from backend.application.research.contracts import Analysis, RankedEvidence, ReadEvidence
from backend.services.research.contradiction_detector import contradiction_detector
from backend.services.research.corroboration import corroboration_engine
from backend.services.research.evidence_graph import evidence_graph_builder
from backend.services.research.evidence_integrity import evidence_integrity_validator
from backend.services.research.passage_extractor import has_usable_passage, passage_extractor
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
    investigated_items = [item for item in investigated_items if has_usable_passage(item)]
    financial_contexts = {}
    if domain == "financial":
        from backend.services.research.financial_context import financial_passage_context
        for item in investigated_items:
            financial_contexts[item.id] = financial_passage_context(item.relevant_excerpt,
                title=item.title, published_at=item.published_at,
                observed_at=item.metadata.get("acquired_at") or item.metadata.get("retrieved_at") or item.discovered_at,
                issuer=target_name, intent=intent)
        # Historical captures remain in the corpus/evidence inspection. They
        # cannot become a current financial finding merely because a query
        # returned an old, relevant article. Unknown dates stay explicitly
        # undated observations, not current performance verification.
        investigated_items = [item for item in investigated_items
            if financial_contexts[item.id]["publication_scope"] not in {"HISTORICAL_BACKGROUND", "FUTURE_PUBLICATION"}
            or financial_contexts[item.id]["assessment_eligible"]]
    if domain == "trending":
        # Casual community conversation is retained in evidence/inspection but
        # is not a strategic event merely because it mentions the topic.
        investigated_items = [item for item in investigated_items
            if item.channel.casefold() not in {"reddit", "twitter", "twitter/x"}
            or re.search(r"announc|launch|releas|report|claim|deni|alleg|scam|deepfake|counterfeit|lawsuit|regulat|protest",
                         item.relevant_excerpt or "", re.I)]
        investigated_items.sort(key=lambda item: (item.metadata.get("trend_source_context") or {}).get("classification") == "COMPETITIVE_CONTEXT")
    if not investigated_items:
        return findings

    # A shared discovery query is not a shared proposition. Only identical
    # observed passages may share a finding/citation group; paraphrase-level
    # corroboration requires separate entailment evaluation.
    class_map: Dict[tuple, List[EvidenceItem]] = {}
    for item in investigated_items:
        qc = item.query_class or "general"
        passage = re.sub(r"\s+", " ", item.relevant_excerpt or item.snippet or item.title).strip().casefold()
        class_map.setdefault((qc, passage), []).append(item)

    # Generate findings per significant query class
    for (q_class, _passage), items_in_class in class_map.items():
        if len(findings) >= 6:
            break

        top_item = items_in_class[0]
        sup_ids = [it.id for it in items_in_class]
        
        # Find any contradictions matching these items
        matched_cont_ids = []
        for c in contradictions:
            if c.get("established") is False or c.get("type") == "POSSIBLE_DISAGREEMENT":
                continue
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
        community_observation = domain == "trending" and top_item.channel.casefold() in {"reddit", "twitter", "twitter/x"}
        if community_observation:
            clean_class_title = "Sampled Community Observation — Not Measured Virality"
        financial_context = financial_contexts.get(top_item.id)
        if financial_context and financial_context["publication_scope"] == "UNKNOWN_PUBLICATION_OR_CAPTURE_TIME":
            clean_class_title = "Undated Financial Observation — Current Period Unverified"
        elif financial_context and financial_context["assessment_scope"] == "HISTORICAL_REQUEST":
            clean_class_title = "Historical Financial Context — Not Current Performance"
        elif financial_context and financial_context["content_kind"] == "CORPORATE_STRATEGY_CONTEXT":
            clean_class_title = "Corporate Strategy Context — Not Financial Verification"
            f_type = FindingType.EVENT.value
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

        # An original document (e.g. an arbitrary GitHub repository) is not an
        # authenticated authority. Neither a primary-role label nor unrelated
        # results sharing a query class are sufficient to declare a known fact.
        # Evaluate 6-State Epistemic Status
        if matched_cont_ids:
            ep_state = EpistemicState.CONTESTED.value
        else:
            ep_state = EpistemicState.UNVERIFIED.value

        f = Finding(
            finding_id=f"fnd_{domain[:2]}_{len(findings) + 1:03d}",
            title=title,
            statement=statement,
            type=f_type,
            importance="LOW" if community_observation or (top_item.metadata.get("trend_source_context") or {}).get("classification") == "COMPETITIVE_CONTEXT"
                or (financial_context and not financial_context["current_assessment_eligible"])
                or (financial_context and financial_context["content_kind"] == "CORPORATE_STRATEGY_CONTEXT")
                else "HIGH" if len(prim_sources) > 0 or corrob["independent_group_count"] >= 2 else "MEDIUM",
            confidence=corrob["confidence"],
            epistemic_state=ep_state,
            quality_tensor=q_tensor,
            supporting_evidence_ids=sup_ids,
            contradicting_evidence_ids=matched_cont_ids,
            independence_groups=corrob["independent_groups"],
            primary_sources=prim_sources,
            explanation=f"Observed passages from {corrob['independent_group_count']} publisher group(s) with {len(items_in_class)} citations; claim support requires proposition-level assessment.",
            metadata={"observation_only": True, "citation_entailment_verified": False,
                      **({"financial_context": financial_context} if financial_context else {}),
                      **({"source_context": top_item.metadata["trend_source_context"]} if top_item.metadata.get("trend_source_context") else {}),
                      **({"community_sample_only": True, "virality_measured": False} if community_observation else {})},
            temporal_status=TemporalStatus.HISTORICAL_CONTEXT.value
                if financial_context and financial_context["assessment_scope"] == "HISTORICAL_REQUEST" else TemporalStatus.UNKNOWN.value,
            invalidation_criteria=f"Rebuttal or retraction issued by primary official channels ({', '.join(prim_sources) if prim_sources else 'official portal'})."
        )
        findings.append(f)

    return findings



class PassageAnalysisStage:
    def run(self, request: ResearchRequest, ranked: RankedEvidence, read: ReadEvidence, advisor_timeout=0.0) -> ReadEvidence:
        from backend.services.research.source_identity import unique_captures
        read.telemetry["duplicate_captures"] = []
        read.investigated = unique_captures(read.investigated, read.telemetry["duplicate_captures"])
        from backend.services.research.body_context import reconcile_captured_context
        from backend.services.research.relevance_gate import relevance_gate
        for item in read.investigated:
            if request.domain == "trending":
                item.metadata["temporal_required"] = True
            reconcile_captured_context(item)
            if request.domain == "trending":
                # Recheck the acquired page, not its provisional snippet.
                result = relevance_gate.evaluate_item(item, request.target, domain="trending", intent=request.intent,
                    window_hours=request.extra_params.get("trending_window_hours"))
                item.metadata["temporal_eligible"] = result.is_accepted
                item.metadata["post_read_qualification_reason"] = result.rejection_reason
        read.investigated = passage_extractor.extract_passages(
            read.investigated, target_name=request.target, intent=request.intent, domain=request.domain
        )
        from backend.services.research.body_context import reconcile_captured_context
        for item in read.investigated:
            reconcile_captured_context(item)
        passage_extractor.extract_passages(
            ranked.ranked, target_name=request.target, intent=request.intent, domain=request.domain
        )
        from backend.services.research.passage_records import captured_passages
        from backend.services.research.financial_observations import financial_observations
        for item in {item.id: item for item in ranked.ranked + read.investigated}.values():
            item.metadata["passages"] = captured_passages(item, request.domain, request.target)
            if request.domain == "financial":
                item.metadata["financial_observations"] = financial_observations(item.content or "", item.id)
        if os.getenv("AEGIS_EVIDENCE_ADVISOR_ENABLED", "false").lower() in {"1", "true", "yes"} and advisor_timeout > 0:
            from backend.services.research.evidence_advisor import EvidenceAdvisor
            advice = EvidenceAdvisor().advise(request, read.investigated, timeout=advisor_timeout)
            if advice["status"] != "SKIPPED_NOT_NEEDED":
                read.telemetry["ai_passage_advice"] = advice
        return read


class GroundedSynthesisStage:
    def run(self, request: ResearchRequest, ranked: RankedEvidence, read: ReadEvidence) -> Analysis:
        contradictions = contradiction_detector.detect_contradictions(
            read.investigated or ranked.ranked[:12], target_name=request.target
        )
        findings = synthesize_grounded_findings(
            target_name=request.target,
            domain=request.domain,
            investigated_items=read.investigated,
            contradictions=contradictions,
            intent=request.intent,
        )
        exact_claim = request.extra_params.get("claim_text") or (request.target if request.domain == "fact_check" else "")
        if re.fullmatch(r"https?://\S+", exact_claim.strip(), re.I):
            # A caller-supplied source URL is not itself a factual proposition.
            exact_claim = ""
        if request.domain != "fact_check" and exact_claim.strip().casefold() == re.sub(r"\([^)]*\)", "", request.target).strip().casefold():
            exact_claim = ""
        if exact_claim:
            # Reuse the shared proposition assessor, not a second verdict path.
            # Entity scans without a claim retain explicitly unverified observations.
            from backend.services.research.claim_intelligence import claim_intelligence_engine
            claims = claim_intelligence_engine.decompose_claims(exact_claim)[:6]
            if claims:
                findings = []
            for index, claim in enumerate(claims, 1):
                if request.domain != "fact_check":
                    claim.entity = re.sub(r"\([^)]*\)", "", request.target).strip()
                evaluated = claim_intelligence_engine.evaluate_claim(claim, read.investigated)
                assessment = evaluated.to_dict()
                assessment.update(is_heuristic=True, confidence_model="uncalibrated_conservative_lexical")
                if request.domain == "financial":
                    from backend.services.research.financial_observations import compare_financial_observations
                    assessment["financial_comparisons"] = compare_financial_observations(claim.claim_text,
                        [o for item in read.investigated for o in item.metadata.get("financial_observations", [])])
                state = evaluated.verdict if evaluated.verdict in {"SUPPORTED", "REFUTED"} else "CONTESTED" if evaluated.verdict == "MIXED" else "UNVERIFIED"
                findings.append(Finding(
                    finding_id=f"fnd_claim_{index:03d}", title=f"{evaluated.verdict}: {evaluated.claim_text[:100]}",
                    statement=evaluated.claim_text, confidence="INSUFFICIENT" if not evaluated.evidence_citations else "LOW",
                    quality_tensor=None,  # No measured six-axis tensor for a proposition assessment.
                    epistemic_state=state, temporal_status=TemporalStatus.UNKNOWN.value,
                    supporting_evidence_ids=evaluated.supporting_evidence_ids,
                    contradicting_evidence_ids=evaluated.contradicting_evidence_ids,
                    explanation=evaluated.rationale,
                    metadata={"claim_assessment": assessment, "observation_only": False},
                ))
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

