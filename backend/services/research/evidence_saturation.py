"""
Aegis Protocol — Evidence Saturation & Novelty Engine
=====================================================
Implements mathematical stopping criteria for adaptive research.
Tracks marginal evidence novelty N(q_k) and cumulative saturation index S_k
across retrieval iterations to prevent redundant search loops.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class NoveltyStepRecord:
    """Record of an individual query iteration's evidence yield and novelty."""
    step: int
    query_id: str
    query_text: str
    channel: str
    candidates_count: int
    new_entities_count: int
    marginal_novelty: float  # N(q_k) in [0.0, 1.0]
    cumulative_saturation: float  # S_k in [0.0, 1.0]
    halt_triggered: bool = False
    halt_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "query_id": self.query_id,
            "query_text": self.query_text,
            "channel": self.channel,
            "candidates_count": self.candidates_count,
            "new_entities_count": self.new_entities_count,
            "marginal_novelty": round(self.marginal_novelty, 3),
            "cumulative_saturation": round(self.cumulative_saturation, 3),
            "halt_triggered": self.halt_triggered,
            "halt_reason": self.halt_reason,
        }


class EvidenceNoveltyTracker:
    """
    Computes marginal novelty and saturation across successive query iterations.

    Mathematical Formulation:
      - Marginal Novelty N(q_k):
          N(q_k) = 0.5 * EntityNovelty + 0.5 * ShingleNovelty
          where EntityNovelty = |E_k \\ U_{j<k} E_j| / (|E_k| + 1)
          and ShingleNovelty = 1 - Jaccard(Shingles_k, Shingles_{<k})
      - Cumulative Saturation S_k:
          S_k = 1 - (1/k) * sum_{j=1}^k N(q_j)
      - Halting Rule:
          Halt when S_k >= tau (default 0.88) OR N(q_k) < epsilon (default 0.08)
          OR step >= max_steps
    """

    def __init__(
        self,
        saturation_threshold: float = 0.88,
        min_novelty_epsilon: float = 0.08,
        max_steps: int = 8
    ):
        self.saturation_threshold = saturation_threshold
        self.min_novelty_epsilon = min_novelty_epsilon
        self.max_steps = max_steps

        # Cumulative sets
        self._accumulated_entities: Set[str] = set()
        self._accumulated_shingles: Set[str] = set()
        self._step_records: List[NoveltyStepRecord] = []
        self._is_saturated: bool = False
        self._halt_reason: Optional[str] = None

    def _extract_shingles(self, text: str, n: int = 3) -> Set[str]:
        """Extract character/token n-grams for semantic overlap detection."""
        tokens = re.findall(r'\b[a-z0-9]{3,}\b', (text or "").lower())
        if len(tokens) < n:
            return set(tokens)
        return {" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}

    def _extract_entities_heuristic(self, text: str) -> Set[str]:
        """Heuristic named entity extraction for capitalization/ticker patterns."""
        # Find capitalized words or all-caps tickers (e.g. TSLA, JLR, SEBI, Q3)
        tickers = set(re.findall(r'\b[A-Z]{2,6}\b', text))
        proper_names = set(re.findall(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b', text))
        return {e.lower() for e in (tickers | proper_names)}

    def record_step(
        self,
        query_id: str,
        query_text: str,
        channel: str,
        evidence_snippets: List[str],
        explicit_entities: Optional[List[str]] = None
    ) -> NoveltyStepRecord:
        """
        Record a query retrieval step, calculate marginal novelty, and check saturation.
        """
        step = len(self._step_records) + 1
        combined_text = " ".join(evidence_snippets)

        # 1. Entity Set for this step
        step_entities = set(e.lower() for e in (explicit_entities or []))
        step_entities.update(self._extract_entities_heuristic(combined_text))

        # 2. Shingle Set for this step
        step_shingles = self._extract_shingles(combined_text)

        # 3. Calculate Marginal Novelty
        if step == 1:
            marginal_novelty = 0.95 if evidence_snippets else 0.50
            new_entities_count = len(step_entities)
        else:
            # Entity Novelty
            new_entities = step_entities - self._accumulated_entities
            new_entities_count = len(new_entities)
            entity_novelty = (new_entities_count / (len(step_entities) + 1)) if step_entities else 0.0

            # Shingle Novelty (1 - Jaccard overlap)
            if self._accumulated_shingles and step_shingles:
                inter = len(step_shingles & self._accumulated_shingles)
                union = len(step_shingles | self._accumulated_shingles)
                jaccard_overlap = inter / union if union > 0 else 0.0
                shingle_novelty = 1.0 - jaccard_overlap
            else:
                shingle_novelty = 0.80 if step_shingles else 0.10

            marginal_novelty = 0.50 * entity_novelty + 0.50 * shingle_novelty
            # Bound within [0.0, 1.0]
            marginal_novelty = max(0.0, min(1.0, marginal_novelty))

        # Update accumulators
        self._accumulated_entities.update(step_entities)
        self._accumulated_shingles.update(step_shingles)

        # 4. Calculate Cumulative Saturation
        prior_novelties = [r.marginal_novelty for r in self._step_records] + [marginal_novelty]
        mean_novelty = sum(prior_novelties) / len(prior_novelties)
        cumulative_saturation = max(0.0, min(1.0, 1.0 - (mean_novelty * (1.0 / (1.0 + 0.15 * step)))))

        # 5. Check Halting Condition
        halt_triggered = False
        halt_reason = None

        if cumulative_saturation >= self.saturation_threshold:
            halt_triggered = True
            halt_reason = f"Saturation threshold reached (S_{step}={cumulative_saturation:.2f} >= {self.saturation_threshold})"
        elif marginal_novelty < self.min_novelty_epsilon and step >= 3:
            halt_triggered = True
            halt_reason = f"Marginal novelty depleted (N_{step}={marginal_novelty:.2f} < {self.min_novelty_epsilon})"
        elif step >= self.max_steps:
            halt_triggered = True
            halt_reason = f"Max retrieval steps reached ({self.max_steps})"

        if halt_triggered:
            self._is_saturated = True
            self._halt_reason = halt_reason

        record = NoveltyStepRecord(
            step=step,
            query_id=query_id,
            query_text=query_text,
            channel=channel,
            candidates_count=len(evidence_snippets),
            new_entities_count=new_entities_count,
            marginal_novelty=marginal_novelty,
            cumulative_saturation=cumulative_saturation,
            halt_triggered=halt_triggered,
            halt_reason=halt_reason,
        )
        self._step_records.append(record)
        return record

    @property
    def is_saturated(self) -> bool:
        return self._is_saturated

    @property
    def halt_reason(self) -> Optional[str]:
        return self._halt_reason

    def get_saturation_curve(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._step_records]

    def get_summary(self) -> Dict[str, Any]:
        """Return executive summary of the saturation lifecycle."""
        if not self._step_records:
            return {"steps_executed": 0, "saturated": False}

        final_rec = self._step_records[-1]
        return {
            "steps_executed": len(self._step_records),
            "final_marginal_novelty": round(final_rec.marginal_novelty, 3),
            "final_saturation_index": round(final_rec.cumulative_saturation, 3),
            "is_saturated": self._is_saturated,
            "stopping_criterion_met": self._is_saturated,
            "halt_reason": self._halt_reason or "Completed standard budget",
            "saturation_curve": self.get_saturation_curve(),
            "total_unique_entities": len(self._accumulated_entities),
        }
