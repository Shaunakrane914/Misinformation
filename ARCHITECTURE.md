# 🛡️ Aegis Protocol — System Architecture

**Status:** Canonical System Architecture Entrypoint  
**Authoritative Specifications:**
- [🏛️ Target Modular Monolith Blueprint](docs/architecture/TARGET_ARCHITECTURE.md)
- [📦 Codebase Inventory & Defect Register](docs/architecture/CODEBASE_INVENTORY.md)
- [🗺️ Phased Migration Plan](docs/architecture/MIGRATION_PLAN.md)
- [📋 Architecture Decision Records (ADRs)](docs/architecture/adr/README.md)
- [🔬 Detailed Multi-Agent Fabric & Schemas](docs/ARCHITECTURE.md)

---

## 1. High-Level Architectural Topology

Aegis Protocol is an evidence-first claim verification system and intelligence sentinel fabric built as a **structured modular monolith** with strict layer boundaries:

```
                            ┌──────────────────────────────────────┐
                            │    Human Analyst / Web Consoles      │
                            │  (Level 1 -> Level 2 -> Level 3 UI)  │
                            └──────────────────┬───────────────────┘
                                               │ HTTP / REST / JSON
                                               ▼
                            ┌──────────────────────────────────────┐
                            │      FastAPI Gateway (backend/api)   │
                            │  7 Domain Routers: claims, scout,    │
                            │  trending, brandshield, personal,    │
                            │  replay, healthz                     │
                            └──────────────────┬───────────────────┘
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐
               ▼                                                               ▼
 ┌───────────────────────────┐                                   ┌───────────────────────────┐
 │   Domain Sentinel Fleet   │                                   │       Truth Tribunal      │
 ├───────────────────────────┤                                   ├───────────────────────────┤
 │ • Scout Agent (Financial) │                                   │ • Claim Ingestion Agent   │
 │ • Trending Agent (Virality│                                   │   (Unicode NFC + SHA-256) │
 │ • BrandShield (Reputation)│                                   │ • Research Engine         │
 │ • Personal Watch (VIP/OSINT                                   │   (Relevance Gate + Guard)│
 └─────────────┬─────────────┘                                   │ • Investigator Agent      │
               │                                                 │   (Forensic Case Dossier) │
               │                                                 └─────────────┬─────────────┘
               │                                                               │
               └───────────────────────────────┬───────────────────────────────┘
                                               │
                                               ▼
                            ┌──────────────────────────────────────┐
                            │   Shared Acquisition Runtime Layer   │
                            │      (backend/services/agent_reach)  │
                            ├──────────────────────────────────────┤
                            │ • 14-Channel Capability Registry     │
                            │ • Domain Retrieval Planner           │
                            │ • Platform Adapters (Web, RSS, Social│
                            │ • SSRF Pre-Fetch Validation Guard    │
                            │ • Wire Syndication Clustering        │
                            └──────────────────┬───────────────────┘
                                               │
                                               ▼
                            ┌──────────────────────────────────────┐
                            │      Dual Persistence Engines        │
                            ├──────────────────────────────────────┤
                            │ • SQLite: aegis_local.db (offline)   │
                            │ • PostgreSQL / Supabase (cloud)      │
                            └──────────────────────────────────────┘
```

---

## 2. Core Subsystems & Responsibilities

### 1. API & Presentation Layer (`backend/api/`, `frontend/`)
- **FastAPI Modular Routers:** Decomposed across 7 domain routers (`claims.py`, `agents.py`, `health.py`, `replay.py`) under `backend/api/`.
- **Progressive Disclosure Consoles:** Vanilla HTML/JS analyst consoles applying a 3-tier disclosure model:
  - **Level 1 (Orientation):** Decision banner, verdict badge, confidence score, bottom-line takeaway (<10s comprehension).
  - **Level 2 (Investigation):** Empirical "Why" findings, supporting vs. refuting evidence comparison matrix, unresolved factor boxes.
  - **Level 3 (Raw Evidence):** Expandable evidence cards with excerpt quotes, source roles (`PRIMARY`, `SECONDARY`), and zero placeholder links.

