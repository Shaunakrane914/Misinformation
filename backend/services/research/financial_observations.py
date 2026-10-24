"""Conservative financial prose observations. Ambiguous tables abstain.

Never infer a period from a year alone, compare currencies, or pick a table
column without a unique header. Every value retains its exact source span.
"""
from datetime import datetime
from decimal import Decimal
import re


def financial_observations(text, evidence_id):
    period_matches = list(re.finditer(r"quarter ended\s+([A-Z][a-z]+\s+\d{1,2},?\s+20\d\d)", text))
    periods = set()
    for match in period_matches:
        try:
            periods.add(datetime.strptime(match.group(1).replace(",", ""), "%B %d %Y").date().isoformat())
        except ValueError:
            pass
    amount = r"(?P<currency>US\$|USD|INR|EUR|GBP|\$|₹|€|£)?\s*(?P<value>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>million|billion|crore|%)?"
    patterns = [
        ("REVENUE", r"revenues?\s+(?:at|of|was|were|totalled|totaled)\s*" + amount),
        ("REVENUE", r"(?:delivered|reported)\s+" + amount + r"\s+in\s+Q[1-4]\s+revenues?"),
        ("OPERATING_MARGIN", r"operating\s+margin\s+(?:was\s+)?(?:at|of)\s*" + amount),
        ("EPS", r"(?:basic\s+)?EPS\s+(?:at|of)\s*" + amount),
        ("FREE_CASH_FLOW", r"(?:FCF|free cash flow)\s+(?:at|of)\s*" + amount),
    ]
    result, seen = [], set()
    for metric, pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            key = (metric, match.start("value"), match.end("value"))
            if key in seen:
                continue
            seen.add(key)
            observed_currency = (match.group("currency") or "").upper()
            # A dollar glyph is shared by multiple national currencies. Do not
            # silently turn it into USD, including when another amount in the
            # document is explicitly denominated in USD.
            currency = {"$": "DOLLAR_SYMBOL_UNSPECIFIED", "US$": "USD", "₹": "INR",
                        "€": "EUR", "£": "GBP"}.get(observed_currency, observed_currency) or None
            unit = (match.group("unit") or "").lower()
            # Revenue share/growth percentages are not monetary revenue amounts.
            if metric == "REVENUE" and unit == "%":
                continue
            if not currency and unit != "%":
                continue
            value = Decimal(match.group("value").replace(",", ""))
            multiplier = {"million": Decimal(10**6), "billion": Decimal(10**9), "crore": Decimal(10**7)}.get(unit, Decimal(1))
            pages = re.findall(r"\[PDF page (\d+)\]", text[:match.start()])
            headers = list(re.finditer(r"Guidance for[^\n]*|Key highlights:|For the quarter ended[^\n]*", text[:match.start()], re.I))
            guidance = bool(headers and headers[-1].group().lower().startswith("guidance for"))
            range_match = re.match(r"\s*[-–]\s*(\d+(?:\.\d+)?)%?", text[match.end():])
            result.append({"evidence_id": evidence_id, "metric": metric, "value": str(value),
                "unit": "percent" if unit == "%" else unit or "currency_unit", "currency": currency,
                "normalized_value": str(value * multiplier), "period_end": next(iter(periods)) if len(periods) == 1 and not guidance else None,
                "period_alignment": "UNIQUE_DOCUMENT_QUARTER" if len(periods) == 1 and not guidance else "AMBIGUOUS_OR_UNKNOWN",
                "scope": "GUIDANCE" if guidance else "REPORTED_SOURCE_PROSE", "range_upper": range_match.group(1) if range_match else None,
                "source_page": int(pages[-1]) if pages else None, "start": match.start(), "end": match.end(),
                "text": match.group(), "status": "OBSERVED_SOURCE_ASSERTION", "table_alignment_verified": False})
    return result[:24]


def compare_financial_observations(claim_text, observations):
    """Compare only explicitly typed prose measurements, never overall truth.

    Different periods/currencies, negation, missing headers and conflicting
    values abstain. A match means agreement with captured source assertions.
    """
    claims = financial_observations(claim_text, "claim")
    result = []
    for claim in claims:
        currencies = {"USD", "INR", "EUR", "GBP"}
        compatible = [o for o in observations if o.get("metric") == claim["metric"] and o.get("scope") != "GUIDANCE"
                      and claim["period_end"] and o.get("period_end") == claim["period_end"]
                      and o.get("currency") == claim["currency"]
                      and ((o.get("currency") in currencies and claim["currency"] in currencies)
                           or (o.get("unit") == claim["unit"] == "percent"))
                      and not o.get("range_upper")]
        # Compare monetary magnitude, not spelling/scale (5.082 billion and
        # 5,082 million). Never perform an exchange-rate conversion.
        values = {Decimal(o["normalized_value"]) for o in compatible}
        status = "INSUFFICIENT_COMPARABLE_CONTEXT"
        if len(values) == 1 and not re.search(r"\bnot\b|\bnever\b|\bdenied\b", claim_text, re.I):
            status = ("MATCHES_SOURCE_ASSERTION" if Decimal(claim["normalized_value"]) in values
                      else "DISAGREES_WITH_SOURCE_ASSERTION")
        result.append({"claim_metric": claim["metric"], "status": status,
                       "source_evidence_ids": list(dict.fromkeys(o["evidence_id"] for o in compatible)),
                       "independent_verification": False})
    return result
