# Aegis Protocol — System Architecture & Multi-Agent Fabric

This document details the architectural topology, progressive disclosure information framework, and inter-agent coordination model of the Aegis Protocol.

---

## 1. High-Level Architecture Overview

Aegis Protocol is designed as an intelligence fabric composed of specialized autonomous agents coordinated over modular REST endpoints, zero-cost public telemetry scrapers, and physics-based threat instruments.

```
                      ┌────────────────────────────────────────┐
                      │    Human Analyst / Web Consoles       │
                      │  (Level 1 -> Level 2 -> Level 3 UI)    │
                      └──────────────────┬─────────────────────┘
                                         │ HTTP / JSON
                                         ▼
                      ┌────────────────────────────────────────┐
                      │          FastAPI Gateway               │
                      │       (/api/claims, /api/agents)       │
                      └──────────┬──────────────────┬──────────┘
                                 │                  │
               ┌─────────────────┴─────┐      ┌─────┴─────────────────┐
               ▼                       ▼      ▼                       ▼
      ┌──────────────────┐  ┌───────────────┐ ┌───────────────┐  ┌──────────────────┐
      │   Domain Sentinels│  │ Truth Tribunal│ │ Physics Lab   │  │   Agent Reach    │
      │                  │  │               │ │               │  │ Capability Layer │
      │ • Scout 2.0      │  │ • Ingestion   │ │ • Mandelbrot  │  │ • 14 Adapters    │
      │ • Trending 2.0   │  │ • Research    │ │ • Hawkes Proc │  │ • RSS Wires      │
      │ • BrandShield 2.0│  │ • Investigator│ │ • Byzantine   │  │ • Syndication    │
      │ • Personal Watch │  │               │ │   Quorum      │  │ • Dedup & Normal │
      └──────────────────┘  └───────────────┘ └───────────────┘  └──────────────────┘
```

---

## 2. Autonomous Sentinel Fleet

| Sentinel Node | Primary Responsibility | Monitored Vectors | Console |
| :--- | :--- | :--- | :--- |
| **Scout Agent 2.0** | Financial volatility, price anomalies, leak correlation | Yahoo Finance, Reddit (r/stocks, r/wsb), SEC EDGAR, X Cashtags | [`scout-agent.html`](../frontend/scout-agent.html) |
| **Trending Agent 2.0** | Viral velocity, topic discovery, narrative emergence | Multi-platform RSS, PullPush Reddit, News wires, TikTok | [`trending-agent.html`](../frontend/trending-agent.html) |
| **BrandShield Agent 2.0** | Counterfeit listings, review brigading, smear PR | Amazon/Flipkart storefronts, Trustpilot, consumer forums | [`brandshield-agent.html`](../frontend/brandshield-agent.html) |
| **Personal Watch 2.0** | Identity monitoring, deepfakes, smear campaigns | Public OSINT footprint, acoustic spectrograms, news wires | [`personal-watch-agent.html`](../frontend/personal-watch-agent.html) |
| **Claim Fact-Check** | Dual-column empirical verification (FOR vs. AGAINST) | Wire registries (AP, Reuters), official government gazettes | [`submit.html`](../frontend/submit.html) |
| **Research Agent** | Intelligence workspace clustering findings with sources | SEC filings, Jina Reader, investigative archives | [`research-agent.html`](../frontend/research-agent.html) |
| **Investigator Agent** | Forensic case dossiers, chain of custody, gap analysis | Provenance tracking, source dependency graphs | [`investigator-agent.html`](../frontend/investigator-agent.html) |

---

## 3. Human-Centered 3-Tier Progressive Disclosure

Every user-facing interface adheres to strict information stratification:

1. **Level 1 — Decision / Orientation (Above the fold):**
   * Framed by a primary investigative question banner (`.aegis-orientation-banner`).
   * Comprehension within 5–10 seconds.
   * Renders only statement identity, definitive verdict badge, qualitative evidence strength (`Strong`, `Moderate`, `Limited`, `Insufficient`), and a 1–3 sentence bottom-line summary.
2. **Level 2 — Investigation:**
   * Bulleted "Why" findings (2–4 concise empirical points).
   * Dual-column evidence matrix comparing supporting citations directly against refuting citations.
   * Clustered event reporting (`.aegis-event-group`) that unifies multiple articles about the same real-world event.
   * Explicit disclosures of unresolved factors and unknown gaps (`.aegis-unknown-box`).
3. **Level 3 — Raw Evidence & Provenance:**
   * Collapsed-by-default evidence rows (`.aegis-evidence-row`).
   * Clicking expands excerpt quotes, publisher roles (`PRIMARY`, `SECONDARY`, `FACT-CHECK`), and independent syndication group IDs (`G-01`, `G-02`).
   * First-class, verified `Open source ↗` links opening in external tabs with zero `#` placeholders.

