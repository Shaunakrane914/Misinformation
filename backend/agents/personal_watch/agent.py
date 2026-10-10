"""
Aegis Protocol — Personal Watch Agent 2.0
=========================================
Autonomous personal identity protection and online threat intelligence agent.
Monitors public figures, executives, creators, researchers, and employees.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from apify_client import ApifyClient
from backend.agents.personal_watch.assessment import (
    heuristic_threat_synthesis,
    synthesize_personal_threats,
)
from backend.agents.personal_watch.dossier import (
    build_investigation_dossiers,
    build_threat_timeline,
    compute_change_detection,
)
from backend.agents.personal_watch.identity import resolve_personal_entity
from backend.agents.personal_watch.models import (
    KNOWN_PUBLIC_PROFILES,
    SENSITIVE_PII_KEYWORDS,
    THREAT_TAXONOMY,
    CareerEvent,
    PersonalWatchExtractionResult,
    PublicStatement,
)
from backend.agents.personal_watch.monitoring import (
    analyze_spread_and_velocity,
    deduplicate_and_group_evidence,
    extract_domain,
    normalize_item,
    search_personal_evidence,
    utcnow_iso,
)

logger = logging.getLogger(__name__)


class PersonalWatchAgent:
    """
    Personal Watch 2.0: Personal Identity & Online Threat Intelligence System.
    Provides OSINT-grounded evidence collection, entity resolution, threat clustering,
    dossiers, clickable source provenance, change detection, and alert management.
    """

    def __init__(self):
        apify_token = os.getenv("APIFY_TOKEN")
        if apify_token:
            self.apify_client = ApifyClient(apify_token)
        else:
            self.apify_client = None

        # In-memory monitoring snapshots for Change Detection ("WHAT CHANGED?")
        # Key: canonical_name.lower() -> List[snapshot_dict]
        self._history_snapshots: Dict[str, List[Dict[str, Any]]] = {}
        self._last_research_res = None

        logger.info("[PersonalWatch 2.0] Agent initialized with Agent Reach backbone")

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Subject Profile & Entity Resolution
    # ─────────────────────────────────────────────────────────────────────────

    def resolve_personal_entity(self, profile_or_name: Any) -> Dict[str, Any]:
        """Resolve subject identity from raw name or structured profile."""
        return resolve_personal_entity(profile_or_name)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Multi-Channel Retrieval via Agent Reach
    # ─────────────────────────────────────────────────────────────────────────

    def search_personal_evidence(
        self,
        subject_info: Dict[str, Any],
        max_results: int = 24,
        timeout: float = 12.0
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, Any], int]:
        """Execute domain-specific multi-channel retrieval using the Agent Reach backbone."""
        deduped, channel_health, retrieval_plan_info, syndication_count, last_res = search_personal_evidence(
            subject_info=subject_info, max_results=max_results, timeout=timeout
        )
        self._last_research_res = last_res
        return deduped, channel_health, retrieval_plan_info, syndication_count

    def _normalize_item(self, item: Dict[str, Any], default_platform: str, source_role: str, subject: str) -> Dict[str, Any]:
        return normalize_item(item, default_platform, source_role, subject)

    def _extract_domain(self, url: str) -> str:
        return extract_domain(url)

    def _deduplicate_and_group_evidence(self, items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        return deduplicate_and_group_evidence(items)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Grounded Threat & Claim Reasoning
    # ─────────────────────────────────────────────────────────────────────────

    def _synthesize_personal_threats(
        self,
        subject_info: Dict[str, Any],
        evidence_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return synthesize_personal_threats(subject_info, evidence_list)

    def _heuristic_threat_synthesis(self, subject_name: str, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        return heuristic_threat_synthesis(subject_name, evidence_list)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Investigation Dossier Builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_investigation_dossiers(
        self,
        threats: List[Dict[str, Any]],
        evidence_list: List[Dict[str, Any]],
        claims: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return build_investigation_dossiers(threats, evidence_list, claims)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Spread & Velocity Analysis
    # ─────────────────────────────────────────────────────────────────────────

    def _analyze_spread_and_velocity(self, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        return analyze_spread_and_velocity(evidence_list)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Personal Threat Timeline
    # ─────────────────────────────────────────────────────────────────────────

    def _build_threat_timeline(self, evidence_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return build_threat_timeline(evidence_list)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Change Detection ("WHAT CHANGED?") & Snapshots
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_change_detection(
        self,
        subject_name: str,
        current_threats: List[Dict[str, Any]],
        current_evidence: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        return compute_change_detection(
            subject_name=subject_name,
            current_threats=current_threats,
            current_evidence=current_evidence,
            history_snapshots=self._history_snapshots,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Main Public Interface: scan()
    # ─────────────────────────────────────────────────────────────────────────

    def scan(self, vip_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Execute full Personal Watch 2.0 scan for an individual or executive profile."""
        start_time = time.time()

        subject_info = self.resolve_personal_entity(vip_profile)
        subject_name = subject_info["canonical_name"]

        logger.info(f"[PersonalWatch 2.0] Initiating intelligence scan for '{subject_name}'")

        evidence_list, channel_health, retrieval_plan_info, syndicated_count = self.search_personal_evidence(
            subject_info=subject_info,
            max_results=24,
            timeout=12.0
        )

        synthesis = self._synthesize_personal_threats(subject_info, evidence_list)
        threats = synthesis.get("threats", [])
        claims = synthesis.get("claims", [])
        narratives = synthesis.get("narratives", [])
        impersonations = synthesis.get("suspected_impersonations", [])
        scams = synthesis.get("suspected_scams", [])
        deepfakes = synthesis.get("deepfake_claims", [])

        dossiers = self._build_investigation_dossiers(threats, evidence_list, claims)
        spread_analysis = self._analyze_spread_and_velocity(evidence_list)
        timeline = self._build_threat_timeline(evidence_list)
        changes, snapshot = self._compute_change_detection(subject_name, threats, evidence_list)

        high_risk_threats = [t for t in threats if t.get("risk_level") == "HIGH"]
        medium_risk_threats = [t for t in threats if t.get("risk_level") == "MEDIUM"]
        low_risk_threats = [t for t in threats if t.get("risk_level") == "LOW"]

        phone_number = vip_profile.get("phone_number") if isinstance(vip_profile, dict) else subject_info.get("phone_number")
        alert_preference = subject_info.get("alert_preferences", {}).get("level", "HIGH_ONLY")
        alerts_sent = 0
        alert_logs: List[Dict[str, Any]] = []

        if phone_number and threats:
            try:
                try:
                    from backend.services.notifier import alert_manager, send_security_alert
                except (ImportError, ModuleNotFoundError):
                    from services.notifier import alert_manager, send_security_alert

                for threat in threats:
                    should_send, reason_code = alert_manager.should_send_alert(
                        subject=subject_name,
                        threat=threat,
                        alert_preference=alert_preference
                    )

                    if should_send:
                        ev_ids = threat.get("evidence_ids", [])
                        matching_ev = [e for e in evidence_list if e.get("evidence_id") in ev_ids]
                        src_url = matching_ev[0].get("url") if matching_ev else None
                        first_obs = matching_ev[0].get("published_at") if matching_ev else "Recent"

                        success = send_security_alert(
                            to_number=phone_number,
                            threat_type=threat.get("threat_type", "UNKNOWN"),
                            content_preview=threat.get("title", ""),
                            vip_name=subject_name,
                            use_whatsapp=True,
                            source_url=src_url,
                            evidence_count=len(matching_ev) or 1,
                            independent_groups=len(set(e.get("source_group_id", e.get("source")) for e in matching_ev)) or 1,
                            first_observed=first_obs,
                            reason=threat.get("reason", ""),
                            dossier_url=None
                        )

                        if success:
                            alerts_sent += 1
                            alert_manager.record_alert(subject=subject_name, threat=threat, success=True)
                            alert_logs.append({
                                "threat_id": threat.get("threat_id"),
                                "status": "dispatched",
                                "recipient": phone_number
                            })
                    else:
                        alert_logs.append({
                            "threat_id": threat.get("threat_id"),
                            "status": "suppressed",
                            "reason": reason_code
                        })

            except Exception as alert_err:
                logger.error(f"[PersonalWatch 2.0] Alert dispatch error: {alert_err}")

        scan_duration_s = round(time.time() - start_time, 2)

        web_mentions = [e for e in evidence_list if e.get("platform") in ("Web", "News", "RSS")]
        twitter_mentions = [e for e in evidence_list if e.get("platform") in ("Twitter/X", "Twitter")]

        unique_sources = len(set(e.get("source", "Web") for e in evidence_list))
        independent_groups = len(set(e.get("source_group_id", e.get("source", "Web")) for e in evidence_list))

        summary = {
            "sources_scanned": len(evidence_list),
            "unique_sources": unique_sources,
            "independent_groups": independent_groups,
            "threats_discovered": len(threats),
            "unverified_claims": len([c for c in claims if c.get("status") in ("unverified", "unknown")]),
            "high_priority_items": len(high_risk_threats),
            "platforms_active": len(set(e.get("platform") for e in evidence_list)),
            "scan_duration_s": scan_duration_s,
            "last_updated": utcnow_iso()
        }

        limitations = [
            "Personal Watch strictly observes publicly available online information.",
            "Private PII (phone numbers, private addresses, family data) is strictly omitted.",
            "Technical media forensic verification (e.g. Mel-spectrogram model) is reported as unavailable unless explicitly executed.",
            "Social community posts are treated as unverified public discourse, not authoritative factual proof."
        ]

        return {
            # Backward compatibility keys
            "vip_name": subject_name,
            "total_mentions": len(evidence_list),
            "web_mentions": len(web_mentions),
            "twitter_mentions": len(twitter_mentions),
            "mentions": evidence_list,
            "threats": threats,
            "high_risk_count": len(high_risk_threats),
            "medium_risk_count": len(medium_risk_threats),
            "low_risk_count": len(low_risk_threats),
            "alerts_sent": alerts_sent,

            # Personal Watch 2.0 Intelligence Dossier
            "subject": subject_info,
            "scan_metadata": {
                "scan_id": f"pw_scan_{hashlib.md5(f'{subject_name}:{time.time()}'.encode()).hexdigest()[:8]}",
                "scanned_at": utcnow_iso(),
                "duration_seconds": scan_duration_s,
                "ai_enrichment_active": synthesis.get("ai_enrichment_active", False)
            },
            "channel_health": channel_health,
            "retrieval_plan": retrieval_plan_info,
            "summary": summary,
            "claims": claims,
            "narratives": narratives,
            "suspected_impersonations": impersonations,
            "suspected_scams": scams,
            "deepfake_claims": deepfakes,
            "evidence": evidence_list,
            "dossiers": dossiers,
            "findings": [f.to_dict() if hasattr(f, "to_dict") else f for f in self._last_research_res.findings] if getattr(self, "_last_research_res", None) else [],
            "contradictions": [c.to_dict() if hasattr(c, "to_dict") else c for c in self._last_research_res.contradictions] if getattr(self, "_last_research_res", None) else [],
            "deep_research_trace": retrieval_plan_info.get("trace", {}),
            "deep_reads": retrieval_plan_info.get("trace", {}).get("deep_read_success", 0),
            "spread_analysis": spread_analysis,
            "timeline": timeline,
            "changes": changes,
            "alerts": alert_logs,
            "retrieval_trace": retrieval_plan_info.get("trace", {}),
            "limitations": limitations
        }

    def generate_personal_watch_intelligence(
        self,
        person: str,
        monitoring_scope: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Aegis Protocol Output Contract implementation for Personal Watch Agent."""
        profile = {
            "name": person,
            "category": category or "public_figure",
            "monitoring_scope": monitoring_scope or ["public statements", "career moves", "publications"]
        }
        scan_res = self.scan(vip_profile=profile)
        subject_info = scan_res.get("subject", {})
        canonical_name = subject_info.get("canonical_name") or person
        confidence = float(subject_info.get("confidence", 0.85))

        evidence_items = scan_res.get("evidence", [])
        threats = scan_res.get("threats", [])
        claims = scan_res.get("claims", [])
        changes = scan_res.get("changes", {})
        timeline = scan_res.get("timeline", [])

        # 1. Observed facts
        observed: List[str] = []
        for ev in evidence_items[:5]:
            observed.append(f"Public citation ({ev.get('platform')}/{ev.get('source')}): {ev.get('title')}")
        for imp in scan_res.get("suspected_impersonations", [])[:2]:
            observed.append(f"Discovered lookalike/impersonation profile: {imp.get('title')}")

        # 2. Inferred interpretations
        inferred: List[str] = []
        if isinstance(changes, dict) and changes.get("has_changes"):
            inferred.append("Material change detected across monitored public profiles since previous interval.")
        else:
            inferred.append("Public footprint remains consistent with baseline activity.")
        if scan_res.get("high_risk_count", 0) > 0:
            inferred.append(f"High-priority threat exposure detected: {scan_res.get('high_risk_count')} severe vectors flagged.")

        # 3. Uncertain / Unknown
        uncertain: List[str] = []
        for c in claims:
            if c.get("status") in ("unverified", "unknown"):
                uncertain.append(f"Unverified public claim: {c.get('claim_text')}")
        for contra in scan_res.get("contradictions", []):
            uncertain.append(f"Contradictory statement noted: {contra}")
        if not evidence_items:
            uncertain.append(f"No public signals found for {canonical_name} within requested monitoring scope.")

        status = "no_material_change"
        if scan_res.get("contradictions"):
            status = "contradicted"
        elif isinstance(changes, dict) and changes.get("has_changes"):
            status = "material_change"
        elif any(c.get("status") == "verified" for c in claims):
            status = "confirmed"
        elif evidence_items:
            status = "new_information"

        retrieval_trace = scan_res.get("retrieval_trace", {})
        fallback_used = retrieval_trace.get("fallback_rate", 0.0) > 0.0
        fallback_reason = "SEARCH_INDEX_FALLBACK" if fallback_used else None

        privacy_flags = [
            "PII_GUARD_ACTIVE: Private contact details, residential addresses, and family data strictly suppressed."
        ]
        if any(t.get("threat_type") == "DOXXING_PRIVACY" for t in threats):
            privacy_flags.append("POTENTIAL_PUBLIC_LEAK_SIGNAL: Public mention of leaked credentials or private files detected.")

        updates = []
        if isinstance(changes, dict):
            updates = changes.get("new_threats", []) + changes.get("resolved_threats", [])
        elif isinstance(changes, list):
            updates = changes

        return {
            "agent": "personal_watch",
            "person": canonical_name,
            "identity_confidence": round(confidence, 2),
            "monitoring_scope": monitoring_scope or ["public statements", "career moves", "publications"],
            "status": status,
            "updates": updates,
            "observed": observed,
            "inferred": inferred,
            "uncertain": uncertain,
            "timeline": timeline,
            "sources": evidence_items,
            "corroboration": scan_res.get("findings", []),
            "contradictions": scan_res.get("contradictions", []),
            "privacy_flags": privacy_flags,
            "retrieval": {
                "direct": not fallback_used,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason
            }
        }

    # Backward-compatible aliases
    generate_intelligence = generate_personal_watch_intelligence


PersonalAgent = PersonalWatchAgent
personal_watch_agent = PersonalWatchAgent()


def process_personal_watch(vip_profile: Dict[str, Any]) -> Dict[str, Any]:
    """External entry point for Personal Watch 2.0 scans."""
    return personal_watch_agent.scan(vip_profile)


__all__ = [
    "PersonalWatchAgent",
    "PersonalAgent",
    "personal_watch_agent",
    "process_personal_watch",
]
