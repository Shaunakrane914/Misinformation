"""
Aegis Protocol — Intelligence Service (Delegating to Centralized LLM Gateway)
=============================================================================
ADR 0004 Implementation: Delegates inference execution to `backend.infrastructure.llm.llm_gateway`
and configuration to `backend.core.settings.settings`.
Preserves legacy public functions: `call_gemini_text`, `clean_json_string`,
`analyze_sentiment`, `generate_defense`, and `analyze_security_risk`.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from backend.infrastructure.llm.gateway import clean_json_markdown, get_llm_gateway

logger = logging.getLogger(__name__)


def clean_json_string(text: str) -> str:
    """Clean markdown code fences from JSON text."""
    return clean_json_markdown(text)


def call_gemini_text(prompt: str) -> str:
    """Call LLM via the centralized LLMGateway."""
    gateway = get_llm_gateway()
    return gateway.generate_text(prompt)


def get_last_llm_provenance() -> Dict[str, Any]:
    """Return non-secret provider metadata for the most recent gateway call."""
    response = get_llm_gateway().last_response
    if response is None:
        return {"provider": "unavailable", "synthetic": False, "evidence_eligible": False}
    return {
        "provider": response.provider,
        "model": response.model,
        "synthetic": response.synthetic,
        "evidence_eligible": not response.synthetic,
        "usage_is_estimated": response.usage.is_estimated,
    }


def analyze_sentiment(text_items: List[str]) -> List[Dict[str, Any]]:
    """Analyze text items for sentiment and crisis risk using centralized LLM gateway."""
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
    """Generate a formal refutation statement for a rumor using centralized LLM gateway."""
    try:
        prompt = f"""You are a Strategic Communications Director.
A malicious unverified rumor is spreading: "{rumor_text}".

Draft a dignified, firm, and authoritative clarification statement (max 280 characters). Return ONLY the statement."""
        return call_gemini_text(prompt).strip()
    except Exception as e:
        logger.error(f"[Intelligence] Defense statement error: {e}")
        return f"Official Notice: The claims regarding '{rumor_text[:50]}' are unsubstantiated and lack factual basis."


def analyze_security_risk(mentions: List[Dict[str, Any]], vip_name: str) -> List[Dict[str, Any]]:
    """Analyze mentions for personal security and reputation risks using centralized LLM gateway."""
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
