/* Shared cold-start handling and server-observed research progress. No simulated ETA. */
(function (root) {
  'use strict';
  const STARTUP_MS = 90000;
  const ANALYSIS_MS = 300000;
  const PHASES = { accepted: 0, analysis: 1, report: 2 };
  const LABELS = { accepted: 'Request accepted', analysis: 'Running agent research', report: 'Assembling the report' };
  const api = path => typeof root.getAegisApiUrl === 'function' ? root.getAegisApiUrl(path) : path;

  function createProgress(target, options = {}) {
    const mount = typeof target === 'string' ? document.querySelector(target) : target;
    if (!mount) return null;
    mount.innerHTML = `<section class="research-progress agent-progress-box">
      <h3 data-r-title></h3><p data-r-status role="status" aria-live="polite">Connecting to the backend; a free server may need to wake.</p>
      <label>Overall confirmed stages <span data-r-count>0 / 3</span>
        <progress data-r-overall max="3" aria-label="Confirmed overall stages"></progress></label>
      <p>Stages have different durations. This bar is not a time-remaining estimate.</p>
      <div data-r-pass hidden><label data-r-step></label>
        <progress data-r-work max="13" value="0" aria-label="Confirmed steps in this research pass"></progress>
        <p>Each pass is counted separately; completing a pass does not mean the whole analysis is complete.</p></div>
      <p><span data-r-elapsed>0s elapsed</span> · Startup wait: up to 90s · Analysis wait: up to 5 minutes</p>
      <details data-r-debug><summary>Connection diagnostics</summary><pre data-r-diagnostics></pre></details>
    </section>`;
    const find = name => mount.querySelector(`[data-r-${name}]`);
    find('title').textContent = options.title || 'Research progress';
    const started = Date.now();
    const diagnostic = { phase: 'startup', analysis_id: 'Not assigned', last_backend_event: 'None', http_status: null };
    const passes = new Map();
    let stopped = false;
    const refresh = () => {
      find('elapsed').textContent = `${Math.floor((Date.now() - started) / 1000)}s elapsed`;
      find('diagnostics').textContent = JSON.stringify(diagnostic, null, 2);
    };
    const timer = setInterval(refresh, 1000);
    function update(event = {}) {
      if (stopped) return;
      if (event.phase) diagnostic.phase = event.phase;
      if (event.http_status) diagnostic.http_status = event.http_status;
      for (const key of ['startup_attempt', 'startup_http_status', 'startup_error', 'backend_status']) {
        if (event[key] != null) diagnostic[key] = event[key];
      }
      if (event.analysis_id) diagnostic.analysis_id = event.analysis_id;
      if (event.elapsed_seconds != null) diagnostic.backend_elapsed_seconds = event.elapsed_seconds;
      if (event.analysis_id) diagnostic.last_backend_event = new Date().toISOString();
      if (Object.hasOwn(PHASES, event.phase)) {
        find('overall').value = PHASES[event.phase];
        find('count').textContent = `${PHASES[event.phase]} / 3`;
        find('status').textContent = LABELS[event.phase];
      }
      if (event.phase === 'legacy') {
        find('overall').removeAttribute('value');
        find('status').textContent = 'This backend has no live-progress support. Waiting for its report; progress is unknown.';
      }
      if (typeof event.pipeline_pass === 'string' && Number.isInteger(event.pipeline_completed) && event.pipeline_total === 13 && event.pipeline_completed >= 0 && event.pipeline_completed <= 13) {
        if (!passes.has(event.pipeline_pass)) passes.set(event.pipeline_pass, passes.size + 1);
        find('pass').hidden = false;
        find('work').value = event.pipeline_completed;
        find('step').textContent = `Research pass ${passes.get(event.pipeline_pass)}: ${event.pipeline_completed} / 13 steps finished — ${event.pipeline_step}`;
        diagnostic.research_step = event.pipeline_step;
        find('status').textContent = event.pipeline_completed === 13 ? 'Research pass finished; agent analysis may still be running.' : `Research: ${event.pipeline_step}`;
        if (event.pipeline_failed) {
          diagnostic.research_pass_incomplete = true;
          find('status').textContent = 'Research pass could not finish. A report, if returned, may have evidence limitations.';
        }
      }
      refresh();
    }
    function stop() { clearInterval(timer); stopped = true; refresh(); }
    return {
      update,
      finish(callback) {
        find('overall').value = 3;
        find('count').textContent = '3 / 3';
        find('status').textContent = 'Report received. Research may be incomplete; inspect the evidence and uncertainty. Completion is not verification.';
        diagnostic.phase = 'complete'; stop();
        const debug = find('debug');
        if (callback) { callback(); mount.appendChild(debug); }
      },
      error(message) {
        diagnostic.phase = 'failed';
        find('status').textContent = message; stop();
      }
    };
  }

  async function consumeStream(response, onEvent) {
    if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) throw new Error('Backend did not return a live-progress stream.');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let pending = '', bytes = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        if (bytes > 32 * 1024 * 1024) throw new Error('Research response exceeded the safe display limit.');
        pending += decoder.decode(value, { stream: true });
        pending = pending.replace(/\r\n/g, '\n');
        let boundary;
        while ((boundary = pending.indexOf('\n\n')) !== -1) {
          const block = pending.slice(0, boundary); pending = pending.slice(boundary + 2);
          const lines = block.split('\n');
          const type = lines.find(line => line.startsWith('event:'))?.slice(6).trim();
          const text = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
          if (!text) continue;
          const data = JSON.parse(text);
          onEvent(type, data);
          if (type === 'error') throw new Error(data.status === 429 ? 'Another scan is still running. Wait before retrying.' : data.status === 504 ? 'Backend observation wait expired. Server work may still continue.' : 'The backend could not finish the report. Server work may still continue.');
          if (type === 'result') {
            if (!data.result || typeof data.result !== 'object' || Array.isArray(data.result)) throw new Error('Backend returned an invalid report.');
            return data.result;
          }
        }
        if (pending.length > 16 * 1024 * 1024) throw new Error('Research event exceeded the safe display limit.');
      }
      throw new Error('Connection ended before a completed report. Server work may still continue.');
    } finally {
      await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
  }

  async function run(path, payload, progress, options = {}) {
    const fetcher = options.fetch || root.fetch.bind(root);
    const started = Date.now();
    let analysisId = 'Not assigned', phase = 'startup', httpStatus = null;
    const update = event => { if (progress) progress.update(event); };
    const startupMs = options.startupMs ?? STARTUP_MS;
    const analysisMs = options.analysisMs ?? ANALYSIS_MS;
    let ready = false, attempts = 0;
    const startupDeadline = Date.now() + startupMs;
    try {
      while (Date.now() < startupDeadline) {
        update({ startup_attempt: ++attempts });
        try {
          const response = await fetcher(api('/api/healthz'), { signal: AbortSignal.timeout(Math.max(1, Math.min(15000, startupDeadline - Date.now()))), cache: 'no-store' });
          update({ startup_http_status: response.status });
          if (response.ok && (await response.json()).status === 'ok') { ready = true; break; }
        } catch (error) {
          update({ startup_error: ['AbortError', 'TimeoutError'].includes(error.name) ? 'Health check timed out' : 'Health request failed' });
        }
        await new Promise(resolve => setTimeout(resolve, Math.min(1000, Math.max(0, startupDeadline - Date.now()))));
      }
      if (!ready) throw new Error('Backend startup wait expired. Check connectivity or Render service status.');
      phase = 'request'; update({ phase });
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), analysisMs);
      const request = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal: controller.signal };
      try {
        let response = await fetcher(api(`${path}/stream`), request);
        httpStatus = response.status; update({ http_status: httpStatus });
        // Safe rollback compatibility: a missing route did not start research.
        // Never resubmit after timeouts, 429, 5xx, or a partially received stream.
        if ([404, 405].includes(response.status)) {
          phase = 'legacy'; update({ phase });
          response = await fetcher(api(path), request);
          httpStatus = response.status; update({ http_status: httpStatus });
          if (!response.ok) throw new Error(`Research request failed (HTTP ${response.status}). No automatic retry was made.`);
          const legacyResult = await response.json();
          if (!legacyResult || typeof legacyResult !== 'object' || Array.isArray(legacyResult)) throw new Error('Backend returned an invalid report.');
          return legacyResult;
        }
        if (!response.ok) throw new Error(response.status === 429 ? 'Another scan is still running. Wait before retrying.' : `Research request failed (HTTP ${response.status}). No automatic retry was made.`);
        return await consumeStream(response, (type, data) => {
          if (typeof data.analysis_id === 'string' && /^[a-f0-9-]{36}$/i.test(data.analysis_id)) analysisId = data.analysis_id;
          if (data.phase) phase = data.phase;
          if (type === 'error') data.backend_status = data.status;
          update(data);
          if (type === 'progress' && data.phase) console.info('[Aegis research]', { analysis_id: analysisId, phase, elapsed_seconds: data.elapsed_seconds });
        });
      } finally { clearTimeout(timeout); }
    } catch (cause) {
      const reason = ['AbortError', 'TimeoutError'].includes(cause.name)
        ? 'Analysis wait expired. This does not prove the backend is down; server work may still continue. Do not repeatedly retry.'
        : cause.name === 'TypeError' ? 'Research connection interrupted. Check network, CORS or proxy availability; server work may still continue.'
        : cause.name === 'SyntaxError' ? 'Backend returned an unreadable research response; no completed report is claimed.' : cause.message;
      const error = new Error(`${reason} Analysis ID: ${analysisId}. Last phase: ${phase}. Elapsed: ${Math.floor((Date.now() - started) / 1000)}s. HTTP: ${httpStatus ?? 'unavailable'}.`);
      if (progress) progress.error(error.message);
      throw error;
    }
  }

  const exported = { createProgress, run, consumeStream, STARTUP_MS, ANALYSIS_MS };
  root.AegisResearch = exported;
  if (typeof module !== 'undefined' && module.exports) module.exports = exported;
})(typeof window !== 'undefined' ? window : globalThis);
