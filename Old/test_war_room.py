"""
Test Strategic Crisis Governor
"""
import sys
sys.path.insert(0, '.')

from backend.agents.coordinator_agent import scan_ticker
import json

print("="*80)
print("🏛️ STRATEGIC CRISIS GOVERNOR TEST")
print("="*80)

print("\n🧪 Testing complete War Room pipeline with RELIANCE.NS...")
print("\nPIPELINE STAGES:")
print("  1. Scout Agent → Financial Analysis")
print("  2. Trending Agent → Content Intelligence")
print("  3. Correlation Engine → Causality Analysis")
print("  4. Response Generator → Crisis Communication")
print("  5. Archive → Database Storage")
print("\n" + "-"*80 + "\n")

result = scan_ticker("RELIANCE.NS")

print("\n" + "="*80)
print("📊 FINAL RESULT")
print("="*80)
print(json.dumps(result, indent=2, default=str))

print("\n" + "="*80)
print("✅ Test complete!")
print("="*80)
