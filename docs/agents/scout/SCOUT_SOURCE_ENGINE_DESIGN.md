# SCOUT SOURCE ENGINE DESIGN SPECIFICATION
**Aegis Protocol — Agent 1: Scout Proprietary Source Acquisition Engine**
*Phase 2 Deliverable — System Architecture & Component Design*

---

## 1. Architectural Role & Boundary

In the Aegis Protocol, **Scout is Agent 1 — the Trading & News Intelligence Agent**.
Scout is **NOT** a generic web crawler, search wrapper, or verification judge.
Scout's role is intelligence:
```text
Discover market catalysts & price anomalies
        ↓
Understand corporate & market events
        ↓
Determine affected companies, tickers, and sectors
        ↓
Assess novelty, relevance, credibility, and market significance
        ↓
Synthesize actionable financial intelligence
```

To fulfill this mission, Scout requires its own **proprietary source acquisition engine**: `ScoutSourceEngine`.
The engine operates underneath Scout as a dedicated, high-performance evidence acquisition and structured extraction infrastructure layer.

```text
┌────────────────────────────────────────────────────────┐
│                      SCOUT AGENT                       │
│        (Trading & News Intelligence Orchestrator)      │
│  • Market Anomaly Analysis  • Volatility Forecasting   │
│  • Catalyst Synthesis       • Risk & Narrative Model   │
└───────────────────────────┬────────────────────────────┘
                            │
               ScoutSourceRequest / ScoutEvidence
                            │
┌───────────────────────────▼────────────────────────────┐
│                  SCOUT SOURCE ENGINE                   │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 1. Discovery Engine (Multi-Strategy, Expansion)   │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ 2. Candidate Manager & Hard Rejection Gates       │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ 3. Adaptive Acquisition Cascade (Native/Mirrors)   │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ 4. Structured Extraction (Metadata, Numbers, Time) │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ 5. Deduplication & Story Clustering (Wire Synd.)   │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ 6. Corroboration & Contradiction Detection         │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ 7. Quality Ranking, Evidence Normalization & Audit │ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

---

## 2. Core Design Principles

1. **Search Results are Candidates, NOT Evidence**:
   A search hit is never directly trusted as fact. It must undergo candidate validation, full-content acquisition, structured extraction, and semantic verification.
2. **Task-Aware & Event-Aware Retrieval**:
   Scout adjusts its discovery strategies and source tiers based on the event type (`EARNINGS`, `M_AND_A`, `REGULATORY_ACTION`, `SUPPLY_CHAIN_DISRUPTION`, `MACRO_EVENT`).
3. **Structured Financial Facts, Not Just Text**:
   The engine extracts normalized numerical values, currencies, units, metrics, directions, and periods (e.g. `revenue: 5.4 billion USD, Q4, raised guidance`).
4. **Temporal Disambiguation**:
   Strict separation between `published_at` (when an article was published) and `event_at` (when the corporate action took place).
5. **Wire Syndication & Duplicate Clustering**:
   Republished copies of AP, Reuters, or PR Newswire articles are clustered into a single story with 1 primary publisher and explicit syndicated echoes.
6. **Corroboration & Contradiction**:
   Conflicting figures (e.g. deal size $2B vs $3B) trigger `conflicting_information = True` and preserve both sources rather than averaging them.
7. **Rumor vs. Confirmed Status**:
   Strict epistemic labeling (`OFFICIAL`, `CONFIRMED`, `REPORTED`, `UNCONFIRMED_RUMOR`, `CONTRADICTED`, `RETRACTED`).
8. **Zero-Auth Default**:
   Public data only. No user credentials, cookies, CAPTCHA circumventions, or authentication bypasses.
9. **Maximum Information Quality per Network Request**:
   Connection reuse, bounded concurrency, polite token-bucket pacing, deduplication, and early rejection gates prevent unnecessary network calls.

---

## 3. Detailed Engine Pipeline

### Stage 1: Discovery Engine
- **Purpose**: Identify candidate sources across multiple independent discovery routes.
- **Strategies**:
  - `BingDiscovery`: Web and news search queries.
  - `YahooDiscovery`: Financial news index queries.
  - `CompanyIRDiscovery`: Direct company investor relations disclosure search.
  - `SECDiscovery`: Regulatory filing and official disclosure search.
  - `SocialDiscovery`: Public social discussions (Reddit via Arctic Shift, X via FxTwitter).
  - `QueryExpansionDiscovery`: Entity ticker variations, CEO/executive names, and sector synonyms.
- **Pacing & Pool**: Token-bucket rate limiter enforcing 0.5s–0.75s intervals between search engine requests with shared session pooling.

### Stage 2: Hard Gate Candidate Validation
- **Purpose**: Discard irrelevant, malicious, or malformed candidate URLs before any expensive content fetch.
- **Gates**:
  1. `SSRFGate`: Blocks private IPs, loopback, metadata services (AWS 169.254.169.254), non-http(s) schemes.
  2. `PlatformScopeGate`: Ensures Reddit candidates belong to requested subreddits (e.g. `r/investing` vs `r/privacy`).
  3. `URLStructureGate`: Enforces `/comments/<id>` for Reddit and `/status/<id>` for X. Rejects login, search, settings, and homepages.
  4. `AntiTokenCheatGate`: Enforces multi-token disambiguation (e.g., rejecting "Satya" incense for "Satya Nadella", "Sam" in LOTR for "Sam Altman").
  5. `DomainIntegrityGate`: Rejects corporate homepages when social evidence is required, and vice versa.

### Stage 3: Adaptive Acquisition Cascade
- **Purpose**: Fetch the best available version of content using the cheapest reliable mechanism.
- **Cascade Order**:
  1. *Native / Direct REST API* (Official filings, public APIs).
  2. *Zero-Auth Public Mirror* (Arctic Shift for Reddit, FxTwitter for X).
  3. *Direct HTTP Extraction* (Persistent `requests`/`httpx` session with browser headers).
  4. *Scrapling DOM Parser* (Structured HTML parsing with anti-bot resistance).
  5. *Jina Reader Markdown* (`r.jina.ai/<url>` only when direct DOM parsing is insufficient or JS-heavy).
  6. *Playwright Dynamic Rendering* (Restricted fallback for heavy client-side applications).
  7. *Syndication / Search Snippet Fallback* (When full source is deleted or blocked).
  8. *Reject* (`CONTENT_UNAVAILABLE` or `RATE_LIMITED`).

### Stage 4: Structured Content & Financial Extraction
- **Purpose**: Transform raw HTML/JSON into structured, typed financial evidence.
- **Sub-Extractors**:
  - `StructuredMetadataExtractor`: Parses JSON-LD, OpenGraph, Twitter Cards, schema.org, and meta tags.
  - `FinancialNumberExtractor`: Extracts regex-backed numerical facts: values, currencies (`USD`, `INR`, `EUR`, `GBP`), units (`billion`, `crore`, `million`, `bps`, `%`), metrics (`revenue`, `ebitda`, `eps`, `margin`, `guidance`, `capex`), and periods (`Q1`, `Q2`, `Q3`, `Q4`, `FY25`).
  - `CorporateEventExtractor`: Classifies events into typed enums (`EARNINGS`, `GUIDANCE_CHANGE`, `M_AND_A`, `PRODUCT_LAUNCH`, `PARTNERSHIP`, `CAPEX_CHANGE`, `LAYOFF`, `REGULATORY_ACTION`, `LEGAL_ACTION`, `MANAGEMENT_CHANGE`, `SUPPLY_DISRUPTION`).
  - `TemporalExtractor`: Extracts both `published_at` (article publication) and `event_at` (real-world event occurrence).
  - `ContentExtractor`: Extracts clean body text, headings, author bylines, and publishing organizations.

### Stage 5: Deduplication & Story Clustering
- **Purpose**: Prevent duplicate syndicated reporting from masquerading as multiple independent corroborations.
- **Techniques**:
  - Canonical URL normalization (stripping tracking parameters, UTM codes, session IDs).
  - Content hashing (SimHash / normalized token overlap).
  - Wire syndication detection (matching AP, Reuters, Bloomberg, PR Newswire signatures).
  - Groups identical reports into a `StoryCluster` with 1 canonical primary source and linked syndicated echoes.

### Stage 6: Corroboration & Contradiction Detection
- **Purpose**: Evaluate truthfulness and identify disagreements across independent sources.
- **Logic**:
  - Tracks `independent_source_count` (distinct publishers excluding syndications).
  - Verifies `primary_source_present` (presence of SEC filings, company press releases, official announcements).
  - Flags `conflicting_information`: Compares financial facts across sources. If values for the same metric/period disagree, creates an explicit `ContradictionRecord`.
  - Determines `epistemic_status`:
    - `OFFICIAL`: Directly corroborated by primary source.
    - `CONFIRMED`: Corroborated by 2+ independent Tier 2 publishers.
    - `REPORTED`: Reported by 1 reputable publisher without secondary corroboration.
    - `UNCONFIRMED_RUMOR`: Sourced only from social media or anonymous claims.
    - `CONTRADICTED`: Conflicting reports exist across sources.

### Stage 7: Ranking, Normalization & Provenance
- **Purpose**: Package validated evidence into canonical `EvidenceFragment` and `ScoutEvidence` structures.
- **Scoring**: Multi-axis tensor (`source_tier_weight`, `relevance_score`, `freshness_score`, `independence_score`, `primary_weight`).
- **Telemetry**: Records full audit trail: requested channel, actual channel, retrieval mode, backend adapter, latency, bytes retrieved, and status codes.

---

## 4. Component Structure & Modular Hierarchy

```text
backend/services/agent_reach/scout/
├── __init__.py               # Public API exports
├── models.py                 # Strongly typed Pydantic & dataclass contracts
├── transport.py              # Connection pool, rate limiter, SSRF validator
├── discovery.py              # Modular discovery strategies & candidate manager
├── adapters/                 # Source-specific acquisition adapters
│   ├── __init__.py
│   ├── base.py               # ScoutSourceAdapter abstract base class
│   ├── web_adapter.py        # Generic web & financial news adapter
│   ├── reddit_adapter.py     # Arctic Shift Reddit adapter
│   ├── x_adapter.py          # FxTwitter X/Twitter adapter
│   ├── youtube_adapter.py    # yt-dlp & video metadata adapter
│   ├── github_adapter.py     # GitHub REST repository & issue adapter
│   └── primary_adapter.py    # SEC / Company IR filing adapter
├── extraction/               # Structured extraction engine
│   ├── __init__.py
│   ├── metadata.py           # JSON-LD, OpenGraph, schema.org extractor
│   ├── financial.py          # Financial number, currency & metric extractor
│   ├── events.py             # Corporate event classifier & direction extractor
│   └── temporal.py           # Event time vs publication time extractor
├── deduplication.py          # Canonicalization, hashing & syndication clustering
├── corroboration.py          # Story clustering & contradiction detector
├── ranking.py                # Hard gates & candidate quality tensor ranker
├── cache.py                  # Bounded TTL cache with freshness tiers
├── telemetry.py              # Provenance ledger & execution metrics
└── engine.py                 # ScoutSourceEngine master coordinator
```

---

## 5. Summary of Key Differences from Legacy Scraper

| Feature | Legacy Scraper | Scout Source Engine |
|---|---|---|
| **Role** | Monolithic utility function | Dedicated trading & news intelligence engine |
| **Search Selection** | Top-1 result blindly accepted | Top-5/10 candidates ranked semantically |
| **Extraction** | Raw `get_text()` string dump | JSON-LD, financial facts, metrics, and events |
| **Financial Numbers** | Unparsed text | Normalized value, currency, unit, and period |
| **Timestamps** | Only publication timestamp | Explicit `published_at` vs. `event_at` |
| **Syndication** | Counts 20 AP echoes as 20 sources | Clusters echoes into 1 story with 1 primary |
| **Contradictions** | Ignored or overwritten | Explicitly recorded and preserved |
| **Rumor vs Fact** | All items treated identically | Epistemic states (`OFFICIAL`, `RUMOR`, etc.) |
| **Provenance** | Basic channel name | Full lineage, tier, mode, and audit trace |

Proceeding to **Phase 3**: Data contracts, source policies, extraction specifications, and failure models.