---

## 4. Agent Reach Capability Layer

The retrieval subsystem operates without requiring expensive third-party search API keys:
* **Zero-Cost Telemetry:** Ingests public RSS feeds, SEC EDGAR registries, and syndicated wires.
* **Content Normalization:** Applies Unicode NFC normalization, whitespace collapsing, and SHA-256 deduplication.
* **Syndication Clustering:** Detects echo-chamber propagation by grouping articles with identical phrasing or shared wire origins.
* **Security Hardening:** Enforces strict SSRF protection, rejecting internal network IP ranges (`127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`, `169.254.169.254`) and non-HTTP protocols.

---

## 5. Relational Database Schema & Data Dictionary (SQL Specification)

Aegis Protocol implements a dual-engine persistence layer:
1. **Production Engine (PostgreSQL / Supabase):** High-throughput, ACID-compliant cloud storage with native JSONB indexing, pgcrypto UUID generation, and real-time CDC (Change Data Capture).
2. **Local & Air-Gapped Engine (SQLite):** Zero-configuration local database (`aegis_local.db`) allowing complete offline execution, deterministic integration testing, and instant failover resilience.

### 5.1 Entity Relationship Diagram

```
   ┌───────────────────────────┐                ┌───────────────────────────┐
   │          CLAIMS           │                │         EVIDENCE          │
   ├───────────────────────────┤ 1            N ├───────────────────────────┤
   │ PK  id (uuid / text)      │◄───────────────┤ FK  claim_id (uuid / text)│
   │ UQ  claim_hash (text)     │                │ PK  id (uuid / text)      │
   │     claim_text (text)     │                │     source_url (text)     │
   │     normalized_text (text)│                │     canonical_url (text)  │
   │     status (text)         │                │     publisher (text)      │
   │     verdict (text)        │                │     title (text)          │
   │     confidence (float)    │                │     stance (text)         │
   │     severity (text)       │                │     summary (text)        │
   │     reasoning (text)      │                │     retrieval_method      │
   │     source_url (text)     │                │     retrieval_timestamp   │
   │     metadata (jsonb/text) │                │     metadata (jsonb/text) │
   │     created_at (timestamptz)               └───────────────────────────┘
   │     updated_at (timestamptz)
   └───────────────────────────┘

   ┌───────────────────────────┐                ┌───────────────────────────┐
   │     VERIFIED_THREATS      │                │     DEPLOYED_MEASURES     │
   ├───────────────────────────┤ 1            N ├───────────────────────────┤
   │ PK  id (bigint identity)  │◄───────────────┤ FK  event_id (bigint)     │
   │ UQ  event_id (text)       │                │ PK  id (bigint identity)  │
   │     ticker (text)         │                │     measure_type (text)   │
   │     crash_timestamp       │                │     current_stock_price   │
   │     current_price (float) │                │     stock_price_at_deploy │
   │     projected_loss (float)│                │     deployed_at           │
   │     z_score (float)       │                │     effectiveness (text)  │
   │     smoking_gun_headline  │                │     metadata (jsonb/text) │
   │     smoking_gun_link      │                └───────────────────────────┘
   │     latency_minutes(float)│
   │     panic_score (integer) │                ┌───────────────────────────┐
   │     responses (jsonb/text)│                │      ACTIVE_SIGNALS       │
   │     response_deployed     │                ├───────────────────────────┤
   └───────────────────────────┘                │ PK  id (bigint identity)  │
                                                │     ticker (text)         │
                                                │     signal_type (text)    │
                                                │     severity (float)      │
                                                │     timestamp             │
                                                │     metadata (jsonb/text) │
                                                └───────────────────────────┘
```

---

### 5.2 Table: `claims` (Core Epistemic Truth Verification)

Stores cryptographic hashes, normalized texts, and synthesized truth determinations for investigated statements.

