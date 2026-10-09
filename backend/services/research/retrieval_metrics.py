"""
Aegis Protocol — Rigorous Information Retrieval Metrics Engine
==============================================================
Standard mathematical formulations for candidate ranking evaluation.

Relevance Definitions:
- Broad Relevance (Default): gold_grade >= 2 (Grade 3: Direct True Positive, Grade 2: Secondary Relevant)
- Strict Relevance: gold_grade == 3 (Direct Target Entity + Exact Intent only)
- Non-relevant: gold_grade <= 1 (Grade 1: Boundary Distractor, Grade 0: Adversarial Hard Negative / Homograph)

Mathematical Formulations:
1. Precision@k:
   P@k = (Count of items in top-k with grade >= threshold) / k
   Evaluated at natural pool cutoffs k in {1, 3, 4} (and reference k=5).

2. Recall@k (Cranfield/TREC Formulation):
   Recall@k = (Count of items in top-k with grade >= threshold) / R_query
   Evaluated strictly over queries with R_query >= 1. Queries with R_query == 0 return None
   and are excluded from macro-averaging.

3. Mean Reciprocal Rank (MRR):
   RR = 1 / rank* of the first candidate with grade >= threshold (1-indexed).

4. Normalized Discounted Cumulative Gain (nDCG@k):
   DCG@k = sum_{i=1}^{min(|G|, k)} (2^{grade_i} - 1) / log2(i + 1)
   IDCG@k = DCG@k of the ideal ranking (sorted descending by gold grade)
   nDCG@k = DCG@k / IDCG@k

5. Hard-Negative Metrics:
   - top1_hard_negative_avoidance:
     Fraction of scenarios containing Grade 0 items where Rank-1 candidate is NOT Grade 0.
   - candidate_hard_negative_rejection_rate:
     Fraction of all Grade 0 candidates in the pool that were rejected (is_accepted == False)
     by the production relevance gate.

6. Entity & Intent Accuracy Metrics:
   - entity_accuracy_at_1: Fraction of scenarios where Rank-1 matches canonical target entity.
   - top_k_entity_density: Mean fraction of top-k candidates that match canonical target entity.
   - intent_accuracy_at_1: Fraction of scenarios where Rank-1 matches intended domain intent.
   - top_k_intent_density: Mean fraction of top-k candidates that match intended domain intent.
"""

import math
from typing import Any, Dict, List, Optional, Tuple


def compute_precision_at_k(ranked_grades: List[int], k: int, threshold: int = 2) -> float:
    """Standard Precision@k with fixed denominator k."""
    if k <= 0:
        return 0.0
    top_k_grades = ranked_grades[:k]
    relevant_count = sum(1 for g in top_k_grades if g >= threshold)
    return round(relevant_count / float(k), 4)


def compute_recall_at_k(ranked_grades: List[int], total_relevant: int, k: int, threshold: int = 2) -> Optional[float]:
    """
    Standard Cranfield Recall@k.
    Returns None if total_relevant == 0 (query has no relevant documents in corpus;
    recall is undefined and excluded from macro-averaging).
    """
    if total_relevant <= 0:
        return None
    top_k_grades = ranked_grades[:k]
    relevant_retrieved = sum(1 for g in top_k_grades if g >= threshold)
    return round(min(1.0, relevant_retrieved / float(total_relevant)), 4)


def compute_reciprocal_rank(ranked_grades: List[int], threshold: int = 2) -> float:
    """Reciprocal Rank of first relevant candidate."""
    for rank_idx, g in enumerate(ranked_grades, 1):
        if g >= threshold:
            return round(1.0 / rank_idx, 4)
    return 0.0


def compute_dcg_at_k(ranked_grades: List[int], k: int) -> float:
    """Discounted Cumulative Gain at k using exponential gain (2^rel - 1) / log2(rank + 1)."""
    dcg = 0.0
    for idx, grade in enumerate(ranked_grades[:k]):
        gain = (2.0 ** grade) - 1.0
        discount = math.log2(idx + 2)
        dcg += gain / discount
    return dcg


