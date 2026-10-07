# SCOUT EVENT MODEL SPECIFICATION
**Aegis Protocol — Agent 1: Scout Proprietary Source Acquisition Engine**
*Event Taxonomy, Financial Facts, Epistemic States & Contradiction Detection*

---

## 1. Corporate & Market Event Taxonomy

Scout constructs typed market events with company affiliation, tickers, timestamps, old/new values, and direction:

```python
from enum import Enum


class CorporateEventType(str, Enum):
    EARNINGS = "EARNINGS"
    GUIDANCE_CHANGE = "GUIDANCE_CHANGE"
    M_AND_A = "M_AND_A"
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"
    PARTNERSHIP = "PARTNERSHIP"
    CONTRACT = "CONTRACT"
    CAPEX_CHANGE = "CAPEX_CHANGE"
    SUPPLY_DISRUPTION = "SUPPLY_DISRUPTION"
    PRICE_CHANGE = "PRICE_CHANGE"
    REGULATORY_ACTION = "REGULATORY_ACTION"
    LEGAL_ACTION = "LEGAL_ACTION"
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"
    LAYOFF = "LAYOFF"
    FINANCING = "FINANCING"
    MACRO_RELEASE = "MACRO_RELEASE"
    GEOPOLITICAL_EVENT = "GEOPOLITICAL_EVENT"
    OTHER = "OTHER"
```

---

## 2. Epistemic Classification (Rumor vs. Confirmed)

A core rule of trading intelligence: **Never turn a rumor into a confirmed fact.**

| Epistemic State | Definition | Required Evidence |
|---|---|---|
| `UNCONFIRMED` | Rumor, anonymous leak, or single social post | Social commentary, "sources say", unverified leak |
| `REPORTED` | Reputable news publication reported the story | 1 reputable Tier 2 financial press outlet |
| `MULTIPLE_SOURCES` | Multiple independent outlets report without primary confirmation | 2+ independent reporting outlets |
| `OFFICIAL` | Disclosed directly by company IR or regulator | Primary Tier 1 disclosure (SEC 8-K, exchange notice, IR) |
| `CONFIRMED` | Corroborated by primary filing or 2+ Tier 2 outlets with named sources | Official filing or multiple verified press releases |
| `CONTRADICTED` | Outlets report conflicting facts or explicit denials exist | Source A reports deal valued at $2B; Source B says $3B |
| `RETRACTED` | Outlet or primary source issued formal correction/retraction | Retraction notice issued |

---

## 3. Financial Fact Normalization

Preserves both raw text representation and normalized numerical value:

```json
{
  "metric": "guidance",
  "raw_value": "$5.5B",
  "normalized_value": 5500000000.0,
  "unit": "billion",
  "currency": "USD",
  "period": "FY26",
  "direction": "POSITIVE",
  "comparison": "vs_consensus",
  "context_sentence": "Management raised full-year revenue guidance to $5.5B, above Street estimates.",
  "confidence": 0.94
}
```

---

## 4. Contradiction Detection Rule

When sources present conflicting numerical values or statements (e.g., deal size $2B vs $3B):
1. **Never perform destructive averaging**: Do NOT merge $2B and $3B into $2.5B.
2. **Flag Explicit Contradiction**:
   ```json
   {
     "contradiction": true,
     "metric": "deal_value",
     "sources": [
       {"url": "https://sourceA.com", "value": "$2.0B"},
       {"url": "https://sourceB.com", "value": "$3.0B"}
     ],
     "epistemic_status": "CONTRADICTED"
   }
   ```
3. Preserve both raw records in the evidence ledger so downstream agents can evaluate which source is more authoritative.
