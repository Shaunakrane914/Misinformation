"""
Test script for Phase 5: Alerts & Defense.
Verifies threat detection logic and defense generation.
"""
import logging
from dotenv import load_dotenv
from backend.services.alerts import check_critical_threats
from backend.services.intelligence import generate_defense

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env
load_dotenv()

def test_alerts_and_defense():
    print("="*60)
    print("TEST: Phase 5 - The Guardian (Alerts & Defense)")
    print("="*60)

    # 1. Test Threat Detection
    print("\n1. Testing Threat Detection...")
    mock_report = {
        "sources": {
            "news": [
                {"title": "Actor X wins award", "sentiment_score": 90, "is_threat": False},
                {"title": "Actor X scandal exposed!", "sentiment_score": -85, "is_threat": True}
            ],
            "fan_wars": [
                {"text": "#BoycottActorX trending now", "sentiment_score": -95, "is_threat": True}
            ]
        }
    }
    
    alerts = check_critical_threats(mock_report)
    print(f"   Found {len(alerts)} alerts (Expected 2).")
    
    if len(alerts) == 2:
        print("   ✅ Alert logic working correctly.")
    else:
        print("   ❌ Alert logic failed.")

    # 2. Test Defense Generation
    print("\n2. Testing Defense Generation...")
    rumor = "Deepika Padukone is quitting Bollywood due to pressure."
    print(f"   Rumor: '{rumor}'")
    print("   Generating defense (calling Gemini)...")
    
    defense = generate_defense(rumor)
    print(f"\n   Defense Statement:\n   '{defense}'")
    
    if defense and "Error" not in defense:
        print("\n   ✅ Defense generation successful.")
    else:
        print("\n   ❌ Defense generation failed.")

if __name__ == "__main__":
    test_alerts_and_defense()
