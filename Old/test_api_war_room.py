"""
Test War Room API Gateway Endpoints
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

print("="*80)
print("🏛️ WAR ROOM API GATEWAY TEST")
print("="*80)
print()

# Step 1: Trigger demo attack to create data
print("📌 STEP 1: Trigger Demo Attack")
print("-" * 40)

response = requests.get(f"{BASE_URL}/api/war-room/demo-attack")
if response.status_code == 200:
    result = response.json()
    if result['status'] == 'demo_success':
        attack = result['attack_package']
        event_id = attack['event_id']
        ticker = attack['ticker']
        
        print(f"✅ Demo attack triggered successfully!")
        print(f"   Event ID: {event_id}")
        print(f"   Ticker: {ticker}")
        print(f"   Stock Drop: {attack['projected_loss']}%")
        print(f"   Smoking Gun: {attack['smoking_gun_headline'][:60]}...")
    else:
        print(f"⚠️ Demo incomplete: {result['message']}")
        event_id = None
else:
    print(f"❌ Error: {response.status_code}")
    event_id = None

# Step 2: Get War Room signals (timeline data)
print("\n\n📌 STEP 2: Get War Room Signals")
print("-" * 40)

response = requests.get(f"{BASE_URL}/api/war-room/signals")
if response.status_code == 200:
    result = response.json()
    print(f"✅ Status: {result['status']}")
    print(f"   Time Range: {result['time_range_hours']} hours")
    print(f"   Stock Events (Crashes): {len(result['stock_events'])}")
    print(f"   Threat Events (Rumors): {len(result['threat_events'])}")
    print(f"   Total Events: {result['total_events']}")
else:
    print(f"❌ Error: {response.status_code}")

# Step 3: Get live threat feed
print("\n\n📌 STEP 3: Get Live Threat Feed")
print("-" * 40)

response = requests.get(f"{BASE_URL}/api/feed/live")
if response.status_code == 200:
    result = response.json()
    print(f"✅ Status: {result['status']}")
    print(f"   Total Threats: {result['total_threats']}")
    
    if result['threats']:
        print(f"\n   Latest Threat:")
        threat = result['threats'][0]
        print(f"     Event ID: {threat['event_id']}")
        print(f"     Ticker: {threat['ticker']}")
        print(f"     Severity: {threat['severity']}")
        print(f"     Status: {threat['status']}")
        print(f"     Correlation: {threat['correlation_confidence']}%")
        print(f"     Response Types Available:")
        for resp_type in threat['responses'].keys():
            print(f"       - {resp_type}")
else:
    print(f"❌ Error: {response.status_code}")

# Step 4: Deploy a countermeasure
if event_id:
    print("\n\n📌 STEP 4: Deploy Countermeasure")
    print("-" * 40)
    
    deploy_request = {
        "event_id": event_id,
        "response_type": "cease_desist",
        "current_stock_price": 1245.50
    }
    
    response = requests.post(
        f"{BASE_URL}/api/deploy-response",
        json=deploy_request
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Status: {result['status']}")
        print(f"   Message: {result['message']}")
        print(f"   Deployment Details:")
        dep = result['deployment']
        print(f"     Event ID: {dep['event_id']}")
        print(f"     Type: {dep['response_type']}")
        print(f"     Deployed At: {dep['deployed_at']}")
        print(f"     Stock Price: ${dep['stock_price']}")
        print(f"     Action: {dep['action']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

# Step 5: Verify deployment in live feed
print("\n\n📌 STEP 5: Verify Deployment Status")
print("-" * 40)

response = requests.get(f"{BASE_URL}/api/feed/live")
if response.status_code == 200:
    result = response.json()
    
    deployed_threats = [t for t in result['threats'] if t['response_deployed']]
    ready_threats = [t for t in result['threats'] if not t['response_deployed']]
    
    print(f"✅ Threat Status:")
    print(f"   Deployed: {len(deployed_threats)}")
    print(f"   Ready to Deploy: {len(ready_threats)}")
    
    if deployed_threats:
        print(f"\n   Recently Deployed:")
        for threat in deployed_threats[:3]:
            print(f"     - {threat['ticker']}: {threat['event_id']}")
else:
    print(f"❌ Error: {response.status_code}")

print("\n" + "="*80)
print("✅ WAR ROOM API GATEWAY TEST COMPLETE!")
print("="*80)
print()
print("Summary of Available Endpoints:")
print("  GET  /api/war-room/signals      - Timeline data for Chart.js")
print("  GET  /api/feed/live              - High-severity threat feed")
print("  POST /api/deploy-response        - Deploy countermeasure")
print("  GET  /api/war-room/demo-attack   - Trigger demo attack")
print("  GET  /api/war-room/latest-threat - Get latest threat")
print("  GET  /api/war-room/scan/{ticker} - Scan specific ticker")
print()
print("="*80)
