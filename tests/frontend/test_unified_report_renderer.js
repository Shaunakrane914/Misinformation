'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const { renderUnifiedReport, fetchAndRenderReport } = require(
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
  evidence: { primary: [null, { title: 'Valid', url: 'data:text/html,attack' }] },
  disagreements: null, timeline: [null], trust: { query_telemetry: {} },
});
assert(container.innerHTML.includes('Valid'));
assert(container.innerHTML.includes('No source URL'));
assert(container.innerHTML.includes('source coverage cannot be verified'));

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
    console.log('UNIFIED REPORT RENDERER PASSED');
  } finally {
    global.fetch = previousFetch;
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
