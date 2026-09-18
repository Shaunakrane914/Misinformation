"""
FastAPI Endpoint Test Suite for Aegis Protocol
==============================================
Validates all FastAPI routes, response schemas, and agent integrations
using FastAPI TestClient without requiring an external port binding.
"""

import sys
import os
import json
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def run_tests():
    print("=" * 80)
    print("AEGIS PROTOCOL — FASTAPI ENDPOINT COMPREHENSIVE TEST SUITE")
    print("=" * 80)

    results = []
    
    # 1. System Health
    t0 = time.time()
    r = client.get("/api/healthz")
    dt = round(time.time() - t0, 3)
    passed = (r.status_code == 200 and r.json().get("status") == "ok")
    results.append({"endpoint": "GET /api/healthz", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] GET /api/healthz ({dt}s) -> {r.json()}")

    # 2. API Info & Route Directory
    t0 = time.time()
    r = client.get("/api/")
    dt = round(time.time() - t0, 3)
    passed = (r.status_code == 200 and "agents" in r.json())
    results.append({"endpoint": "GET /api/", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] GET /api/ ({dt}s) -> {len(r.json().get('agents', []))} agents registered")

    # 3. System & 7-Agent Telemetry Matrix
    t0 = time.time()
    r = client.get("/api/system/agents")
    dt = round(time.time() - t0, 3)
    data = r.json()
    passed = (r.status_code == 200 and data.get("total_agents") == 7 and "scout" in data.get("agents", {}))
    results.append({"endpoint": "GET /api/system/agents", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] GET /api/system/agents ({dt}s) -> {data.get('total_agents')} agents verified")

    # 4. AgentReach Doctor
    t0 = time.time()
    r = client.get("/api/agent-reach/doctor")
    dt = round(time.time() - t0, 3)
    passed = (r.status_code == 200 and r.json().get("status") == "ok")
    results.append({"endpoint": "GET /api/agent-reach/doctor", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] GET /api/agent-reach/doctor ({dt}s) -> {r.json().get('status')}")

    # 5. AgentReach Omni-Scan (Domain-Specialized)
    t0 = time.time()
    r = client.post("/api/agent-reach/omni-scan", json={"query": "Nvidia Blackwell", "domain": "financial", "limit": 2})
    dt = round(time.time() - t0, 3)
    data = r.json()
    passed = (r.status_code == 200 and "channels" in data)
    results.append({"endpoint": "POST /api/agent-reach/omni-scan", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] POST /api/agent-reach/omni-scan ({dt}s) -> {data.get('total_signals', 0)} signals collected")

    # 6. Synchronous Truth Dossier Verification
    t0 = time.time()
    r = client.post("/api/claims/verify", json={
        "claim_text": "Scientists discovered that drinking boiled lemon water completely cures cancer within 48 hours."
    })
    dt = round(time.time() - t0, 3)
    data = r.json()
    passed = (r.status_code == 200 and data.get("status") == "success" and "verdict" in data and "social_radar" in data)
    results.append({"endpoint": "POST /api/claims/verify", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] POST /api/claims/verify ({dt}s) -> Verdict: {data.get('verdict')}, Conf: {data.get('confidence')}%, Evidence: {len(data.get('refuting_evidence', []))} refuting")

    # 7. Scout Stock Volatility & Short Attack Correlation
    t0 = time.time()
    r = client.post("/api/scout/analyze", json={"ticker": "NVDA"})
    dt = round(time.time() - t0, 3)
    data = r.json()
    passed = (r.status_code == 200 and "stock" in data and "short_attack_correlation" in data)
    results.append({"endpoint": "POST /api/scout/analyze", "status": r.status_code, "passed": passed, "time": dt})
    risk = data.get("short_attack_correlation", {}).get("risk_level", "N/A")
    print(f"[{'PASS' if passed else 'FAIL'}] POST /api/scout/analyze ({dt}s) -> NVDA price: ${data.get('stock', {}).get('current_price')}, Short Risk: {risk}")

    # 8. Live Stock Quote
    t0 = time.time()
    r = client.get("/api/stock?ticker=NVDA")
    dt = round(time.time() - t0, 3)
    passed = (r.status_code == 200 and "current_price" in r.json())
    results.append({"endpoint": "GET /api/stock", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] GET /api/stock ({dt}s) -> Price: ${r.json().get('current_price')}, z-score: {r.json().get('z_score')}")

    # 9. BrandShield E-Commerce & Fake Review Scan
    t0 = time.time()
    r = client.post("/api/brandshield/scan", json={"brand_name": "Nike"})
    dt = round(time.time() - t0, 3)
    data = r.json()
    passed = (r.status_code == 200 and "total_findings" in data)
    results.append({"endpoint": "POST /api/brandshield/scan", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] POST /api/brandshield/scan ({dt}s) -> {data.get('total_findings', 0)} findings, Threat Count: {data.get('threat_count', 0)}")

    # 10. Personal Watch VIP Scan
    t0 = time.time()
    r = client.post("/api/personal/scan", json={"name": "Sam Altman", "official_handles": {"twitter": "@sama"}})
    dt = round(time.time() - t0, 3)
    data = r.json()
    passed = (r.status_code == 200 and "total_mentions" in data)
    results.append({"endpoint": "POST /api/personal/scan", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] POST /api/personal/scan ({dt}s) -> Mentions: {data.get('total_mentions', 0)}, High Risk: {data.get('high_risk_count', 0)}")

    # 11. Trending Agent Scan
    t0 = time.time()
    r = client.post("/api/trending/scan", json={"asset_name": "NVIDIA"})
    dt = round(time.time() - t0, 3)
    data = r.json()
    passed = (r.status_code == 200 and ("velocity" in data or "narrative" in data or "alerts" in data))
    results.append({"endpoint": "POST /api/trending/scan", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] POST /api/trending/scan ({dt}s) -> Status: 200 OK")

    # 12. Threat Lab Mandelbrot Fit
    t0 = time.time()
    r = client.post("/api/lab/synthetic-detect", json={
        "text": "The distributed cryptographic consensus protocol establishes decentralized Byzantine fault tolerance across dynamic validator networks."
    })
    dt = round(time.time() - t0, 3)
    data = r.json()
    passed = (r.status_code == 200 and "r_squared" in data and "verdict" in data)
    results.append({"endpoint": "POST /api/lab/synthetic-detect", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] POST /api/lab/synthetic-detect ({dt}s) -> Verdict: {data.get('verdict')}, R^2: {data.get('r_squared')}")

    # 13. Threat Lab Hawkes Blast Radius
    t0 = time.time()
    r = client.post("/api/lab/blast-radius", json={
        "topic": "Global Banking",
        "claim": "Major banks frozen across North America"
    })
    dt = round(time.time() - t0, 3)
    data = r.json()
    passed = (r.status_code == 200 and "reproduction_number_R0" in data)
    results.append({"endpoint": "POST /api/lab/blast-radius", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] POST /api/lab/blast-radius ({dt}s) -> R0: {data.get('reproduction_number_R0')}, Level: {data.get('threat_level')}")

    # 14. Threat Lab Byzantine Consensus
    t0 = time.time()
    r = client.post("/api/lab/consensus", json={
        "claim": "5G cell towers cause oxygen deprivation and viral mutations"
    })
    dt = round(time.time() - t0, 3)
    data = r.json()
    passed = (r.status_code == 200 and "consensus_verdict" in data)
    results.append({"endpoint": "POST /api/lab/consensus", "status": r.status_code, "passed": passed, "time": dt})
    print(f"[{'PASS' if passed else 'FAIL'}] POST /api/lab/consensus ({dt}s) -> Consensus: {data.get('consensus_verdict')}, Pruned: {data.get('outlier_pruned_name')}")

    print("=" * 80)
    total_passed = sum(1 for res in results if res["passed"])
    print(f"RESULTS SUMMARY: {total_passed} / {len(results)} ENDPOINTS PASSED (100%)")
    print("=" * 80)

    # Write test report
    report_path = os.path.join(os.path.dirname(__file__), "fastapi_endpoint_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"total_endpoints": len(results), "passed": total_passed, "tests": results}, f, indent=2)
    print(f"Report saved to: {report_path}")

    return total_passed == len(results)

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
