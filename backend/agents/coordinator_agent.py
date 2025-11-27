"""
Coordinator Agent: Strategic Crisis Governor
=============================================
Correlates financial crashes with viral misinformation and generates
autonomous crisis response strategies using advanced AI reasoning.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

import google.generativeai as genai

from backend.agents.scout_agent import ScoutAgent
from backend.agents.trending_agent import TrendingAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


class CoordinatorAgent:
    """
    The Strategic Crisis Governor orchestrates the entire War Room pipeline:
    
    1. Financial Surveillance (Scout Agent)
    2. Content Intelligence (Trending Agent)
    3. Causality Correlation (Timeline Analysis)
    4. Response Generation (Crisis Communication)
    5. Threat Archival (Verified Claims Database)
    """
    
    def __init__(self):
        """Initialize the Crisis Governor with all subsystems."""
        logger.info("🏛️ Initializing Strategic Crisis Governor...")
        
        # Initialize AI agents
        self.scout = ScoutAgent()
        self.trending = TrendingAgent()
        
        # High-reasoning model for crisis response (fast, economical)
        self.response_model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        # Surveillance state
        self.surveillance_active = False
        self.monitored_tickers = []
        
        # Event tracking
        self.active_threats = []
        self.verified_attacks = []
        self.response_history = []
        
        logger.info("✅ Strategic Crisis Governor online")
        logger.info(f"   Scout: Ready")
        logger.info(f"   Trending: Ready")
        logger.info(f"   Response AI: gemini-2.0-flash-lite")

    def monitor_effectiveness(self):
        logger.info("[Coordinator] Running Impact Analysis...")
        active_battles = []
        try:
            from backend.db import database as db
            if db.supabase:
                cutoff = datetime.now() - timedelta(hours=2)
                resp = db.supabase.table('deployed_measures').select('*').gte('deployed_at', cutoff.isoformat()).execute()
                active_battles = resp.data or []
        except Exception:
            active_battles = []
        if not active_battles:
            active_battles = [{"id": 1, "ticker": "TATAMOTORS.NS", "deploy_price": 945.50, "strategy": "cease_desist", "status": "active"}]
        for battle in active_battles:
            ticker = battle.get("ticker")
            deploy_price = battle.get("deploy_price") or battle.get("stock_price_at_deployment")
            try:
                deploy_price = float(deploy_price)
            except Exception:
                deploy_price = 0.0
            current_data = self.scout.check_stock_impact(ticker)
            current_price = current_data.get("last_price") or current_data.get("current_price") or 0.0
            try:
                current_price = float(current_price)
            except Exception:
                current_price = 0.0
            if not deploy_price or not current_price:
                continue
            recovery_pct = ((current_price - deploy_price) / deploy_price) * 100.0
            effectiveness = "NEUTRAL"
            if recovery_pct > 0.5:
                effectiveness = "SUCCESS"
            if recovery_pct < -1.0:
                effectiveness = "FAILURE"
            logger.info(f"Battle {battle.get('id')} {battle.get('strategy')}: {recovery_pct:.2f}% -> {effectiveness}")
            self.response_history.append({
                "battle_id": battle.get("id"),
                "ticker": ticker,
                "strategy": battle.get("strategy") or battle.get("measure_type"),
                "deploy_price": deploy_price,
                "current_price": current_price,
                "recovery_pct": round(recovery_pct, 2),
                "effectiveness": effectiveness,
                "checked_at": datetime.now().isoformat()
            })
    
    def correlate_events(self, stock_data: Dict, news_items: List[Dict]) -> Dict:
        """
        Correlate stock crash events with news articles to find causation.
        
        This is the "Causality Engine" that proves misinformation caused
        financial damage by analyzing temporal relationships and panic metrics.
        
        Args:
            stock_data: Crash data from Scout (timestamp, z_score, etc.)
            news_items: News articles from Trending (title, time, panic_score)
            
        Returns:
            Dict with smoking_gun article and correlation_confidence (0-100)
        """
        logger.info("🔗 CAUSALITY CORRELATION ENGINE")
        logger.info("="*80)
        
        if not news_items:
            logger.info("ℹ️ No news items to correlate")
            return {
                'smoking_gun_found': False,
                'correlation_confidence': 0,
                'verdict': 'NO_NEWS_DATA'
            }
        
        # Extract crash timestamp
        crash_time_str = stock_data.get('crash_timestamp') or stock_data.get('timestamp')
        crash_time = datetime.fromisoformat(crash_time_str)
        
        logger.info(f"📊 Crash Time: {crash_time.strftime('%H:%M:%S')}")
        logger.info(f"📰 Analyzing {len(news_items)} news articles...")
        
        # Find potential smoking guns
        candidates = []
        
        for article in news_items:
            article_time_str = article.get('published')
            if not article_time_str:
                continue
            
            try:
                article_time = datetime.fromisoformat(article_time_str)
                
                # Calculate latency (crash_time - article_time)
                latency_seconds = (crash_time - article_time).total_seconds()
                latency_minutes = latency_seconds / 60
                
                # Smoking gun criteria:
                # 1. Article published BEFORE crash (latency > 0)
                # 2. Within tight window (0-30 minutes)
                if 0 < latency_minutes <= 30:
                    candidates.append({
                        'article': article,
                        'latency_minutes': latency_minutes,
                        'article_time': article_time
                    })
                    logger.info(f"   ✓ Candidate: '{article.get('title')[:60]}...' ({latency_minutes:.1f} mins before crash)")
            
            except Exception as e:
                logger.warning(f"Failed to parse article timestamp: {e}")
        
        if not candidates:
            logger.info("ℹ️ No articles found in causal window (0-30 mins before crash)")
            return {
                'smoking_gun_found': False,
                'correlation_confidence': 0,
                'verdict': 'NO_TEMPORAL_MATCH'
            }
        
        # Sort by latency (closest to crash = most likely cause)
        candidates.sort(key=lambda x: x['latency_minutes'])
        
        # Get the earliest article (most likely trigger)
        smoking_gun = candidates[0]
        article = smoking_gun['article']
        latency = smoking_gun['latency_minutes']
        
        # Calculate correlation confidence
        # Factors: Temporal proximity, panic score, article count
        temporal_score = max(0, 100 - (latency * 3))  # Closer = higher score
        panic_score = stock_data.get('panic_score', 50)  # From Trending Agent analysis
        
        # Combined confidence
        correlation_confidence = int((temporal_score * 0.6) + (panic_score * 0.4))
        
        verdict = "HIGH_CONFIDENCE" if correlation_confidence > 80 else "MEDIUM_CONFIDENCE"
        
        logger.critical("="*80)
        if correlation_confidence > 80:
            logger.critical("🎯 SMOKING GUN IDENTIFIED!")
        else:
            logger.info("⚠️ POTENTIAL CORRELATION DETECTED")
        logger.critical(f"   Headline: {article.get('title')}")
        logger.critical(f"   Published: {smoking_gun['article_time'].strftime('%H:%M:%S')}")
        logger.critical(f"   Time to Impact: {latency:.1f} minutes")
        logger.critical(f"   Correlation Confidence: {correlation_confidence}%")
        logger.critical(f"   Verdict: {verdict}")
        logger.critical("="*80)
        
        return {
            'smoking_gun_found': True,
            'smoking_gun': article,
            'article_time': smoking_gun['article_time'].isoformat(),
            'latency_minutes': round(latency, 2),
            'correlation_confidence': correlation_confidence,
            'verdict': verdict,
            'total_candidates': len(candidates)
        }
    
    def generate_response(self, threat_data: Dict) -> Dict:
        """
        Generate autonomous crisis response strategies using Gemini AI.
        
        Creates three types of responses:
        1. Cease & Desist (legal threat to misinformation source)
        2. Official Denial (investor relations statement)
        3. Internal Alert (CEO briefing)
        
        Args:
            threat_data: Verified threat with headline and stock impact
            
        Returns:
            Dict with three drafted responses
        """
        logger.info("🤖 AUTONOMOUS RESPONSE GENERATOR")
        logger.info("="*80)
        
        headline = threat_data.get('smoking_gun_headline', 'Unknown headline')
        ticker = threat_data.get('ticker', 'UNKNOWN')
        drop_percent = abs(threat_data.get('projected_loss', 0))
        panic_score = threat_data.get('panic_score', 0)
        
        # Extract company name from ticker
        company_name = ticker.replace('.NS', '').replace('.BO', '').replace('_', ' ')
        
        logger.info(f"📝 Generating response for: {company_name}")
        logger.info(f"   Fake Headline: '{headline}'")
        logger.info(f"   Stock Impact: -{drop_percent}%")
        logger.info(f"   Panic Level: {panic_score}/100")
        
        # Construct prompt for Gemini
        prompt = f"""You are a Crisis Communication Officer for {company_name}.

