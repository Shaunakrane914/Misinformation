"""
Aegis Protocol — Second-Stage Cross-Encoder Semantic Reranker
============================================================
Provides neural cross-encoder semantic reranking for candidate retrieval.
Operates downstream of the hard entity gate and first-stage deterministic ranker:

    Candidate discovery
            ↓
    Entity hard gate
            ↓
    Current deterministic relevance/ranking (Top 20–30)
            ↓
    Semantic reranker (CrossEncoder ms-marco-MiniLM-L-6-v2)
            ↓
    Top candidates
            ↓
    Deep acquisition
            ↓
    Evidence quality gate

Invariants:
1. Deterministic inference settings.
2. Supports CPU and CUDA execution with explicit telemetry.
3. Graceful degradation: If model is unavailable or disabled, preserves first-stage
   order and sets semantic_score=None (never fabricates fake scores).
4. Controlled via AEGIS_SEMANTIC_RERANKER environment variable.
"""

import os
import math
import time
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Configurable environment variable
ENV_SEMANTIC_RERANKER = "AEGIS_SEMANTIC_RERANKER"


def sigmoid(x: float) -> float:
    """Map logit score to [0.0, 1.0] interval."""
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


class SemanticReranker:
    """
    Second-stage neural CrossEncoder reranker for high-precision semantic candidate ranking.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        enabled: Optional[bool] = None,
        top_k_input: int = 30,
        top_k_output: int = 5,
        device: Optional[str] = None,
        batch_size: int = 16,
    ):
        self.model_name = model_name
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = os.getenv(ENV_SEMANTIC_RERANKER, "0").strip() in ("1", "true", "True")

        self.top_k_input = top_k_input
        self.top_k_output = top_k_output
        self.batch_size = batch_size
        self.device = device
        self.device_used = "none"

        self._model = None
        self._available = False
        self._load_attempted = False
        self._load_error: Optional[str] = None

        # Observable telemetry
        self.pairs_scored_count = 0
        self.total_inference_time_sec = 0.0
        self.inference_failure_count = 0
        self.fallback_count = 0

        if self.enabled:
            self._ensure_loaded()

    def _ensure_loaded(self) -> bool:
        """Lazily load the CrossEncoder model."""
        if self._load_attempted:
            return self._available

        self._load_attempted = True
        try:
            import torch
            from sentence_transformers import CrossEncoder

            dev = self.device
            if dev is None:
                dev = "cuda" if torch.cuda.is_available() else "cpu"

            self.device_used = dev
            logger.info("Initializing SemanticReranker with model '%s' on %s", self.model_name, dev)
            self._model = CrossEncoder(
                self.model_name,
                max_length=512,
                device=dev,
            )
            self._available = True
            logger.info("SemanticReranker successfully initialized on %s", dev)
        except Exception as ex:
            self._load_error = str(ex)
            logger.warning("SemanticReranker failed to load model '%s': %s", self.model_name, ex)
            self._available = False
            self._model = None

        return self._available

    @property
    def is_available(self) -> bool:
        if not self._load_attempted and self.enabled:
            return self._ensure_loaded()
        return self._available

    def get_telemetry(self) -> Dict[str, Any]:
        """Expose observable execution telemetry."""
        return {
            "model_name": self.model_name,
            "enabled": self.enabled,
            "is_available": self._available,
            "device": self.device_used,
            "pairs_scored": self.pairs_scored_count,
            "inference_duration_sec": round(self.total_inference_time_sec, 3),
            "inference_failures": self.inference_failure_count,
            "fallback_count": self.fallback_count,
            "load_error": self._load_error,
        }

    def score_text_pairs(self, pairs: List[Tuple[str, str]]) -> List[Dict[str, float]]:
        """
        Compute CrossEncoder predictions for a list of (query, document) text pairs.
        Returns list of dicts with 'raw_score' (logit) and 'semantic_score' (sigmoid [0, 1]).
        """
        if not self.enabled or not self.is_available or not self._model:
            self.fallback_count += len(pairs)
            return [{"raw_score": 0.0, "semantic_score": 0.0} for _ in pairs]

        if not pairs:
            return []

        start_t = time.time()
        try:
            import torch
            with torch.no_grad():
                logits = self._model.predict(
                    pairs,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                )

            elapsed = time.time() - start_t
            self.total_inference_time_sec += elapsed
            self.pairs_scored_count += len(pairs)

            results = []
            for score in logits:
                val = float(score)
                results.append({
                    "raw_score": round(val, 4),
                    "semantic_score": round(sigmoid(val), 4),
                })
            return results
        except Exception as ex:
            self.inference_failure_count += 1
            self.fallback_count += len(pairs)
            logger.error("Error during CrossEncoder inference: %s", ex)
            return [{"raw_score": 0.0, "semantic_score": 0.0} for _ in pairs]

    def rerank(
        self,
        query: str,
        candidates: List[Any],
        top_k: Optional[int] = None,
        entity_score_threshold: float = 0.35,
    ) -> List[Any]:
        """
        Rerank a pool of candidates using second-stage neural cross-encoding.
        """
        k_out = top_k if top_k is not None else self.top_k_output
        if not candidates:
            return []

        # Graceful degradation if disabled or model unavailable
        if not self.enabled or not self.is_available:
            self.fallback_count += len(candidates[:k_out])
            annotated = []
            for idx, c in enumerate(candidates[:k_out]):
                item = self._ensure_dict(c)
                item["semantic_score"] = None
                item["raw_cross_encoder_score"] = None
                item["semantic_status"] = "DISABLED" if not self.enabled else "UNAVAILABLE"
                annotated.append(item)
            return annotated

        # Take up to top_k_input candidates
        pool = [self._ensure_dict(c) for c in candidates[: self.top_k_input]]

        # Build query-document pairs
        pairs = []
        for c in pool:
            title = c.get("title") or c.get("headline") or ""
            snippet = c.get("snippet") or c.get("content") or c.get("relevant_excerpt") or ""
            doc_text = f"{title}. {snippet}".strip()
            pairs.append((query, doc_text))

        # Predict semantic scores
        scores = self.score_text_pairs(pairs)

        # Attach scores and compute hybrid rerank score
        for idx, item in enumerate(pool):
            sc = scores[idx] if idx < len(scores) else {"raw_score": 0.0, "semantic_score": 0.0}
            sem_score = sc["semantic_score"]
            raw_logit = sc["raw_score"]

            item["semantic_score"] = sem_score
            item["raw_cross_encoder_score"] = raw_logit
            item["semantic_status"] = "SCORED"

            first_stage = item.get("first_stage_score") or item.get("relevance_score") or 0.50
            entity_score = item.get("entity_score", 0.50)

            # Invariant: If candidate failed temporal eligibility (e.g. stale trending article),
            # the neural reranker MUST NOT restore or promote it into top rank!
            if item.get("temporal_eligible") is False or item.get("rejection_stage") == "TEMPORAL_GATE_ERROR":
                rerank_score = 0.0
            elif entity_score < entity_score_threshold:
                # Heavy penalty for failed entity match
                rerank_score = sem_score * 0.10
            else:
                # Balanced hybrid second-stage: 40% first-stage gate + 60% neural cross-encoder
                rerank_score = 0.40 * first_stage + 0.60 * sem_score

            item["rerank_score"] = round(rerank_score, 4)

        # Sort descending by rerank_score
        sorted_candidates = sorted(
            pool,
            key=lambda x: (x.get("rerank_score", 0.0), x.get("relevance_score", 0.0)),
            reverse=True,
        )

        return sorted_candidates[:k_out]

    def _ensure_dict(self, candidate: Any) -> Dict[str, Any]:
        """Convert candidate object to dict if necessary."""
        if isinstance(candidate, dict):
            return dict(candidate)
        elif hasattr(candidate, "to_dict"):
            return candidate.to_dict()
        elif hasattr(candidate, "__dict__"):
            return dict(candidate.__dict__)
        else:
            return {"raw": candidate}


# Global singleton instance
semantic_reranker = SemanticReranker()
