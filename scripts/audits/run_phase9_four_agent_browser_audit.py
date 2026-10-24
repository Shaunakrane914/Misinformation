"""Chromium button -> SSE -> native/shared report acceptance.

One fresh request per fixed input; both viewport captures use that same result.
Explicit --replay-dir uses saved SSE and blocks additional provider calls.
Replay validates presentation, not fresh acquisition, progress timing or accuracy.
"""
import argparse
import hashlib
import subprocess
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import re
import sys
import threading
import time
from urllib.parse import urlsplit

from dotenv import dotenv_values
from playwright.sync_api import sync_playwright
import uvicorn

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, required=True)
parser.add_argument('--env-file', type=Path, required=True, help='Server-side local configuration, never copied to output')
parser.add_argument('--chart-js', type=Path, required=True, help='Actual pinned Chart.js 4.4.1 asset')
parser.add_argument('--limit', type=int, default=12)
parser.add_argument('--allow-live-ai', action='store_true', help='Separate opt-in; acquisition/replay excludes AI credentials by default')
parser.add_argument('--case', action='append', default=[], help='Up to four explicit unseen controls as agent:input; default is the fixed twelve-case matrix')
parser.add_argument('--replay-dir', type=Path, help='Replay saved SSE events through page buttons; no acquisition, explicitly labeled')
args = parser.parse_args()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=False)
sys.path.insert(0, str(ROOT))


def application_fingerprint():
    digest = hashlib.sha256()
    names = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','backend','frontend'], cwd=ROOT, text=True).splitlines()
    for name in sorted(set(names)):
        path = ROOT / name
        if path.is_file():
            digest.update(name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


initial_application_sha256 = application_fingerprint()
values = dotenv_values(args.env_file)
allowed = ('GEMINI_API_KEY', 'GEMINI_KEY_', 'GROQ_API_KEY', 'YF_API_KEY', 'AGENT_REACH_', 'REDDIT_',
           'AEGIS_REDDIT_', 'EXA_API_KEY', 'TAVILY_API_KEY', 'BRAVE_API_KEY', 'FACTCHECK_API_KEY',
           'SEC_USER_AGENT', 'YOUTUBE_API_KEY', 'GITHUB_TOKEN', 'JINA_API_KEY')
ai_prefixes = ('GEMINI_', 'GROQ_', 'OPENAI_', 'ANTHROPIC_')
if not args.allow_live_ai:
    for key in list(os.environ):
        if key.startswith(ai_prefixes):
            os.environ[key] = ''
for key, value in values.items():
    os.environ[key] = str(value or '') if key.startswith(allowed) and (args.allow_live_ai or not key.startswith(ai_prefixes)) else ''
for key in list(os.environ):
    if key.startswith(('SUPABASE_', 'TWILIO_', 'SMTP_', 'SENDGRID_', 'RENDER_', 'CLOUDFLARE_')):
        os.environ[key] = ''
os.environ.update(SQLITE_DB_PATH=str(OUT / 'aegis.db'), AEGIS_SQLITE_PATH=str(OUT / 'aegis.db'),
                  AEGIS_DOSSIER_DIR=str(OUT / 'dossiers'), AEGIS_MOCK_LLM='false',
                  ENVIRONMENT='development', AEGIS_ENV='development', RSS_INGESTION_ENABLED='false',
                  LLM_REQUEST_TIMEOUT='5', LLM_MAX_RETRIES='1')
secrets = [str(v) for k,v in values.items() if v and len(str(v)) > 8 and
           any(s in k.upper() for s in ('KEY','TOKEN','SECRET','PASSWORD','COOKIE'))]


class SafeFormatter(logging.Formatter):
    def format(self, record):
        text = super().format(record)
        for value in secrets:
            text = text.replace(value, '[REDACTED]')
        return re.sub(r'([?&](?:key|token|api_key)=)[^&\s]+', r'\1[REDACTED]', text, flags=re.I)


def write_json(path, value):
    text = json.dumps(value, ensure_ascii=False, indent=2)
    for secret in secrets:
        text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'([?&](?:key|token|api_key)=)[^&\s"\\]+', r'\1[REDACTED]', text, flags=re.I)
    path.write_text(text, encoding='utf-8')


