"""Render saved completed SSE in the real frontend. All external requests blocked.

Measurements distinguish first workbench page, viewport text and all paginated
passages. Static hero/form/guide text is outside the measured workspace.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
VIEWPORTS = [(1366, 768), (1440, 900), (1920, 1080), (390, 844)]
PAGES = {"scout": ("scout-agent", "tickerInput", "analyzeBtn", "#workspaceRoot"),
         "brandshield": ("brandshield-agent", "brandInput", "scanBtn", "#resultsContainer"),
         "personal_watch": ("personal-watch-agent", "personInput", "scanBtn", "#resultsMount"),
         "trending": ("trending-agent", "scanQueryInput", "trendingScanBtn", None)}
MEASURE = r"""({rootSelector, knownPassages}) => {
 const words=t=>(t||'').trim().split(/\s+/).filter(Boolean).length;
 const visible=e=>!!(e.getClientRects().length && getComputedStyle(e).visibility!=='hidden');
 const distinct=t=>[...new Set(t.split(/\n+/).map(x=>x.trim()).filter(Boolean))].join('\n');
 const sections=[...document.querySelectorAll('.unified-report .ur-section')];
 if(rootSelector){const root=document.querySelector(rootSelector);
   if(root)for(const child of root.children)if(!child.querySelector('.unified-report')&&!child.matches('.unified-report'))sections.push(child);
 }else{
   for(const id of ['trendsFeed','claimsList','timelineList','evidenceGrid','boxOfficeContent','chartEmptyState']){
     const e=document.getElementById(id);if(e)sections.push(e);
   }
 }
 return sections.filter(visible).map((e,i)=>{
   const r=e.getBoundingClientRect(), text=e.innerText||'';
   const quotes=[...e.querySelectorAll('blockquote')].filter(visible).map(x=>x.innerText.trim());
   const backed=quotes.filter(t=>knownPassages.includes(t));
   const walker=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let node,viewport=0,viewportEvidence=0;
   while(node=walker.nextNode()){
     if(!node.textContent.trim()||!visible(node.parentElement))continue;
     const range=document.createRange();range.selectNodeContents(node);
     const bounds=range.getBoundingClientRect();
     if(bounds.bottom<80||bounds.top>innerHeight)continue;
     for(const word of node.textContent.matchAll(/\S+/g)){
       range.setStart(node,word.index);range.setEnd(node,word.index+word[0].length);
       const rect=range.getBoundingClientRect();
       if(rect.top>=80&&rect.bottom<=innerHeight&&rect.left>=0&&rect.right<=innerWidth){
         viewport++;if(node.parentElement.closest('blockquote'))viewportEvidence++;
       }
     }
   }
   const clips=[...e.querySelectorAll('*')].filter(x=>visible(x)&&
     ['hidden','clip'].includes(getComputedStyle(x).overflowY)&&x.scrollHeight>x.clientHeight+2);
   return {id:e.id||e.className||'native-'+i,name:e.querySelector('h2,h3,h4,.panel-title')?.innerText||e.id||'Native result block',
     width:Math.round(r.width),height:Math.round(r.height),scroll_height:e.scrollHeight,
     dynamic_text_words:words(text),nonduplicate_line_words:words(distinct(text)),
     exact_source_quote_words:words(distinct(backed.join('\n'))),viewport_text_words:viewport,
     viewport_fully_visible_quote_words:viewportEvidence,
     quote_cards:quotes.length,visible_cards:[...e.querySelectorAll('article,.ur-ev-card,.trend-card,.claim-card,.fe-finding-card,.fe-source-accordion,.source-card,.threat-card')].filter(visible).length,
     card_count_basis:'VISIBLE_ARTICLE_SOURCE_FINDING_TREND_CLAIM_SELECTORS; native container blocks separately measured',
     empty_markers:[...e.querySelectorAll('.ur-empty,.ur-list-empty,.ur-ev-empty,.empty-banner')].filter(visible).length,
     has_empty_copy:/No (?:findings|evidence|source|eligible|dated|qualified)|insufficient evidence|unable to retrieve/i.test(text),
     collapsed:e.classList.contains('ur-collapsed'),details_count:e.querySelectorAll('details').length,
     open_details:e.querySelectorAll('details[open]').length,pagination:!!e.querySelector('[data-ur-wb-next]'),
     text_clipping_elements:clips.length,horizontal_overflow:e.scrollWidth>e.clientWidth+2,
     generated_summary_words:null,summary_provenance:'NOT_INFERRED_FROM_PROSE'};
 });
}"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--chart", type=Path, required=True, help="Previously saved pinned Chart 4.4.1 bytes")
    args = parser.parse_args()
    cases = json.loads(args.index.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    chart = args.chart.read_bytes()

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *unused):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT / "frontend")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_port)
    results = []
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for case in cases:
                native = json.loads(Path(case["native_path"]).read_text(encoding="utf-8"))
                events = json.loads(Path(case["events_path"]).read_text(encoding="utf-8"))
                stream = "".join("event: " + e["event"] + "\ndata: " + json.dumps(e["data"]) + "\n\n" for e in events)
                report = native.get("unified_report") or {}
                expected = [p["text"] for p in (report.get("evidence_workbench") or {}).get("passages", [])]
                backgrounds = ((report.get("agent_intelligence") or {}).get("historical_background") or {}).get("sources", [])
                background_text = [s["passage"] for s in backgrounds]
                reference_text = [s['passage'] for s in ((report.get('agent_intelligence') or {}).get('reference_background') or {}).get('sources', [])]
                for width, height in VIEWPORTS:
                    page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
                    errors, posts = [], []
                    page.on("pageerror", lambda error: errors.append(str(error)))

                    def route(request):
                        url = request.request.url
                        cors = {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                                "Access-Control-Allow-Headers": "Content-Type"}
                        if "/api/" in url or urlsplit(url).path in {"/healthz", "/readyz"}:
                            if request.request.method == "OPTIONS":
                                request.fulfill(status=204, headers=cors, body="")
                            elif request.request.method == "POST" and "/stream" in url:
                                posts.append(url)
                                request.fulfill(status=200, headers=cors, content_type="text/event-stream", body=stream)
                            elif any(part in url for part in ("/healthz", "/readyz")):
                                request.fulfill(status=200, headers=cors, content_type="application/json", body='{"status":"ok","mode":"OFFLINE_REPLAY_STUB"}')
                            else:
                                request.fulfill(status=503, headers=cors, content_type="application/json", body='{"detail":"Saved capture only"}')
                        elif url == "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js":
                            request.fulfill(status=200, content_type="application/javascript", body=chart)
                        elif urlsplit(url).netloc == urlsplit(origin).netloc:
                            request.continue_()
                        else:
                            request.abort()

                    page.route("**/*", route)
                    filename, field, button, root = PAGES[case["agent"]]
                    page.goto(origin + "/" + filename + ".html", wait_until="load")
                    page.locator("#" + field).fill(case["input"])
                    if case["agent"] == "trending":
                        category = case.get("category", "general")
                        page.locator("#catSelect").select_option(category)
                    page.locator("#" + button).click()
                    page.wait_for_selector(".unified-report", timeout=30000)
                    page.wait_for_function("id=>!document.getElementById(id).disabled", arg=button)
                    page.evaluate("async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}")
                    workspace = page.locator(root or ".main-grid").first
                    workspace.evaluate("e=>{e.scrollIntoView({block:'start'});scrollBy(0,-80)}")
                    sections = page.evaluate(MEASURE, {"rootSelector": root, "knownPassages": expected + background_text + reference_text})
                    overview = case["id"] + f"-{width}x{height}.png"
                    page.screenshot(path=str(args.output_dir / overview))
                    first = page.locator(".ur-workbench-passage blockquote:visible").all_text_contents()
                    wb = page.locator("#ur-evidence-workbench")
                    layout_trials = []
                    details_ok = None
                    navigation_ok = None
                    if wb.count():
                        wb.evaluate("e=>{e.scrollIntoView({block:'start'});scrollBy(0,-80)}")
                        page.screenshot(path=str(args.output_dir / (case["id"] + f"-{width}x{height}-evidence.png")))
                        details = page.locator('.ur-capture-details').first
                        if details.count():
                            details.locator('summary').click()
                            details_ok = details.evaluate('e=>e.open')
                            details.locator('summary').click()
                            details_ok = details_ok and not details.evaluate('e=>e.open')
                        link = page.locator('[data-evidence-navigation] a[href="#ur-evidence-workbench"]')
                        if link.count():
                            link.click()
                            navigation_ok = wb.evaluate('e=>e.getBoundingClientRect().top>=80&&e.getBoundingClientRect().top<=120')
                        for amount in (1, 2, 4, 8):
                            trial = wb.evaluate(r"""(e,n)=>{
                              const cards=[...e.querySelectorAll('.ur-workbench-passage')];
                              cards.forEach((c,i)=>c.style.display=i<n?'':'none');
                              const kept=cards.slice(0,n),text=kept.map(c=>c.querySelector('blockquote').innerText).join(' ');
                              return {cards:kept.length,evidence_words:text.trim()?text.trim().split(/\s+/).length:0,
                                section_height:Math.round(e.getBoundingClientRect().height),
                                card_height:Math.round(kept.reduce((sum,c)=>sum+c.getBoundingClientRect().height,0)),
                                clipping:kept.some(c=>c.scrollHeight>c.clientHeight+2)};
                            }""", amount)
                            trial["scope"] = "UI_ONLY_SUBSET_OF_GENUINE_FIRST_PAGE_PASSAGES_NOT_NEW_RESEARCH"
                            layout_trials.append(trial)
                            if width == 1440 and amount == 2:
                                page.screenshot(path=str(args.output_dir / (case["id"] + "-layout-two-passages.png")))
                        wb.evaluate("e=>e.querySelectorAll('.ur-workbench-passage').forEach(c=>c.style.display='')")
                    seen = []
                    for unused in range(65):
                        seen.extend(page.locator(".ur-workbench-passage blockquote").all_text_contents())
                        nxt = page.locator("[data-ur-wb-next]")
                        if not nxt.count() or nxt.is_disabled():
                            break
                        nxt.click()
                    normalize = lambda text: " ".join(text.split())
                    older = page.locator("[data-ur-historical-background] blockquote").all_text_contents()
                    references = page.locator('[data-ur-reference-background] blockquote').all_text_contents()
                    row = {"id": case["id"], "agent": case["agent"], "width": width, "height": height,
                           "capture_scope": case.get("capture_scope", "ORIGINAL_SAVED_NATIVE_RESPONSE"),
                           "mode": "OFFLINE_CURRENT_FRONTEND_SAVED_NATIVE_SSE", "sections": sections,
                           "layout_trials": layout_trials,
                           "capture_details_expand_collapse_ok": details_ok, "evidence_navigation_ok": navigation_ok,
                           "first_workbench_page_words": sum(len(t.split()) for t in first),
                           "all_accessible_workbench_words": sum(len(t.split()) for t in seen),
                           "historical_background_words": sum(len(t.split()) for t in older),
                           "reference_background_words": sum(len(t.split()) for t in references),
                           "exact_reference_match": list(map(normalize, references)) == list(map(normalize, reference_text)),
                           "expected_passages": len(expected), "rendered_passages": len(seen),
                           "exact_passages_match": list(map(normalize, seen)) == list(map(normalize, expected)),
                           "exact_background_match": list(map(normalize, older)) == list(map(normalize, background_text)),
                           "page_errors": errors, "stream_posts": len(posts), "overview_screenshot": overview,
                           "horizontal_overflow": page.evaluate("document.documentElement.scrollWidth>innerWidth"),
                           "report_height": page.locator(".unified-report").evaluate("e=>Math.round(e.getBoundingClientRect().height)"),
                           "summary_analysis_words": len((report.get("summary") or "").split()) + sum(len(str(f).split()) for f in report.get("findings", []))}
                    reference_card = page.locator('[data-ur-reference-background]')
                    if reference_card.count():
                        reference_card.evaluate('e => window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 96)')
                        reference_shot = args.output_dir / f"{case['id']}-{width}x{height}-reference.png"
                        page.screenshot(path=str(reference_shot))
                        row['reference_screenshot'] = str(reference_shot)
                    results.append(row)
                    (args.output_dir / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
                    print(json.dumps({k: v for k, v in row.items() if k != "sections"}), flush=True)
                    page.close()
            browser.close()
    finally:
        server.shutdown()
    return int(any(not r["exact_passages_match"] or not r["exact_background_match"] or not r["exact_reference_match"] or r["page_errors"]
                   or r["horizontal_overflow"] or r["evidence_navigation_ok"] is False
                   or r["capture_details_expand_collapse_ok"] is False for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
