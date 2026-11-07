'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../frontend');
const benchmark = fs.readFileSync(path.join(root, 'benchmark.html'), 'utf8');
const body = [...benchmark.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(row => row[1]).find(row => row.includes('DOMContentLoaded'));

async function checkLedger(available) {
  const container = {innerHTML: '', textContent: ''};
  const urls = [];
  let ready;
  const context = vm.createContext({
    window: {getAegisApiUrl: p => 'https://backend.example' + p, escapeHtml: String},
    document: {getElementById: () => container, addEventListener: (_, callback) => { ready = callback; }},
    AbortSignal,
    fetch: async url => { urls.push(url); return {ok: available, json: async () => ({commit: 'recorded-sha', recorded_at: '2026-10-04',
      classification: {test_samples: 2948, metrics: {accuracy: .885, macro_f1: .885, accuracy_95ci: [.873, .896]}},
      reranker: {evaluation: {held_out_queries_count: 7}, raw: {mrr: .2}, reranked: {mrr: 1}}})}; }
  });
  vm.runInContext(body, context); await ready();
  assert(urls.every(url => url.startsWith('https://backend.example/api/')));
  assert(available ? container.innerHTML.includes('2948') : container.textContent.includes('unavailable'));
  assert(!container.innerHTML.includes('SAMPLE RECORDED DOSSIER'));
  assert(!container.innerHTML.includes('Saturation: TRUE'));
}

(async () => {
  await checkLedger(false);
  await checkLedger(true);
  assert(benchmark.includes("window.getAegisApiUrl('/api/system/benchmarks')"));
  assert(benchmark.includes('do not measure live claim accuracy'));
  assert(fs.readFileSync(path.join(root, 'index.html'), 'utf8').includes("window.getAegisApiUrl('/api/system/deployment-status')"));
  const rules = fs.readFileSync(path.join(root, '_redirects'), 'utf8').split('\n').filter(line => line.trim() && !line.trim().startsWith('#'));
  assert(!rules.some(line => /https?:\/\/\S+\s+200\s*$/.test(line)));
  console.log('CLOUDFLARE DIRECT API AND LEDGER EMPTY STATES PASSED');
})().catch(error => { console.error(error); process.exitCode = 1; });
