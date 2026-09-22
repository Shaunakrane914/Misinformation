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
