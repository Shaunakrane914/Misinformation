"""Simple Apify test to see exact error"""
import os
import sys
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

token = os.getenv("APIFY_TOKEN")
print(f"Token loaded: {bool(token)}")

if not token:
    print("ERROR: No APIFY_TOKEN found!")
    sys.exit(1)

client = ApifyClient(token)
print("Client created successfully")

# Test the exact actor call
try:
    print("\n=== Testing Instagram scraper ===")
    actor = client.actor("apidojo/instagram-scraper")
    print(f"Actor found: {actor}")
    
    run = actor.call(
        run_input={
            "startUrls": [{"url": "https://www.instagram.com/viralbhayani/"}],
            "resultsType": "posts",
            "resultsLimit": 15,
        }
    )
    print(f"\nRun started: {run.get('id')}")
    print(f"Status: {run.get('status')}")
    
    # Get results
    dataset = client.dataset(run["defaultDatasetId"])
    items = dataset.list_items().get("items", [])
    
    print(f"\n✅ SUCCESS! Got {len(items)} items")
    if items:
        print(f"\nFirst item keys: {list(items[0].keys())}")
        
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
    import traceback
    traceback.print_exc()
