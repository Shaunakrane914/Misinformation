"""Simple Apify test - no emojis"""
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
    print(f"Actor object created")
    
    run = actor.call(
        run_input={
            "startUrls": [{"url": "https://www.instagram.com/viralbhayani/"}],
            "resultsType": "posts",
            "resultsLimit": 15,
        }
    )
    print(f"\nRun ID: {run['id']}")
    print(f"Status: {run['status']}")
    
    # Get results
    dataset = client.dataset(run["defaultDatasetId"])
    items = dataset.list_items().get("items", [])
    
    print(f"\nSUCCESS! Got {len(items)} items")
    if items:
        print(f"\nFirst item has these fields: {list(items[0].keys())[:10]}")
        if 'caption' in items[0]:
            caption = items[0].get('caption', '')[:100]
            print(f"Sample caption: {caption}")
        
except Exception as e:
    print(f"\nERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
