'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function inlineScript(filename) {
  const html = fs.readFileSync(path.resolve(__dirname, '../../frontend', filename), 'utf8');
  const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
  assert(scripts.length > 0, `${filename} needs an inline controller`);
  return { html, code: scripts.at(-1)[1] };
}

function element() {
  return {
    value: '', innerHTML: '', textContent: '', className: '', style: {},
    addEventListener() {}, scrollIntoView() {}, focus() {},
  };
}

async function checkClaimWorkspace() {
  const { html, code } = inlineScript('submit.html');
  assert(!html.includes('gemini-client.js'));
  assert(!code.includes('window.askGemini'));
  assert(!code.includes('setInterval('));

  const nodes = new Map();
  const document = {
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, element());
      return nodes.get(id);
    },
    addEventListener() {}, querySelector() { return null; },
  };
  const context = {
    document, URL, URLSearchParams, Set,
    window: { location: { search: '' } },
    sessionStorage: { getItem: () => null, removeItem() {} },
    console, setTimeout,
  };
  vm.createContext(context);
  vm.runInContext(code, context, { filename: 'submit.html' });

  const offline = await context.runClientFactCheck('Unverified claim', '');
  assert.equal(offline.verdict, 'INSUFFICIENT_EVIDENCE');
  assert.deepEqual(Array.from(offline.supporting_evidence), []);
  assert.deepEqual(Array.from(offline.refuting_evidence), []);
  context.renderClaimWorkspace('Exact unverified claim', offline);
  assert.equal(document.getElementById('verdictPill').textContent, 'UNRESOLVED');
  assert(!document.getElementById('whyPointsList').innerHTML.includes('Cross-referenced'));

  context.renderClaimWorkspace('Ambiguous claim', {
    verdict: 'UNTRUE', evidence: [{
      text: 'Provider text', url: 'javascript:alert(1)',
    }],
  });
  assert.equal(document.getElementById('verdictPill').textContent, 'UNRESOLVED');
  assert.equal(document.getElementById('refutingCountBadge').textContent, 0);
  assert(document.getElementById('evidenceRowsContainer').innerHTML.includes('Provider text'));
  assert(!document.getElementById('evidenceRowsContainer').innerHTML.includes('href="javascript:'));
  assert(document.getElementById('sourceGroupCounts').textContent.includes('independence unverified'));

  context.renderClaimWorkspace('Unsupported decisive claim', {
    verdict: 'TRUE', evidence_strength: 'Strong', explanation: 'Claim is proved.',
    supporting_evidence: [{ text: 'Unlinked summary' }],
  });
  assert.equal(document.getElementById('verdictPill').textContent, 'UNRESOLVED');
  assert.equal(document.getElementById('strengthPill').textContent, 'Evidence: Insufficient');
  assert(document.getElementById('bottomLineText').textContent.includes('no inspectable source passage'));

  context.renderClaimWorkspace('Cited decisive claim', {
    verdict: 'TRUE', supporting_evidence: [{
      text: 'Observed publication passage', url: 'https://example.org/publication',
    }],
  });
  assert.equal(document.getElementById('verdictPill').textContent, 'SUPPORTED');
}

function checkInvestigatorGateway() {
  const { html, code } = inlineScript('investigator-agent.html');
  assert(!html.includes('gemini-client.js'));
  assert(!html.includes('Zero official filings'));
  assert(!code.includes('Math.random'));
  assert(!code.includes('askGemini'));

  const nodes = new Map();
  const storage = new Map();
  let destination = '';
  const document = {
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, element());
      return nodes.get(id);
    },
  };
  const context = {
    document,
    sessionStorage: { setItem: (key, value) => storage.set(key, value) },
    window: { location: { assign: value => { destination = value; } } },
  };
  vm.createContext(context);
  vm.runInContext(code, context, { filename: 'investigator-agent.html' });
  let submitted = false;
  document.getElementById('investigatorForm').addEventListener = (event, callback) => {
    assert.equal(event, 'submit');
    document.getElementById('investigatorForm').submit = callback;
  };
  // The controller binds its listener at load; rerun after attaching the spy.
  vm.runInContext(code, context, { filename: 'investigator-agent.html' });
  document.getElementById('caseInput').value = 'Exact claim about a filing';
  document.getElementById('investigatorForm').submit({ preventDefault() { submitted = true; } });
  assert(submitted);
  assert.equal(storage.get('aegis_pending_claim'), 'Exact claim about a filing');
  assert.equal(destination, 'submit.html');
}

function checkResearchGateway() {
  const { html, code } = inlineScript('research-agent.html');
  assert(!html.includes('gemini-client.js'));
  assert(!code.includes('askGemini'));
  assert(!html.includes('raw_excerpts'));

  const nodes = new Map();
  const storage = new Map();
  let destination = '';
  const document = {
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, element());
      return nodes.get(id);
    },
  };
  document.getElementById('researchEntryForm').addEventListener = (event, callback) => {
    assert.equal(event, 'submit');
    document.getElementById('researchEntryForm').submit = callback;
  };
  const context = {
    document,
    sessionStorage: { setItem: (key, value) => storage.set(key, value) },
    window: { location: { assign: value => { destination = value; } } },
  };
  vm.createContext(context);
  vm.runInContext(code, context, { filename: 'research-agent.html' });
  document.getElementById('researchClaim').value = ' Exact claim about a filing ';
  document.getElementById('researchEntryForm').submit({ preventDefault() {} });
  assert.equal(storage.get('aegis_pending_claim'), 'Exact claim about a filing');
  assert.equal(destination, 'submit.html');
}

checkClaimWorkspace().then(() => {
  checkInvestigatorGateway();
  checkResearchGateway();
  console.log('CLAIM UI TRUTH CONTRACTS PASSED');
}).catch(error => { console.error(error); process.exitCode = 1; });
