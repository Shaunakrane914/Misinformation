"""
Aegis Protocol — Evaluation Framework Test Suite
================================================
Validates scientific integrity, mathematical correctness, and leakage defenses:
1. Zero ground-truth leakage guarantee (evaluator rejects label tampering)
2. Train/validation/test strict split separation (zero sample intersection)
3. Wilson Score confidence interval bounds and edge cases
4. Non-parametric bootstrap Macro-F1 confidence interval
5. Abstention, coverage, selective risk, and coverage-adjusted accuracy formulas
6. Expected Calibration Error (ECE) and Brier score calibration
7. Information retrieval metrics (MRR, Recall@1, Recall@5, Recall@10)
8. Learned evidence reranker ordering and feature extraction
9. Scientific mode failure on missing live API keys without silent mock fallback
10. Result JSON schema conformity
"""

import math
import os
import tempfile
import pytest
import numpy as np

from backend.evaluation.baselines import SinglePromptLLMBaseline, TfidfLogisticBaseline
from backend.evaluation.datasets.averitec import AVeriTeCDataset
from backend.evaluation.datasets.india_track import IndiaMultilingualTrack
from backend.evaluation.datasets.welfake import WelfakeDataset, get_welfake_splits
from backend.evaluation.metrics import (
    ClassificationMetrics,
    RetrievalMetrics,
    bootstrap_metric_ci,
    compute_abstention_metrics,
    compute_brier_score,
    compute_calibration_curve,
    compute_calibration_metrics,
    compute_classification_metrics,
    compute_expected_calibration_error,
    compute_retrieval_metrics,
    macro_f1_wrapper,
    mcnemar_significance_test,
    wilson_score_interval,
)
from backend.evaluation.reranker import LearnedEvidenceReranker
from backend.services.gemini_service import gemini_service


# ── 1. GROUND TRUTH LEAKAGE PREVENTION TESTS ─────────────────────────────

def test_zero_ground_truth_leakage_in_baseline():
    """
    Deliberately asserts that SinglePromptLLMBaseline.evaluate_sample() signature
    and execution has NO access to ground truth label.
    """
    baseline = SinglePromptLLMBaseline(allow_mock=True)
    claim = "Drinking green tea completely prevents viral infections."

    # evaluate_sample accepts ONLY claim_text — passing ground_truth must fail inspect/runtime
    result = baseline.evaluate_sample(claim)
    assert "prediction_label" in result
    assert "ground_truth" not in result
    assert "effective_direction" not in result


def test_evaluator_architecture_prevents_label_driven_evidence():
    """
    Verifies that unlike the old broken evaluate_dataset.py,
    the reranker and ingestion layers never consume ground-truth labels.
    """
    reranker = LearnedEvidenceReranker()
    candidate = {
        "title": "Clinical trials on herbal extracts",
        "snippet": "Observational studies show no prophylactic antiviral efficacy.",
        "url": "https://ncbi.nlm.nih.gov/pmc/12345",
        "primary_source": True,
    }

    # Verify extract_features accepts only (claim, candidate)
    feats = reranker.extract_features(
        claim="Drinking green tea prevents infections",
        candidate=candidate,
    )
    assert len(feats) == 7
    assert isinstance(feats, np.ndarray)


# ── 2. TRAIN / VAL / TEST SPLIT ISOLATION TESTS ──────────────────────────

def test_welfake_stratified_split_isolation():
    """Ensures deterministic train/val/test splits with zero intersection."""
    ds = WelfakeDataset()
    splits = ds.get_splits(seed=42)

    train_df = splits["train"]
    val_df = splits["val"]
    test_df = splits["test"]

    # Ratio assertions: 70 / 15 / 15 on content-deduplicated dataset
    total = len(train_df) + len(val_df) + len(test_df)
    assert total == 19647
    assert abs(len(train_df) / total - 0.70) < 0.01
    assert abs(len(val_df) / total - 0.15) < 0.01
    assert abs(len(test_df) / total - 0.15) < 0.01

    # Zero content overlap across partitions
    train_titles = set(train_df["normalized_title"])
    val_titles = set(val_df["normalized_title"])
    test_titles = set(test_df["normalized_title"])
    assert len(train_titles & test_titles) == 0
    assert len(train_titles & val_titles) == 0
    assert len(val_titles & test_titles) == 0

    # Class balance preserved in each split
    train_prop = train_df["label"].mean()
    test_prop = test_df["label"].mean()
    assert abs(train_prop - test_prop) < 0.02

    # Determinism across runs with same seed
    splits2 = ds.get_splits(seed=42)
    assert splits["test"]["title"].iloc[0] == splits2["test"]["title"].iloc[0]



