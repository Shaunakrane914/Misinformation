// Netlify Serverless Function — Gemini Proxy
// Keys stored in Netlify environment variables (never in code/git)
// Endpoint: /.netlify/functions/gemini

exports.handler = async (event) => {
  const CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
    'Content-Type': 'application/json',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers: CORS, body: '' };
  }

  // GET: debug endpoint — shows which env vars are present (not values)
  if (event.httpMethod === 'GET') {
    const present = ['GEMINI_KEY_1','GEMINI_KEY_2','GEMINI_KEY_3','GEMINI_API_KEY','GEMINI_API_KEY_1','GEMINI_API_KEY_2']
      .filter(k => !!process.env[k]);
    return { statusCode: 200, headers: CORS, body: JSON.stringify({ present, total: present.length }) };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers: CORS, body: 'Method Not Allowed' };
  }

  // Accept both naming conventions
  const KEYS = [
    process.env.GEMINI_KEY_1,
    process.env.GEMINI_KEY_2,
    process.env.GEMINI_KEY_3,
    process.env.GEMINI_API_KEY,
    process.env.GEMINI_API_KEY_1,
    process.env.GEMINI_API_KEY_2,
  ].filter(Boolean);

  if (KEYS.length === 0) {
    return {
      statusCode: 500, headers: CORS,
      body: JSON.stringify({ error: 'No Gemini keys configured. Set GEMINI_KEY_1, GEMINI_KEY_2, GEMINI_KEY_3 in Netlify env vars.' })
    };
  }

  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: 'Invalid JSON body' }) };
  }

  const prompt = body.prompt;
  if (!prompt) {
    return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: 'Missing prompt' }) };
  }

  // Try models in order: 2.0-flash has highest free quota, 1.5-flash as fallback
  const MODELS = [
    { model: 'gemini-2.0-flash', version: 'v1beta' },
    { model: 'gemini-1.5-flash-latest', version: 'v1' },
    { model: 'gemini-1.5-flash', version: 'v1' },
  ];

  const lastErrors = [];

  for (const { model, version } of MODELS) {
    const BASE_URL = `https://generativelanguage.googleapis.com/${version}/models/${model}:generateContent`;

    for (let i = 0; i < KEYS.length; i++) {
      const key = KEYS[i];
      try {
        const res = await fetch(`${BASE_URL}?key=${key}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
        });

        if (res.status === 429) {
          lastErrors.push(`${model} key${i+1}: 429`);
          await new Promise(r => setTimeout(r, 300));
          continue;
        }

        if (res.status === 404) {
          lastErrors.push(`${model}: 404 not found`);
          break; // try next model
        }

        if (!res.ok) {
          const err = await res.text();
          lastErrors.push(`${model} key${i+1}: ${res.status}`);
          continue;
        }

        const data = await res.json();
        const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || '';
        if (!text) {
          lastErrors.push(`${model} key${i+1}: empty response`);
          continue;
        }

        return {
          statusCode: 200,
          headers: CORS,
          body: JSON.stringify({ text, model }),
        };
      } catch (e) {
        lastErrors.push(`${model} key${i+1}: ${e.message}`);
        continue;
      }
    }
  }

  return {
    statusCode: 503,
    headers: CORS,
    body: JSON.stringify({ error: 'All Gemini models/keys exhausted', details: lastErrors })
  };
};
