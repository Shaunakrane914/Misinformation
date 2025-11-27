"""
Alerts Service.
Handles detection of critical threats and notifications.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def check_critical_threats(report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scan the aggregated report for critical threats.
    Criteria: is_threat=True AND sentiment_score < -70.
    """
    critical_items = []
    
    sources = report_data.get("sources", {})
    all_items = []
    
    # Aggregate all items
    all_items.extend(sources.get("news", []))
    all_items.extend(sources.get("paparazzi", []))
    all_items.extend(sources.get("fan_wars", []))
    
    for item in all_items:
        is_threat = item.get("is_threat", False)
        sentiment = item.get("sentiment_score", 0)
        
        # Ensure sentiment is an integer
        try:
            sentiment = int(sentiment)
        except (ValueError, TypeError):
            sentiment = 0
            
        if is_threat and sentiment < -70:
            logger.critical(f"🚨 CRITICAL THREAT DETECTED: {item.get('title') or item.get('text') or item.get('caption')} (Score: {sentiment})")
            critical_items.append(item)
            
    if critical_items:
        logger.info(f"Found {len(critical_items)} critical threats requiring immediate attention.")
        # In a real system, we would send SMS/Email/Slack alerts here.
        
    return critical_items
