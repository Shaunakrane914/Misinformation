'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const { renderUnifiedReport, fetchAndRenderReport, sourceReadRequest } = require(
  path.resolve(__dirname, '../../frontend/unified-report-renderer.js')
);

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
} }] } });
assert(inspectionMount.innerHTML.includes('Inspect captured passages'));
assert(inspectionMount.innerHTML.includes('Remote source completeness: unknown'));
assert(inspectionMount.innerHTML.includes('published_at'));
assert(inspectionMount.innerHTML.includes('was truncated'));
assert(!inspectionMount.innerHTML.includes(attack));
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
