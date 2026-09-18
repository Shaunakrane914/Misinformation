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
        Predict future price movement using linear regression.
        
        Uses the last 10 price points to calculate a trend line, then
        extrapolates 12 data points (60 minutes) into the future.
        
        Args:
            prices: List of historical closing prices
            
        Returns:
            Dict containing prediction results
        """
        try:
            # Use the last 10 points for trend analysis
            recent_prices = prices[-10:]
            prices_array = np.array(recent_prices)
            
            # Create x-axis (time indices)
            x = np.arange(len(recent_prices))
            
            # Calculate linear regression (y = mx + b)
            # Using numpy's polyfit for simplicity
            coefficients = np.polyfit(x, prices_array, 1)
            slope = coefficients[0]
            intercept = coefficients[1]
            
            # Project 12 data points into the future (60 minutes at 1-min intervals)
            future_time_index = len(recent_prices) + 12
            projected_price = slope * future_time_index + intercept
            
            # Calculate estimated loss/gain percentage
            current_price = prices_array[-1]
            estimated_change = ((projected_price - current_price) / current_price) * 100
            
            # Determine trend direction
            if slope < -0.1:
                trend = "DOWNWARD"
            elif slope > 0.1:
                trend = "UPWARD"
            else:
                trend = "SIDEWAYS"
            
            logger.info(f"Prediction: {trend} trend, projected change: {estimated_change:.2f}%")
            
            return {
                "projected_price_1hr": round(projected_price, 2),
                "projected_loss": round(estimated_change, 2),
                "trend": trend,
                "slope": round(slope, 4),
                "confidence": "MEDIUM"  # Simple model = medium confidence
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
                from backend.services.agent_reach_scraper import reach_scraper
            except (ImportError, ModuleNotFoundError):
                from services.agent_reach_scraper import reach_scraper
            omni_data = reach_scraper.omni_scan(
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
