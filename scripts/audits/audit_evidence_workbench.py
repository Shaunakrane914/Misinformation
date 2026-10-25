"""Render saved API reports locally; no acquisition, provider, or model calls.

Tests the actual shared renderer on each native agent page at 320/390/1440px.
All non-local browser traffic is blocked. This is report replay, not live UI
submission, fresh discovery, full accessibility certification, or a 20x claim.
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
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output_dir.resolve()
    protected = [root / name for name in ("research", "artifacts", "backend/data/dossiers", "tests/retrieval_benchmark")]
    if output.exists() or any(output == path or output.is_relative_to(path) for path in protected):
        raise ValueError("Use a fresh output directory outside protected data")
    output.mkdir(parents=True, exist_ok=False)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root / "frontend")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = []
    pages = {"scout": "scout-agent.html", "trending": "trending-agent.html",
             "brandshield": "brandshield-agent.html", "personal_watch": "personal-watch-agent.html"}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for path in args.report:
                if path.is_symlink() or path.stat().st_size > 20_000_000:
                    raise ValueError("Reports must be bounded regular files")
                payload = json.loads(path.read_text(encoding="utf-8"))
                report = payload.get("unified_report", payload)
                agent = report["_meta"]["agent"]
                for width in (320, 390, 1440):
                    page = browser.new_page(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    def route(request):
                        url = urlsplit(request.request.url)
                        if url.hostname == "127.0.0.1" and url.port == server.server_port and not url.path.startswith("/api/"):
                            request.continue_()
                        else:
                            request.abort()
                    page.route("**/*", route)
                    page.goto(f"http://127.0.0.1:{server.server_port}/{pages[agent]}", wait_until="networkidle")
                    page.evaluate("""report => {
                        const mount = document.createElement('main'); mount.id = 'workbench-audit';
                        mount.style.cssText = 'max-width:1100px;margin:auto;padding:12px';
                        document.body.replaceChildren(mount);
                        window.renderUnifiedReport(mount, report);
                    }""", report)
                    section = page.locator('#ur-evidence-workbench')
                    section.scroll_into_view_if_needed()
                    expected = report["evidence_workbench"]["passages"]
                    visited = []
                    while True:
                        visited.extend(page.locator('[data-ur-wb-results] blockquote').all_text_contents())
                        next_button = page.locator('[data-ur-wb-next]')
                        if next_button.is_disabled():
                            break
                        next_button.focus()
                        page.keyboard.press("Enter")
                    all_accessible = visited == [row["text"] for row in expected]
                    page.locator('[data-ur-wb-search]').fill("no-such-passage-987654")
                    zero_filter = page.locator('[data-ur-wb-results] blockquote').count() == 0
                    page.locator('[data-ur-wb-search]').fill("")
                    role = expected[0]["content_role"] if expected else None
                    role_filter = True
                    if role:
                        page.locator('[data-ur-wb-role]').select_option(role)
                        expected_role = sum(row["content_role"] == role for row in expected)
                        role_filter = f"of {expected_role} matching" in page.locator('[data-ur-wb-results] [role="status"]').inner_text()
                        page.locator('[data-ur-wb-role]').select_option("")
                    publisher_filter = True
                    if expected and expected[0].get("publisher_host"):
                        publisher = expected[0]["publisher_host"]
                        page.locator('[data-ur-wb-publisher]').select_option(publisher)
                        count = sum(row["publisher_host"] == publisher for row in expected)
                        publisher_filter = f"of {count} matching" in page.locator('[data-ur-wb-results] [role="status"]').inner_text()
                        page.locator('[data-ur-wb-publisher]').select_option("")
                    overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                    section.screenshot(path=str(output / f"{agent}-{width}.png"))
                    results.append({"agent": agent, "width": width, "expected_passages": len(expected),
                        "visited_passages": len(visited), "all_passages_accessible_by_keyboard_pagination": all_accessible,
                        "search_filter": zero_filter, "role_filter": role_filter, "publisher_filter": publisher_filter,
                        "horizontal_overflow": overflow, "page_errors": errors})
                    page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    summary = {"mode": "OFFLINE_SAVED_API_REPORT_RENDERING", "new_provider_calls": 0, "model_calls": 0,
        "external_browser_traffic": "BLOCKED", "states": results,
        "limitations": ["Shared report rendering, not native form submission or fresh acquisition.",
                        "External fonts/resources blocked; no screen-reader or contrast certification."]}
    with (output / "measurements.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
    passed = all(row["all_passages_accessible_by_keyboard_pagination"] and row["search_filter"]
        and row["role_filter"] and row["publisher_filter"] and not row["horizontal_overflow"]
        and not row["page_errors"] for row in results)
    print(json.dumps({"states": len(results), "passed": passed, "output_dir": str(output)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
