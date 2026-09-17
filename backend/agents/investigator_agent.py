"""
Investigator Agent

This agent provides final verdict on claims using Google Gemini Pro for high reasoning.
Phase 2: Returns dictionary responses only (no database integration yet).
"""

import os
import json
import re
from typing import Dict
import requests
from dotenv import load_dotenv
import os as _os


import itertools
import time


class InvestigatorAgent:
    """
    Agent responsible for investigating claims and providing final verdicts.
    Uses Gemini Pro for advanced reasoning and analysis.
    """
    
    def __init__(self):
        """
        Initialize the Investigator Agent with Google Gemini configuration.
        Loads all available keys and rotates across them per request.
        """
        print("[InvestigatorAgent] Initializing Investigator Agent")
        env_path = _os.path.abspath(
            _os.path.join(_os.path.dirname(__file__), "..", "..", ".env")
        )
        print(f"[InvestigatorAgent] Loading .env from: {env_path}")
        load_dotenv(env_path, override=True)

        def _clean(s):
            if not s:
                return ""
            return s.strip().strip('"').strip("'")

        all_keys = []
        for k, v in sorted(os.environ.items()):
            if k == "GEMINI_API_KEY" or k.startswith("GEMINI_API_KEY_"):
                cleaned = _clean(v)
                if cleaned and cleaned not in all_keys:
                    all_keys.append(cleaned)
        self.api_keys = all_keys

        if not self.api_keys:
            raise ValueError(
                "[InvestigatorAgent] No API key found. Set GEMINI_API_KEY in .env"
            )

        self.available_models = [
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite-preview",
            "gemini-3.6-flash",
            "gemini-flash-latest",
            "gemini-2.0-flash-lite-preview-02-05",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ]
        self.model_name = self.available_models[0]
        self._key_cycle = itertools.cycle(self.api_keys)
        print(f"[InvestigatorAgent] Loaded {len(self.api_keys)} Gemini key(s), round-robin active.")
        print(f"[InvestigatorAgent] Using primary model: {self.model_name}")

    def _call_gemini(self, prompt: str) -> str:
        """
        Call Gemini via HTTP, rotating models and keys with retry.
        """
        print("[InvestigatorAgent] Calling Gemini via HTTP API...")
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        last_error = None
        for model in self.available_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            for attempt in range(len(self.api_keys)):
                api_key = next(self._key_cycle)
                try:
                    resp = requests.post(url, headers=headers, params={"key": api_key}, json=payload, timeout=25)
                    if resp.status_code == 200:
                        data = resp.json()
                        try:
                            return data["candidates"][0]["content"]["parts"][0]["text"]
                        except Exception:
                            return json.dumps(data)
                    elif resp.status_code == 429:
                        print(f"[InvestigatorAgent] 429 on model {model}, key ...{api_key[-6:]}. Rotating key.")
                        time.sleep(0.4)
                        last_error = Exception(f"429 on {model}")
                        continue
                    else:
                        print(f"[InvestigatorAgent] Model {model} returned status {resp.status_code}: {resp.text[:100]}")
                        last_error = Exception(f"{resp.status_code} on {model}")
                        break
                except Exception as e:
                    last_error = e
                    time.sleep(0.3)

        raise last_error or RuntimeError("[InvestigatorAgent] All Gemini models/keys exhausted")


    
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

            # Call Gemini API via HTTP
            raw_text = self._call_gemini(prompt)
            
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
