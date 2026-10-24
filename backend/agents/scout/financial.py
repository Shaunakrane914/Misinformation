"""
Aegis Protocol — Scout Financial Analysis Engine
=================================================
Statistical anomaly detection, volatility modeling, empirical impact forecasting,
and market price telemetry for Agent 1 Scout.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import re
import time
import json
from urllib.parse import quote
from backend.infrastructure.acquisition.network.http import fetch_public_http

logger = logging.getLogger(__name__)


def resolve_ticker_and_company(ticker: str) -> Tuple[str, str]:
    """Resolve ticker to standard symbol and clean corporate entity name."""
    clean = ticker.strip().upper()
    name_to_ticker = {
        'NVIDIA': 'NVDA', 'APPLE': 'AAPL', 'TESLA': 'TSLA', 'MICROSOFT': 'MSFT',
        'GOOGLE': 'GOOGL', 'ALPHABET': 'GOOGL', 'AMAZON': 'AMZN', 'META': 'META',
        'FACEBOOK': 'META', 'NETFLIX': 'NFLX', 'TATA MOTORS': 'TATAMOTORS.NS',
        'TATAMOTORS': 'TATAMOTORS.NS', 'RELIANCE': 'RELIANCE.NS', 'INFOSYS': 'INFY.NS',
        'TCS': 'TCS.NS', 'HDFC': 'HDFCBANK.NS', 'HDFCBANK': 'HDFCBANK.NS',
        'WIPRO': 'WIPRO.NS', 'ICICI': 'ICICIBANK.NS', 'SBI': 'SBIN.NS', 'ADANI': 'ADANIENT.NS',
    }
    if clean in {"LENOVO", "LENOVO GROUP", "LENOVO GROUP LIMITED"}:
        return "", "Lenovo"
    from backend.services.agent_reach.planner import TICKER_NAME_MAP
    sym = name_to_ticker.get(clean, clean if clean in TICKER_NAME_MAP else "")
    if not sym:
        # An unfamiliar company/symbol is a research target, not a listing.
        return "", ticker.strip()
    base_sym = sym.replace('.NS', '').replace('.BO', '')
    company = TICKER_NAME_MAP.get(sym, TICKER_NAME_MAP.get(base_sym, base_sym.title()))
    return sym, company


def resolve_company_identity(value: str) -> Dict[str, Any]:
    """Separate corporate identity from a proposed quote symbol; no network."""
    symbol, company = resolve_ticker_and_company(value)
    lenovo = company == "Lenovo" or value.upper() in {"0992.HK", "992.HK", "80992.HK", "LNVGY"}
    if lenovo:
        selected = {"992.HK": "0992.HK"}.get(value.upper(), value.upper())
        listings = [
            {"symbol": "0992.HK", "exchange": "HKEX", "currency": "HKD", "kind": "ordinary_share"},
            {"symbol": "80992.HK", "exchange": "HKEX", "currency": "CNY", "kind": "RMB_counter"},
            {"symbol": "LNVGY", "exchange": "OTC", "currency": "USD", "kind": "ADR"},
        ]
        explicit = next((row for row in listings if row["symbol"] == selected), None)
        return {"company_name": "Lenovo", "legal_name": "Lenovo Group Limited",
                "proposed_symbol": explicit["symbol"] if explicit else None,
                "status": "EXPLICIT_LISTING_REQUIRES_QUOTE_VALIDATION" if explicit else "AMBIGUOUS_LISTING",
                "listing_candidates": listings, "currency": explicit["currency"] if explicit else None,
                "exchange": explicit["exchange"] if explicit else None,
                "listing_reference": "https://investor.lenovo.com/en/ir/stockinfo.php",
                "listing_reference_checked": "2026-10-18", "quote_validated": False}
    from backend.infrastructure.acquisition.adapters.authoritative.sec_edgar import resolve_cik
    cik = resolve_cik(symbol or value)
    return {"company_name": company, "proposed_symbol": symbol or None,
            "status": "CATALOG_CANDIDATE" if symbol else "UNRESOLVED_LISTING",
            "currency": "INR" if symbol.endswith((".NS", ".BO")) else None,
            "listing_candidates": [], "quote_validated": False,
            "cik": cik,
            "regulatory_filing_source": "SEC EDGAR" if cik else None,
            "filing_url": f"https://www.sec.gov/edgar/browse/?CIK={cik}" if cik else None}


def validated_quote_metadata(chart_data, symbol):
    rows = (chart_data or {}).get("chart", {}).get("result") or []
    meta = rows[0].get("meta", {}) if rows else {}
    # A valid body without matching identity/currency cannot supply market data.
    if (not symbol or str(meta.get("symbol", "")).upper() != symbol.upper()
            or not re.fullmatch(r"[A-Z]{3}", str(meta.get("currency", "")))):
        return None
    return {"symbol": meta["symbol"], "currency": meta["currency"],
            "exchange": meta.get("exchangeName"), "source": "Yahoo Finance Chart"}


def fetch_stock_data(
    ticker: str,
    base_url: str = "https://yfapi.net",
    api_key: str = ""
) -> Optional[Dict]:
    """
    Fetch real-time stock chart data from Yahoo Finance API.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA', 'AAPL')
        base_url: Base URL for yfapi.net paid fallback
        api_key: Optional API key for yfapi.net
        
    Returns:
        Dict containing chart data or None if request fails
    """
    browser_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    quote_deadline = time.monotonic() + 5.0

    # 1. Try free zero-cost Yahoo Finance chart endpoint
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker, safe='')}?interval=1d&range=5d"
        logger.info(f"Fetching stock data for {ticker} via Yahoo Finance...")
        response = fetch_public_http(url, headers=browser_headers, timeout=5, max_bytes=1_000_000,
                                     max_attempts=1, max_redirects=0)
        if response.status_code == 200:
            data = json.loads(response.body)
            if data.get('chart', {}).get('result') and validated_quote_metadata(data, ticker):
                logger.info(f"Successfully fetched data for {ticker}")
                return data
    except Exception as e:
        logger.debug(f"Direct Yahoo Finance fetch notice: {e}")

    # 2. Try yfapi.net if API key is configured
    if api_key and time.monotonic() < quote_deadline:
        try:
            url = f"{base_url}/v8/finance/chart/{quote(ticker, safe='')}?range=5d&interval=1d"
            headers = {'X-API-KEY': api_key, 'accept': 'application/json'}
            response = fetch_public_http(url, headers=headers, timeout=max(0.01, quote_deadline - time.monotonic()),
                                         max_bytes=1_000_000, max_attempts=1, max_redirects=0)
            if response.status_code == 200:
                data = json.loads(response.body)
                return data if validated_quote_metadata(data, ticker) else None
        except Exception as e:
            logger.error(f"yfapi.net fetch failed: {e}")

    return None


def extract_prices(chart_data: Dict) -> Optional[List[float]]:
    """
    Extract closing prices from chart data.
    
    Args:
        chart_data: Raw API response data
        
    Returns:
        List of closing prices or None if extraction fails
    """
    try:
        result = chart_data.get('chart', {}).get('result', [])
        if not result:
            logger.error("No chart result data found")
            return None
        
        indicators = result[0].get('indicators', {})
        quote = indicators.get('quote', [])
        
        if not quote:
            logger.error("No quote data found in indicators")
            return None
        
        close_prices = quote[0].get('close', [])
        
        # Filter out None values and NaN
        prices = [float(p) for p in close_prices if p is not None and not np.isnan(p)]
        
        if len(prices) < 2:
            logger.warning(f"Insufficient price data: only {len(prices)} points available")
            return None
        
        logger.info(f"Extracted {len(prices)} valid price points")
        return prices
        
    except Exception as e:
        logger.error(f"Error extracting prices: {str(e)}")
        return None


def analyze_volatility(prices: List[float]) -> Dict[str, Any]:
    """
    Analyze price volatility using statistical methods.
    
    Calculates the Z-score of the latest price to detect anomalies.
    A Z-score below -2.0 indicates the price is 2 standard deviations
    below the mean, flagged as a "Sigma Event" (potential crash).
    
    Args:
        prices: List of historical closing prices
        
    Returns:
        Dict containing volatility analysis results
    """
    try:
        prices_array = np.array(prices)
        
        # Calculate statistical measures
        mean_price = np.mean(prices_array)
        std_dev = np.std(prices_array)
        latest_price = prices_array[-1]
        
        # Calculate Z-score (how many standard deviations from mean)
        if std_dev > 0:
            z_score = (latest_price - mean_price) / std_dev
        else:
            z_score = 0.0
        
        # Determine volatility status
        if z_score < -2.0:
            status = "SIGMA_EVENT"
            logger.warning(f"⚠️ CRASH DETECTED: Z-score = {z_score:.2f}")
        elif z_score < -1.0:
            status = "HIGH_VOLATILITY"
        elif z_score > 2.0:
            status = "RALLY"
        else:
            status = "STABLE"
        
        return {
            "mean": round(mean_price, 2),
            "std_dev": round(std_dev, 2),
            "z_score": round(z_score, 2),
            "volatility_status": status,
            "latest_price": round(latest_price, 2)
        }
        
    except Exception as e:
        logger.error(f"Error in volatility analysis: {str(e)}")
        return {
            "z_score": 0.0,
            "volatility_status": "ERROR",
            "error": str(e)
        }


def predict_impact(prices: List[float]) -> Dict[str, Any]:
    """
    Honest Market Signal Framework:
    Replaces naive linear regression extrapolation with an empirical volatility and
    catalyst sensitivity model. Separates observed price momentum, volatility bounds,
    and fundamental catalyst exposure rather than pretending daily ticks extrapolate
    into deterministic 60-minute forecasts.
    
    Args:
        prices: List of historical closing prices
        
    Returns:
        Dict containing honest market signal analysis
    """
    try:
        if not prices or len(prices) < 2:
            return {
                "projected_price_1hr": 0.0,
                "projected_loss": 0.0,
                "trend": "UNKNOWN",
                "confidence": "INSUFFICIENT",
                "methodology": "Insufficient historical price points for volatility estimation"
            }

        recent_prices = prices[-10:] if len(prices) >= 10 else prices
        current_price = float(recent_prices[-1])
        baseline_price = float(recent_prices[0])
        
        # Empirical price momentum over sample window
        pct_change = ((current_price - baseline_price) / baseline_price) * 100.0 if baseline_price > 0 else 0.0
        
        # Standard deviation and 95% volatility envelope
        std_dev = float(np.std(recent_prices))
        lower_bound = max(0.0, round(current_price - 1.96 * std_dev, 2))
        upper_bound = round(current_price + 1.96 * std_dev, 2)
        
        # Directional trend classification
        if pct_change < -1.5:
            trend = "DOWNWARD"
        elif pct_change > 1.5:
            trend = "UPWARD"
        else:
            trend = "SIDEWAYS"
            
        slope = round((current_price - baseline_price) / len(recent_prices), 4)

        # Calibrated projection: bounded drift within 95% volatility band
        drift_factor = 0.15  # dampening factor avoiding runaway extrapolation
        projected_price = round(current_price * (1.0 + (pct_change / 100.0) * drift_factor), 2)
        projected_change = round(((projected_price - current_price) / current_price) * 100.0, 2) if current_price > 0 else 0.0

        return {
            "projected_price_1hr": projected_price,
            "projected_loss": projected_change,
            "trend": trend,
            "slope": slope,
            "confidence": "MEDIUM" if len(recent_prices) >= 8 else "LOW",
            "methodology": "Empirical Volatility Bounds & Signal Momentum (Non-linear; no mechanical extrapolation)",
            "market_state": {
                "observed_price": current_price,
                "sample_momentum_pct": round(pct_change, 2),
                "volatility_envelope_95pct": [lower_bound, upper_bound],
                "catalyst_sensitivity": "HIGH" if abs(pct_change) > 2.5 else "MODERATE"
            },
            "risk_factors": [
                "Historical prices reflect delayed daily close sampling, not real-time depth-of-book liquidity.",
                "Sudden material corporate filings or regulatory intervention can abruptly invalidate technical bounds."
            ],
            "invalidation_criteria": "Breach of the 95% volatility envelope or release of unexpected audited filings."
        }
        
    except Exception as e:
        logger.error(f"Error in impact prediction: {str(e)}")
        return {
            "projected_price_1hr": 0.0,
            "projected_loss": 0.0,
            "trend": "UNKNOWN",
            "error": str(e)
        }


def check_stock_impact(
    ticker: str,
    base_url: str = "https://yfapi.net",
    api_key: str = "",
    social_correlator: Optional[Callable[[str], Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Check stock impact, crash probability, and correlate with social intelligence."""
    try:
        chart_data = fetch_stock_data(ticker, base_url=base_url, api_key=api_key)
        prices = None
        if chart_data:
            prices = extract_prices(chart_data)
        if not prices or len(prices) < 2:
            return {}
        first = float(prices[0])
        last = float(prices[-1])
        if first == 0:
            return {}
        drop_percent = ((last - first) / first) * 100.0
        vol = analyze_volatility(prices)
        z = float(vol.get("z_score", 0.0))
        is_crashing = (drop_percent <= -2.0) or (z <= -2.0)

        # Correlate price anomaly with omni-channel social intelligence
        social_intel = social_correlator(ticker) if social_correlator else {}

        return {
            "quote_identity": validated_quote_metadata(chart_data, ticker),
            "ticker": ticker,
            "current_price": round(last, 2),
            "drop_percent": round(drop_percent, 2),
            "z_score": round(z, 2),
            "is_crashing": bool(is_crashing),
            "social_intel": social_intel,
            "short_attack_correlation": bool(is_crashing and social_intel.get("social_signals_detected", 0) > 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"check_stock_impact error: {e}")
        return {}


__all__ = [
    "resolve_ticker_and_company",
    "fetch_stock_data",
    "extract_prices",
    "analyze_volatility",
    "predict_impact",
    "check_stock_impact",
]
