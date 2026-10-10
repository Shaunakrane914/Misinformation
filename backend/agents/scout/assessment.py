"""
Aegis Protocol — Scout Assessment & Synthesis Engine
====================================================
Cross-channel rumor correlation, evidence-grounded catalyst synthesis,
narrative theme detection, and contradiction assessment for Agent 1 Scout.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
    sources: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Synthesize financial intelligence over retrieved evidence fragments.
    Relies strictly on provided evidence. Never hallucinates facts, dates, or sources.
    """
    if not sources:
        return {
            "catalysts": {"positive": [], "negative": [], "unresolved": []},
            "risks": ["No verified online sources retrieved across monitored channels."],
            "narratives": [],
            "contradictions": {"for": [], "against": [], "unresolved": []},
            "misinformation": {
                "status": "NOMINAL",
                "rumors_detected": [],
                "manipulation_risk": "LOW",
                "evidence_quality_score": 0.0,
                "notes": "Zero external records discovered for cross-verdict synthesis."
            }
        }

    source_summary = "\n".join([
        f"[{s['evidence_id']}] ({s['source_role']}) {s['source']}: {s['title']} — {s['snippet'][:160]}"
        for s in sources[:12]
    ])

    prompt = f"""You are a principal financial intelligence analyst at Aegis Protocol.
Analyze the following retrieved market evidence for {company_name} ({ticker}).
CRITICAL RULE: Rely ONLY on the provided evidence below. DO NOT invent, assume, or hallucinate any facts, dates, filings, or sources.

RETRIEVED EVIDENCE:
{source_summary}

STOCK STATUS: Price {stock_data.get('current_price', 'N/A')} {stock_data.get('currency', '')}, 24h Change {stock_data.get('drop_percent', 0)}%, Z-Score {stock_data.get('z_score', 0)}

TASK:
Respond in STRICT JSON with this schema:
{{
  "catalysts": {{
    "positive": [{{"catalyst": "Concise factual statement", "impact": "High|Medium|Low", "evidence_ids": ["src_001"]}}],
    "negative": [{{"catalyst": "Concise factual statement", "impact": "High|Medium|Low", "evidence_ids": ["src_002"]}}],
    "unresolved": [{{"factor": "Concise factual statement", "evidence_ids": ["src_003"]}}]
  }},
  "risks": ["Specific risk grounded directly in evidence"],
  "narratives": [
    {{"theme": "Theme Name", "description": "Brief summary", "sentiment": "Bullish|Bearish|Neutral", "evidence_ids": ["src_001"]}}
  ],
  "contradictions": {{
    "for": ["Grounded supporting point"],
    "against": ["Grounded contradicting point"],
    "unresolved": ["Ambiguous or conflicting aspect"]
  }},
  "misinformation": {{
    "status": "NOMINAL|ELEVATED|CRITICAL",
    "rumors_detected": ["Any unverified or sensationalized claim"],
    "manipulation_risk": "LOW|MEDIUM|HIGH",
    "evidence_quality_score": 0.85,
    "primary_corroboration": true
  }}
}}"""

    try:
        from backend.services.gemini_service import gemini_service
        raw_text = gemini_service.generate_text(prompt)
        cleaned = raw_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "catalysts" in parsed:
            return parsed
    except Exception as e:
        logger.debug(f"[ScoutAssessment:synthesize] LLM synthesis notice, using grounded rule-based parsing: {e}")

    # Deterministic evidence-grounded fallback extraction
    pos_cats = []
    neg_cats = []
    unres_cats = []
    narratives = []
    risks = []
    rumors = []

    pos_kw = ["growth", "profit", "surge", "gain", "rally", "deal", "order", "boost", "strong", "outperform", "expand"]
    neg_kw = ["drop", "crash", "plunge", "fall", "debt", "investigation", "probe", "loss", "fraud", "lawsuit", "defect"]
    rumor_kw = ["rumor", "unverified", "alleged", "claim", "hoax", "speculation", "leak"]

    for s in sources:
        text = f"{s['title']} {s['snippet']}".lower()
        if any(k in text for k in pos_kw):
            pos_cats.append({
                "catalyst": s['title'][:110],
                "impact": "Medium",
                "evidence_ids": [s['evidence_id']]
            })
        elif any(k in text for k in neg_kw):
            neg_cats.append({
                "catalyst": s['title'][:110],
                "impact": "High" if "investigation" in text or "fraud" in text else "Medium",
                "evidence_ids": [s['evidence_id']]
            })
        else:
            unres_cats.append({
                "factor": s['title'][:110],
                "evidence_ids": [s['evidence_id']]
            })

        if any(k in text for k in rumor_kw):
            rumors.append(s['title'][:100])

    if any("earnings" in s['title'].lower() or "result" in s['title'].lower() for s in sources):
        narratives.append({
            "theme": "Earnings & Financial Performance",
            "description": f"Market focus on operational margins and periodic results for {company_name}.",
            "sentiment": "Neutral",
            "evidence_ids": [s['evidence_id'] for s in sources if "earning" in s['title'].lower() or "result" in s['title'].lower()]
        })
    if any("regulatory" in s['title'].lower() or "investigation" in s['title'].lower() for s in sources):
        narratives.append({
            "theme": "Regulatory & Legal Scrutiny",
            "description": f"Regulatory compliance or inquiry signals observed in discourse.",
            "sentiment": "Bearish",
            "evidence_ids": [s['evidence_id'] for s in sources if "regulatory" in s['title'].lower() or "investigation" in s['title'].lower()]
        })
    if not narratives:
        narratives.append({
            "theme": "General Market Momentum",
            "description": f"Trading volume and sector momentum surrounding {company_name}.",
            "sentiment": "Neutral",
            "evidence_ids": [sources[0]['evidence_id']] if sources else []
        })

    for nc in neg_cats[:3]:
        risks.append(nc["catalyst"])
    if not risks:
        risks.append(f"Standard macroeconomic and sector-wide volatility impacting {company_name}.")

    return {
        "catalysts": {
            "positive": pos_cats[:4],
            "negative": neg_cats[:4],
            "unresolved": unres_cats[:3]
        },
        "risks": risks[:4],
        "narratives": narratives[:3],
        "contradictions": {
            "for": [p["catalyst"] for p in pos_cats[:2]],
            "against": [n["catalyst"] for n in neg_cats[:2]],
            "unresolved": [u["factor"] for u in unres_cats[:2]]
        },
        "misinformation": {
            "status": "ELEVATED" if rumors else "NOMINAL",
            "rumors_detected": rumors[:3],
            "manipulation_risk": "ELEVATED" if len(rumors) >= 2 else ("MEDIUM" if rumors else "LOW"),
            "evidence_quality_score": round(min(0.95, 0.50 + 0.05 * len(sources)), 2),
            "primary_corroboration": any(s["source_role"] == "PRIMARY" for s in sources)
        }
    }


__all__ = [
    "correlate_social_rumors",
    "synthesize_financial_intelligence",
]
