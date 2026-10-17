'use strict';

const assert = require('node:assert/strict');
const vm = require('node:vm');
const path = require('node:path');
const theme = require('node:fs').readFileSync(path.resolve(__dirname, '../../frontend/aegis-theme.css'), 'utf8');
assert(theme.includes('minmax(min(100%, 320px), 1fr)'), 'Claim grid must shrink inside narrow cards; rendered clipping is separately tested');
assert(theme.includes('grid-template-columns: repeat(3, minmax(0, 1fr))'), 'Evidence grid tracks must not expand to unbounded min-content widths');
const { renderUnifiedReport, fetchAndRenderReport, sourceReadRequest } = require(
  path.resolve(__dirname, '../../frontend/unified-report-renderer.js')
);

// Agent pages own helpers named esc/array too. Loading an inline page script
// after the shared renderer must not mutate its escaping or erase zero counts.
const isolated = { window: {} };
vm.createContext(isolated);
vm.runInContext(require('node:fs').readFileSync(path.resolve(__dirname, '../../frontend/unified-report-renderer.js'), 'utf8'), isolated);
vm.runInContext("function esc(s) { return 'PAGE_OVERRIDE'; } function array() { return []; } function renderTimeline() { return 'PAGE_TIMELINE'; }", isolated);
const isolatedMount = { innerHTML: '', querySelectorAll: () => [] };
isolated.window.renderUnifiedReport(isolatedMount, { summary: 'Retained summary', timeline: [{ timestamp: '2026-10-17', description: 'Captured timeline' }], evidence: { primary: [{
  title: 'Captured source', extraction: { evidentiary_use: 'REQUIRES_PASSAGE_REVIEW', missing_fields: [], passages: [] },
}] } });
assert(isolatedMount.innerHTML.includes('Retained summary'));
assert(isolatedMount.innerHTML.includes('0 metadata/unknown-depth records'));
assert(!isolatedMount.innerHTML.includes('PAGE_OVERRIDE'));
assert(isolatedMount.innerHTML.includes('Captured timeline'));
assert(!isolatedMount.innerHTML.includes('PAGE_TIMELINE'));

function mount() {
  return { innerHTML: '', querySelectorAll: () => [] };
}

function interactiveMount() {
  const attributes = {};
  const section = { classList: { toggle: () => true } };
  const button = {
    closest: () => section,
    setAttribute: (name, value) => { attributes[name] = value; },
    addEventListener: (name, callback) => { if (name === 'click') button.click = callback; },
  };
  return { innerHTML: '', querySelectorAll: () => [button], button, attributes };
}

const attack = '<img src=x onerror=alert(1)>';
const report = {
  _meta: { agent: 'claim_verifier', query: `Exact claim ${attack}` },
  summary: `Claim ${attack}`,
  evidence: { primary: [{
    title: attack, snippet: attack, url: 'javascript:alert(1)',
    source: { name: 'Unverified' },
    retrieval_lineage: [{ channel: 'web', backend_id: attack,
      retrieval_mode: 'direct_http', retrieved_at: '2026-10-12T12:00:00Z' }],
  }], independent: [], community: [] },
  trust: {
    quality_tensor: { relevance: 2 },
    query_telemetry: { queries_submitted: 1, queries_succeeded: 0, queries_auth_required: 1,
      execution_log: [{ channel: 'web', status: 'AUTH_REQUIRED' },
        { channel: 'rss', status: 'SUCCESS' }] },
  },
};

const container = mount();
renderUnifiedReport(container, report);
assert(!container.innerHTML.includes(attack));
assert(!container.innerHTML.includes('href="javascript:'));
assert(container.innerHTML.includes('No source URL'));
assert(container.innerHTML.includes('Acquisition trace'));
assert(container.innerHTML.includes('Source grouping is not proof'));
assert(container.innerHTML.includes('required authorization'));
assert(container.innerHTML.includes('Claim under review'));
assert(container.innerHTML.includes('SOURCE COVERAGE'));
assert(container.innerHTML.includes('Observed query outcomes'));
assert(container.innerHTML.includes('aria-controls="ur-summary-body"'));
assert(container.innerHTML.includes('<button type="button" class="ur-heading-button"'));
assert(!container.innerHTML.includes('width:200%'));

const preservationMount = mount();
renderUnifiedReport(preservationMount, {
  findings: ['Observed finding'],
  finding_details: [{ statement: 'Observed finding', epistemic_state: attack,
    citation_observations: [{ evidence_id: attack, availability: 'UNAVAILABLE' }] }],
  discovery: [{ evidence_id: attack, title: attack, snippet: 'Captured index text',
    url: 'javascript:alert(1)', extraction: { evidentiary_use: 'DISCOVERY_ONLY', passages: [] } }],
});
assert(preservationMount.innerHTML.includes('Observed finding'));
assert(preservationMount.innerHTML.includes('<ul class="ur-list">'), 'findings retain the design-system inset');
assert(preservationMount.innerHTML.includes('Captured index text'));
assert(preservationMount.innerHTML.includes('UNAVAILABLE'));
assert(preservationMount.innerHTML.includes('DISCOVERY ONLY'));
assert(!preservationMount.innerHTML.includes(attack));
assert(!preservationMount.innerHTML.includes('href="javascript:'));

