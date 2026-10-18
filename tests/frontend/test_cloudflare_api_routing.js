'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../frontend');
const benchmark = fs.readFileSync(path.join(root, 'benchmark.html'), 'utf8');
const body = benchmark.slice(benchmark.indexOf('async function loadLedgerDossiers()'), benchmark.indexOf('async function inspectLiveDossier(id)'));

async function checkLedger(available) {
  const container = {innerHTML: ''};
  const urls = [];
  const context = vm.createContext({
    window: {getAegisApiUrl: p => 'https://backend.example' + p},
    document: {getElementById: () => container},
    AbortSignal,
    fetch: async url => { urls.push(url); return {ok: available, json: async () => ({dossiers: []})}; }
  });
  await vm.runInContext(body + '; loadLedgerDossiers();', context);
  assert(urls.every(url => url.startsWith('https://backend.example/api/')));
  assert(container.innerHTML.includes(available ? 'No recorded dossiers returned.' : 'Live ledger unavailable.'));
  assert(!container.innerHTML.includes('SAMPLE RECORDED DOSSIER'));
  assert(!container.innerHTML.includes('Saturation: TRUE'));
}

(async () => {
  await checkLedger(false);
  await checkLedger(true);
  assert(benchmark.includes('window.getAegisApiUrl(`/api/research/replay/dossiers/${encodeURIComponent(id)}`)'));
  assert(benchmark.includes('window.getAegisApiUrl(`/api/research/replay/reexecute/${encodeURIComponent(id)}`)'));
  assert(fs.readFileSync(path.join(root, 'index.html'), 'utf8').includes("window.getAegisApiUrl('/api/system/deployment-status')"));
  const rules = fs.readFileSync(path.join(root, '_redirects'), 'utf8').split('\n').filter(line => line.trim() && !line.trim().startsWith('#'));
  assert(!rules.some(line => /https?:\/\/\S+\s+200\s*$/.test(line)));
  console.log('CLOUDFLARE DIRECT API AND LEDGER EMPTY STATES PASSED');
})().catch(error => { console.error(error); process.exitCode = 1; });