def compute_ndcg_at_k(ranked_grades: List[int], all_candidate_grades: List[int], k: int) -> float:
    """Normalized Discounted Cumulative Gain at k."""
    actual_dcg = compute_dcg_at_k(ranked_grades, k)
    ideal_grades = sorted(all_candidate_grades, reverse=True)
    ideal_dcg = compute_dcg_at_k(ideal_grades, k)

    if ideal_dcg <= 0.0:
        return 1.0 if actual_dcg == 0.0 else 0.0

    return round(min(1.0, actual_dcg / ideal_dcg), 4)


def evaluate_ranking_run(
    ranked_candidates: List[Dict[str, Any]],
    all_candidates: List[Dict[str, Any]],
    labels_by_cand_id: Dict[str, Dict[str, Any]],
    target_canonical: str,
    target_intent: str,
    pool_size: int = 4,
) -> Dict[str, Any]:
    """
    Evaluate a single scenario ranking run with exact metric calculations.
    """
    if not ranked_candidates:
        return {"status": "NOT_EVALUABLE", "error": "Empty ranked candidates"}

    ranked_grades = []
    all_grades = [
        labels_by_cand_id[c["candidate_id"]]["gold_grade"]
        for c in all_candidates
        if c.get("candidate_id") in labels_by_cand_id
    ]

    total_broad_relevant = sum(1 for g in all_grades if g >= 2)
    total_strict_relevant = sum(1 for g in all_grades if g == 3)
    has_hard_negative = any(g == 0 for g in all_grades)

    entity_matches_in_pool = 0
    intent_matches_in_pool = 0
    grade0_total = 0
    grade0_gate_rejected = 0

    for idx, c in enumerate(ranked_candidates):
        cid = c.get("candidate_id")
        lb = labels_by_cand_id.get(cid, {})
        grade = lb.get("gold_grade", 0)
        ranked_grades.append(grade)

        # Entity match check
        cand_entity = lb.get("gold_entity", "").lower()
        if target_canonical.lower() in cand_entity or cand_entity in target_canonical.lower():
            entity_matches_in_pool += 1

        # Intent match check
        cand_intent = lb.get("gold_intent", "").lower()
        if target_intent.lower() in cand_intent or cand_intent in target_intent.lower() or grade == 3:
            intent_matches_in_pool += 1

        # Gate-level rejection audit for Grade 0 items
        if grade == 0:
            grade0_total += 1
            if not c.get("is_accepted", True):
                grade0_gate_rejected += 1

    top1 = ranked_candidates[0] if ranked_candidates else {}
    top1_cid = top1.get("candidate_id")
    top1_label = labels_by_cand_id.get(top1_cid, {})
    top1_grade = top1_label.get("gold_grade", 0)

    # Rank 1 entity accuracy
    top1_entity = top1_label.get("gold_entity", "").lower()
    entity_acc_at_1 = 1.0 if (target_canonical.lower() in top1_entity or top1_entity in target_canonical.lower()) else 0.0

    # Rank 1 intent accuracy
    top1_intent = top1_label.get("gold_intent", "").lower()
    intent_acc_at_1 = 1.0 if (target_intent.lower() in top1_intent or top1_intent in target_intent.lower() or top1_grade == 3) else 0.0

    # Avoidance of hard negative at Rank 1
    top1_is_grade0 = (top1_grade == 0)

    k_eval = max(1, len(ranked_candidates))

    return {
        # Broad metrics (grade >= 2)
        "p_at_1": compute_precision_at_k(ranked_grades, 1, threshold=2),
        "p_at_3": compute_precision_at_k(ranked_grades, 3, threshold=2),
        "p_at_4": compute_precision_at_k(ranked_grades, 4, threshold=2),
        "p_at_5": compute_precision_at_k(ranked_grades, 5, threshold=2),

        # Strict metrics (grade == 3)
        "strict_p_at_1": compute_precision_at_k(ranked_grades, 1, threshold=3),
        "strict_p_at_3": compute_precision_at_k(ranked_grades, 3, threshold=3),
        "strict_p_at_4": compute_precision_at_k(ranked_grades, 4, threshold=3),

        # Cranfield Recall metrics (defined strictly if relevant items exist in pool)
        "recall_at_1": compute_recall_at_k(ranked_grades, total_broad_relevant, 1, threshold=2),
        "recall_at_3": compute_recall_at_k(ranked_grades, total_broad_relevant, 3, threshold=2),
        "recall_at_4": compute_recall_at_k(ranked_grades, total_broad_relevant, 4, threshold=2),
        "recall_at_5": compute_recall_at_k(ranked_grades, total_broad_relevant, 5, threshold=2),

        # Ordering & ranking
        "mrr": compute_reciprocal_rank(ranked_grades, threshold=2),
        "strict_mrr": compute_reciprocal_rank(ranked_grades, threshold=3),
        "ndcg_at_3": compute_ndcg_at_k(ranked_grades, all_grades, 3),
        "ndcg_at_4": compute_ndcg_at_k(ranked_grades, all_grades, 4),
        "ndcg_at_5": compute_ndcg_at_k(ranked_grades, all_grades, 5),

        # Accuracy & Densities
        "entity_accuracy_at_1": entity_acc_at_1,
        "top_k_entity_density": round(entity_matches_in_pool / float(k_eval), 4),
        "intent_accuracy_at_1": intent_acc_at_1,
        "top_k_intent_density": round(intent_matches_in_pool / float(k_eval), 4),

        # Hard negative metrics
        "has_hard_negative": has_hard_negative,
        "top1_is_grade0": top1_is_grade0,
        "grade0_total": grade0_total,
        "grade0_gate_rejected": grade0_gate_rejected,

        "total_broad_relevant": total_broad_relevant,
        "total_strict_relevant": total_strict_relevant,
        "ranked_grades": ranked_grades,
        "top1_grade": top1_grade,
    }


