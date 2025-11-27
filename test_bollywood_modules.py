"""
Test script for Phase 3: Bollywood Modules.
Verifies Box Office scraping and Fan War monitoring.
"""
import os
import logging
from dotenv import load_dotenv
from backend.agents.trending_agent import TrendingAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env
load_dotenv()

def test_bollywood_modules():
    print("="*60)
    print("TEST: Bollywood Modules (Box Office & Fan Wars)")
    print("="*60)

    agent = TrendingAgent()
    
    # 1. Test Box Office
    movie = "Jawan"
    print(f"\n1. Testing Box Office for '{movie}'...")
    bo_data = agent.fetch_box_office(movie)
    print(f"   Result: {bo_data}")
    
    if bo_data.get("source") == "Sacnilk":
        print("   ✅ Box Office scraper structure is correct.")
    else:
        print("   ❌ Box Office scraper failed or returned unexpected structure.")

    # 2. Test Fan Wars (Twitter)
    hashtag = "#BoycottBollywood"
    print(f"\n2. Testing Fan Wars for '{hashtag}'...")
    
    if not os.getenv("APIFY_TOKEN"):
        print("   ⚠️ Skipping Twitter test (No APIFY_TOKEN)")
    else:
        tweets = agent.fetch_fan_wars(hashtag)
        print(f"   Found {len(tweets)} tweets.")
        if tweets:
            print(f"   Sample: {tweets[0].get('text')[:50]}...")
            print("   ✅ Fan War scraper working.")
        else:
            print("   ⚠️ No tweets found (could be rate limit or empty result).")

    # 3. Test Full Scan Integration
    print("\n3. Testing Full Scan Integration...")
    scan_result = agent.scan(
        asset_name="Pathaan",
        identifiers={
            "box_office": True,
            "hashtag": "#Pathaan"
        }
    )
    
    sources = scan_result.get("sources", {})
    print(f"   Box Office Data Present: {bool(sources.get('box_office'))}")
    print(f"   Fan Wars Data Present: {bool(sources.get('fan_wars'))}")
    
    if sources.get("box_office") and "fan_wars" in sources:
        print("   ✅ Scan integration successful.")
    else:
        print("   ❌ Scan integration missing keys.")

if __name__ == "__main__":
    test_bollywood_modules()
