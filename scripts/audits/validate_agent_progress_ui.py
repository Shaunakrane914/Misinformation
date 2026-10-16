"""Offline Chromium UI/HTTP-stream checks using explicitly synthetic reports.

No provider traffic, secrets, real investigations or production writes. Output
must be new. Requires the optional Playwright package and installed Chromium.
"""

import argparse
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=False)
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    release = threading.Event()
    failure = threading.Event()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(frontend), **kwargs)

        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path.startswith("/api/"):
                payload = {"status": "ok"} if self.path == "/api/healthz" else {"channels": {}}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())
            else:
                super().do_GET()

        def do_POST(self):
            self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 20000))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            def send(kind, data):
                payload = {"analysis_id": "12345678-1234-1234-1234-123456789012", **data}
                self.wfile.write(f"event: {kind}\ndata: {json.dumps(payload)}\n\n".encode())
                self.wfile.flush()

            try:
                send("progress", {"phase": "analysis", "completed": 1, "total": 3})
                send("progress", {"pipeline_pass": "synthetic-pass", "pipeline_completed": 4,
                                  "pipeline_total": 13, "pipeline_step": "Synthetic staged acquisition"})
                if not release.wait(15):
                    return
                if failure.is_set():
                    send("error", {"status": 500})
                else:
                    send("result", {"result": {"status": "TEST_ONLY", "sources": []}})
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    cases = {
        "scout": ("tickerInput", "analyzeStock"),
        "trending": ("scanQueryInput", "runTrendingScan"),
        "brandshield": ("brandInput", "scanBrand"),
        "personal-watch": ("personInput", "triggerScan"),
    }
    rows = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for agent, (field, action) in cases.items():
                    for width in (390, 1440):
                        for fails in (False, True):
                            release.clear()
                            failure.set() if fails else failure.clear()
                            page = browser.new_page(viewport={"width": width, "height": 900})
                            errors = []
                            page.on("pageerror", lambda error: errors.append(str(error)))
                            page.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).netloc == urlsplit(base).netloc else route.abort())
                            page.goto(f"{base}/{agent}-agent.html", wait_until="load")
                            # Isolate progress/transport acceptance from report rendering,
                            # which has separate recorded-API browser coverage.
                            page.evaluate("""() => {
                              window.getAegisApiUrl = path => location.origin + path;
                              window.renderWorkspace = window.renderDashboard = window.renderScanResults =
                                window.renderBrandShieldWorkspace = () => { window.testReportReceived = true; };
                            }""")
                            page.locator(f"#{field}").fill("SYNTHETIC UI TEST ONLY")
                            page.evaluate(f"void {action}()")
                            page.locator('[data-r-step]').filter(has_text="4 / 13").wait_for()
                            assert page.locator('[data-r-overall]').evaluate("element => element.value") == 1
                            page.locator('[data-r-debug] summary').focus()
                            page.keyboard.press("Enter")
                            assert page.locator('[data-r-debug]').evaluate("element => element.open")
                            overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                            assert not overflow
                            page.screenshot(path=str(args.output_root / f"{agent}-{width}-{'error' if fails else 'success'}-SYNTHETIC.png"), full_page=True)
                            release.set()
                            if fails:
                                page.wait_for_function("document.body.textContent.includes('server work may still continue') || document.body.textContent.includes('Server work may still continue')")
                                assert not page.evaluate("Boolean(window.testReportReceived)")
                            else:
                                page.wait_for_function("window.testReportReceived === true")
                            assert not errors, errors
                            rows.append({"agent": agent, "width": width, "scenario": "failure" if fails else "success",
                                         "input": "SYNTHETIC_ONLY", "observed_steps": "4/13", "observed_overall": "1/3",
                                         "overflow": overflow, "page_errors": errors, "keyboard_details": "PASS"})
                            page.close()
            finally:
                browser.close()
    finally:
        release.set()
        server.shutdown()
        server.server_close()
    output = {"mode": "OFFLINE_SYNTHETIC_HTTP_STREAM_UI", "cases": rows,
              "limitations": ["Not live-provider or research-accuracy acceptance", "Not manual screen-reader acceptance"]}
    with (args.output_root / "summary.json").open("x", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)
    print(json.dumps({"cases": len(rows), "status": "PASS", "mode": output["mode"]}))


if __name__ == "__main__":
    main()
