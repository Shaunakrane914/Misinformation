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
        Search the web for mentions of the VIP using DuckDuckGo.
        
        Args:
            vip_name: Name of the VIP to search for
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with title, link, and snippet
        """
        try:
            logger.info(f"Searching web for mentions of: {vip_name}")
            
            # Use DuckDuckGo search
            ddgs = DDGS()
            results = ddgs.text(vip_name, max_results=max_results)
            
            # Format results
            mentions = []
            for result in results:
                mentions.append({
                    "source": "Web",
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                    "content": f"{result.get('title', '')} - {result.get('body', '')}"
                })
            
            logger.info(f"Found {len(mentions)} web mentions")
            return mentions
            
        except Exception as e:
            logger.error(f"Error searching web mentions: {str(e)}")
            return []
    
    def search_social_mentions(
        self, 
        vip_name: str, 
        official_handle: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Twitter for mentions of the VIP, excluding their own posts.
        
        Args:
            vip_name: Name of the VIP to search for
            official_handle: VIP's official Twitter handle (to exclude their posts)
            max_results: Maximum number of results to return
            
        Returns:
            List of tweets mentioning the VIP
        """
        if not self.apify_client:
            logger.warning("Apify client not available - skipping Twitter search")
            return []
        
        try:
            logger.info(f"Searching Twitter for mentions of: {vip_name}")
            
            # Build search query - exclude VIP's own posts
            if official_handle:
                # Remove @ if present
                handle = official_handle.lstrip('@')
                query = f'"{vip_name}" -from:{handle}'
            else:
                query = f'"{vip_name}"'
            
            logger.info(f"Twitter query: {query}")
            
            # Run Apify Twitter scraper
            actor = self.apify_client.actor("apidojo/tweet-scraper")
            run = actor.call(
                run_input={
                    "searchTerms": [query],
                    "maxTweets": max_results,
                    "includeSearchTerms": True
                },
                timeout_secs=120
            )
            
            if not run or run.get("status") != "SUCCEEDED":
                logger.error(f"Twitter scraper failed with status: {run.get('status') if run else 'No run'}")
                return []
            
            # Get results
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                logger.error("No dataset ID in Twitter scraper results")
                return []
            
            dataset = self.apify_client.dataset(dataset_id)
            items = dataset.list_items().get("items", [])
            
            # Format results
            mentions = []
            for item in items:
                mentions.append({
                    "source": "Twitter",
                    "author": item.get("author", {}).get("userName", "Unknown"),
                    "content": item.get("text", ""),
                    "url": item.get("url", ""),
                    "likes": item.get("likeCount", 0),
                    "retweets": item.get("retweetCount", 0)
                })
            
            logger.info(f"Found {len(mentions)} Twitter mentions")
            return mentions
            
        except Exception as e:
            logger.error(f"Error searching Twitter mentions: {str(e)}")
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
                from backend.services.intelligence import analyze_security_risk
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
                from backend.services.notifier import send_security_alert
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


# Global instance
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
