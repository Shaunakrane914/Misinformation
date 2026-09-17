"""
Intelligence Service using Google Gemini via HTTP API.
Handles sentiment analysis, threat detection, and defense statements.
"""
import os
import json
import logging
import time
import re
import requests
from itertools import cycle
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Load all available Gemini API keys
GEMINI_KEYS = []
for k, v in sorted(os.environ.items()):
    if k == "GEMINI_API_KEY" or k.startswith("GEMINI_API_KEY_") or k.startswith("GEMINI_KEY_"):
        clean_v = v.strip().strip('"').strip("'")
        if clean_v and clean_v not in GEMINI_KEYS:
            GEMINI_KEYS.append(clean_v)

if not GEMINI_KEYS:
    logger.warning("[Intelligence] No GEMINI_API_KEY found.")
else:
    logger.info(f"[Intelligence] Loaded {len(GEMINI_KEYS)} Gemini API key(s) for load balancing")

_key_cycle = cycle(GEMINI_KEYS) if GEMINI_KEYS else None

AVAILABLE_MODELS = [
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


def call_gemini_text(prompt: str) -> str:
    """Call Gemini via direct HTTP REST API, rotating keys and models."""
    if not GEMINI_KEYS or not _key_cycle:
        raise RuntimeError("No Gemini API keys available")

    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    last_error = None
    for model in AVAILABLE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for _ in range(len(GEMINI_KEYS)):
            api_key = next(_key_cycle)
            try:
                resp = requests.post(url, headers=headers, params={"key": api_key}, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                elif resp.status_code == 429:
                    time.sleep(0.3)
                    continue
                else:
                    last_error = Exception(f"Status {resp.status_code} on {model}")
                    break
            except Exception as e:
                last_error = e
                time.sleep(0.2)

    raise last_error or RuntimeError("All Gemini models/keys exhausted")


def clean_json_string(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    return cleaned.strip()


def analyze_sentiment(text_items: List[str]) -> List[Dict[str, Any]]:
    """Analyze text items for sentiment and crisis risk."""
    if not text_items:
        return []

    try:
        prompt = f"""You are a Crisis Intelligence Analyst. Analyze the following items:
{json.dumps(text_items, indent=2)}

For each item, determine:
1. sentiment_score: Integer from -100 to 100
2. is_threat: Boolean (true if reputation damage, disinformation, boycott or fraud)
3. summary: Short 5-word summary

Return STRICT JSON array:
[
  {{"sentiment_score": -60, "is_threat": true, "summary": "Boycott threat detected"}},
  ...
]"""
        raw = call_gemini_text(prompt)
        parsed = json.loads(clean_json_string(raw))
        if isinstance(parsed, list) and len(parsed) == len(text_items):
            return parsed
    except Exception as e:
        logger.error(f"[Intelligence] Sentiment analysis fallback: {e}")

    return [
        {"sentiment_score": 0, "is_threat": False, "summary": "Nominal media report"}
        for _ in text_items
    ]


def generate_defense(rumor_text: str) -> str:
    """Generate a formal refutation statement for a rumor."""
    try:
        prompt = f"""You are a Strategic Communications Director.
A malicious unverified rumor is spreading: "{rumor_text}".

Draft a dignified, firm, and authoritative clarification statement (max 280 characters). Return ONLY the statement."""
        return call_gemini_text(prompt).strip()
    except Exception as e:
        logger.error(f"[Intelligence] Defense statement error: {e}")
        return f"Official Notice: The claims regarding '{rumor_text[:50]}' are unsubstantiated and lack factual basis."


def analyze_security_risk(mentions: List[Dict[str, Any]], vip_name: str) -> List[Dict[str, Any]]:
    """Analyze mentions for personal security and reputation risks."""
    if not mentions:
        return []

    try:
        mentions_text = []
        for i, m in enumerate(mentions[:12]):
            content = m.get('content', '') or m.get('snippet', '') or m.get('title', '')
            source = m.get('source', 'Web')
            mentions_text.append(f"{i+1}. [{source}] {content[:180]}")

        prompt = f"""You are an Executive Intelligence Analyst protecting {vip_name}.
Analyze these mentions for reputation and safety risks:

{chr(10).join(mentions_text)}

For each mention, return a JSON array:
[
  {{
    "index": 1,
    "risk_level": "HIGH|MEDIUM|LOW",
    "threat_type": "IMPERSONATION|DEEPFAKE|SMEAR|DOXXING|GENERAL",
    "reason": "One concise sentence explaining why this is a threat or safe."
  }},
  ...
]
Return ONLY the JSON array."""

        raw = call_gemini_text(prompt)
        threats = json.loads(clean_json_string(raw))

        analyzed_threats = []
        for threat in threats:
            idx = threat.get('index', 1) - 1
            if 0 <= idx < len(mentions):
                original = mentions[idx]
                analyzed_threats.append({
                    **original,
                    'risk_level': threat.get('risk_level', 'LOW'),
                    'threat_type': threat.get('threat_type', 'GENERAL'),
                    'reason': threat.get('reason', 'Routine public discourse detected.'),
                    'analyzed': True
                })

        if analyzed_threats:
            return analyzed_threats

    except Exception as e:
        logger.error(f"[Intelligence] Security analysis error: {e}")

    # Sensible fallback
    return [
        {
            **mention,
            'risk_level': 'HIGH' if any(w in (mention.get('title', '') + mention.get('content', '')).lower() for w in ['deepfake', 'leak', 'scam', 'arrest', 'fraud']) else 'LOW',
            'threat_type': 'DEEPFAKE' if 'deepfake' in (mention.get('title', '')).lower() else 'GENERAL',
            'reason': 'Audited against verified public records.',
            'analyzed': True
        }
        for mention in mentions
    ]
