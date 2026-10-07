# SCOUT EXTRACTION SPECIFICATION
**Aegis Protocol — Agent 1: Scout Proprietary Source Acquisition Engine**
*Phase 3 Deliverable — Structured Extraction, Financial Numbers & Event Schemas*

---

## 1. Structured Metadata Extraction

Scout does not rely solely on raw HTML text stripping. The extraction layer parses metadata in hierarchical order:

1. **JSON-LD Schema (`application/ld+json`)**:
   - Extracts `@type: NewsArticle`, `Article`, `Report`, `FinancialProduct`.
   - Extracts `headline`, `description`, `articleBody`, `datePublished`, `dateModified`.
   - Extracts `author.name`, `publisher.name`, `mainEntityOfPage`.
2. **OpenGraph & Twitter Card Meta Tags**:
   - `og:title`, `og:description`, `og:url`, `og:site_name`, `og:image`.
   - `twitter:title`, `twitter:description`, `twitter:creator`, `twitter:site`.
   - `article:published_time`, `article:modified_time`, `article:author`, `article:section`.
3. **Semantic HTML5 Elements**:
   - Enforces hierarchy: `<article>`, `<h1>`, `<h2>`, `<header>`, `<time>`, `<p>`.
   - Strips non-content boilerplate: `<nav>`, `<footer>`, `<aside>`, `<script>`, `<style>`, ads, cookie notices.

---

## 2. Financial Number Extraction Specification

The `FinancialNumberExtractor` identifies and normalizes financial metrics, currencies, and magnitudes.
It never alters the raw representation, preserving both original context and normalized numerical floats.

### Supported Metric Patterns:
- **Revenue / Sales**: `revenue of $5.4B`, `sales rose to 12.3 billion`, `Q3 top-line $2.1B`.
- **Earnings & Net Income**: `net profit of ₹10,000 crore`, `adjusted net income of $450M`.
- **EPS (Earnings Per Share)**: `$1.25 EPS`, `diluted earnings per share of $0.85`.
- **Operating Margin & Growth**: `operating margin expanded 200 bps`, `gross margin 45.2%`, `revenue up 18% YoY`.
- **Guidance & Forecasts**: `raised full-year guidance to $25B-$26B`, `lowered forecast to $4.2B`.
- **Capital Expenditure (CapEx)**: `capex expected at 12B`, `capital spending $4.5B`.
- **Deal Values & Valuation**: `deal valued at $2.8B`, `market cap crossed $3T`.

### Normalization Multipliers:
- `thousand` / `k` -> $10^3$
- `million` / `M` / `m` -> $10^6$
- `billion` / `B` / `b` -> $10^9$
- `trillion` / `T` / `t` -> $10^{12}$
- `lakh` / `lac` -> $10^5$
- `crore` / `cr` -> $10^7$
- `bps` (basis points) -> $1\text{ bps} = 0.01\%$

### Schema:
```json
{
  "metric": "revenue",
  "raw_value": "$5.4B",
  "normalized_value": 5400000000.0,
  "unit": "billion",
  "currency": "USD",
  "period": "Q4",
  "direction": "POSITIVE",
  "comparison": "YoY",
  "context_sentence": "Nvidia reported record Q4 revenue of $5.4B, up 22% YoY.",
  "confidence": 0.95
}
```

---

## 3. Corporate Event Classification Specification

Scout categorizes market catalysts into formal typed corporate events:

| Event Type | Typical Trigger Keywords | Key Extracted Fields |
|---|---|---|
| `EARNINGS` | results, revenue, net profit, EPS, quarterly release | metric, reported_value, expected_value, period |
| `GUIDANCE_CHANGE` | raised guidance, lowered forecast, revised outlook | old_guidance, new_guidance, direction |
| `M_AND_A` | acquisition, merger, buyout, takeover, talks, deal | acquirer, target, deal_value, regulatory_status |
| `PRODUCT_LAUNCH` | unveiled, launched, announced, released, introduced | product_name, category, commercial_availability |
| `PARTNERSHIP` | partnership, collaboration, alliance, agreement, pact | partner_entities, scope, duration |
| `CAPEX_CHANGE` | capex, capital expenditure, factory, foundry, fab | amount, facility_location, timeline |
| `LAYOFF` | workforce reduction, layoffs, job cuts, headcount | headcount_affected, percentage, restructuring_charge |
| `REGULATORY_ACTION` | probe, investigation, antitrust, penalty, fine, subpoena | regulator, allegation, sanction_amount |
| `LEGAL_ACTION` | lawsuit, sued, litigation, patent infringement, injunction | plaintiff, defendant, jurisdiction, claims |
| `MANAGEMENT_CHANGE` | CEO, CFO, stepped down, resigned, appointed, successor | executive_name, role, previous_role, effective_date |
| `SUPPLY_DISRUPTION` | shortage, delay, fire, strike, halt, embargo, ban | affected_component, estimated_delay, alternatives |
| `FINANCING` | debt offering, bond issuance, equity dilution, credit facility | amount, interest_rate, maturity_date |
| `MACRO_RELEASE` | CPI, inflation, interest rate, Fed decision, GDP | indicator, actual_value, forecast_value |

---

## 4. Temporal Disambiguation: Event Time vs. Publication Time

Trading intelligence demands knowing **when an event happened** versus **when it was reported**.
Confusing these leads to trading on already-digested news.

- **`published_at`**: The ISO 8601 timestamp when the web page, article, or post was indexed/published online.
  *Sources*: `article:published_time`, `datePublished` (JSON-LD), HTTP `Last-Modified`, RSS `<pubDate>`.
- **`event_at`**: The ISO 8601 timestamp when the underlying corporate action or disclosure occurred.
  *Sources*: Extracted from filing submission headers, explicit timestamps in press release datelines (e.g., `"SANTA CLARA, Calif. — Feb 21, 2026, 4:05 PM ET"`), earnings call times.
- **`retrieved_at`**: The ISO 8601 timestamp when Scout performed the acquisition.