const inspectionMount = mount();
renderUnifiedReport(inspectionMount, { evidence: { community: [{ title: 'Observed', extraction: {
  content_depth: 'METADATA', evidentiary_use: 'DISCOVERY_ONLY', captured_chars: 600,
  missing_fields: ['published_at'], provider_truncated: true, passages_omitted: 2,
  passages: [{ id: attack, start: 0, end: 25, text: attack }],
  text_metrics: { raw_words: 200, raw_utf8_bytes: 4000, readable_words: 80, readable_utf8_bytes: 1250,
    selection_method: attack, content_scope: 'article' },
  source_observations: { answer_lookup_status: attack, content_license: 'CC BY-SA 4.0' },
} }] } });
assert(inspectionMount.innerHTML.includes('Inspect captured passages'));
assert(inspectionMount.innerHTML.includes('Remote source completeness: unknown'));
assert(inspectionMount.innerHTML.includes('published_at'));
assert(inspectionMount.innerHTML.includes('was truncated'));
assert(!inspectionMount.innerHTML.includes(attack));
assert(inspectionMount.innerHTML.includes('Retained raw text: 200 words / 4.000 KB'));
assert(inspectionMount.innerHTML.includes('Readable capture: 80 words / 1.250 KB'));
assert(inspectionMount.innerHTML.includes('CC BY-SA 4.0'));
assert(inspectionMount.innerHTML.includes('Text volume does not establish usefulness'));
assert.equal(sourceReadRequest('javascript:alert(1)'), null);
assert.equal(sourceReadRequest('https://x.com/jack/status/20').operation, 'status');
assert.equal(sourceReadRequest('https://www.reddit.com/r/Python/comments/abc/').platform, 'reddit');
assert.equal(sourceReadRequest('https://news.ycombinator.com/item?id=8863').platform, 'hackernews');
assert.equal(sourceReadRequest('https://stackoverflow.com/questions/231767').platform, 'stackexchange');
assert.equal(sourceReadRequest('https://github.com/python/cpython/releases').query, 'python/cpython');
assert.equal(sourceReadRequest('https://github.com.evil/python/cpython').platform, 'web');
assert.equal(sourceReadRequest('https://example.org/?redirect=https://x.com/jack/status/20').platform, 'web');
assert.equal(sourceReadRequest('https://youtu.be/video').operation, 'transcript');
assert.equal(sourceReadRequest('https://www.v2ex.com/t/1000000').query, '1000000');

report.evidence.primary[0].url = 'https://example.org/source?q=1&view=full';
renderUnifiedReport(container, report);
assert(container.innerHTML.includes('href="https://example.org/source?q=1&amp;view=full"'));

const keyboardAccessible = interactiveMount();
renderUnifiedReport(keyboardAccessible, report);
keyboardAccessible.button.click();
assert.equal(keyboardAccessible.attributes['aria-expanded'], 'false');

const many = Array.from({ length: 120 }, (_, index) => ({
  title: `Long headline ${index} ${'x'.repeat(300)}`,
  url: `https://example.org/item/${index}`, source: { name: 'Fixture' },
}));
renderUnifiedReport(container, { evidence: { community: many }, trust: {} });
assert(container.innerHTML.includes('Long headline 119'));

renderUnifiedReport(container, {
  summary: null, findings: { invalid: true },
  evidence: { primary: [null, { title: 'Valid', url: 'data:text/html,attack',
    source: { type: 'publisher', domain: 'example.org' }, retrieval_lineage: [null, { channel: 'web' }] }] },
  disagreements: null, timeline: [null],
  trust: { independent_source_count: 2,
    query_telemetry: { execution_log: { malformed: true }, queries_failed: '<img src=x onerror=alert(1)>' } },
});
assert(container.innerHTML.includes('Valid'));
assert(container.innerHTML.includes('No source URL'));
assert(container.innerHTML.includes('source coverage cannot be verified'));
assert(container.innerHTML.includes('Grouping is heuristic'));
assert(container.innerHTML.includes('Reported domain: example.org'));
assert(container.innerHTML.includes('No contradiction assessment was returned'));
assert(container.innerHTML.includes('No change history was returned'));
assert(!container.innerHTML.includes('<img src=x onerror=alert(1)>'));

renderUnifiedReport(container, {claim_decomposition: [{
  claim_text: 'Example revenue was $50 billion.', verdict: 'REFUTED', confidence: .8,
  is_heuristic: true, rationale: 'Matched period and metric; observed value differs.',
  evidence_citations: [{canonical_url: 'https://example.org/results', source_name: 'Original issuer',
    relevant_excerpt: 'Example revenue was $10 billion. <script>attack()</script>'}],
}], evidence: {}, trust: {}});
assert(container.innerHTML.includes('href="https://example.org/results"'));
assert(container.innerHTML.includes('Matched period and metric'));
assert(container.innerHTML.includes('Uncalibrated heuristic'));
assert(container.innerHTML.includes('&lt;script&gt;attack()&lt;/script&gt;'));
assert(!container.innerHTML.includes('<script>attack()'));

(async () => {
  const previousFetch = global.fetch;
  try {
    global.fetch = async () => ({ ok: true, json: async () => ({ unified_report: {
      summary: 'Wrapped API report', evidence: {}, trust: {},
    } }) });
    await fetchAndRenderReport(container, '/api/claims/verify');
    assert(container.innerHTML.includes('Wrapped API report'));
    global.fetch = async () => ({ ok: true, json: async () => ({ unified_report: null }) });
    await fetchAndRenderReport(container, '/api/claims/verify');
    assert(container.innerHTML.includes('No report data available'));
    global.fetch = async () => ({ ok: true, json: async () => null });
    await fetchAndRenderReport(container, '/api/claims/verify');
    assert(container.innerHTML.includes('No report data available'));
    console.log('UNIFIED REPORT RENDERER PASSED');
  } finally {
    global.fetch = previousFetch;
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
