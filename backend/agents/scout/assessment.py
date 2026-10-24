"""
Aegis Protocol — Scout Assessment & Synthesis Engine
====================================================
Cross-channel rumor correlation, evidence-grounded catalyst synthesis,
narrative theme detection, and contradiction assessment for Agent 1 Scout.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def financial_source_observation(source, company_name):
    """Inspectable financial context, without currency/period/entity invention.

    This is an observation of a retained passage, not extraction of comparable
    filing facts. Related legal entities, estimates, currencies and reporting
    periods remain separate even when they occur under the same brand root.
    """
    from backend.services.research.financial_context import financial_passage_context
    passage = str(source.get("relevant_excerpt") or source.get("content") or "")
    body = str(source.get("content") or "")
    start = body.find(passage) if passage else -1
    target = re.sub(r"\([^)]*\)", "", company_name or "").strip()
    extended_names = []
    if target:
        for match in re.finditer(r"\b" + re.escape(target) + r"\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)", str(source.get("title") or "")):
            if match.group(1).casefold() not in {"shares", "earnings", "sees", "profit", "targets", "stock", "projects", "reports", "posts"}:
                extended_names.append(match.group())
    context = financial_passage_context(passage, title=source.get("title", ""),
        published_at=source.get("published_at", ""),
        observed_at=source.get("retrieved_at") or source.get("acquired_at") or "", issuer=company_name)
    source_id = source.get("evidence_id") or source.get("id")
    return {"evidence_id": source_id, "source_url": source.get("url") or source.get("canonical_url"),
        "published_at": source.get("published_at") or None,
        "passage": {"text": passage, "start": start, "end": start + len(passage) if start >= 0 else -1,
                    "exact_capture_span": start >= 0},
        "observed_entity_names": list(dict.fromkeys(extended_names)),
        "entity_alignment": "EXTENDED_ENTITY_REQUIRES_REVIEW" if extended_names else "SOURCE_MENTIONS_TARGET_NOT_AUTHENTICATED",
        **context,
        "publisher_independence_verified": False,
        "interpretation": "Retained corporate-news passage; related entities, periods, currencies and forecasts must not be reconciled as the same financial fact."}


def _financial_direction(text):
    """Conservative lexical direction of an observed passage, not investment advice.

    A bare 'profit', 'growth opportunity' or hypothetical forecast cannot establish
    a positive catalyst. Mixed directions and negated/uncertain claims abstain.
    """
    if re.search(r"\b(?:not|never|no|denied|denies|unverified|alleged|rumou?r|speculat\w*|forecast\w*|project\w*|estimat\w*|expect\w*|guidance|outlook|will|may|could|would)\b", text, re.I):
        return "unresolved", "NEGATED_OR_UNCERTAIN_CONTEXT"
    metrics = r"(?:profits?|revenues?|earnings|sales|margins?|cash flow|operating income|shares?|stock price|dividends?|orders?)"
    up = r"(?:grew|grown|growth|rose|risen|rise|rises|rising|increas\w*|surged?|surges|gain\w*|jump\w*|expand\w*|higher|improv\w*)"
    down = r"(?:fell|fallen|fall|falls|falling|declin\w*|drop\w*|decreas\w*|plung\w*|slump\w*|lower|shrank|contract\w*|down)"
    gap = r"[^.!?;\n]{0,45}"
    positive = bool(re.search(r"\b" + metrics + r"\b" + gap + r"\b" + up + r"\b|\b" + up + r"\b" + gap + r"\b" + metrics + r"\b", text, re.I))
    negative = bool(re.search(r"\b" + metrics + r"\b" + gap + r"\b" + down + r"\b|\b" + down + r"\b" + gap + r"\b" + metrics + r"\b", text, re.I))
    negative = negative or bool(re.search(r"\b(?:reported|posted|recorded)\s+(?:an?\s+)?(?:net\s+|operating\s+)?loss\b|\b(?:regulatory investigation|fraud investigation|filed for bankruptcy)\b", text, re.I))
    if positive and negative:
        return "unresolved", "MIXED_DIRECTIONAL_OBSERVATIONS"
    if positive:
        return "positive", "OBSERVED_FINANCIAL_INCREASE_HEURISTIC"
    if negative:
        return "negative", "OBSERVED_FINANCIAL_DECREASE_HEURISTIC"
    return "unresolved", "NO_UNAMBIGUOUS_DIRECTION"


def correlate_social_rumors(ticker: str) -> Dict[str, Any]:
    """
    Correlate stock price volatility with real-time Reddit (WSB), Twitter ($CASHTAG),
    and YouTube financial analysis signals via AgentReach omni-scan.
    """
    social_intel = {
        "social_signals_detected": 0,
        "short_seller_risk": "LOW",
        "reddit_discussions": [],
        "twitter_cashtags": [],
        "youtube_analyses": [],
        "news_catalysts": []
    }
    try:
        from backend.services.agent_reach.adapter import agent_reach_service
        omni_data = agent_reach_service.omni_scan(
            query=ticker,
            domain="financial",
            limit_per_channel=4
        )

        channels = omni_data.get("channels", {})
        r_items = channels.get("reddit", [])
        t_items = channels.get("twitter", [])
        y_items = channels.get("youtube", [])
        n_items = channels.get("news", [])

        social_intel["reddit_discussions"] = [
            {"title": r.get("title", ""), "url": r.get("url", ""), "author": r.get("author", "u/trader")}
            for r in r_items
        ]
        social_intel["twitter_cashtags"] = [
            {"text": t.get("content", ""), "author": t.get("author", "@pulse"), "url": t.get("url", "")}
            for t in t_items
        ]
        social_intel["youtube_analyses"] = [
            {"title": y.get("title", ""), "url": y.get("url", "")}
            for y in y_items
        ]
        social_intel["news_catalysts"] = [
            {"title": n.get("title", ""), "source": n.get("source", "Wire"), "url": n.get("url", "")}
            for n in n_items
        ]

        total_signals = len(r_items) + len(t_items) + len(y_items) + len(n_items)
        social_intel["social_signals_detected"] = total_signals

        # Detect panic keywords across social discourse
        panic_keywords = ["crash", "scam", "fraud", "short", "investigation", "bankrupt", "dump", "sec", "probe"]
        all_text = " ".join([r.get("title", "") for r in r_items] + [t.get("content", "") for t in t_items]).lower()
        panic_hits = sum(1 for kw in panic_keywords if kw in all_text)

        if panic_hits >= 4:
            social_intel["short_seller_risk"] = "CRITICAL (High Coordinated Short Buzz)"
        elif panic_hits >= 2:
            social_intel["short_seller_risk"] = "ELEVATED (Rumor Discourse Active)"
        else:
            social_intel["short_seller_risk"] = "NOMINAL (Standard Chatter)"

    except Exception as e:
        logger.debug(f"[ScoutAssessment:correlate_social_rumors] Scraper notice: {e}")

    return social_intel


def synthesize_financial_intelligence(
    company_name: str,
    ticker: str,
    stock_data: Dict[str, Any],
    sources: List[Dict[str, Any]],
    intent: str = "",
) -> Dict[str, Any]:
    """
    Synthesize financial intelligence over retrieved evidence fragments.
    Relies strictly on provided evidence. Never hallucinates facts, dates, or sources.
    """
    from backend.services.research.passage_extractor import has_usable_passage
    sources = [source for source in sources if has_usable_passage(source)]
    if not sources:
        return {
            "catalysts": {"positive": [], "negative": [], "unresolved": []},
            "risks": ["No verified online sources retrieved across monitored channels."],
            "narratives": [],
            "contradictions": {"for": [], "against": [], "unresolved": []},
            "misinformation": {
                "status": "INSUFFICIENT_EVIDENCE",
                "rumors_detected": [],
                "manipulation_risk": "UNASSESSED",
                "evidence_quality_score": None,
                "notes": "No substantive acquired passages available for synthesis; discovery-only or navigation/profile records may still exist."
            }
        }

    # Final financial assessment is deterministic; AI cannot adjudicate claims.

    # Deterministic evidence-grounded fallback extraction
    pos_cats = []
    neg_cats = []
    unres_cats = []
    narratives = []
    risks = []
    rumors = []
    observations = []

    rumor_kw = ["rumor", "unverified", "alleged", "claim", "hoax", "speculation", "leak"]

    assessment_sources = []
    background_observations = []
    undated_observations = []
    strategy_observations = []
    incomplete_observations = []
    for s in sources:
        passage = str(s.get("relevant_excerpt") or s.get("content") or "")
        # A headline is a lead, not the financial proposition. In particular a
        # bullish title must not override a qualified or forecast-only passage.
        text = passage.lower()
        observation = financial_source_observation(s, company_name)
        if intent:
            from backend.services.research.financial_context import financial_passage_context
            observation.update(financial_passage_context(passage, title=s.get("title", ""),
                published_at=s.get("published_at", ""),
                observed_at=s.get("retrieved_at") or s.get("acquired_at") or "", issuer=company_name, intent=intent))
        observations.append(observation)
        if observation["publication_scope"] == "HISTORICAL_BACKGROUND":
            background_observations.append(observation)
        if observation["content_kind"] == "CORPORATE_STRATEGY_CONTEXT":
            strategy_observations.append(observation)
            # Brand strategy is retained corporate context, not a financial
            # result, measured market catalyst, or a filing comparison.
            continue
        if observation["content_kind"] == "FINANCIAL_CONTEXT_INCOMPLETE":
            # Recent publication is not financial eligibility. A biography or
            # other on-company paragraph remains inspectable context, not an
            # unresolved financial catalyst merely because its title says results.
            incomplete_observations.append(observation)
            continue
        if not observation["financial_assessment_eligible"]:
            if observation["publication_scope"] != "HISTORICAL_BACKGROUND":
                undated_observations.append(observation)
                unres_cats.append({"factor": s['title'][:110], "evidence_ids": [s['evidence_id']],
                    "classification_basis": observation["publication_scope"], "assessment_is_heuristic": True,
                    "publication_scope": observation["publication_scope"], "current_financial_conclusion": False})
            continue
        assessment_sources.append(s)
        direction, reason = _financial_direction(text)
        context_fields = {"publication_scope": observation["publication_scope"],
            "assessment_scope": observation["assessment_scope"],
            "observed_period_labels": observation["observed_period_labels"],
            "observed_currencies": observation["observed_currencies"],
            "period_alignment": "NOT_RECONCILED", "filing_comparison_status": "NOT_PERFORMED"}
        if direction == "positive":
            pos_cats.append({
                "catalyst": s['title'][:110],
                "impact": "Medium",
                "evidence_ids": [s['evidence_id']], "classification_basis": reason,
                "assessment_is_heuristic": True, **context_fields
            })
        elif direction == "negative":
            neg_cats.append({
                "catalyst": s['title'][:110],
                "impact": "High" if "investigation" in text or "fraud" in text else "Medium",
                "evidence_ids": [s['evidence_id']], "classification_basis": reason,
                "assessment_is_heuristic": True, **context_fields
            })
        else:
            unres_cats.append({
                "factor": s['title'][:110],
                "evidence_ids": [s['evidence_id']], "classification_basis": reason,
                "assessment_is_heuristic": True, **context_fields
            })

        if any(k in text for k in rumor_kw):
            rumors.append(s['title'][:100])

    if any("earnings" in s['title'].lower() or "result" in s['title'].lower() for s in assessment_sources):
        narratives.append({
            "theme": "Earnings & Financial Performance",
            "description": f"Sampled reporting discusses results for {company_name}; fiscal periods remain separate and unreconciled.",
            "sentiment": "Neutral",
            "evidence_ids": [s['evidence_id'] for s in assessment_sources if "earning" in s['title'].lower() or "result" in s['title'].lower()]
        })
    if any("regulatory" in s['title'].lower() or "investigation" in s['title'].lower() for s in assessment_sources):
        narratives.append({
            "theme": "Regulatory & Legal Scrutiny",
            "description": f"Regulatory compliance or inquiry signals observed in discourse.",
            "sentiment": "Bearish",
            "evidence_ids": [s['evidence_id'] for s in assessment_sources if "regulatory" in s['title'].lower() or "investigation" in s['title'].lower()]
        })
    if not narratives:
        narratives.append({
            "theme": "Unclassified sampled references",
            "description": "Retrieved records did not establish a current market catalyst; historical/undated observations are separate context, not current verification.",
            "sentiment": "Neutral",
            "evidence_ids": [sources[0]['evidence_id']] if sources else []
        })

    for nc in neg_cats[:3]:
        risks.append(nc["catalyst"])
    if not risks:
        risks.append("No specific market risk was established from the sampled records.")

    return {
        "catalysts": {
            "positive": pos_cats[:4],
            "negative": neg_cats[:4],
            "unresolved": unres_cats[:3]
        },
        "risks": risks[:4],
        "narratives": narratives[:3],
        "contradictions": {
            # Polarity is already represented by catalysts. Headings alone do
            # not establish opposing propositions or passage-level conflicts.
            "for": [], "against": [], "unresolved": []
        },
        "misinformation": {
            "status": "UNVERIFIED" if rumors else "INSUFFICIENT_EVIDENCE",
            "rumors_detected": rumors[:3],
            "manipulation_risk": "UNASSESSED",
            "evidence_quality_score": None,
            "primary_corroboration": False,
            "notes": "Corporate-news source assertions only; no claim entailment, independent corroboration or filing reconciliation is established."
        },
        "financial_observations": observations,
        "financial_context_summary": {"current_reporting_context_count": sum(o["current_assessment_eligible"] for o in observations),
            "historical_background_count": len(background_observations), "unknown_or_future_date_count": len(undated_observations),
            "corporate_strategy_context_count": len(strategy_observations),
            "incomplete_financial_context_count": len(incomplete_observations),
            "historical_background_evidence_ids": [o["evidence_id"] for o in background_observations],
            "period_alignment": "NOT_RECONCILED", "filing_comparison_status": "NOT_PERFORMED",
            "interpretation": "Publication recency is a display heuristic, not fiscal-period alignment or proof of current company performance."},
        "filing_comparison": {"status": "NOT_PERFORMED", "comparisons": [],
            "reason": "No comparable acquired filing/claim assessment was performed; article counts are not filing reconciliation."},
    }


def compare_sec_filing_numbers(
    filing_facts: Dict[str, Any],
    circulating_claims: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 8C Scout Specialization:
    Direct numerical comparison between official regulatory filings (e.g. SEC 10-K, 10-Q, 8-K)
    and circulating financial social media claims or whisper numbers.
    Computes exact percentage deviations, contradiction thresholds (>20%), and citation anchors.
    """
    if not filing_facts or not circulating_claims:
        return {
            "status": "INSUFFICIENT_DATA",
            "comparisons": [],
            "anomalies_detected": 0,
            "summary": "Insufficient filing facts or circulating claims provided for comparative audit."
        }

    comparisons: List[Dict[str, Any]] = []
    anomalies = 0

    from backend.services.research.source_quality import canonical_hostname, hostname_matches
    import math
    filing_url = filing_facts.get("source_url") or filing_facts.get("filing_url", "")
    period = filing_facts.get("period", "")

    for claim in circulating_claims:
        metric = claim.get("metric", "").lower().strip()
        claimed_val = claim.get("claimed_value")
        if claimed_val is None:
            continue
        if (not hostname_matches(canonical_hostname(filing_url), "sec.gov")
                or not period or claim.get("period") != period
                or not filing_facts.get("unit") or claim.get("unit") != filing_facts.get("unit")
                or not isinstance(claimed_val, (int, float)) or not math.isfinite(claimed_val)):
            comparisons.append({"metric": metric, "status": "UNVERIFIED_ALIGNMENT", "verdict": "UNVERIFIED",
                                "citation": filing_url, "explanation": "A trusted filing URL and matching period/unit are required for numeric comparison."})
            continue

        # Look up metric in official filing facts
        official_val = None
        for k, v in filing_facts.items():
            if k.lower() == metric:
                if isinstance(v, (int, float)):
                    official_val = float(v)
                    break

        if official_val is None or official_val == 0 or not math.isfinite(official_val):
            comparisons.append({
                "metric": metric,
                "circulating_claim": claim.get("raw_text", str(claimed_val)),
                "claimed_value": claimed_val,
                "official_filing_value": None,
                "status": "UNVERIFIED_IN_FILING",
                "discrepancy_pct": None,
                "citation": filing_url,
                "verdict": "UNVERIFIED"
            })
            continue

        # Compute percentage deviation
        delta_pct = round(((claimed_val - official_val) / abs(official_val)) * 100.0, 2)
        ratio = max(abs(claimed_val), abs(official_val)) / min(abs(claimed_val), abs(official_val)) if min(abs(claimed_val), abs(official_val)) > 0 else None

        if abs(delta_pct) > 20.0:
            status = "CONTRADICTED_BY_OFFICIAL_FILING"
            verdict = "REFUTED"
            anomalies += 1
            expl = (
                f"Significant numerical divergence on {metric}: Circulating rumor asserts {claim.get('raw_text', claimed_val)} "
                f"({claimed_val}), but official SEC filing records {official_val} ({delta_pct:+}% deviation)."
            )
        elif abs(delta_pct) <= 5.0:
            status = "CORROBORATED_BY_FILING"
            verdict = "SUPPORTED"
            expl = f"Circulating value on {metric} matches official SEC filing within 5% tolerance."
        else:
            status = "MINOR_VARIANCE"
            verdict = "MIXED"
            expl = f"Reported value deviates from filing by {delta_pct:+}%, potentially reflecting non-GAAP adjustments or different reporting periods."

        comparisons.append({
            "metric": metric,
            "period": period,
            "circulating_claim": claim.get("raw_text", str(claimed_val)),
            "claimed_value": claimed_val,
            "official_filing_value": official_val,
            "status": status,
            "discrepancy_pct": delta_pct,
            "discrepancy_ratio": round(ratio, 2) if ratio is not None else None,
            "citation": filing_url,
            "explanation": expl,
            "verdict": verdict,
            "source_claim_url": claim.get("url", "")
        })

    return {
        "status": "ANOMALIES_DETECTED" if anomalies > 0 else "INSUFFICIENT_ALIGNMENT" if all(c["verdict"] == "UNVERIFIED" for c in comparisons) else "CONSISTENT",
        "comparisons": comparisons,
        "anomalies_detected": anomalies,
        "filing_citation": filing_url,
        "summary": (
            f"Evaluated {len(comparisons)} quantitative financial claims against official filing. "
            f"Identified {anomalies} significant discrepancies (>20% threshold)."
        )
    }


