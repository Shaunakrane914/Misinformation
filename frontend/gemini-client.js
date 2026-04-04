/**
 * gemini-client.js
 * Shared Gemini API client with 3-key round-robin rotation.
 * Handles 429 retries automatically.
 * Called directly from the browser — no backend needed.
 */

window.GeminiClient = (() => {
  const KEYS = [
    'AIzaSyCVA75lunDwCY17CmYPbXnTdUNzCU0l28g',
    'AIzaSyDkpPh_APxjOvufzZ8gRink760teECAaeI',
    'AIzaSyBTuOZbc4WA-KJH_sgGRh2s2wMyXsfZFdQ'
  ];
  const MODEL = 'gemini-2.5-flash';
  const BASE_URL = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`;

  let keyIndex = 0;
  function nextKey() {
    const key = KEYS[keyIndex % KEYS.length];
    keyIndex++;
    return key;
  }

  /**
   * Call Gemini with a prompt. Rotates keys on 429.
   * Returns the text string response.
   */
  async function ask(prompt, maxRetries = 6) {
    let lastError = null;
    for (let i = 0; i < maxRetries; i++) {
      const key = nextKey();
      try {
        const res = await fetch(`${BASE_URL}?key=${key}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
        });
        if (res.status === 429) {
          console.warn(`[GeminiClient] 429 on key ...${key.slice(-6)}, rotating`);
          await sleep(600);
          lastError = new Error('429');
          continue;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        return data?.candidates?.[0]?.content?.parts?.[0]?.text || '';
      } catch (e) {
        lastError = e;
        await sleep(400);
      }
    }
    throw lastError || new Error('Gemini: all retries exhausted');
  }

  /**
   * Ask Gemini and parse the response as JSON.
   * Strips markdown code fences before parsing.
   */
  async function askJSON(prompt) {
    const raw = await ask(prompt);
    const cleaned = raw
      .replace(/^```json\s*/i, '')
      .replace(/^```\s*/i, '')
      .replace(/\s*```$/i, '')
      .trim();
    try {
      return JSON.parse(cleaned);
    } catch (e) {
      // Try extracting first JSON object/array
      const match = cleaned.match(/(\[[\s\S]*\]|\{[\s\S]*\})/);
      if (match) return JSON.parse(match[1]);
      throw new Error('JSON parse failed: ' + cleaned.slice(0, 100));
    }
  }

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  return { ask, askJSON };
})();
