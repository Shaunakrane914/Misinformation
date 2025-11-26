"""
Investigator Agent

This agent provides final verdict on claims using Google Gemini Pro for high reasoning.
Phase 2: Returns dictionary responses only (no database integration yet).
"""

import os
import json
import re
from typing import Dict
from google import genai
from google.genai import types as genai_types


class InvestigatorAgent:
    """
    Agent responsible for investigating claims and providing final verdicts.
    Uses Gemini Pro for advanced reasoning and analysis.
    """
    
    def __init__(self):
        """
        Initialize the Investigator Agent with Google Gemini Pro configuration.
        
        Uses API key priority:
        1. GEMINI_API_KEY_2 (primary)
        2. GEMINI_API_KEY (fallback)
        """
        print("[InvestigatorAgent] Initializing Investigator Agent")
        
        # Key priority: GEMINI_API_KEY_2 first, then GEMINI_API_KEY
        api_key = os.getenv("GEMINI_API_KEY_2") or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "[InvestigatorAgent] No API key found. Set GEMINI_API_KEY_2 or GEMINI_API_KEY"
            )
        
        print(f"[InvestigatorAgent] Using API key: {api_key[:10]}...")
        
        # Configure Gemini client with flash-lite model
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.0-flash-lite"
        
        print(f"[InvestigatorAgent] Configured with model: {self.model_name}")
        print("[InvestigatorAgent] Initialization complete")
    
    def _clean_json(self, text: str) -> str:
        """
        Clean JSON text by removing markdown code block wrappers.
        
        Removes:
        - ```json and ```
        - Leading/trailing whitespace
        
        Args:
            text (str): Raw text potentially containing markdown wrappers
        
        Returns:
            str: Cleaned and trimmed JSON text
        """
        print("[InvestigatorAgent] Cleaning JSON text...")
        
        # Remove ```json and ``` markers
        cleaned = text.strip()
        cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        
        # Trim whitespace
        cleaned = cleaned.strip()
        
        print(f"[InvestigatorAgent] Cleaned text preview: {cleaned[:100]}...")
        
        return cleaned
    
    def investigate(self, claim_text: str, evidence_json: Dict) -> Dict:
        """
        Investigate a claim and provide a final verdict based on evidence.
        
        Uses Gemini Pro to analyze the claim and evidence, producing:
        - verdict: True | False | Misleading | Unverified
        - confidence: 0.0-1.0
        - reasoning: short explanation
        - severity: Low | Medium | High
        
        Args:
            claim_text (str): The claim to investigate
            evidence_json (Dict): Evidence gathered from ResearchAgent with keys:
                                  supporting_evidence, refuting_evidence, 
                                  overall_evidence_confidence
        
        Returns:
            Dict: Final verdict with verdict, confidence, reasoning, and severity
        """
        print(f"[InvestigatorAgent] Investigating claim: {claim_text[:50]}...")
        print(f"[InvestigatorAgent] Evidence summary:")
        print(f"  - Supporting points: {len(evidence_json.get('supporting_evidence', []))}")
        print(f"  - Refuting points: {len(evidence_json.get('refuting_evidence', []))}")
        print(f"  - Evidence confidence: {evidence_json.get('overall_evidence_confidence', 'N/A')}")
        
        # Fallback response for any failures
        fallback_response = {
            "verdict": "Unverified",
            "confidence": 0.5,
            "reasoning": "Unable to determine verdict due to insufficient or unclear evidence.",
            "severity": "Medium"
        }
        
        try:
            # Construct the prompt for high-reasoning analysis
            prompt = f"""You are an expert fact-checker. Analyze the following claim and evidence, then provide a final verdict.

CLAIM:
"{claim_text}"

EVIDENCE GATHERED:

Supporting Evidence:
{json.dumps(evidence_json.get('supporting_evidence', []), indent=2)}

Refuting Evidence:
{json.dumps(evidence_json.get('refuting_evidence', []), indent=2)}

Overall Evidence Confidence: {evidence_json.get('overall_evidence_confidence', 0.5)}

TASK:
Provide your verdict in STRICT JSON format only (no additional text):

{{
  "verdict": "True | False | Misleading | Unverified",
  "confidence": <number between 0.0 and 1.0>,
  "reasoning": "<one short sentence explaining your verdict>",
  "severity": "Low | Medium | High"
}}

GUIDELINES:
- verdict = "True" if claim is factually accurate
- verdict = "False" if claim is factually incorrect
- verdict = "Misleading" if claim contains some truth but misrepresents context
- verdict = "Unverified" if insufficient evidence to determine
- confidence = how certain you are (0.0 = not certain, 1.0 = very certain)
- severity = potential harm if claim is false/misleading (Low/Medium/High)
- reasoning = brief explanation in one sentence

Return ONLY the JSON object, nothing else."""
            
            print("[InvestigatorAgent] Sending investigation request to Gemini...")
            
            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            # Extract raw text
            raw_text = response.text
            
            print(f"[InvestigatorAgent] Received response ({len(raw_text)} characters)")
            print(f"[InvestigatorAgent] Raw response preview: {raw_text[:150]}...")
            
            # Clean JSON
            cleaned_text = self._clean_json(raw_text)
            
            # Parse JSON
            verdict_json = json.loads(cleaned_text)
            
            # Validate required keys
            required_keys = ["verdict", "confidence", "reasoning", "severity"]
            for key in required_keys:
                if key not in verdict_json:
                    print(f"[InvestigatorAgent] WARNING: Missing required key '{key}'")
                    print("[InvestigatorAgent] Returning fallback response")
                    return fallback_response
            
            # Validate verdict value
            valid_verdicts = ["True", "False", "Misleading", "Unverified"]
            if verdict_json["verdict"] not in valid_verdicts:
                print(f"[InvestigatorAgent] WARNING: Invalid verdict '{verdict_json['verdict']}'")
                verdict_json["verdict"] = "Unverified"
            
            # Validate and clamp confidence
            try:
                confidence = float(verdict_json["confidence"])
                verdict_json["confidence"] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                print("[InvestigatorAgent] WARNING: Invalid confidence value, using 0.5")
                verdict_json["confidence"] = 0.5
            
            # Validate severity
            valid_severities = ["Low", "Medium", "High"]
            if verdict_json["severity"] not in valid_severities:
                print(f"[InvestigatorAgent] WARNING: Invalid severity '{verdict_json['severity']}'")
                verdict_json["severity"] = "Medium"
            
            # Ensure reasoning is a string
            if not isinstance(verdict_json["reasoning"], str):
                verdict_json["reasoning"] = str(verdict_json["reasoning"])
            
            print("[InvestigatorAgent] Investigation complete")
            print(f"[InvestigatorAgent] Verdict: {verdict_json['verdict']}")
            print(f"[InvestigatorAgent] Confidence: {verdict_json['confidence']}")
            print(f"[InvestigatorAgent] Severity: {verdict_json['severity']}")
            print(f"[InvestigatorAgent] Reasoning: {verdict_json['reasoning'][:80]}...")
            
            return verdict_json
            
        except json.JSONDecodeError as e:
            print(f"[InvestigatorAgent] ERROR: JSON parsing failed: {str(e)}")
            print(f"[InvestigatorAgent] Problematic text: {cleaned_text[:200]}...")
            print("[InvestigatorAgent] Returning fallback response")
            return fallback_response
            
        except Exception as e:
            print(f"[InvestigatorAgent] ERROR during investigation: {str(e)}")
            print("[InvestigatorAgent] Returning fallback response")
            return fallback_response
    
    def process(self, claim_text: str, evidence_json: Dict) -> Dict:
        """
        Process a claim investigation.
        
        This is the main method that orchestrates the investigation workflow.
        
        Args:
            claim_text (str): The claim to investigate
            evidence_json (Dict): Evidence from ResearchAgent
        
        Returns:
            Dict: Final verdict with verdict, confidence, reasoning, and severity
        """
        print(f"[InvestigatorAgent] Processing investigation for: {claim_text[:50]}...")
        
        # Call investigate to get the final verdict
        result = self.investigate(claim_text, evidence_json)
        
        print("[InvestigatorAgent] Investigation processing complete")
        
        return result
