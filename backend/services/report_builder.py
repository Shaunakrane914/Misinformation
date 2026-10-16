"""
Aegis Protocol — Unified Report Builder (v3.8.0)
=================================================
Provides ``ReportBuilder``, a single adapter that converts each agent's
native output into a ``UnifiedReport``.  Each agent endpoint calls the
appropriate builder method instead of constructing its own response shape.

Usage example (claims endpoint)::

    from backend.services.report_builder import ReportBuilder

    report = ReportBuilder.from_claim_result(
        claim_text   = "Drinking bleach cures COVID",
        verdict      = investigator_result,
        corpus       = research_corpus,
        execution_log= query_log,
    )
    return report.to_dict()
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.schemas.unified_report import (
    UnifiedReport,
    UnifiedEvidenceSet,
    UnifiedEvidenceItem,
    UnifiedEvidenceSource,
    UnifiedQualityTensor,
    RetrievalLineageEntry,
    TimelineEvent,
    TrustMetadata,
    QueryTelemetry,
    classify_evidence_items,
    build_trust_metadata,
)

logger = logging.getLogger(__name__)


def _record_list(value):
    """Normalize grouped agent records without treating mapping keys as evidence."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [entry for entries in value.values() if isinstance(entries, list) for entry in entries]
    return []

# ─────────────────────────────────────────────────────────────────────────────
# CLAIM VERIFIER
# ─────────────────────────────────────────────────────────────────────────────

