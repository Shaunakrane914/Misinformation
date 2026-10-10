"""
Aegis Protocol — Baseline Classifiers
=====================================
Implements sound, leak-free baselines for claim and article classification:
1. TfidfLogisticBaseline: Classical supervised ML (TF-IDF + L2 Logistic Regression)
2. SinglePromptLLMBaseline: Direct LLM classification without retrieval or multi-agent orchestration
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.evaluation.metrics import (
    ClassificationMetrics,
    compute_brier_score,
    compute_calibration_curve,
    compute_classification_metrics,
    compute_expected_calibration_error,
)

logger = logging.getLogger(__name__)


class TfidfLogisticBaseline:
    """
    Supervised classical ML baseline for article/claim classification.
    - Vectorizer fit ONLY on training data.
    - Classifier fit ONLY on training data.
    - Evaluated strictly on held-out test data.
    - Zero ground-truth leakage.
    """

    def __init__(
        self,
        max_features: int = 10000,
        ngram_range: Tuple[int, int] = (1, 2),
        C: float = 1.0,
        max_iter: int = 1000,
        random_state: int = 42,
    ):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression

        self.max_features = max_features
        self.ngram_range = ngram_range
        self.C = C
        self.max_iter = max_iter
        self.random_state = random_state

        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=True,
            stop_words="english",
        )
        self.classifier = LogisticRegression(
            C=C,
            max_iter=max_iter,
            random_state=random_state,
            solver="lbfgs",
            class_weight="balanced",
        )
        self.is_trained = False
        self.train_time_sec: float = 0.0

    def fit(self, train_texts: List[str], train_labels: List[int]) -> "TfidfLogisticBaseline":
        """Fit vectorizer and logistic regression on training split only."""
        t0 = time.perf_counter()
        logger.info(f"Fitting TF-IDF vectorizer on {len(train_texts)} training samples...")
        X_train = self.vectorizer.fit_transform(train_texts)

        logger.info(f"Fitting LogisticRegression (C={self.C}, max_iter={self.max_iter})...")
        self.classifier.fit(X_train, train_labels)

        self.train_time_sec = time.perf_counter() - t0
        self.is_trained = True
        logger.info(f"Training completed in {self.train_time_sec:.2f}s")
        return self

    def predict_proba(self, texts: List[str]) -> np.ndarray:
        """Return probability estimates (P(y=0), P(y=1))."""
        if not self.is_trained:
            raise RuntimeError("Model must be fit before calling predict_proba.")
        X = self.vectorizer.transform(texts)
        return self.classifier.predict_proba(X)

    def predict(self, texts: List[str]) -> np.ndarray:
        """Return discrete binary predictions (0 or 1)."""
        if not self.is_trained:
            raise RuntimeError("Model must be fit before calling predict.")
        X = self.vectorizer.transform(texts)
        return self.classifier.predict(X)

    def evaluate(
        self,
        test_texts: List[str],
        test_labels: List[int],
        split_name: str = "test",
    ) -> Dict[str, Any]:
        """
        Evaluate strictly on held-out data.
        Returns comprehensive metrics with confidence intervals and calibration.
        """
        if not self.is_trained:
            raise RuntimeError("Model must be fit before evaluation.")

        t0 = time.perf_counter()
        probabilities = self.predict_proba(test_texts)
        infer_time_sec = time.perf_counter() - t0

        predictions = np.argmax(probabilities, axis=1).tolist()
        confidences = np.max(probabilities, axis=1).tolist()
        p1 = probabilities[:, 1].tolist()

        metrics = ClassificationMetrics(
            compute_classification_metrics(
                y_true=test_labels,
                y_pred=predictions,
                confidences=confidences,
                seed=self.random_state,
            )
        )


        ece = compute_expected_calibration_error(y_true=test_labels, y_prob=p1)
        brier = compute_brier_score(y_true=test_labels, y_prob=p1)
        bins = compute_calibration_curve(y_true=test_labels, y_prob=p1)

        return {
            "model": "tfidf_logistic_regression",
            "split": split_name,
            "sample_count": len(test_texts),
            "inference_time_sec": round(infer_time_sec, 3),
            "throughput_samples_per_sec": round(len(test_texts) / max(infer_time_sec, 0.001), 1),
            "metrics": metrics.to_dict(),
            "calibration": {
                "ece": round(ece, 4),
                "brier_score": round(brier, 4),
                "bins": bins,
            },
            "hyperparameters": {
                "max_features": self.max_features,
                "ngram_range": list(self.ngram_range),
                "C": self.C,
                "max_iter": self.max_iter,
                "random_state": self.random_state,
                "train_time_sec": round(self.train_time_sec, 3),
            },
        }


class SinglePromptLLMBaseline:
    """
    Evaluates Gemini directly on headline/claim classification without retrieval,
    without evidence, and without multi-agent routing.
    Strictly isolated from ground truth.
    """

    SYSTEM_PROMPT = (
        "You are an impartial fact-checking classifier. Your task is to evaluate the provided "
        "headline or claim solely based on your internal knowledge.\n"
        "Do not assume the claim is true or false without basis.\n"
        "Output strictly valid JSON with the following schema:\n"
        "{\n"
        '  "prediction": "Real" | "Fake" | "Unverified",\n'
        '  "confidence": <float between 0.50 and 1.00>,\n'
        '  "reasoning": "<concise explanation>"\n'
        "}\n"
        "If you do not have sufficient historical knowledge to determine veracity, output "
        '"Unverified" with confidence 0.50.'
    )

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        allow_mock: bool = False,
    ):
        self.model_name = model_name
        self.allow_mock = allow_mock

    def evaluate_sample(self, claim_text: str) -> Dict[str, Any]:
        """
        Evaluate a single claim text without ground truth access.
        Returns prediction, confidence, latency, and whether fallback/failure occurred.
        """
        import json
        from backend.services.gemini_service import gemini_service

        user_content = f"Evaluate this claim/headline:\n\"{claim_text}\""

        # In scientific mode (allow_mock=False), verify live API key exists
        has_valid_key = any(k.startswith("AIzaSy") for k in gemini_service.api_keys)
        if not self.allow_mock and not has_valid_key:
            return {
                "status": "BLOCKED",
                "error": "No valid Google AI Studio key (AIzaSy...) configured for live scientific benchmark",
                "prediction": "Unverified",
                "prediction_label": "Unverified",
                "prediction_int": -1,
                "confidence": 0.5,
                "abstained": True,
                "latency_ms": 0.0,
                "provider": "none",
            }

        t0 = time.perf_counter()
        try:
            raw_response = gemini_service.generate_text(
                prompt=f"{self.SYSTEM_PROMPT}\n\n{user_content}",
                allow_mock_fallback=self.allow_mock,
                model=self.model_name,
            )
            latency_ms = (time.perf_counter() - t0) * 1000.0

            # Clean JSON markdown fences if present
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            pred_raw = parsed.get("prediction", "Unverified")
            conf = float(parsed.get("confidence", 0.5))

            # Normalize prediction: WELFake uses 0=Real, 1=Fake
            abstained = pred_raw == "Unverified"
            pred_int = 1 if pred_raw == "Fake" else (0 if pred_raw == "Real" else -1)

            return {
                "status": "RUN",
                "prediction_label": pred_raw,
                "prediction_int": pred_int,
                "confidence": min(max(conf, 0.5), 1.0),
                "abstained": abstained,
                "reasoning": parsed.get("reasoning", ""),
                "latency_ms": round(latency_ms, 2),
                "provider": "offline_mock" if self.allow_mock else "live_gemini",
                "model": self.model_name,
            }
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning(f"SinglePromptLLMBaseline query failed: {exc}")
            return {
                "status": "FAILED",
                "error": str(exc),
                "prediction_label": "Unverified",
                "prediction_int": -1,
                "confidence": 0.5,
                "abstained": True,
                "latency_ms": round(latency_ms, 2),
                "provider": "error",
                "model": self.model_name,
            }

