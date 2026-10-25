'use strict';
const assert = require('node:assert/strict');
const { renderUnifiedReport, workbenchPage } = require('../../frontend/unified-report-renderer.js');
const passages = Array.from({length: 25}, (_, index) => ({text: `Exact paragraph ${index}. The source did not confirm the claim.`,
  evidence_id: `ev_${index}`, passage_id: `ps_${index}`, publisher_host: index % 2 ? 'second.example' : 'first.example',
  source_title: index === 0 ? '<img src=x onerror=alert(1)>' : 'Captured report',
  content_role: index % 2 ? 'DISPUTED_CLAIM' : 'FINANCIAL_STATEMENT', source_url: index === 0 ? 'javascript:alert(1)' : 'https://publisher.example/article',
  start: 0, end: 68}));
const workbench = {schema: 'evidence-workbench-v1', passages, accounting: {published_passages: 25, published_unique_words: 325, observed_publisher_hosts: 2}};
assert.equal(workbenchPage(workbench).rows.length, 8);
assert.equal(workbenchPage(workbench, {page: 3}).rows.length, 1);
assert.equal(workbenchPage(workbench, {page: 999}).page, 3);
assert.equal(workbenchPage(workbench, {search: 'paragraph 24'}).rows[0].evidence_id, 'ev_24');
assert.equal(workbenchPage(workbench, {publisher: 'second.example'}).total, 12);
assert.equal(workbenchPage(workbench, {role: 'DISPUTED_CLAIM'}).total, 12);
assert.equal(workbenchPage(workbench, {publisher: 'second.example', role: 'FINANCIAL_STATEMENT'}).total, 0);
const mount = {innerHTML: '', querySelectorAll: () => []};
renderUnifiedReport(mount, {evidence_workbench: workbench});
assert(mount.innerHTML.includes('Showing 1–8 of 25'));
assert(mount.innerHTML.includes('Next passages'));
assert(mount.innerHTML.includes('did not confirm'));
assert(mount.innerHTML.includes('&lt;img'));
assert(!mount.innerHTML.includes('<img'));
assert(!mount.innerHTML.includes('href="javascript:'));
assert(!mount.innerHTML.includes('Exact paragraph 24.'));
assert(mount.innerHTML.includes('20× depth target has not been evaluated'));
assert(mount.innerHTML.includes('<label>Search captured passages'));
console.log('EVIDENCE WORKBENCH PASSED');
