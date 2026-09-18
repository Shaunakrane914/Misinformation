"""
Personal Watch Agent
====================
Monitors the web and social media for threats to VIP profiles.
Detects impersonation, doxxing, and smear campaigns.
"""

import logging
import os
from typing import Dict, List, Any, Optional
from duckduckgo_search import DDGS
from apify_client import ApifyClient

logger = logging.getLogger(__name__)


class PersonalWatchAgent:
    """
    The Personal Watch Agent monitors mentions of VIPs across the web and social media.
    
    Key Features:
    - Web search using DuckDuckGo (no API key required)
    - Twitter search using Apify
    - AI-powered threat analysis
    - WhatsApp alerting for high-risk threats
    """
    
    def __init__(self):
        """Initialize the Personal Watch Agent."""
        # Apify client for Twitter scraping
        apify_token = os.getenv("APIFY_TOKEN")
        if apify_token:
            self.apify_client = ApifyClient(apify_token)
        else:
            self.apify_client = None
            logger.warning("APIFY_TOKEN not found - Twitter search will be disabled")
        
        logger.info("Personal Watch Agent initialized")
    
    def search_web_mentions(self, vip_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search the web for mentions of the VIP using AgentReach and DuckDuckGo.
        """
        try:
            logger.info(f"[PersonalWatch] Searching web for mentions of: {vip_name}")
            try:
                from backend.services.agent_reach_scraper import reach_scraper
            except (ImportError, ModuleNotFoundError):
                from services.agent_reach_scraper import reach_scraper
            
            # Use unified news & web extraction
            news_items = reach_scraper.search_news(vip_name, limit=max_results)
            mentions = []
            for item in news_items:
                mentions.append({
                    "source": item.get("source", "Web"),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "content": item.get("content", "")
                })
            
            # If news had few results, fallback to DDGS
            if len(mentions) < max_results:
                try:
                    ddgs = DDGS()
                    for r in ddgs.text(vip_name, max_results=max_results - len(mentions)):
                        mentions.append({
                            "source": "Web",
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                            "content": f"{r.get('title', '')} - {r.get('body', '')}"
                        })
                except Exception as d_err:
                    logger.debug(f"[PersonalWatch] DDGS fallback notice: {d_err}")

            logger.info(f"[PersonalWatch] Found {len(mentions)} web mentions")
            return mentions
            
        except Exception as e:
            logger.error(f"[PersonalWatch] Error searching web mentions: {str(e)}")
            return []
    
    def search_social_mentions(
        self, 
        vip_name: str, 
        official_handle: Optional[str] = None,
        max_results: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Search Twitter/X, Reddit, and YouTube for mentions of the VIP,
        including audio/video deepfake indicators, without requiring paid API keys.
        """
        mentions: List[Dict[str, Any]] = []
        try:
            try:
                from backend.services.agent_reach_scraper import reach_scraper
            except (ImportError, ModuleNotFoundError):
                from services.agent_reach_scraper import reach_scraper
            logger.info(f"[PersonalWatch] Searching omni-channels (Twitter + Reddit + YouTube) for: {vip_name}")

            omni_data = reach_scraper.omni_scan(
                query=vip_name,
                domain="personal",
                vip_handle=official_handle,
                limit_per_channel=max(3, max_results // 3)
            )
            channels = omni_data.get("channels", {})

            # 1. Zero-cost Twitter/X extraction via AgentReach
            for t in channels.get("twitter", []):
                mentions.append({
                    "source": "Twitter/X",
                    "author": t.get("author", "@user"),
                    "content": t.get("content", ""),
                    "url": t.get("url", ""),
                    "likes": t.get("likes", 0),
                    "retweets": t.get("retweets", 0),
                    "title": t.get("title", ""),
                    "is_official": t.get("is_official", False)
                })

            # 2. Zero-cost Reddit community extraction via AgentReach
            for r in channels.get("reddit", []):
                mentions.append({
                    "source": "Reddit",
                    "author": r.get("author", "u/user"),
                    "content": r.get("content", ""),
                    "url": r.get("url", ""),
                    "likes": r.get("score", 0),
                    "retweets": 0,
                    "title": r.get("title", "")
                })

            # 3. YouTube video / deepfake / audio leak extraction
            for y in channels.get("youtube", []):
                mentions.append({
                    "source": "YouTube",
                    "author": y.get("channel", "YouTube Video"),
                    "content": f"[Video/Audio Signal] {y.get('title', '')}",
                    "url": y.get("url", ""),
                    "likes": 0,
                    "retweets": 0,
                    "title": y.get("title", ""),
                    "is_video": True
                })

            # 4. Optional Apify enhancement if token exists

            if self.apify_client and len(mentions) < max_results:
                try:
                    actor = self.apify_client.actor("apidojo/tweet-scraper")
                    run = actor.call(
                        run_input={"searchTerms": [f'"{vip_name}"'], "maxTweets": 5},
                        timeout_secs=30
                    )
                    if run and run.get("status") == "SUCCEEDED":
                        dataset_id = run.get("defaultDatasetId")
                        if dataset_id:
                            dataset = self.apify_client.dataset(dataset_id)
                            for item in dataset.list_items().get("items", []):
                                mentions.append({
                                    "source": "Twitter",
                                    "author": item.get("author", {}).get("userName", "Unknown"),
                                    "content": item.get("text", ""),
                                    "url": item.get("url", ""),
                                    "likes": item.get("likeCount", 0),
                                    "retweets": item.get("retweetCount", 0)
                                })
                except Exception as apify_err:
                    logger.debug(f"[PersonalWatch] Apify client attempt notice: {apify_err}")

            logger.info(f"[PersonalWatch] Found {len(mentions)} social mentions for {vip_name}")
            return mentions[:max_results]

        except Exception as e:
            logger.error(f"[PersonalWatch] Error searching social mentions: {str(e)}")
            return []
    
    def scan(self, vip_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete scan for a VIP profile.
        
        Args:
            vip_profile: Dict containing VIP info (name, official_handles, etc.)
            
        Returns:
            Dict containing all detected mentions and analyzed threats
        """
        vip_name = vip_profile.get("name", "")
        official_handles = vip_profile.get("official_handles", {})
        twitter_handle = official_handles.get("twitter")
        
        logger.info(f"🔍 Starting Personal Watch scan for: {vip_name}")
        
        # Step 1: Gather mentions from all sources
        web_mentions = self.search_web_mentions(vip_name)
        twitter_mentions = self.search_social_mentions(vip_name, twitter_handle)
        
        # Combine all mentions
        all_mentions = web_mentions + twitter_mentions
        
        logger.info(f"Found {len(all_mentions)} total mentions ({len(web_mentions)} web, {len(twitter_mentions)} Twitter)")
        
        # Step 2: Analyze threats using Gemini
        analyzed_threats = []
        if all_mentions:
            try:
                try:
                    from backend.services.intelligence import analyze_security_risk
                except (ImportError, ModuleNotFoundError):
                    from services.intelligence import analyze_security_risk
                logger.info(f"Analyzing security risks for {len(all_mentions)} mentions...")
                analyzed_threats = analyze_security_risk(all_mentions, vip_name)
                logger.info(f"Analysis complete: {len(analyzed_threats)} threats identified")
            except Exception as e:
                logger.error(f"Failed to analyze security risks: {str(e)}")
        
        # Step 3: Filter high-risk threats
        high_risk_threats = [t for t in analyzed_threats if t.get('risk_level') == 'HIGH']
        medium_risk_threats = [t for t in analyzed_threats if t.get('risk_level') == 'MEDIUM']
        
        logger.info(f"🚨 Risk summary: {len(high_risk_threats)} HIGH, {len(medium_risk_threats)} MEDIUM")
        
        # Step 4: Send alerts for HIGH risk threats
        alerts_sent = 0
        if high_risk_threats and vip_profile.get("phone_number"):
            try:
                try:
                    from backend.services.notifier import send_security_alert
                except (ImportError, ModuleNotFoundError):
                    from services.notifier import send_security_alert
                phone_number = vip_profile.get("phone_number")
                
                for threat in high_risk_threats:
                    logger.warning(f"HIGH RISK THREAT: {threat.get('threat_type')} - {threat.get('reason')}")
                    
                    # Send WhatsApp alert
                    content = threat.get('content', '') or threat.get('title', '')
                    success = send_security_alert(
                        to_number=phone_number,
                        threat_type=threat.get('threat_type', 'UNKNOWN'),
                        content_preview=content,
                        vip_name=vip_name,
                        use_whatsapp=True
                    )
                    
                    if success:
                        alerts_sent += 1
                        
                logger.info(f"📱 Sent {alerts_sent}/{len(high_risk_threats)} WhatsApp alerts")
                
            except Exception as e:
                logger.error(f"Failed to send alerts: {str(e)}")
        
        return {
            "vip_name": vip_name,
            "total_mentions": len(all_mentions),
            "web_mentions": len(web_mentions),
            "twitter_mentions": len(twitter_mentions),
            "mentions": all_mentions,
            "threats": analyzed_threats,
            "high_risk_count": len(high_risk_threats),
            "medium_risk_count": len(medium_risk_threats),
            "low_risk_count": len(analyzed_threats) - len(high_risk_threats) - len(medium_risk_threats),
            "alerts_sent": alerts_sent
        }


# Alias for backward compatibility
PersonalAgent = PersonalWatchAgent
personal_watch_agent = PersonalWatchAgent()


def process_personal_watch(vip_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    External interface for processing Personal Watch scans.
    
    Args:
        vip_profile: VIP profile dictionary
        
    Returns:
        Scan results dictionary
    """
    return personal_watch_agent.scan(vip_profile)
