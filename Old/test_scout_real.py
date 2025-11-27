"""
Test Scout Agent with REAL Yahoo Finance API
"""
import os
from dotenv import load_dotenv
from backend.agents.scout_agent import process_scout_task
import json

# Load environment variables
load_dotenv()

print("=" * 80)
print("🧪 TESTING SCOUT AGENT WITH REAL API")
print("=" * 80)
print(f"API Key loaded: {'Yes' if os.getenv('YFAPI_KEY') else 'No'}")
print()

# Test with Tata Motors (Indian stock)
test_task = {
    "ticker": "TATAMOTORS.NS",
    "type": "volatility_check"
}

print("📊 Scanning: TATAMOTORS.NS")
print("⏳ Fetching live data from Yahoo Finance...")
print()

result = process_scout_task(test_task)

print("\n" + "=" * 80)
print("📈 SCOUT AGENT RESULTS")
print("=" * 80)
print(json.dumps(result, indent=2))
print()

# Interpret results
if result.get("status") == "completed":
    stats = result.get("stats", {})
    prediction = result.get("prediction", {})
    
    print("=" * 80)
    print("🎯 INTERPRETATION")
    print("=" * 80)
    print(f"Current Price: ₹{result.get('current_price')}")
    print(f"Z-Score: {stats.get('z_score')} (2σ threshold for crash)")
    print(f"Status: {stats.get('volatility_status')}")
    print(f"Prediction (1hr): ₹{prediction.get('projected_price_1hr')} ({prediction.get('projected_loss')}%)")
    print(f"Trend: {prediction.get('trend')}")
    
    if stats.get('volatility_status') == 'SIGMA_EVENT':
        print("\n🚨 ALERT: SIGMA EVENT DETECTED!")
        print("   → This would trigger the Trending Agent in War Room mode")
    else:
        print("\n✅ Market is stable - continuing surveillance")
else:
    print("❌ Test failed. Check your YFAPI_KEY in .env file")
