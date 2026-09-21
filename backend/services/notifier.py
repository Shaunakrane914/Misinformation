"""
Notifier Service
================
Handles sending alerts via Twilio (WhatsApp/SMS) with rich structured context,
verified source link inclusion, alert deduplication, cooldown windows,
and preference filtering for Personal Watch 2.0.
"""

import os
import time
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple
from twilio.rest import Client

logger = logging.getLogger(__name__)


class PersonalAlertManager:
    """
    Manages alerting deduplication and cooldown for Personal Watch 2.0.
    Prevents alert storms by tracking threat fingerprints and suppression windows.
    """

    def __init__(self, default_cooldown_seconds: int = 3600):
        self.default_cooldown_seconds = default_cooldown_seconds
        # Key: fingerprint string -> { 'timestamp': float, 'evidence_count': int, 'risk_level': str }
        self._sent_alerts: Dict[str, Dict[str, Any]] = {}

    def _generate_fingerprint(self, subject: str, threat: Dict[str, Any]) -> str:
        """Generate a deterministic fingerprint for a threat instance."""
        subject_norm = subject.strip().lower()
        threat_type = threat.get("threat_type", "GENERAL").upper()
        
        # Use claim, title or core reason for fingerprinting
        core_text = threat.get("title", "") or threat.get("reason", "") or threat.get("content", "")
        norm_text = " ".join(core_text.lower().split()[:15])  # first 15 tokens
        
        raw_key = f"{subject_norm}:{threat_type}:{norm_text}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    def should_send_alert(
        self,
        subject: str,
        threat: Dict[str, Any],
        alert_preference: str = "HIGH_ONLY",
        cooldown_seconds: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Determine whether an alert should be dispatched based on preferences,
        prior history, and cooldown.
        """
        risk_level = threat.get("risk_level", "LOW").upper()
        pref = (alert_preference or "HIGH_ONLY").upper()

        # 1. Alert preference filtering
        if pref == "HIGH_ONLY" and risk_level != "HIGH":
            return False, f"filtered_by_preference_{pref}"
        if pref in ("HIGH_AND_MEDIUM", "HIGH_MEDIUM") and risk_level not in ("HIGH", "MEDIUM"):
            return False, f"filtered_by_preference_{pref}"

        # 2. Cooldown & change detection
        cooldown = cooldown_seconds if cooldown_seconds is not None else self.default_cooldown_seconds
        fingerprint = self._generate_fingerprint(subject, threat)
        now = time.time()

        if fingerprint in self._sent_alerts:
            last_record = self._sent_alerts[fingerprint]
            elapsed = now - last_record["timestamp"]
            prev_evidence_count = last_record.get("evidence_count", 1)
            curr_evidence_count = len(threat.get("evidence_ids", [])) or 1

            # If inside cooldown window, only allow if significant new evidence emerged (>= 2 new sources)
            if elapsed < cooldown:
                if curr_evidence_count >= prev_evidence_count + 2:
                    logger.info(f"[AlertManager] Breaking cooldown due to significant evidence growth (+{curr_evidence_count - prev_evidence_count})")
                    return True, "escalated_evidence_growth"
                return False, f"cooldown_active_{int(cooldown - elapsed)}s_remaining"

        return True, "alert_permitted"

    def record_alert(self, subject: str, threat: Dict[str, Any], success: bool = True):
        """Record dispatched alert for cooldown tracking."""
        if not success:
            return
        fingerprint = self._generate_fingerprint(subject, threat)
        self._sent_alerts[fingerprint] = {
            "timestamp": time.time(),
            "evidence_count": len(threat.get("evidence_ids", [])) or 1,
            "risk_level": threat.get("risk_level", "LOW").upper(),
            "threat_type": threat.get("threat_type", "GENERAL"),
        }

    def clear_cache(self):
        """Reset sent alerts cache (useful in tests)."""
        self._sent_alerts.clear()


# Global alert manager singleton
alert_manager = PersonalAlertManager()


def send_security_alert(
    to_number: str,
    threat_type: str,
    content_preview: str,
    vip_name: str,
    use_whatsapp: bool = True,
    source_url: Optional[str] = None,
    evidence_count: int = 1,
    independent_groups: int = 1,
    first_observed: Optional[str] = None,
    reason: Optional[str] = None,
    dossier_url: Optional[str] = None
) -> bool:
    """
    Send a structured personal threat alert via Twilio (WhatsApp/SMS).
    Includes verified source links, factual evidence context, and reason.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        logger.warning("Twilio credentials not found - skipping live alert dispatch")
        return False

    try:
        client = Client(account_sid, auth_token)

        # Build structured message following Section 29 requirements
        body_lines = [
            "🚨 *AEGIS PERSONAL WATCH*",
            "*HIGH-PRIORITY THREAT EVENT*",
            "",
            f"👤 *Subject:* {vip_name}",
            f"⚠️ *Threat:* {threat_type}",
            f"📊 *Evidence:* {evidence_count} source(s) · {independent_groups} independent group(s)",
        ]

        if first_observed:
            body_lines.append(f"🕒 *First Observed:* {first_observed}")

        flag_reason = reason or content_preview
        if flag_reason:
            body_lines.append(f"🎯 *Why Flagged:* {flag_reason[:140]}")

        # Enforce real source URL preservation
        if source_url and source_url.startswith("http") and source_url != "#":
            body_lines.append(f"🔗 *Source:* {source_url}")

        if dossier_url and dossier_url.startswith("http"):
            body_lines.append(f"📁 *Open Dossier:* {dossier_url}")
        else:
            body_lines.append("📁 *Open Dossier:* Check Personal Watch Dashboard")

        body = "\n".join(body_lines)

        to_addr = f"whatsapp:{to_number}" if use_whatsapp else to_number
        from_addr = f"whatsapp:{from_number}" if use_whatsapp else from_number

        message = client.messages.create(
            body=body,
            from_=from_addr,
            to=to_addr
        )

        logger.info(f"🚨 Structured alert sent to {to_number}: {message.sid}")
        return True

    except Exception as e:
        logger.error(f"Failed to send Twilio alert: {str(e)}")
        return False
