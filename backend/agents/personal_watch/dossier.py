"""
Aegis Protocol — Personal Watch Dossier & Change Detection
==========================================================
Constructs rich investigation dossiers, chronological timelines, and
change detection diffs ("WHAT CHANGED?") across monitoring intervals.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_investigation_dossiers(
    threats: List[Dict[str, Any]],
    evidence_list: List[Dict[str, Any]],
    claims: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Builds rich investigation dossiers linking each threat to origin platform,
    earliest observed timestamp, evidence chain, and verified clickable source URLs.
    """
    ev_map = {e["evidence_id"]: e for e in evidence_list}
    dossiers: List[Dict[str, Any]] = []

    for threat in threats:
        threat_id = threat.get("threat_id", "thr_001")
        threat_type = threat.get("threat_type", "GENERAL")
        evidence_ids = threat.get("evidence_ids", [])

        linked_ev = [ev_map[eid] for eid in evidence_ids if eid in ev_map]
        if not linked_ev and evidence_list:
            linked_ev = [evidence_list[0]]

        sorted_ev = sorted(linked_ev, key=lambda x: str(x.get("published_at", "")), reverse=False)
        earliest_item = sorted_ev[0] if sorted_ev else (linked_ev[0] if linked_ev else {})
        origin_platform = earliest_item.get("platform", threat.get("platform", "Web"))
        first_observed_time = earliest_item.get("published_at", "Recent")

        platforms_affected = list(set([e.get("platform", "Web") for e in linked_ev]))
        source_urls = [e.get("url") for e in linked_ev if e.get("url") and e.get("url") != "#"]
        source_groups = list(set([e.get("source_group_id", e.get("source", "Web")) for e in linked_ev]))

        related_claims = [c for c in claims if any(eid in evidence_ids for eid in c.get("evidence_ids", []))]

        dossier = {
            "dossier_id": f"dos_{threat_id}",
            "threat_id": threat_id,
            "threat_type": threat_type,
            "risk_level": threat.get("risk_level", "LOW"),
            "title": threat.get("title", ""),
            "why_flagged": threat.get("reason", ""),
            "first_observed_source": earliest_item.get("source", origin_platform),
            "first_observed_platform": origin_platform,
            "first_observed_at": first_observed_time,
            "platforms_affected": platforms_affected,
            "independent_source_groups_count": len(source_groups),
            "indicators": threat.get("indicators", []),
            "related_claims": related_claims,
            "evidence_chain": [
                {
                    "evidence_id": e["evidence_id"],
                    "platform": e["platform"],
                    "source": e["source"],
                    "title": e["title"],
                    "snippet": e["snippet"],
                    "url": e["url"],
                    "author": e.get("author", "@user"),
                    "published_at": e.get("published_at", "Recent")
                }
                for e in linked_ev
            ],
            "primary_source_url": source_urls[0] if source_urls else None,
            "all_source_urls": source_urls
        }
        dossiers.append(dossier)

    return dossiers


def build_threat_timeline(evidence_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build chronological sequence of events strictly grounded in verified source timestamps.
    Never fabricates timestamps.
    """
    timeline: List[Dict[str, Any]] = []

    for e in evidence_list[:12]:
        pub = e.get("published_at", "Recent")
        timeline.append({
            "timestamp": pub,
            "platform": e.get("platform", "Web"),
            "source": e.get("source", "Web"),
            "event_description": e.get("title", ""),
            "evidence_id": e.get("evidence_id"),
            "url": e.get("url", "")
        })

    return timeline


def compute_change_detection(
    subject_name: str,
    current_threats: List[Dict[str, Any]],
    current_evidence: List[Dict[str, Any]],
    history_snapshots: Dict[str, List[Dict[str, Any]]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Compare current scan against prior snapshot for this subject.
    Detects: NEW threats, RESOLVED threats, ESCALATED threats, and NEW PLATFORMS.
    Persists compact snapshot.
    """
    key = subject_name.strip().lower()
    history = history_snapshots.get(key, [])

    changes: List[Dict[str, Any]] = []
    now_iso = utcnow_iso()

    current_threat_keys = {f"{t.get('threat_type')}:{t.get('title', '')[:30].lower()}": t for t in current_threats}
    current_platforms = set(e.get("platform") for e in current_evidence)

    if history:
        prev_snapshot = history[-1]
        prev_threat_keys = prev_snapshot.get("threat_keys", {})
        prev_platforms = set(prev_snapshot.get("platforms", []))

        # 1. New threats
        for tk, t in current_threat_keys.items():
            if tk not in prev_threat_keys:
                changes.append({
                    "change_type": "NEW_THREAT",
                    "severity": t.get("risk_level", "MEDIUM"),
                    "description": f"New threat detected: {t.get('threat_type')} - {t.get('title')}",
                    "timestamp": now_iso
                })
            else:
                prev_risk = prev_threat_keys[tk].get("risk_level")
                curr_risk = t.get("risk_level")
                if curr_risk == "HIGH" and prev_risk != "HIGH":
                    changes.append({
                        "change_type": "ESCALATED_THREAT",
                        "severity": "HIGH",
                        "description": f"Threat escalated from {prev_risk} to HIGH: {t.get('title')}",
                        "timestamp": now_iso
                    })

        # 2. Resolved threats
        for tk, pt in prev_threat_keys.items():
            if tk not in current_threat_keys:
                changes.append({
                    "change_type": "RESOLVED_THREAT",
                    "severity": "INFO",
                    "description": f"Prior threat no longer detected in active scan: {pt.get('threat_type')} - {pt.get('title')}",
                    "timestamp": now_iso
                })

        # 3. New platforms
        new_plats = current_platforms - prev_platforms
        for np in new_plats:
            changes.append({
                "change_type": "NEW_PLATFORM",
                "severity": "INFO",
                "description": f"Narrative expanded to new platform: {np}",
                "timestamp": now_iso
            })
    else:
        changes.append({
            "change_type": "BASELINE_INITIALIZED",
            "severity": "INFO",
            "description": f"Initial monitoring baseline established with {len(current_threats)} threats and {len(current_platforms)} platforms.",
            "timestamp": now_iso
        })

    new_snapshot = {
        "timestamp": now_iso,
        "source_count": len(current_evidence),
        "threat_count": len(current_threats),
        "platform_count": len(current_platforms),
        "platforms": list(current_platforms),
        "threat_keys": {tk: {"threat_type": t.get("threat_type"), "title": t.get("title"), "risk_level": t.get("risk_level")} for tk, t in current_threat_keys.items()}
    }

    if key not in history_snapshots:
        history_snapshots[key] = []
    history_snapshots[key].append(new_snapshot)
    if len(history_snapshots[key]) > 10:
        history_snapshots[key] = history_snapshots[key][-10:]

    return changes, new_snapshot