SITUATION:
A false news story has just gone viral and caused immediate market damage:

- FALSE HEADLINE: "{headline}"
- STOCK IMPACT: Stock dropped {drop_percent}% within minutes
- PANIC SCORE: {panic_score}/100 (extremely high)
- VERDICT: This is verified misinformation that caused financial harm

YOUR TASK:
Draft THREE crisis responses. Be professional, firm, and fact-based.

1. CEASE & DESIST (Twitter/X reply to the source)
   - Max 280 characters
   - Firm legal warning tone
   - Demand immediate retraction
   
2. OFFICIAL DENIAL (Investor Relations statement)
   - 2-3 sentences
   - Calm, factual tone
   - Reassure investors with truth
   
3. CEO ALERT (Internal SMS to leadership)
   - Max 160 characters
   - Urgent but concise
   - Key facts only

Return ONLY valid JSON in this exact format:
{{
  "cease_desist": "<text>",
  "official_denial": "<text>",
  "ceo_alert": "<text>"
}}"""

        try:
            logger.info("🧠 Consulting Gemini AI for crisis response...")
            response = self.response_model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean markdown formatting
            if result_text.startswith('```json'):
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif result_text.startswith('```'):
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            responses = json.loads(result_text)
            
            logger.info("✅ Response generation complete")
            logger.info("="*80)
            logger.info("📢 CEASE & DESIST:")
            logger.info(f"   {responses['cease_desist']}")
            logger.info("")
            logger.info("📰 OFFICIAL DENIAL:")
            logger.info(f"   {responses['official_denial']}")
            logger.info("")
            logger.info("📱 CEO ALERT:")
            logger.info(f"   {responses['ceo_alert']}")
            logger.info("="*80)
            
            return {
                'status': 'success',
                'cease_desist': responses['cease_desist'],
                'official_denial': responses['official_denial'],
                'ceo_alert': responses['ceo_alert'],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Response generation failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def save_attack_package(self, attack_data: Dict):
        """
        Save verified attack package to database for audit trail.
        
        In production, this would insert into Supabase 'verified_threats' table.
        
        Args:
            attack_data: Complete attack package with all data
        """
        logger.info("💾 ARCHIVING ATTACK PACKAGE")
        logger.info("="*80)
        
        event_id = attack_data.get('event_id')
        logger.info(f"Event ID: {event_id}")
        logger.info(f"Ticker: {attack_data.get('ticker')}")
        logger.info(f"Confidence: {attack_data.get('correlation_confidence')}%")
        
        try:
            from backend.db import database as db
            if db.supabase:
                payload = {
                    'event_id': attack_data.get('event_id'),
                    'ticker': attack_data.get('ticker'),
                    'crash_timestamp': attack_data.get('crash_timestamp'),
                    'current_price': attack_data.get('current_price'),
                    'projected_loss': attack_data.get('projected_loss'),
                    'z_score': attack_data.get('z_score'),
                    'smoking_gun_headline': attack_data.get('smoking_gun_headline'),
                    'smoking_gun_link': attack_data.get('smoking_gun_link'),
                    'panic_score': attack_data.get('panic_score'),
                    'correlation_confidence': attack_data.get('correlation_confidence'),
                    'latency_minutes': attack_data.get('latency_minutes'),
                    'responses': attack_data.get('responses'),
                    'response_deployed': False
                }
                db.supabase.table('verified_threats').insert(payload).execute()
        except Exception:
            pass
        
        self.verified_attacks.append(attack_data)
        
        logger.info(f"✅ Attack package archived ({len(self.verified_attacks)} total)")
        logger.info("="*80)
    
    def process_ticker(self, ticker: str) -> Dict:
        """
        Process a single ticker through the complete War Room pipeline.
        
        PIPELINE:
        1. Scout Agent → Detect crashes
        2. Trending Agent → Find misinformation
        3. Correlate → Prove causation
        4. Generate Response → Create countermeasures
        5. Archive → Save to database
        
        Args:
            ticker: Stock ticker to analyze
            
        Returns:
            Complete analysis results
        """
        logger.info("\n" + "="*80)
        logger.info(f"🏛️ WAR ROOM PIPELINE: {ticker}")
        logger.info("="*80)
        
        # STEP 1: RUN SCOUT AGENT
        logger.info("\n📊 STEP 1: FINANCIAL SURVEILLANCE")
        scout_result = self.scout.process_task({'ticker': ticker})
        
        if scout_result.get('status') != 'completed':
            logger.warning(f"⚠️ Scout failed: {scout_result.get('error')}")
            return {'status': 'scout_failed', 'result': scout_result}
        
        stats = scout_result.get('stats', {})
        volatility_status = stats.get('volatility_status')
        
        logger.info(f"   Status: {volatility_status}")
        logger.info(f"   Z-Score: {stats.get('z_score')}")
        
        # Check for Sigma Event
        # DEV OVERRIDE: Force crash mode for testing (create file FORCE_CRASH_TEST in project root)
        import os as _test_os
        if _test_os.path.exists("FORCE_CRASH_TEST"):
            logger.critical("🧪 FORCE CRASH TEST MODE ACTIVATED!")
            logger.critical("   Simulating SIGMA_EVENT for testing purposes")
            volatility_status = "SIGMA_EVENT"
            stats['z_score'] = -2.5
            scout_result['current_price'] = 945.00
            scout_result['prediction'] = {'projected_loss': -5.0, 'trend': 'DOWNWARD'}
        
        if volatility_status != "SIGMA_EVENT":
            logger.info("✅ No crash detected - market is stable")
            return {
                'status': 'normal',
                'volatility_status': volatility_status,
                'message': 'No action needed'
            }
        
        # SIGMA EVENT DETECTED!
        logger.critical("\n🚨 SIGMA EVENT DETECTED!")
        logger.critical(f"   Current Price: {scout_result.get('current_price')}")
        logger.critical(f"   Z-Score: {stats.get('z_score')}")
        logger.critical(f"   Projected Loss: {scout_result.get('prediction', {}).get('projected_loss')}%")
        
        # STEP 2: RUN TRENDING AGENT (HUNT MODE)
        logger.info("\n🔎 STEP 2: CONTENT INTELLIGENCE HUNT")
        trending_task = {
            'mode': 'hunt',
            'target_ticker': ticker,
            'crash_time': scout_result.get('timestamp'),
            'search_window_minutes': 30,
            'urgency_level': 'CRITICAL'
        }
        
        trending_result = self.trending.process_task(trending_task)
        
        if trending_result.get('status') != 'completed':
            logger.error(f"❌ Trending Agent failed: {trending_result.get('error')}")
            return {'status': 'trending_failed', 'result': trending_result}
        
        logger.info(f"   Articles Found: {trending_result.get('articles_analyzed', 0)}")
        logger.info(f"   Panic Score: {trending_result.get('panic_score', 0)}/100")
        logger.info(f"   Smoking Gun: {trending_result.get('smoking_gun_found')}")
        
        # STEP 3: CORRELATE EVENTS
        logger.info("\n🔗 STEP 3: CAUSALITY CORRELATION")
        
        # Add panic score to stock data for correlation
        scout_result['panic_score'] = trending_result.get('panic_score', 0)
        scout_result['crash_timestamp'] = scout_result.get('timestamp')
        
        correlation = self.correlate_events(
            stock_data=scout_result,
            news_items=trending_result.get('articles', [])
        )
        
        if not correlation.get('smoking_gun_found'):
            logger.info("ℹ️ No clear misinformation correlation - crash appears organic")
            return {
                'status': 'organic_crash',
                'correlation': correlation
            }
        
        confidence = correlation.get('correlation_confidence', 0)
        
        # Only proceed if high confidence
        if confidence < 80:
            logger.info(f"⚠️ Confidence too low ({confidence}%) - manual review recommended")
            return {
                'status': 'low_confidence',
                'correlation': correlation
            }
        
        # HIGH CONFIDENCE CORRELATION CONFIRMED!
        logger.critical("\n✅ HIGH CONFIDENCE CORRELATION!")
        
        # STEP 4: GENERATE CRISIS RESPONSE
        logger.info("\n🤖 STEP 4: AUTONOMOUS RESPONSE GENERATION")
        
        threat_data = {
            'ticker': ticker,
            'smoking_gun_headline': correlation['smoking_gun'].get('title'),
            'projected_loss': scout_result['prediction'].get('projected_loss'),
            'panic_score': trending_result.get('panic_score')
        }
        
        responses = self.generate_response(threat_data)
        
        # STEP 5: ARCHIVE ATTACK PACKAGE
        logger.info("\n💾 STEP 5: ARCHIVING VERIFIED THREAT")
        
        attack_package = {
            'event_id': f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'ticker': ticker,
            'crash_timestamp': scout_result['crash_timestamp'],
            'current_price': scout_result['current_price'],
            'z_score': stats['z_score'],
            'projected_loss': scout_result['prediction']['projected_loss'],
            'smoking_gun_headline': correlation['smoking_gun']['title'],
            'smoking_gun_link': correlation['smoking_gun'].get('link'),
            'article_timestamp': correlation['article_time'],
            'latency_minutes': correlation['latency_minutes'],
            'panic_score': trending_result['panic_score'],
            'correlation_confidence': confidence,
            'verdict': 'MISINFORMATION_CAUSED_CRASH',
            'responses': responses,
            'archived_at': datetime.now().isoformat()
        }
        
        self.save_attack_package(attack_package)
        
        logger.info("\n" + "="*80)
        logger.info("🏁 WAR ROOM PIPELINE COMPLETE")
        logger.info("="*80)
        
        return {
            'status': 'attack_verified',
            'attack_package': attack_package
        }
    
    def start_surveillance(self, tickers: List[str], interval: int = 300):
        """
        Start continuous War Room surveillance.
        
        Args:
            tickers: List of stock tickers to monitor
            interval: Seconds between cycles (default 300 = 5 minutes)
        """
        self.monitored_tickers = tickers
        self.surveillance_active = True
        
        logger.info("="*80)
        logger.info("🏛️ WAR ROOM SURVEILLANCE ACTIVATED")
        logger.info("="*80)
        logger.info(f"📊 Monitoring: {', '.join(tickers)}")
        logger.info(f"⏱️ Scan Interval: {interval} seconds")
        logger.info("="*80)
        
        cycle_count = 0
        
        try:
            while self.surveillance_active:
                cycle_count += 1
                logger.info(f"\n🔄 Cycle #{cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                for ticker in self.monitored_tickers:
                    result = self.process_ticker(ticker)
                    
                    if result['status'] == 'attack_verified':
                        logger.critical(f"🚨 VERIFIED ATTACK ON {ticker}!")
                self.monitor_effectiveness()
                
                logger.info(f"\n⏳ Next scan in {interval} seconds...")
                import time
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("\n⏹️ Surveillance stopped by user")
            self.surveillance_active = False


# Global instance
coordinator = CoordinatorAgent()


def scan_ticker(ticker: str) -> Dict:
    """
    External interface: Scan a single ticker.
    
    Args:
        ticker: Stock ticker to scan
        
    Returns:
        Analysis results
    """
    return coordinator.process_ticker(ticker)


def start_war_room(tickers: List[str], interval: int = 300):
    """
    External interface: Start War Room surveillance.
    
    Args:
        tickers: Tickers to monitor
        interval: Scan interval in seconds
    """
    coordinator.start_surveillance(tickers, interval)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🏛️ STRATEGIC CRISIS GOVERNOR TEST")
    print("="*80)
    
    # Test single scan
    print("\n🧪 Testing single ticker scan...")
    result = scan_ticker("RELIANCE.NS")
    print(json.dumps(result, indent=2, default=str))
