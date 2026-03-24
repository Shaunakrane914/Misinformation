"""
Research Agent

This agent is responsible for researching claims using Google Gemini API.
Phase 2: Returns dictionary responses only (no database integration yet).
"""

import os
import json
import re
from typing import Dict, List
import requests
from dotenv import load_dotenv
import os as _os


import itertools
import time


class ResearchAgent:
    """
    Agent responsible for researching claims using Google Gemini AI.
    Gathers evidence supporting and refuting claims.
    """
    
    def __init__(self):
        """
        Initialize the Research Agent with Google Gemini configuration.
        Loads all available keys and rotates across them per request.
        """
        print("[ResearchAgent] Initializing Research Agent")
        env_path = _os.path.abspath(
            _os.path.join(_os.path.dirname(__file__), "..", "..", ".env")
        )
        print(f"[ResearchAgent] Loading .env from: {env_path}")
        load_dotenv(env_path, override=True)

        def _clean(s):
            if not s:
                return ""
            return s.strip().strip('"').strip("'")

        all_keys = [
            _clean(os.getenv("GEMINI_API_KEY")),
            _clean(os.getenv("GEMINI_API_KEY_1")),
            _clean(os.getenv("GEMINI_API_KEY_2")),
        ]
        self.api_keys = [k for k in all_keys if k]

        if not self.api_keys:
            raise ValueError(
                "[ResearchAgent] No API key found. Set GEMINI_API_KEY, GEMINI_API_KEY_1, or GEMINI_API_KEY_2"
            )

        self._key_cycle = itertools.cycle(self.api_keys)
        self.model_name = "gemini-2.5-flash"
        print(f"[ResearchAgent] Loaded {len(self.api_keys)} Gemini key(s), round-robin active.")
        print(f"[ResearchAgent] Using model: {self.model_name}")

    def _call_gemini(self, prompt: str) -> str:
        """
        Call Gemini via HTTP, rotating keys and retrying on 429.
        """
        print("[ResearchAgent] Calling Gemini via HTTP API...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        last_error = None
        for attempt in range(len(self.api_keys) * 2):  # try each key twice
            api_key = next(self._key_cycle)
            try:
                resp = requests.post(url, headers=headers, params={"key": api_key}, json=payload, timeout=30)
                if resp.status_code == 429:
                    print(f"[ResearchAgent] 429 on key ...{api_key[-6:]}. Rotating key.")
                    time.sleep(0.5)
                    last_error = Exception(f"429 Too Many Requests on key ...{api_key[-6:]}")
                    continue
                resp.raise_for_status()
                data = resp.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except Exception:
                    return json.dumps(data)
            except Exception as e:
                if "429" not in str(e):
                    raise
                last_error = e
                time.sleep(0.5)

        raise last_error or RuntimeError("[ResearchAgent] All keys exhausted on 429s")



    def gather_evidence(self, claim_text: str) -> str:
        """
        Query Google Gemini to gather evidence about a claim.
        
        Args:
            claim_text (str): The claim to research
        
        Returns:
            str: Raw text response from the Gemini model
        """
        print(f"[ResearchAgent] Gathering evidence for claim: {claim_text[:50]}...")
        
        # Construct the prompt
        prompt = f"""Search and summarize evidence supporting and refuting this claim:

"{claim_text}"

Provide your response in the following JSON format:
{{
  "supporting_evidence": ["evidence point 1", "evidence point 2", ...],
  "refuting_evidence": ["evidence point 1", "evidence point 2", ...],
  "overall_evidence_confidence": 0.0
}}

The overall_evidence_confidence should be a number between 0.0 and 1.0, where:
- 1.0 = Strong evidence the claim is TRUE
- 0.5 = Neutral/unclear evidence
- 0.0 = Strong evidence the claim is FALSE

Provide at least 2-3 evidence points for each category if available."""
        
        try:
            print("[ResearchAgent] Sending request to Gemini API...")

            # Call Gemini API over HTTP
            raw_text = self._call_gemini(prompt)
            
            print(f"[ResearchAgent] Received response ({len(raw_text)} characters)")
            print(f"[ResearchAgent] Raw response preview: {raw_text[:100]}...")
            
            return raw_text
            
        except Exception as e:
            print(f"[ResearchAgent] ERROR calling Gemini API: {str(e)}")
            raise
    
    def extract_json(self, raw_text: str) -> Dict:
        """
        Parse model output into strict JSON format.
        
        This method:
        1. Removes markdown code blocks (```)
        2. Trims whitespace
        3. Parses JSON
        4. Returns safe fallback if parsing fails
        
        Args:
            raw_text (str): Raw text response from Gemini
        
        Returns:
            Dict: Parsed JSON with keys: supporting_evidence, refuting_evidence, 
                  overall_evidence_confidence
        """
        print("[ResearchAgent] Extracting JSON from raw text...")
        
        # Default fallback response
        fallback_response = {
            "supporting_evidence": [],
            "refuting_evidence": [],
            "overall_evidence_confidence": 0.5
        }
        
        try:
            # Step 1: Remove markdown code blocks
            cleaned_text = raw_text.strip()
            
            # Remove ```json and ``` markers
            cleaned_text = re.sub(r'^```json\s*', '', cleaned_text, flags=re.IGNORECASE)
            cleaned_text = re.sub(r'^```\s*', '', cleaned_text)
            cleaned_text = re.sub(r'\s*```$', '', cleaned_text)
            
            # Step 2: Trim whitespace
            cleaned_text = cleaned_text.strip()
            
            print(f"[ResearchAgent] Cleaned text preview: {cleaned_text[:100]}...")
            
            # Step 3: Parse JSON
            parsed_json = json.loads(cleaned_text)
            
            # Step 4: Validate required keys
            required_keys = ["supporting_evidence", "refuting_evidence", "overall_evidence_confidence"]
            
            for key in required_keys:
                if key not in parsed_json:
                    print(f"[ResearchAgent] WARNING: Missing required key '{key}', using fallback")
                    return fallback_response
            
            # Ensure lists are actually lists
            if not isinstance(parsed_json["supporting_evidence"], list):
                parsed_json["supporting_evidence"] = []
            
            if not isinstance(parsed_json["refuting_evidence"], list):
                parsed_json["refuting_evidence"] = []
            
            # Ensure confidence is a float between 0 and 1
            try:
                confidence = float(parsed_json["overall_evidence_confidence"])
                parsed_json["overall_evidence_confidence"] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                print("[ResearchAgent] WARNING: Invalid confidence value, using 0.5")
                parsed_json["overall_evidence_confidence"] = 0.5
            
            print("[ResearchAgent] Successfully extracted and validated JSON")
            print(f"[ResearchAgent] Supporting evidence: {len(parsed_json['supporting_evidence'])} points")
            print(f"[ResearchAgent] Refuting evidence: {len(parsed_json['refuting_evidence'])} points")
            print(f"[ResearchAgent] Confidence: {parsed_json['overall_evidence_confidence']}")
            
            return parsed_json
            
        except json.JSONDecodeError as e:
            print(f"[ResearchAgent] ERROR: JSON parsing failed: {str(e)}")
            print(f"[ResearchAgent] Problematic text: {cleaned_text[:200]}...")
            print("[ResearchAgent] Returning fallback response")
            return fallback_response
            
        except Exception as e:
            print(f"[ResearchAgent] ERROR: Unexpected error during JSON extraction: {str(e)}")
            print("[ResearchAgent] Returning fallback response")
            return fallback_response
    
    def process(self, claim_text: str) -> Dict:
        """
        Process a claim by gathering evidence and converting to JSON.
        
        This is the main method that orchestrates:
        1. Gathering evidence from Gemini
        2. Extracting and parsing JSON
        3. Returning structured response
        
        Args:
            claim_text (str): The claim to research
        
        Returns:
            Dict: Structured response with supporting_evidence, refuting_evidence, 
                  and overall_evidence_confidence
        """
        print(f"[ResearchAgent] Processing claim: {claim_text[:50]}...")
        
        try:
            # Step 1: Gather evidence from Gemini
            raw_text = self.gather_evidence(claim_text)
            
            # Step 2: Extract JSON from raw text
            result = self.extract_json(raw_text)
            
            print("[ResearchAgent] Claim processing complete")
            
            return result
            
        except Exception as e:
            print(f"[ResearchAgent] ERROR during processing: {str(e)}")
            print("[ResearchAgent] Returning fallback response")
            
            # Return safe fallback
            return {
                "supporting_evidence": [],
                "refuting_evidence": [],
                "overall_evidence_confidence": 0.5
            }

    async def generate_dashboard_explanation(self, claim_text: str, label: str) -> Dict:
        print(f"[ResearchAgent] Generating dashboard explanation for: {claim_text[:50]}...")
        fallback = {
            "explanation": "Short explanation unavailable.",
            "evidence_url": ""
        }
        try:
            prompt = f"""You are assisting a dashboard that displays claims and their labels.

CLAIM:
"{claim_text}"

LABEL:
"{label}"

CONTEXT:
The dataset already provides the correct verdict.
Your task: produce a short explanation + 1 evidence link supporting the label.

REQUIREMENTS:
- 75–100 word explanation
- Provide one credible evidence URL
- Return STRICT JSON only:
{{
  "explanation": "<75–100 words>",
  "evidence_url": "https://<one credible source>"
}}
"""
            raw_text = self._call_gemini(prompt)
            cleaned = raw_text.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'^```\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()
            result = json.loads(cleaned)
            if "explanation" not in result or "evidence_url" not in result:
                return fallback
            if not isinstance(result["explanation"], str):
                result["explanation"] = str(result["explanation"])[:1000]
            if not isinstance(result["evidence_url"], str):
                result["evidence_url"] = str(result["evidence_url"])[:500]
            print("[ResearchAgent] Dashboard explanation generated")
            return {
                "explanation": result.get("explanation", fallback["explanation"]),
                "evidence_url": result.get("evidence_url", fallback["evidence_url"]) 
            }
        except json.JSONDecodeError as e:
            print(f"[ResearchAgent] ERROR: JSON parsing failed: {str(e)}")
            return fallback
        except Exception as e:
            print(f"[ResearchAgent] ERROR generating dashboard explanation: {str(e)}")
            return fallback
