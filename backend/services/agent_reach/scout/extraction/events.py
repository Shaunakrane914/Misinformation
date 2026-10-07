"""
Aegis Protocol — Scout Corporate Event Extractor
=================================================
Identifies and categorizes corporate market catalysts into typed CorporateEvent instances.
"""

from typing import List, Optional
from backend.services.agent_reach.scout.models import CorporateEvent, CorporateEventType, FactDirection


class CorporateEventExtractor:
    """
    Extracts structured CorporateEvent instances from text.
    Preserves raw event description, interpreted direction, confidence, and target company.
    """

    EVENT_TRIGGERS = [
        (CorporateEventType.GUIDANCE_CHANGE, [
            r"guidance\s+(?:raise|cut|hike|boost)",
            r"(?:raised|lowered|boosted|cut|revised|updated)\s+(?:[\w-]+\s+)?guidance",
            r"(?:revised|updated|lowered|raised)\s+forecast",
            r"outlook\s+updated"
        ]),
        (CorporateEventType.EARNINGS, [
            r"earnings\s+report", r"quarterly\s+results", r"q[1-4]\s+results",
            r"net\s+profit\s+reported", r"financial\s+results"
        ]),
        (CorporateEventType.M_AND_A, [
            r"to\s+acquire", r"acquisition\s+of", r"merger\s+agreement",
            r"agreed\s+to\s+buy", r"buyout", r"takeover\s+bid"
        ]),
        (CorporateEventType.PRODUCT_LAUNCH, [
            r"unveiled\s+(?:new\s+)?", r"launched\s+(?:new\s+)?",
            r"announced\s+launch\s+of", r"releases\s+new\s+product"
        ]),
        (CorporateEventType.PARTNERSHIP, [
            r"strategic\s+partnership", r"multi-year\s+agreement",
            r"signs\s+pact", r"collaboration\s+with"
        ]),
        (CorporateEventType.CAPEX_CHANGE, [
            r"plans?\s+capex", r"capital\s+expenditure\s+plan",
            r"new\s+fab", r"semiconductor\s+foundry", r"factory\s+expansion"
        ]),
        (CorporateEventType.LAYOFF, [
            r"workforce\s+reduction", r"layoffs?", r"cutting\s+jobs",
            r"lay\s+off", r"headcount\s+reduction"
        ]),
        (CorporateEventType.REGULATORY_ACTION, [
            r"antitrust\s+probe", r"investigation\s+into", r"sec\s+investigation",
            r"doj\s+probe", r"regulator\s+fine", r"subpoena"
        ]),
        (CorporateEventType.LEGAL_ACTION, [
            r"lawsuit\s+filed", r"sued\s+by", r"patent\s+infringement", r"class\s+action"
        ]),
        (CorporateEventType.MANAGEMENT_CHANGE, [
            r"named\s+new\s+ceo", r"ceo\s+stepped\s+down", r"resigned\s+as\s+cfo",
            r"appointed\s+president"
        ]),
        (CorporateEventType.SUPPLY_DISRUPTION, [
            r"supply\s+shortage", r"factory\s+fire", r"shipping\s+halt",
            r"export\s+ban", r"trade\s+restriction"
        ]),
        (CorporateEventType.FINANCING, [
            r"debt\s+offering", r"bond\s+sale", r"credit\s+facility", r"equity\s+dilution"
        ]),
        (CorporateEventType.MACRO_RELEASE, [
            r"interest\s+rate\s+decision", r"inflation\s+rate", r"cpi\s+report", r"central\s+bank"
        ]),
    ]

    def extract_events(self, text: str, company_name: str = "", ticker: str = "") -> List[CorporateEvent]:
        import re
        events: List[CorporateEvent] = []
        if not text:
            return events

        t_lower = text.lower()

        for ev_type, patterns in self.EVENT_TRIGGERS:
            matched_trigger = None
            for pat in patterns:
                m = re.search(pat, t_lower)
                if m:
                    matched_trigger = m.group(0)
                    break

            if matched_trigger:
                direction = FactDirection.NEUTRAL
                if any(w in matched_trigger for w in ("raise", "boost", "unveiled", "launched", "partnership", "expansion")):
                    direction = FactDirection.POSITIVE
                elif any(w in matched_trigger for w in ("cut", "layoff", "probe", "investigation", "sued", "shortage", "halt")):
                    direction = FactDirection.NEGATIVE

                events.append(CorporateEvent(
                    event_type=ev_type,
                    company=company_name or "Target Entity",
                    ticker=ticker or "",
                    direction=direction,
                    description=f"Corporate event '{ev_type.value}' detected via trigger: '{matched_trigger}'",
                    confidence=0.88
                ))

        return events


corporate_event_extractor = CorporateEventExtractor()
