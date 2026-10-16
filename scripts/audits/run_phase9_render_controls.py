"""Rendered fixture controls and exact report replay, explicitly NOT live scraping."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--chart-js", type=Path, required=True)
    parser.add_argument("--claim-results", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    args.output_dir.mkdir(parents=True, exist_ok=False)

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root / "frontend")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    chart = args.chart_js.read_bytes()
    rows = []
    cases = []
    for status in ("SUPPORTED", "REFUTED", "MISLEADING", "MIXED", "OUTDATED", "UNVERIFIED", "INSUFFICIENT_EVIDENCE"):
        cases.append((f"fixture-{status}", "SYNTHETIC CONTRACT", {
            "summary": "[SYNTHETIC UI CONTROL] Not a live investigation.",
            "claim_decomposition": [{"claim_text": "[SYNTHETIC] Example claim <img src=x onerror=alert(1)>",
                                     "verdict": status, "confidence": .5, "is_heuristic": True,
                                     "rationale": "Fixture explanation, not an adjudication.",
                                     "evidence_citations": [{"canonical_url": "javascript:alert(1)", "source_name": "Hostile test link",
                                                             "relevant_excerpt": "<script>window.fixtureInjected=true</script>"}]}],
            "evidence": {}, "trust": {},
        }))
    cases.append(("fixture-large", "SYNTHETIC 200-RECORD STRESS", {
        "summary": "[SYNTHETIC UI CONTROL] Large collection.", "findings": ["[SYNTHETIC] " + "LongTitle" * 100],
        "evidence": {"community": [{"evidence_id": f"fixture-{i}", "title": "[SYNTHETIC] " + "LongTitle" * 100,
                                     "url": "javascript:alert(1)", "source": {"name": "Test source"}}
                                    for i in range(200)]}, "trust": {},
    }))
    for index, path in enumerate(args.claim_results):
        for row in json.loads(path.read_text(encoding="utf-8"))["cases"]:
            if row.get("report"):
                cases.append((f"replay-{index}-{row['id']}", "EXACT SAVED RESEARCH REPORT REPLAY", row["report"]))
    cases.append(("fixture-brand-zero", "SYNTHETIC NATIVE ZERO-SOURCE BRANCH", {
        "summary": "[SYNTHETIC UI CONTROL] Zero acquired records, preserve uncertainty and findings.",
        "findings": ["[SYNTHETIC] Unverified lead remains inspectable."], "evidence": {}, "trust": {},
    }))
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for code, scope, report in cases:
                page = browser.new_page(viewport={"width": 320, "height": 1000}, reduced_motion="reduce")
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))

                def route(request):
                    url = request.request.url
                    if urlsplit(url).netloc == urlsplit(base).netloc:
                        request.continue_()
                    elif url == "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js":
                        request.fulfill(status=200, content_type="application/javascript", body=chart)
                    else:
                        request.abort()

                page.route("**/*", route)
                page.goto(base + "/brandshield-agent.html", wait_until="load")
                if code == "fixture-brand-zero":
                    page.evaluate("r => renderBrandShieldWorkspace({brand_name:'[SYNTHETIC]',sources:[],threats:[],unified_report:r},document.getElementById('resultsContainer'))", report)
                else:
                    page.evaluate("r => renderUnifiedReport(document.getElementById('resultsContainer'),r)", report)
                for width in (320, 1440):
                    page.set_viewport_size({"width": width, "height": 1000})
                    page.evaluate("async () => {await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));}")
                    mount = page.locator(".unified-report")
                    focus = page.locator("#ur-claim-decomp")
                    if focus.count():
                        focus.evaluate("el => el.scrollIntoView({block:'start'})")
                    else:
                        mount.evaluate("el => el.scrollIntoView({block:'start'})")
                    page.evaluate("window.scrollBy(0,-80)")
                    screenshot = f"{code}-{width}.png"
                    page.screenshot(path=str(args.output_dir / screenshot))
                    metrics = page.evaluate("""() => ({width:innerWidth,document_width:document.documentElement.scrollWidth,
                        injected:!!window.fixtureInjected,unsafe_links:document.querySelectorAll('a[href^="javascript:"]').length,
                        injected_images:document.querySelectorAll('img[onerror]').length,
                        cards:document.querySelectorAll('#ur-evidence .ur-ev-card').length,
                        clipped_claim_cards:[...document.querySelectorAll('.ur-decomp-card')].filter(card=>{
                          const boundary=card.closest('section')||card.parentElement;
                          return card.getBoundingClientRect().right > boundary.getBoundingClientRect().right+1;
                        }).length})""")
                    toggle = page.locator(".ur-heading-button").first
                    toggle.focus()
                    before = toggle.get_attribute("aria-expanded")
                    toggle.press("Enter")
                    keyboard = toggle.get_attribute("aria-expanded") != before
                    toggle.press("Enter")
                    rows.append({"id": code, "scope": scope, "screenshot": screenshot, "report_visible": mount.is_visible(),
                                 "keyboard_disclosure": keyboard, "page_errors": list(errors), **metrics})
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    result = {"scope": "Synthetic hostile/verdict/stress controls plus saved backend reports rendered without reacquisition",
              "screen_reader": "NOT_VERIFIED", "contrast": "NOT_MEASURED", "axe": "NOT_RUN", "rows": rows}
    (args.output_dir / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    failures = [row for row in rows if row["page_errors"] or row["document_width"] > row["width"] + 1
                or row["injected"] or row["unsafe_links"] or row["injected_images"]
                or row["clipped_claim_cards"]
                or not row["keyboard_disclosure"] or not row["report_visible"]]
    print(json.dumps({"states": len(rows), "failed_states": len(failures), "scope": result["scope"]}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
