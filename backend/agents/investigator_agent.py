"""
Aegis Protocol — Investigator Agent (Verdict Synthesis & Forensic Chain)
========================================================================
Synthesizes cross-platform evidence and deep research findings into structured,
source-grounded forensic verdicts and auditable evidence chains matching:
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
from backend.services.research import ConfidenceLevel

logger = logging.getLogger(__name__)


class InvestigatorAgent:
    """
    Forensic investigator agent responsible for analyzing cross-platform evidence,
    resolving conflicting claims, calibrating confidence levels, and constructing
    transparent evidence chains: Finding -> Primary Evidence -> Corroboration -> Contradictions.
    """

    def __init__(self):
        logger.info("[InvestigatorAgent] Initialized with calibrated forensic evidence chains and centralized GeminiService")

    def _call_gemini(self, prompt: str) -> str:
        """Compatibility wrapper routing through centralized GeminiService."""
        return gemini_service.generate_text(prompt)

    def determine_verdict(self, claim_text: str, evidence_json: Dict[str, Any]) -> str:
        """
        Synthesize final verdict using evidence context, primary documentation,
        independent corroboration, and explicit contradiction checks.
        """
        sup = evidence_json.get("supporting_evidence", [])
        ref = evidence_json.get("refuting_evidence", [])
        primary_ev = evidence_json.get("primary_evidence", [])
        disagrees = evidence_json.get("what_disagrees", [])
        unknowns = evidence_json.get("what_is_unknown", [])
        contradictions = evidence_json.get("contradictions", [])

        # Handle explicit insufficient evidence edge case
        if not sup and not ref and not primary_ev:
            return json.dumps({
                "verdict": "Insufficient Evidence",
                "confidence": 0.20,
                "confidence_level": ConfidenceLevel.INSUFFICIENT.value,
                "severity": "Low",
                "reasoning": "No verifiable supporting or refuting empirical evidence was discovered across monitored channels.",
                "explanation": "Monitored news wires, corporate registries, and primary archives did not contain verifiable records to substantiate or refute this claim.",
                "evidence_limitations": ["No primary documentation available", "Indexed sources yielded zero corroborating records"],
                "evidence_chain": {
                    "what_happened": "Unsubstantiated assertion",
                    "who_says": [],
                    "primary_evidence": [],
                    "independent_corroboration": [],
                    "contradicting_evidence": [],
                    "what_remains_unresolved": ["Entire claim lacks empirical documentation"]
                }
            })

        prompt = f"""You are a principal forensic misinformation fact-checking investigator.
Analyze the following claim and structured evidence to determine a definitive truth verdict and construct an evidence chain.

CLAIM:
"{claim_text}"

PRIMARY DOCUMENTATION / OFFICIAL EVIDENCE:
{json.dumps(primary_ev, indent=2)}

GATHERED SUPPORTING EVIDENCE:
{json.dumps(sup, indent=2)}

GATHERED REFUTING EVIDENCE:
{json.dumps(ref, indent=2)}

CONTRADICTIONS & DISAGREEMENTS:
{json.dumps(disagrees or contradictions, indent=2)}

UNRESOLVED GAPS:
{json.dumps(unknowns, indent=2)}

TAXONOMY:
- "True": Fully substantiated by reliable empirical sources, primary documents, or scientific consensus.
- "False": Conclusively contradicted by primary records, official data, or empirical consensus.
- "Misleading": Contains factual fragments but reaches deceptive or false conclusions.
- "Partially True": Core statement is partially accurate, but omits essential context.
- "Unverified": Contradictory evidence exists without definitive resolution.
- "Insufficient Evidence": Lack of credible verifiable sources to make a determination.

CONFIDENCE CALIBRATION:
- "HIGH": Substantiated by verified primary documents or multiple independent source families.
- "MEDIUM": Supported by reliable secondary reporting without unresolvable contradiction.
- "LOW": Relying on single unconfirmed reports, commentary, or conflicting signals.
- "INSUFFICIENT": Lacks verifiable empirical foundation.

TASK:
Respond in STRICT JSON matching this schema:
{{
  "verdict": "True" | "False" | "Misleading" | "Partially True" | "Unverified" | "Insufficient Evidence",
  "confidence": 0.0 to 1.0,
  "confidence_level": "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT",
  "severity": "Low" | "Medium" | "High" | "Critical",
  "reasoning": "One concise sentence summarizing the core finding.",
  "explanation": "Detailed multi-sentence explanation breaking down the evidence and why this verdict was reached.",
  "evidence_limitations": ["Limitation 1", "Limitation 2"],
  "evidence_chain": {{
    "what_happened": "Summary of actual observed event or lack thereof",
    "primary_evidence": ["List of official filings, statements, or primary records"],
    "independent_corroboration": ["Summary of independent source groups confirming"],
    "contradicting_evidence": ["Summary of disputes, denials, or conflicting attribution"],
    "what_remains_unresolved": ["Specific missing records or open questions"]
  }}
}}"""

        return gemini_service.generate_text(prompt)

    def extract_verdict(self, raw_text: str) -> Dict[str, Any]:
        """Parse raw model output into validated verdict dictionary."""
        fallback = {
            "verdict": "Unverified",
            "confidence": 0.50,
            "confidence_level": ConfidenceLevel.LOW.value,
            "severity": "Medium",
            "reasoning": "Unable to definitively verify claim due to conflicting or ambiguous evidence.",
            "explanation": "The available intelligence streams do not provide unambiguous corroboration.",
            "evidence_limitations": ["Automated verdict synthesis fallback engaged"],
            "evidence_chain": {
                "what_happened": "Ambiguous signal",
                "primary_evidence": [],
                "independent_corroboration": [],
                "contradicting_evidence": [],
                "what_remains_unresolved": ["Verification inconclusive"]
            }
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

            conf_level = str(data.get("confidence_level", "MEDIUM")).upper()
            if conf_level not in [c.value for c in ConfidenceLevel]:
                conf_level = "HIGH" if confidence_val >= 0.80 else ("MEDIUM" if confidence_val >= 0.50 else "LOW")

            return {
                "verdict": canonical_v,
                "confidence": confidence_val,
                "confidence_score": confidence_val,
                "confidence_level": conf_level,
                "severity": severity_str,
                "reasoning": str(data.get("reasoning", "Evidence review complete.")),
                "explanation": str(data.get("explanation", data.get("reasoning", ""))),
                "evidence_limitations": data.get("evidence_limitations", []),
                "evidence_chain": data.get("evidence_chain", fallback["evidence_chain"])
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
        if isinstance(evidence_list, dict):
            evidence_json = evidence_list
        else:
            evidence_json = {
                "supporting_evidence": [e for e in (evidence_list or []) if getattr(e, "evidence_type", "") == "supporting"],
                "refuting_evidence": [e for e in (evidence_list or []) if getattr(e, "evidence_type", "") == "refuting"],
                "overall_evidence_confidence": 0.5
            }
        return self.process(claim_text, evidence_json)


_investigator_singleton: Optional[InvestigatorAgent] = None


def get_investigator_agent() -> InvestigatorAgent:
    """Return singleton instance of InvestigatorAgent."""
    global _investigator_singleton
    if _investigator_singleton is None:
        _investigator_singleton = InvestigatorAgent()
    return _investigator_singleton