handler = logging.FileHandler(OUT / 'backend.log', encoding='utf-8')
handler.setFormatter(SafeFormatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
from backend.main import app
from backend.core.settings import settings

assert not settings.is_mock_llm and not settings.supabase_write_key and not settings.supabase_url
if not args.allow_live_ai:
    assert not settings.gemini_api_keys
config = uvicorn.Config(app, host='127.0.0.1', port=0, lifespan='off', log_config=None, access_log=False)
backend = uvicorn.Server(config)
sock = config.bind_socket()
thread = threading.Thread(target=backend.run, kwargs={'sockets':[sock]}, daemon=True)
thread.start()
for _ in range(150):
    if backend.started:
        break
    time.sleep(.1)
assert backend.started
api_base = 'http://127.0.0.1:' + str(sock.getsockname()[1])


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


static = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'frontend')))
threading.Thread(target=static.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{static.server_port}'
origins = {urlsplit(base).netloc, urlsplit(api_base).netloc}
chart = args.chart_js.read_bytes()
matrix = [{'agent':a, 'input':q} for a, queries in (
    ('scout', ('TATAMOTORS.NS','INFY.NS','AAPL')),
    ('trending', ('OpenAI','NVIDIA','electric vehicles')),
    ('brandshield', ('Nike','Apple','Tata Motors')),
    ('personal_watch', ('Sam Altman','Tim Cook','Satya Nadella')),
) for q in queries][:max(0, min(12,args.limit))]
if args.case:
    if len(args.case) > 4:
        parser.error('At most four explicit control inputs')
    controls = []
    for value in args.case:
        agent, separator, query = value.partition(':')
        if not separator or agent not in {'scout', 'trending', 'brandshield', 'personal_watch'} or not query.strip():
            parser.error('Control must be a supported agent:input')
        controls.append({'agent': agent, 'input': query.strip()})
    matrix = controls
mapping = {'scout':('scout-agent','tickerInput','analyzeBtn'), 'trending':('trending-agent','scanQueryInput','trendingScanBtn'),
           'brandshield':('brandshield-agent','brandInput','scanBtn'), 'personal_watch':('personal-watch-agent','personInput','scanBtn')}
summary = {'scope':f'Actual Chromium page buttons to real local backend SSE; {len(matrix)} new acquisitions, no response or progress stubs. 390/1440px screenshots share one result per input. Startup lifespan/background ingestion off; remote persistence and notifications disabled; external fonts blocked; actual pinned Chart.js served from saved bytes.',
           'configured_gemini_credentials':len(settings.gemini_api_keys), 'mock_llm':settings.is_mock_llm, 'cases':[]}
summary.update(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               dirty_source=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
               application_sha256=initial_application_sha256, llm_timeout_seconds=settings.llm_request_timeout,
               llm_max_retries=settings.llm_max_retries, chart_sha256=hashlib.sha256(chart).hexdigest(),
               independent_entailment_accuracy=None, retrieval_recall=None)
summary['mode'] = 'EXACT_SAVED_SSE_REPLAY' if args.replay_dir else 'LIVE_BROWSER_BACKEND'
if args.replay_dir:
    summary['scope'] = 'Exact saved SSE replay through all agent page buttons; readiness is a harness stub, all other API calls are blocked. No provider, health or fresh research claims.'
print(json.dumps({'api_base':api_base, 'configured_gemini_credentials':summary['configured_gemini_credentials']}), flush=True)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for number, item in enumerate(matrix,1):
            case_id = f"{number:02d}-{item['agent']}"
            filename, field, button = mapping[item['agent']]
            print('UI_START ' + case_id + ' ' + item['input'], flush=True)
            page = browser.new_page(viewport={'width':390,'height':1000}, reduced_motion='reduce')
            page.set_default_timeout(20000)
            page.add_init_script("""(() => {
              const original = window.fetch.bind(window);
              window.auditStream = null;
              window.fetch = async (...args) => {
                const response = await original(...args);
                if (String(args[0]).includes('/stream')) {
                  response.clone().text().then(text => {
                    window.auditStream = {status: response.status, text};
                  }).catch(error => { window.auditStream = {error: String(error)}; });
                }
                return response;
              };
            })();""")
            errors, console_errors, posts = [], [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: console_errors.append(m.text) if m.type == 'error' else None)
            failed_resources = []
            page.on('requestfailed', lambda r: failed_resources.append({'url':urlsplit(r.url)._replace(query='').geturl(), 'failure':r.failure}))
            page.on('request', lambda r: posts.append({'url':urlsplit(r.url).path,'body':r.post_data_json}) if r.method == 'POST' else None)

            def route(request):
                url = request.request.url
                if args.replay_dir and request.request.method == 'POST' and '/stream' in url:
                    saved = json.loads((args.replay_dir / (case_id + '-events.json')).read_text(encoding='utf-8'))
                    body = ''.join('event: ' + event['event'] + '\ndata: ' + json.dumps(event['data']) + '\n\n' for event in saved)
                    request.fulfill(status=200,content_type='text/event-stream',body=body)
                elif args.replay_dir and urlsplit(url).netloc == urlsplit(api_base).netloc:
                    # Exact-response UI replay must not invoke doctor/status
                    # routes or source reads that could touch a provider.
                    readiness = urlsplit(url).path in {'/api/healthz', '/healthz', '/readyz', '/api/readyz'}
                    request.fulfill(status=200 if readiness else 503, content_type='application/json',
                                    body=json.dumps({'status':'ok', 'mode':'REPLAY_READINESS_STUB'} if readiness
                                                    else {'detail':'Unavailable in offline report replay'}))
                elif urlsplit(url).netloc in origins:
                    request.continue_()
                elif url == 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js':
                    request.fulfill(status=200, content_type='application/javascript', body=chart)
                else:
                    request.abort()

            page.route('**/*', route)
            page.goto(f'{base}/{filename}.html', wait_until='load')
            page.evaluate('(api) => { window.getAegisApiUrl = path => api + path; }', api_base)
            # Observe the real progress renderer without replacing its updates,
            # changing event payloads or inventing network timing during replay.
            page.evaluate('''buttonId => {
                window.auditProgress = [];
                const realCreate = window.AegisResearch.createProgress;
                window.AegisResearch.createProgress = (...args) => {
                    const progress = realCreate(...args);
                    if (!progress) return progress;
                    const realUpdate = progress.update;
                    progress.update = event => {
                        realUpdate(event);
                        const work = document.querySelector('[data-r-work]');
                        window.auditProgress.push({completed: event?.pipeline_completed,
                            total: event?.pipeline_total, rendered_value: work?.value,
                            rendered_max: work?.max, button_disabled: document.getElementById(buttonId).disabled});
                    };
                    return progress;
                };
            }''', button)
            page.locator('#' + field).fill(item['input'])
            if item['agent'] == 'trending':
                page.locator('#catSelect').select_option('business' if item['input'] == 'electric vehicles' else 'technology')
            start = time.perf_counter()
            row = {'case_id':case_id, 'agent':item['agent'], 'input':item['input']}
            try:
                with page.expect_response(lambda r: '/stream' in r.url and r.request.method == 'POST', timeout=30000) as info:
                    page.locator('#' + button).click()
                response = info.value
                # Chrome's Network.getResponseBody can reject fetch-consumed SSE.
                # Observe a cloned browser Response without replacing consumption.
                page.wait_for_function('window.auditStream !== null', timeout=270000)
                observed = page.evaluate('window.auditStream')
                if observed.get('error'):
                    raise RuntimeError(observed['error'])
                stream = observed['text']
                row['elapsed_seconds'] = round(time.perf_counter()-start,2)
                row['http_status'] = observed['status']
                events = []
                for block in re.split(r'\r?\n\r?\n', stream):
                    event = next((line[7:] for line in block.splitlines() if line.startswith('event: ')), None)
                    data = next((line[6:] for line in block.splitlines() if line.startswith('data: ')), None)
                    if event and data:
                        events.append({'event':event,'data':json.loads(data)})
                write_json(OUT / (case_id + '-events.json'), events)
                native = next((e['data']['result'] for e in events if e['event']=='result'), {})
                native_records = next((native[key] for key in ('evidence', 'sources')
                                       if isinstance(native.get(key), list)), [])
                body = [str(record.get('content') or record.get('snippet') or '') for record in native_records if isinstance(record,dict)]
                row['retained_native_records'] = len(native_records)
                row['retained_text_words'] = sum(len(text.split()) for text in body)
                row['retained_text_kb'] = round(sum(len(text.encode('utf-8')) for text in body)/1000,3)
                write_json(OUT / (case_id + '.json'), native)
                row['result_event'] = bool(native)
                row['error_events'] = [e['data'] for e in events if e['event']=='error']
                row['progress_events'] = sum(e['event']=='progress' for e in events)
                row['heartbeat_events'] = sum(e['event']=='heartbeat' for e in events)
                row['progress_phases'] = sorted({e['data'].get('phase') for e in events if e['event']=='progress' and e['data'].get('phase')})
                progress_samples = page.evaluate('window.auditProgress')
                row['ui_progress_updates'] = len(progress_samples)
                row['ui_step_mismatches'] = [sample for sample in progress_samples if isinstance(sample.get('total'), int)
                    and (sample.get('completed') != sample.get('rendered_value') or sample['total'] != sample.get('rendered_max'))]
                row['loading_button_observed_disabled'] = any(sample.get('button_disabled') for sample in progress_samples)
                report = native.get('unified_report') or {}
                row['findings'] = len(report.get('findings',[]))
                row['acquired_records'] = sum(len(v) for v in report.get('evidence',{}).values() if isinstance(v,list))
                row['discovery_records'] = len(report.get('discovery',[]))
                report_records = [record for bucket in report.get('evidence', {}).values()
                                  if isinstance(bucket, list) for record in bucket if isinstance(record, dict)]
                expected_sources = {record['evidence_id']: record for record in report_records if record.get('evidence_id')}
                native_ids = {record.get('id') or record.get('evidence_id') for record in native_records}
                native_ids.discard(None)
                row['native_ids_missing_from_report'] = sorted(native_ids - set(expected_sources))
                row['report_ids_missing_from_native'] = sorted(set(expected_sources) - native_ids)
                row['citation_observations'] = [observation for finding in report.get('finding_details', [])
                    if isinstance(finding, dict) for observation in finding.get('citation_observations', [])]
                row['unresolved_finding_citations'] = [entry for entry in row['citation_observations']
                    if entry.get('availability') != 'SOURCE_RECORD']
                row['acquisition_metrics'] = (report.get('processing_notes') or {}).get('acquisition_metrics')
                page.wait_for_function('(id) => !document.getElementById(id).disabled', arg=button,timeout=20000)
                row['views'] = []
                for width in (320,390,1440):
                    page.set_viewport_size({'width':width,'height':1000})
                    page.evaluate('async () => { await document.fonts.ready; await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); }')
                    page.evaluate('window.scrollTo(0,0)')
                    full = case_id + '-' + str(width) + '-full.png'
                    shot = case_id + '-' + str(width) + '-report.png'
                    page.screenshot(path=str(OUT / full),full_page=True)
                    report_node = page.locator('.unified-report')
                    visible = report_node.count()>0 and report_node.is_visible()
                    if visible:
                        report_node.evaluate("el => el.scrollIntoView({block:'start'})")
                        page.evaluate('window.scrollBy(0,-80)')
                    else:
                        page.locator('#' + button).scroll_into_view_if_needed()
                        page.evaluate('window.scrollBy(0,250)')
                    page.screenshot(path=str(OUT / shot))
                    intel = page.locator('#ur-agent-intel')
                    intel_shot = None
                    if intel.count() and intel.is_visible():
                        intel_shot = case_id + '-' + str(width) + '-intelligence.png'
                        intel.evaluate("el=>el.scrollIntoView({block:'start'})")
                        page.evaluate('window.scrollBy(0,-80)')
                        page.screenshot(path=str(OUT / intel_shot))
                    text = page.locator('body').inner_text()
                    (OUT / (case_id + '-' + str(width) + '-text.txt')).write_text(text,encoding='utf-8')
                    trust = page.locator('#ur-trust')
                    trust_shot, trust_text = None, None
                    if trust.count() and trust.is_visible():
                        trust_shot = case_id + '-' + str(width) + '-trust.png'
                        trust_text = trust.inner_text()
                        trust.screenshot(path=str(OUT / trust_shot))
                    inspection = page.locator('#ur-evidence .ur-ev-inspection').first
                    inspection_keyboard = None
                    inspection_shot = None
                    if inspection.count():
                        inspection.locator(':scope > summary').focus()
                        page.keyboard.press('Enter')
                        inspection_keyboard = inspection.evaluate('el=>el.open')
                        inspection.evaluate("el=>window.scrollTo({top:el.getBoundingClientRect().top+scrollY-90,behavior:'instant'})")
                        inspection_shot = case_id + '-' + str(width) + '-inspection.png'
                        page.screenshot(path=str(OUT / inspection_shot))
                        inspection.evaluate('el=>el.open=false')
                    dom_sources = page.locator('#ur-evidence .ur-ev-card').evaluate_all('''cards => cards.map(card => ({
                        id: card.dataset.urEvidenceId,
                        url: card.querySelector('.ur-ev-title')?.getAttribute('href') || '',
                        title: card.querySelector('.ur-ev-title')?.textContent || '',
                        inspection: card.querySelector('.ur-ev-inspection')?.textContent || ''
                    }))''')
                    source_mismatches = []
                    for observed in dom_sources:
                        expected = expected_sources.get(observed['id'])
                        if not expected:
                            source_mismatches.append({'id': observed['id'], 'reason': 'UNKNOWN_SOURCE_ID'})
                            continue
                        if (observed['url'] != (expected.get('url') or '')
                                or expected.get('title') and observed['title'] != expected['title']):
                            source_mismatches.append({'id': observed['id'], 'reason': 'URL_OR_TITLE_MISMATCH'})
                        extraction = expected.get('extraction') or {}
                        digest = extraction.get('captured_text_sha256')
                        if digest and digest not in observed['inspection']:
                            source_mismatches.append({'id': observed['id'], 'reason': 'INSPECTION_HASH_MISMATCH'})
                        for passage in extraction.get('passages', [])[:8]:
                            expected_text = re.sub(r'\s+', ' ', str(passage.get('text') or '')[:600])
                            if expected_text not in re.sub(r'\s+', ' ', observed['inspection']):
                                source_mismatches.append({'id': observed['id'], 'reason': 'INSPECTION_PASSAGE_MISMATCH'})
                    # Full context can be intentionally collapsed; verify it is
                    # retained in DOM separately from actual screenshot paint.
                    normalized = re.sub(r'\s+',' ', report_node.text_content() if visible else '')
                    row['views'].append({'width':width, 'unified_report_visible':visible,
                                         'inspection_keyboard_open':inspection_keyboard,
                                         'inspection_screenshot':inspection_shot,
                                         'intelligence_screenshot':intel_shot,
                                         'trust_screenshot':trust_shot,
                                         'trust_text':trust_text,
                                         'source_identity_mismatches':source_mismatches,
                                         'rendered_findings':page.locator('#ur-findings-body > ul > li').count(),
                                         'rendered_acquired_cards':page.locator('#ur-evidence .ur-ev-card').count(),
                                         'rendered_discovery_cards':page.locator('#ur-discovery .ur-ev-card').count(),
                                         'missing_finding_texts':[f[:100] for f in report.get('findings',[]) if re.sub(r'\s+',' ',f) not in normalized],
                                         'document_width':page.evaluate('document.documentElement.scrollWidth'),
                                         'screenshots':[full,shot]})
            except Exception as error:
                row['error_type'] = type(error).__name__
                row['error_message'] = str(error)[:600]
                row['elapsed_seconds'] = round(time.perf_counter()-start,2)
                page.screenshot(path=str(OUT / (case_id+'-error.png')),full_page=True)
            row.update(page_errors=list(errors),console_errors=list(console_errors),failed_resources=failed_resources,posts=list(posts))
            summary['cases'].append(row)
            write_json(OUT / 'summary.json', summary)
            print('UI_DONE ' + json.dumps({k:v for k,v in row.items() if k not in ('console_errors','views')}),flush=True)
            page.close()
        browser.close()
finally:
    backend.should_exit = True
    thread.join(timeout=30)
    sock.close()
    static.shutdown()
    static.server_close()
print('UI_COMPLETE ' + str(OUT / 'summary.json'),flush=True)
summary['application_unchanged_during_run'] = application_fingerprint() == initial_application_sha256
write_json(OUT / 'summary.json', summary)
failed = not summary['cases'] or any(
    row.get('error_type') or not row.get('result_event') or row.get('error_events') or row.get('page_errors')
    or row.get('ui_step_mismatches') or not row.get('loading_button_observed_disabled')
    or row.get('native_ids_missing_from_report') or row.get('report_ids_missing_from_native')
    or any(not view['unified_report_visible'] or view['missing_finding_texts'] or view.get('inspection_keyboard_open') is False
           or view.get('source_identity_mismatches')
           or view['document_width'] > view['width'] + 1
           or view['rendered_findings'] != row['findings']
           or view['rendered_acquired_cards'] != row['acquired_records']
           or view['rendered_discovery_cards'] != row['discovery_records'] for view in row.get('views',[]))
    for row in summary['cases'])
raise SystemExit(1 if failed or not summary['application_unchanged_during_run'] else 0)
