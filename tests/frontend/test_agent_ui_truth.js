'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
const { aegisSafeSourceUrl } = require('../../frontend/safe-source-url.js');

class Element {
  constructor() {
    this._html = ''; this.children = []; this.style = {}; this.className = '';
    this.textContent = ''; this.value = ''; this.dataset = {};
    this.classList = { add() {}, remove() {}, toggle() {} };
  }
  get innerHTML() { return this._html; }
  set innerHTML(value) { this._html = value; this.children = []; }
  insertAdjacentHTML(_position, value) { this._html += value; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; this._html = ''; }
  addEventListener() {}
  querySelector() { return new Element(); }
  scrollIntoView() {}
}

function page(filename) {
  const elements = new Map();
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, new Element());
      return elements.get(id);
    },
    createElement() { return new Element(); },
    createTextNode(value) { return { nodeType: 3, textContent: value }; },
    addEventListener() {}, querySelector() { return new Element(); },
    querySelectorAll() { return []; },
  };
  const context = vm.createContext({
    document, console, URL, URLSearchParams, Date,
    setTimeout, clearTimeout, setInterval, clearInterval,
    AbortController, AbortSignal, addEventListener() {},
    fetch: async () => ({ ok: true, json: async () => ({ channels: {} }) }),
    location: { search: '' },
  });
  context.window = context;
  vm.runInContext(fs.readFileSync(path.join(root, 'frontend/operation-health.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(root, 'frontend/safe-source-url.js'), 'utf8'), context);
  const html = fs.readFileSync(path.join(root, 'frontend', filename), 'utf8');
  for (const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)) {
    if (match[1].trim()) vm.runInContext(match[1], context, { filename });
  }
  return { context, elements, document };
}

function rendered(element) {
  return element.innerHTML + element.children.map(rendered).join('');
}

function testSharedLinkGuard() {
  for (const unsafe of ['javascript:alert(1)', 'data:text/html,hi',
    'https://user:pass@example.org/story', 'not-a-url', 'httpx://example.org']) {
    assert.equal(aegisSafeSourceUrl(unsafe), '');
  }
  assert.equal(aegisSafeSourceUrl('https://example.org/story'), 'https://example.org/story');
}

function testScout() {
  const { context, elements } = page('scout-agent.html');
  context.renderWorkspace({ company_name: 'Acme', stock: {} });
  const html = rendered(elements.get('workspaceRoot'));
  assert(html.includes('NOT ASSESSED'));
  assert(html.includes('currency unreported'));
  assert(html.includes('No rumor findings returned'));
  assert(!html.includes('Daily Close series via Financial REST Provider'));
  assert(!html.includes('Zero coordinated smear campaigns'));
}

function testTrending() {
  const { context, elements } = page('trending-agent.html');
  context.renderClaims([{ claims: [{
    status: 'VERIFIED', claim_text: 'A claim',
    source_urls: ['javascript:alert(1)'], supporting_sources: '<img onerror=alert(1)>',
  }] }]);
  let html = rendered(elements.get('claimsList'));
  assert(html.includes('inspect cited evidence'));
  assert(!html.includes('Corroborated by independent sources'));
  assert(!html.includes('href="javascript:'));
  assert(!html.includes('<img'));

  context.renderClaims([{ claims: [{ status: 'VERIFIED', claim_text: 'A claim', source_urls: ['https://example.org/report'] }] }]);
  assert(rendered(elements.get('claimsList')).includes('href="https://example.org/report"'));
  context.renderTimeline([{ event: 'Event', url: 'javascript:alert(1)' }]);
  assert(!rendered(elements.get('timelineList')).includes('href="javascript:'));
  context.renderTrends([{ topic: 'Sparse trend' }]);
  assert(rendered(elements.get('trendsFeed')).includes('UNMEASURED'));
}

function testBrandShield() {
  const { context, elements } = page('brandshield-agent.html');
  const unsafe = context.renderSourceCards([{
    title: 'Source', has_url: true, url: 'javascript:alert(1)', evidence_id: '<img>',
  }]);
  assert(!unsafe.includes('href="javascript:'));
  assert(!unsafe.includes('<img>'));
  assert(unsafe.includes('Not supplied'));
  const container = new Element();
  context.renderBrandShieldWorkspace({ brand_name: 'Acme', threats: [], review_intel: {} }, container);
  const html = rendered(container);
  assert(html.includes('No source evidence returned'));
  context.renderBrandShieldWorkspace({ brand_name: 'Acme', sources: [{ title: 'A public item' }], threats: [], review_intel: {} }, container);
  assert(rendered(container).includes('INSUFFICIENT EVIDENCE FOR REVIEW SCREENING'));
  assert(!html.includes('No Suspicious Patterns Detected'));
}

function testPersonalWatch() {
  const { context, elements } = page('personal-watch-agent.html');
  context.renderDashboard({ vip_name: 'Public person', threats: [{ title: 'Reported item' }],
    evidence: [{ title: 'Source', url: 'javascript:alert(1)' }], changes: [] });
  const html = rendered(elements.get('resultsMount'));
  assert(html.includes('UNASSESSED'));
  assert(html.includes('Not supplied'));
  assert(!html.includes('Verified OSINT footprint'));
  assert(!html.includes('href="javascript:'));
  assert(html.includes('>0</div>'), 'no change event should be inferred from a threat');
}

testSharedLinkGuard();
testScout();
testTrending();
testBrandShield();
testPersonalWatch();
console.log('AGENT UI TRUTH CONTRACTS PASSED');
