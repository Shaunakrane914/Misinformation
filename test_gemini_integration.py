"""
Test script for Phase 2: Gemini Integration.
Verifies that the Trending Agent correctly enriches news with sentiment analysis.
"""
import os
import json
import logging
from dotenv import load_dotenv
from backend.agents.trending_agent import TrendingAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env
load_dotenv()

def test_gemini_enrichment():
    print("="*60)
    print("TEST: Gemini Sentiment Analysis Integration")
    print("="*60)

    # Check API Key
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env")
        return

    print(f"✅ Found GEMINI_API_KEY: {key[:10]}...")

    # Initialize Agent
    agent = TrendingAgent()
    
    # Run Scan (News only to be fast)
    asset = "Shah Rukh Khan"
    print(f"\nScanning for: {asset}...")
    
    # We pass empty identifiers to skip the slow Instagram scrape for this test
    result = agent.scan(asset_name=asset, identifiers={})
    
    news_items = result["sources"]["news"]
    print(f"\nFound {len(news_items)} news items.")

    if not news_items:
        print("⚠️ No news found. Cannot verify sentiment.")
        return

    # Verify Enrichment
    print("\nVerifying Enrichment:")
    all_good = True
    
    for i, item in enumerate(news_items):
        title = item.get("title", "No Title")
        sentiment = item.get("sentiment_score")
        is_threat = item.get("is_threat")
        summary = item.get("summary")
        
        print(f"\n[{i+1}] {title[:60]}...")
        print(f"    Sentiment: {sentiment}")
        print(f"    Threat: {is_threat}")
        print(f"    Summary: {summary}")
        
        if sentiment is None or is_threat is None:
            all_good = False
            print("    ❌ MISSING ANALYSIS FIELDS")
        else:
            print("    ✅ Analysis Present")

    print("="*60)
    if all_good:
        print("✅ SUCCESS: Gemini integration is working!")
    else:
        print("❌ FAILURE: Some items were not enriched.")

if __name__ == "__main__":
    test_gemini_enrichment()