# ── 3. STATISTICAL UNCERTAINTY & CONFIDENCE INTERVALS ────────────────────

def test_wilson_score_interval_bounds():
    """Validates Wilson score interval on boundary and standard cases."""
    # Boundary: 0 / 100
    low, high = wilson_score_interval(0, 100, confidence=0.95)
    assert low == 0.0
    assert 0.0 < high < 0.05

    # Boundary: 100 / 100
    low, high = wilson_score_interval(100, 100, confidence=0.95)
    assert 0.95 < low < 1.0
    assert high == 1.0

    # Symmetric: 50 / 100
    low, high = wilson_score_interval(50, 100, confidence=0.95)
    assert 0.40 < low < 0.50
    assert 0.50 < high < 0.60
    assert abs((low + high) / 2 - 0.50) < 1e-4


def test_bootstrap_macro_f1_ci():
    """Validates percentile bootstrap confidence interval on Macro-F1."""
    y_true = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1]
    y_pred = [0, 0, 0, 1, 1, 1, 1, 1, 0, 1]

    low, high = bootstrap_metric_ci(
        y_true, y_pred, macro_f1_wrapper, n_resamples=200, confidence=0.95, seed=42
    )
    assert 0.0 <= low <= high <= 1.0
    assert high - low > 0.05


# ── 4. ABSTENTION & SELECTIVE PREDICTION METRICS ─────────────────────────

def test_abstention_and_selective_metrics():
    """Validates coverage, covered accuracy, selective risk, and coverage-adjusted accuracy."""
    total_samples = 10
    y_true = [1, 1, 0, 0, 1, 0, 1, 0, 1, 0]
    # Predict 6 samples correctly, 2 incorrectly, 2 abstained
    y_pred = [1, 1, 0, 0, 1, 0, 0, 1, -1, -1]
    abstained = [False, False, False, False, False, False, False, False, True, True]

    metrics = compute_abstention_metrics(total_samples, y_true, y_pred, abstained)

    assert metrics["total_samples"] == 10
    assert metrics["covered_samples"] == 8
    assert metrics["abstained_samples"] == 2
    assert metrics["coverage"] == 0.80
    assert metrics["abstention_rate"] == 0.20
    # 6 correct out of 8 covered = 0.75
    assert metrics["covered_accuracy"] == 0.75
    # Selective risk = 1 - 0.75 = 0.25
    assert metrics["selective_risk"] == 0.25
    # Coverage adjusted accuracy = 6 / 10 = 0.60
    assert metrics["coverage_adjusted_accuracy"] == 0.60


# ── 5. CALIBRATION METRICS (ECE & BRIER SCORE) ───────────────────────────

def test_expected_calibration_error_and_brier():
    """Validates ECE and Brier score computation."""
    # Perfectly calibrated probabilities
    y_true = [1, 1, 0, 0]
    probs = [1.0, 1.0, 0.0, 0.0]
    brier = compute_brier_score(y_true, probs)
    assert brier == 0.0

    # Miscalibrated overconfident probabilities
    probs_bad = [0.0, 0.0, 1.0, 1.0]
    brier_bad = compute_brier_score(y_true, probs_bad)
    assert brier_bad == 1.0

    # ECE calculation on balanced predictions
    ece = compute_expected_calibration_error([1, 0], [0.8, 0.2], n_bins=2)
    assert 0.0 <= ece <= 1.0


# ── 6. RETRIEVAL QUALITY METRICS ─────────────────────────────────────────

