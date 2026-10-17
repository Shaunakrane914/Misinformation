"""Render fresh native source captures on all four pages; not agent research acceptance.

Uses the exact captured inspection objects, not invented article text. The report
scaffold is a labeled display harness, not a native agent investigation or API
response. External resources are blocked except the supplied pinned Chart.js.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--round", type=int, default=2)
    parser.add_argument("--chart-js", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[2]
    source_files = sorted((args.cycle_dir / f"samples_{args.round}").glob("*.json"))
    if not source_files:
        parser.error("No recorded native samples found")
    evidence = []
    for path in source_files:
        for sample in json.loads(path.read_text(encoding="utf-8")):
            inspection = sample["inspection"]
            evidence.append({"title": f"{path.stem.split('_')[0]} — {sample['title']}",
                             "snippet": sample["captured_text"][:350],
                             "evidence_id": inspection["document_id"], "extraction": inspection})
    report = {"summary": "Native source-capture display audit. Not an agent verdict or verified finding.",
              "evidence": {"community": evidence}, "trust": {}}

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root / "frontend")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    chart = args.chart_js.read_bytes()
    rows = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for agent in ("scout-agent", "trending-agent", "brandshield-agent", "personal-watch-agent"):
                page = browser.new_page(viewport={"width": 390, "height": 1000})
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
                page.goto(base + "/" + agent + ".html", wait_until="load")
                page.evaluate("r => {const m=document.createElement('main');m.id='source-text-audit';document.body.append(m);renderUnifiedReport(m,r);}", report)
                for width in (320, 390, 1440):
                    page.set_viewport_size({"width": width, "height": 1000})
                    page.locator("#source-text-audit details").evaluate_all("nodes=>nodes.forEach(n=>n.open=true)")
                    inspector = page.locator("#source-text-audit .ur-ev-inspection").first
                    inspector.evaluate("el=>el.open=false")
                    inspector.locator(":scope > summary").focus()
                    page.keyboard.press("Enter")
                    keyboard = inspector.evaluate("el=>el.open")
                    page.evaluate("async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));}")
                    inspector.evaluate("el=>window.scrollTo({top:el.getBoundingClientRect().top+scrollY-90,behavior:'instant'})")
                    metrics = page.evaluate("""()=>({document_width:document.documentElement.scrollWidth,
                        cards:document.querySelectorAll('#source-text-audit .ur-ev-card').length,
                        inspections:document.querySelectorAll('#source-text-audit .ur-ev-inspection').length,
                        metric_rows:[...document.querySelectorAll('#source-text-audit p')].filter(n=>n.textContent.includes('Retained raw text:')).length,
                        unsafe_links:document.querySelectorAll('#source-text-audit a[href^="javascript:"]').length,
                        clipped_inspections:[...document.querySelectorAll('#source-text-audit .ur-ev-inspection')].filter(n=>n.scrollWidth>n.clientWidth+1).length})""")
                    metrics["clipped_evidence_cards"] = page.evaluate("""()=>[...document.querySelectorAll('#source-text-audit .ur-ev-card')].filter(n=>{
                        const r=n.getBoundingClientRect(), p=n.closest('.ur-section').getBoundingClientRect();
                        return r.right>Math.min(innerWidth,p.right)+1 || r.left<Math.max(0,p.left)-1;
                    }).length""")
                    filename = f"{agent}-{width}.png"
                    page.screenshot(path=str(args.output_dir / filename))
                    rows.append({"agent": agent, "width": width, "keyboard_open": keyboard,
                                 "page_errors": list(errors), "screenshot": filename, **metrics})
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    failures = [r for r in rows if r["page_errors"] or r["document_width"] > r["width"] + 1
                or r["clipped_inspections"] or r["clipped_evidence_cards"] or r["unsafe_links"] or not r["keyboard_open"]
                or r["cards"] != len(evidence) or r["metric_rows"] != len(evidence)]
    result = {"scope": "Exact native captured inspections in a display harness, not four fresh agent/API investigations",
              "native_samples": len(evidence), "states": len(rows), "failed_states": len(failures), "rows": rows,
              "screen_reader": "NOT_VERIFIED", "contrast": "NOT_MEASURED", "axe": "NOT_RUN"}
    (args.output_dir / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("scope", "native_samples", "states", "failed_states")}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
