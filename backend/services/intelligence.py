"""
Intelligence Service using Google Gemini.
Handles sentiment analysis and threat detection for the Trending Agent.
"""
import os
import json
import logging
import time
import google.generativeai as genai
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Load all available Gemini API keys
GEMINI_KEYS = []
for i in range(1, 4):  # Check for GEMINI_API_KEY, GEMINI_API_KEY_1, GEMINI_API_KEY_2
    key_name = f"GEMINI_API_KEY_{i}" if i > 1 else "GEMINI_API_KEY"
    key = os.getenv(key_name)
    if key:
        GEMINI_KEYS.append(key)
        logger.info(f"Loaded {key_name}")

if not GEMINI_KEYS:
    logger.warning("No GEMINI_API_KEY found. Intelligence service will return mock data.")
else:
    logger.info(f"Loaded {len(GEMINI_KEYS)} Gemini API keys for load balancing")

# Round-robin counter for key rotation
_key_index = 0

def get_next_api_key():
    """Get the next API key in round-robin fashion."""
    global _key_index
    if not GEMINI_KEYS:
        return None
    key = GEMINI_KEYS[_key_index]
    _key_index = (_key_index + 1) % len(GEMINI_KEYS)
    return key

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def analyze_sentiment(text_items: List[str]) -> List[Dict[str, Any]]:
    """
    Analyze a list of text items (headlines, captions) using Gemini Flash.
    Returns a list of analysis results matching the input order.
    Uses round-robin across available API keys for load balancing.
    """
    if not text_items:
        return []

    if not GEMINI_KEYS:
        logger.warning("Skipping Gemini analysis (no keys). Returning neutral mocks.")
        return [
            {"sentiment_score": 0, "is_threat": False, "summary": "Analysis skipped (no key)"}
            for _ in text_items
        ]

    for attempt in range(MAX_RETRIES):
        try:
            # Get next API key in rotation
            api_key = get_next_api_key()
            genai.configure(api_key=api_key)
            logger.info(f"Using API key #{(_key_index % len(GEMINI_KEYS)) + 1} for sentiment analysis")
            
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Construct a batch prompt
            prompt = """
            You are a Bollywood Crisis Manager. Analyze the following social media posts/headlines.
            For each item, determine:
            1. sentiment_score: Integer from -100 (Extremely Negative/Hateful) to 100 (Extremely Positive).
            2. is_threat: Boolean. True if it's a PR crisis, fake news, boycott call, or reputation damage. False if it's just news or gossip.
            3. summary: A very short 5-word summary of the sentiment.

            Input Items:
            {items}

            Return ONLY a raw JSON list of objects, one for each input item, in the exact same order.
            Format:
            [
                {{"sentiment_score": -80, "is_threat": true, "summary": "Boycott campaign detected"}},
                ...
            ]
            """.format(items=json.dumps(text_items))

            response = model.generate_content(prompt)
            
            # Clean up response text to ensure valid JSON
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            analysis_results = json.loads(response_text)
            
            # Validate length
            if len(analysis_results) != len(text_items):
                logger.warning(f"Gemini returned {len(analysis_results)} items, expected {len(text_items)}")
                if len(analysis_results) < len(text_items):
                    analysis_results.extend([{"sentiment_score": 0, "is_threat": False, "summary": "Incomplete analysis"}] * (len(text_items) - len(analysis_results)))
                else:
                    analysis_results = analysis_results[:len(text_items)]

            logger.info(f"Successfully analyzed {len(text_items)} items")
            return analysis_results

        except json.JSONDecodeError as json_error:
            logger.error(f"Failed to parse Gemini response as JSON (attempt {attempt + 1}/{MAX_RETRIES}): {json_error}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                continue
                
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "rate limit" in error_msg:
                logger.error(f"Gemini API rate limit hit (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1) * 2)  # Longer backoff for rate limits
                    continue
            else:
                logger.error(f"Gemini analysis failed (attempt {attempt + 1}/{MAX_RETRIES}): {type(e).__name__} - {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
    
    # All retries exhausted
    logger.error(f"Gemini analysis failed after {MAX_RETRIES} attempts")
    return [
        {"sentiment_score": 0, "is_threat": False, "summary": "Analysis failed"}
        for _ in text_items
    ]

def generate_defense(rumor_text: str) -> str:
    """
    Generate a pre-bunking or denial statement for a rumor.
    Uses round-robin across available API keys.
    """
    if not GEMINI_KEYS:
        return "Gemini API Key missing. Cannot generate defense."

    try:
        # Get next API key in rotation
        api_key = get_next_api_key()
        genai.configure(api_key=api_key)
        logger.info(f"Using API key #{(_key_index % len(GEMINI_KEYS)) + 1} for defense generation")
        
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        prompt = f"""
        You are a PR Crisis Manager for a top Bollywood Star. 
        A malicious rumor is spreading: "{rumor_text}". 
        
        Draft a dignified, legal-sounding, yet firm denial tweet (max 280 chars). 
        Do not sound defensive. Sound authoritative.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Defense generation failed: {e}")
        return "Error generating defense statement."