class ReportBuilder:
    """Static factory methods — one per agent domain."""

    # ── Claim Verifier ────────────────────────────────────────────────────────

    @staticmethod
    def from_claim_result(
        *,
        claim_text: str,
        verdict: Optional[Dict[str, Any]] = None,
        corpus: Any = None,
        execution_log: Optional[List[Any]] = None,
        queries_planned: int = 0,
        timeline_events: Optional[List[Dict[str, Any]]] = None,
    ) -> UnifiedReport:
        """
        Build a UnifiedReport for the Claim Verifier agent.

        Parameters
        ----------
        claim_text:     The raw user-submitted claim.
        verdict:        Dict from InvestigatorAgent (verdict, confidence, reasoning, severity, …).
        corpus:         ResearchCorpus produced by ResearchEngine (may be None).
        execution_log:  List of QueryExecutionRecord objects.
        queries_planned: How many queries were originally planned.
        timeline_events: Optional list of {timestamp, description} dicts.
        """
        # ── Summary ──────────────────────────────────────────────────────────
        summary: Optional[str] = None
        if verdict:
            v = verdict.get("verdict") or ""
            reasoning = verdict.get("reasoning") or verdict.get("explanation") or ""
            if v:
                summary = f"Claim is **{v}**."
                if reasoning:
                    # Take first sentence only for brevity
                    first_sentence = re.split(r"(?<=[.!?])\s", reasoning.strip())[0]
                    summary = f"Claim is **{v}**. {first_sentence}"
            elif reasoning:
                summary = reasoning[:300]

        # ── Findings ─────────────────────────────────────────────────────────
        findings: List[str] = []
        if verdict:
            explanation = verdict.get("explanation") or verdict.get("reasoning") or ""
            if explanation:
                # Split on sentence boundaries into bullets
                sentences = re.split(r"(?<=[.!?])\s+", explanation.strip())
                for s in sentences[:6]:
                    if s.strip():
                        findings.append(s.strip())
            benefit = verdict.get("benefit") or verdict.get("key_finding") or ""
            if benefit and benefit.strip():
                findings.insert(0, benefit.strip())

        # ── Evidence ─────────────────────────────────────────────────────────
        evidence = UnifiedEvidenceSet()
        if corpus is not None:
            items = getattr(corpus, "evidence_items", []) or []
            evidence = classify_evidence_items(items)

        # ── Disagreements ─────────────────────────────────────────────────────
        # ── Disagreements & Contradictions ────────────────────────────────────
        disagreements: List[str] = []
        structured_contradictions: List[Dict[str, Any]] = []
        if corpus is not None:
            raw_contra = getattr(corpus, "contradictions", []) or []
            for c in raw_contra[:6]:
                if isinstance(c, dict):
                    desc = c.get("explanation") or c.get("description") or c.get("summary") or str(c)
                    if desc:
                        disagreements.append(desc)
                    structured_contradictions.append(c)
                elif hasattr(c, "to_dict"):
                    d = c.to_dict()
                    structured_contradictions.append(d)
                    desc = d.get("explanation") or d.get("description") or str(c)
                    if desc:
                        disagreements.append(desc)
        if verdict and isinstance(verdict.get("contradictions"), list):
            for c in verdict["contradictions"][:6]:
                if isinstance(c, dict):
                    desc = c.get("explanation") or c.get("description") or str(c)
                    if desc and desc not in disagreements:
                        disagreements.append(desc)
                    if c not in structured_contradictions:
                        structured_contradictions.append(c)

        # ── Claim Decomposition ──────────────────────────────────────────────
        decomposed: List[Dict[str, Any]] = []
        if verdict:
            raw_decomp = verdict.get("claim_decomposition") or verdict.get("sub_claims") or []
            if isinstance(raw_decomp, list):
                decomposed = [item for item in raw_decomp if isinstance(item, dict)]

        # ── Changes ──────────────────────────────────────────────────────────
        changes: List[str] = []
        if verdict:
            updates = verdict.get("updates") or verdict.get("changes") or []
            if isinstance(updates, list):
                changes = [str(u) for u in updates[:4]]

        # ── Timeline ─────────────────────────────────────────────────────────
        timeline: List[TimelineEvent] = []
        for ev in (timeline_events or []):
            timeline.append(TimelineEvent(
                timestamp=ev.get("timestamp"),
                description=ev.get("description"),
            ))

        # ── Trust / telemetry ─────────────────────────────────────────────────
        trust = build_trust_metadata(corpus, execution_log, queries_planned)

        # ── Next steps ────────────────────────────────────────────────────────
        next_steps: List[str] = []
        if verdict:
            suggestions = verdict.get("next_steps") or verdict.get("recommendations") or []
            if isinstance(suggestions, list):
                next_steps = [str(s) for s in suggestions[:4]]
        if not next_steps:
            v_str = (verdict or {}).get("verdict", "")
            if "false" in str(v_str).lower():
                next_steps = [
                    "Share verified official sources with your network.",
                    "Report misleading content to platform moderators.",
                ]
            elif "true" in str(v_str).lower():
                next_steps = ["Monitor for updates from primary sources."]

        return UnifiedReport(
            summary=summary,
            findings=findings,
            evidence=evidence,
            disagreements=disagreements,
            changes=changes,
            timeline=timeline,
            trust=trust,
            next_steps=next_steps,
            agent="claim_verifier",
            query=claim_text,
            claim_decomposition=decomposed,
            detailed_contradictions=structured_contradictions,
        )

    # ── Trending Agent ────────────────────────────────────────────────────────

    @staticmethod
    def from_trending_result(
        *,
        query: str,
        trend_data: Dict[str, Any],
        execution_log: Optional[List[Any]] = None,
        queries_planned: int = 0,
    ) -> UnifiedReport:
        """Build a UnifiedReport from TrendingAgent output."""
        # ── Summary ──────────────────────────────────────────────────────────
        raw_summary = (
            trend_data.get("trend_summary")
            or trend_data.get("summary")
            or trend_data.get("narrative_summary")
        )
        summary = str(raw_summary).strip() if raw_summary else None

        # ── Findings ─────────────────────────────────────────────────────────
        findings: List[str] = []
        narratives = trend_data.get("narratives") or trend_data.get("claims") or []
        for n in narratives[:6]:
            if isinstance(n, dict):
                text = n.get("summary") or n.get("text") or n.get("claim_text") or ""
            else:
                text = str(n)
            if text.strip():
                findings.append(text.strip())

        # ── Evidence ─────────────────────────────────────────────────────────
        evidence = UnifiedEvidenceSet()
        raw_evidence = trend_data.get("evidence")
        if not raw_evidence and isinstance(trend_data.get("sources"), dict):
            flattened = []
            for src_list in trend_data.get("sources", {}).values():
                if isinstance(src_list, list):
                    flattened.extend(src_list)
            raw_evidence = flattened
        elif not raw_evidence and isinstance(trend_data.get("sources"), list):
            raw_evidence = trend_data.get("sources")
        else:
            raw_evidence = raw_evidence or []

        for ev in raw_evidence:
            if isinstance(ev, dict):
                item = _dict_to_evidence_item(ev)
            else:
                item = UnifiedEvidenceItem.from_evidence_item(ev)
            platform = (ev.get("platform") if isinstance(ev, dict) else getattr(ev, "platform", "")) or ""
            if isinstance(platform, str) and platform.lower() in ("reddit", "twitter", "x", "instagram", "youtube"):
                evidence.community.append(item)
            elif (ev.get("is_primary") if isinstance(ev, dict) else getattr(ev, "primary_source", False)):
                evidence.primary.append(item)
            else:
                evidence.independent.append(item)

        # ── Disagreements ─────────────────────────────────────────────────────
        disagreements: List[str] = []
        structured_contradictions: List[Dict[str, Any]] = []
        for c in (trend_data.get("contradictions") or trend_data.get("disputes") or [])[:4]:
            if isinstance(c, dict):
                disagreements.append(c.get("explanation") or c.get("description") or c.get("text") or str(c))
                structured_contradictions.append(c)
            else:
                disagreements.append(str(c))

        # ── Changes ──────────────────────────────────────────────────────────
        changes: List[str] = []
        for ch in (trend_data.get("changes") or trend_data.get("updates") or [])[:4]:
            changes.append(str(ch))

        # ── Timeline ─────────────────────────────────────────────────────────
        timeline: List[TimelineEvent] = []
        for ev in (trend_data.get("timeline") or [])[:10]:
            if isinstance(ev, dict):
                timeline.append(TimelineEvent(
                    timestamp=ev.get("timestamp") or ev.get("ts"),
                    description=ev.get("description") or ev.get("event"),
                ))

        # ── Trust ────────────────────────────────────────────────────
        ind_count = trend_data.get("independent_source_count") or trend_data.get("independent_sources")
        raw_qt = trend_data.get("quality_vector") or trend_data.get("quality_tensor")
        qt = _dict_to_quality_tensor(raw_qt) if raw_qt else None

        telemetry = QueryTelemetry.from_execution_log(
            log=execution_log or trend_data.get("query_log") or [],
            queries_planned=queries_planned,
        )
        trust = TrustMetadata(
            quality_tensor=qt,
            independent_source_count=int(ind_count) if ind_count is not None else None,
            query_telemetry=telemetry,
        )

        # ── Agent Intelligence (Trending) ────────────────────────────────────
        t_intel: Dict[str, Any] = {}
        if trend_data.get("bot_amplification"):
            t_intel["bot_amplification"] = trend_data["bot_amplification"]
        if trend_data.get("narrative_velocity"):
            t_intel["narrative_velocity"] = trend_data["narrative_velocity"]
        if trend_data.get("claim_mutations"):
            t_intel["claim_mutations"] = trend_data["claim_mutations"]

        # ── Next steps ────────────────────────────────────────────────────────
        next_steps = [
            "Monitor this trend for misinformation amplification.",
            "Cross-reference with official sources before sharing.",
        ]

        return UnifiedReport(
            summary=summary,
            findings=findings,
            evidence=evidence,
            disagreements=disagreements,
            changes=changes,
            timeline=timeline,
            trust=trust,
            next_steps=next_steps,
            agent="trending",
            query=query,
            detailed_contradictions=structured_contradictions,
            agent_intelligence=t_intel,
        )

    # ── Scout Agent (Financial Intelligence) ──────────────────────────────────

    @staticmethod
    def from_scout_result(
        *,
        query: str,
        scout_data: Dict[str, Any],
        execution_log: Optional[List[Any]] = None,
        queries_planned: int = 0,
    ) -> UnifiedReport:
        """Build a UnifiedReport from ScoutAgent output."""
        # ── Summary ──────────────────────────────────────────────────────────
        raw_summary = (
            scout_data.get("market_summary")
            or scout_data.get("summary")
            or scout_data.get("narrative")
        )
        summary = str(raw_summary).strip() if raw_summary else None

        # ── Findings ─────────────────────────────────────────────────────────
        findings: List[str] = []
        catalysts = scout_data.get("catalysts") or scout_data.get("catalyst_summary") or []
        if isinstance(catalysts, str):
            catalysts = [catalysts]
        elif isinstance(catalysts, dict):
            # Scout's production contract groups factors by polarity.
            catalysts = [f"{polarity}: {entry.get('factor', '')}" for polarity, entries in catalysts.items()
                         if isinstance(entries, list) for entry in entries if isinstance(entry, dict) and entry.get("factor")]
        for cat in catalysts[:6]:
            findings.append(str(cat).strip())

        # ── Evidence ─────────────────────────────────────────────────────────
        evidence = UnifiedEvidenceSet()
        filings = scout_data.get("primary_filings") or scout_data.get("filings") or []
        for f in filings:
            evidence.primary.append(_dict_to_evidence_item(f) if isinstance(f, dict) else UnifiedEvidenceItem.from_evidence_item(f))
        news = _record_list(scout_data.get("news_articles") or scout_data.get("news"))
        for n in news:
            evidence.independent.append(_dict_to_evidence_item(n) if isinstance(n, dict) else UnifiedEvidenceItem.from_evidence_item(n))
        social = _record_list(scout_data.get("social_posts") or scout_data.get("social"))
        for s in social:
            evidence.community.append(_dict_to_evidence_item(s) if isinstance(s, dict) else UnifiedEvidenceItem.from_evidence_item(s))
        # Do not discard the canonical source list when specialized legacy buckets are absent.
        if not (filings or news or social):
            for source in scout_data.get("sources", []):
                if isinstance(source, dict):
                    item = _dict_to_evidence_item(source)
                    if source.get("is_primary") or source.get("primary_source"):
                        evidence.primary.append(item)
                    else:
                        evidence.independent.append(item)

        # ── Disagreements, changes, timeline ─────────────────────────────────
        disagreements = []
        structured_contradictions: List[Dict[str, Any]] = []
        for d in _record_list(scout_data.get("contradictions") or scout_data.get("disputes"))[:4]:
            if isinstance(d, dict):
                disagreements.append(d.get("explanation") or d.get("description") or str(d))
                structured_contradictions.append(d)
            else:
                disagreements.append(str(d))
        changes = [str(c) for c in (scout_data.get("changes") or scout_data.get("updates") or [])[:4]]
        timeline = [
            TimelineEvent(timestamp=t.get("timestamp"), description=t.get("description"))
            for t in (scout_data.get("timeline") or [])[:10]
            if isinstance(t, dict)
        ]

        # ── Trust ────────────────────────────────────────────────────────────
        raw_qt = scout_data.get("quality_tensor")
        qt = _dict_to_quality_tensor(raw_qt) if raw_qt else None
        ind_count = scout_data.get("independent_source_count")
        telemetry = QueryTelemetry.from_execution_log(
            log=execution_log or scout_data.get("query_log") or [],
            queries_planned=queries_planned,
        )
        trust = TrustMetadata(
            quality_tensor=qt,
            independent_source_count=int(ind_count) if ind_count is not None else None,
            query_telemetry=telemetry,
        )

        # ── Agent Intelligence (Scout) ───────────────────────────────────────
        s_intel: Dict[str, Any] = {}
        if scout_data.get("filing_comparison"):
            s_intel["filing_comparison"] = scout_data["filing_comparison"]
        if scout_data.get("misinformation"):
            s_intel["corporate_rumors"] = scout_data["misinformation"]
        if scout_data.get("stock"):
            stk = scout_data["stock"]
            s_intel["stock_anomaly"] = {
                "z_score": stk.get("z_score"),
                "is_crashing": stk.get("is_crashing"),
            }

        next_steps = [
            "Review regulatory filings for confirmation.",
            "Monitor earnings announcements and SEC/SEBI disclosures.",
        ]

        return UnifiedReport(
            summary=summary,
            findings=findings,
            evidence=evidence,
            disagreements=disagreements,
            changes=changes,
            timeline=timeline,
            trust=trust,
            next_steps=next_steps,
            agent="scout",
            query=query,
            detailed_contradictions=structured_contradictions,
            agent_intelligence=s_intel,
        )

    # ── BrandShield Agent ─────────────────────────────────────────────────────

    @staticmethod
    def from_brandshield_result(
        *,
        query: str,
        brand_data: Dict[str, Any],
        execution_log: Optional[List[Any]] = None,
        queries_planned: int = 0,
    ) -> UnifiedReport:
        """Build a UnifiedReport from BrandShieldAgent output."""
        raw_summary = (
            brand_data.get("status")
            or brand_data.get("summary")
            or brand_data.get("brand_health_summary")
        )
        summary = str(raw_summary).strip() if raw_summary else None

        findings: List[str] = []
        threats = brand_data.get("threats") or brand_data.get("threat_list") or []
        for t in threats[:6]:
            if isinstance(t, dict):
                text = t.get("description") or t.get("summary") or t.get("type") or str(t)
            else:
                text = str(t)
            if text.strip():
                findings.append(text.strip())

        evidence = UnifiedEvidenceSet()
        _append_observed_evidence(evidence, brand_data.get("documents") or brand_data.get("evidence") or [])
        for n in (brand_data.get("news") or []):
            evidence.independent.append(_dict_to_evidence_item(n) if isinstance(n, dict) else UnifiedEvidenceItem.from_evidence_item(n))
        for s in (brand_data.get("social") or brand_data.get("social_posts") or []):
            evidence.community.append(_dict_to_evidence_item(s) if isinstance(s, dict) else UnifiedEvidenceItem.from_evidence_item(s))

        disagreements = [str(c) for c in (brand_data.get("conflicts") or [])[:4]]
        changes = [str(c) for c in (brand_data.get("new_threats") or brand_data.get("changes") or [])[:4]]
        timeline = [
            TimelineEvent(timestamp=t.get("timestamp"), description=t.get("description"))
            for t in (brand_data.get("timeline") or [])[:10]
            if isinstance(t, dict)
        ]

        raw_qt = brand_data.get("quality_tensor")
        qt = _dict_to_quality_tensor(raw_qt) if raw_qt else None
        ind_count = brand_data.get("independent_source_count")
        telemetry = QueryTelemetry.from_execution_log(
            log=execution_log or brand_data.get("query_log") or [],
            queries_planned=queries_planned,
        )
        trust = TrustMetadata(
            quality_tensor=qt,
            independent_source_count=int(ind_count) if ind_count is not None else None,
            query_telemetry=telemetry,
        )

        # ── Agent Intelligence (BrandShield) ─────────────────────────────────
        b_intel: Dict[str, Any] = {}
        if brand_data.get("executive_impersonation"):
            b_intel["executive_impersonation"] = brand_data["executive_impersonation"]
        if brand_data.get("smear_analysis"):
            b_intel["smear_analysis"] = brand_data["smear_analysis"]
        if brand_data.get("counterfeit_domains"):
            b_intel["counterfeit_domains"] = brand_data["counterfeit_domains"]

        next_steps = [
            "Alert your legal team to any counterfeit listings.",
            "Submit DMCA/trademark takedown requests where applicable.",
            "Improve brand keyword monitoring cadence.",
        ]

        return UnifiedReport(
            summary=summary,
            findings=findings,
            evidence=evidence,
            disagreements=disagreements,
            changes=changes,
            timeline=timeline,
            trust=trust,
            next_steps=next_steps,
            agent="brandshield",
            query=query,
            agent_intelligence=b_intel,
        )

    # ── Personal Watch Agent ──────────────────────────────────────────────────

    @staticmethod
    def from_personal_result(
        *,
        query: str,
        personal_data: Dict[str, Any],
        execution_log: Optional[List[Any]] = None,
        queries_planned: int = 0,
    ) -> UnifiedReport:
        """Build a UnifiedReport from PersonalWatchAgent output."""
        raw_summary = (
            personal_data.get("status")
            or personal_data.get("summary")
            or personal_data.get("identity_summary")
        )
        if isinstance(raw_summary, dict):
            raw_summary = personal_data.get("status_note") or "Sampled evidence requires contextual review; telemetry is shown separately."
        summary = str(raw_summary).strip() if raw_summary else None

        findings: List[str] = []
        alerts = personal_data.get("threats") or personal_data.get("alerts") or []
        for a in alerts[:6]:
            if isinstance(a, dict):
                text = a.get("description") or a.get("summary") or a.get("type") or str(a)
            else:
                text = str(a)
            if text.strip():
                findings.append(text.strip())

        evidence = UnifiedEvidenceSet()
        for doc in (personal_data.get("officials") or personal_data.get("documents") or []):
            evidence.primary.append(_dict_to_evidence_item(doc) if isinstance(doc, dict) else UnifiedEvidenceItem.from_evidence_item(doc))
        for n in (personal_data.get("news") or []):
            evidence.independent.append(_dict_to_evidence_item(n) if isinstance(n, dict) else UnifiedEvidenceItem.from_evidence_item(n))
        for s in (personal_data.get("social") or personal_data.get("impostor_accounts") or []):
            evidence.community.append(_dict_to_evidence_item(s) if isinstance(s, dict) else UnifiedEvidenceItem.from_evidence_item(s))
        if not (evidence.primary or evidence.independent or evidence.community):
            _append_observed_evidence(evidence, personal_data.get("evidence") or personal_data.get("sources") or [])

        disagreements = [str(c) for c in (personal_data.get("conflicts") or [])[:4]]
        changes = [str(c) for c in (personal_data.get("new_incidents") or personal_data.get("changes") or [])[:4]]
        timeline = [
            TimelineEvent(timestamp=t.get("timestamp"), description=t.get("description"))
            for t in (personal_data.get("timeline") or [])[:10]
            if isinstance(t, dict)
        ]

        raw_qt = personal_data.get("quality_tensor")
        qt = _dict_to_quality_tensor(raw_qt) if raw_qt else None
        ind_count = personal_data.get("independent_source_count")
        telemetry = QueryTelemetry.from_execution_log(
            log=execution_log or personal_data.get("query_log") or [],
            queries_planned=queries_planned,
        )
        trust = TrustMetadata(
            quality_tensor=qt,
            independent_source_count=int(ind_count) if ind_count is not None else None,
            query_telemetry=telemetry,
        )

        # ── Agent Intelligence (Personal Watch) ──────────────────────────────
        p_intel: Dict[str, Any] = {}
        if personal_data.get("identity_verification") or personal_data.get("subject"):
            p_intel["identity_verification"] = personal_data.get("identity_verification") or personal_data.get("subject")
        if personal_data.get("doxxing_exposure"):
            p_intel["doxxing_exposure"] = personal_data["doxxing_exposure"]
        if personal_data.get("synthetic_media"):
            p_intel["synthetic_media"] = personal_data["synthetic_media"]
        if personal_data.get("quote_attribution"):
            p_intel["quote_attribution"] = personal_data["quote_attribution"]

        next_steps = [
            "Report impostor accounts to the relevant platform.",
            "Share official verified identity references to counter misinformation.",
        ]

        return UnifiedReport(
            summary=summary,
            findings=findings,
            evidence=evidence,
            disagreements=disagreements,
            changes=changes,
            timeline=timeline,
            trust=trust,
            next_steps=next_steps,
            agent="personal_watch",
            query=query,
            agent_intelligence=p_intel,
        )


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _append_observed_evidence(evidence, records):
    """Generic evidence is not inherently primary, official or independent."""
    for record in _record_list(records):
        if not isinstance(record, dict):
            continue
        item = _dict_to_evidence_item(record)
        role = str(record.get("source_role") or "").upper()
        platform = str(record.get("channel") or record.get("platform") or "").lower()
        primary = item.source.is_primary or role in {"PRIMARY", "PRIMARY_OFFICIAL", "PRIMARY_REGULATORY"}
        if primary:
            item.source.is_primary = True
            evidence.primary.append(item)
        elif role == "COMMUNITY" or platform in {"reddit", "twitter", "twitter/x", "x", "youtube", "v2ex", "hackernews", "stackexchange"}:
            evidence.community.append(item)
        else:
            evidence.independent.append(item)


