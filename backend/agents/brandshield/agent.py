"""
Aegis Protocol — BrandShield Agent 2.0
=======================================
Autonomous brand protection, counterfeit detection, and online threat intelligence agent.
Coordinates entity resolution, evidence acquisition, threat synthesis, and dossier construction.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.agents.brandshield.assessment import (
    heuristic_threat_synthesis,
    screen_review_patterns,
    synthesize_brand_threats,
)
from backend.agents.brandshield.dossier import build_investigation_dossiers
from backend.agents.brandshield.models import KNOWN_BRAND_CATALOG, THREAT_TAXONOMY
from backend.agents.brandshield.planning import resolve_brand_entity
from backend.agents.brandshield.scanning import search_brand_evidence

logger = logging.getLogger(__name__)


class BrandShieldAgent:
    """
    BrandShield 2.0: Autonomous Brand Protection & Threat Intelligence Agent.
    Investigates brand reputation, counterfeits, impersonations, and disinformation.
    """

    def __init__(self):
        logger.info("[BrandShield 2.0] Agent initialized with Agent Reach backbone")
        self._last_research_res = None

    def resolve_brand_entity(self, raw_input: str) -> Dict[str, Any]:
        """Normalize and resolve brand vs product distinctions."""
        return resolve_brand_entity(raw_input)

    def search_brand_evidence(
        self,
        brand_info: Dict[str, Any],
        max_results: int = 20,
        timeout: float = 12.0
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, Any], int]:
        """Execute domain-specific retrieval using central AgentReach/ResearchEngine fabric."""
        evidence_items, channel_health, plan, syndicated_count, research_res = search_brand_evidence(
            brand_info=brand_info, max_results=max_results, timeout=timeout
        )
        self._last_research_res = research_res
        return evidence_items, channel_health, plan, syndicated_count

    def screen_review_patterns(self, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic review-pattern screening over retrieved evidence."""
        return screen_review_patterns(evidence_list)

    def _synthesize_brand_threats(
        self,
        brand_info: Dict[str, Any],
        evidence_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze retrieved evidence for genuine brand threats, claims, and narratives."""
        return synthesize_brand_threats(brand_info, evidence_list)

    def _heuristic_threat_synthesis(
        self,
        brand_info: Dict[str, Any],
        evidence_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Deterministic rule-based forensic analysis over retrieved evidence when AI is offline."""
        return heuristic_threat_synthesis(brand_info, evidence_list)

    def _build_investigation_dossiers(
        self,
        brand_info: Dict[str, Any],
        threats: List[Dict[str, Any]],
        claims: List[Dict[str, Any]],
        evidence_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build exhaustive investigation dossiers for identified threats."""
        return build_investigation_dossiers(brand_info, threats, claims, evidence_list)

    def scan(
        self,
        brand_name: str = "",
        query: Optional[str] = None,
        brand_input: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute full BrandShield 2.0 brand protection and threat intelligence scan."""
        effective_name = (brand_name or brand_input or kwargs.get("brand") or "").strip()
        start_time = datetime.utcnow()
        clean_input = effective_name if effective_name else (query.strip() if query else "")
        logger.info(f"[BrandShield 2.0] Executing scan for input: '{clean_input}'")

        # 1. Entity Resolution
        brand_info = self.resolve_brand_entity(clean_input)

        # 2. Multi-Channel Evidence Retrieval via Agent Reach
        evidence_items, channel_health, plan, syndicated_count = self.search_brand_evidence(brand_info)

        # 3. Grounded Threat & Claim Reasoning
        synthesis = self._synthesize_brand_threats(brand_info, evidence_items)

        # 4. Chronological Research Timeline
        timeline = []
        dated_evidence = [e for e in evidence_items if e.get("published_at") and e.get("published_at") != "Recent"]
        for e in dated_evidence[:8]:
            timeline.append({
                "time": e.get("published_at") or e.get("published", "Recent"),
                "platform": e.get("platform", "Web"),
                "title": e.get("title", ""),
                "url": e.get("url", ""),
                "has_url": e.get("has_url", bool(e.get("url"))),
                "source_role": e.get("source_role", "COMMUNITY")
            })
        if not timeline and evidence_items:
            for e in evidence_items[:5]:
                timeline.append({
                    "time": e.get("published_at") or "Monitored Stream",
                    "platform": e.get("platform", "Web"),
                    "title": e.get("title", ""),
                    "url": e.get("url", ""),
                    "has_url": e.get("has_url", bool(e.get("url"))),
                    "source_role": e.get("source_role", "COMMUNITY")
                })

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        threats = synthesis.get("threats", [])
        claims = synthesis.get("claims", [])
        narratives = synthesis.get("narratives", [])
        dossiers = synthesis.get("dossiers", [])
        counterfeits = synthesis.get("counterfeits", [])
        impersonations = synthesis.get("impersonations", [])
        review_intel = synthesis.get("review_intel", {})
        recommendations = synthesis.get("recommendations", [])

        # 5. Platforms actually scanned
        active_platforms = list(set(e["platform"] for e in evidence_items if e.get("platform")))

        # 6. Backward Compatibility: 'findings' array
        findings = []
        for t in threats:
            matching_ev = next((e for e in evidence_items if e["evidence_id"] in t.get("evidence_ids", [])), None)
            url = matching_ev["url"] if matching_ev else ""
            findings.append({
                "platform": t.get("platforms", ["Web"])[0] if t.get("platforms") else "Web",
                "title": t.get("title", ""),
                "summary": t.get("summary", ""),
                "threat_type": t.get("type", "Reputation Attack"),
                "is_threat": t.get("type") != "CUSTOMER_COMPLAINT",
                "severity": t.get("severity", "medium"),
                "fake_review_score": None,
                "stars": None,
                "url": url or None,
                "has_url": bool(url),
                "evidence_id": matching_ev["evidence_id"] if matching_ev else ""
            })

        # Add safe items if needed to reflect balanced state
        safe_evs = [e for e in evidence_items if not any(e["evidence_id"] in t.get("evidence_ids", []) for t in threats)]
        for s_ev in safe_evs[:3]:
            findings.append({
                "platform": s_ev["platform"],
                "title": s_ev["title"][:60],
                "summary": s_ev["snippet"][:120],
                "threat_type": "Genuine Issue",
                "is_threat": False,
                "severity": "low",
                "fake_review_score": None,
                "stars": None,
                "url": s_ev["url"] or None,
                "has_url": bool(s_ev.get("has_url") and s_ev.get("url")),
                "evidence_id": s_ev["evidence_id"]
            })

        threat_count = sum(1 for f in findings if f.get("is_threat"))
        safe_count = len(findings) - threat_count

        return {
            # Brand & Entity Resolution
            "brand": brand_info["brand"],
            "brand_name": brand_info["brand"],
            "entity": brand_info,
            "scanned_at": datetime.utcnow().isoformat() + "Z",

            # Backward-Compatible Core Metrics
            "total_findings": len(findings),
            "threat_count": threat_count,
            "safe_count": safe_count,
            "findings": findings,
            "platforms": active_platforms,

            # Scout 2.0 / BrandShield 2.0 Rich Intelligence Payload
            "scan_metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": duration_ms,
                "ai_enrichment": synthesis.get("ai_enrichment", "ONLINE_GEMINI"),
            },
            "findings_structured": [f.to_dict() if hasattr(f, "to_dict") else f for f in self._last_research_res.findings] if getattr(self, "_last_research_res", None) else [],
            "contradictions": [c.to_dict() if hasattr(c, "to_dict") else c for c in self._last_research_res.contradictions] if getattr(self, "_last_research_res", None) else [],
            "deep_research_trace": plan.get("trace", {}),
            "retrieval": {
                "plan": plan,
                "channels": channel_health,
                "latency_ms": duration_ms,
                "total_sources": len(evidence_items),
                "unique_sources": max(0, len(evidence_items) - (syndicated_count or 0)),
                "syndicated_sources": syndicated_count or 0,
                "deep_reads": plan.get("trace", {}).get("deep_read_success", 0),
                "trace": plan.get("trace", {}),
            },
            "retrieval_trace": plan.get("trace", {}),
            "summary": {
                "threats_count": len(threats),
                "claims_count": len(claims),
                "counterfeit_count": len(counterfeits),
                "impersonation_count": len(impersonations),
                "independent_groups_count": max(1, len(set(e.get("independence_group") for e in evidence_items))),
                "high_priority_count": sum(1 for t in threats if t.get("severity") in ("high", "critical")),
            },
            "threats": threats,
            "claims": claims,
            "narratives": narratives,
            "dossiers": dossiers,
            "counterfeits": counterfeits,
            "impersonations": impersonations,
            "review_intel": review_intel,
            "evidence": evidence_items,
            "sources": evidence_items,
            "timeline": timeline,
            "recommendations": recommendations,
            "limitations": [
                "Only platforms actively returned by Agent Reach search endpoints are displayed.",
                "E-commerce product reviews reflect public web mentions; closed private marketplace databases are not directly polled.",
                "All citations reflect retrieved public web records; direct human investigation is recommended before legal escalation."
            ]
        }

    def generate_brandshield_intelligence(
        self,
        entity_input: str,
        entity_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Aegis Protocol Output Contract implementation for BrandShield Agent."""
        scan_res = self.scan(brand_name=entity_input)
        entity_info = scan_res.get("entity", {})
        canonical_brand = scan_res.get("brand", entity_input)
        ent_type = entity_type or entity_info.get("entity_type", "brand")
        confidence = float(entity_info.get("confidence", 0.85))

        threats = scan_res.get("threats", [])
        evidence_items = scan_res.get("evidence", [])
        narratives = scan_res.get("narratives", [])
        timeline = scan_res.get("timeline", [])
        recommendations = scan_res.get("recommendations", [])

        # 1. Observed facts
        observed: List[str] = []
        for t in threats[:4]:
            t_name = t.get("threat_name") or t.get("threat_type") or t.get("type", "THREAT")
            desc = t.get("description") or t.get("title") or t.get("summary", "")
            plat = t.get("platform") if isinstance(t.get("platform"), str) else (t.get("platforms", ["web"])[0] if t.get("platforms") else "web")
            observed.append(f"Observed {t_name} on {plat}: {desc}")
        for s in scan_res.get("counterfeits", [])[:2]:
            s_title = s.get("title") or s.get("product", "Suspected Product")
            s_plat = s.get("platform") or s.get("marketplace_or_domain", "Web")
            observed.append(f"Identified suspicious/counterfeit asset: {s_title} ({s_plat})")
        for imp in scan_res.get("impersonations", [])[:2]:
            imp_title = imp.get("title") or imp.get("handle_or_domain", "Suspected Impersonator")
            imp_plat = imp.get("platform", "Web")
            observed.append(f"Identified potential brand impersonation: {imp_title} ({imp_plat})")
        if not observed and evidence_items:
            observed.append(f"Retrieved {len(evidence_items)} active public web citations across {len(scan_res.get('platforms', []))} platforms.")

        # 2. Inferred interpretations
        inferred: List[str] = []
        high_threats = [t for t in threats if t.get("severity") in ("high", "critical")]
        if high_threats:
            inferred.append(f"High-priority threat exposure detected: {len(high_threats)} severe brand/customer-risk vectors identified.")
        elif threats:
            inferred.append("Moderate brand threat vectors identified; manageable via routine monitoring and response.")
        else:
            inferred.append("Brand security perimeter stable; no acute coordinated smear or counterfeit campaigns detected.")

        # 3. Uncertain / Unknown
        uncertain: List[str] = []
        unverified_rumors = [t for t in threats if t.get("threat_type") in ("UNVERIFIED_RUMOR", "RUMOR") or t.get("type") == "RUMOR"]
        for r in unverified_rumors:
            uncertain.append(f"Unsubstantiated public discourse: {r.get('description') or r.get('title', '')}")
        for contra in scan_res.get("contradictions", []):
            uncertain.append(f"Contradiction flagged in public claims: {contra}")
        if not evidence_items:
            uncertain.append(f"Zero public threat signals discovered in current scan window for {canonical_brand}.")

        # Determine overall risk level
        risk_level = "low"
        if any(t.get("severity") == "critical" for t in threats):
            risk_level = "critical"
        elif any(t.get("severity") == "high" for t in threats):
            risk_level = "high"
        elif any(t.get("severity") == "medium" for t in threats):
            risk_level = "moderate"

        # Determine retrieval directness & fallback
        retrieval_trace = scan_res.get("retrieval_trace", {})
        fallback_used = retrieval_trace.get("fallback_rate", 0.0) > 0.0
        fallback_reason = "SEARCH_INDEX_FALLBACK" if fallback_used else None

        # Build clean recommendations list
        clean_recs = []
        for r in recommendations:
            if isinstance(r, str) and r.strip():
                clean_recs.append(r.strip())
            elif isinstance(r, dict) and r.get("action"):
                clean_recs.append(r.get("action").strip())

        return {
            "agent": "brandshield",
            "entity": canonical_brand,
            "entity_type": ent_type if ent_type in ("brand", "company", "product", "domain", "account") else "brand",
            "identity_confidence": round(confidence, 2),
            "threats": threats,
            "risk_level": risk_level,
            "observed": observed,
            "inferred": inferred,
            "uncertain": uncertain,
            "narrative_clusters": narratives,
            "timeline": timeline,
            "sources": evidence_items,
            "corroboration": scan_res.get("findings_structured", []),
            "contradictions": scan_res.get("contradictions", []),
            "recommended_attention": clean_recs or ["Continue passive monitoring"],
            "retrieval": {
                "direct": not fallback_used,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason
            }
        }

    # Backward-compatible alias
    generate_intelligence = generate_brandshield_intelligence


brandshield_agent = BrandShieldAgent()

__all__ = [
    "BrandShieldAgent",
    "brandshield_agent",
]
