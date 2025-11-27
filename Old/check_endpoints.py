"""
Quick API Endpoint Checker
"""
import requests

BASE = "http://127.0.0.1:8000"

endpoints = [
    "/",
    "/docs",
    "/api/war-room/signals",
    "/api/war-room/latest-threat",
    "/api/feed/live",
    "/api/war-room/demo-attack"
]

print("Testing API Endpoints...")
print("="*60)

for endpoint in endpoints:
    try:
        r = requests.get(BASE + endpoint, timeout=2)
        status_icon = "✅" if r.status_code == 200 else "❌"
        print(f"{status_icon} {r.status_code} - {endpoint}")
    except Exception as e:
        print(f"❌ ERROR - {endpoint}: {e}")

print("="*60)