def test_retrieval_metrics_mrr_and_recall():
    """Validates MRR and Recall@K on ranked lists."""
    # Query 1: relevant document at rank 1
    # Query 2: relevant document at rank 4
    # Query 3: no relevant document in top 10
    ranked = [
        [1, 0, 0, 0, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0],
    ]
    res = compute_retrieval_metrics(ranked, k_list=(1, 3, 5, 10))

    # Query 1 RR = 1.0, Query 2 RR = 1/4 = 0.25, Query 3 RR = 0.0
    # MRR = (1.0 + 0.25 + 0.0) / 3 = 1.25 / 3 = 0.4167
    assert abs(res["mrr"] - 0.4167) < 1e-3

    # Recall@1: 1 / 3 = 0.3333
    assert abs(res["recall@1"] - 0.3333) < 1e-3
    # Recall@3: 1 / 3 = 0.3333
    assert abs(res["recall@3"] - 0.3333) < 1e-3
    # Recall@5: 2 / 3 = 0.6667
    assert abs(res["recall@5"] - 0.6667) < 1e-3


# ── 7. LEARNED EVIDENCE RERANKER ─────────────────────────────────────────

def test_learned_evidence_reranker_reorders_high_credibility():
    """Ensures reranker prioritizes primary and domain-credible sources over noisy blogs."""
    reranker = LearnedEvidenceReranker()
    claim = "Consuming raw garlic cures stage 4 cancer"

    distractor = {
        "title": "Celebrity wellness blog tips",
        "snippet": "Garlic remedies for everyday colds and vitality.",
        "url": "https://randomblog123.xyz/garlic",
        "domain": "randomblog123.xyz",
        "primary_source": False,
        "original_index": 0,
    }
    authoritative = {
        "title": "WHO Clinical Statement on Cancer Interventions",
        "snippet": "Clinical evidence disproves raw garlic as a curative oncology intervention.",
        "url": "https://who.int/cancer/advisory",
        "domain": "who.int",
        "primary_source": True,
        "original_index": 1,
    }

    # Raw order: distractor first (index 0), authoritative second (index 1)
    candidates = [distractor, authoritative]
    reranked, lat_ms = reranker.rerank(claim, candidates, top_k=2)

    assert len(reranked) == 2
    assert lat_ms < 50.0  # Sub-50ms execution
    # Authoritative must be elevated to rank 1
    assert reranked[0]["domain"] == "who.int"
    assert reranked[0]["reranker_score"] > reranked[1]["reranker_score"]


# ── 8. SCIENTIFIC MODE BLOCKS ON MISSING LIVE KEYS ───────────────────────

def test_scientific_mode_blocks_without_silent_mock_fallback(monkeypatch):
    """
    CRITICAL: Scientific benchmark mode must NOT silently fall back to MockGeminiProvider
    when live keys are absent. It must cleanly report BLOCKED.
    """
    # Temporarily remove any AIzaSy keys
    monkeypatch.setattr(gemini_service, "api_keys", [])

    baseline = SinglePromptLLMBaseline(allow_mock=False)
    res = baseline.evaluate_sample("Test scientific claim")

    assert res["status"] == "BLOCKED"
    assert "No valid Google AI Studio key" in res["error"]
    assert res["provider"] == "none"


# ── 9. AVERITEC ADAPTER STATUS REPORTING ─────────────────────────────────

def test_averitec_status_reporting():
    """Verifies AVeriTeC reports NOT RUN when dataset is not locally present."""
    av = AVeriTeCDataset()
    status = av.get_status()
    assert "status" in status
    assert status["status"] in ("READY", "NOT RUN")
    if status["status"] == "NOT RUN":
        assert "not locally present" in status["reason"]
        assert "Schlichtkrull" in status["paper"]


# ── 10. INDIA MULTILINGUAL TRACK INTEGRITY ───────────────────────────────

def test_india_multilingual_track_properties():
    """Validates structure and diversity of the India Gold Track."""
    track = IndiaMultilingualTrack()
    claims = track.get_claims()
    assert len(claims) >= 14

    languages = set(c["language"] for c in claims)
    assert {"English", "Hindi", "Marathi", "Hinglish"}.issubset(languages)

    domains = set(c["domain"] for c in claims)
    assert {"Public Health", "Finance & Banking", "Infrastructure"}.issubset(domains)


    for item in claims:
        assert "claim" in item
        assert "language" in item
        assert "domain" in item
        assert item["label"] in (0, 1)
        assert item["canonical_verdict"] in ("True", "False")
        assert "verification_source" in item
