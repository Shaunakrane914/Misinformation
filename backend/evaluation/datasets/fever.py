"""
Aegis Protocol — FEVER Benchmark Adapter
========================================
Research adapter for FEVER (Fact Extraction and VERification, Thorne et al., NAACL 2018).

Task Definition:
- Given a textual claim and a corpus of reference articles (e.g. Wikipedia),
  1. Retrieve relevant evidence sentences (Evidence Retrieval: Recall@K, Precision@K).
  2. Predict the verification verdict: SUPPORTS, REFUTES, or NOT ENOUGH INFO.
  3. Calculate the strict FEVER Score: correct verdict AND correct evidence retrieved.

Label Taxonomy:
- SUPPORTS         -> Maps to Aegis "True"
- REFUTES          -> Maps to Aegis "False"
- NOT ENOUGH INFO  -> Maps to Aegis "Insufficient Evidence" (Abstention)
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple


class FEVERAdapter:
    """
    Adapter that normalizes FEVER benchmark instances into the Aegis Claim format,
    providing standardized metrics for evidence retrieval and claim verification.
    """

    LABEL_MAPPING = {
        "SUPPORTS": "True",
        "REFUTES": "False",
        "NOT ENOUGH INFO": "Insufficient Evidence",
    }

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "fever_dev.jsonl")
        )
        self.is_available = os.path.exists(self.data_path)

    def status(self) -> Dict[str, Any]:
        """Reports availability status with academic provenance."""
        if not self.is_available:
            return {
                "benchmark_name": "FEVER (NAACL 2018)",
                "status": "NOT RUN",
                "reason": (
                    f"Benchmark dataset file not locally present at {self.data_path}. "
                    "Download official splits from https://fever.ai/resources.html"
                ),
                "paper": "Thorne et al., 'FEVER: a large-scale dataset for Fact Extraction and VERification', NAACL 2018.",
                "official_url": "https://fever.ai/",
                "task_decomposition": [
                    "Document Retrieval (Entity linking / Search)",
                    "Sentence Selection (Evidence Reranking: Recall@K, MRR)",
                    "Recognizing Textual Entailment (Verdicts: SUPPORTS, REFUTES, NOT ENOUGH INFO)",
                ],
                "label_taxonomy": list(self.LABEL_MAPPING.keys()),
            }

        file_size = os.path.getsize(self.data_path)
        return {
            "benchmark_name": "FEVER (NAACL 2018)",
            "status": "READY",
            "file_path": self.data_path,
            "file_size_bytes": file_size,
            "label_taxonomy": list(self.LABEL_MAPPING.keys()),
        }

    def load_samples(self, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        """Loads normalized FEVER instances from JSONL."""
        if not self.is_available:
            raise FileNotFoundError(
                f"FEVER dataset not found at {self.data_path}. "
                "Download the official dataset from https://fever.ai/resources.html"
            )

        records = []
        with open(self.data_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if max_samples and idx >= max_samples:
                    break
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                raw_label = item.get("label", "NOT ENOUGH INFO")
                mapped_verdict = self.LABEL_MAPPING.get(raw_label, "Unverified")

                # Extract gold evidence sets [[annotation_id, evidence_id, page_title, sentence_id], ...]
                gold_evidence = []
                raw_evidence = item.get("evidence", [])
                for ev_set in raw_evidence:
                    for ev in ev_set:
                        if len(ev) >= 4 and ev[2] is not None:
                            gold_evidence.append({
                                "page": ev[2],
                                "sentence_id": ev[3],
                            })

                records.append({
                    "claim_id": str(item.get("id", idx)),
                    "claim_text": item.get("claim", "").strip(),
                    "original_label": raw_label,
                    "canonical_verdict": mapped_verdict,
                    "is_abstained_expected": (mapped_verdict == "Insufficient Evidence"),
                    "gold_evidence": gold_evidence,
                })

        return records

    @staticmethod
    def evaluate_evidence_retrieval(
        retrieved_pages: List[str],
        gold_evidence: List[Dict[str, Any]],
        k_list: Tuple[int, ...] = (1, 3, 5, 10),
    ) -> Dict[str, Any]:
        """
        Evaluates whether retrieved documents contain the gold reference documents.
        """
        if not gold_evidence:
            return {f"recall@{k}": 1.0 for k in k_list}

        gold_pages = {ev["page"] for ev in gold_evidence if ev.get("page")}
        if not gold_pages:
            return {f"recall@{k}": 1.0 for k in k_list}

        results = {}
        for k in k_list:
            top_k_set = set(retrieved_pages[:k])
            # Check if at least one complete evidence item is covered
            hit = bool(gold_pages.intersection(top_k_set))
            results[f"recall@{k}"] = 1.0 if hit else 0.0

        return results


FEVERDataset = FEVERAdapter
