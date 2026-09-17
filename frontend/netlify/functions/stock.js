// Netlify Serverless Function — Live Stock & Telemetry Proxy
// Fetches Yahoo Finance chart data server-side (avoids browser CORS restrictions)
// Endpoint: /.netlify/functions/stock?ticker=NVDA

const TICKER_MAP = {
  'NVIDIA': 'NVDA',
  'APPLE': 'AAPL',
  'TESLA': 'TSLA',
  'MICROSOFT': 'MSFT',
  'GOOGLE': 'GOOGL',
  'ALPHABET': 'GOOGL',
  'AMAZON': 'AMZN',
  'META': 'META',
  'FACEBOOK': 'META',
  'NETFLIX': 'NFLX',
  'TATA MOTORS': 'TATAMOTORS.NS',
  'TATAMOTORS': 'TATAMOTORS.NS',
  'RELIANCE': 'RELIANCE.NS',
  'INFOSYS': 'INFY.NS',
  'TCS': 'TCS.NS',
  'HDFC': 'HDFCBANK.NS',
  'HDFCBANK': 'HDFCBANK.NS',
  'WIPRO': 'WIPRO.NS',
  'ICICI': 'ICICIBANK.NS',
  'SBI': 'SBIN.NS',
  'ADANI': 'ADANIENT.NS',
};

function normalizeTicker(input) {
  if (!input) return 'NVDA';
  const clean = input.trim().toUpperCase();
  if (TICKER_MAP[clean]) return TICKER_MAP[clean];
  return clean;
}

exports.handler = async (event) => {
  const CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Content-Type': 'application/json',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers: CORS, body: '' };
  }

  let rawTicker = event.queryStringParameters?.ticker || event.queryStringParameters?.symbol;
  if (!rawTicker && event.body) {
    try {
      const b = JSON.parse(event.body);
      rawTicker = b.ticker || b.symbol;
    } catch (_) {}
  }

  const ticker = normalizeTicker(rawTicker || 'NVDA');

  const yUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=5d`;

  try {
    const res = await fetch(yUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 AegisScout/1.0',
        'Accept': 'application/json',
      },
      signal: AbortSignal.timeout(8000),
    });

    if (!res.ok) {
      throw new Error(`Yahoo Finance responded with status ${res.status}`);
    }

    const data = await res.json();
    const result = data?.chart?.result?.[0];
    if (!result) {
      throw new Error(`No chart data returned for ticker ${ticker}`);
    }

    const meta = result.meta || {};
    const indicators = result.indicators?.quote?.[0] || {};
    const closes = (indicators.close || []).filter((p) => p !== null && !isNaN(p));

    const currPrice = meta.regularMarketPrice || (closes.length > 0 ? closes[closes.length - 1] : 0);
    const prevClose = meta.chartPreviousClose || (closes.length >= 2 ? closes[closes.length - 2] : currPrice);

    let dropPercent = 0;
    if (prevClose && prevClose > 0) {
      dropPercent = (((currPrice - prevClose) / prevClose) * 100);
    }

    let zScore = 0;
    if (closes.length >= 3) {
      const avg = closes.reduce((a, b) => a + b, 0) / closes.length;
      const variance = closes.reduce((a, c) => a + Math.pow(c - avg, 2), 0) / closes.length;
      const stdDev = Math.sqrt(variance);
      if (stdDev > 0) {
        zScore = ((currPrice - avg) / stdDev);
      }
    }

    const isCrashing = dropPercent <= -3.0 || zScore <= -2.0;

    return {
      statusCode: 200,
      headers: CORS,
      body: JSON.stringify({
        ticker: meta.symbol || ticker,
        name: meta.longName || meta.shortName || ticker,
        current_price: parseFloat(currPrice.toFixed(2)),
        prev_close: parseFloat(prevClose.toFixed(2)),
        drop_percent: parseFloat(dropPercent.toFixed(2)),
        z_score: parseFloat(zScore.toFixed(2)),
        currency: meta.currency || (ticker.endsWith('.NS') || ticker.endsWith('.BO') ? 'INR' : 'USD'),
        is_crashing: isCrashing,
        timestamp: new Date().toISOString(),
      }),
    };
  } catch (err) {
    // Graceful fallback response
    const isINR = ticker.endsWith('.NS') || ticker.endsWith('.BO');
    return {
      statusCode: 200,
      headers: CORS,
      body: JSON.stringify({
        ticker: ticker,
        name: ticker,
        current_price: 0.0,
        prev_close: 0.0,
        drop_percent: 0.0,
        z_score: 0.0,
        currency: isINR ? 'INR' : 'USD',
        is_crashing: false,
        status: 'Telemetry Standby',
        note: err.message,
      }),
    };
  }
};
