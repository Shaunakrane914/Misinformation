"""
Aegis Enterprise - Agent Verification Script
=============================================
Tests Phase 1 (Scout) and Phase 2 (Trending) agents independently.
"""

import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from backend.agents.scout_agent import ScoutAgent
from backend.agents.trending_agent import TrendingAgent


def test_scout_agent():
    """Test Phase 1: Scout Agent (Financial Watchdog)"""
    print("\n" + "="*80)
    print("PHASE 1: SCOUT AGENT VERIFICATION")
    print("="*80)
    
    try:
        scout = ScoutAgent()
        
        # Test crash detection
        result = scout.check_stock_impact("TATAMOTORS.NS")
        
        if result:
            print(f"✅ Scout Agent functional")
            print(f"   Ticker: {result.get('ticker')}")
            print(f"   Current Price: ₹{result.get('current_price', 0):.2f}")
            print(f"   Drop Percent: {result.get('drop_percent', 0):.2f}%")
            print(f"   Z-Score: {result.get('z_score', 0):.2f}")
            print(f"   Is Crashing: {result.get('is_crashing')}")
            return True
        else:
            print("❌ Scout Agent returned empty result")
            return False
            
    except Exception as e:
        print(f"❌ Scout Agent error: {str(e)}")
        return False


async def test_trending_agent():
    """Test Phase 2: Trending Agent (Reputation Radar)"""
    print("\n" + "="*80)
    print("PHASE 2: TRENDING AGENT VERIFICATION")
    print("="*80)
    
    try:
        trending = TrendingAgent()
        
        # Test hunt mode (reactive dragnet)
        result = trending.process_task({
            'mode': 'hunt',
            'target_ticker': 'TATAMOTORS.NS',
            'crash_time': '2025-11-27T15:00:00',
            'search_window_minutes': 60
        })
        
        if result and result.get('status') == 'completed':
            print(f"✅ Trending Agent functional")
            print(f"   Mode: {result.get('mode')}")
            print(f"   Articles Analyzed: {result.get('articles_analyzed', 0)}")
            print(f"   Panic Score: {result.get('panic_score', 0)}/100")
            print(f"   Smoking Gun Found: {result.get('smoking_gun_found')}")
            
            if result.get('smoking_gun_headline'):
                print(f"   Headline: {result.get('smoking_gun_headline')[:80]}...")
            
            return True
        else:
            print("❌ Trending Agent failed to complete")
            return False
            
    except Exception as e:
        print(f"❌ Trending Agent error: {str(e)}")
        return False


async def main():
    """Run all agent verification tests"""
    print("\n" + "="*80)
    print("AEGIS ENTERPRISE - AGENT VERIFICATION")
    print("="*80)
    
    # Run tests
    scout_ok = test_scout_agent()
    trending_ok = await test_trending_agent()
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    print(f"Phase 1 (Scout):    {'✅ PASS' if scout_ok else '❌ FAIL'}")
    print(f"Phase 2 (Trending): {'✅ PASS' if trending_ok else '❌ FAIL'}")
    print("="*80)
    
    if scout_ok and trending_ok:
        print("\n✅ ALL AGENTS VERIFIED - Ready for Phase 3 (Coordinator)")
        return 0
    else:
        print("\n❌ VERIFICATION FAILED - Check errors above")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
