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
        _set_retained_publisher_trust(trust, evidence)

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
        summary = _summary_text(raw_summary)

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

        for ev in _record_list(raw_evidence):
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
        background = (trend_data.get('retrieval_trace') or {}).get('historical_background')
        if isinstance(background, dict):
            t_intel['historical_background'] = background
        if trend_data.get("bot_amplification"):
            t_intel["bot_amplification"] = trend_data["bot_amplification"]
        if trend_data.get("narrative_velocity"):
            t_intel["narrative_velocity"] = trend_data["narrative_velocity"]
        if trend_data.get("claim_mutations"):
            t_intel["claim_mutations"] = trend_data["claim_mutations"]
        for context_key in ("recent_developments", "competitive_context"):
            if not isinstance(trend_data.get(context_key), list):
                continue
            t_intel[context_key] = [
                {key: row[key] for key in ("title", "published_at", "publisher", "evidence_id", "url",
                                          "passage", "observation_scope") if key in row}
                for row in trend_data[context_key][:24] if isinstance(row, dict)]
        if isinstance(trend_data.get("primary_topic_coverage"), dict):
            t_intel["primary_topic_coverage"] = trend_data["primary_topic_coverage"]

        # ── Next steps ────────────────────────────────────────────────────────
        next_steps = [
            "Monitor this trend for misinformation amplification.",
            "Cross-reference with official sources before sharing.",
        ]

        return _complete_agent_report(UnifiedReport(
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
        ), trend_data, execution_log, queries_planned)

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
        summary = _summary_text(raw_summary)

        # ── Findings ─────────────────────────────────────────────────────────
        findings: List[str] = []
        catalysts = scout_data.get("catalysts") or scout_data.get("catalyst_summary") or []
        if isinstance(catalysts, str):
            catalysts = [catalysts]
        elif isinstance(catalysts, dict):
            # Scout's production contract groups factors by polarity.
            catalysts = [f"{polarity}: {entry.get('factor') or entry.get('catalyst')}"
                         for polarity, entries in catalysts.items() if isinstance(entries, list) and polarity != "unresolved"
                         for entry in entries if isinstance(entry, dict) and (entry.get("factor") or entry.get("catalyst"))]
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
        native_conflicts = scout_data.get("contradictions") or scout_data.get("disputes")
        # Legacy for/against/unresolved factors describe polarity/context, not
        # paired incompatible propositions. Never flatten their headings here.
        for d in (native_conflicts if isinstance(native_conflicts, list) else [])[:4]:
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
        if isinstance(scout_data.get("financial_observations"), list):
            s_intel["financial_observations"] = [row for row in scout_data["financial_observations"][:24]
                                                  if isinstance(row, dict)]
        if isinstance(scout_data.get("financial_context_summary"), dict):
            s_intel["financial_context_summary"] = scout_data["financial_context_summary"]
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

        return _complete_agent_report(UnifiedReport(
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
        ), scout_data, execution_log, queries_planned)

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
            brand_data.get("summary")
            or brand_data.get("status")
            or brand_data.get("brand_health_summary")
        )
        summary = _summary_text(raw_summary)

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
        if isinstance(brand_data.get("source_assessments"), list):
            b_intel["source_assessments"] = [
                {key: row[key] for key in ("evidence_id", "source_url", "classification", "actor_url",
                    "epistemic_state", "ownership_verified", "reason", "discovery_only", "temporal_state") if key in row}
                for row in brand_data["source_assessments"][:30] if isinstance(row, dict)]
            b_intel["assessment_status"] = brand_data.get("assessment_status") or "UNASSESSED"

        next_steps = [
            "Review the exact captured incident passages, attribution and publication dates.",
            "Independently verify the specific suspected listing, account or domain; the reporting publisher is not the accused actor.",
            "Preserve source evidence and obtain human review before any alert, accusation or takedown. A reported allegation is not verified fraud.",
        ]
        if (any(isinstance(t, dict) and t.get("source_relation") == "REPORTS_SAFETY_ADVICE" for t in threats)
                and not any(isinstance(t, dict) and t.get("is_threat") is True for t in threats)):
            next_steps = [
                "Review the captured guidance, cited examples and publication dates.",
                "Obtain a specific suspected listing, account or URL before assessing an active threat. Awareness advice alone does not justify a takedown.",
            ]

        return _complete_agent_report(UnifiedReport(
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
        ), brand_data, execution_log, queries_planned)

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
            personal_data.get("summary")
            or personal_data.get("status")
            or personal_data.get("identity_summary")
        )
        if isinstance(raw_summary, dict):
            raw_summary = personal_data.get("status_note") or "Sampled evidence requires contextual review; telemetry is shown separately."
        summary = _summary_text(raw_summary)

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
        changes = [_summary_text(c) for c in (personal_data.get("new_incidents") or personal_data.get("changes") or [])[:4]]
        changes = [text for text in changes if text]
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
        if isinstance(personal_data.get("public_statements"), list):
            p_intel["public_statements"] = [
                {key: row[key] for key in ("evidence_id", "speaker", "text", "start", "end", "attribution",
                    "quotation", "identity_authenticated", "interpretation") if key in row}
                for row in personal_data["public_statements"][:16] if isinstance(row, dict)]
        if isinstance(personal_data.get("disputed_claims"), list):
            p_intel["disputed_claims"] = [
                {key: row[key] for key in ("claim_id", "claim_type", "text", "evidence_ids", "source_passages",
                    "source_report_url", "source_published_at", "claim_status", "epistemic_state",
                    "assessment_status", "identity_authenticated", "interpretation") if key in row}
                for row in personal_data["disputed_claims"][:16] if isinstance(row, dict)]

        next_steps = [
            "Review the captured speaker attribution and original passage before sharing a quotation.",
            "Investigate a specific suspect account or media artifact before making an impersonation report; catalog matches and quotations do not authenticate identity.",
        ]

        return _complete_agent_report(UnifiedReport(
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
        ), personal_data, execution_log, queries_planned)


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _append_observed_evidence(evidence, records):
    """Generic evidence is not inherently primary, official or independent."""
    for record in _record_list(records):
        if not isinstance(record, dict):
            continue
        item = _dict_to_evidence_item(record)
        existing = [entry for bucket in (evidence.primary, evidence.independent, evidence.community) for entry in bucket]
        if any((item.evidence_id and item.evidence_id == entry.evidence_id)
               or (not item.evidence_id and item.url and item.url == entry.url) for entry in existing):
            continue
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
            captured_author=_str_val(raw_source.get("captured_author")),
            discovery_attribution=_str_val(raw_source.get("discovery_attribution")),
            attribution_conflict=bool(raw_source.get("attribution_conflict")),
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

    meta = d.get("metadata") or d.get("raw_metadata") or {}
    if isinstance(meta, dict) and meta.get("body_author"):
        source.captured_author = _str_val(meta["body_author"])
        source.discovery_attribution = _str_val(meta.get("discovery_author_or_source"))
        source.attribution_conflict = bool(meta.get("attribution_conflict"))
        source.name = source.captured_author

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
        snippet=_str_val(d.get("snippet") or d.get("relevant_excerpt") or d.get("content") or d.get("summary")),
        url=url,
        timestamp=_str_val(d.get("timestamp") or d.get("published_at") or d.get("published")),
        source=source,
        quality_tensor=qt,
        retrieval_lineage=lineage,
        extraction=inspect_evidence(d),
        evidence_id=_str_val(d.get("evidence_id") or d.get("id") or d.get("candidate_id")),
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
        contradiction=d.get("contradiction") if d.get("contradiction") is not None else d.get("contradiction_level"),
    )


