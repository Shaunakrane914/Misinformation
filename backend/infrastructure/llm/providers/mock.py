"""
Aegis Protocol — Mock LLM Provider
===================================
Deterministic mock provider for offline development, evaluation, and test suites.
Guarantees 100% offline determinism, zero network egress, and realistic structured outputs.
"""

from __future__ import annotations

import json
import time
from typing import Any
from backend.infrastructure.llm.protocol import LLMProvider, LLMResponse, LLMUsage


class MockLLMProvider(LLMProvider):
    """Deterministic, offline-safe mock provider."""

    def __init__(self, latency_sim_seconds: float = 0.0):
        self.latency_sim_seconds = latency_sim_seconds

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, model: str | None = None, **kwargs: Any) -> LLMResponse:
        t0 = time.perf_counter()
        if self.latency_sim_seconds > 0:
            time.sleep(self.latency_sim_seconds)

        content = self._resolve_mock_content(prompt)
        latency = (time.perf_counter() - t0) * 1000

        return LLMResponse(
            content=content,
            model="mock-model",
            provider="mock",
            latency_ms=latency,
            usage=LLMUsage(
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(content.split()),
                total_tokens=len(prompt.split()) + len(content.split()),
                estimated_cost_usd=0.0
            ),
            synthetic=True,
            metadata={
                "synthetic": True,
                "evidence_eligible": False,
                "requested_model": model,
            },
        )

    @staticmethod
    def _json(payload: Any) -> str:
        """Attach an auditable marker without changing the expected container."""
        marker = {
            "provider": "mock",
            "synthetic": True,
            "evidence_eligible": False,
        }
        if isinstance(payload, dict):
            payload = {**payload, "_aegis_provenance": marker}
        elif isinstance(payload, list):
            payload = [
                {**item, "_aegis_provenance": marker} if isinstance(item, dict) else item
                for item in payload
            ]
        return json.dumps(payload)

    def _resolve_mock_content(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        # 1. Evidence extraction mock
        if "search and summarize evidence" in prompt_lower or "supporting_evidence" in prompt_lower:
            if any(w in prompt_lower for w in ["lemon", "diabetes", "cure cancer", "blood sugar"]):
                return self._json({
                    "supporting_evidence": [],
                    "refuting_evidence": [
                        "Clinical research and medical guidance indicate this intervention has no demonstrated therapeutic efficacy.",
                        "Health regulatory authorities have debunked claims of rapid curative properties."
                    ],
                    "overall_evidence_confidence": 0.05
                })
            elif any(w in prompt_lower for w in ["whatsapp", "red tick", "three tick", "tick"]):
                return self._json({
                    "supporting_evidence": [],
                    "refuting_evidence": [
                        "Official platform documentation confirms tick marks denote delivery and read status only.",
                        "Fact-checking organizations confirmed no government enforcement action is indicated by message checkmarks."
                    ],
                    "overall_evidence_confidence": 0.05
                })
            elif any(w in prompt_lower for w in ["water", "gravity", "earth orbits", "nasa", "europa"]):
                return self._json({
                    "supporting_evidence": [
                        "Empirical scientific records and peer-reviewed observations confirm the claim.",
                        "Published research from primary institutional repositories substantiates the premise."
                    ],
                    "refuting_evidence": [],
                    "overall_evidence_confidence": 0.95
                })
            else:
                return self._json({
                    "supporting_evidence": [],
                    "refuting_evidence": ["Verified public reporting and official registries indicate no substantiation for this claim."],
                    "overall_evidence_confidence": 0.35
                })

        # 2. Verdict synthesis mock
        if "determine the verdict" in prompt_lower or "final verdict" in prompt_lower or "verdict" in prompt_lower or "fact-checking" in prompt_lower:
            if "gathered refuting evidence:" in prompt_lower and "gathered supporting evidence:" in prompt_lower:
                idx_ref = prompt.find("GATHERED REFUTING EVIDENCE:")
                idx_sup = prompt.find("GATHERED SUPPORTING EVIDENCE:")
                idx_score = prompt.find("EVIDENCE RETRIEVAL CONFIDENCE SCORE:")

                sup_chunk = prompt[idx_sup:idx_ref] if idx_sup != -1 and idx_ref != -1 else ""
                ref_chunk = prompt[idx_ref:idx_score] if idx_ref != -1 and idx_score != -1 else prompt[idx_ref:]

                has_refuting = '"claim_supported": false' in ref_chunk.lower() or '"text":' in ref_chunk.lower()
                has_supporting = '"claim_supported": true' in sup_chunk.lower() or '"text":' in sup_chunk.lower()

                if has_refuting and not has_supporting:
                    return self._json({
                        "verdict": "False",
                        "confidence": 0.94,
                        "severity": "High",
                        "reasoning": "Primary investigation and corroborating debunks disprove the claim.",
                        "explanation": "Independent fact-checkers and primary records refute the empirical validity of the submitted claim.",
                        "evidence_limitations": ["Evaluated against verified wire sources and institutional databases"]
                    })
                elif has_supporting and not has_refuting:
                    return self._json({
                        "verdict": "True",
                        "confidence": 0.92,
                        "severity": "Low",
                        "reasoning": "Primary filings, institutional declarations, and official reporting confirm the event.",
                        "explanation": "Corroborated by primary institutional statements and wire reporting.",
                        "evidence_limitations": ["Evaluated against verified wire sources and institutional databases"]
                    })
                else:
                    return self._json({
                        "verdict": "Unverified",
                        "confidence": 0.50,
                        "severity": "Medium",
                        "reasoning": "Insufficient definitive primary evidence available to verify or refute.",
                        "explanation": "Public reporting contains conflicting statements without official confirmation.",
                        "evidence_limitations": ["Limited primary documentation available in current scan window"]
                    })
            else:
                return self._json({
                    "verdict": "False",
                    "confidence": 0.88,
                    "severity": "High",
                    "reasoning": "Empirical evidence does not support the premise.",
                    "explanation": "No reputable sources substantiate this assertion.",
                    "evidence_limitations": ["Evaluated against indexed public web records"]
                })

        # 3. Sentiment analysis mock
        if "crisis intelligence analyst" in prompt_lower or "sentiment_score" in prompt_lower or "analyze_sentiment" in prompt_lower:
            return self._json([
                {"sentiment_score": -60, "is_threat": True, "summary": "Boycott threat detected"},
                {"sentiment_score": 10, "is_threat": False, "summary": "General consumer discussion"}
            ])

        # 4. Defense statement mock
        if "corporate defense" in prompt_lower or "pr response" in prompt_lower or "defense statement" in prompt_lower:
            return "[SYNTHETIC MOCK OUTPUT — NOT EVIDENCE] Official Corporate Statement: We take all feedback seriously. After internal review, our operations remain strictly compliant with all regulatory safety and quality standards."

        # 5. Threat detection mock
        if "threat detection" in prompt_lower or "is_threat" in prompt_lower:
            return self._json({
                "threat_detected": True,
                "threat_level": "medium",
                "recommended_action": "Issue clarification notice and monitor social channels."
            })

        # 6. Default generic structured response if prompt requests JSON
        if "json" in prompt_lower:
            return self._json({
                "status": "success",
                "summary": "Deterministic offline mock intelligence response",
                "confidence": 0.85
            })

        return "[SYNTHETIC MOCK OUTPUT — NOT EVIDENCE] Deterministic offline mock LLM response."
