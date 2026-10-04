"""
Aegis Protocol — Evaluation Metrics Library
===========================================
Defensive, mathematically verified metric computation:
- Multi-class / binary classification (Accuracy, Precision, Recall, Macro-F1)
- Statistical uncertainty intervals (Wilson score interval, Non-parametric bootstrap)
- Abstention & selective prediction metrics (Coverage, Covered Accuracy, Selective Risk)
- Probability calibration (Expected Calibration Error, Brier Score, Reliability bins)
- Information retrieval metrics (Recall@K, MRR, nDCG@K)
- Paired statistical comparison (McNemar's test with continuity correction)
"""

import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy import stats
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    brier_score_loss,
)


def wilson_score_interval(
    successes: int,
    total: int,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Computes Wilson score interval for a binomial proportion.
    More accurate than normal approximation, especially near 0 or 1 and with small N.
    """
    if total == 0:
        return 0.0, 0.0
    p_hat = successes / total
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    z2 = z ** 2
    n = total

    denominator = 1 + z2 / n
    center = (p_hat + z2 / (2 * n)) / denominator
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z2 / (4 * n)) / n) / denominator

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    if successes == 0:
        lower = 0.0
    if successes == total:
        upper = 1.0
    return float(lower), float(upper)



def bootstrap_metric_ci(
    y_true: List[int],
    y_pred: List[int],
    metric_fn: Any,
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42
) -> Tuple[float, float]:
    """
    Computes non-parametric percentile bootstrap confidence interval for arbitrary metric.
    """
    if len(y_true) < 2 or len(y_true) != len(y_pred):
        return 0.0, 0.0

    rng = np.random.default_rng(seed)
    n = len(y_true)
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)

    boot_scores = []
    for _ in range(n_resamples):
        indices = rng.integers(0, n, size=n)
        try:
            score = metric_fn(y_true_arr[indices], y_pred_arr[indices])
            if not np.isnan(score):
                boot_scores.append(score)
        except Exception:
            continue

    if not boot_scores:
        return 0.0, 0.0

    alpha = 1.0 - confidence
    lower = float(np.percentile(boot_scores, 100 * (alpha / 2)))
    upper = float(np.percentile(boot_scores, 100 * (1 - alpha / 2)))
    return lower, upper


def macro_f1_wrapper(y_t: np.ndarray, y_p: np.ndarray) -> float:
    _, _, f1, _ = precision_recall_fscore_support(
        y_t, y_p, average="macro", zero_division=0
    )
    return float(f1)


def compute_classification_metrics(
    y_true: List[int],
    y_pred: List[int],
    confidences: Optional[List[float]] = None,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Computes comprehensive classification metrics with 95% confidence bounds.
    Labels: 0 = Real / True, 1 = Fake / False.
    """
    if len(y_true) == 0:
        return {
            "sample_count": 0,
            "accuracy": 0.0,
            "macro_f1": 0.0,
            "precision": 0.0,
            "recall": 0.0
        }

    acc = float(accuracy_score(y_true, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    p_per, r_per, f1_per, support = precision_recall_fscore_support(
        y_true, y_pred, average=None, labels=[0, 1], zero_division=0
    )

    # 95% Wilson Score Interval for Accuracy
    n_correct = int(sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp))
    acc_ci_low, acc_ci_high = wilson_score_interval(n_correct, len(y_true), confidence=0.95)

    # 95% Bootstrap CI for Macro-F1
    f1_ci_low, f1_ci_high = bootstrap_metric_ci(
        y_true, y_pred, macro_f1_wrapper, n_resamples=1000, confidence=0.95, seed=seed
    )

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    result: Dict[str, Any] = {
        "sample_count": len(y_true),
        "accuracy": round(acc, 4),
        "accuracy_95ci": [round(acc_ci_low, 4), round(acc_ci_high, 4)],
        "macro_f1": round(float(f1_macro), 4),
        "macro_f1_95ci": [round(f1_ci_low, 4), round(f1_ci_high, 4)],
        "macro_precision": round(float(p_macro), 4),
        "macro_recall": round(float(r_macro), 4),
        "per_class": {
            "class_0_real": {
                "precision": round(float(p_per[0]), 4),
                "recall": round(float(r_per[0]), 4),
                "f1": round(float(f1_per[0]), 4),
                "support": int(support[0]),
            },
            "class_1_fake": {
                "precision": round(float(p_per[1]), 4),
                "recall": round(float(r_per[1]), 4),
                "f1": round(float(f1_per[1]), 4),
                "support": int(support[1]),
            },
        },
        "confusion_matrix": {
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "tp": tp,
            "interpretation": {
                "true_negatives": "Real verified news correctly classified as Real",
                "false_positives": "Real news incorrectly flagged as Fake (Type I error)",
                "false_negatives": "Fake news missed and passed as Real (Type II error)",
                "true_positives": "Fake news correctly identified as Fake",
            }
        },
        "bootstrap_parameters": {
            "resamples": 1000,
            "confidence_level": 0.95,
            "seed": seed,
            "interval_type": "percentile"
        }
    }

    if confidences and len(confidences) == len(y_true):
        result["mean_confidence"] = round(float(np.mean(confidences)), 4)
        result["median_confidence"] = round(float(np.median(confidences)), 4)

    return result


def compute_abstention_metrics(
    total_samples: int,
    y_true: List[int],
    y_pred: List[int],
    abstained_mask: List[bool]
) -> Dict[str, Any]:
    """
    Computes abstention-aware and selective classification metrics:
    - Coverage = |Covered| / |Total|
    - Covered Accuracy = Correct in Covered / |Covered|
    - Selective Risk = 1.0 - Covered Accuracy
    - Coverage-Adjusted Accuracy = Correct in Covered / |Total|
    """
    if total_samples <= 0:
        return {
            "total_samples": 0,
            "coverage": 0.0,
            "abstention_rate": 0.0,
            "covered_accuracy": 0.0,
            "selective_risk": 0.0,
            "coverage_adjusted_accuracy": 0.0
        }

    n_abstained = int(sum(1 for a in abstained_mask if a))
    n_covered = total_samples - n_abstained
    coverage = n_covered / total_samples
    abstention_rate = n_abstained / total_samples

    # Count correct among covered samples only
    covered_correct = 0
    for yt, yp, is_abs in zip(y_true, y_pred, abstained_mask):
        if not is_abs and yt == yp:
            covered_correct += 1

    covered_acc = (covered_correct / n_covered) if n_covered > 0 else 0.0
    selective_risk = (1.0 - covered_acc) if n_covered > 0 else 1.0
    cov_adjusted_acc = covered_correct / total_samples

    cov_low, cov_high = wilson_score_interval(n_covered, total_samples, confidence=0.95)
    cov_acc_low, cov_acc_high = wilson_score_interval(covered_correct, n_covered, confidence=0.95) if n_covered > 0 else (0.0, 0.0)

    return {
        "total_samples": total_samples,
        "covered_samples": n_covered,
        "abstained_samples": n_abstained,
        "coverage": round(coverage, 4),
        "coverage_95ci": [round(cov_low, 4), round(cov_high, 4)],
        "abstention_rate": round(abstention_rate, 4),
        "covered_accuracy": round(covered_acc, 4),
        "covered_accuracy_95ci": [round(cov_acc_low, 4), round(cov_acc_high, 4)],
        "selective_risk": round(selective_risk, 4),
        "coverage_adjusted_accuracy": round(cov_adjusted_acc, 4),
        "definitions": {
            "coverage": "Fraction of samples where the system committed to a verdict without abstaining",
            "covered_accuracy": "Accuracy evaluated strictly on non-abstained decisions",
            "selective_risk": "Empirical error rate on non-abstained decisions (1 - covered_accuracy)",
            "coverage_adjusted_accuracy": "Total correct predictions divided by all samples (treating abstentions as non-resolutions)"
        }
    }


def compute_calibration_metrics(
    y_true: List[int],
    confidences: List[float],
    n_bins: int = 5
) -> Dict[str, Any]:
    """
    Computes Expected Calibration Error (ECE), Brier score, and reliability bin statistics.
    Confidence represents the model's confidence in its predicted class.
    """
    if len(y_true) == 0 or len(confidences) != len(y_true):
        return {"ece": 0.0, "brier_score": 0.0, "bins": []}

    y_arr = np.array(y_true)
    c_arr = np.array(confidences)
    n = len(y_arr)

    # Brier score: MSE between confidence (in class 1) and actual binary label
    brier = float(brier_score_loss(y_arr, c_arr))

    # Bins across [0.5, 1.0] since binary confidence is typically >= 0.5 for predicted class
    # or [0.0, 1.0] for predicted probability
    min_c = min(c_arr)
    bin_low = 0.5 if min_c >= 0.5 else 0.0
    bin_edges = np.linspace(bin_low, 1.0, n_bins + 1)

    ece = 0.0
    bins_data = []

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]
        if i == n_bins - 1:
            in_bin = (c_arr >= low) & (c_arr <= high)
        else:
            in_bin = (c_arr >= low) & (c_arr < high)

        count = int(np.sum(in_bin))
        if count > 0:
            bin_acc = float(np.mean(y_arr[in_bin]))
            bin_conf = float(np.mean(c_arr[in_bin]))
            bin_error = abs(bin_acc - bin_conf)
            ece += (count / n) * bin_error

            bins_data.append({
                "bin_range": f"{low:.2f}-{high:.2f}",
                "count": count,
                "empirical_accuracy": round(bin_acc, 4),
                "mean_confidence": round(bin_conf, 4),
                "calibration_gap": round(bin_error, 4)
            })
        else:
            bins_data.append({
                "bin_range": f"{low:.2f}-{high:.2f}",
                "count": 0,
                "empirical_accuracy": None,
                "mean_confidence": None,
                "calibration_gap": None
            })

    return {
        "expected_calibration_error": round(float(ece), 4),
        "brier_score": round(brier, 4),
        "bin_count": n_bins,
        "bins": bins_data,
        "definition": "ECE measures the weighted average absolute difference between predicted confidence and empirical accuracy."
    }


def compute_retrieval_metrics(
    ranked_relevance: List[List[int]],
    k_list: Tuple[int, ...] = (1, 3, 5, 10)
) -> Dict[str, Any]:
    """
    Computes retrieval quality metrics:
    - Recall@K: fraction of queries where at least one relevant document is in top-K
    - MRR (Mean Reciprocal Rank): 1 / rank of first relevant document
    - nDCG@K: normalized discounted cumulative gain
    ranked_relevance: List of queries, where each item is a list of binary relevances (1=relevant, 0=not) in retrieval rank order.
    """
    if not ranked_relevance:
        return {"mrr": 0.0, "recall": {f"recall@{k}": 0.0 for k in k_list}}

    mrr_total = 0.0
    recall_totals = {k: 0.0 for k in k_list}
    q_count = len(ranked_relevance)

    for ranks in ranked_relevance:
        # First relevant rank (1-indexed)
        first_rel = -1
        for idx, rel in enumerate(ranks):
            if rel > 0:
                first_rel = idx + 1
                break

        if first_rel > 0:
            mrr_total += 1.0 / first_rel
            for k in k_list:
                if first_rel <= k:
                    recall_totals[k] += 1.0

    return {
        "query_count": q_count,
        "mrr": round(mrr_total / q_count, 4),
        **{f"recall@{k}": round(recall_totals[k] / q_count, 4) for k in k_list}
    }


def mcnemar_significance_test(
    y_true: List[int],
    y_pred_a: List[int],
    y_pred_b: List[int]
) -> Dict[str, Any]:
    """
    Computes McNemar's test with Edwards continuity correction for paired nominal classification models.
    Contingency table:
      b: A correct, B incorrect
      c: A incorrect, B correct
    """
    if len(y_true) != len(y_pred_a) or len(y_true) != len(y_pred_b) or len(y_true) == 0:
        return {"error": "Mismatched sample lengths"}

    b = 0  # A right, B wrong
    c = 0  # A wrong, B right
    a_and_b = 0  # Both right
    neither = 0  # Both wrong

    for yt, pa, pb in zip(y_true, y_pred_a, y_pred_b):
        a_ok = (yt == pa)
        b_ok = (yt == pb)
        if a_ok and b_ok:
            a_and_b += 1
        elif a_ok and not b_ok:
            b += 1
        elif not a_ok and b_ok:
            c += 1
        else:
            neither += 1

    discordant = b + c
    if discordant == 0:
        chi2_stat = 0.0
        p_val = 1.0
    else:
        # Edwards continuity correction
        chi2_stat = (abs(b - c) - 1.0) ** 2 / discordant
        p_val = 1.0 - stats.chi2.cdf(chi2_stat, df=1)

    return {
        "contingency_table": {
            "both_correct": a_and_b,
            "model_a_only": b,
            "model_b_only": c,
            "both_incorrect": neither
        },
        "chi2_statistic": round(float(chi2_stat), 4),
        "p_value": float(f"{p_val:.6g}"),
        "method": "McNemar test with Edwards continuity correction (df=1)"
    }


class ClassificationMetrics:
    """Dataclass wrapper for classification metrics."""
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.accuracy = data.get("accuracy", 0.0)
        self.macro_f1 = data.get("macro_f1", 0.0)
        self.precision = data.get("macro_precision", 0.0)
        self.recall = data.get("macro_recall", 0.0)
        self.accuracy_ci_95_low = data.get("accuracy_95ci", [0.0, 0.0])[0]
        self.accuracy_ci_95_high = data.get("accuracy_95ci", [0.0, 0.0])[1]
        self.macro_f1_bootstrap_ci_95_low = data.get("macro_f1_95ci", [0.0, 0.0])[0]
        self.macro_f1_bootstrap_ci_95_high = data.get("macro_f1_95ci", [0.0, 0.0])[1]
        self.total_samples = data.get("sample_count", 0)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class RetrievalMetrics:
    """Dataclass wrapper for retrieval metrics."""
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.mrr = data.get("mrr", 0.0)
        self.recall_at_1 = data.get("recall@1", 0.0)
        self.recall_at_3 = data.get("recall@3", 0.0)
        self.recall_at_5 = data.get("recall@5", 0.0)
        self.recall_at_10 = data.get("recall@10", 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


def compute_expected_calibration_error(y_true: List[int], y_prob: List[float], n_bins: int = 5) -> float:
    calib = compute_calibration_metrics(y_true, y_prob, n_bins=n_bins)
    return float(calib.get("expected_calibration_error", 0.0))


def compute_brier_score(y_true: List[int], y_prob: List[float]) -> float:
    calib = compute_calibration_metrics(y_true, y_prob)
    return float(calib.get("brier_score", 0.0))


def compute_calibration_curve(y_true: List[int], y_prob: List[float], n_bins: int = 5) -> List[Dict[str, Any]]:
    calib = compute_calibration_metrics(y_true, y_prob, n_bins=n_bins)
    return calib.get("bins", [])