### 2. Autonomous Sentinel Fleet (`backend/agents/`)
Specialized intelligence nodes with domain-tailored threat scoring:
- **Scout Agent (Financial Surveillance):** Yahoo Finance real-time price feeds, volume z-scores, event-clustered news correlation, SEC EDGAR filings.
- **Trending Agent (Viral Claims):** Multi-channel RSS discovery, velocity estimation, memetic emergence tracking, and 48-hour freshness enforcement via `TemporalGuard`.
- **BrandShield Agent (Brand Protection):** Brand threat cards, counterfeit storefront listings, astroturfing review brigading heuristics.
- **Personal Watch Agent (Executive Defense):** Executive OSINT footprint monitoring, impersonation handle detection, defamation triage.

### 3. Truth Tribunal & Fact Verification (`backend/agents/`, `backend/services/research/`)
- **Claim Ingestion Agent:** Unicode NFC normalization, whitespace collapsing, length limits, deterministic SHA-256 deduplication.
- **Research Engine:** Multi-stage investigation pipeline executing planning, discovery, relevance gating, temporal eligibility, source quality scoring, deep reading, and passage extraction.
- **Investigator Agent:** Forensic case dossiers, 6-verdict taxonomy (`True`, `False`, `Misleading`, `Partially True`, `Unverified`, `Insufficient Evidence`), structured limitations disclosures.

### 4. Shared Acquisition Runtime (`backend/services/agent_reach/`)
The single authoritative internet evidence acquisition backbone:
- **Capability Registry:** Dynamic health tracking across 14 channels (7 zero-config: `reddit`, `twitter`, `youtube`, `news`, `jina_reader`, `github`, `rss`; 7 authenticated: `linkedin`, `bilibili`, `xueqiu`, `xiaohongshu`, `instagram`, `facebook`, `boss`).
- **Domain Retrieval Planner:** Generates specialized search strategies for `fact_check`, `financial`, `brand`, `personal`, and `trending` queries.
- **Syndication Clustering:** Identifies duplicate wire stories (Reuters, AP, Bloomberg, PR Newswire) to prevent false corroboration.
- **SSRF Defense:** Hard pre-fetch validation blocking private RFC 1918, loopback, and cloud metadata (AWS/GCP) addresses.

### 5. Persistence & Provenance (`backend/db/`, `backend/services/research/replay_ledger.py`)
- **Dual Persistence:** High-throughput PostgreSQL (Supabase) in production with automatic fallback to zero-configuration local SQLite (`aegis_local.db`).
- **Replay Ledger:** Cryptographic SHA-256 provenance chain recording all executed queries, raw responses, parsed fragments, and verdict states.

---

## 3. Documentation Index & Canonical Sources

| Topic | Canonical Documentation File | Description |
| :--- | :--- | :--- |
| **Documentation Portal** | [`docs/index.md`](docs/index.md) | Central entrypoint for all project documentation |
| **Target Architecture** | [`docs/architecture/TARGET_ARCHITECTURE.md`](docs/architecture/TARGET_ARCHITECTURE.md) | Target modular monolith layering and boundary rules |
| **Codebase Inventory** | [`docs/architecture/CODEBASE_INVENTORY.md`](docs/architecture/CODEBASE_INVENTORY.md) | Authoritative module, size, dependency, and defect catalog |
| **Migration Plan** | [`docs/architecture/MIGRATION_PLAN.md`](docs/architecture/MIGRATION_PLAN.md) | Phased engineering refactoring roadmap (Phases 0–7) |
| **Architecture Decisions** | [`docs/architecture/adr/`](docs/architecture/adr/) | Proposed ADRs 0001–0005 pending review (ADR 0000 active template) |
| **Detailed System Fabric** | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Complete SQL schemas, UI disclosure tiers, inter-agent workflows |
| **Feature Status** | [`docs/FEATURE_STATUS.md`](docs/FEATURE_STATUS.md) | Truth matrix separating production, prototype, and simulation |
| **Testing & Verification** | [`docs/TESTING.md`](docs/TESTING.md) | Test suite runbook and regression test baseline (530 tests) |
| **Scientific Evaluation** | [`docs/EVALUATION.md`](docs/EVALUATION.md) | 104-scenario Cranfield benchmark and ML baseline audit |
| **Security Policy** | [`docs/SECURITY.md`](docs/SECURITY.md) | SSRF defenses, URL sanitization, prompt injection safeguards |
| **Operational Runbook** | [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Deployment runbook, health probes, Docker setup, and settings |
| **Historical Archive** | [`docs/archive/README.md`](docs/archive/README.md) | Archived legacy audits and superseded milestone reports |
