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
from typing import Dict, List, Optional, Tuple
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
            ticker: Stock ticker symbol (e.g., 'TATAMOTORS.NS')
            
        Returns:
            Dict containing chart data or None if request fails
        """
        try:
            # Try 1-minute data first
            url = f"{self.base_url}/v8/finance/chart/{ticker}"
            headers = {
                'X-API-KEY': self.api_key,
                'accept': 'application/json'
            }
            params = {
                'range': '1d',
                'interval': '1m',
                'indicators': 'quote',
                'includeTimestamps': 'true'
            }
            
            logger.info(f"Fetching stock data for {ticker}...")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Check if we got valid data
                result = data.get('chart', {}).get('result', [])
                if result:
                    logger.info(f"Successfully fetched data for {ticker}")
                    return data
                else:
                    logger.warning(f"No data in response for {ticker}, trying 5-minute interval...")
                    # Fallback to 5-minute interval
                    params['interval'] = '5m'
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Successfully fetched 5-minute data for {ticker}")
                        return data
                    return None
            else:
                logger.error(f"API request failed with status {response.status_code}")
                logger.error(f"Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching stock data: {str(e)}")
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
            prices = [p for p in close_prices if p is not None]
            
            if len(prices) < 10:
                logger.warning(f"Insufficient price data: only {len(prices)} points available")
                meta = result[0].get('meta', {})
                ticker_symbol = meta.get('symbol', '')
                try:
                    url = f"{self.base_url}/v8/finance/chart/{ticker_symbol}"
                    headers = {'X-API-KEY': self.api_key, 'accept': 'application/json'}
                    params = {'range': '5d', 'interval': '1d', 'indicators': 'quote', 'includeTimestamps': 'true'}
                    r = requests.get(url, headers=headers, params=params, timeout=10)
                    if r.status_code == 200:
                        d = r.json()
                        r2 = d.get('chart', {}).get('result', [])
                        if r2:
                            q2 = r2[0].get('indicators', {}).get('quote', [])
                            closes = [p for p in (q2[0].get('close', []) if q2 else []) if p is not None]
                            if len(closes) >= 2:
                                logger.info(f"Using last available daily closes for fallback: {len(closes)} points")
                                return closes
                except Exception as e:
                    logger.warning(f"Fallback to daily data failed: {e}")
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
            return {
                "ticker": ticker,
                "current_price": round(last, 2),
                "drop_percent": round(drop_percent, 2),
                "z_score": round(z, 2),
                "is_crashing": bool(is_crashing),
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
