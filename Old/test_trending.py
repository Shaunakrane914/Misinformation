"""
Test Trending Agent
"""
from backend.agents.trending_agent import trending_agent
import json

print("="*80)
print("🧪 TRENDING AGENT TESTS")
print("="*80)

# Test 1: Impersonation Detection
print("\n📌 Test 1: Impersonation Detection")
print("-" * 40)

test_cases = [
    ("@TataMotors", "@TataMotors", "Legitimate account"),
    ("@TataM0tors", "@TataMotors", "Zero instead of O"),
    ("@TataMotorss", "@TataMotors", "Extra 's'"),
    ("@Tata_Motors", "@TataMotors", "Underscore added"),
    ("@Apple", "@TataMotors", "Completely different"),
]

for suspect, official, description in test_cases:
    result = trending_agent.detect_impersonation(suspect, official)
    print(f"\n{description}:")
    print(f"  Suspect: {suspect}")
    print(f"  Verdict: {result['attack_type']}")
    print(f"  Similarity: {result['similarity_score']:.1%}")
    if result['is_impersonation']:
        print(f"  🚨 ALERT: {result['confidence']} confidence impersonation")

# Test 2: Panic Analysis
print("\n\n📌 Test 2: Panic Analysis")
print("-" * 40)

calm_headlines = [
    "Tata Motors reports quarterly earnings",
    "New electric vehicle launch planned",
    "Company expands manufacturing facilities"
]

panic_headlines = [
    "BREAKING: Tata Motors CEO ARRESTED in massive fraud scandal",
    "URGENT: Stock crashes 20% as RAID uncovers accounting irregularities",
    "CRISIS: Tata Motors files for BANKRUPTCY protection"
]

print("\nAnalyzing CALM headlines...")
calm_result = trending_agent.analyze_panic(calm_headlines)
print(f"  Panic Score: {calm_result['panic_score']}/100")

print("\nAnalyzing PANIC headlines...")
panic_result = trending_agent.analyze_panic(panic_headlines)
print(f"  Panic Score: {panic_result['panic_score']}/100")
if panic_result.get('highest_risk_headline'):
    print(f"  ⚠️ Highest Risk: {panic_result['highest_risk_headline']}")
    print(f"  Reason: {panic_result.get('risk_reason')}")

# Test 3: News Fetch (Recent news about a company)
print("\n\n📌 Test 3: Live News Fetch")
print("-" * 40)

print("\nFetching recent news about Apple...")
articles = trending_agent.fetch_targeted_news("Apple iPhone", window_mins=1440)
print(f"Found {len(articles)} articles in last 24 hours")
if articles:
    print("\nTop 3 articles:")
    for i, article in enumerate(articles[:3], 1):
        print(f"  {i}. {article['title']}")
        print(f"     Age: {article['age_minutes']} minutes ago")

print("\n" + "="*80)
print("✅ All tests completed!")
print("="*80)
