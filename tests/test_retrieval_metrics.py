"""
Aegis Protocol — Retrieval Metrics Unit Tests
=============================================
Tests standard IR evaluation metrics: Precision@k, Recall@k, MRR, nDCG@k,
entity accuracy, intent accuracy, and hard-negative rejection.
"""

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


def test_top5_precision():
    # 5 items: grades [3, 2, 1, 0, 3] -> 3 relevant (>=2) out of 5 -> 0.60
    grades = [3, 2, 1, 0, 3]
    p5 = compute_precision_at_k(grades, 5)
    assert p5 == 0.60

    # 1 item: grade 3 -> 1.0
    p1 = compute_precision_at_k(grades, 1)
    assert p1 == 1.0

    # 3 items: [3, 2, 1] -> 2 / 3 -> 0.6667
    p3 = compute_precision_at_k(grades, 3)
    assert p3 == 0.6667


def test_mrr():
    # First relevant at rank 1 -> MRR = 1.0
    assert compute_reciprocal_rank([3, 0, 0]) == 1.0

    # First relevant at rank 2 -> MRR = 0.5
    assert compute_reciprocal_rank([1, 2, 0]) == 0.5

    # First relevant at rank 4 -> MRR = 0.25
    assert compute_reciprocal_rank([0, 1, 0, 3]) == 0.25

    # No relevant item -> MRR = 0.0
    assert compute_reciprocal_rank([0, 1, 0, 1]) == 0.0


def test_ndcg():
    # Perfect ranking: [3, 2, 1, 0] vs ideal [3, 2, 1, 0] -> nDCG = 1.0
    assert compute_ndcg_at_k([3, 2, 1, 0], [3, 2, 1, 0], 4) == 1.0

    # Inverted ranking: [0, 1, 2, 3] vs ideal [3, 2, 1, 0] -> nDCG < 1.0
    ndcg_inverted = compute_ndcg_at_k([0, 1, 2, 3], [3, 2, 1, 0], 4)
    assert ndcg_inverted < 0.60

    # Partial drop
    ndcg_partial = compute_ndcg_at_k([2, 3, 1, 0], [3, 2, 1, 0], 4)
    assert 0.80 < ndcg_partial < 1.0


def test_entity_accuracy():
    ranked = [
        {"candidate_id": "c1"},
        {"candidate_id": "c2"},
    ]
    all_cands = ranked
    labels = {
        "c1": {"gold_grade": 3, "gold_entity": "Microsoft", "gold_intent": "threat"},
        "c2": {"gold_grade": 0, "gold_entity": "Apple", "gold_intent": "other"},
    }
    eval_res = evaluate_ranking_run(ranked, all_cands, labels, "Microsoft", "threat", top_k=2)
    assert eval_res["entity_accuracy"] == 0.50
    assert eval_res["intent_accuracy"] == 0.50


def test_intent_accuracy():
    ranked = [
        {"candidate_id": "c1"},
        {"candidate_id": "c2"},
    ]
    all_cands = ranked
    labels = {
        "c1": {"gold_grade": 3, "gold_entity": "Microsoft", "gold_intent": "brand_threat"},
        "c2": {"gold_grade": 2, "gold_entity": "Microsoft", "gold_intent": "stock_market"},
    }
    eval_res = evaluate_ranking_run(ranked, all_cands, labels, "Microsoft", "brand_threat", top_k=2)
    assert eval_res["entity_accuracy"] == 1.0
    assert eval_res["intent_accuracy"] == 0.50


def test_hard_negative_rejection():
    # If grade 0 leaks to rank 1, hard_neg_leak_at_1 is triggered
    ranked_leaking = [{"candidate_id": "c_leak"}]
    labels_leaking = {"c_leak": {"gold_grade": 0, "gold_entity": "Other", "gold_intent": "other"}}
    eval_leak = evaluate_ranking_run(ranked_leaking, ranked_leaking, labels_leaking, "Microsoft", "brand", top_k=1)
    assert eval_leak["hard_neg_leak_at_1"] == 1
    assert eval_leak["false_positive_rate"] == 1.0

    # Aggregate metric calculates rejection rate
    agg = aggregate_metrics([eval_leak])
    assert agg["hard_negative_rejection_rate"] == 0.0


def test_zero_denominator_safe():
    # Recall with 0 relevant candidates in corpus
    rec = compute_recall_at_k([0, 1], total_relevant=0, k=2)
    assert rec == 1.0

    # Empty evals aggregate
    empty_agg = aggregate_metrics([])
    assert empty_agg["p_at_1"] == 0.0
    assert empty_agg["count"] == 0
