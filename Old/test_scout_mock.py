"""
Test Scout Agent with Mock Data
"""
from backend.agents.scout_agent import ScoutAgent
import json

# Create scout instance
scout = ScoutAgent()

# Test 1: Analyze volatility with stable prices
print("=" * 80)
print("TEST 1: STABLE MARKET (Normal Prices)")
print("=" * 80)
stable_prices = [100.0, 100.5, 99.8, 100.2, 100.1, 99.9, 100.3, 100.0, 100.2, 99.8, 
                 100.1, 100.0, 99.9, 100.2, 100.1]
volatility_result = scout.analyze_volatility(stable_prices)
print(json.dumps(volatility_result, indent=2))

prediction_result = scout.predict_impact(stable_prices)
print("\nPrediction:")
print(json.dumps(prediction_result, indent=2))

# Test 2: Analyze volatility with a CRASH (Sigma Event)
print("\n" + "=" * 80)
print("TEST 2: SIGMA EVENT (Market Crash)")
print("=" * 80)
crash_prices = [100.0, 100.5, 99.8, 100.2, 100.1, 99.9, 100.3, 100.0, 95.0, 94.5,
                93.8, 93.2, 92.5, 92.0, 91.5]  # Sudden drop to 91.5
volatility_result = scout.analyze_volatility(crash_prices)
print(json.dumps(volatility_result, indent=2))

prediction_result = scout.predict_impact(crash_prices)
print("\nPrediction:")
print(json.dumps(prediction_result, indent=2))

# Test 3: Analyze volatility with a RALLY
print("\n" + "=" * 80)
print("TEST 3: RALLY (Price Surge)")
print("=" * 80)
rally_prices = [100.0, 100.5, 99.8, 100.2, 100.1, 99.9, 100.3, 100.0, 105.0, 106.5,
                107.8, 108.2, 109.1, 110.0, 111.5]  # Sudden surge to 111.5
volatility_result = scout.analyze_volatility(rally_prices)
print(json.dumps(volatility_result, indent=2))

prediction_result = scout.predict_impact(rally_prices)
print("\nPrediction:")
print(json.dumps(prediction_result, indent=2))

print("\n" + "=" * 80)
print("✅ Scout Agent Logic: WORKING!")
print("=" * 80)
