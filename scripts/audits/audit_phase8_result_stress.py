"""Recorded API replay and clearly synthetic hostile/large-result browser controls."""
import argparse
import copy
import json
from pathlib import Path
import time


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-results", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=False)
    recorded = json.loads(args.api_results.read_text(encoding="utf-8"))
    rows = []
    renderers = {
        "scout": ("scout-agent.html", "d => renderWorkspace(d)", "#workspaceRoot"),
        "trending": ("trending-agent.html", "d => {currentScanData=d; renderTrends(d.trends || []); renderClaims(d.trends || []);}", "#trendsFeed"),
        "brandshield": ("brandshield-agent.html", "d => renderBrandShieldWorkspace(d,document.getElementById('resultsContainer'))", "#resultsContainer"),
        "personal_watch": ("personal-watch-agent.html", "d => renderDashboard(d)", "#resultsMount"),
    }
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, (path, renderer, mount) in renderers.items():
            for mode in ("API_REPLAY", "SYNTHETIC_STRESS"):
                page = browser.new_page(viewport={"width": 320, "height": 800})
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(args.base_url.rstrip("/") + "/" + path, wait_until="load")
                data = copy.deepcopy(recorded["agents"][name]["response"])
                if mode == "SYNTHETIC_STRESS":
                    sources = [{"evidence_id": f"TEST_{i}", "title": "[SYNTHETIC TEST] " + "LongTitle" * 120 + '<img src=x onerror=alert(1)>',
                                "url": "javascript:alert(1)", "platform": "web", "snippet": "Unverified test data", "content_depth": "DIRECT_METADATA", "published_at": ""} for i in range(200)]
                    data["sources"], data["evidence"] = sources, sources
                    data["trends"] = [{"topic": "[SYNTHETIC TEST] " + "LongTopic" * 120, "claims": [{"claim_text": "Unverified hostile control", "status": "UNSUPPORTED", "source_urls": ["javascript:alert(1)"]}]}]
                    data["unified_report"] = None
                start = time.monotonic()
                error = None
                try:
                    page.evaluate(renderer, data)
                    render_ms = round((time.monotonic() - start) * 1000, 2)
                    page.locator(mount).scroll_into_view_if_needed()
                    page.wait_for_timeout(900)
                    metrics = page.evaluate("""() => ({width:innerWidth, document_width:document.documentElement.scrollWidth,
                      unsafe_links:document.querySelectorAll('a[href^="javascript:"]').length,
                      injected_images:document.querySelectorAll('img[onerror]').length,
                      overflow:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1 && e.getBoundingClientRect().left>=0 && getComputedStyle(e).position !== 'fixed').slice(0,20).map(e=>({id:e.id,cls:e.className,text:(e.innerText||'').slice(0,90)}))})""")
                    screenshot = f"{name}-{mode}-320.png"
                    page.screenshot(path=str(args.output_root / screenshot))
                    axe = None
                    if args.axe_script:
                        page.add_script_tag(path=str(args.axe_script))
                        checks = page.evaluate("async () => axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})")
                        axe = {"violations": [{"id": v["id"], "targets": [n["target"] for n in v["nodes"]]} for v in checks["violations"]], "incomplete": [v["id"] for v in checks["incomplete"]]}
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    metrics, screenshot, axe, render_ms = {}, None, None, None
                rows.append({"agent": name, "mode": mode, "error": error, "page_errors": list(errors), "render_ms": render_ms, "screenshot": screenshot, "axe": axe, **metrics})
                page.close()
        browser.close()
    result = {"scope": "320px recorded live-API replay plus synthetic 200-record/long-title/hostile-link controls. No manual screen reader.", "records": rows}
    (args.output_root / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if any(r["error"] or r["page_errors"] or r.get("document_width", 0) > 321 or r.get("unsafe_links") or r.get("injected_images") or (r["axe"] and r["axe"]["violations"]) for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
