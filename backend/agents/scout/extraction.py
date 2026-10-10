"""
Aegis Protocol — Scout Domain Extraction Engine
================================================
Consumes normalized EvidenceFragment[] records produced by the Shared Acquisition
Fabric and extracts structured financial facts, corporate catalysts, social rumor
signals, and contradiction matrices. Never initiates direct network requests.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.agents.scout.models import (
    CorporateEvent,
    FinancialContradiction,
    FinancialFact,
    ScoutExtractionResult,
)
from backend.services.agent_reach.channels import EvidenceFragment

logger = logging.getLogger(__name__)


class ScoutExtractionEngine:
    """
    Dedicated extraction engine for Scout.
    Consumes EvidenceFragment[] and extracts trading/market intelligence.
    Never initiates network requests directly.
    """

    def extract(
        self,
        fragments: List[EvidenceFragment],
        ticker_or_company: str = "",
        symbol: str = "",
        company_name: str = "",
        market_telemetry: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ScoutExtractionResult:
        """
        Extract financial facts, corporate catalysts, and contradictions from normalized evidence.
        """
        target = symbol or company_name or ticker_or_company or "ENTITY"
        financial_facts: List[FinancialFact] = []
        corporate_events: List[CorporateEvent] = []
        contradictions: List[FinancialContradiction] = []
        rumor_signals: List[Dict[str, Any]] = []

        # 1. Multi-Currency Financial Number Extraction
        # Handles $B, $M, €B, £M, ₹Crore, etc.
        num_patterns = [
            (r"\$([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?\b", "USD"),
            (r"€([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?\b", "EUR"),
            (r"£([0-9]+(?:\.[0-9]+)?)\s*(billion|million|b|m)?\b", "GBP"),
            (r"₹\s*([0-9]+(?:\.[0-9]+)?)\s*(crore|lakh)?\b", "INR"),
        ]

        extracted_deal_values: List[Tuple[float, str, str]] = []

        for idx, f in enumerate(fragments, start=1):
            text = f"{f.title} {f.snippet} {f.content}"
            text_lower = text.lower()
            ev_id = f.evidence_id or f"ev_{idx}"

            # Number parsing
            for pat, curr in num_patterns:
                for match in re.finditer(pat, text, re.IGNORECASE):
                    val_str = match.group(1)
                    mult_str = (match.group(2) or "").lower() if len(match.groups()) > 1 else ""
                    try:
                        base_val = float(val_str)
                        if mult_str in ("billion", "b"):
                            mult = 1e9
                        elif mult_str in ("million", "m"):
                            mult = 1e6
                        elif mult_str == "crore":
                            mult = 1e7
                        elif mult_str == "lakh":
                            mult = 1e5
                        else:
                            mult = 1.0

                        full_val = base_val * mult
                        financial_facts.append(
                            FinancialFact(
                                metric="Valuation / Deal / Revenue Figure",
                                value=full_val,
                                raw_str=match.group(0),
                                currency=curr,
                                evidence_ids=[ev_id],
                            )
                        )
                        if any(k in text_lower for k in ("deal", "acquisition", "acquire", "valuation", "buyout", "merger", "takeover")):
                            extracted_deal_values.append((full_val, match.group(0), ev_id))
                    except Exception:
                        pass

            # 2. Corporate Event Extraction
            if any(k in text_lower for k in ("earnings", "q1", "q2", "q3", "q4", "revenue missed", "revenue beat")):
                corporate_events.append(
                    CorporateEvent(
                        event_id=f"EVT-ERN-{idx:03d}",
                        event_type="EARNINGS",
                        summary=f.title[:150],
                        company=ticker_or_company,
                        impact_potential="HIGH",
                        evidence_ids=[ev_id],
                    )
                )
            elif any(k in text_lower for k in ("acquire", "acquisition", "merger", "buyout", "takeover")):
                corporate_events.append(
                    CorporateEvent(
                        event_id=f"EVT-MA-{idx:03d}",
                        event_type="MERGERS_ACQUISITIONS",
                        summary=f.title[:150],
                        company=ticker_or_company,
                        impact_potential="HIGH",
                        evidence_ids=[ev_id],
                    )
                )
            elif any(k in text_lower for k in ("guidance cut", "raises guidance", "outlook lowered", "profit warning")):
                corporate_events.append(
                    CorporateEvent(
                        event_id=f"EVT-GUI-{idx:03d}",
                        event_type="GUIDANCE_UPDATE",
                        summary=f.title[:150],
                        company=ticker_or_company,
                        impact_potential="HIGH",
                        evidence_ids=[ev_id],
                    )
                )
            elif any(k in text_lower for k in ("sec probe", "doj investigation", "antitrust lawsuit", "regulator")):
                corporate_events.append(
                    CorporateEvent(
                        event_id=f"EVT-REG-{idx:03d}",
                        event_type="REGULATORY",
                        summary=f.title[:150],
                        company=ticker_or_company,
                        impact_potential="HIGH",
                        evidence_ids=[ev_id],
                    )
                )

            # 3. Social Rumor Signal
            if f.platform in ("reddit", "twitter") and any(k in text_lower for k in ("unconfirmed", "rumor", "leak", "hearing that")):
                rumor_signals.append({
                    "rumor_id": f"RUM-{idx:03d}",
                    "platform": f.platform,
                    "claim": f.title[:120],
                    "evidence_ids": [ev_id],
                    "status": "UNVERIFIED",
                })

        # 4. Contradiction Detection (e.g. conflicting reported deal values)
        if len(extracted_deal_values) >= 2:
            v1, s1, e1 = extracted_deal_values[0]
            for v2, s2, e2 in extracted_deal_values[1:]:
                # If numbers diverge by more than 20%
                if e1 != e2 and abs(v1 - v2) / max(v1, v2, 1.0) > 0.20:
                    contradictions.append(
                        FinancialContradiction(
                            contradiction_id=f"CONTR-{len(contradictions)+1:02d}",
                            topic="Conflicting Reported Valuation / Deal Terms",
                            claim_a=f"Reported value: {s1}",
                            claim_b=f"Reported value: {s2}",
                            evidence_id_a=e1,
                            evidence_id_b=e2,
                            divergence_score=0.85,
                        )
                    )
                    break

        return ScoutExtractionResult(
            ticker_or_company=target,
            financial_facts=financial_facts,
            corporate_events=corporate_events,
            contradictions=contradictions,
            rumor_signals=rumor_signals,
            market_sentiment="BULLISH" if len(corporate_events) > 0 and "beat" in str(corporate_events) else "NEUTRAL",
            total_signals_analyzed=len(fragments),
        )

    # Canonical alias
    extract_market_intelligence = extract


scout_extractor = ScoutExtractionEngine()

__all__ = [
    "ScoutExtractionEngine",
    "scout_extractor",
]