| Column Name | PostgreSQL Type | SQLite Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `id` | `uuid` | `TEXT` | **NO** | `gen_random_uuid()` | **PRIMARY KEY**. Unique claim record identifier. |
| `claim_hash` | `text` | `TEXT` | **NO** | *None* | **UNIQUE**. SHA-256 hash of normalized text for instant $O(1)$ deduplication. |
| `claim_text` | `text` | `TEXT` | **NO** | *None* | Raw, unmodified claim or headline as submitted by user or scraped by ingestion. |
| `normalized_text` | `text` | `TEXT` | **NO** | *None* | Whitespace-collapsed, lowercased, Unicode NFC normalized string for linguistic comparison. |
| `status` | `text` | `TEXT` | **NO** | `'pending'` | Ingestion lifecycle state: `'pending'`, `'in_progress'`, `'completed'`, `'failed'`. |
| `verdict` | `text` | `TEXT` | YES | `NULL` | Truth determination: `'True'`, `'False'`, `'Misleading'`, `'Partially True'`, `'Unverified'`, `'Insufficient Evidence'`. |
| `confidence` | `float` | `REAL` | YES | `NULL` | Bayesian certainty score computed across independent evidence clusters ($0.00$ to $1.00$). |
| `severity` | `text` | `TEXT` | YES | `NULL` | Societal or market impact severity: `'Low'`, `'Medium'`, `'High'`, `'Critical'`. |
| `reasoning` | `text` | `TEXT` | YES | `NULL` | Synthesized 1–3 sentence bottom-line rationale explaining why the verdict was issued. |
| `source_url` | `text` | `TEXT` | YES | `NULL` | Original URL or platform permalink where the claim was first observed. |
| `metadata` | `jsonb` | `TEXT` | YES | `'{}'::jsonb` | Extensible JSON storing pipeline telemetry, tokens used, latency ms, and agent attribution. |
| `created_at` | `timestamptz` | `TEXT` | YES | `now()` | ISO-8601 UTC timestamp of initial record ingestion. |
| `updated_at` | `timestamptz` | `TEXT` | YES | `now()` | ISO-8601 UTC timestamp of last verdict re-evaluation or evidence attachment. |

---

### 5.3 Table: `evidence` (Source-Grounded Citations & Quotes)

Maintains empirical evidentiary fragments retrieved across Agent Reach channels, directly bound to parent claims.

| Column Name | PostgreSQL Type | SQLite Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `id` | `uuid` | `TEXT` | **NO** | `gen_random_uuid()` | **PRIMARY KEY**. Unique evidence fragment identifier. |
| `claim_id` | `uuid` | `TEXT` | **NO** | *None* | **FOREIGN KEY** $\rightarrow$ `claims(id)` `ON DELETE CASCADE`. Associated claim. |
| `source_url` | `text` | `TEXT` | YES | `NULL` | Direct, verifiable external hyperlink to the cited article or filing (zero placeholders). |
| `canonical_url` | `text` | `TEXT` | YES | `NULL` | Normalized destination URL after stripping tracking query parameters (`utm_*`, `ref`). |
| `publisher` | `text` | `TEXT` | YES | `NULL` | Human-readable source or outlet name (e.g. `Reuters`, `SEC EDGAR`, `r/stocks`). |
| `title` | `text` | `TEXT` | YES | `NULL` | Headline or document title of the retrieved source. |
| `stance` | `text` | `TEXT` | **NO** | `'supporting'` | Stance relative to the claim: `'supporting'`, `'refuting'`, or `'neutral'`. |
| `summary` | `text` | `TEXT` | **NO** | *None* | Factual extract or verbatim quote demonstrating why this citation supports or refutes. |
| `retrieval_method` | `text` | `TEXT` | YES | `'agent_reach_scraper'` | Ingestion mechanism (e.g. `agent_reach_scraper`, `google_news_rss`, `jina_reader`). |
| `retrieval_timestamp` | `timestamptz` | `TEXT` | YES | `now()` | Timestamp when the scraper indexed the external resource. |
| `metadata` | `jsonb` | `TEXT` | YES | `'{}'::jsonb` | JSON payload storing Jaccard similarity score, syndication group ID, and credibility score. |

---

### 5.4 Table: `active_signals` (Scout Agent Market Surveillance)

Logs statistical price volatility alerts, z-score spikes, and abnormal volume deviations detected across equity tickers.

| Column Name | PostgreSQL Type | SQLite Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `id` | `bigint identity` | `INTEGER` | **NO** | Auto-increment | **PRIMARY KEY**. Sequence counter. |
| `ticker` | `text` | `TEXT` | **NO** | *None* | Stock ticker symbol (e.g. `NVDA`, `TATAMOTORS.NS`, `RELIANCE.NS`). |
| `signal_type` | `text` | `TEXT` | **NO** | *None* | Alert classification: `'CRASH'`, `'SIGMA_EVENT'`, `'HIGH_VOLATILITY'`. |
| `severity` | `float` | `REAL` | YES | `NULL` | Quantitative anomaly magnitude: Volatility dispersion z-score ($Z = \frac{P_t - \mu}{\sigma}$). |
| `timestamp` | `timestamptz` | `TEXT` | YES | `now()` | Observation timestamp. |
| `metadata` | `jsonb` | `TEXT` | YES | `NULL` | JSON containing intraday high/low quotes, moving averages, and exchange status. |

---

### 5.5 Table: `verified_threats` (Correlated Financial Smear Attacks)

Captures high-conviction events where false rumors or synthetic smears correlate directly with sudden market sell-offs.