def _summary_text(value):
    """A structured summary is not Python-dict prose or a factual verdict."""
    if isinstance(value, dict):
        value = next((value.get(key) for key in ("text", "summary", "description", "status_note")
                      if isinstance(value.get(key), str) and value[key].strip()), None)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _captured_observation_brief(data, details):
    """Repeat one complete captured paragraph with attribution, not a verdict."""
    from urllib.parse import urlsplit
    from backend.services.research.passage_extractor import has_usable_passage
    corpus = data.get("research_corpus") or {}
    records = _record_list(data.get("sources")) + _record_list(data.get("evidence"))
    records += _record_list(corpus.get("deep_read_sources")) if isinstance(corpus, dict) else []
    # Prefer an already-qualified target financial assertion over an earnings
    # calendar/logistics paragraph. This only changes display order, never the
    # words, attribution, fiscal scope, forecast labels or evidence acceptance.
    def brief_priority(detail):
        context = (detail.get("metadata") or {}).get("financial_context") or {}
        return not (context.get("content_kind") == "FINANCIAL_PERFORMANCE_ASSERTION"
                    and context.get("financial_assessment_eligible") is True
                    and context.get("issuer_mention")
                    and context.get("result_scope") == "REPORTED_SOURCE_ASSERTION")
    for detail in sorted(details, key=brief_priority):
        if (detail.get("metadata") or {}).get("observation_only") is not True:
            continue
        text = detail.get("statement")
        if not isinstance(text, str) or not 60 <= len(text) <= 1000:
            continue  # Never cut off an attribution, qualification or negation.
        ids = detail.get("supporting_evidence_ids") or []
        for record in records:
            if not isinstance(record, dict) or (record.get("id") or record.get("evidence_id")) not in ids:
                continue
            body = record.get("content") or ""
            if (not has_usable_passage(record) or text not in [p.strip() for p in re.split(r"\n\s*\n", body)]):
                continue
            try:
                host = urlsplit(record.get("canonical_url") or record.get("url") or "").hostname
            except ValueError:
                host = None
            if host:
                return f"Captured passage from {host} (source assertion; not independently verified): {text} "
    return ""


