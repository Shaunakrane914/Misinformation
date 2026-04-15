/**
 * gemini-client.js
 * Calls Gemini via the Netlify serverless proxy (/.netlify/functions/gemini).
 * NO API keys in this file — keys live in Netlify environment variables.
 */

window.GeminiClient = (() => {
  const PROXY_URL = '/.netlify/functions/gemini';

  /**
   * Call Gemini with a prompt via the secure proxy.
   * Returns the text string response.
   */
  async function ask(prompt) {
    const res = await fetch(PROXY_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Gemini proxy error ${res.status}: ${err}`);
    }
    const data = await res.json();
    return data.text || '';
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
      const match = cleaned.match(/(\[[\s\S]*\]|\{[\s\S]*\})/);
      if (match) return JSON.parse(match[1]);
      throw new Error('JSON parse failed: ' + cleaned.slice(0, 100));
    }
  }

  return { ask, askJSON };
})();
