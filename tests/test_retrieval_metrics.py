"""
Aegis Protocol — Rigorous Information Retrieval Metrics Unit Tests
==================================================================
Tests standard IR evaluation metrics with exact hand-calculated assertions:
- P@1, P@3, P@4 with fixed denominators
- Recall@1, Recall@3, Recall@4 over evaluable queries (R_query > 0)
- R_query == 0 returns None and is excluded from macro-averaging
- MRR and nDCG with documented gain functions
- Shuffled ranking lists changing metrics as expected
- Empty candidate sets returning NOT_EVALUABLE
"""

import math
import pytest
from backend.services.research.retrieval_metrics import (
    compute_precision_at_k,
    compute_recall_at_k,
    compute_reciprocal_rank,
    compute_dcg_at_k,
    compute_ndcg_at_k,
    evaluate_ranking_run,
    aggregate_metrics,
)


def test_top_k_precision_hand_calculated():
    # 4 candidates with grades [3, 2, 1, 0]
    grades = [3, 2, 1, 0]
    # P@1 (threshold 2): 1 item, grade 3 >= 2 -> 1 / 1 = 1.0
    assert compute_precision_at_k(grades, 1, threshold=2) == 1.0
    # Strict P@1 (threshold 3): 1 item, grade 3 == 3 -> 1 / 1 = 1.0
    assert compute_precision_at_k(grades, 1, threshold=3) == 1.0

    # P@3 (threshold 2): 3 items [3, 2, 1], 2 are >= 2 -> 2 / 3 = 0.6667
    assert compute_precision_at_k(grades, 3, threshold=2) == 0.6667
    # Strict P@3 (threshold 3): 3 items [3, 2, 1], 1 is == 3 -> 1 / 3 = 0.3333
    assert compute_precision_at_k(grades, 3, threshold=3) == 0.3333

    # P@4 (threshold 2): 4 items [3, 2, 1, 0], 2 are >= 2 -> 2 / 4 = 0.50
    assert compute_precision_at_k(grades, 4, threshold=2) == 0.50

    # Fixed-denominator P@5 on a 4-item list:
    # 4 items [3, 2, 1, 0], 2 are >= 2 -> fixed denominator 5 -> 2 / 5 = 0.40
    assert compute_precision_at_k(grades, 5, threshold=2) == 0.40


def test_recall_at_k_hand_calculated():
    # Pool has total_relevant = 2 (e.g. grades [3, 2, 1, 0])
    grades = [3, 2, 1, 0]
    # At k=1: 1 relevant retrieved out of 2 total -> 1 / 2 = 0.50
    assert compute_recall_at_k(grades, total_relevant=2, k=1, threshold=2) == 0.50
    # At k=2: 2 relevant retrieved out of 2 total -> 2 / 2 = 1.0
    assert compute_recall_at_k(grades, total_relevant=2, k=2, threshold=2) == 1.0
    # At k=3: 2 relevant retrieved out of 2 total -> 2 / 2 = 1.0
    assert compute_recall_at_k(grades, total_relevant=2, k=3, threshold=2) == 1.0
    # At k=4: 2 relevant retrieved out of 2 total -> 2 / 2 = 1.0
    assert compute_recall_at_k(grades, total_relevant=2, k=4, threshold=2) == 1.0


def test_recall_undefined_when_zero_relevant_in_pool():
    # When a query has NO relevant items in the pool (e.g. hard negative scenario)
    # Recall is mathematically undefined (0/0) and MUST return None to avoid false 100% inflation
    grades = [1, 0, 0, 0]
    rec = compute_recall_at_k(grades, total_relevant=0, k=4, threshold=2)
    assert rec is None


def test_reciprocal_rank_hand_calculated():
    # First relevant at rank 1 -> 1.0
    assert compute_reciprocal_rank([3, 1, 0], threshold=2) == 1.0
    # First relevant at rank 2 -> 0.5
    assert compute_reciprocal_rank([1, 2, 0], threshold=2) == 0.5
    # First relevant at rank 3 -> 0.3333
    assert compute_reciprocal_rank([0, 1, 3], threshold=2) == 0.3333
    # No relevant item found -> 0.0
    assert compute_reciprocal_rank([1, 0, 0], threshold=2) == 0.0


