"""
Aegis Protocol — Scout Financial Number Extractor
=================================================
Identifies and normalizes financial numbers, metrics, currencies, units,
and directions from unformatted text without ever distorting original values.
"""

import re
from typing import List, Optional
from backend.agents.scout.sources.models import FactDirection, FinancialFact


class FinancialNumberExtractor:
    """
    Extracts structured FinancialFact instances from news and filing text.
    Handles USD ($), INR (₹/Rs), EUR (€), GBP (£), units (B, M, crore, lakh, bps, %),
    and metric associations (revenue, EPS, margin, guidance, capex).
    """

    # Multipliers
    MULTIPLIERS = {
        "k": 1_000.0,
        "thousand": 1_000.0,
        "m": 1_000_000.0,
        "million": 1_000_000.0,
        "b": 1_000_000_000.0,
        "bn": 1_000_000_000.0,
        "billion": 1_000_000_000.0,
        "t": 1_000_000_000_000.0,
        "trillion": 1_000_000_000_000.0,
        "lakh": 100_000.0,
        "lac": 100_000.0,
        "crore": 10_000_000.0,
        "cr": 10_000_000.0,
    }

    # Currencies
    CURRENCY_SYMBOLS = {
        "$": "USD",
        "usd": "USD",
        "₹": "INR",
        "rs": "INR",
        "inr": "INR",
        "€": "EUR",
        "eur": "EUR",
        "£": "GBP",
        "gbp": "GBP",
    }

    def extract_from_text(self, text: str, source_url: str = "") -> List[FinancialFact]:
        """Alias for compatibility with shared scout extraction pipeline."""
        return self.extract_facts(text)

    def extract_facts(self, text: str) -> List[FinancialFact]:
        facts: List[FinancialFact] = []
        if not text:
            return facts

        # Split into sentence-like chunks
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for sent in sentences:
            if len(sent) < 10:
                continue
            s_lower = sent.lower()

            # 1. Regex for Currency + Number + Unit (e.g., $5.4B, $10.5 billion, ₹10,000 crore)
            pattern_curr_num = re.finditer(
                r"([\$₹€£]|rs\.?|usd|inr|eur|gbp)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(b|bn|billion|m|million|k|thousand|t|trillion|crore|cr|lakh|lac|bps|%)?",
                s_lower
            )

            for match in pattern_curr_num:
                raw_curr, raw_digits, raw_unit = match.groups()
                if not raw_digits:
                    continue

                clean_digits = raw_digits.replace(",", "")
                try:
                    num_val = float(clean_digits)
                except ValueError:
                    continue

                # Filter out trivial bare numbers (like single years 2024, 2025 unless marked with units)
                if not raw_curr and not raw_unit:
                    continue
                if not raw_curr and raw_unit is None and (1900 <= num_val <= 2100):
                    continue

                currency = "NONE"
                if raw_curr:
                    currency = self.CURRENCY_SYMBOLS.get(raw_curr.strip("."), "USD")

                unit = raw_unit.lower() if raw_unit else ("dollars" if currency == "USD" else "units")
                multiplier = self.MULTIPLIERS.get(unit, 1.0)
                norm_val = num_val * multiplier if unit != "%" and unit != "bps" else num_val

                # Determine metric from sentence context
                metric = self._infer_metric(s_lower)
                direction = self._infer_direction(s_lower)
                period = self._infer_period(s_lower)

                raw_fact_repr = match.group(0).strip()
                facts.append(FinancialFact(
                    metric=metric,
                    raw_value=raw_fact_repr,
                    normalized_value=norm_val,
                    unit=unit,
                    currency=currency,
                    period=period,
                    direction=direction,
                    context_sentence=sent.strip()[:200],
                    confidence=0.90 if metric != "general_financial" else 0.70
                ))

        return facts[:15]  # bound facts per source

    def _infer_metric(self, s: str) -> str:
        if "revenue" in s or "sales" in s or "top-line" in s or "turnover" in s:
            return "revenue"
        if "eps" in s or "earnings per share" in s:
            return "eps"
        if "net profit" in s or "net income" in s or "bottom-line" in s:
            return "net_income"
        if "ebitda" in s:
            return "ebitda"
        if "operating margin" in s or "gross margin" in s or "margin" in s:
            return "margin"
        if "guidance" in s or "forecast" in s or "outlook" in s:
            return "guidance"
        if "capex" in s or "capital expenditure" in s or "capital spending" in s:
            return "capex"
        if "deal" in s or "acquisition" in s or "valuation" in s:
            return "deal_value"
        return "general_financial"

    def _infer_direction(self, s: str) -> FactDirection:
        pos_words = ["rose", "jumped", "surged", "expanded", "raised", "exceeded", "beat", "positive", "record", "growth"]
        neg_words = ["dropped", "slumped", "fell", "cut", "lowered", "missed", "negative", "loss", "decline", "contracted"]
        if any(w in s for w in pos_words):
            return FactDirection.POSITIVE
        if any(w in s for w in neg_words):
            return FactDirection.NEGATIVE
        return FactDirection.NEUTRAL

    def _infer_period(self, s: str) -> Optional[str]:
        p_match = re.search(r"\b(q[1-4]|fy\d{2,4}|full-year|half-year|first-quarter|fourth-quarter)\b", s)
        return p_match.group(1).upper() if p_match else None


financial_number_extractor = FinancialNumberExtractor()
