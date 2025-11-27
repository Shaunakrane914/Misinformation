"""
🎬 THE MONEY SHOT DEMO
======================
Complete demonstration of the Aegis War Room detecting and responding
to a coordinated misinformation attack.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

print("="*80)
print("🎬 AEGIS WAR ROOM - MONEY SHOT DEMONSTRATION")
print("="*80)
print()
print("This demo simulates a complete coordinated misinformation attack:")
print("  1. Fake news published: 'CEO Under Investigation'")
print("  2. Stock crashes 12 minutes later (-4%)")
print("  3. War Room detects correlation")
print("  4. AI generates crisis responses")
print("  5. Responses ready to deploy")
print()
input("Press ENTER to trigger the attack simulation...")

print("\n" + "="*80)
print("🚨 TRIGGERING DEMO ATTACK")
print("="*80)

# Trigger the demo attack
response = requests.get(f"{BASE_URL}/api/war-room/demo-attack")

if response.status_code == 200:
    result = response.json()
    
    if result['status'] == 'demo_success':
        print("\n✅ ATTACK DETECTED AND ANALYZED!")
        
        attack = result['attack_package']
        
        print("\n" + "="*80)
        print("📊 ATTACK INTELLIGENCE")
        print("="*80)
        print(f"Ticker:              {attack['ticker']}")
        print(f"Current Price:       ${attack['current_price']}")
        print(f"Stock Drop:          {attack['projected_loss']}%")
        print(f"Z-Score:             {attack['z_score']}")
        print()
        print(f"Smoking Gun:")
        print(f"  '{attack['smoking_gun_headline']}'")
        print(f"  Published:         {attack['article_timestamp']}")
        print(f"  Time to Impact:    {attack['latency_minutes']} minutes")
        print(f"  Correlation:       {attack['correlation_confidence']}%")
        
        print("\n" + "="*80)
        print("🤖 AI-GENERATED CRISIS RESPONSES")
        print("="*80)
        
        responses = attack['responses']
        
        print("\n1️⃣ CEASE & DESIST (Twitter Response):")
        print(f"   {responses['cease_desist']}")
        
        print("\n2️⃣ OFFICIAL DENIAL (Investor Relations):")
        print(f"   {responses['official_denial']}")
        
        print("\n3️⃣ CEO ALERT (Internal SMS):")
        print(f"   {responses['ceo_alert']}")
        
        print("\n" + "="*80)
        print("🚀 READY TO DEPLOY")
        print("="*80)
        print("\nThe attack package has been saved and is ready for deployment.")
        print(f"Event ID: {attack['event_id']}")
        
        # Demonstrate deploying a response
        print("\n" + "="*80)
        print("Demonstrating Response Deployment...")
        print("="*80)
        
        time.sleep(1)
        
        deploy_request = {
            "event_id": attack['event_id'],
            "response_type": "cease_desist"
        }
        
        deploy_response = requests.post(
            f"{BASE_URL}/api/war-room/deploy-response",
            json=deploy_request
        )
        
        if deploy_response.status_code == 200:
            deploy_result = deploy_response.json()
            print("\n✅ RESPONSE DEPLOYED!")
            print(f"\nType: {deploy_result['deployment']['response_type'].upper()}")
            print(f"Action: {deploy_result['deployment']['action']}")
            print(f"\nResponse Text:")
            print(f"  {deploy_result['deployment']['response_text']}")
        
        print("\n" + "="*80)
        print("✅ DEMONSTRATION COMPLETE")
        print("="*80)
        print("\nThe Aegis War Room successfully:")
        print("  ✓ Detected the crash (Scout Agent)")
        print("  ✓ Found the misinformation (Trending Agent)")
        print("  ✓ Proved causation (Correlation Engine)")
        print("  ✓ Generated responses (AI Crisis Manager)")
        print("  ✓ Deployed countermeasure (Response System)")
        
    else:
        print(f"\n⚠️ Demo incomplete: {result['message']}")
        print(json.dumps(result, indent=2, default=str))
else:
    print(f"\n❌ Error: HTTP {response.status_code}")
    print(response.text)

print("\n" + "="*80)
print("🏁 DEMO SESSION ENDED")
print("="*80)