def _set_retained_publisher_trust(trust, evidence):
    """Count final-record publishers, never pre-specialist/verified independence."""
    from dataclasses import replace
    from urllib.parse import urlsplit
    from backend.services.research.proposition_grounding import publisher_key
    publishers = set()
    for bucket in (evidence.primary, evidence.independent, evidence.community):
        for item in bucket:
            try:
                parsed = urlsplit(item.url or "")
                if parsed.scheme in {"http", "https"} and parsed.hostname:
                    key = publisher_key(item.url)
                    if key:
                        publishers.add(key)
            except (TypeError, ValueError):
                continue
    trust.observed_publisher_count = len(publishers)
    trust.independent_source_count = None  # No verified-independence contract yet.
    if trust.quality_tensor is not None:
        # Internal grouping ratios (including 1/1) are not independence proof.
        trust.quality_tensor = replace(trust.quality_tensor, independence=None)


def _complete_agent_report(report, data, execution_log, queries_planned):
    """Preserve canonical observations at the four native-agent boundaries.

    Keep the old string/bucket projections for compatibility. Discovery stays
    separate from acquired sources, and no inference or new retrieval occurs.
    Explicit caller log=[] means no log: do not replace it through truthiness.
    """
    from copy import deepcopy

    details = []
    finding_texts = []
    for finding in _record_list(data.get("findings_structured")) + _record_list(data.get("findings")):
        if hasattr(finding, "to_dict"):
            finding = finding.to_dict()
        if isinstance(finding, dict):
            text = _summary_text(finding.get("statement") or finding.get("description")
                                 or finding.get("summary") or finding.get("title"))
            if text:
                details.append(deepcopy(finding))
        else:
            text = _summary_text(finding)
        if text and text not in finding_texts:
            finding_texts.append(text)
    report.finding_details = details
    assessments = [detail.get("metadata", {}).get("claim_assessment") for detail in details
                   if isinstance(detail.get("metadata"), dict)]
    if any(isinstance(assessment, dict) for assessment in assessments):
        report.claim_decomposition = [assessment for assessment in assessments if isinstance(assessment, dict)]
    # Scout's legacy catalysts are headline/polarity projections, not additional
    # passage-grounded findings. When canonical structured observations exist,
    # merging those headings back in can reintroduce forecasts or market-reaction
    # text that the passage/period gate deliberately did not select. Keep the
    # compatibility fallback only for payloads without usable structured findings.
    # Personal Watch likewise must not stringify legacy threat dictionaries as
    # extra findings beside canonical source-attributed passages.
    if report.agent in {"scout", "personal_watch"} and details:
        report.findings = finding_texts
    else:
        report.findings = list(dict.fromkeys(finding_texts + report.findings))

    # Rich canonical records take precedence over lossy legacy news summaries.
    canonical = UnifiedEvidenceSet()
    _append_observed_evidence(canonical, _record_list(data.get("sources")) + _record_list(data.get("evidence")))
    retained = [item for bucket in (canonical.primary, canonical.independent, canonical.community) for item in bucket]
    seen_ids = {item.evidence_id for item in retained if item.evidence_id}
    seen_urls = {item.url for item in retained if item.url}
    for name in ("primary", "independent", "community"):
        for item in getattr(report.evidence, name):
            if (item.evidence_id and item.evidence_id in seen_ids) or (item.url and item.url in seen_urls):
                continue
            getattr(canonical, name).append(item)
            if item.evidence_id:
                seen_ids.add(item.evidence_id)
            if item.url:
                seen_urls.add(item.url)
    report.evidence = canonical
    from backend.services.research.evidence_workbench import build_evidence_workbench
    report.evidence_workbench = build_evidence_workbench([
        item.to_dict() for bucket in (canonical.primary, canonical.independent, canonical.community) for item in bucket])

    # Legacy structured conflict types are not established merely because an
    # adapter named them FACTUAL_CONTRADICTION. Require explicit review and
    # inspectable paired passages, otherwise retain a labeled review lead.
    report.detailed_contradictions = deepcopy(report.detailed_contradictions)
    for conflict in report.detailed_contradictions:
        if not (conflict.get("established") is True and len(conflict.get("passage_references") or []) >= 2):
            conflict.setdefault("reported_type", conflict.get("type"))
            conflict["type"] = "POSSIBLE_DISAGREEMENT"
            conflict["established"] = False
            conflict["claim_support_verified"] = False

    corpus = data.get("research_corpus") or {}
    corpus = corpus if isinstance(corpus, dict) else {}
    raw_pool = corpus.get("raw_acquisition_pool") or {}
    raw_pool = raw_pool if isinstance(raw_pool, dict) else {}
    raw_sources = [source for source in _record_list(raw_pool.get("sources")) if isinstance(source, dict)]
    from collections import Counter
    raw_id_counts = Counter(source.get("source_id") for source in raw_sources)
    raw_by_id = {source["source_id"]: source for source in raw_sources
                 if source.get("source_id") and raw_id_counts[source["source_id"]] == 1}
    candidates = list(_record_list(corpus.get("ranked_candidates")))
    if isinstance(corpus.get("raw_acquisition_pool"), dict):
        # The acquisition-first path keeps read-eligible leads separate from
        # qualified evidence. Absence of findings must not hide those leads.
        candidates += [candidate for candidate in _record_list(corpus.get("raw_candidates"))
                       if isinstance(candidate, dict) and (candidate.get("metadata") or {}).get("harvest_acquisition_eligible")][:100]
    cited_ids = {e_id for detail in details for e_id in _record_list(detail.get("supporting_evidence_ids"))
                 if isinstance(e_id, str)}
    candidates += [item for item in _record_list(corpus.get("raw_candidates"))
                   if isinstance(item, dict) and (item.get("id") or item.get("evidence_id")) in cited_ids]
    discovery_seen = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        # A rejected acquired body is not an unread discovery snippet. Retain
        # its bounded inspection separately without promoting it to evidence.
        raw = raw_by_id.get(candidate.get("id") or candidate.get("evidence_id"))
        if raw and isinstance(raw.get("readable_text"), str) and raw["readable_text"]:
            candidate = {**candidate, "content": raw["readable_text"][:12_000],
                "content_depth": raw.get("content_depth") or "UNKNOWN", "read_status": raw.get("read_status"),
                "metadata": {**(candidate.get("metadata") or {}), "page_metadata": raw.get("page_metadata") or {}}}
        item = _dict_to_evidence_item(candidate)
        identity = item.evidence_id or item.url
        if not identity or identity in discovery_seen or item.evidence_id in seen_ids or item.url in seen_urls:
            continue
        discovery_seen.add(identity)
        # Qualification/read failure never promotes a candidate into a body.
        item.extraction["evidentiary_use"] = "DISCOVERY_ONLY"
        if raw:
            item.extraction.update(raw_source_type=raw.get("source_type"), read_status=raw.get("read_status"),
                qualification_status=raw.get("qualification_status"),
                qualification_reasons=raw.get("qualification_reasons") or [])
        item.source.is_primary = False
        report.discovery.append(item)

    discovery_ids = {item.evidence_id for item in report.discovery if item.evidence_id}
    for detail in details:
        # Presence of an ID is not entailment. Resolve what can actually be
        # inspected and disclose missing references instead of inventing text.
        detail["citation_observations"] = [
            {"evidence_id": e_id, "availability": "SOURCE_RECORD" if e_id in seen_ids
             else "DISCOVERY_ONLY" if e_id in discovery_ids else "UNAVAILABLE"}
            for e_id in _record_list(detail.get("supporting_evidence_ids")) if isinstance(e_id, str)]

    report.timeline = [TimelineEvent(
        timestamp=item.get("timestamp") or item.get("time") or item.get("ts"),
        description=item.get("description") or item.get("event_description") or item.get("title") or item.get("event"))
        for item in _record_list(data.get("timeline")) if isinstance(item, dict)]
    trace = data.get("deep_research_trace") or data.get("retrieval_trace") or {}
    trace = deepcopy(trace) if isinstance(trace, dict) else {}
    unresolved = data.get("catalysts", {}).get("unresolved", []) if isinstance(data.get("catalysts"), dict) else []
    if unresolved:
        report.processing_notes["unresolved_leads"] = [item for item in unresolved[:12] if isinstance(item, dict)]
    advice = trace.get("ai_passage_advice")
    if isinstance(advice, dict):
        report.processing_notes["ai_passage_advice"] = {
            key: advice[key] for key in ("status", "accepted", "rejected", "advisory_only", "entailment_verified")
            if key in advice and type(advice[key]) in (str, int, bool)}
    log = execution_log if execution_log is not None else data.get("query_log") or trace.get("query_records") or []
    planned = queries_planned or trace.get("queries_planned") or 0
    report.trust.query_telemetry = QueryTelemetry.from_execution_log(log, planned)
    count = trace.get("independent_source_groups")
    if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
        report.processing_notes["upstream_reporting_group_count"] = count
    _set_retained_publisher_trust(report.trust, canonical)
    generated_summary = not report.summary
    if generated_summary:
        record_count = sum(len(getattr(canonical, name)) for name in ("primary", "independent", "community"))
        report.summary = (f"Report retains {len(report.findings)} finding(s), {record_count} source record(s) "
                          f"and {len(report.discovery)} discovery-only candidate(s). "
                          "Claim support requires review of captured passages and acquisition limits.")
    if report.agent in {"brandshield", "personal_watch"}:
        from backend.services.research.specialist_brief import specialist_brief
        coverage, brief, steps = specialist_brief(data, report.agent, report.query, len(report.discovery))
        report.processing_notes["specialist_coverage"] = coverage
        if not isinstance(data.get("summary"), str):
            report.summary = brief
        if coverage["status"] == "INSUFFICIENT_EVIDENCE":
            report.next_steps = steps
    acquisition = trace.get("acquisition")
    metrics = trace.get("acquisition_metrics")
    has_acquisition_metrics = isinstance(metrics, dict)
    if isinstance(metrics, dict):
        report.processing_notes["acquisition_metrics"] = deepcopy(metrics)
        report.processing_notes["research_profile"] = trace.get("research_profile")
    if isinstance(trace.get("discovery_funnel"), dict):
        # Saved legacy traces can mix hundreds of navigation/link observations
        # into qualification_rejections. Reproject, never rewrite saved proof.
        from backend.services.research.discovery_funnel import summarize_qualification_decisions
        funnel = trace["discovery_funnel"]
        if "qualification_decision_count" not in funnel:
            funnel.update(summarize_qualification_decisions(funnel.get("qualification_rejections") or []))
        report.processing_notes["discovery_funnel"] = deepcopy(trace["discovery_funnel"])
        funnel = trace["discovery_funnel"]
        report.processing_notes["research_outcome"] = (
            "QUALIFIED_ARTICLE_OBSERVATIONS" if funnel.get("qualified_evidence", 0) else
            "INSUFFICIENT_ARTICLE_EVIDENCE" if funnel.get("successful_body_captures", 0) else "NO_ARTICLE_ACQUIRED")
    funnel = trace.get("discovery_funnel") or {}
    metrics = metrics if isinstance(metrics, dict) else {}
    observed_captures = sum(bool(source.get("readable_text")) for source in raw_sources)
    capture_values = [value for value in (metrics.get("successful_captures"), funnel.get("raw_capture_count"))
                      if type(value) is int and value >= 0]
    raw_count = max(capture_values + [observed_captures]) if capture_values or raw_sources else None
    article_values = [value for value in (metrics.get("article_bodies"), funnel.get("extracted_article_bodies"))
                      if type(value) is int and value >= 0]
    article_count = max(article_values + [sum(bool(source.get("readable_text")) and source.get("source_type") == "ARTICLE_BODY"
                        for source in raw_sources)]) if article_values or raw_sources else None
    if raw_count is not None:
        report.processing_notes["captured_source_summary"] = {
            "raw_captures": raw_count, "article_bodies": article_count,
            "displayed_qualified_sources": sum(len(getattr(canonical, bucket)) for bucket in ("primary", "independent", "community")),
            "scope": "Captured content is not automatically task-relevant evidence or a verified finding"}
        # Raw captures are stronger observations than an old status calculated
        # from a post-qualification empty evidence list. Preserve its origin.
        if isinstance(acquisition, dict) and raw_count and acquisition.get("status") == "ACQUISITION_FAILED":
            acquisition = {**acquisition, "reported_status": acquisition["status"],
                "status": "INSUFFICIENT_EVIDENCE", "raw_capture_count": raw_count,
                "message": "Source content was captured, but no usable task-relevant evidence qualified. Inspect captured structure and per-source decisions."}
    if not isinstance(acquisition, dict) and (log or trace.get("deep_read_attempted")):
        from backend.services.research.acquisition_status import acquisition_outcome
        record_count = sum(len(getattr(canonical, bucket)) for bucket in ("primary", "independent", "community"))
        acquisition = acquisition_outcome(log, record_count, trace.get("deep_read_attempted", 0),
            raw_capture_count=raw_count, qualified_count=record_count)
    if isinstance(acquisition, dict):
        report.investigation_status = acquisition.get("status")
        report.processing_notes["acquisition"] = acquisition
        if acquisition.get("status") == "ACQUISITION_FAILED":
            report.summary = acquisition.get("message") or "Unable to retrieve evidence."
            report.findings = []
            report.finding_details = []
            report.disagreements = []
            report.detailed_contradictions = []
            report.agent_intelligence = {}
            report.next_steps = ["Inspect query-level failures below; retry only after the access or timeout failure is addressed."]
    if report.investigation_status != "ACQUISITION_FAILED":
        funnel = trace.get("discovery_funnel") or {}
        if (report.investigation_status == "COMPLETED" and (
                funnel and not funnel.get("qualified_evidence", 0)
                or raw_count and not report.findings and not any(getattr(canonical, bucket)
                    for bucket in ("primary", "independent", "community")))):
            # COMPLETED here describes transport, not a research conclusion.
            # Background hubs/profiles cannot turn the investigation green.
            report.investigation_status = "INSUFFICIENT_EVIDENCE"
        if not report.findings and raw_count:
            failures = metrics.get("failed_reads_by_cause") or funnel.get("read_failure_reasons") or {}
            failure_text = ", ".join(f"{reason}: {count}" for reason, count in sorted(failures.items())
                                     if type(count) is int and count > 0) or "none recorded"
            reasons = funnel.get("qualification_rejection_counts_by_reason") or {}
            if not reasons:
                reasons = Counter(reason for source in raw_sources for reason in source.get("qualification_reasons", [])
                                  if isinstance(reason, str))
            reason_text = ", ".join(f"{reason}: {count}" for reason, count in sorted(reasons.items())) or "inspect per-source structure/relevance/passage decisions"
            report.summary = (f"Acquisition retained {raw_count} raw capture(s)"
                + (f", including {article_count} article body/bodies" if article_count is not None else "")
                + ", but no task-qualified finding was returned. Captures are not automatically evidence. "
                + f"Qualification reasons: {reason_text}. Read failures: {failure_text}. "
                + "This does not establish that no relevant public information exists.")
        elif not report.findings and not funnel.get("successful_body_captures", 0) and funnel.get("qualification_rejections"):
            from collections import Counter
            reasons = Counter(row.get("rejection_stage") or "QUALIFICATION" for row in funnel["qualification_rejections"]
                              if isinstance(row, dict))
            # Rows without an identity remain decision observations, never a
            # fabricated count of distinct rejected sources.
            report.summary = ("No eligible source body was acquired. Qualification decision observations: "
                              + ", ".join(f"{reason}: {count}" for reason, count in reasons.items())
                              + ". These are discovery observations, not proof that no relevant information exists. "
                              + ("Trending retains its 48-hour freshness requirement. " if report.agent == "trending" else ""))
        elif generated_summary:
            report.summary = _captured_observation_brief(data, details) + report.summary
        if report.agent == "trending" and not report.findings and has_acquisition_metrics:
            # Do not hide a freshness/access failure behind a zero-count brief.
            # Feed timestamps are leads; only acquired publication declarations
            # can support the current-article evidence window.
            decisions = Counter(str(reason).split(":", 1)[0] for source in raw_sources
                for reason in source.get("qualification_reasons", [])
                if isinstance(reason, str) and reason.startswith("TEMPORAL_"))
            failures = metrics.get("failed_reads_by_cause") or {}
            failed = sum(count for count in failures.values() if isinstance(count, int) and count > 0)
            reason_text = ", ".join(f"{reason}: {count}" for reason, count in sorted(decisions.items())) or "no acquired article met subject/date/passage requirements"
            report.summary = (f"No recent article qualified for the 48-hour research window. "
                + (f"{raw_count} raw capture(s) retained; " if raw_count is not None else "")
                +
                f"{metrics.get('article_bodies', 0)} article capture(s); qualification decisions: {reason_text}; "
                f"{failed} failed read(s). Fresh-looking feed entries remain discovery leads, not current article evidence. "
                "This does not measure popularity or establish an absence of new developments.")
    reference = trace.get("reference_background")
    if isinstance(reference, dict):
        report.agent_intelligence["reference_background"] = deepcopy(reference)
    return report
