"""
Test script for Personal Watch Agent ingestion.
Tests web and social media search functionality.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.agents.personal_agent import PersonalWatchAgent

def test_web_search():
    """Test web search functionality."""
    print("\n" + "="*80)
    print("TESTING WEB SEARCH")
    print("="*80 + "\n")
    
    agent = PersonalWatchAgent()
    
    # Test with a well-known person
    test_name = "Elon Musk"
    print(f"Searching for: {test_name}\n")
    
    results = agent.search_web_mentions(test_name, max_results=5)
    
    print(f"Found {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Snippet: {result['snippet'][:100]}...")
        print()
    
    return len(results) > 0

def test_full_scan():
    """Test full scan with VIP profile."""
    print("\n" + "="*80)
    print("TESTING FULL SCAN")
    print("="*80 + "\n")
    
    agent = PersonalWatchAgent()
    
    # Test VIP profile
    vip_profile = {
        "name": "Shaunak Rane",
        "official_handles": {
            "twitter": "@shaunakrane914"
        }
    }
    
    print(f"Scanning for: {vip_profile['name']}\n")
    
    results = agent.scan(vip_profile)
    
    print(f"Scan Results:")
    print(f"  Total mentions: {results['total_mentions']}")
    print(f"  Web mentions: {results['web_mentions']}")
    print(f"  Twitter mentions: {results['twitter_mentions']}")
    print()
    
    if results['mentions']:
        print("Sample mentions:")
        for mention in results['mentions'][:3]:
            print(f"  - [{mention['source']}] {mention.get('title') or mention.get('content', '')[:80]}")
    
    return results['total_mentions'] > 0

if __name__ == "__main__":
    print("\n🔍 Personal Watch Agent - Ingestion Test\n")
    
    # Test web search
    web_success = test_web_search()
    
    # Test full scan
    scan_success = test_full_scan()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Web Search: {'✅ PASSED' if web_success else '❌ FAILED'}")
    print(f"Full Scan: {'✅ PASSED' if scan_success else '❌ FAILED'}")
    print()