def evaluate_corporate_rumor(
    ticker: str,
    rumor_text: str,
    evidence: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 8C Scout Specialization:
    Cross-checks a specific corporate rumor (e.g. undisclosed acquisition, executive exit, regulatory probe)
    against primary financial filings, regulatory notices, and wire reporting.
    Returns calibrated non-binary verdict, confidence score, and exact citations.
    """
    if not evidence:
        return {
            "ticker": ticker,
            "rumor": rumor_text,
            "verdict": "INSUFFICIENT_EVIDENCE",
            "confidence": 0.0,
            "explanation": "Zero evidence items retrieved. Truthful refusal to speculate.",
            "citations": []
        }

    from backend.services.research.claim_intelligence import claim_intelligence_engine
    from backend.services.research.research_models import EvidenceItem

    # Convert evidence dicts to typed EvidenceItems
    typed_evidence = []
    for idx, e in enumerate(evidence):
        typed_evidence.append(EvidenceItem(
            id=e.get("evidence_id", f"ev_scout_{idx+1}"),
            canonical_url=e.get("url", ""),
            title=e.get("title", ""),
            source_name=e.get("source", e.get("platform", "Source")),
            source_role=e.get("source_role", "DISCOVERY"),
            source_tier=e.get("source_tier", "TIER_3_AGGREGATE"),
            primary_source=e.get("source_role") in ("PRIMARY", "PRIMARY_OFFICIAL", "PRIMARY_REGULATORY") or e.get("primary_source", False),
            snippet=e.get("snippet", ""),
            relevant_excerpt=e.get("content", e.get("snippet", "")),
            published_at=e.get("published_at", "")
        ))

    synthesis = claim_intelligence_engine.synthesize_intelligence(
        text_or_claims=rumor_text,
        evidence_items=typed_evidence,
        target_name=ticker
    )

    return {
        "ticker": ticker,
        "rumor": rumor_text,
        "verdict": synthesis["overall_verdict"],
        "confidence": synthesis["overall_confidence"],
        "claims_evaluated": synthesis["claims"],
        "contradictions": synthesis["contradictions"],
        "citations": synthesis["citations"],
        "epistemic_breakdown": synthesis["epistemic_breakdown"]
    }


__all__ = [
    "compare_sec_filing_numbers",
    "correlate_social_rumors",
    "evaluate_corporate_rumor",
    "synthesize_financial_intelligence",
]

