"""
Aegis Protocol — Retrieval Quality Metrics Engine
=================================================
Calculates standard information retrieval and quality metrics over graded candidate rankings:
- Precision@1, Precision@3, Precision@5
- Recall@5, Recall@10
- MRR (Mean Reciprocal Rank)
- nDCG@5, nDCG@10 (Normalized Discounted Cumulative Gain)
- Entity Accuracy
- Intent Accuracy
- False-Positive Rate (Grade 0 leaks)
- Ambiguous Rate (Grade 1 distractors)
- Hard-Negative Rejection Rate

Relevance Definition:
- Relevant: gold_grade >= 2 (3 = Direct True Positive, 2 = Secondary Relevant)
- Non-relevant: gold_grade <= 1 (1 = Borderline Distractor, 0 = Hard Negative / Homograph)
"""

import math
from typing import Any, Dict, List, Optional, Tuple


def compute_precision_at_k(ranked_grades: List[int], k: int, threshold: int = 2) -> float:
    """Precision@k: proportion of top-k items with gold_grade >= threshold."""
    if k <= 0:
        return 0.0
    top_k = ranked_grades[:k]
    if not top_k:
        return 0.0
    relevant_count = sum(1 for g in top_k if g >= threshold)
    return round(relevant_count / float(k), 4)


def compute_recall_at_k(ranked_grades: List[int], total_relevant: int, k: int, threshold: int = 2) -> float:
    """Recall@k: proportion of total relevant items retrieved in top-k."""
    if total_relevant <= 0:
        # If there are no relevant items in the corpus, recall is 1.0 if none retrieved, 0.0 otherwise
        return 1.0 if sum(1 for g in ranked_grades[:k] if g >= threshold) == 0 else 0.0
    top_k = ranked_grades[:k]
    relevant_retrieved = sum(1 for g in top_k if g >= threshold)
    return round(min(1.0, relevant_retrieved / float(total_relevant)), 4)


def compute_reciprocal_rank(ranked_grades: List[int], threshold: int = 2) -> float:
    """Reciprocal Rank: 1 / rank of the first relevant item (1-indexed)."""
    for rank_idx, g in enumerate(ranked_grades, 1):
        if g >= threshold:
            return round(1.0 / rank_idx, 4)
    return 0.0


def compute_dcg_at_k(ranked_grades: List[int], k: int) -> float:
    """Discounted Cumulative Gain at k."""
    dcg = 0.0
    for idx, grade in enumerate(ranked_grades[:k]):
        # Standard gain formula: (2^rel - 1) / log2(rank + 1)
        gain = (2.0 ** grade) - 1.0
        discount = math.log2(idx + 2)  # idx 0 -> rank 1 -> log2(2) = 1.0
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
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Evaluate a single scenario's ranked candidate output against gold labels.
    """
    ranked_grades = []
    all_grades = [labels_by_cand_id[c["candidate_id"]]["gold_grade"] for c in all_candidates if c["candidate_id"] in labels_by_cand_id]
    total_relevant = sum(1 for g in all_grades if g >= 2)

    top_items = ranked_candidates[:top_k]
    entity_matches = 0
    intent_matches = 0
    false_positives = 0
    ambiguous_count = 0
    hard_neg_leaks = 0

    for idx, item in enumerate(top_items):
        cid = item.get("candidate_id")
        lb = labels_by_cand_id.get(cid, {})
        grade = lb.get("gold_grade", 0)
        ranked_grades.append(grade)

        # Entity correctness
        cand_entity = lb.get("gold_entity", "").lower()
        if target_canonical.lower() in cand_entity or cand_entity in target_canonical.lower():
            entity_matches += 1

        # Intent correctness
        cand_intent = lb.get("gold_intent", "").lower()
        if target_intent.lower() in cand_intent or cand_intent in target_intent.lower() or grade == 3:
            intent_matches += 1

        # False positive: Grade 0 item in top rank
        if grade == 0:
            false_positives += 1
            if idx == 0:
                hard_neg_leaks += 1
        elif grade == 1:
            ambiguous_count += 1

    evaluated_k = len(top_items) if top_items else 1

    return {
        "p_at_1": compute_precision_at_k(ranked_grades, 1),
        "p_at_3": compute_precision_at_k(ranked_grades, 3),
        "p_at_5": compute_precision_at_k(ranked_grades, 5),
        "recall_at_5": compute_recall_at_k(ranked_grades, total_relevant, 5),
        "recall_at_10": compute_recall_at_k(ranked_grades, total_relevant, 10),
        "mrr": compute_reciprocal_rank(ranked_grades),
        "ndcg_at_5": compute_ndcg_at_k(ranked_grades, all_grades, 5),
        "ndcg_at_10": compute_ndcg_at_k(ranked_grades, all_grades, 10),
        "entity_accuracy": round(entity_matches / float(evaluated_k), 4),
        "intent_accuracy": round(intent_matches / float(evaluated_k), 4),
        "false_positive_rate": round(false_positives / float(evaluated_k), 4),
        "ambiguous_rate": round(ambiguous_count / float(evaluated_k), 4),
        "hard_neg_leak_at_1": hard_neg_leaks,
        "total_relevant_in_pool": total_relevant,
        "ranked_grades": ranked_grades,
    }


def aggregate_metrics(scenario_evals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate per-scenario metric results into mean summary metrics."""
    if not scenario_evals:
        return {
            "p_at_1": 0.0,
            "p_at_3": 0.0,
            "p_at_5": 0.0,
            "recall_at_5": 0.0,
            "recall_at_10": 0.0,
            "mrr": 0.0,
            "ndcg_at_5": 0.0,
            "ndcg_at_10": 0.0,
            "entity_accuracy": 0.0,
            "intent_accuracy": 0.0,
            "false_positive_rate": 0.0,
            "ambiguous_rate": 0.0,
            "hard_negative_rejection_rate": 0.0,
            "count": 0,
        }

    n = float(len(scenario_evals))
    hard_neg_leaks = sum(s.get("hard_neg_leak_at_1", 0) for s in scenario_evals)
    hard_neg_rejection_rate = round(1.0 - (hard_neg_leaks / n), 4)

    return {
        "p_at_1": round(sum(s["p_at_1"] for s in scenario_evals) / n, 4),
        "p_at_3": round(sum(s["p_at_3"] for s in scenario_evals) / n, 4),
        "p_at_5": round(sum(s["p_at_5"] for s in scenario_evals) / n, 4),
        "recall_at_5": round(sum(s["recall_at_5"] for s in scenario_evals) / n, 4),
        "recall_at_10": round(sum(s["recall_at_10"] for s in scenario_evals) / n, 4),
        "mrr": round(sum(s["mrr"] for s in scenario_evals) / n, 4),
        "ndcg_at_5": round(sum(s["ndcg_at_5"] for s in scenario_evals) / n, 4),
        "ndcg_at_10": round(sum(s["ndcg_at_10"] for s in scenario_evals) / n, 4),
        "entity_accuracy": round(sum(s["entity_accuracy"] for s in scenario_evals) / n, 4),
        "intent_accuracy": round(sum(s["intent_accuracy"] for s in scenario_evals) / n, 4),
        "false_positive_rate": round(sum(s["false_positive_rate"] for s in scenario_evals) / n, 4),
        "ambiguous_rate": round(sum(s["ambiguous_rate"] for s in scenario_evals) / n, 4),
        "hard_negative_rejection_rate": hard_neg_rejection_rate,
        "count": len(scenario_evals),
    }
