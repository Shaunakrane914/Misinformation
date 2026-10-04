"""
Aegis Protocol — AVeriTeC Benchmark Adapter
===========================================
Research adapter for AVeriTeC (Automated Verification of Textual Claims, Schlichtkrull et al., NeurIPS 2023).

Task Definition:
- Given an open-domain real-world claim and web-retrieved QA evidence documents,
  predict the truthfulness label and justify with question-answer evidence pairs.

Label Taxonomy:
- Supported                  -> Maps to Aegis "True" (label 0)
- Refuted                    -> Maps to Aegis "False" (label 1)
- Not Enough Evidence (NEI)  -> Maps to Aegis "Insufficient Evidence" (Abstention)
- Conflicting Evidence       -> Maps to Aegis "Misleading" (Partially True / Disputed)

Data Structure:
- Each item contains: claim, claim_id, speaker, date, context, questions, answers, label.
"""

import os
import json
from typing import Dict, List, Any, Optional, Iterator


class AVeriTeCAdapter:
    """
    Adapter that normalizes AVeriTeC instances into Aegis Claim format
    without coupling benchmark assumptions into production agents.
    """

    LABEL_MAPPING = {
        "Supported": "True",
        "Refuted": "False",
        "Not Enough Evidence": "Insufficient Evidence",
        "Conflicting Evidence/Cherrypicking": "Misleading",
    }

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "averitec_dev.json")
        )
        self.is_available = os.path.exists(self.data_path)

    def status(self) -> Dict[str, Any]:
        """Reports availability status honestly without synthetic simulation."""
        if not self.is_available:
            return {
                "benchmark_name": "AVeriTeC (NeurIPS 2023)",
                "status": "NOT RUN",
                "reason": f"Benchmark dataset file not locally present at {self.data_path}. (Corpus size ~1.2 GB).",
                "paper": "Schlichtkrull et al., 'AVeriTeC: A Dataset for Real-world Claim Verification with Evidence from the Web', NeurIPS 2023.",
                "official_repository": "https://github.com/MichSchli/AVeriTeC",
                "official_protocol_summary": "Open-domain web search -> QA decomposition -> multi-hop evidence aggregation -> 4-way label prediction",
                "label_taxonomy": list(self.LABEL_MAPPING.keys())
            }
        
        file_size = os.path.getsize(self.data_path)
        return {
            "benchmark_name": "AVeriTeC (NeurIPS 2023)",
            "status": "READY",
            "file_path": self.data_path,
            "file_size_bytes": file_size,
            "label_taxonomy": list(self.LABEL_MAPPING.keys())
        }

    def load_samples(self, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
        """Loads normalized claim items if dataset exists."""
        if not self.is_available:
            raise FileNotFoundError(
                f"AVeriTeC dataset not found at {self.data_path}. "
                "Download the official dataset from https://github.com/MichSchli/AVeriTeC"
            )

        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = []
        for item in data[:max_samples] if max_samples else data:
            raw_label = item.get("label", "Not Enough Evidence")
            mapped_verdict = self.LABEL_MAPPING.get(raw_label, "Unverified")
            
            records.append({
                "claim_id": str(item.get("claim_id", "")),
                "claim_text": item.get("claim", "").strip(),
                "speaker": item.get("speaker"),
                "date": item.get("date"),
                "original_label": raw_label,
                "canonical_verdict": mapped_verdict,
                "is_abstained_expected": (mapped_verdict in ["Insufficient Evidence", "Unverified"]),
                "questions_evidence": item.get("questions", [])
            })

        return records


AVeriTeCAdapter.get_status = AVeriTeCAdapter.status
AVeriTeCDataset = AVeriTeCAdapter

