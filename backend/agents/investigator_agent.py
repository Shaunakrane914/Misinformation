"""
Aegis Protocol — Investigator Agent (Verdict Synthesis & Fact-Checking)
======================================================================
Synthesizes evidence gathered across intelligence feeds and renders structured,
source-grounded verdicts matching the canonical 6-verdict taxonomy:
- True
- False
- Misleading
- Partially True
- Unverified
- Insufficient Evidence
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from backend.schemas.claim_schemas import SeverityLevel, VerdictType
from backend.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


class InvestigatorAgent:
    """
    Forensic investigator agent responsible for analyzing cross-platform evidence,
    resolving conflicting claims, and generating transparent, auditable verdicts.
    """

    def __init__(self):
        logger.info("[InvestigatorAgent] Initialized with 6-verdict taxonomy and centralized GeminiService")

    def _call_gemini(self, prompt: str) -> str:
        """Compatibility wrapper routing through centralized GeminiService."""
        return gemini_service.generate_text(prompt)

    def determine_verdict(self, claim_text: str, evidence_json: Dict[str, Any]) -> str:
        """
        Synthesize final verdict using evidence context with strict JSON instructions.
        """
        sup = evidence_json.get("supporting_evidence", [])
        ref = evidence_json.get("refuting_evidence", [])
        conf = evidence_json.get("overall_evidence_confidence", 0.5)

        # Handle explicit insufficient evidence edge case
        if not sup and not ref:
            return json.dumps({
                "verdict": "Insufficient Evidence",
                "confidence": 0.20,
                "severity": "Low",
                "reasoning": "No verifiable supporting or refuting empirical evidence was discovered across monitored channels.",
                "explanation": "Monitored news wires, scientific archives, and community fact-checking databases did not contain sufficient verifiable records to substantiate or refute this claim.",
                "evidence_limitations": ["No primary documentation available", "Indexed sources yielded zero corroborating records"]
            })

        prompt = f"""You are a principal forensic misinformation fact-checking investigator.
Analyze the following claim and structured evidence to determine a definitive truth verdict.

CLAIM:
"{claim_text}"

GATHERED SUPPORTING EVIDENCE:
{json.dumps(sup, indent=2)}

GATHERED REFUTING EVIDENCE:
{json.dumps(ref, indent=2)}

EVIDENCE RETRIEVAL CONFIDENCE SCORE: {conf}

TAXONOMY:
- "True": Fully substantiated by reliable empirical sources and scientific consensus.
- "False": Conclusively contradicted by primary records, official data, or empirical consensus.
- "Misleading": Contains factual fragments but reaches deceptive or false conclusions.
- "Partially True": Core statement is partially accurate, but omits essential context.
- "Unverified": Contradictory evidence exists without definitive resolution.
- "Insufficient Evidence": Lack of credible verifiable sources to make a determination.

TASK:
Respond in STRICT JSON matching this schema:
{{
  "verdict": "True" | "False" | "Misleading" | "Partially True" | "Unverified" | "Insufficient Evidence",
  "confidence": 0.0 to 1.0,
  "severity": "Low" | "Medium" | "High" | "Critical",
  "reasoning": "One concise sentence summarizing the core finding.",
  "explanation": "Detailed multi-sentence explanation breaking down the evidence.",
  "evidence_limitations": ["Any limitation 1", "Any limitation 2"]
}}"""

        return gemini_service.generate_text(prompt)

    def extract_verdict(self, raw_text: str) -> Dict[str, Any]:
        """Parse raw model output into validated verdict dictionary."""
        fallback = {
            "verdict": "Unverified",
            "confidence": 0.50,
            "severity": "Medium",
            "reasoning": "Unable to definitively verify claim due to conflicting or ambiguous evidence.",
            "explanation": "The available intelligence streams do not provide unambiguous corroboration.",
            "evidence_limitations": ["Automated verdict synthesis fallback engaged"]
        }

        if not raw_text:
            return fallback

        try:
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            data = json.loads(cleaned)
            verdict_str = str(data.get("verdict", "Unverified")).strip()

            # Map common variations to canonical taxonomy
            valid_verdicts = {v.value.lower(): v.value for v in VerdictType}
            canonical_v = valid_verdicts.get(verdict_str.lower(), "Unverified")

            confidence_val = float(data.get("confidence", 0.50))
            confidence_val = max(0.0, min(1.0, confidence_val))

            severity_str = str(data.get("severity", "Medium")).capitalize()
            if severity_str not in [s.value for s in SeverityLevel]:
                severity_str = "Medium"

            return {
                "verdict": canonical_v,
                "confidence": confidence_val,
                "severity": severity_str,
                "reasoning": str(data.get("reasoning", "Evidence review complete.")),
                "explanation": str(data.get("explanation", data.get("reasoning", ""))),
                "evidence_limitations": data.get("evidence_limitations", [])
            }
        except Exception as e:
            logger.warning(f"[InvestigatorAgent] Verdict extraction failed: {e}")
            return fallback

    def process(self, claim_text: str, evidence_json: Dict[str, Any]) -> Dict[str, Any]:
        """Full pipeline execution for investigator agent."""
        raw_text = self.determine_verdict(claim_text, evidence_json)
        return self.extract_verdict(raw_text)

    def investigate(self, claim_text: str, evidence_list: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Convenience evaluation method for batch/eval benchmarks."""
        evidence_json = {
            "supporting_evidence": [e for e in (evidence_list or []) if getattr(e, "evidence_type", "") == "supporting"],
            "refuting_evidence": [e for e in (evidence_list or []) if getattr(e, "evidence_type", "") == "refuting"],
            "overall_evidence_confidence": 0.5
        }
        res = self.process(claim_text, evidence_json)
        # Add confidence_score alias
        res["confidence_score"] = res.get("confidence", 0.5)
        return res


_investigator_singleton: Optional[InvestigatorAgent] = None


def get_investigator_agent() -> InvestigatorAgent:
    """Return singleton instance of InvestigatorAgent."""
    global _investigator_singleton
    if _investigator_singleton is None:
        _investigator_singleton = InvestigatorAgent()
    return _investigator_singleton
