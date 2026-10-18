'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..', '..');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this.children = []; this.style = {};
    this.className = ''; this.title = ''; this.innerHTML = ''; this.textContent = '';
    this.value = ''; this.dataset = {}; this.listeners = {};
    this.classList = { add() {}, remove() {}, toggle() {} };
  }
  addEventListener(event, listener) { this.listeners[event] = listener; }
  set innerHTML(value) { this._innerHTML = value; this.children = []; }
  get innerHTML() { return this._innerHTML; }
  querySelector() { if (!this.dot) this.dot = new Element('span'); return this.dot; }
  replaceChildren(...children) { this.children = children; this._innerHTML = ''; }
  appendChild(child) { this.children.push(child); return child; }
}

function pageContext(page) {
  const elements = new Map(); const visibilityListeners = [];
  const document = {
    visibilityState: 'visible',
    getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
    createElement(tag) { return new Element(tag); },
    createTextNode(text) { return { nodeType: 3, textContent: text }; },
    addEventListener(event, listener) { if (event === 'visibilitychange') visibilityListeners.push(listener); },
    querySelector() { return new Element(); },
  };
  const context = vm.createContext({ document, console, setTimeout, clearTimeout, setInterval, clearInterval,
    Date, URL, URLSearchParams, AbortController, AbortSignal, location: { search: '' }, addEventListener() {},
    fetch: async () => ({ ok: true, json: async () => ({ channels: {} }) }),
  });
  context.window = context;
  vm.runInContext(fs.readFileSync(path.join(root, 'frontend', 'operation-health.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(root, 'frontend', 'agent-research-client.js'), 'utf8'), context);
  const runResearch = context.AegisResearch.run;
  context.AegisResearch.run = (endpoint, payload, progress) => runResearch(endpoint, payload, progress, { startupMs: 15 });
  const html = fs.readFileSync(path.join(root, 'frontend', page), 'utf8');
  for (const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)) {
    if (match[1].trim()) vm.runInContext(match[1], context, { filename: page });
  }
  return { context, elements, document, visibilityListeners };
}

function capabilities(state = 'HEALTHY') {
  const op = { runtime_health: state, last_outcome: 'DIRECT_CONTENT', decision: state === 'BLOCKED' ? 'EXCLUDE' : 'PREFER' };
  const operations = { search: op, read: op, comments: op, profile: op, status: op, transcript: op, oembed: op, latest: op, topic: op, replies: op, issues: op, prs: op };
  return { channels: Object.fromEntries(['web', 'rss', 'news', 'reddit', 'twitter', 'youtube', 'bilibili', 'v2ex', 'github', 'instagram'].map(name => [name, { operation_capabilities: operations }])) };
}

async function testPages() {
  const personal = pageContext('personal-watch-agent.html');
  const attack = '<img src=x onerror="globalThis.pwned=true">';
  const button = new Element('button');
  personal.context.setPersonalScanBusy(button, attack);
  assert.strictEqual(button.children[0].tagName, 'SPAN');
  assert.strictEqual(button.children[1].nodeType, 3);
  assert.strictEqual(button.children[1].textContent, ` Auditing ${attack}...`);
  assert.strictEqual(button.innerHTML, '');
  assert.strictEqual(personal.context.pwned, undefined);

  const dashboard = pageContext('scout-agent.html');
  vm.runInContext(fs.readFileSync(path.join(root, 'frontend', 'dashboard.js'), 'utf8'), dashboard.context);
  for (const verdict of ['Unverified', 'Insufficient Evidence']) {
    const card = dashboard.context.buildCard({ claim: 'A claim', verdict, record_origin: 'investigation' });
    assert.strictEqual(card.children[1].textContent, verdict.toUpperCase());
    assert(card.children[1].style.cssText.includes('#8b5cf6'), 'Uncertainty must not use false/red styling');
    assert.strictEqual(card.children[2].textContent, 'Stored investigation result');
  }
  const historical = dashboard.context.buildCard({ claim: 'Example', verdict: 'False', record_origin: 'historical_dataset' });
  assert(historical.children[2].textContent.includes('not a live investigation'));
  vm.runInContext('backendAlive = true;', dashboard.context);
  dashboard.context.fetch = async () => ({ json: async () => ({ explanation: 'Reasoning', evidence_url: 'javascript:globalThis.pwned=true' }) });
  const unsafeLink = dashboard.context.buildCard({ claim: 'Example', verdict: 'Unverified' });
  const evidence = unsafeLink.children[5]; evidence.style.display = 'none';
  await unsafeLink.children[4].listeners.click();
  assert.strictEqual(evidence.children[1].children[0].tagName, 'SPAN');
  assert.strictEqual(dashboard.context.pwned, undefined);
  personal.document.getElementById('personInput').value = attack;
  personal.context.fetch = async () => { throw new Error('API offline'); };
  const scan = personal.context.triggerScan();
  const actualButton = personal.elements.get('scanBtn');
  assert.strictEqual(actualButton.children[1].nodeType, 3);
  assert.strictEqual(actualButton.children[1].textContent, ` Auditing ${attack}...`);
  assert(!actualButton.innerHTML.includes('<img'), 'Actual URL-prefilled scan path must not create markup');
  await scan;
  assert.strictEqual(personal.context.pwned, undefined);

  for (const [page, load, element, isGreen] of [
    ['scout-agent.html', 'loadLiveDoctorStatus', 'agentReachLiveStrip', el => el.innerHTML.includes('channel-pill active')],
    ['trending-agent.html', 'loadTrendingOperationHealth', 'ch_web', el => el.className === 'ch-badge ok'],
  ]) {
    const loaded = pageContext(page);
    const ctx = loaded.context;
    let value = capabilities();
    let error = false;
    ctx.fetch = async () => {
      if (error) throw new Error('API offline');
      return { ok: true, json: async () => value };
    };
    ctx.AegisOperationHealth.configure({ ttlMs: 25 });
    await ctx[load]();
    const badge = loaded.elements.get(element);
    assert(isGreen(badge), `${page}: direct content should start healthy`);
    // Actual page subscription must repaint, not just classify an isolated helper.
    error = true;
    await sleep(45);
    assert(!isGreen(badge), `${page}: failed TTL refresh must remove green`);
    assert((badge.innerHTML + badge.querySelector('.dot-val').textContent).includes('Stale observation'));

    loaded.document.visibilityState = 'hidden';
    value = capabilities('BLOCKED'); error = false;
    await sleep(30);
    loaded.document.visibilityState = 'visible';
    loaded.visibilityListeners.forEach(listener => listener());
    await sleep(10);
    assert(!isGreen(badge));
    assert((badge.innerHTML + badge.querySelector('.dot-val').textContent).includes('Policy blocked'), `${page}: visibility must repaint fresh blocked state`);
    vm.runInContext(page.startsWith('scout') ? 'stopScoutHealthObservation();' : 'stopTrendingHealthObservation();', ctx);
  }
}

(async () => {
  await testPages();
  console.log('FRONTEND SECURITY AND HEALTH REGRESSIONS PASSED');
})().catch(error => { console.error(error); process.exitCode = 1; });