| Column Name | PostgreSQL Type | SQLite Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `id` | `bigint identity` | `INTEGER` | **NO** | Auto-increment | **PRIMARY KEY**. Sequence counter. |
| `event_id` | `text` | `TEXT` | **NO** | *None* | **UNIQUE**. Canonical format: `TICKER_YYYYMMDD_HHMMSS`. |
| `ticker` | `text` | `TEXT` | **NO** | *None* | Affected equity ticker. |
| `crash_timestamp` | `timestamptz` | `TEXT` | YES | `NULL` | Timestamp when equity price crossed the negative sigma threshold. |
| `current_price` | `float` | `REAL` | YES | `NULL` | Equity price at time of incident detection. |
| `projected_loss` | `float` | `REAL` | YES | `NULL` | Total percentage drop ($\Delta\%$) observed during anomaly window. |
| `z_score` | `float` | `REAL` | YES | `NULL` | Statistical standard deviation dispersion score ($\ge 2.0\sigma$). |
| `smoking_gun_headline`| `text` | `TEXT` | YES | `NULL` | The specific sensational headline identified as the primary catalyst. |
| `smoking_gun_link` | `text` | `TEXT` | YES | `NULL` | Hyperlink to the catalyst post or article. |
| `article_timestamp` | `timestamptz` | `TEXT` | YES | `NULL` | Publication timestamp of the catalyst article. |
| `latency_minutes` | `float` | `REAL` | YES | `NULL` | Time elapsed (minutes) between catalyst publication and market crash. |
| `panic_score` | `integer` | `INTEGER` | YES | `NULL` | Social velocity score on a scale of $0$ to $100$. |
| `correlation_confidence`| `integer` | `INTEGER` | YES | `NULL` | Epistemic correlation certainty ($0$ to $100$). |
| `responses` | `jsonb` | `TEXT` | YES | `NULL` | Automated crisis PR, cease-and-desist drafts, and regulatory filing notices. |
| `response_deployed` | `boolean` | `INTEGER` | YES | `false` | Boolean flag ($1/0$) indicating if mitigation measures were activated. |
| `created_at` | `timestamptz` | `TEXT` | YES | `now()` | Record creation timestamp. |
| `metadata` | `jsonb` | `TEXT` | YES | `NULL` | Telemetry payload storing short attack probability and source clusters. |

---

### 5.6 Table: `deployed_measures` (Incident Response Audit Trail)

Maintains the immutable ledger of countermeasures deployed in response to verified threats.

| Column Name | PostgreSQL Type | SQLite Type | Nullable | Default | Constraints & Description |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `id` | `bigint identity` | `INTEGER` | **NO** | Auto-increment | **PRIMARY KEY**. Countermeasure execution identifier. |
| `event_id` | `bigint` | `INTEGER` | **NO** | *None* | **FOREIGN KEY** $\rightarrow$ `verified_threats(id)` `ON DELETE CASCADE`. |
| `measure_type` | `text` | `TEXT` | **NO** | *None* | Strategy type: `'cease_desist'`, `'official_denial'`, `'ceo_alert'`, `'sec_filing'`. |
| `current_stock_price` | `float` | `REAL` | YES | `NULL` | Current stock price as of the latest audit. |
| `stock_price_at_deployment`| `float` | `REAL` | YES | `NULL` | Stock price at the exact moment countermeasure was dispatched. |
| `deployed_at` | `timestamptz` | `TEXT` | YES | `now()` | Timestamp of deployment. |
| `effectiveness` | `text` | `TEXT` | YES | `NULL` | Post-mitigation evaluation: `'SUCCESS'` (price stabilized), `'FAILURE'`, `'NEUTRAL'`. |
| `metadata` | `jsonb` | `TEXT` | YES | `NULL` | Delivery receipts, dispatch logs, or webhook response payloads. |

---

### 5.7 Performance Indexing Strategy

To guarantee sub-15ms response times across the REST gateway, the following B-tree indexes are enforced:

```sql
-- Claims deduplication and temporal ordering
CREATE INDEX IF NOT EXISTS idx_claims_hash ON claims(claim_hash);
CREATE INDEX IF NOT EXISTS idx_claims_created ON claims(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);

-- Evidence relational lookup
CREATE INDEX IF NOT EXISTS idx_evidence_claim_id ON evidence(claim_id);

-- Scout Agent market surveillance queries
CREATE INDEX IF NOT EXISTS idx_active_signals_timestamp ON active_signals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_active_signals_ticker ON active_signals(ticker);

-- Verified threats & incident response joins
CREATE INDEX IF NOT EXISTS idx_verified_threats_ticker ON verified_threats(ticker);
CREATE INDEX IF NOT EXISTS idx_verified_threats_created ON verified_threats(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deployed_measures_event ON deployed_measures(event_id);
```

