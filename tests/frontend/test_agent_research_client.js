'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const client = require('../../frontend/agent-research-client.js');
const id = '12345678-1234-1234-1234-123456789012';
const result = { status: 'INSUFFICIENT_EVIDENCE', sources: [] };
const event = (type, data) => `event: ${type}\r\ndata: ${JSON.stringify({ analysis_id: id, ...data })}\r\n\r\n`;
function stream(text, chunkSize = 7) {
  const bytes = new TextEncoder().encode(text);
  return new Response(new ReadableStream({ start(controller) {
    for (let n = 0; n < bytes.length; n += chunkSize) controller.enqueue(bytes.slice(n, n + chunkSize));
    controller.close();
  } }), { headers: { 'Content-Type': 'text/event-stream' } });
}
const healthy = () => Response.json({ status: 'ok' });
const progress = () => ({ events: [], update(data) { this.events.push(data); }, error(message) { this.failure = message; } });

async function tests() {
  assert.equal(client.STARTUP_MS, 90000);
  assert.equal(client.ANALYSIS_MS, 300000);
  const seen = [];
  assert.deepEqual(await client.consumeStream(stream(event('progress', { phase: 'analysis', pipeline_step: '中文' }) + event('result', { result }), 1), (type, data) => seen.push([type, data])), result);
  assert.equal(seen[0][1].pipeline_step, '中文');
  await assert.rejects(client.consumeStream(stream(event('progress', { phase: 'analysis' })), () => {}), /ended before a completed report/);
  await assert.rejects(client.consumeStream(stream(event('error', { status: 500 })), () => {}), /could not finish/);
  await assert.rejects(client.consumeStream(stream(event('result', { result: null })), () => {}), /invalid report/);

  const requests = [], tracker = progress();
  const fetch = async (url, options) => {
    requests.push([url, options]);
    return url.endsWith('healthz') ? healthy() : stream(event('progress', { phase: 'analysis' }) + event('result', { result }));
  };
  assert.deepEqual(await client.run('/api/scout/analyze', { ticker: 'Infosys' }, tracker, { fetch }), result);
  assert.equal(requests.length, 2);
  assert.equal(requests[1][0], '/api/scout/analyze/stream');
  assert.equal(requests[1][1].method, 'POST');
  assert.equal(tracker.failure, undefined);

  for (const status of [429, 500, 503]) {
    let posts = 0;
    const failed = progress();
    await assert.rejects(client.run('/api/trending/scan', {}, failed, { fetch: async url => {
      if (url.endsWith('healthz')) return healthy();
      posts++; return new Response('', { status });
    } }));
    assert.equal(posts, 1, 'Never retry ambiguous or rejected research POSTs');
    assert(failed.failure.includes('HTTP: ' + status));
  }
  let fallback = [];
  const legacy = progress();
  assert.deepEqual(await client.run('/api/personal/scan', {}, legacy, { fetch: async url => {
    fallback.push(url);
    if (url.endsWith('healthz')) return healthy();
    return url.endsWith('/stream') ? new Response('', { status: 404 }) : Response.json(result);
  } }), result);
  assert.equal(fallback.length, 3);
  assert(legacy.events.some(data => data.phase === 'legacy'));

  const timed = progress();
  await assert.rejects(client.run('/api/brandshield/scan', {}, timed, { analysisMs: 15, fetch: async (url, options) => {
    if (url.endsWith('healthz')) return healthy();
    return new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('abort', 'AbortError'))));
  } }), /server work may still continue/);
  assert(timed.failure.includes('Last phase: request'));
  let coldPosts = 0;
  await assert.rejects(client.run('/api/scout/analyze', {}, progress(), { startupMs: 15, fetch: async url => {
    if (!url.endsWith('healthz')) coldPosts++;
    throw new TypeError('network down');
  } }), /startup wait expired/);
  assert.equal(coldPosts, 0);

  class Element {
    constructor() { this.value = null; this.textContent = ''; this.hidden = false; }
    removeAttribute(name) { if (name === 'value') this.value = null; }
  }
  const nodes = new Map();
  const mount = { innerHTML: '', querySelector(key) { if (!nodes.has(key)) nodes.set(key, new Element()); return nodes.get(key); }, appendChild() {} };
  global.document = { querySelector: () => mount };
  const bar = client.createProgress(mount, { title: '<img onerror=alert(1)>' });
  assert(mount.innerHTML.includes('aria-live="polite"'));
  assert(!mount.innerHTML.includes('<img'));
  bar.update({ phase: 'analysis' });
  assert.equal(nodes.get('[data-r-overall]').value, 1);
  bar.update({ pipeline_pass: 'pass1', pipeline_completed: 4, pipeline_total: 13, pipeline_step: '<img>' });
  assert.equal(nodes.get('[data-r-work]').value, 4);
  assert(nodes.get('[data-r-step]').textContent.includes('<img>'));
  bar.update({ elapsed_seconds: 1000 });
  assert.equal(nodes.get('[data-r-work]').value, 4, 'Elapsed time never advances progress');
  bar.error('Failed');
  assert.equal(nodes.get('[data-r-overall]').value, 1, 'Error never claims 100% completion');
  const completed = client.createProgress(mount);
  completed.finish();
  assert.equal(nodes.get('[data-r-overall]').value, 3);
  delete global.document;

  for (const file of ['scout-agent.html', 'trending-agent.html', 'brandshield-agent.html', 'personal-watch-agent.html']) {
    const html = fs.readFileSync(path.resolve(__dirname, '../../frontend', file), 'utf8');
    assert(html.includes('src="agent-research-client.js"'));
    assert(html.includes('AegisResearch.run('));
    assert(!/AbortSignal.timeout\((25000|35000)\)/.test(html));
  }
  console.log('AGENT RESEARCH CLIENT CONTRACTS PASSED');
}
tests().catch(error => { console.error(error); process.exitCode = 1; });
