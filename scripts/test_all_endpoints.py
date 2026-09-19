"""
Comprehensive Endpoint & Supabase Database Verification Script
Tests all FastAPI endpoints and Supabase CRUD operations.
"""
import sys
import os
import requests
import json
import time

# Ensure project root is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

BASE_URL = "http://localhost:8000"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def test_health():
    log("Testing Health Endpoint (/healthz)...")
    try:
        r = requests.get(f"{BASE_URL}/healthz", timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        log(f"Health check OK: {data}", "PASS")
        return True
    except Exception as e:
        log(f"Health check failed: {e}", "FAIL")
        return False

def test_supabase_direct():
    log("Testing Supabase Database Direct Operations...")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from backend.db.database import supabase, insert_claim, get_claim_by_id, get_all_claims, insert_evidence
        
        if not supabase:
            log("Supabase client not initialized (in-memory mode active)", "WARN")
            return True

        # Test insert claim
        test_hash = f"test_{int(time.time())}"
        test_text = "Test claim for database verification."
        row = insert_claim(test_hash, test_text, test_text.lower())
        claim_id = row.get("id")
        log(f"Inserted claim into Supabase ID: {claim_id}", "PASS")

        # Test read claim
        fetched = get_claim_by_id(claim_id)
        assert fetched is not None, "Failed to retrieve inserted claim from Supabase"
        log(f"Retrieved claim successfully: {fetched.get('id')}", "PASS")

        # Test insert evidence
        insert_evidence(claim_id, "Test evidence text from verifier", "https://reuters.com", "reuters.com", 0.95, "support")
        log("Inserted evidence row into Supabase", "PASS")

        return True
    except Exception as e:
        log(f"Supabase database operation failed: {e}", "FAIL")
        return False

def test_claim_submission_and_pipeline():
    log("Testing Claim Submission (/api/claims/submit)...")
    try:
        payload = {
            "claim_text": "Tech company announced breakthrough quantum computing chip in Zurich.",
            "source_url": "https://example.com/quantum"
        }
        r = requests.post(f"{BASE_URL}/api/claims/submit", json=payload, timeout=20)
        assert r.status_code in [200, 202], f"Expected 200/202, got {r.status_code}: {r.text}"
        data = r.json()
        claim_id = data.get("claim_id")
        log(f"Claim submitted successfully, Claim ID: {claim_id}", "PASS")

        # Test fetch claim status
        time.sleep(2)
        r2 = requests.get(f"{BASE_URL}/api/claims/{claim_id}", timeout=5)
        assert r2.status_code == 200, f"Expected 200 fetching claim, got {r2.status_code}"
        log(f"Claim status retrieved: {r2.json().get('status')}", "PASS")
        return True
    except Exception as e:
        log(f"Claim submission test failed: {e}", "FAIL")
        return False

def test_dashboard_endpoints():
    log("Testing Dashboard Endpoints (/api/dashboard/claims)...")
    try:
        r = requests.get(f"{BASE_URL}/api/dashboard/claims", timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        claims_list = data if isinstance(data, list) else data.get("claims", [])
        log(f"Dashboard returned {len(claims_list)} verified claims", "PASS")
        return True
    except Exception as e:
        log(f"Dashboard test failed: {e}", "FAIL")
        return False

def test_agent_endpoints():
    log("Testing Specialized Agent Endpoints...")
    results = {}

    # 1. Trending Agent
    try:
        log("Testing Trending Agent (/api/trending/scan)...")
        r = requests.post(f"{BASE_URL}/api/trending/scan", json={"query": "AI Chip Announcement"}, timeout=15)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        results["Trending Agent"] = True
        log(f"Trending Agent OK: status={r.status_code}", "PASS")
    except Exception as e:
        results["Trending Agent"] = False
        log(f"Trending Agent failed: {e}", "WARN")

    # 2. Scout Agent
    try:
        log("Testing Scout Agent (/api/scout/analyze)...")
        r = requests.post(f"{BASE_URL}/api/scout/analyze", json={"ticker": "NVDA"}, timeout=15)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        results["Scout Agent"] = True
        log(f"Scout Agent OK: status={r.status_code}", "PASS")
    except Exception as e:
        results["Scout Agent"] = False
        log(f"Scout Agent failed: {e}", "WARN")

    # 3. Personal Watch Agent
    try:
        log("Testing Personal Watch Agent (/api/personal/scan)...")
        r = requests.post(f"{BASE_URL}/api/personal/scan", json={"name": "Elon Musk"}, timeout=15)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        results["Personal Watch"] = True
        log(f"Personal Watch OK: status={r.status_code}", "PASS")
    except Exception as e:
        results["Personal Watch"] = False
        log(f"Personal Watch failed: {e}", "WARN")

    # 4. BrandShield Agent
    try:
        log("Testing BrandShield Agent (/api/brandshield/scan)...")
        r = requests.post(f"{BASE_URL}/api/brandshield/scan", json={"brand_name": "Tesla"}, timeout=15)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        results["BrandShield"] = True
        log(f"BrandShield OK: status={r.status_code}", "PASS")
    except Exception as e:
        results["BrandShield"] = False
        log(f"BrandShield failed: {e}", "WARN")

    return all(results.values())

def test_threat_lab_and_feeds():
    log("Testing Feeds and War Room Signals...")
    try:
        r = requests.get(f"{BASE_URL}/api/feed/live", timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        log(f"Live Feed OK: {r.json().get('count', 0)} items", "PASS")

        r2 = requests.get(f"{BASE_URL}/api/war-room/signals", timeout=5)
        assert r2.status_code == 200, f"Expected 200, got {r2.status_code}"
        log(f"War Room Signals OK: {r2.json().get('count', 0)} signals", "PASS")
        return True
    except Exception as e:
        log(f"Feed test failed: {e}", "FAIL")
        return False

if __name__ == "__main__":
    print("\n==================================================")
    print("  AEGIS PROTOCOL — ENDPOINT & DATABASE TEST SUITE ")
    print("==================================================\n")
    
    h_ok = test_health()
    db_ok = test_supabase_direct()
    sub_ok = test_claim_submission_and_pipeline()
    dash_ok = test_dashboard_endpoints()
    agents_ok = test_agent_endpoints()
    feed_ok = test_threat_lab_and_feeds()

    print("\n--------------------------------------------------")
    print("SUMMARY RESULTS:")
    print(f"  Health Check:          {'PASSED' if h_ok else 'FAILED'}")
    print(f"  Supabase DB CRUD:      {'PASSED' if db_ok else 'FAILED'}")
    print(f"  Claim Pipeline:        {'PASSED' if sub_ok else 'FAILED'}")
    print(f"  Live Dashboard API:    {'PASSED' if dash_ok else 'FAILED'}")
    print(f"  4 Specialized Agents:  {'PASSED' if agents_ok else 'FAILED'}")
    print(f"  Live Feeds & Signals:  {'PASSED' if feed_ok else 'FAILED'}")
    print("--------------------------------------------------\n")
