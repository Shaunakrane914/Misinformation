"""Optional real-browser layout smoke for the four agent pages.

Requires an existing Playwright Python install and Chromium browser binary.
Serve ``frontend/`` locally, then pass that base URL. Optional synthetic
contract fixtures are confined to the browser test run and labeled in output;
they are never presented as live evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin


PAGES = (
    "scout-agent.html",
    "trending-agent.html",
    "brandshield-agent.html",
    "personal-watch-agent.html",
)
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844},
    "narrow": {"width": 320, "height": 800},
}
FIXTURE_RENDER = {
    "scout-agent.html": """() => renderWorkspace({
      company_name: '[TEST FIXTURE] Example Company', stock: {}
    })""",
    "trending-agent.html": """() => {
      renderTrends([{ topic: '[TEST FIXTURE] Unverified narrative' }]);
      renderClaims([{ claims: [{ claim_text: '[TEST FIXTURE] A circulating claim',
        status: 'UNVERIFIED', source_urls: ['javascript:alert(1)'] }] }]);
    }""",
    "brandshield-agent.html": """() => renderBrandShieldWorkspace({
      brand_name: '[TEST FIXTURE] Example Brand', threats: [], review_intel: {},
      sources: [{ title: '<img onerror=alert(1)> Test listing',
        url: 'javascript:alert(1)', platform: 'web' }]
    }, document.getElementById('resultsContainer'))""",
    "personal-watch-agent.html": """() => renderDashboard({
      vip_name: '[TEST FIXTURE] Public Subject', threats: [], changes: [],
      evidence: [{ title: '<img onerror=alert(1)> Test mention',
        url: 'javascript:alert(1)', platform: 'web' }],
      subject: { canonical_name: '[TEST FIXTURE] Public Subject',
        candidate_handles: { twitter: '@unverified' }, official_handles: {} }
    })""",
}
FIXTURE_MOUNTS = {
    "scout-agent.html": "#workspaceRoot",
    "trending-agent.html": "#trendsFeed",
    "brandshield-agent.html": "#resultsContainer",
    "personal-watch-agent.html": "#resultsMount",
}
MODAL_OPEN = {
    "scout-agent.html": """() => {
      currentResearchData = { sources: [] }; openWhyDrawer('source', 0);
    }""",
    "trending-agent.html": """() => {
      currentScanData = { trends: [{ trend_id: 'TEST', topic: '[TEST FIXTURE] Topic' }] };
      openDossier(0);
    }""",
    "brandshield-agent.html": """() => {
      activeScanData = { dossiers: [{ dossier_id: 'TEST',
        threat_title: '[TEST FIXTURE] Signal', evidence_chain: [] }] };
      openDossierModal(0);
    }""",
    "personal-watch-agent.html": """() => {
      currentData = { dossiers: [{ threat_id: 'TEST',
        title: '[TEST FIXTURE] Signal', evidence_chain: [] }] };
      openDossier(0);
    }""",
}
MODAL_CLOSED = {
    "scout-agent.html": "document.getElementById('provenanceDrawer').inert",
    "trending-agent.html": "document.getElementById('dossierModal').style.display === 'none'",
    "brandshield-agent.html": "!document.getElementById('dossierModalWrap').innerHTML",
    "personal-watch-agent.html": "!document.getElementById('modalMount').innerHTML",
}
MODAL_SELECTOR = {
    "scout-agent.html": "#provenanceDrawer[role='dialog']",
    "trending-agent.html": "#dossierModal [role='dialog']",
    "brandshield-agent.html": "#dossierModalWrap [role='dialog']",
    "personal-watch-agent.html": "#modalMount [role='dialog']",
}


def audit(
    base_url: str, output_root: Path, test_fixtures: bool = False,
    viewport_filter: str | None = None,
) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright Python is not installed") from exc

    if output_root.exists():
        raise FileExistsError(f"Choose a new append-only output directory: {output_root}")
    output_root.mkdir(parents=True)
    records = []
    fixture_records = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for viewport_name, viewport in VIEWPORTS.items():
                if viewport_filter and viewport_filter != viewport_name:
                    continue
                page = browser.new_page(viewport=viewport, device_scale_factor=1)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                for name in PAGES:
                    errors.clear()
                    response = page.goto(
                        urljoin(base_url.rstrip("/") + "/", name),
                        wait_until="load",
                        timeout=20000,
                    )
                    # Exercise scroll-triggered reveal styles before a full-page
                    # capture; otherwise an automated screenshot can show blank
                    # sections that become visible to an actual scrolling user.
                    height = page.evaluate("document.documentElement.scrollHeight")
                    for offset in range(0, height, viewport["height"]):
                        page.evaluate("offset => window.scrollTo(0, offset)", offset)
                        page.wait_for_timeout(90)
                    guide = page.locator(".agent-guide")
                    if guide.count():
                        guide.scroll_into_view_if_needed()
                        page.wait_for_timeout(600)
                    page.evaluate(
                        "() => { document.documentElement.style.scrollBehavior = 'auto'; "
                        "window.scrollTo({ top: 0, behavior: 'instant' }); }"
                    )
                    page.wait_for_timeout(300)
                    data = page.evaluate(
                        """() => ({
                          viewport_width: window.innerWidth,
                          document_width: document.documentElement.scrollWidth,
                          h1_count: document.querySelectorAll('h1').length,
                          unnamed_buttons: [...document.querySelectorAll('button')]
                            .filter(el => !((el.getAttribute('aria-label') ||
                              el.textContent || '').trim())).length,
                          unnamed_links: [...document.querySelectorAll('a[href]')]
                            .filter(el => !((el.getAttribute('aria-label') ||
                              el.textContent || el.querySelector('img')?.alt || '').trim())).length,
                          images_without_alt: [...document.querySelectorAll('img')]
                            .filter(el => !el.hasAttribute('alt')).length,
                          non_button_presets: [...document.querySelectorAll(
                            '.qchip, .quick-chip, .preset-chips .chip')]
                            .filter(el => el.tagName !== 'BUTTON').length,
                          guide_visible: !document.querySelector('.agent-guide') ||
                            getComputedStyle(document.querySelector('.agent-guide')).opacity === '1',
                          overflow_elements: [...document.querySelectorAll('body *')]
                            .filter(el => el.getBoundingClientRect().right > window.innerWidth + 1)
                            .slice(0, 12).map(el => ({
                              selector: el.id ? `#${el.id}` : `${el.tagName.toLowerCase()}.${el.className || ''}`,
                              right: Math.round(el.getBoundingClientRect().right),
                              text: (el.textContent || '').trim().slice(0, 60),
                              parent: el.parentElement?.className || ''
                            }))
                        })"""
                    )
                    screenshot = f"{name.removesuffix('.html')}-{viewport_name}.png"
                    page.screenshot(path=str(output_root / screenshot), full_page=True)
                    keyboard_disclosure = None
                    if name == "personal-watch-agent.html":
                        toggle = page.locator(".adv-toggle")
                        toggle.focus()
                        page.keyboard.press("Enter")
                        keyboard_disclosure = toggle.get_attribute("aria-expanded") == "true"
                        page.keyboard.press("Enter")
                    records.append(
                        {
                            "page": name,
                            "viewport": viewport_name,
                            "http_status": response.status if response else None,
                            "screenshot": screenshot,
                            "horizontal_overflow": data["document_width"] > data["viewport_width"] + 1,
                            **data,
                            "keyboard_disclosure": keyboard_disclosure,
                            "page_errors": errors[:10],
                        }
                    )
                    if test_fixtures:
                        fixture_error = None
                        try:
                            page.evaluate(FIXTURE_RENDER[name])
                            mount = page.locator(FIXTURE_MOUNTS[name])
                            mount.scroll_into_view_if_needed()
                            for reveal in mount.locator(".ae-reveal").all():
                                if reveal.is_visible():
                                    reveal.scroll_into_view_if_needed()
                                    page.wait_for_timeout(90)
                            page.wait_for_timeout(650)
                            fixture_data = page.evaluate(
                                """selector => {
                                  const mount = document.querySelector(selector);
                                  const reveals = [...mount.querySelectorAll('.ae-reveal')];
                                  return {
                                    visible_text_chars: (mount.innerText || '').length,
                                    document_width: document.documentElement.scrollWidth,
                                    viewport_width: window.innerWidth,
                                    first_reveal_visible: !reveals.length ||
                                      getComputedStyle(reveals[0]).opacity === '1',
                                    injected_img: !!mount.querySelector('img[onerror]'),
                                    javascript_link: !!mount.querySelector('a[href^="javascript:"]'),
                                    overflow_elements: [...document.querySelectorAll('body *')]
                                      .filter(el => el.getBoundingClientRect().right > window.innerWidth + 1)
                                      .slice(0, 12).map(el => ({
                                        selector: el.id ? `#${el.id}` : `${el.tagName.toLowerCase()}.${el.className || ''}`,
                                        right: Math.round(el.getBoundingClientRect().right),
                                        text: (el.textContent || '').trim().slice(0, 60),
                                        parent: el.parentElement?.className || ''
                                      }))
                                  };
                                }""",
                                FIXTURE_MOUNTS[name],
                            )
                            fixture_screenshot = (
                                f"{name.removesuffix('.html')}-{viewport_name}-TEST-FIXTURE.png"
                            )
                            page.evaluate(
                                "() => window.scrollTo({ top: 0, behavior: 'instant' })"
                            )
                            page.wait_for_timeout(120)
                            page.screenshot(
                                path=str(output_root / fixture_screenshot), full_page=True
                            )
                            page.evaluate(MODAL_OPEN[name])
                            modal_open = page.locator(MODAL_SELECTOR[name]).count() == 1
                            modal_close_focused = page.evaluate(
                                "document.activeElement?.getAttribute('aria-label')?.startsWith('Close') === true"
                            )
                            page.keyboard.press("Escape")
                            modal_escape_closed = page.evaluate(MODAL_CLOSED[name])
                            fixture_data.update({
                                "modal_open": modal_open,
                                "modal_close_focused": modal_close_focused,
                                "modal_escape_closed": modal_escape_closed,
                            })
                        except Exception as exc:
                            fixture_error = f"{type(exc).__name__}: {exc}"
                            fixture_data = {}
                            fixture_screenshot = None
                        fixture_records.append({
                            "page": name,
                            "viewport": viewport_name,
                            "fixture_only": True,
                            "screenshot": fixture_screenshot,
                            "error": fixture_error,
                            **fixture_data,
                        })
                    errors.clear()
                page.close()
        finally:
            browser.close()
    result = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "scope": "Initial rendered pages and optional labeled synthetic contract fixtures; no live backend or screen-reader audit",
        "browser": "Playwright Chromium headless",
        "records": records,
        "fixture_records": fixture_records,
    }
    (output_root / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--test-fixtures", action="store_true")
    parser.add_argument("--viewport", choices=VIEWPORTS.keys())
    args = parser.parse_args()
    result = audit(args.base_url, args.output_root, args.test_fixtures, args.viewport)
    for record in result["records"]:
        print(
            f"{record['page']} {record['viewport']}: HTTP {record['http_status']}, "
            f"overflow={record['horizontal_overflow']}, "
            f"unnamed_buttons={record['unnamed_buttons']}, "
            f"unnamed_links={record['unnamed_links']}, "
            f"missing_alt={record['images_without_alt']}, "
            f"non_button_presets={record['non_button_presets']}, "
            f"guide_visible={record['guide_visible']}, "
            f"overflow_selectors={[item['selector'] for item in record['overflow_elements'][:3]]}, "
            f"page_errors={len(record['page_errors'])}"
        )
    for record in result["fixture_records"]:
        print(
            f"TEST FIXTURE {record['page']} {record['viewport']}: "
            f"error={record['error']}, "
            f"visible_chars={record.get('visible_text_chars')}, "
            f"first_reveal_visible={record.get('first_reveal_visible')}"
            f", overflow_selectors={[item['selector'] for item in record.get('overflow_elements', [])[:3]]}"
        )
    initial_pass = all(
        record["http_status"] == 200
        and not record["horizontal_overflow"]
        and record["h1_count"] == 1
        and not record["unnamed_buttons"]
        and not record["unnamed_links"]
        and not record["images_without_alt"]
        and not record["non_button_presets"]
        and record["guide_visible"]
        and record["keyboard_disclosure"] is not False
        and not record["page_errors"]
        for record in result["records"]
    )
    fixture_pass = all(
        not record["error"]
        and record["visible_text_chars"] > 0
        and record["document_width"] <= record["viewport_width"] + 1
        and record["first_reveal_visible"]
        and not record["injected_img"]
        and not record["javascript_link"]
        and record["modal_open"]
        and record["modal_close_focused"]
        and record["modal_escape_closed"]
        for record in result["fixture_records"]
    )
    return 0 if initial_pass and fixture_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
