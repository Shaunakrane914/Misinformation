"""
Scout Agent: Predictive Financial Engine
==========================================
Detects statistical anomalies in stock prices and predicts future crashes
using volatility analysis and linear regression forecasting.
"""

import numpy as np
import requests
import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScoutAgent:
    """
    The Scout Agent monitors stock prices for anomalies and predicts future movements.
    
    Key Features:
    - Statistical anomaly detection using Z-score analysis
    - Volatility monitoring with 2-sigma threshold
    - Linear regression-based price prediction
    - Real-time market data integration via yfapi.net
    """
    
    def __init__(self):
        """Initialize the Scout Agent with API configuration."""
        self.api_key = os.getenv("YF_API_KEY", "")
        # Use yfapi.net (paid service) instead of direct Yahoo Finance
        self.base_url = "https://yfapi.net"
        
        if not self.api_key:
            logger.warning("YF_API_KEY not found in environment variables")
        else:
            logger.info(f"Scout Agent initialized with yfapi.net")
    
    def fetch_stock_data(self, ticker: str) -> Optional[Dict]:
        """
        Fetch real-time stock chart data from Yahoo Finance API.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'NVDA', 'AAPL')
            
        Returns:
            Dict containing chart data or None if request fails
        """
        browser_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }

        # 1. Try free zero-cost Yahoo Finance chart endpoint
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
            logger.info(f"Fetching stock data for {ticker} via Yahoo Finance...")
            response = requests.get(url, headers=browser_headers, timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data.get('chart', {}).get('result'):
                    logger.info(f"Successfully fetched data for {ticker}")
                    return data
        except Exception as e:
            logger.debug(f"Direct Yahoo Finance fetch notice: {e}")

        # 2. Try yfapi.net if API key is configured
        if self.api_key:
            try:
                url = f"{self.base_url}/v8/finance/chart/{ticker}?range=5d&interval=1d"
                headers = {'X-API-KEY': self.api_key, 'accept': 'application/json'}
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.error(f"yfapi.net fetch failed: {e}")

        return None
    
    def extract_prices(self, chart_data: Dict) -> Optional[List[float]]:
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
            
            # Filter out None values
            prices = [float(p) for p in close_prices if p is not None and not np.isnan(p)]
            
            if len(prices) < 2:
                logger.warning(f"Insufficient price data: only {len(prices)} points available")
                return None
            
            logger.info(f"Extracted {len(prices)} valid price points")
            return prices
            
        except Exception as e:
            logger.error(f"Error extracting prices: {str(e)}")
            return None
    
    def analyze_volatility(self, prices: List[float]) -> Dict:
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
    
    def predict_impact(self, prices: List[float]) -> Dict:
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
    
    def process_task(self, task: Dict) -> Dict:
        """
        Main processing method for the Scout Agent.
        
        Orchestrates the entire analysis pipeline:
        1. Fetch real-time stock data
        2. Extract closing prices
        3. Analyze volatility for crash detection
        4. Predict future price movement
        
        Args:
            task: Task dictionary containing ticker and other parameters
            
        Returns:
            Dict containing complete analysis results
        """
        try:
            ticker = task.get('ticker', 'TATAMOTORS.NS')
            logger.info(f"🔍 Processing Scout task for ticker: {ticker}")
            
            # DEMO MODE: Return mock crash for DEMO.NS ticker
            if ticker == "DEMO.NS":
                logger.critical("🎬 DEMO MODE: Simulating Sigma Event for demonstration")
                return {
                    "ticker": "DEMO.NS",
                    "current_price": 1250.00,
                    "timestamp": datetime.now().isoformat(),
                    "stats": {
                        "z_score": -2.8,
                        "volatility_status": "SIGMA_EVENT",
                        "mean": 1300.00,
                        "std_dev": 17.86
                    },
                    "prediction": {
                        "projected_price_1hr": 1200.00,
                        "projected_loss": -4.0,
                        "trend": "DOWNWARD"
                    },
                    "status": "completed",
                    "data_points_analyzed": 100,
                    "demo_mode": True
                }
            
            # Step 1: Fetch stock data
            chart_data = self.fetch_stock_data(ticker)
            if not chart_data:
                return {
                    "ticker": ticker,
                    "status": "failed",
                    "error": "Failed to fetch stock data"
                }
            
            # Step 2: Extract prices
            prices = self.extract_prices(chart_data)
            if not prices:
                return {
                    "ticker": ticker,
                    "status": "failed",
                    "error": "Failed to extract price data"
                }
            
            # Step 3: Analyze volatility
            volatility_analysis = self.analyze_volatility(prices)
            current_price = volatility_analysis.get('latest_price', prices[-1])
            
            # Step 4: Predict impact
            prediction = self.predict_impact(prices)
            
            # Step 5: Compile results
            result = {
                "ticker": ticker,
                "current_price": current_price,
                "timestamp": datetime.now().isoformat(),
                "stats": {
                    "z_score": volatility_analysis.get('z_score', 0.0),
                    "volatility_status": volatility_analysis.get('volatility_status', 'UNKNOWN'),
                    "mean": volatility_analysis.get('mean', 0.0),
                    "std_dev": volatility_analysis.get('std_dev', 0.0)
                },
                "prediction": {
                    "projected_price_1hr": prediction.get('projected_price_1hr', 0.0),
                    "projected_loss": prediction.get('projected_loss', 0.0),
                    "trend": prediction.get('trend', 'UNKNOWN')
                },
                "status": "completed",
                "data_points_analyzed": len(prices)
            }
            
            # Log critical events
            if volatility_analysis.get('volatility_status') == 'SIGMA_EVENT':
                logger.critical(f"🚨 SIGMA EVENT DETECTED for {ticker}!")
                logger.critical(f"   Current: {current_price} | Z-score: {volatility_analysis.get('z_score')}")
                logger.critical(f"   Projected 1hr: {prediction.get('projected_price_1hr')} ({prediction.get('projected_loss')}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing Scout task: {str(e)}")
            return {
                "ticker": task.get('ticker', 'UNKNOWN'),
                "status": "failed",
                "error": str(e)
            }

    def correlate_social_rumors(self, ticker: str) -> Dict[str, Any]:
        """
        Correlate stock price volatility with real-time Reddit (WSB), Twitter ($CASHTAG),
        and YouTube financial analysis signals via AgentReach omni-scan.
        """
        social_intel = {
            "social_signals_detected": 0,
            "short_seller_risk": "LOW",
            "reddit_discussions": [],
            "twitter_cashtags": [],
            "youtube_analyses": [],
            "news_catalysts": []
        }
        try:
            try:
                from backend.services.agent_reach import agent_reach_service
            except (ImportError, ModuleNotFoundError):
                from services.agent_reach import agent_reach_service
            omni_data = agent_reach_service.omni_scan(
                query=ticker,
                domain="financial",
                limit_per_channel=4
            )

            channels = omni_data.get("channels", {})
            r_items = channels.get("reddit", [])
            t_items = channels.get("twitter", [])
            y_items = channels.get("youtube", [])
            n_items = channels.get("news", [])

            social_intel["reddit_discussions"] = [
                {"title": r.get("title", ""), "url": r.get("url", ""), "author": r.get("author", "u/trader")}
                for r in r_items
            ]
            social_intel["twitter_cashtags"] = [
                {"text": t.get("content", ""), "author": t.get("author", "@pulse"), "url": t.get("url", "")}
                for t in t_items
            ]
            social_intel["youtube_analyses"] = [
                {"title": y.get("title", ""), "url": y.get("url", "")}
                for y in y_items
            ]
            social_intel["news_catalysts"] = [
                {"title": n.get("title", ""), "source": n.get("source", "Wire"), "url": n.get("url", "")}
                for n in n_items
            ]

            total_signals = len(r_items) + len(t_items) + len(y_items) + len(n_items)
            social_intel["social_signals_detected"] = total_signals

            # Detect panic keywords across social discourse
            panic_keywords = ["crash", "scam", "fraud", "short", "investigation", "bankrupt", "dump", "sec", "probe"]
            all_text = " ".join([r.get("title", "") for r in r_items] + [t.get("content", "") for t in t_items]).lower()
            panic_hits = sum(1 for kw in panic_keywords if kw in all_text)

            if panic_hits >= 4:
                social_intel["short_seller_risk"] = "CRITICAL (High Coordinated Short Buzz)"
            elif panic_hits >= 2:
                social_intel["short_seller_risk"] = "ELEVATED (Rumor Discourse Active)"
            else:
                social_intel["short_seller_risk"] = "NOMINAL (Standard Chatter)"

        except Exception as e:
            logger.debug(f"[ScoutAgent:correlate_social_rumors] Scraper notice: {e}")

        return social_intel

    def check_stock_impact(self, ticker: str) -> Dict:
        try:
            chart_data = self.fetch_stock_data(ticker)
            prices = None
            if chart_data:
                prices = self.extract_prices(chart_data)
            if not prices or len(prices) < 2:
                try:
                    url = f"{self.base_url}/v8/finance/chart/{ticker}"
                    headers = {'X-API-KEY': self.api_key, 'accept': 'application/json'}
                    params = {'range': '5d', 'interval': '1d', 'indicators': 'quote', 'includeTimestamps': 'true'}
                    r = requests.get(url, headers=headers, params=params, timeout=10)
                    if r.status_code == 200:
                        d = r.json()
                        rr = d.get('chart', {}).get('result', [])
                        if rr:
                            q = rr[0].get('indicators', {}).get('quote', [])
                            closes = [p for p in (q[0].get('close', []) if q else []) if p is not None]
                            if len(closes) >= 2:
                                prices = closes
                except Exception:
                    pass
            if not prices or len(prices) < 2:
                return {}
            first = float(prices[0])
            last = float(prices[-1])
            if first == 0:
                return {}
            drop_percent = ((last - first) / first) * 100.0
            vol = self.analyze_volatility(prices)
            z = float(vol.get("z_score", 0.0))
            is_crashing = (drop_percent <= -2.0) or (z <= -2.0)

            # Correlate price anomaly with omni-channel social intelligence
            social_intel = self.correlate_social_rumors(ticker)

            return {
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

    def resolve_ticker_and_company(self, ticker: str) -> Tuple[str, str]:
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
        sym = name_to_ticker.get(clean, clean)
        from backend.services.agent_reach.planner import TICKER_NAME_MAP
        base_sym = sym.replace('.NS', '').replace('.BO', '')
        company = TICKER_NAME_MAP.get(sym, TICKER_NAME_MAP.get(base_sym, base_sym.title()))
        return sym, company

    def _synthesize_financial_intelligence(
        self, company_name: str, ticker: str, stock_data: Dict, sources: List[Dict]
    ) -> Dict[str, Any]:
        """
        Use Gemini strictly as a reasoning engine over retrieved evidence fragments.
        Never hallucinate facts, dates, or non-existent sources.
        """
        if not sources:
            return {
                "catalysts": {"positive": [], "negative": [], "unresolved": []},
                "risks": ["No verified online sources retrieved across monitored channels."],
                "narratives": [],
                "contradictions": {"for": [], "against": [], "unresolved": []},
                "misinformation": {
                    "status": "NOMINAL",
                    "rumors_detected": [],
                    "manipulation_risk": "LOW",
                    "evidence_quality_score": 0.0,
                    "notes": "Zero external records discovered for cross-verdict synthesis."
                }
            }

        source_summary = "\n".join([
            f"[{s['evidence_id']}] ({s['source_role']}) {s['source']}: {s['title']} — {s['snippet'][:160]}"
            for s in sources[:12]
        ])

        prompt = f"""You are a principal financial intelligence analyst at Aegis Protocol.
Analyze the following retrieved market evidence for {company_name} ({ticker}).
CRITICAL RULE: Rely ONLY on the provided evidence below. DO NOT invent, assume, or hallucinate any facts, dates, filings, or sources.

RETRIEVED EVIDENCE:
{source_summary}

STOCK STATUS: Price {stock_data.get('current_price', 'N/A')} {stock_data.get('currency', '')}, 24h Change {stock_data.get('drop_percent', 0)}%, Z-Score {stock_data.get('z_score', 0)}

TASK:
Respond in STRICT JSON with this schema:
{{
  "catalysts": {{
    "positive": [{{"catalyst": "Concise factual statement", "impact": "High|Medium|Low", "evidence_ids": ["src_001"]}}],
    "negative": [{{"catalyst": "Concise factual statement", "impact": "High|Medium|Low", "evidence_ids": ["src_002"]}}],
    "unresolved": [{{"factor": "Concise factual statement", "evidence_ids": ["src_003"]}}]
  }},
  "risks": ["Specific risk grounded directly in evidence"],
  "narratives": [
    {{"theme": "Theme Name", "description": "Brief summary", "sentiment": "Bullish|Bearish|Neutral", "evidence_ids": ["src_001"]}}
  ],
  "contradictions": {{
    "for": ["Grounded supporting point"],
    "against": ["Grounded contradicting point"],
    "unresolved": ["Ambiguous or conflicting aspect"]
  }},
  "misinformation": {{
    "status": "NOMINAL|ELEVATED|CRITICAL",
    "rumors_detected": ["Any unverified or sensationalized claim"],
    "manipulation_risk": "LOW|MEDIUM|HIGH",
    "evidence_quality_score": 0.85,
    "primary_corroboration": true
  }}
}}"""

        try:
            from backend.services.gemini_service import gemini_service
            raw_text = gemini_service.generate_text(prompt)
            cleaned = raw_text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "catalysts" in parsed:
                return parsed
        except Exception as e:
            logger.debug(f"[ScoutAgent:synthesize] LLM synthesis notice, using grounded rule-based parsing: {e}")

        # Deterministic evidence-grounded fallback extraction
        pos_cats = []
        neg_cats = []
        unres_cats = []
        narratives = []
        risks = []
        rumors = []

        pos_kw = ["growth", "profit", "surge", "gain", "rally", "deal", "order", "boost", "strong", "outperform", "expand"]
        neg_kw = ["drop", "crash", "plunge", "fall", "debt", "investigation", "probe", "loss", "fraud", "lawsuit", "defect"]
        rumor_kw = ["rumor", "unverified", "alleged", "claim", "hoax", "speculation", "leak"]

        for s in sources:
            text = f"{s['title']} {s['snippet']}".lower()
            if any(k in text for k in pos_kw):
                pos_cats.append({
                    "catalyst": s['title'][:110],
                    "impact": "Medium",
                    "evidence_ids": [s['evidence_id']]
                })
            elif any(k in text for k in neg_kw):
                neg_cats.append({
                    "catalyst": s['title'][:110],
                    "impact": "High" if "investigation" in text or "fraud" in text else "Medium",
                    "evidence_ids": [s['evidence_id']]
                })
            else:
                unres_cats.append({
                    "factor": s['title'][:110],
                    "evidence_ids": [s['evidence_id']]
                })

            if any(k in text for k in rumor_kw):
                rumors.append(s['title'][:100])

        if any("earnings" in s['title'].lower() or "result" in s['title'].lower() for s in sources):
            narratives.append({
                "theme": "Earnings & Financial Performance",
                "description": f"Market focus on operational margins and periodic results for {company_name}.",
                "sentiment": "Neutral",
                "evidence_ids": [s['evidence_id'] for s in sources if "earning" in s['title'].lower() or "result" in s['title'].lower()]
            })
        if any("regulatory" in s['title'].lower() or "investigation" in s['title'].lower() for s in sources):
            narratives.append({
                "theme": "Regulatory & Legal Scrutiny",
                "description": f"Regulatory compliance or inquiry signals observed in discourse.",
                "sentiment": "Bearish",
                "evidence_ids": [s['evidence_id'] for s in sources if "regulatory" in s['title'].lower() or "investigation" in s['title'].lower()]
            })
        if not narratives:
            narratives.append({
                "theme": "General Market Momentum",
                "description": f"Trading volume and sector momentum surrounding {company_name}.",
                "sentiment": "Neutral",
                "evidence_ids": [sources[0]['evidence_id']] if sources else []
            })

        for nc in neg_cats[:3]:
            risks.append(nc["catalyst"])
        if not risks:
            risks.append(f"Standard macroeconomic and sector-wide volatility impacting {company_name}.")

        return {
            "catalysts": {
                "positive": pos_cats[:4],
                "negative": neg_cats[:4],
                "unresolved": unres_cats[:3]
            },
            "risks": risks[:4],
            "narratives": narratives[:3],
            "contradictions": {
                "for": [p["catalyst"] for p in pos_cats[:2]],
                "against": [n["catalyst"] for n in neg_cats[:2]],
                "unresolved": [u["factor"] for u in unres_cats[:2]]
            },
            "misinformation": {
                "status": "ELEVATED" if rumors else "NOMINAL",
                "rumors_detected": rumors[:3],
                "manipulation_risk": "ELEVATED" if len(rumors) >= 2 else ("MEDIUM" if rumors else "LOW"),
                "evidence_quality_score": round(min(0.95, 0.50 + 0.05 * len(sources)), 2),
                "primary_corroboration": any(s["source_role"] == "PRIMARY" for s in sources)
            }
        }

    def analyze_stock(self, ticker: str, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute comprehensive Financial Intelligence Research Workspace analysis.
        Orchestrates:
        1. Market telemetry & anomaly detection
        2. Agent Reach multi-channel retrieval (News, Reddit, Twitter, YouTube, RSS)
        3. Forensic source role & primary source classification
        4. Chronological research timeline construction
        5. Grounded catalyst, narrative, and contradiction reasoning
        """
        start_t = datetime.utcnow()
        sym, company_name = self.resolve_ticker_and_company(ticker)

        # 1. Market Telemetry
        stock_data = self.check_stock_impact(sym)
        if not stock_data or not stock_data.get("current_price"):
            stock_data = {
                "ticker": sym,
                "name": company_name,
                "current_price": 0.0,
                "prev_close": 0.0,
                "drop_percent": 0.0,
                "z_score": 0.0,
                "currency": "INR" if sym.endswith(".NS") or sym.endswith(".BO") else "USD",
                "is_crashing": False,
                "data_source": "Historical Daily Close via Yahoo Finance Chart API (Delayed) — Non-realtime"
            }
        else:
            stock_data["name"] = company_name
            stock_data["currency"] = "INR" if sym.endswith(".NS") or sym.endswith(".BO") else "USD"
            stock_data["data_source"] = "Historical Daily Close via Yahoo Finance Chart API (Delayed) — Non-realtime"

        # 2. Shared Deep Research Engine Retrieval & Investigation
        from backend.services.research import research_engine, ResearchRequest
        research_req = ResearchRequest(
            target=f"{company_name} ({sym})",
            domain="financial",
            intent=query or f"investigate financial performance, corporate filings, regulatory risks, and market catalysts for {company_name}",
            query_classes=[
                "latest_primary", "official_statement", "regulatory", "investigative",
                "independent_reporting", "community_signal", "contradiction"
            ],
            required_source_roles=["PRIMARY", "SECONDARY", "COMMUNITY"],
            deep_read_budget=6,
            corroboration_budget=4,
        )
        research_res = None
        try:
            research_res = research_engine.investigate(research_req)
            evidence_items = research_res.evidence
            research_findings = research_res.findings
            research_telemetry = research_res.telemetry
            retrieval_trace = research_telemetry
            retrieval_plan = {
                "query_classes": research_req.query_classes,
                "trace": research_telemetry
            }
            channel_health = research_telemetry.get("channel_health", {})
        except Exception as e_ret:
            logger.warning(f"[ScoutAgent:analyze_stock] ResearchEngine exception: {e_ret}")
            evidence_items = []
            research_findings = []
            research_telemetry = {}
            retrieval_plan = {}
            retrieval_trace = {}
            channel_health = {}

        # 3. Classify & Group Fragments
        primary_sources = []
        news_items = []
        reddit_items = []
        twitter_items = []
        youtube_items = []
        all_sources = []

        syndicated_count = 0

        for idx, item in enumerate(evidence_items):
            # item may be an EvidenceItem instance or a dict
            if hasattr(item, "id"):
                e_id = item.id
                title = item.title or "Untitled Discovered Signal"
                url = item.canonical_url or ""
                source_name = item.source_name or item.channel
                channel = item.channel
                published = item.published_at or "Recent"
                discovered = item.discovered_at
                snippet = item.snippet or item.relevant_excerpt[:240]
                relevant_excerpt = item.relevant_excerpt
                role = item.source_role
                tier = item.source_tier
                group = item.independence_group
                family_id = item.source_family_id
                depth = item.content_depth
                q_id = item.query_id
                q_class = item.query_class
                q_text = item.query_text
                is_primary = item.primary_source or role in ("PRIMARY", "PRIMARY_OFFICIAL", "PRIMARY_REGULATORY")
            else:
                e_id = item.get("evidence_id", f"src_{idx+1:03d}")
                title = item.get("title", "Untitled Discovered Signal")
                url = item.get("url", "")
                source_name = item.get("source", item.get("platform", "Channel"))
                channel = item.get("channel", item.get("platform", "news"))
                published = item.get("published_at", item.get("published", "Recent"))
                discovered = item.get("retrieved_at", "")
                snippet = item.get("snippet", "")
                relevant_excerpt = item.get("relevant_excerpt", "")
                role = item.get("source_role", "DISCOVERY")
                tier = item.get("source_tier", "TIER_3_AGGREGATE")
                group = item.get("independence_group", item.get("source_independence_group", "independent"))
                family_id = item.get("source_family_id", "")
                depth = item.get("content_depth", "SNIPPET")
                q_id = item.get("query_id", "")
                q_class = item.get("query_class", "general")
                q_text = item.get("query_text", "")
                is_primary = role == "PRIMARY"

            if group and group.startswith("syndicated_"):
                syndicated_count += 1

            source_record = {
                "evidence_id": e_id,
                "title": title,
                "url": url,
                "has_url": bool(url),
                "author": source_name,
                "source": source_name,
                "channel": channel,
                "published_at": published,
                "retrieved_at": discovered,
                "snippet": snippet,
                "relevant_excerpt": relevant_excerpt,
                "source_role": role,
                "source_tier": tier,
                "independence_group": group,
                "source_family_id": family_id,
                "content_depth": depth,
                "query_id": q_id,
                "query_class": q_class,
                "query_text": q_text,
            }
            all_sources.append(source_record)

            if is_primary or "investor" in url.lower() or "filing" in title.lower() or "sec.gov" in url.lower():
                primary_sources.append(source_record)

            ch_low = channel.lower()
            if "reddit" in ch_low:
                reddit_items.append(source_record)
            elif "twitter" in ch_low:
                twitter_items.append(source_record)
            elif "youtube" in ch_low:
                youtube_items.append(source_record)
            else:
                news_items.append(source_record)

        # 4. Chronological Research Timeline (sorted by publication if available)
        timeline = []
        dated_sources = [s for s in all_sources if s.get("published_at") and s.get("published_at") != "Recent"]
        for s in dated_sources[:8]:
            timeline.append({
                "time": s["published_at"],
                "source": s["source"],
                "title": s["title"],
                "url": s["url"],
                "role": s["source_role"]
            })
        if not timeline and all_sources:
            for s in all_sources[:5]:
                timeline.append({
                    "time": s.get("published_at") or "Monitored Stream",
                    "source": s["source"],
                    "title": s["title"],
                    "url": s["url"],
                    "role": s["source_role"]
                })

        # 5. Extract Grounded Catalysts, Narratives, Contradictions, & Misinformation Risk
        reasoning = self._synthesize_financial_intelligence(company_name, sym, stock_data, all_sources)

        # 6. Backward compatibility fields
        drop_pct = abs(stock_data.get("drop_percent", 0.0))
        z_score = abs(stock_data.get("z_score", 0.0))
        total_social = len(reddit_items) + len(twitter_items) + len(youtube_items)
        if drop_pct >= 3.0 and total_social >= 4:
            risk_level = "CRITICAL COVERT SHORT ATTACK"
            corr_score = 92
        elif drop_pct >= 1.5 or z_score >= 1.5:
            risk_level = "ELEVATED VOLATILITY DISINFO"
            corr_score = 68
        else:
            risk_level = "NOMINAL (NO ANOMALY)"
            corr_score = 15

        short_attack_correlation = {
            "risk_level": risk_level,
            "correlation_score": corr_score,
            "social_catalyst_volume": total_social,
            "drop_percent": stock_data.get("drop_percent", 0.0),
            "z_score": stock_data.get("z_score", 0.0),
            "is_anomalous": risk_level != "NOMINAL (NO ANOMALY)",
            "recommendation": (
                "Immediate War Room escalation: Coordinated negative narrative volume matches algorithmic sell threshold."
                if risk_level.startswith("CRITICAL")
                else "Continue passive monitoring of cashtag sentiment."
            )
        }

        # News object format for backward compatibility
        legacy_company_articles = [
            {
                "title": n["title"],
                "source": n["source"],
                "source_url": n["url"],
                "url": n["url"],
                "category": "Primary Source" if n["source_role"] == "PRIMARY" else "Market Intelligence",
                "summary": n["snippet"][:120],
                "is_threat": "investigation" in n["title"].lower() or "crash" in n["title"].lower() or "fraud" in n["title"].lower(),
                "sentiment": 15,
                "time": n["published_at"],
                "source_role": n["source_role"],
                "source_tier": n["source_tier"]
            }
            for n in news_items
        ]

        total_time_ms = int((datetime.utcnow() - start_t).total_seconds() * 1000)

        return {
            "ticker": sym,
            "company_name": company_name,
            "analyzed_at": datetime.utcnow().isoformat(),
            "stock": stock_data,
            "market_state": {
                "observed_price": stock_data.get("current_price", 0.0),
                "volatility_status": stock_data.get("stats", {}).get("volatility_status", "STABLE"),
                "drop_percent": stock_data.get("drop_percent", 0.0),
                "z_score": stock_data.get("z_score", 0.0),
                "data_source": stock_data.get("data_source", "Market Feed")
            },
            "findings": [f.to_dict() if hasattr(f, "to_dict") else f for f in research_findings],
            "evidence_chain": getattr(research_res, "evidence_graph", {}),
            "deep_research_trace": research_telemetry,
            "retrieval": {
                "plan": retrieval_plan,
                "channels": channel_health,
                "latency_ms": total_time_ms,
                "total_sources": len(all_sources),
                "unique_sources": max(0, len(all_sources) - syndicated_count),
                "syndicated_sources": syndicated_count,
                "deep_reads": research_telemetry.get("deep_read_success", 0),
                "trace": retrieval_trace,
            },
            "retrieval_trace": retrieval_trace,
            "sources": all_sources,
            "news": {
                "company": legacy_company_articles,
                "ceo": [],
                "analysis": legacy_company_articles
            },
            "social": {
                "reddit": reddit_items,
                "twitter": twitter_items,
                "youtube": youtube_items,
            },
            "social_intel": {
                "reddit": [r["title"] for r in reddit_items],
                "twitter": [t["title"] for t in twitter_items],
                "youtube": [y["title"] for y in youtube_items],
                "news": [n["title"] for n in news_items]
            },
            "primary_sources": primary_sources,
            "catalysts": reasoning.get("catalysts", {"positive": [], "negative": [], "unresolved": []}),
            "risks": reasoning.get("risks", []),
            "narratives": reasoning.get("narratives", []),
            "contradictions": reasoning.get("contradictions", {"for": [], "against": [], "unresolved": []}),
            "timeline": timeline,
            "misinformation": reasoning.get("misinformation", {
                "status": "NOMINAL",
                "rumors_detected": [],
                "manipulation_risk": "LOW",
                "evidence_quality_score": 0.85
            }),
            "limitations": [
                "Market telemetry reflects delayed daily closing series from Yahoo Finance (free tier), not high-frequency tick streams.",
                "Social channels operate via public feeds without authenticated enterprise firehoses.",
                "All citations reflect retrieved public web records; user verification of primary filings is recommended."
            ],
            "short_attack_correlation": short_attack_correlation
        }



# Agent instance for external use
scout_agent = ScoutAgent()


def process_scout_task(task: Dict) -> Dict:
    """
    External interface for processing Scout tasks.
    
    Args:
        task: Task dictionary with ticker and parameters
        
    Returns:
        Analysis results dictionary
    """
    return scout_agent.process_task(task)


if __name__ == "__main__":
    # Test the Scout Agent
    test_task = {
        "ticker": "TATAMOTORS.NS",
        "type": "volatility_check"
    }
    
    result = process_scout_task(test_task)
    print("\n" + "="*60)
    print("SCOUT AGENT TEST RESULTS")
    print("="*60)
    print(json.dumps(result, indent=2))
