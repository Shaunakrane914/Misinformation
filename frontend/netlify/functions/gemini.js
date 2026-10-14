// Gemini proxy: only real provider output is returned. Credentials stay server-side.
const MAX_PROMPT_CHARS = 20000;
const MAX_RESPONSE_BYTES = 1000000;
const REQUEST_TIMEOUT_MS = 5000;
const TOTAL_BUDGET_MS = 20000;
const MAX_ATTEMPTS = 6;

async function readBoundedJson(response) {
  if (!response.body || typeof response.body.getReader !== 'function') throw new Error('Provider response is not streamable');
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_RESPONSE_BYTES) throw new Error('Provider response exceeds limit');
      chunks.push(Buffer.from(value));
    }
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

exports.handler = async (event) => {
  const headers = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
  const reply = (statusCode, payload) => ({ statusCode, headers, body: JSON.stringify(payload) });
  const production = String(process.env.ENVIRONMENT || '').trim().toLowerCase() === 'production';
  const origin = event.headers?.origin || event.headers?.Origin;
  const host = event.headers?.host || event.headers?.Host;
  const origins = String(process.env.AEGIS_ALLOWED_ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean);
  if (host) origins.push(`https://${host}`);
  if (!production && host) origins.push(`http://${host}`);
  if (origin) {
    if (!origins.includes(origin)) return reply(403, { status: 'failed', error: 'Origin not allowed' });
    headers['Access-Control-Allow-Origin'] = origin;
    headers.Vary = 'Origin';
  }
  headers['Access-Control-Allow-Headers'] = 'Content-Type';
  headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS';

  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers, body: '' };
  if (event.httpMethod !== 'POST') return reply(405, { error: 'Method not allowed' });
  if (production && String(process.env.AEGIS_MOCK_LLM || '').trim().toLowerCase() === 'true') {
    return reply(503, { status: 'failed', error: 'Mock LLM mode is forbidden in production' });
  }
  if (Buffer.byteLength(event.body || '', 'utf8') > 100000) return reply(413, { error: 'Request exceeds limit' });
  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch (_) { return reply(400, { error: 'Invalid JSON body' }); }
  if (!body || typeof body.prompt !== 'string' || !body.prompt.trim()) return reply(400, { error: 'Missing prompt' });
  if (body.prompt.length > MAX_PROMPT_CHARS) return reply(413, { error: 'Prompt exceeds limit' });

  const keys = [...new Set([
    process.env.GEMINI_KEY_1, process.env.GEMINI_KEY_2, process.env.GEMINI_KEY_3,
    process.env.GEMINI_API_KEY, process.env.GEMINI_API_KEY_1, process.env.GEMINI_API_KEY_2,
  ].filter(Boolean))];
  if (!keys.length) return reply(503, { status: 'failed', error: 'AI provider is not configured' });

  const models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest'];
  const deadline = Date.now() + TOTAL_BUDGET_MS;
  let attempts = 0;
  for (const model of models) {
    for (const key of keys) {
      if (++attempts > MAX_ATTEMPTS || Date.now() >= deadline) break;
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), Math.min(REQUEST_TIMEOUT_MS, deadline - Date.now()));
      try {
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
          method: 'POST', signal: controller.signal,
          headers: { 'Content-Type': 'application/json', 'x-goog-api-key': key },
          body: JSON.stringify({ contents: [{ parts: [{ text: body.prompt }] }] }),
        });
        if (!response.ok) {
          await response.body?.cancel().catch(() => {});
          if (response.status === 404) break;
          continue;
        }
        const data = await readBoundedJson(response);
        const text = data?.candidates?.[0]?.content?.parts?.map(part => part.text || '').join('') || '';
        if (text) return reply(200, { text, model, status: 'success' });
      } catch (_) {
        // Do not echo provider errors: they can include credential-bearing URLs.
      } finally {
        clearTimeout(timeout);
      }
    }
  }
  return reply(503, { status: 'failed', error: 'AI provider is unavailable', retryable: true });
};
