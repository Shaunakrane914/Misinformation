/**
 * gemini-client.js
 * Calls Gemini via the backend API (/api/gemini) or Netlify serverless proxy.
 * NO API keys in client code — keys live securely in environment variables.
 */

window.GeminiClient = (() => {
  const ENDPOINTS = ['/api/gemini', '/.netlify/functions/gemini'];

  /**
   * Call Gemini with a prompt via backend proxy.
   * Returns the text string response.
   */
  async function ask(prompt) {
    let lastError = null;

    for (const ep of ENDPOINTS) {
      try {
        const res = await fetch(ep, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt }),
        });
        if (res.ok) {
          const data = await res.json();
          return data.text || '';
        }
        lastError = new Error(`Proxy error ${res.status}: ${await res.text()}`);
      } catch (err) {
        lastError = err;
      }
    }

    throw lastError || new Error('All Gemini proxy endpoints failed');
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