def test_ndcg_hand_calculated():
    # Perfect ranking: [3, 2, 1, 0] vs ideal [3, 2, 1, 0] -> 1.0
    assert compute_ndcg_at_k([3, 2, 1, 0], [3, 2, 1, 0], 4) == 1.0

    # Inverted ranking: [0, 1, 2, 3]
    # DCG = (2^0-1)/1 + (2^1-1)/log2(3) + (2^2-1)/log2(4) + (2^3-1)/log2(5)
    #     = 0 + 1/1.585 + 3/2 + 7/2.322 = 0 + 0.6309 + 1.5 + 3.0146 = 5.1455
    # IDCG = (2^3-1)/1 + (2^2-1)/1.585 + (2^1-1)/2 + (2^0-1)/2.322
    #      = 7 + 3/1.585 + 1/2 + 0 = 7 + 1.8927 + 0.5 = 9.3927
    # nDCG = 5.1455 / 9.3927 = 0.5478
    ndcg_inv = compute_ndcg_at_k([0, 1, 2, 3], [3, 2, 1, 0], 4)
    assert abs(ndcg_inv - 0.5478) < 0.01


def test_shuffled_rankings_change_metrics():
    """
    Invariance test: Permuting the candidate ranking order MUST change P@1, MRR, and nDCG!
    """
    ideal_order = [3, 2, 1, 0]
    degraded_order = [0, 1, 2, 3]

    p1_ideal = compute_precision_at_k(ideal_order, 1, threshold=2)
    p1_degraded = compute_precision_at_k(degraded_order, 1, threshold=2)
    assert p1_ideal == 1.0
    assert p1_degraded == 0.0

    mrr_ideal = compute_reciprocal_rank(ideal_order, threshold=2)
    mrr_degraded = compute_reciprocal_rank(degraded_order, threshold=2)
    assert mrr_ideal == 1.0
    assert mrr_degraded == 0.3333

    ndcg_ideal = compute_ndcg_at_k(ideal_order, [3, 2, 1, 0], 4)
    ndcg_degraded = compute_ndcg_at_k(degraded_order, [3, 2, 1, 0], 4)
    assert ndcg_ideal > ndcg_degraded


def test_empty_candidate_set_not_evaluable():
    eval_res = evaluate_ranking_run(
        ranked_candidates=[],
        all_candidates=[],
        labels_by_cand_id={},
        target_canonical="Microsoft",
        target_intent="brand_threat",
    )
    assert eval_res.get("status") == "NOT_EVALUABLE"


def test_aggregate_metrics_excludes_undefined_recall():
    # Scenario 1: has 2 relevant items, retrieves 1 at k=1 -> Recall = 0.5
    s1 = {
        "p_at_1": 1.0, "p_at_3": 0.67, "p_at_4": 0.5, "p_at_5": 0.4,
        "strict_p_at_1": 1.0, "strict_p_at_3": 0.33, "strict_p_at_4": 0.25,
        "recall_at_1": 0.5, "recall_at_3": 1.0, "recall_at_4": 1.0, "recall_at_5": 1.0,
        "mrr": 1.0, "strict_mrr": 1.0, "ndcg_at_3": 1.0, "ndcg_at_4": 1.0, "ndcg_at_5": 1.0,
        "entity_accuracy_at_1": 1.0, "intent_accuracy_at_1": 1.0,
        "has_hard_negative": False, "hard_neg_leak_at_1": 0
    }
    # Scenario 2: purely negative scenario (0 relevant items) -> Recall is None
    s2 = {
        "p_at_1": 0.0, "p_at_3": 0.0, "p_at_4": 0.0, "p_at_5": 0.0,
        "strict_p_at_1": 0.0, "strict_p_at_3": 0.0, "strict_p_at_4": 0.0,
        "recall_at_1": None, "recall_at_3": None, "recall_at_4": None, "recall_at_5": None,
        "mrr": 0.0, "strict_mrr": 0.0, "ndcg_at_3": 1.0, "ndcg_at_4": 1.0, "ndcg_at_5": 1.0,
        "entity_accuracy_at_1": 1.0, "intent_accuracy_at_1": 0.0,
        "has_hard_negative": True, "hard_neg_leak_at_1": 0
    }

    agg = aggregate_metrics([s1, s2])
    assert agg["status"] == "EVALUATED"
    assert agg["evaluable_scenarios"] == 2
    assert agg["recall_evaluable_scenarios"] == 1
    # Recall at k=1 should be strictly 0.5 (from s1 only), NOT diluted or inflated
    assert agg["recall_at_1"] == 0.5
    assert agg["recall_at_4"] == 1.0
    assert agg["hard_negative_rejection_rate"] == 1.0