def _dict_to_evidence_item(d: Dict[str, Any]) -> UnifiedEvidenceItem:
    """Convert an arbitrary evidence dict into a UnifiedEvidenceItem."""
    if not isinstance(d, dict):
        return UnifiedEvidenceItem.from_evidence_item(d)

    def _str_val(v: Any) -> Optional[str]:
        if v is None or callable(v):
            return None
        s = str(v).strip()
        return s if s else None

    url = _str_val(d.get("url") or d.get("canonical_url") or d.get("source_url"))

    raw_source = d.get("source")
    if isinstance(raw_source, dict):
        source = UnifiedEvidenceSource(
            name=_str_val(raw_source.get("name")),
            type=_str_val(raw_source.get("type")),
            domain=_str_val(raw_source.get("domain")),
            is_primary=bool(raw_source.get("is_primary") or d.get("is_primary") or d.get("primary_source", False)),
            authority=_str_val(raw_source.get("authority") or d.get("authority")),
            reliability=float(raw_source["reliability"]) if raw_source.get("reliability") is not None else (float(d["reliability"]) if d.get("reliability") is not None else None),
        )
    else:
        source = UnifiedEvidenceSource(
            name=_str_val(d.get("source") or d.get("publisher") or d.get("source_name")),
            type=_str_val(d.get("type") or d.get("source_type")),
            domain=_str_val(d.get("domain") or d.get("source_domain")),
            is_primary=bool(d.get("is_primary") or d.get("primary_source", False)),
            authority=_str_val(d.get("authority")),
            reliability=float(d["reliability"]) if d.get("reliability") is not None else None,
        )

    raw_qt = d.get("quality_tensor")
    qt = _dict_to_quality_tensor(raw_qt) if isinstance(raw_qt, (dict, object)) else None

    lineage = []
    raw_lin = d.get("retrieval_lineage")
    if isinstance(raw_lin, (list, tuple)):
        for entry in raw_lin:
            if isinstance(entry, dict):
                lineage.append(RetrievalLineageEntry(
                    query_id=_str_val(entry.get("query_id")),
                    channel=_str_val(entry.get("channel")),
                    retrieval_mode=_str_val(entry.get("retrieval_mode")),
                    backend_id=_str_val(entry.get("backend_id")),
                    is_authenticated=bool(entry.get("is_authenticated", False)),
                    fallback_reason=_str_val(entry.get("fallback_reason")),
                    retrieved_at=_str_val(entry.get("retrieved_at")),
                ))

    from backend.schemas.evidence_inspection import inspect_evidence
    return UnifiedEvidenceItem(
        title=_str_val(d.get("title")),
        snippet=_str_val(d.get("snippet") or d.get("content") or d.get("summary")),
        url=url,
        timestamp=_str_val(d.get("timestamp") or d.get("published_at") or d.get("published")),
        source=source,
        quality_tensor=qt,
        retrieval_lineage=lineage,
        extraction=inspect_evidence(d),
    )


def _dict_to_quality_tensor(d: Any) -> Optional[UnifiedQualityTensor]:
    """Safely convert a dict or QualityTensor-like object to UnifiedQualityTensor."""
    if d is None:
        return None
    if isinstance(d, UnifiedQualityTensor):
        return d
    if hasattr(d, "to_dict"):
        d = d.to_dict()
    if not isinstance(d, dict):
        return None
    return UnifiedQualityTensor(
        relevance=d.get("relevance"),
        source_quality=d.get("source_quality"),
        independence=d.get("independence"),
        primary_weight=d.get("primary_weight"),
        freshness=d.get("freshness"),
        contradiction=d.get("contradiction") or d.get("contradiction_level"),
    )
