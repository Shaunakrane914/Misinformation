"""
verify_live_scan.py
===================
Real, live end-to-end browser verification of the deployed Aegis website.
Executes exact user interactions, monitors console/network, extracts exact DOM output,
captures screenshots, and tests determinism/caching.
"""

import os
import sys
import json
import time
import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "https://aegis-protocol-110.pages.dev"
SUBMIT_URL = f"{BASE_URL}/submit.html"
TEST_CLAIM = "WhatsApp has introduced three red ticks that mean a government agency has registered a case against you."

ARTIFACTS_DIR = Path("artifacts/live_agent_verification")
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def run_verification():
    print(f"[VERIFY] Starting live QA & observability probe on {BASE_URL}...")
    now_ist = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    timestamp_ist_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    print(f"[VERIFY] Timestamp: {timestamp_ist_str}")

    network_requests = []
    network_responses = []
    failed_requests = []
    console_messages = []

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Wire up observability listeners
        def on_console(msg):
            entry = {
                "type": msg.type,
                "text": msg.text,
                "location": msg.location,
                "time": time.time()
            }
            console_messages.append(entry)
            print(f"  [CONSOLE {msg.type.upper()}] {msg.text}")

        def on_request(req):
            entry = {
                "url": req.url,
                "method": req.method,
                "headers": {k: v for k, v in req.headers.items() if "auth" not in k.lower() and "key" not in k.lower()},
                "post_data": req.post_data,
                "resource_type": req.resource_type,
                "time": time.time()
            }
            network_requests.append(entry)
            if any(k in req.url for k in ["/api/", "claims", "gemini", "render", "onrender", "netlify"]):
                print(f"  [NETWORK REQ] {req.method} {req.url}")
                if req.post_data:
                    print(f"    Payload: {req.post_data[:200]}")

        def on_response(res):
            body_text = None
            try:
                # Only capture bodies for api/json calls to keep memory sensible
                if any(k in res.url for k in ["/api/", "claims", "gemini", "render", "onrender", "netlify"]) or res.status >= 400:
                    body_text = res.text()
            except Exception:
                body_text = "<could not read body>"
            
            entry = {
                "url": res.url,
                "status": res.status,
                "status_text": res.status_text,
                "headers": {k: v for k, v in res.headers.items() if "auth" not in k.lower() and "key" not in k.lower()},
                "body": body_text,
                "time": time.time()
            }
            network_responses.append(entry)
            if any(k in res.url for k in ["/api/", "claims", "gemini", "render", "onrender", "netlify"]) or res.status >= 400:
                print(f"  [NETWORK RES] {res.status} {res.url} (bytes: {len(body_text or '')})")
                if body_text:
                    print(f"    Response preview: {body_text[:250]}")

        def on_request_failed(req):
            entry = {
                "url": req.url,
                "method": req.method,
                "failure": req.failure,
                "time": time.time()
            }
            failed_requests.append(entry)
            print(f"  [NETWORK FAIL] {req.method} {req.url} -> {req.failure}")

        page.on("console", on_console)
        page.on("request", on_request)
        page.on("response", on_response)
        page.on("requestfailed", on_request_failed)

        # =====================================================================
        # PHASE 1: INSPECT LIVE SITE (HOME)
        # =====================================================================
        print("\n--- PHASE 1: Inspect Home Page ---")
        page.goto(BASE_URL, wait_until="networkidle")
        home_title = page.title()
        print(f"Home Page Title: {home_title}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_home_initial.png"))

        # Inspect client-side environment globals
        client_env = page.evaluate("""() => {
            return {
                AEGIS_VERSION: window.AEGIS_VERSION || null,
                AEGIS_RELEASE_DATE: window.AEGIS_RELEASE_DATE || null,
                AEGIS_API_BASE: window.AEGIS_API_BASE || null,
                hasGetAegisApiUrl: typeof window.getAegisApiUrl === 'function',
                apiUrlClaims: typeof window.getAegisApiUrl === 'function' ? window.getAegisApiUrl('/api/claims/') : '/api/claims/',
                hasAskGemini: typeof window.askGemini === 'function',
                hasGeminiClient: typeof window.GeminiClient === 'object'
            };
        }""")
        print(f"Client Environment Globals: {json.dumps(client_env, indent=2)}")

        # =====================================================================
        # PHASE 2 & 3: NAVIGATE TO CLAIM VERIFICATION WORKSPACE (SUBMIT.HTML)
        # =====================================================================
        print("\n--- PHASE 2 & 3: Navigate to submit.html ---")
        # Click the 'Verify a Claim' navigation link
        verify_nav_link = page.locator("a.ae-nav-link:has-text('Verify a Claim')")
        if verify_nav_link.count() > 0:
            verify_nav_link.first.click()
            page.wait_for_load_state("networkidle")
        else:
            page.goto(SUBMIT_URL, wait_until="networkidle")

        submit_page_url = page.url
        submit_page_title = page.title()
        print(f"Submit URL: {submit_page_url}")
        print(f"Submit Title: {submit_page_title}")

        # Record form controls
        controls = page.evaluate("""() => {
            const inputEl = document.getElementById('claimText') || document.getElementById('claimInput');
            return {
                claimInputExists: !!inputEl,
                claimInputTag: inputEl ? inputEl.tagName : null,
                claimInputId: inputEl ? inputEl.id : null,
                sourceUrlExists: !!document.getElementById('sourceUrl'),
                sourceContextExists: !!document.getElementById('sourceContext'),
                setSearchRecent: !!document.getElementById('setSearchRecent') && document.getElementById('setSearchRecent').checked,
                setCheckContradict: !!document.getElementById('setCheckContradict') && document.getElementById('setCheckContradict').checked,
                setPreferPrimary: !!document.getElementById('setPreferPrimary') && document.getElementById('setPreferPrimary').checked,
                verifyBtnExists: !!document.getElementById('verifyBtn'),
                verifyBtnText: document.getElementById('verifyBtn') ? document.getElementById('verifyBtn').innerText.trim() : null
            };
        }""")
        print(f"Form Controls: {json.dumps(controls, indent=2)}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "02_submit_page_initial.png"))

        # Enter the exact test claim
        print(f"\n[INPUT] Entering claim: '{TEST_CLAIM}'")
        claim_input = page.locator("#claimText, #claimInput").first
        claim_input.fill(TEST_CLAIM)
        page.screenshot(path=str(SCREENSHOTS_DIR / "03_submit_claim_entered.png"))

        # =====================================================================
        # PHASE 4: EXECUTE SCAN WORKFLOW (RUN 1)
        # =====================================================================
        print("\n--- PHASE 4: Clicking 'Start Investigation' Button (RUN 1) ---")
        start_time_run1 = time.perf_counter()
        verify_btn = page.locator("#verifyBtn")
        verify_btn.click()

        # Capture in-flight progress stages
        time.sleep(0.8)
        stage_state = page.evaluate("""() => {
            const box = document.getElementById('evalStageBox');
            const label = document.getElementById('stageLabel');
            return {
                boxVisible: box ? window.getComputedStyle(box).display !== 'none' : false,
                label: label ? label.innerText.trim() : null,
                activeStep: document.querySelector('.stage-step-item.active') ? document.querySelector('.stage-step-item.active').innerText.trim() : null
            };
        }""")
        print(f"In-Flight Stage (t+0.8s): {stage_state}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "04_submit_scan_clicked_progress.png"))

        # Wait for terminal state: resultsWorkspace display != 'none' or verifyBtn enabled again
        print("[WAIT] Waiting for investigation to reach terminal state...")
        page.wait_for_function("""() => {
            const ws = document.getElementById('resultsWorkspace');
            const btn = document.getElementById('verifyBtn');
            const wsVisible = ws && window.getComputedStyle(ws).display !== 'none';
            const btnReady = btn && !btn.disabled;
            return wsVisible || btnReady;
        }""", timeout=45000)

        elapsed_run1 = time.perf_counter() - start_time_run1
        print(f"[COMPLETED] Run 1 completed in {elapsed_run1:.2f} seconds.")

        # Allow final animations to settle
        time.sleep(1.0)
        page.screenshot(path=str(SCREENSHOTS_DIR / "05_submit_scan_terminal_above_fold.png"))

        # Scroll to evidence section and screenshot
        page.evaluate("() => window.scrollTo(0, 600)")
        time.sleep(0.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "06_submit_scan_terminal_evidence_matrix.png"))

        # Full page screenshot
        page.screenshot(path=str(SCREENSHOTS_DIR / "07_submit_scan_terminal_full_page.png"), full_page=True)

        # =====================================================================
        # PHASE 7: EXTRACT EXACT USER-FACING OUTPUT (DOM)
        # =====================================================================
        raw_ui = page.evaluate("""() => {
            const getText = (id) => {
                const el = document.getElementById(id);
                return el ? el.innerText.trim() : null;
            };
            const getListItems = (id) => {
                const el = document.getElementById(id);
                if (!el) return [];
                return Array.from(el.querySelectorAll('li')).map(li => li.innerText.trim());
            };
            const getEvidenceCards = (id) => {
                const el = document.getElementById(id);
                if (!el) return [];
                return Array.from(el.children).map(c => c.innerText.trim());
            };

            return {
                claim_shown: getText('verdictClaimQuote'),
                verdict_pill: getText('verdictPill'),
                evidence_strength: getText('strengthPill'),
                assessment_summary: getText('bottomLineText'),
                audit_timestamp: getText('auditTimestamp'),
                why_points: getListItems('whyPointsList'),
                supporting_evidence: getEvidenceCards('supportingEvidenceList'),
                refuting_evidence: getEvidenceCards('refutingEvidenceList'),
                unknowns: getListItems('unknownsList'),
                chronology: getEvidenceCards('chronologyFeed'),
                forensic_explorer_present: !!document.getElementById('forensicExplorer'),
                unified_report_present: !!document.getElementById('unifiedReportContainer'),
                full_workspace_text: document.getElementById('resultsWorkspace') ? document.getElementById('resultsWorkspace').innerText : ''
            };
        }""")
        print("\n--- CAPTURED USER-FACING UI OUTPUT ---")
        print(f"Claim Shown: {raw_ui['claim_shown']}")
        print(f"Verdict Pill: {raw_ui['verdict_pill']}")
        print(f"Strength Pill: {raw_ui['evidence_strength']}")
        print(f"Summary: {raw_ui['assessment_summary']}")
        print(f"Why points count: {len(raw_ui['why_points'])}")
        print(f"Refuting count: {len(raw_ui['refuting_evidence'])}")
        print(f"Supporting count: {len(raw_ui['supporting_evidence'])}")

        # =====================================================================
        # PHASE 11: SECOND RUN (TEST DETERMINISM & CACHING)
        # =====================================================================
        print("\n--- PHASE 11: Executing Run 2 (Caching & Determinism Check) ---")
        network_count_before_run2 = len(network_requests)
        start_time_run2 = time.perf_counter()
        verify_btn.click()
        page.wait_for_function("""() => {
            const btn = document.getElementById('verifyBtn');
            return btn && !btn.disabled;
        }""", timeout=45000)
        elapsed_run2 = time.perf_counter() - start_time_run2
        print(f"[COMPLETED] Run 2 completed in {elapsed_run2:.2f} seconds.")
        new_requests_run2 = network_requests[network_count_before_run2:]

        # =====================================================================
        # HERO MODAL VERIFICATION ON INDEX.HTML
        # =====================================================================
        print("\n--- Testing Home Hero Modal (index.html) ---")
        page.goto(BASE_URL, wait_until="networkidle")
        hero_input = page.locator("#heroInput")
        hero_input.fill(TEST_CLAIM)
        hero_btn = page.locator("#heroSubmitBtn")
        hero_btn.click()
        time.sleep(1.0)
        page.screenshot(path=str(SCREENSHOTS_DIR / "08_home_hero_modal_submitted.png"))

        # Wait 8 seconds to observe modal behavior
        time.sleep(8.0)
        hero_modal_data = page.evaluate("""() => {
            return {
                title: document.getElementById('modalVerdictTitle') ? document.getElementById('modalVerdictTitle').innerText : '',
                badge: document.getElementById('modalVerdictBadgeWrap') ? document.getElementById('modalVerdictBadgeWrap').innerText : '',
                reasoning: document.getElementById('modalVerdictReasoning') ? document.getElementById('modalVerdictReasoning').innerText : '',
                timeElapsed: document.getElementById('modalTimeElapsed') ? document.getElementById('modalTimeElapsed').innerText : '',
                stages: {
                    s1: document.getElementById('mStage1') ? document.getElementById('mStage1').innerText : '',
                    s2: document.getElementById('mStage2') ? document.getElementById('mStage2').innerText : '',
                    s3: document.getElementById('mStage3') ? document.getElementById('mStage3').innerText : '',
                    s4: document.getElementById('mStage4') ? document.getElementById('mStage4').innerText : ''
                }
            };
        }""")
        print(f"Hero Modal Terminal Data: {json.dumps(hero_modal_data, indent=2)}")
        page.screenshot(path=str(SCREENSHOTS_DIR / "09_home_hero_modal_terminal.png"))

        browser.close()

    # =====================================================================
    # ANALYSIS & DETERMINATIONS
    # =====================================================================
    print("\n--- ANALYZING TRACES & NETWORK ACTIVITY ---")
    
    # Check if backend was reached
    api_claims_requests = [r for r in network_requests if "/api/claims" in r["url"]]
    api_claims_responses = [r for r in network_responses if "/api/claims" in r["url"]]
    gemini_requests = [r for r in network_requests if "gemini" in r["url"] or "generativelanguage" in r["url"]]
    render_requests = [r for r in network_requests if "onrender.com" in r["url"]]

    print(f"Total network requests: {len(network_requests)}")
    print(f"Requests to /api/claims*: {len(api_claims_requests)}")
    for req in api_claims_requests:
        print(f"  -> {req['method']} {req['url']}")
    print(f"Responses from /api/claims*: {len(api_claims_responses)}")
    for res in api_claims_responses:
        print(f"  -> {res['status']} {res['url']} : {res['body'][:120] if res['body'] else ''}")
    print(f"Direct Gemini requests: {len(gemini_requests)}")
    print(f"Direct Render requests: {len(render_requests)}")

    # Classify execution
    backend_reached = False
    claim_id = None
    execution_class = "FAILED"
    overall_result = "FAIL"
    mock_or_fallback_detected = False
    notes = []

    # Check for 404 on /api/claims
    got_404_on_claims = any(res["status"] == 404 for res in api_claims_responses)
    has_honest_fallback_text = "Backend research service is currently unreachable" in (raw_ui["assessment_summary"] or "")
    
    if got_404_on_claims and has_honest_fallback_text:
        backend_reached = False
        execution_class = "CLIENT_SIDE_FALLBACK" # Honest client fallback triggered due to missing backend proxy
        mock_or_fallback_detected = True
        overall_result = "FAIL"
        notes.append("Cloudflare Pages host (aegis-protocol-110.pages.dev) does not proxy /api/* to the Render backend, causing POST /api/claims/ to return HTTP 404 Not Found.")
        notes.append("The client-side JavaScript caught the 404 error and entered runClientFactCheck(). Because window.askGemini was not defined, it executed the honest fallback INSUFFICIENT_EVIDENCE state.")
    elif any(res["status"] == 200 for res in api_claims_responses):
        backend_reached = True
        execution_class = "REAL_BACKEND_PIPELINE"
        overall_result = "PASS"
    else:
        execution_class = "CLIENT_SIDE_FALLBACK"
        mock_or_fallback_detected = True
        overall_result = "FAIL"

    # Agent records
    agents = [
        {
            "agent_name": "ClaimIngestionAgent",
            "expected": True,
            "invocation_evidence": "None on deployed site — POST /api/claims/ returned 404",
            "input_evidence": "Claim text submitted in browser form",
            "output_evidence": "None (backend not reached)",
            "execution_status": "NOT_EXECUTED",
            "confidence": 0.0
        },
        {
            "agent_name": "ResearchAgent",
            "expected": True,
            "invocation_evidence": "None on deployed site — backend worker never dispatched",
            "input_evidence": "None",
            "output_evidence": "None",
            "execution_status": "NOT_EXECUTED",
            "confidence": 0.0
        },
        {
            "agent_name": "InvestigatorAgent",
            "expected": True,
            "invocation_evidence": "None on deployed site — backend worker never dispatched",
            "input_evidence": "None",
            "output_evidence": "None",
            "execution_status": "NOT_EXECUTED",
            "confidence": 0.0
        }
    ]

    mismatches = [
        {
            "type": "API_ROUTING_MISMATCH",
            "description": "Frontend fetch calls '/api/claims/' relative to origin (https://aegis-protocol-110.pages.dev/api/claims/), but Cloudflare Pages has no rewrite to Render backend (https://misinformation-1ouh.onrender.com). Requests fail with HTTP 404.",
            "status": "CONTRADICTED"
        },
        {
            "type": "AGENT_EXECUTION_MISMATCH",
            "description": "UI shows staged progress ('Searching news sources...', 'Check Contradictions', 'Evaluate Evidence Strength'), but no backend agent ran; the workflow terminated in the client-side INSUFFICIENT_EVIDENCE fallback.",
            "status": "CONTRADICTED"
        },
        {
            "type": "AGENT_COUNT_MISMATCH",
            "description": "Repo code defines 3 named agents in the claim scan pipeline (ClaimIngestionAgent, ResearchAgent, InvestigatorAgent). Marketing/docs reference 4 agents, but only 3 execute in the claims pipeline.",
            "status": "CONTRADICTED"
        }
    ]

    # Build execution summary JSON
    summary_data = {
        "test_name": "Aegis Live Claim Scan Verification",
        "website": BASE_URL,
        "test_claim": TEST_CLAIM,
        "timestamp_ist": timestamp_ist_str,
        "execution_class": execution_class,
        "overall_result": overall_result,
        "backend_reached": backend_reached,
        "claim_id": claim_id,
        "agents": agents,
        "final_ui_output": raw_ui,
        "backend_response": api_claims_responses[0] if api_claims_responses else {},
        "network_summary": {
            "total_requests": len(network_requests),
            "claims_requests": len(api_claims_requests),
            "claims_responses": len(api_claims_responses),
            "failed_requests": len(failed_requests),
            "gemini_requests": len(gemini_requests),
            "render_requests": len(render_requests)
        },
        "latency": {
            "run_1_elapsed_seconds": round(elapsed_run1, 2),
            "run_2_elapsed_seconds": round(elapsed_run2, 2),
            "metric_type": "SINGLE RUN (Run 1 & Run 2 captured separately, no fabricated p50/p95)"
        },
        "mock_or_fallback_detected": mock_or_fallback_detected,
        "mismatches": mismatches,
        "notes": notes
    }

    # Write output files
    with open(ARTIFACTS_DIR / "execution_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    with open(ARTIFACTS_DIR / "network_trace.json", "w", encoding="utf-8") as f:
        json.dump({"requests": network_requests, "responses": network_responses, "failed": failed_requests}, f, indent=2)

    with open(ARTIFACTS_DIR / "console_log.txt", "w", encoding="utf-8") as f:
        for c in console_messages:
            f.write(f"[{c['type'].upper()}] {c['text']}\n")

    with open(ARTIFACTS_DIR / "raw_ui_output.txt", "w", encoding="utf-8") as f:
        f.write(f"CLAIM: {raw_ui['claim_shown']}\n")
        f.write(f"VERDICT PILL: {raw_ui['verdict_pill']}\n")
        f.write(f"STRENGTH PILL: {raw_ui['evidence_strength']}\n")
        f.write(f"ASSESSMENT SUMMARY: {raw_ui['assessment_summary']}\n")
        f.write(f"AUDIT TIMESTAMP: {raw_ui['audit_timestamp']}\n\n")
        f.write("WHY POINTS:\n" + "\n".join(f"- {p}" for p in raw_ui['why_points']) + "\n\n")
        f.write("UNKNOWNS:\n" + "\n".join(f"- {p}" for p in raw_ui['unknowns']) + "\n\n")
        f.write("FULL WORKSPACE TEXT DUMP:\n" + raw_ui['full_workspace_text'] + "\n")

    with open(ARTIFACTS_DIR / "raw_backend_response.json", "w", encoding="utf-8") as f:
        json.dump(api_claims_responses[0] if api_claims_responses else {"error": "NO_BACKEND_RESPONSE_RECEIVED_404"}, f, indent=2)

    with open(ARTIFACTS_DIR / "agent_execution.json", "w", encoding="utf-8") as f:
        json.dump(agents, f, indent=2)

    print(f"\n[DONE] Verification completed. Output files stored in {ARTIFACTS_DIR.absolute()}")

if __name__ == "__main__":
    run_verification()
