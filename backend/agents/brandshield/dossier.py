"""
Aegis Protocol — BrandShield Investigation Dossier Construction
================================================================
Builds forensic investigation dossiers linking threats to origin sources,
affected platforms, evidence chains, and verified URLs.
"""

from typing import Any, Dict, List


def _claim_text(claim):
    """Read observed legacy/structured claim fields without inventing prose."""
    if not isinstance(claim, dict):
        return ""
    for key in ("claim_text", "text", "claim", "statement"):
        value = claim.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for nested in ("text", "statement", "claim_text"):
                if isinstance(value.get(nested), str) and value[nested].strip():
                    return value[nested].strip()
    return ""


def build_investigation_dossiers(
    brand_info: Dict[str, Any],
    threats: List[Dict[str, Any]],
    claims: List[Dict[str, Any]],
    evidence_list: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Build exhaustive investigation dossiers for identified threats,
    linking each threat to its underlying claims, affected platforms, and source URLs.
    """
    dossiers = []
    ev_map = {e["evidence_id"]: e for e in evidence_list}

    for t in threats:
        ev_ids = t.get("evidence_ids", [])
        matched_sources = [ev_map[eid] for eid in ev_ids if eid in ev_map]

        platforms = list(set(s["platform"] for s in matched_sources))
        independent_groups = list(set(s.get("independence_group", "independent") for s in matched_sources))

        origin_ev = ev_map.get(t.get("origin_evidence_id")) or (matched_sources[0] if matched_sources else None)

        # Match related claims
        claim_records = []
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            matched_ids = [eid for eid in claim.get("evidence_ids", []) if eid in ev_ids]
            text = _claim_text(claim)
            if matched_ids and text:
                claim_records.append({"text": text, "claim_id": claim.get("claim_id") or claim.get("id"),
                                      "evidence_ids": matched_ids})
        related_claims = [claim["text"] for claim in claim_records]

        dossiers.append({
            "dossier_id": f"dos_{t['threat_id']}",
            "threat_id": t["threat_id"],
            "threat_title": t.get("title", ""),
            "threat_type": t.get("threat_type") or t.get("type", "UNKNOWN"),
            "severity": t.get("severity", "MEDIUM"),
            "confidence": t.get("confidence", 0.8),
            "status": t.get("status", "unverified"),
            "classification": t.get("classification", "UNVERIFIED"),
            "source_relation": t.get("source_relation"),
            "actor_url": t.get("actor_url"),
            "ownership_verified": False,
            "first_seen": origin_ev.get("published_at", "") if origin_ev else "",
            "latest_seen": matched_sources[-1].get("published_at", "") if matched_sources else "",
            "platforms": platforms,
            "platform_count": len(platforms),
            "source_count": len(matched_sources),
            "independent_source_count": len(independent_groups),
            "origin": {
                "source": origin_ev.get("source") if origin_ev else "Web",
                "url": origin_ev.get("url") if origin_ev else "",
                "has_url": origin_ev.get("has_url", False) if origin_ev else False,
                "author": origin_ev.get("author") if origin_ev else "Unknown"
            },
            "evidence_chain": [
                {
                    "evidence_id": s.get("evidence_id", ""),
                    "platform": s.get("platform", "Web"),
                    "title": s.get("title", ""),
                    "url": s.get("url", ""),
                    "has_url": s.get("has_url", bool(s.get("url"))),
                    "snippet": s.get("snippet", ""),
                    "source_role": s.get("source_role", "DISCOVERY")
                }
                for s in matched_sources
            ],
            "related_claims": related_claims,
            "related_claim_records": claim_records,
            "recommended_action": t.get("actionable_recommendation") or
                "Review the cited source, captured behavior and ownership before considering escalation. A category match alone does not justify a takedown or rebuttal."
        })

    return dossiers