def aggregate_metrics(scenario_evals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate per-scenario metric results into mean macro metrics.
    Averages recall strictly over scenarios where relevant documents exist (R_query > 0).
    """
    if not scenario_evals:
        return {
            "status": "NOT_EVALUABLE",
            "p_at_1": 0.0,
            "p_at_3": 0.0,
            "p_at_4": 0.0,
            "strict_p_at_1": 0.0,
            "recall_at_1": 0.0,
            "recall_at_3": 0.0,
            "recall_at_4": 0.0,
            "mrr": 0.0,
            "ndcg_at_3": 0.0,
            "ndcg_at_4": 0.0,
            "entity_accuracy_at_1": 0.0,
            "top_k_entity_density": 0.0,
            "entity_accuracy": 0.0,
            "intent_accuracy_at_1": 0.0,
            "top_k_intent_density": 0.0,
            "intent_accuracy": 0.0,
            "top1_hard_negative_avoidance": 0.0,
            "candidate_hard_negative_rejection_rate": 0.0,
            "hard_negative_rejection_rate": 0.0,
            "evaluable_scenarios": 0,
            "recall_evaluable_scenarios": 0,
            "hard_negative_scenarios": 0,
        }

    n = float(len(scenario_evals))

    # Recall is averaged strictly over scenarios that have at least 1 relevant candidate
    recall_evals_1 = [s["recall_at_1"] for s in scenario_evals if s.get("recall_at_1") is not None]
    recall_evals_3 = [s["recall_at_3"] for s in scenario_evals if s.get("recall_at_3") is not None]
    recall_evals_4 = [s["recall_at_4"] for s in scenario_evals if s.get("recall_at_4") is not None]
    recall_evals_5 = [s["recall_at_5"] for s in scenario_evals if s.get("recall_at_5") is not None]

    mean_rec_1 = round(sum(recall_evals_1) / float(len(recall_evals_1)), 4) if recall_evals_1 else 0.0
    mean_rec_3 = round(sum(recall_evals_3) / float(len(recall_evals_3)), 4) if recall_evals_3 else 0.0
    mean_rec_4 = round(sum(recall_evals_4) / float(len(recall_evals_4)), 4) if recall_evals_4 else 0.0
    mean_rec_5 = round(sum(recall_evals_5) / float(len(recall_evals_5)), 4) if recall_evals_5 else 0.0

    # Top-1 Hard Negative Avoidance: over scenarios possessing grade 0 candidates
    hn_scenarios = [s for s in scenario_evals if s.get("has_hard_negative")]
    if hn_scenarios:
        hn_leaks_at_1 = sum(1 for s in hn_scenarios if s.get("top1_is_grade0"))
        top1_hn_avoidance = round(1.0 - (hn_leaks_at_1 / float(len(hn_scenarios))), 4)
    else:
        top1_hn_avoidance = 1.0

    # Candidate-level Hard Negative Rejection Rate: across all grade 0 candidates in the pool
    tot_g0 = sum(s.get("grade0_total", 0) for s in scenario_evals)
    rej_g0 = sum(s.get("grade0_gate_rejected", 0) for s in scenario_evals)
    cand_hn_rejection_rate = round(rej_g0 / float(tot_g0), 4) if tot_g0 > 0 else 1.0

    return {
        "status": "EVALUATED",
        # Broad precision (grade >= 2)
        "p_at_1": round(sum(s["p_at_1"] for s in scenario_evals) / n, 4),
        "p_at_3": round(sum(s["p_at_3"] for s in scenario_evals) / n, 4),
        "p_at_4": round(sum(s["p_at_4"] for s in scenario_evals) / n, 4),
        "p_at_5": round(sum(s["p_at_5"] for s in scenario_evals) / n, 4),

        # Strict precision (grade == 3)
        "strict_p_at_1": round(sum(s["strict_p_at_1"] for s in scenario_evals) / n, 4),
        "strict_p_at_3": round(sum(s["strict_p_at_3"] for s in scenario_evals) / n, 4),
        "strict_p_at_4": round(sum(s["strict_p_at_4"] for s in scenario_evals) / n, 4),

        # Cranfield-valid recall
        "recall_at_1": mean_rec_1,
        "recall_at_3": mean_rec_3,
        "recall_at_4": mean_rec_4,
        "recall_at_5": mean_rec_5,

        # Ordering & ranking
        "mrr": round(sum(s["mrr"] for s in scenario_evals) / n, 4),
        "strict_mrr": round(sum(s["strict_mrr"] for s in scenario_evals) / n, 4),
        "ndcg_at_3": round(sum(s["ndcg_at_3"] for s in scenario_evals) / n, 4),
        "ndcg_at_4": round(sum(s["ndcg_at_4"] for s in scenario_evals) / n, 4),
        "ndcg_at_5": round(sum(s["ndcg_at_5"] for s in scenario_evals) / n, 4),

        # Disambiguation accuracy at Rank 1 & pool densities
        "entity_accuracy_at_1": round(sum(s.get("entity_accuracy_at_1", 0.0) for s in scenario_evals) / n, 4),
        "top_k_entity_density": round(sum(s.get("top_k_entity_density", 0.0) for s in scenario_evals) / n, 4),
        "entity_accuracy": round(sum(s.get("entity_accuracy_at_1", 0.0) for s in scenario_evals) / n, 4),
        "intent_accuracy_at_1": round(sum(s.get("intent_accuracy_at_1", 0.0) for s in scenario_evals) / n, 4),
        "top_k_intent_density": round(sum(s.get("top_k_intent_density", 0.0) for s in scenario_evals) / n, 4),
        "intent_accuracy": round(sum(s.get("intent_accuracy_at_1", 0.0) for s in scenario_evals) / n, 4),

        # Hard-negative metrics
        "top1_hard_negative_avoidance": top1_hn_avoidance,
        "candidate_hard_negative_rejection_rate": cand_hn_rejection_rate,
        "hard_negative_rejection_rate": top1_hn_avoidance,

        # Sample counts
        "evaluable_scenarios": len(scenario_evals),
        "recall_evaluable_scenarios": len(recall_evals_1),
        "hard_negative_scenarios": len(hn_scenarios),
        "total_grade0_candidates": tot_g0,
        "rejected_grade0_candidates": rej_g0,
    }
