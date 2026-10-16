"""Real Chromium checks of recorded API reports and labeled hostile controls.

No live investigation is claimed by browser replay. Output is append-only.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-results", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=False)
    recorded = json.loads(args.api_results.read_text(encoding="utf-8"))
    pages = {"scout": "scout-agent", "trending": "trending-agent",
             "brandshield": "brandshield-agent", "personal_watch": "personal-watch-agent"}
    rows = []
    origin = urlsplit(args.base_url).netloc
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for agent, name in pages.items():
            for width in (320, 390, 1440):
                for mode in ("RECORDED_API", "SYNTHETIC_HOSTILE_INSPECTION"):
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    # Rendering test does not need third-party fonts, APIs or telemetry.
                    page.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).netloc == origin else route.abort())
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(args.base_url.rstrip('/') + '/' + name + '.html', wait_until="load")
                    report = recorded["agents"][agent]["response"].get("unified_report") or {}
                    if mode == "SYNTHETIC_HOSTILE_INSPECTION":
                        attack = '<img src=x onerror="alert(1)">'
                        report = {"summary": "SYNTHETIC TEST ONLY — not research evidence", "evidence": {"community": [{
                            "title": attack, "url": "https://news.ycombinator.com/item?id=8863", "extraction": {
                                "content_depth": "METADATA", "evidentiary_use": "DISCOVERY_ONLY",
                                "captured_chars": 600, "missing_fields": ["published_at"],
                                "passages": [{"id": "TEST_" + "x" * 1000, "start": 0, "end": len(attack), "text": attack}],
                                "observed_numeric_mentions": [{"text": "12.5", "context": attack}],
                                "page_observations": {"tables": [[[attack, "x" * 1000]]]},
                            },
                        }]}}
                    page.evaluate("""report => {
                      const main = document.createElement('main'); main.id='phase9-inspector-test';
                      document.body.append(main); renderUnifiedReport(main, report);
                    }""", report)
                    source_read_control = None
                    if mode == "SYNTHETIC_HOSTILE_INSPECTION":
                        requests = []

                        def follow_up(route):
                            requests.append(route.request.post_data_json)
                            route.fulfill(status=200, content_type="application/json", body=json.dumps({
                                "status": "SUCCESS", "evidence": [{"title": attack, "snippet": attack,
                                    "url": "javascript:alert(1)", "extraction": {"passages": [{"text": attack}]}}],
                            }))
                        page.route("**/api/agent-reach/extract", follow_up)
                        button = page.locator('#phase9-inspector-test [data-ur-read-page]').first
                        button.click()
                        page.locator('#phase9-inspector-test [data-ur-read-result]').first.get_by_text('Follow-up SUCCESS', exact=False).wait_for()
                        source_read_control = (len(requests) == 1 and requests[0].get("platform") == "hackernews"
                                               and requests[0].get("mode") == "deep"
                                               and page.locator('#phase9-inspector-test [data-ur-read-page]').count() == 1)
                    inspectors = page.locator('#phase9-inspector-test .ur-ev-inspection > summary')
                    keyboard = None
                    if inspectors.count():
                        # Discovery candidates have an outer disclosure. Expose
                        # ancestors, but leave the inspected disclosure closed
                        # so Enter still tests its actual keyboard behavior.
                        inspectors.first.evaluate("""el => {
                            for (let parent = el.parentElement.parentElement; parent; parent = parent.parentElement) {
                                if (parent.tagName === 'DETAILS') parent.open = true;
                            }
                        }""")
                        inspectors.first.focus()
                        page.keyboard.press("Enter")
                        keyboard = inspectors.first.evaluate("el => el.parentElement.open")
                        page.locator('#phase9-inspector-test details details').evaluate_all("els => els.forEach(el => el.open = true)")
                        inspectors.first.scroll_into_view_if_needed()
                    metrics = page.evaluate("""() => ({document_width:document.documentElement.scrollWidth,
                        unsafe_links:document.querySelectorAll('#phase9-inspector-test a[href^="javascript:"]').length,
                        injected_images:document.querySelectorAll('#phase9-inspector-test img[onerror]').length})""")
                    screenshot = f"{agent}-{width}-{mode}.png"
                    page.screenshot(path=str(args.output_root / screenshot))
                    rows.append({"agent": agent, "width": width, "mode": mode, "page_errors": list(errors),
                                 "inspector_count": inspectors.count(), "keyboard_open": keyboard,
                                 "synthetic_source_read_control": source_read_control,
                                 "screenshot": screenshot, **metrics})
                    page.close()
        browser.close()
    result = {"scope": "Recorded real API replay plus labeled synthetic inspector controls, not fresh browser/API integration",
              "manual_screen_reader": "NOT_VERIFIED", "axe": "NOT_RUN", "records": rows}
    (args.output_root / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    failed = [row for row in rows if row["page_errors"] or row["document_width"] > row["width"] + 1
              or row["unsafe_links"] or row["injected_images"] or row["keyboard_open"] is False
              or row["synthetic_source_read_control"] is False]
    print(f"Browser states: {len(rows)}; failed: {len(failed)}; outputs: {args.output_root}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
