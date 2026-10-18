"""Exact-commit deployment checks, optionally four real public browser scans.

Fail closed before research when backend commit or frontend asset bytes differ.
No provider/model credentials loaded, no notifications, no replay stubs. Successful
transport/rendering is NOT research accuracy, evidence entailment or accessibility.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
FRONTEND = "https://aegis-protocol-110.pages.dev"
BACKEND = "https://misinformation-1ouh.onrender.com"
SERVICE = "srv-d716v3dactks738os7d0"
ASSETS = ("aegis-nav.js", "agent-research-client.js", "unified-report-renderer.js", "benchmark.html", "index.html",
          "scout-agent.html", "trending-agent.html", "brandshield-agent.html", "personal-watch-agent.html")
CASES = (("scout", "MSFT", "scout-agent", "tickerInput", "analyzeBtn"),
         ("trending", "NVIDIA", "trending-agent", "scanQueryInput", "trendingScanBtn"),
         ("brandshield", "Nike", "brandshield-agent", "brandInput", "scanBtn"),
         ("personal_watch", "Satya Nadella", "personal-watch-agent", "personInput", "scanBtn"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True, help="Only Render deployment attestation key is read")
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-live-research", action="store_true", help="Four normal production investigations; creates new dossiers")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{40}", args.expected_commit):
        parser.error("Expected commit must be an exact SHA")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    key = dotenv_values(args.env_file).get("RENDER_API_KEY")
    if not key:
        parser.error("Render deployment attestation credential unavailable")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("Credential-bearing redirect refused")

    request = urllib.request.Request("https://api.render.com/v1/services/" + SERVICE + "/deploys?limit=5",
                                     headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=8) as response:
            deployments = json.loads(response.read(256000))
    except Exception as error:
        print(json.dumps({"status": "ATTESTATION_UNAVAILABLE", "error_type": type(error).__name__}))
        return 1
    live = next((r["deploy"] for r in deployments if r["deploy"].get("status") == "live"), {})
    result = {"expected_commit": args.expected_commit, "backend_live_commit": (live.get("commit") or {}).get("id"),
              "backend_deploy_id": live.get("id"), "frontend_assets": [], "cases": [],
              "scope": "Actual deployment transport/rendering, not research accuracy acceptance",
              "ai_generation_requested": False, "upstream_ai_usage_accounting": "NOT_OBSERVED"}

    def save():
        (args.output_dir / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    if result["backend_live_commit"] != args.expected_commit:
        result["status"] = "BACKEND_COMMIT_MISMATCH_NO_RESEARCH"
        save()
        print(json.dumps(result))
        return 1
    try:
        for name in ASSETS:
            expected = subprocess.check_output(["git", "show", args.expected_commit + ":frontend/" + name], cwd=ROOT)
            asset_request = urllib.request.Request(FRONTEND + "/" + name,
                headers={"User-Agent": "Aegis-Release-Verification/1.0", "Accept": "*/*"})
            with urllib.request.urlopen(asset_request, timeout=10) as response:
                actual = response.read(1_000_001)
            result["frontend_assets"].append({"name": name, "matches_commit": actual == expected,
                                               "sha256": hashlib.sha256(actual).hexdigest()})
    except Exception as error:
        result["status"] = "FRONTEND_CHECK_UNAVAILABLE_NO_RESEARCH"
        result["error_type"] = type(error).__name__
        result["http_status"] = getattr(error, "code", None)
        result["asset"] = name
        save()
        return 1
    if not all(a["matches_commit"] for a in result["frontend_assets"]):
        result["status"] = "FRONTEND_ASSET_MISMATCH_NO_RESEARCH"
        save()
        print(json.dumps(result))
        return 1
    if not args.allow_live_research:
        result["status"] = "EXACT_DEPLOYED_CODE_OBSERVED_NO_RESEARCH"
        save()
        print(json.dumps(result))
        return 0

    from playwright.sync_api import sync_playwright
    from scripts.audits.run_terminal_agent_quality import parse_events, native_source_records
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for index, (agent, target, page_name, field, button) in enumerate(CASES, 1):
                case_id = str(index) + "-" + agent
                page = browser.new_page(viewport={"width": 390, "height": 1000}, reduced_motion="reduce")
                errors = []
                page.on("pageerror", lambda e: errors.append(type(e).__name__))
                page.add_init_script("""(() => {const realFetch=window.fetch.bind(window);window.releaseStream=null;
                  window.fetch=async (...args)=>{const r=await realFetch(...args);
                    if(String(args[0]).includes('/stream')) r.clone().text().then(text=>{
                      window.releaseStream={url:r.url,status:r.status,text};});return r;};})();""")
                row = {"agent": agent, "input": target}
                started = time.monotonic()
                try:
                    page.goto(FRONTEND + "/" + page_name + ".html", wait_until="load", timeout=30000)
                    page.locator("#" + field).fill(target)
                    if agent == "trending":
                        page.locator("#catSelect").select_option("technology")
                    page.locator("#" + button).click()
                    page.wait_for_function("window.releaseStream !== null", timeout=270000)
                    observed = page.evaluate("window.releaseStream")
                    events = parse_events(observed["text"])
                    native = next((e["data"]["result"] for e in events if e["event"] == "result"), {})
                    (args.output_dir / (case_id + "-events.json")).write_text(json.dumps(events), encoding="utf-8")
                    (args.output_dir / (case_id + ".json")).write_text(json.dumps(native), encoding="utf-8")
                    row.update(http_status=observed["status"], stream_url=observed["url"], result_event=bool(native),
                               error_events=sum(e["event"] == "error" for e in events),
                               progress_events=sum(e["event"] == "progress" for e in events),
                               retained_records=len(native_source_records(native)), views=[])
                    report = native.get("unified_report") or {}
                    sources = native_source_records(native)
                    row.update(seconds=round(time.monotonic() - started, 2),
                               retained_text_words=sum(len(str(s.get("content") or s.get("snippet") or "").split()) for s in sources),
                               finding_strings=len(report.get("findings", [])), discovery_records=len(report.get("discovery", [])))
                    expected_cards = sum(len(v) for v in report.get("evidence", {}).values() if isinstance(v, list))
                    for width in (390, 1440):
                        page.set_viewport_size({"width": width, "height": 1000})
                        page.evaluate("async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));}")
                        node = page.locator(".unified-report")
                        if node.count():
                            node.scroll_into_view_if_needed()
                        page.screenshot(path=str(args.output_dir / (case_id + "-" + str(width) + ".png")))
                        counts = [page.locator("#ur-findings-body > ul > li").count(),
                                  page.locator("#ur-evidence .ur-ev-card").count(), page.locator("#ur-discovery .ur-ev-card").count()]
                        row["views"].append({"width": width, "document_width": page.evaluate("document.documentElement.scrollWidth"),
                                             "report_visible": node.count() > 0 and node.is_visible(),
                                             "counts_match": counts == [len(report.get("findings", [])), expected_cards, len(report.get("discovery", []))],
                                             "rendered_counts": counts})
                except Exception as error:
                    row["error_type"] = type(error).__name__
                row["page_errors"] = errors
                result["cases"].append(row)
                save()
                print(json.dumps(row), flush=True)
                page.close()
        finally:
            browser.close()
    passed = all(r.get("result_event") and r.get("http_status") == 200 and r.get("stream_url", "").startswith(BACKEND + "/api/")
                 and not r.get("error_events") and not r.get("error_type") and not r["page_errors"] and len(r.get("views", [])) == 2
                 and all(v["report_visible"] and v["counts_match"] and v["document_width"] <= v["width"] for v in r["views"]) for r in result["cases"])
    result["status"] = "BOUNDED_LIVE_BROWSER_TRANSPORT_PASS" if passed else "LIVE_BROWSER_CHECK_INCOMPLETE"
    save()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
