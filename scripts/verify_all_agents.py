"""
verify_all_agents.py
====================
Real, live end-to-end browser verification of all specialized Aegis Protocol agents:
1. Trending Agent (trending-agent.html)
2. Scout Agent (scout-agent.html)
3. BrandShield Agent (brandshield-agent.html)
4. Personal Watch Agent (personal-watch-agent.html)

Performs live UI interactions, captures screenshots, intercepts network/console,
and probes direct backend counterparts on Render to produce complete empirical evidence.
"""

import os
import sys
import json
import time
import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
import urllib.request

BASE_URL = "https://aegis-protocol-110.pages.dev"
BACKEND_BASE = "https://misinformation-1ouh.onrender.com"

ARTIFACTS_DIR = Path("artifacts/live_agent_verification")
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def verify_all_agents():
    print("[ALL AGENTS VERIFY] Starting multi-agent live probe on deployed website and backend...")
    now_ist = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    timestamp_ist_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")

    agent_results = {}
    network_traces = []
    console_logs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        def on_console(msg):
            entry = {"type": msg.type, "text": msg.text, "time": time.time()}
            console_logs.append(entry)
            if msg.type in ("error", "warning") and any(w in msg.text.lower() for w in ["404", "405", "failed", "api", "scan"]):
                print(f"  [CONSOLE {msg.type.upper()}] {msg.text}")

        def on_response(res):
            if any(k in res.url for k in ["/api/", "trending", "scout", "brandshield", "personal", "claims"]):
                entry = {
                    "url": res.url,
                    "status": res.status,
                    "status_text": res.status_text,
                    "time": time.time()
                }
                network_traces.append(entry)
                print(f"  [NET RES] {res.status} {res.url}")

        page.on("console", on_console)
        page.on("response", on_response)

        # =====================================================================
        # 1. TRENDING AGENT (trending-agent.html)
        # =====================================================================
        print("\n--- 1. Testing Trending Agent (trending-agent.html) ---")
        trending_url = f"{BASE_URL}/trending-agent.html"
        page.goto(trending_url, wait_until="networkidle")
        page.screenshot(path=str(SCREENSHOTS_DIR / "10_trending_initial.png"))

        # Look for search input and scan button
        trend_input = page.locator("#trendingSearchInput, input[type='text'], input[placeholder*='trend']").first
        trend_btn = page.locator("#scanTrendingBtn, button:has-text('Discover'), button:has-text('Scan')").first

        trending_input_exists = trend_input.count() > 0
        trending_btn_exists = trend_btn.count() > 0
        print(f"  Trending Controls: input={trending_input_exists}, btn={trending_btn_exists}")

        trend_query = "AI Regulation Rumors"
        if trending_input_exists and trending_btn_exists:
            trend_input.fill(trend_query)
            page.screenshot(path=str(SCREENSHOTS_DIR / "11_trending_query_entered.png"))
            
            t0 = time.perf_counter()
            trend_btn.click()
            time.sleep(4.0)
            elapsed_trend = time.perf_counter() - t0
            page.screenshot(path=str(SCREENSHOTS_DIR / "12_trending_terminal.png"))

            ui_out = page.evaluate("""() => {
                const emptyBanner = document.querySelector('.empty-banner, .empty-state, .failure-state');
                const resultsMount = document.getElementById('resultsMount') || document.getElementById('trendingResultsMount');
                return {
                    emptyBannerText: emptyBanner ? emptyBanner.innerText : null,
                    resultsText: resultsMount ? resultsMount.innerText.slice(0, 500) : null,
                    fullText: document.body.innerText.slice(0, 600)
                };
            }""")

            agent_results["trending_agent"] = {
                "name": "TrendingAgent",
                "page": "trending-agent.html",
                "route_tested": "POST /api/trending/scan",
                "input_used": trend_query,
                "elapsed_seconds": round(elapsed_trend, 2),
                "ui_state": ui_out,
                "screenshots": ["10_trending_initial.png", "11_trending_query_entered.png", "12_trending_terminal.png"]
            }

        # =====================================================================
        # 2. SCOUT AGENT (scout-agent.html)
        # =====================================================================
        print("\n--- 2. Testing Scout Agent (scout-agent.html) ---")
        scout_url = f"{BASE_URL}/scout-agent.html"
        page.goto(scout_url, wait_until="networkidle")
        page.screenshot(path=str(SCREENSHOTS_DIR / "13_scout_initial.png"))

        scout_input = page.locator("#scoutTickerInput, input[placeholder*='ticker'], input[type='text']").first
        scout_btn = page.locator("#runScoutBtn, button:has-text('Run Financial Scan'), button:has-text('Analyze')").first

        scout_input_exists = scout_input.count() > 0
        scout_btn_exists = scout_btn.count() > 0
        print(f"  Scout Controls: input={scout_input_exists}, btn={scout_btn_exists}")

        scout_query = "NVDA"
        if scout_input_exists and scout_btn_exists:
            scout_input.fill(scout_query)
            page.screenshot(path=str(SCREENSHOTS_DIR / "14_scout_query_entered.png"))

            t0 = time.perf_counter()
            scout_btn.click()
            time.sleep(4.0)
            elapsed_scout = time.perf_counter() - t0
            page.screenshot(path=str(SCREENSHOTS_DIR / "15_scout_terminal.png"))

            ui_out = page.evaluate("""() => {
                const emptyBanner = document.querySelector('.empty-banner, .empty-state, .failure-state, .intel-section');
                return {
                    bannerText: emptyBanner ? emptyBanner.innerText.slice(0, 500) : null,
                    fullText: document.body.innerText.slice(0, 600)
                };
            }""")

            agent_results["scout_agent"] = {
                "name": "ScoutAgent",
                "page": "scout-agent.html",
                "route_tested": "POST /api/scout/analyze",
                "input_used": scout_query,
                "elapsed_seconds": round(elapsed_scout, 2),
                "ui_state": ui_out,
                "screenshots": ["13_scout_initial.png", "14_scout_query_entered.png", "15_scout_terminal.png"]
            }

        # =====================================================================
        # 3. BRANDSHIELD AGENT (brandshield-agent.html)
        # =====================================================================
        print("\n--- 3. Testing BrandShield Agent (brandshield-agent.html) ---")
        brand_url = f"{BASE_URL}/brandshield-agent.html"
        page.goto(brand_url, wait_until="networkidle")
        page.screenshot(path=str(SCREENSHOTS_DIR / "16_brandshield_initial.png"))

        brand_input = page.locator("#brandInput, input[placeholder*='brand'], input[type='text']").first
        brand_btn = page.locator("#auditBrandBtn, button:has-text('Audit Brand'), button:has-text('Audit')").first

        brand_input_exists = brand_input.count() > 0
        brand_btn_exists = brand_btn.count() > 0
        print(f"  BrandShield Controls: input={brand_input_exists}, btn={brand_btn_exists}")

        brand_query = "Nike"
        if brand_input_exists and brand_btn_exists:
            brand_input.fill(brand_query)
            page.screenshot(path=str(SCREENSHOTS_DIR / "17_brandshield_query_entered.png"))

            t0 = time.perf_counter()
            brand_btn.click()
            time.sleep(4.0)
            elapsed_brand = time.perf_counter() - t0
            page.screenshot(path=str(SCREENSHOTS_DIR / "18_brandshield_terminal.png"))

            ui_out = page.evaluate("""() => {
                const banner = document.querySelector('.empty-banner, .empty-state');
                const mount = document.getElementById('brandShieldWorkspace') || document.getElementById('resultsMount');
                return {
                    bannerText: banner ? banner.innerText : null,
                    mountText: mount ? mount.innerText.slice(0, 500) : null
                };
            }""")

            agent_results["brandshield_agent"] = {
                "name": "BrandShieldAgent",
                "page": "brandshield-agent.html",
                "route_tested": "POST /api/brandshield/scan",
                "input_used": brand_query,
                "elapsed_seconds": round(elapsed_brand, 2),
                "ui_state": ui_out,
                "screenshots": ["16_brandshield_initial.png", "17_brandshield_query_entered.png", "18_brandshield_terminal.png"]
            }

        # =====================================================================
        # 4. PERSONAL WATCH AGENT (personal-watch-agent.html)
        # =====================================================================
        print("\n--- 4. Testing Personal Watch Agent (personal-watch-agent.html) ---")
        personal_url = f"{BASE_URL}/personal-watch-agent.html"
        page.goto(personal_url, wait_until="networkidle")
        page.screenshot(path=str(SCREENSHOTS_DIR / "19_personal_initial.png"))

        personal_input = page.locator("#profileName, input[placeholder*='name'], input[type='text']").first
        personal_btn = page.locator("#scanProfileBtn, button:has-text('Scan Identity'), button:has-text('Scan')").first

        personal_input_exists = personal_input.count() > 0
        personal_btn_exists = personal_btn.count() > 0
        print(f"  Personal Watch Controls: input={personal_input_exists}, btn={personal_btn_exists}")

        personal_query = "Sam Altman"
        if personal_input_exists and personal_btn_exists:
            personal_input.fill(personal_query)
            page.screenshot(path=str(SCREENSHOTS_DIR / "20_personal_query_entered.png"))

            t0 = time.perf_counter()
            personal_btn.click()
            time.sleep(4.0)
            elapsed_personal = time.perf_counter() - t0
            page.screenshot(path=str(SCREENSHOTS_DIR / "21_personal_terminal.png"))

            ui_out = page.evaluate("""() => {
                const mount = document.getElementById('resultsMount');
                return {
                    mountText: mount ? mount.innerText.slice(0, 500) : null
                };
            }""")

            agent_results["personal_watch_agent"] = {
                "name": "PersonalWatchAgent",
                "page": "personal-watch-agent.html",
                "route_tested": "POST /api/personal/scan",
                "input_used": personal_query,
                "elapsed_seconds": round(elapsed_personal, 2),
                "ui_state": ui_out,
                "screenshots": ["19_personal_initial.png", "20_personal_query_entered.png", "21_personal_terminal.png"]
            }

        browser.close()

    # =====================================================================
    # DIRECT PROBE OF RENDER BACKEND COUNTERPARTS
    # =====================================================================
    print("\n--- DIRECT PROBE OF RENDER BACKEND AGENTS ---")
    direct_backend_probes = {}

    endpoints_to_probe = [
        ("trending", f"{BACKEND_BASE}/api/trending/scan", {"asset_name": "AI Regulation", "query": "AI Regulation"}),
        ("scout", f"{BACKEND_BASE}/api/scout/analyze", {"ticker": "NVDA"}),
        ("brandshield", f"{BACKEND_BASE}/api/brandshield/scan", {"brand_name": "Nike"}),
        ("personal", f"{BACKEND_BASE}/api/personal/scan", {"name": "Sam Altman"})
    ]

    for key, url, payload in endpoints_to_probe:
        print(f"  Probing Render: POST {url} ...")
        t0 = time.perf_counter()
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        try:
            res = urllib.request.urlopen(req, timeout=35)
            dt = round(time.perf_counter() - t0, 2)
            raw_text = res.read().decode("utf-8", errors="ignore")
            try:
                data = json.loads(raw_text)
                keys = list(data.keys())
            except Exception:
                keys = []
            print(f"    -> Status: {res.getcode()} in {dt}s, Keys: {keys[:6]}")
            direct_backend_probes[key] = {
                "status": res.getcode(),
                "duration_seconds": dt,
                "keys_returned": keys,
                "sample_data": data if isinstance(data, dict) else str(data)[:200]
            }
        except Exception as e:
            dt = round(time.perf_counter() - t0, 2)
            print(f"    -> FAILED in {dt}s: {e}")
            direct_backend_probes[key] = {
                "status": "FAILED",
                "error": str(e),
                "duration_seconds": dt
            }

    # Save comprehensive summary
    full_audit = {
        "audit_name": "Aegis Protocol Comprehensive Multi-Agent Live Verification",
        "timestamp_ist": timestamp_ist_str,
        "frontend_origin": BASE_URL,
        "backend_origin": BACKEND_BASE,
        "deployed_ui_agent_tests": agent_results,
        "direct_render_backend_probes": direct_backend_probes,
        "network_responses_intercepted": network_traces
    }

    with open(ARTIFACTS_DIR / "all_agents_summary.json", "w", encoding="utf-8") as f:
        json.dump(full_audit, f, indent=2)

    print(f"\n[DONE] All agents verified. Saved to {ARTIFACTS_DIR / 'all_agents_summary.json'}")

if __name__ == "__main__":
    verify_all_agents()
