"""
Trending Agent: Content Intelligence Engine
============================================
Multi-vector misinformation hunter that detects the causes of stock crashes
and identifies identity fraud/impersonation attacks.
"""

import requests
import xml.etree.ElementTree as ET
import google.generativeai as genai
import difflib
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


class TrendingAgent:
    """
    The Trending Agent is the Content Intelligence Engine that:
    1. Hunts for misinformation causing stock crashes (Reactive Dragnet)
    2. Performs deep scans for corporate risk vectors (Proactive Analysis)
    3. Detects identity fraud and impersonation attacks (Forensics)
    """
    
    def __init__(self):
        """Initialize the Trending Agent with Gemini model."""
        logger.info("🔎 Initializing Trending Agent...")
        
        # Use fast model for speed
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Google News RSS endpoint
        self.news_base_url = "https://news.google.com/rss/search"
        
        logger.info("✅ Trending Agent initialized with gemini-2.0-flash-exp")
    
    def fetch_targeted_news(self, query: str, window_mins: int = 30) -> List[Dict]:
        """
        Fetch news articles for a specific query within a time window.
        
        This is the "Reactive Dragnet" - searching backwards from a crash
        to find the misinformation that triggered it.
        
        Args:
            query: Search query (e.g., "Tata Motors fraud")
            window_mins: Time window in minutes to search backwards
            
        Returns:
            List of news articles with title, link, and publication time
        """
        try:
            logger.info(f"🔍 Searching news for: '{query}' (last {window_mins} mins)")
            
            params = {
                'q': query,
                'hl': 'en-US',
                'gl': 'US',
                'ceid': 'US:en'
            }
            
            response = requests.get(self.news_base_url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"News fetch failed with status {response.status_code}")
                return []
            
            # Parse RSS XML
            root = ET.fromstring(response.content)
            
            articles = []
            cutoff_time = datetime.now() - timedelta(minutes=window_mins)
            
            for item in root.findall('.//item'):
                title_elem = item.find('title')
                link_elem = item.find('link')
                pub_date_elem = item.find('pubDate')
                
                if title_elem is not None and link_elem is not None:
                    title = title_elem.text
                    link = link_elem.text
                    
                    # Parse publication date
                    pub_time = None
                    if pub_date_elem is not None:
                        try:
                            # RSS date format: "Wed, 27 Nov 2024 10:30:00 GMT"
                            from email.utils import parsedate_to_datetime
                            pub_time_aware = parsedate_to_datetime(pub_date_elem.text)
                            # Convert to naive datetime for comparison
                            pub_time = pub_time_aware.replace(tzinfo=None)
                        except Exception as e:
                            logger.warning(f"Failed to parse date: {pub_date_elem.text}")
                    
                    # Filter by time window
                    if pub_time and pub_time >= cutoff_time:
                        articles.append({
                            'title': title,
                            'link': link,
                            'published': pub_time.isoformat(),
                            'age_minutes': int((datetime.now() - pub_time).total_seconds() / 60)
                        })
                        logger.info(f"   ✓ Found: {title} ({pub_time.strftime('%I:%M %p')})")
            
            logger.info(f"📰 Found {len(articles)} articles within {window_mins} min window")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}")
            return []
    
    def analyze_panic(self, headlines: List[str]) -> Dict:
        """
        Analyze headlines for panic/manipulation indicators using Gemini.
        
        Uses AI to detect fear-mongering, urgency triggers, and crisis language
        that could cause market panic.
        
        Args:
            headlines: List of news headlines to analyze
            
        Returns:
            Dict with panic_score, highest_risk_headline, and analysis
        """
        try:
            if not headlines:
                return {
                    'panic_score': 0,
                    'highest_risk_headline': None,
                    'analysis': 'No headlines to analyze'
                }
            
            logger.info(f"🧠 Analyzing {len(headlines)} headlines for panic indicators...")
            
            # Construct prompt for Gemini
            headlines_text = "\n".join([f"{i+1}. {h}" for i, h in enumerate(headlines)])
            
            prompt = f"""You are a financial misinformation analyst. Analyze these headlines for PANIC indicators.

HEADLINES:
{headlines_text}

PANIC INDICATORS to look for:
- Emergency words: ARREST, RAID, BANKRUPTCY, COLLAPSE, CRISIS, FRAUD
- Urgent language: "BREAKING", "JUST IN", "URGENT"
- Extreme claims: "Biggest scandal", "Massive losses", "Complete failure"
- Fear triggers: "Investors panic", "Stock crashes", "Market meltdown"

TASK:
1. Rate the overall PANIC SCORE from 0-100 (0=calm news, 100=maximum panic)
2. Identify the HIGHEST RISK headline (the one most likely to cause stock drops)
3. Explain WHY that headline is risky in ONE sentence

Return ONLY valid JSON in this exact format:
{{
  "panic_score": <0-100>,
  "highest_risk_headline": "<exact headline text>",
  "risk_reason": "<one sentence explanation>"
}}"""

            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean markdown formatting if present
            if result_text.startswith('```json'):
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif result_text.startswith('```'):
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(result_text)
            
            logger.info(f"🎯 Panic Score: {result['panic_score']}/100")
            if result.get('highest_risk_headline'):
                logger.warning(f"⚠️ Highest Risk: {result['highest_risk_headline']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in panic analysis: {str(e)}")
            return {
                'panic_score': 0,
                'highest_risk_headline': None,
                'analysis': f'Analysis failed: {str(e)}'
            }
    
    def detect_impersonation(self, suspect_handle: str, official_handle: str) -> Dict:
        """
        Detect typosquatting and impersonation attacks using string similarity.
        
        Catches attacks like:
        - @TataM0tors (zero instead of O)
        - @TataMotorss (extra s)
        - @Tata_Motors (underscore)
        
        Args:
            suspect_handle: Handle to check (e.g., "@TataM0tors")
            official_handle: Known official handle (e.g., "@TataMotors")
            
        Returns:
            Dict with is_impersonation, similarity_score, and attack_type
        """
        try:
            logger.info(f"🔬 Checking: '{suspect_handle}' vs official '{official_handle}'")
            
            # Normalize (remove @, lowercase)
            suspect_clean = suspect_handle.lower().replace('@', '').replace('_', '')
            official_clean = official_handle.lower().replace('@', '').replace('_', '')
            
            # Calculate similarity using SequenceMatcher
            similarity = difflib.SequenceMatcher(None, suspect_clean, official_clean).ratio()
            
            # Detection logic
            is_identical = suspect_clean == official_clean
            is_similar = similarity > 0.80
            
            if is_identical:
                result = {
                    'is_impersonation': False,
                    'similarity_score': 1.0,
                    'attack_type': 'LEGITIMATE',
                    'confidence': 'HIGH'
                }
            elif is_similar and not is_identical:
                # High similarity but not exact = TYPOSQUATTING
                result = {
                    'is_impersonation': True,
                    'similarity_score': round(similarity, 3),
                    'attack_type': 'TYPOSQUATTING_ATTACK',
                    'confidence': 'HIGH' if similarity > 0.90 else 'MEDIUM'
                }
                logger.critical(f"🚨 IMPERSONATION DETECTED: {suspect_handle} (similarity: {similarity:.1%})")
            else:
                result = {
                    'is_impersonation': False,
                    'similarity_score': round(similarity, 3),
                    'attack_type': 'UNRELATED',
                    'confidence': 'HIGH'
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in impersonation detection: {str(e)}")
            return {
                'is_impersonation': False,
                'similarity_score': 0.0,
                'attack_type': 'ERROR',
                'error': str(e)
            }

    def search_company_news(self, company_name: str, query_type: str = "panic") -> List[Dict]:
        try:
            base = company_name.replace('.NS', '').replace('.BO', '').replace('_', ' ')
            if query_type == "panic":
                queries = [
                    f"{base} arrest",
                    f"{base} fraud",
                    f"{base} investigation",
                    f"{base} raid",
                    f"{base} fake"
                ]
            else:
                queries = [base]
            items: List[Dict] = []
            for q in queries:
                items.extend(self.fetch_targeted_news(q, 60))
            unique = {a['title']: a for a in items}.values()
            return list(unique)
        except Exception:
            return []

    def filter_by_time(self, news_items: List[Dict], crash_time: str, minutes: int = 30) -> List[Dict]:
        try:
            if not crash_time:
                return news_items
            ct = datetime.fromisoformat(crash_time)
            start = ct - timedelta(minutes=minutes)
            filtered: List[Dict] = []
            for n in news_items:
                ts = n.get('published')
                if not ts:
                    continue
                try:
                    pt = datetime.fromisoformat(ts)
                except Exception:
                    continue
                if start <= pt <= ct:
                    filtered.append(n)
            return filtered
        except Exception:
            return news_items
    
    def process_task(self, task: Dict) -> Dict:
        """
        Main processing method for the Trending Agent.
        
        Supports two modes:
        1. "Hunt" Mode (Reactive Dragnet): Triggered by crash, searches for cause
        2. "Deep Scan" Mode (Proactive): Comprehensive 3-vector risk analysis
        
        Args:
            task: Task dictionary with mode and parameters
            
        Returns:
            Dict containing analysis results and threat intelligence
        """
        try:
            mode = task.get('mode', 'hunt')
            logger.info(f"🎯 Processing Trending task - Mode: {mode.upper()}")
            
            # MODE A: REACTIVE HUNT (Triggered by Scout's Sigma Event)
            if mode == 'hunt' or 'target_ticker' in task:
                return self._hunt_mode(task)
            
            # MODE B: DEEP SCAN (User-triggered or scheduled)
            elif mode == 'deep_scan' or task.get('scan_type') == 'full':
                return self._deep_scan_mode(task)
            
            else:
                return {
                    'status': 'failed',
                    'error': 'Unknown mode. Use "hunt" or "deep_scan"'
                }
                
        except Exception as e:
            logger.error(f"Error processing Trending task: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _hunt_mode(self, task: Dict) -> Dict:
        """
        HUNT MODE: Reactive Dragnet
        
        Triggered when Scout detects a Sigma Event.
        Searches backwards to find the "smoking gun" misinformation.
        """
        ticker = task.get('target_ticker', 'UNKNOWN')
        crash_time = task.get('crash_time')
        window_mins = task.get('search_window_minutes', 30)
        urgency = task.get('urgency_level', 'MEDIUM')
        
        logger.info(f"🚨 HUNT MODE: Searching for cause of {ticker} crash")
        logger.info(f"   Urgency: {urgency} | Window: {window_mins} mins")
        
        # Extract company name from ticker
        company_name = ticker.replace('.NS', '').replace('.BO', '').replace('_', ' ')
        
        # Build panic-focused query
        panic_keywords = ['fraud', 'arrest', 'raid', 'bankruptcy', 'scandal', 'crisis']
        
        all_articles = []
        for keyword in panic_keywords:
            query = f"{company_name} {keyword}"
            articles = self.fetch_targeted_news(query, window_mins)
            all_articles.extend(articles)
        
        # Remove duplicates
        unique_articles = {a['title']: a for a in all_articles}.values()
        unique_articles = list(unique_articles)
        unique_articles = self.filter_by_time(unique_articles, crash_time, window_mins)
        
        if not unique_articles:
            logger.warning("⚠️ No articles found in time window - crash may be organic")
            return {
                'mode': 'hunt',
                'ticker': ticker,
                'status': 'completed',
                'smoking_gun_found': False,
                'articles_analyzed': 0,
                'verdict': 'NO_MISINFORMATION_DETECTED'
            }
        
        # Analyze headlines for panic
        headlines = [a['title'] for a in unique_articles]
        panic_analysis = self.analyze_panic(headlines)
        
        # Determine if this is the "smoking gun"
        smoking_gun_found = panic_analysis['panic_score'] > 60
        
        result = {
            'mode': 'hunt',
            'ticker': ticker,
            'crash_time': crash_time,
            'status': 'completed',
            'smoking_gun_found': smoking_gun_found,
            'articles_analyzed': len(unique_articles),
            'panic_score': panic_analysis['panic_score'],
            'smoking_gun_headline': panic_analysis.get('highest_risk_headline'),
            'risk_reason': panic_analysis.get('risk_reason'),
            'articles': unique_articles[:5],  # Top 5 for review
            'verdict': 'MISINFORMATION_LIKELY' if smoking_gun_found else 'ORGANIC_VOLATILITY',
            'timestamp': datetime.now().isoformat()
        }
        
        if smoking_gun_found:
            logger.critical("🎯 SMOKING GUN FOUND!")
            logger.critical(f"   Headline: {panic_analysis.get('highest_risk_headline')}")
        else:
            logger.info("✓ No clear misinformation trigger detected")
        
        return result
    
    def _deep_scan_mode(self, task: Dict) -> Dict:
        """
        DEEP SCAN MODE: Proactive 3-Vector Analysis
        
        Comprehensive risk assessment across:
        1. Corporate Integrity (fraud, accounting scandals)
        2. Market Manipulation (pump & dump, coordinated attacks)
        3. Executive Risk (CEO scandals, leadership issues)
        """
        ticker = task.get('ticker', 'UNKNOWN')
        company_name = ticker.replace('.NS', '').replace('.BO', '').replace('_', ' ')
        
        logger.info(f"🔬 DEEP SCAN MODE: Comprehensive analysis of {ticker}")
        
        # Vector 1: Corporate Integrity
        logger.info("   Vector 1: Corporate Integrity Scan")
        integrity_articles = self.fetch_targeted_news(
            f"{company_name} fraud accounting scandal",
            window_mins=1440  # 24 hours
        )
        
        # Vector 2: Market Manipulation
        logger.info("   Vector 2: Market Manipulation Scan")
        manipulation_articles = self.fetch_targeted_news(
            f"{company_name} market manipulation pump dump",
            window_mins=1440
        )
        
        # Vector 3: Executive Risk
        logger.info("   Vector 3: Executive Risk Scan")
        executive_articles = self.fetch_targeted_news(
            f"{company_name} CEO executive scandal",
            window_mins=1440
        )
        
        # Analyze each vector
        integrity_headlines = [a['title'] for a in integrity_articles]
        manipulation_headlines = [a['title'] for a in manipulation_articles]
        executive_headlines = [a['title'] for a in executive_articles]
        
        integrity_score = self.analyze_panic(integrity_headlines) if integrity_headlines else {'panic_score': 0}
        manipulation_score = self.analyze_panic(manipulation_headlines) if manipulation_headlines else {'panic_score': 0}
        executive_score = self.analyze_panic(executive_headlines) if executive_headlines else {'panic_score': 0}
        
        # Calculate overall risk
        overall_risk = max(
            integrity_score['panic_score'],
            manipulation_score['panic_score'],
            executive_score['panic_score']
        )
        
        result = {
            'mode': 'deep_scan',
            'ticker': ticker,
            'status': 'completed',
            'overall_risk_score': overall_risk,
            'vectors': {
                'corporate_integrity': {
                    'risk_score': integrity_score['panic_score'],
                    'articles_found': len(integrity_articles),
                    'highest_risk': integrity_score.get('highest_risk_headline')
                },
                'market_manipulation': {
                    'risk_score': manipulation_score['panic_score'],
                    'articles_found': len(manipulation_articles),
                    'highest_risk': manipulation_score.get('highest_risk_headline')
                },
                'executive_risk': {
                    'risk_score': executive_score['panic_score'],
                    'articles_found': len(executive_articles),
                    'highest_risk': executive_score.get('highest_risk_headline')
                }
            },
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Deep scan complete - Overall Risk: {overall_risk}/100")
        
        return result


# Agent instance for external use
trending_agent = TrendingAgent()


def process_trending_task(task: Dict) -> Dict:
    """
    External interface for processing Trending tasks.
    
    Args:
        task: Task dictionary with mode and parameters
        
    Returns:
        Analysis results dictionary
    """
    return trending_agent.process_task(task)


if __name__ == "__main__":
    # Test the Trending Agent
    print("\n" + "="*80)
    print("TRENDING AGENT TEST")
    print("="*80)
    
    # Test 1: Hunt Mode (simulate crash)
    print("\n🧪 Test 1: Hunt Mode (Reactive Dragnet)")
    hunt_task = {
        'mode': 'hunt',
        'target_ticker': 'TATAMOTORS.NS',
        'crash_time': datetime.now().isoformat(),
        'search_window_minutes': 60,
        'urgency_level': 'HIGH'
    }
    result = process_trending_task(hunt_task)
    print(json.dumps(result, indent=2))
    
    # Test 2: Impersonation Detection
    print("\n🧪 Test 2: Impersonation Detection")
    legit = trending_agent.detect_impersonation("@TataMotors", "@TataMotors")
    fake = trending_agent.detect_impersonation("@TataM0tors", "@TataMotors")
    print(f"Legitimate: {json.dumps(legit, indent=2)}")
    print(f"Fake: {json.dumps(fake, indent=2)}")
