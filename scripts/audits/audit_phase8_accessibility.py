"""Run optional axe-core WCAG checks on the four rendered agent pages.

An axe-core distribution must be supplied explicitly; the repository does not
silently install browser tooling. This is an automated check, not a human
screen-reader or usability acceptance test.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from audit_phase8_frontend_rendering import PAGES, VIEWPORTS


def audit(base_url: str, axe_script: Path, output_root: Path) -> dict:
    from playwright.sync_api import sync_playwright

    if not axe_script.is_file():
        raise FileNotFoundError(axe_script)
    if output_root.exists():
        raise FileExistsError(f"Choose a new append-only output directory: {output_root}")
    output_root.mkdir(parents=True)
    records = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for viewport_name, viewport in VIEWPORTS.items():
                page = browser.new_page(viewport=viewport)
                for name in PAGES:
                    page.goto(
                        urljoin(base_url.rstrip("/") + "/", name),
                        wait_until="load", timeout=20000,
                    )
                    height = page.evaluate("document.documentElement.scrollHeight")
                    for offset in range(0, height, viewport["height"]):
                        page.evaluate("offset => window.scrollTo(0, offset)", offset)
                        page.wait_for_timeout(90)
                    page.evaluate(
                        "() => { document.documentElement.style.scrollBehavior = 'auto'; "
                        "window.scrollTo({ top: 0, behavior: 'instant' }); }"
                    )
                    page.wait_for_timeout(650)
                    page.add_script_tag(path=str(axe_script))
                    result = page.evaluate(
                        """async () => axe.run(document, {
                          runOnly: { type: 'tag', values: [
                            'wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa',
                            'wcag22aa', 'best-practice'
                          ] }
                        })"""
                    )
                    records.append({
                        "page": name,
                        "viewport": viewport_name,
                        "violation_count": len(result["violations"]),
                        "incomplete_count": len(result["incomplete"]),
                        "incomplete_rules": [{
                            "id": check["id"],
                            "affected_selectors": [
                                node["target"] for node in check["nodes"]
                            ],
                        } for check in result["incomplete"]],
                        "violations": [{
                            "id": violation["id"],
                            "impact": violation["impact"],
                            "description": violation["description"],
                            "affected_selectors": [
                                node["target"] for node in violation["nodes"]
                            ],
                            "check_data": [{
                                "target": node["target"],
                                "checks": [{
                                    "id": check["id"],
                                    "data": check.get("data"),
                                } for check in node.get("any", []) + node.get("all", [])]
                            } for node in violation["nodes"]],
                        } for violation in result["violations"]],
                    })
                page.close()
        finally:
            browser.close()
    summary = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "scope": "Automated axe-core checks on initial page state only",
        "records": records,
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--axe-script", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    summary = audit(args.base_url, args.axe_script, args.output_root)
    for record in summary["records"]:
        rules = ", ".join(v["id"] for v in record["violations"]) or "none"
        print(
            f"{record['page']} {record['viewport']}: "
            f"violations={record['violation_count']} ({rules}), "
            f"incomplete={record['incomplete_count']}"
        )
    return 0 if all(record["violation_count"] == 0 for record in summary["records"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
