"""
Notifier Service
================
Handles sending alerts via Twilio (WhatsApp/SMS).
"""

import os
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

def send_security_alert(to_number: str, threat_type: str, content_preview: str, vip_name: str, use_whatsapp: bool = True) -> bool:
    """
    Send a security alert to the VIP via Twilio.
    
    Args:
        to_number: Phone number to send alert to (e.g., "+1234567890")
        threat_type: Type of threat (IMPERSONATION, DOXXING, etc.)
        content_preview: Short preview of the threat content
        vip_name: Name of the VIP
        use_whatsapp: Whether to send via WhatsApp (default True)
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    
    if not all([account_sid, auth_token, from_number]):
        logger.warning("Twilio credentials not found - skipping alert")
        return False
        
    try:
        client = Client(account_sid, auth_token)
        
        # Format message
        body = (
            f"🚨 *SECURITY ALERT for {vip_name}*\n\n"
            f"⚠️ *Type:* {threat_type}\n"
            f"📝 *Content:* {content_preview[:100]}...\n\n"
            f"Please check your Personal Watch Dashboard for details."
        )
        
        # Add whatsapp: prefix if using WhatsApp
        to_addr = f"whatsapp:{to_number}" if use_whatsapp else to_number
        from_addr = f"whatsapp:{from_number}" if use_whatsapp else from_number
        
        message = client.messages.create(
            body=body,
            from_=from_addr,
            to=to_addr
        )
        
        logger.info(f"🚨 Alert sent to {to_number}: {message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send Twilio alert: {str(e)}")
        return False
