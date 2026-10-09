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
   P@k = (Count of retrieved candidates in top-k with grade >= threshold) / k
   Note: For a candidate pool of size N, standard fixed-denominator P@k uses the fixed
   denominator k (e.g. k=1, 3, 4).

2. Recall@k:
   Recall@k = (Count of retrieved candidates in top-k with grade >= threshold) / R_query
   where R_query is the total number of relevant candidates available in the pool for that query.
   In standard Cranfield/TREC IR methodology, queries with R_query == 0 have undefined recall
   and are excluded from the macro-average recall calculation (not counted as 100%).

3. Mean Reciprocal Rank (MRR):
   RR = 1 / rank* of the first candidate with grade >= threshold (1-indexed).
   RR = 0.0 if no relevant candidate is retrieved in the ranked list.

4. Normalized Discounted Cumulative Gain (nDCG@k):
   DCG@k = sum_{i=1}^{min(|G|, k)} (2^{grade_i} - 1) / log2(i + 1)
   IDCG@k = DCG@k of the ideal ranking (sorted descending by gold grade)
   nDCG@k = DCG@k / IDCG@k (if IDCG@k == 0, nDCG is 1.0 if actual DCG == 0 else 0.0)

5. Hard-Negative Rejection Rate:
   Evaluated over all scenarios containing at least one Grade 0 candidate.
   Rejection succeeds if rank-1 candidate has grade != 0.
   Rejection Rate = (Count of scenarios where top-1 is NOT grade 0) / (Total scenarios with grade 0 candidates)

6. Entity Accuracy & Intent Accuracy:
   Accuracy at Rank 1: Fraction of scenarios where Rank-1 candidate matches canonical entity / intent.
"""

import math
from typing import Any, Dict, List, Optional, Tuple


def compute_precision_at_k(ranked_grades: List[int], k: int, threshold: int = 2) -> float:
    """
    Standard Precision@k with fixed denominator k.
    P@k = (Count of items in top-k with grade >= threshold) / k
    """
    if k <= 0:
        return 0.0
    top_k_grades = ranked_grades[:k]
    relevant_count = sum(1 for g in top_k_grades if g >= threshold)
    return round(relevant_count / float(k), 4)


def compute_recall_at_k(ranked_grades: List[int], total_relevant: int, k: int, threshold: int = 2) -> Optional[float]:
    """
    Standard Recall@k.
    Returns None if total_relevant == 0 (query has no relevant documents in corpus;
    recall is undefined and should be excluded from macro-averaging).
    """
    if total_relevant <= 0:
        return None
    top_k_grades = ranked_grades[:k]
    relevant_retrieved = sum(1 for g in top_k_grades if g >= threshold)
    return round(min(1.0, relevant_retrieved / float(total_relevant)), 4)


def compute_reciprocal_rank(ranked_grades: List[int], threshold: int = 2) -> float:
    """
    Reciprocal Rank of the first relevant candidate.
    RR = 1.0 / rank (1-indexed). Returns 0.0 if none found.
    """
    for rank_idx, g in enumerate(ranked_grades, 1):
        if g >= threshold:
            return round(1.0 / rank_idx, 4)
    return 0.0


def compute_dcg_at_k(ranked_grades: List[int], k: int) -> float:
    """
    Discounted Cumulative Gain at k using exponential gain (2^rel - 1) / log2(rank + 1).
    """
    dcg = 0.0
    for idx, grade in enumerate(ranked_grades[:k]):
        gain = (2.0 ** grade) - 1.0
        discount = math.log2(idx + 2)  # rank 1 -> log2(2) = 1.0
        dcg += gain / discount
    return dcg


def compute_ndcg_at_k(ranked_grades: List[int], all_candidate_grades: List[int], k: int) -> float:
    """
    Normalized Discounted Cumulative Gain at k.
    """
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
    Computes cutoffs at k = 1, 3, 4 (natural pool cutoffs) and k = 5 (pool-exceeding).
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

    for c in ranked_candidates:
        cid = c.get("candidate_id")
        lb = labels_by_cand_id.get(cid, {})
        ranked_grades.append(lb.get("gold_grade", 0))

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

    # Hard negative leak at rank 1
    hard_neg_leak_at_1 = 1 if (has_hard_negative and top1_grade == 0) else 0

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

        # Recall metrics (defined only if relevant items exist in pool)
        "recall_at_1": compute_recall_at_k(ranked_grades, total_broad_relevant, 1, threshold=2),
        "recall_at_3": compute_recall_at_k(ranked_grades, total_broad_relevant, 3, threshold=2),
        "recall_at_4": compute_recall_at_k(ranked_grades, total_broad_relevant, 4, threshold=2),
        "recall_at_5": compute_recall_at_k(ranked_grades, total_broad_relevant, 5, threshold=2),

        # Ordering quality
        "mrr": compute_reciprocal_rank(ranked_grades, threshold=2),
        "strict_mrr": compute_reciprocal_rank(ranked_grades, threshold=3),
        "ndcg_at_3": compute_ndcg_at_k(ranked_grades, all_grades, 3),
        "ndcg_at_4": compute_ndcg_at_k(ranked_grades, all_grades, 4),
        "ndcg_at_5": compute_ndcg_at_k(ranked_grades, all_grades, 5),

        # Precision & error rates over pool
        "entity_accuracy_at_1": entity_acc_at_1,
        "intent_accuracy_at_1": intent_acc_at_1,
        "has_hard_negative": has_hard_negative,
        "hard_neg_leak_at_1": hard_neg_leak_at_1,
        "total_broad_relevant": total_broad_relevant,
        "total_strict_relevant": total_strict_relevant,
        "ranked_grades": ranked_grades,
        "top1_grade": top1_grade,
    }


def aggregate_metrics(scenario_evals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate per-scenario metric results into mean macro metrics.
    Only averages recall over scenarios where relevant documents exist (R_query > 0).
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
            "entity_accuracy": 0.0,
            "intent_accuracy": 0.0,
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

    # Hard negative rejection is evaluated strictly over scenarios possessing grade 0 candidates
    hn_scenarios = [s for s in scenario_evals if s.get("has_hard_negative")]
    if hn_scenarios:
        hn_leaks = sum(s.get("hard_neg_leak_at_1", 0) for s in hn_scenarios)
        hn_rejection_rate = round(1.0 - (hn_leaks / float(len(hn_scenarios))), 4)
    else:
        hn_rejection_rate = 1.0

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

        # Cranfield-valid recall (averaged over evaluable queries where R_query > 0)
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

        # Disambiguation accuracy
        "entity_accuracy": round(sum(s["entity_accuracy_at_1"] for s in scenario_evals) / n, 4),
        "intent_accuracy": round(sum(s["intent_accuracy_at_1"] for s in scenario_evals) / n, 4),
        "hard_negative_rejection_rate": hn_rejection_rate,

        # Sample counts
        "evaluable_scenarios": len(scenario_evals),
        "recall_evaluable_scenarios": len(recall_evals_1),
        "hard_negative_scenarios": len(hn_scenarios),
    }
