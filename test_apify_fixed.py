"""Fixed Apify test"""
import os
import sys
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

token = os.getenv("APIFY_TOKEN")
print(f"Token loaded: {bool(token)}")

client = ApifyClient(token)
print("Client created\n")

try:
    print("Starting Instagram scraper...")
    actor = client.actor("apidojo/instagram-scraper")
    
    run = actor.call(
        run_input={
            "startUrls": [{"url": "https://www.instagram.com/viralbhayani/"}],
            "resultsType": "posts",
            "resultsLimit": 15,
        }
    )
    
    # run is a dict, not an object with .get()
    run_id = run["id"] if isinstance(run, dict) else str(run)
    status = run["status"] if isinstance(run, dict) else "unknown"
    dataset_id = run["defaultDatasetId"] if isinstance(run, dict) else None
    
    print(f"Run ID: {run_id}")
    print(f"Status: {status}")
    
    if dataset_id:
        print(f"\nFetching results from dataset...")
        dataset = client.dataset(dataset_id)
        result = dataset.list_items()
        items = result.get("items", []) if isinstance(result, dict) else []
        
        print(f"Total items fetched: {len(items)}\n")
        
        if items:
            print("SUCCESS! Here are the first results:")
            for i, item in enumerate(items[:3], 1):
                caption = str(item.get('caption', ''))[:80] if isinstance(item, dict) else ''
                likes = item.get('likesCount', 0) if isinstance(item, dict) else 0
                print(f"{i}. Likes: {likes}, Caption: {caption}...")
        else:
            print("No items returned (might still be processing)")
    else:
        print("No dataset ID found")
        
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
