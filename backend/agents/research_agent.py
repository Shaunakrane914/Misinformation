"""
Research Agent

This agent is responsible for researching claims using Google Gemini API.
Phase 2: Returns dictionary responses only (no database integration yet).
"""

import os
import json
import re
from typing import Dict, List, Optional, Any
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

        all_keys = []
        for k, v in sorted(os.environ.items()):
            if k == "GEMINI_API_KEY" or k.startswith("GEMINI_API_KEY_"):
                cleaned = _clean(v)
                if cleaned and cleaned not in all_keys:
                    all_keys.append(cleaned)
        self.api_keys = all_keys

        if not self.api_keys:
            raise ValueError(
                "[ResearchAgent] No API key found. Set GEMINI_API_KEY in .env"
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
        print(f"[ResearchAgent] Loaded {len(self.api_keys)} Gemini key(s), round-robin active.")
        print(f"[ResearchAgent] Using primary model: {self.model_name}")

    def _call_gemini(self, prompt: str) -> str:
        """
        Call Gemini via HTTP, rotating models and keys with retry.
        """
        print("[ResearchAgent] Calling Gemini via HTTP API...")
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
                        print(f"[ResearchAgent] 429 on model {model}, key ...{api_key[-6:]}. Rotating key.")
                        time.sleep(0.4)
                        last_error = Exception(f"429 on {model}")
                        continue
                    else:
                        print(f"[ResearchAgent] Model {model} returned status {resp.status_code}: {resp.text[:100]}")
                        last_error = Exception(f"{resp.status_code} on {model}")
                        break
                except Exception as e:
                    last_error = e
                    time.sleep(0.3)

        raise last_error or RuntimeError("[ResearchAgent] All Gemini models/keys exhausted")



    def gather_evidence(self, claim_text: str, source_url: Optional[str] = None) -> str:
        """
        Query Google Gemini to gather evidence about a claim, augmented with AgentReach live intelligence.
        """
        print(f"[ResearchAgent] Gathering evidence for claim: {claim_text[:50]}...")
        
        # Pull real-time web & social context via AgentReach
        context_snippets = []
        try:
            from backend.services.agent_reach_scraper import reach_scraper
            
            # If source URL provided, parse clean markdown
            if source_url:
                doc = reach_scraper.read_article_markdown(source_url, max_chars=2000)
                if doc.get("markdown"):
                    context_snippets.append(f"SOURCE ARTICLE CONTENT ({source_url}):\n{doc['markdown'][:1500]}")

            # Pull live news & social mentions
            news_items = reach_scraper.search_news(claim_text, limit=4)
            for item in news_items:
                context_snippets.append(f"- [{item.get('source', 'News')}] {item.get('title', '')}")
                
            reddit_items = reach_scraper.search_reddit(claim_text, limit=3)
            for r in reddit_items:
                context_snippets.append(f"- [Reddit Community] {r.get('title', '')}")
        except Exception as reach_err:
            print(f"[ResearchAgent] AgentReach grounding notice: {reach_err}")

        grounding_block = ""
        if context_snippets:
            grounding_block = f"\nREAL-TIME GROUNDING INTELLIGENCE:\n" + "\n".join(context_snippets) + "\n"

        # Construct the prompt
        prompt = f"""Search and summarize evidence supporting and refuting this claim:

"{claim_text}"
{grounding_block}
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
            raw_text = self._call_gemini(prompt)
            print(f"[ResearchAgent] Received response ({len(raw_text)} characters)")
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
    
    def process(self, claim_text: str, source_url: Optional[str] = None) -> Dict:
        """
        Process a claim by gathering evidence and returning structured results.
        """
        print(f"[ResearchAgent] Processing claim: {claim_text[:50]}...")
        
        try:
            # Step 1: Gather evidence from Gemini with AgentReach live intelligence
            raw_text = self.gather_evidence(claim_text, source_url=source_url)
            
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
            prompt = (
                "You are assisting a dashboard that displays claims and their labels.\n\n"
                f'CLAIM:\n"{claim_text}"\n\n'
                f'LABEL:\n"{label}"\n\n'
                "CONTEXT:\n"
                "The dataset already provides the correct verdict.\n"
                "Your task: produce a short explanation + 1 evidence link supporting the label.\n\n"
                "REQUIREMENTS:\n"
                "- 75-100 word explanation\n"
                "- Provide one credible evidence URL\n"
                "- Return STRICT JSON only:\n"
                "{\n"
                '  "explanation": "<75-100 words>",\n'
                '  "evidence_url": "https://<one credible source>"\n'
                "}\n"
            )
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
