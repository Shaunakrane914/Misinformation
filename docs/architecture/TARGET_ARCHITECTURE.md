# Aegis Protocol — Target Architecture Specification

**Status:** Authoritative Target Blueprint (Phase 0)  
**Date:** October 9, 2026  
**Pattern:** Structured Modular Monolith with Inverted Dependency Boundaries  
**Target Repository:** `ShaunakRane914/Misinformation`

---

## 1. Architectural Vision & Core Principles

Aegis Protocol is designed as a **modular monolith** executing autonomous intelligence discovery, threat deconstruction, and evidence verification.

The target architecture enforces five core principles:
1. **Unidirectional Dependency Inversion**: Higher-level domain and agent policy modules must depend on stable abstractions, not on volatile network scraping tools or database drivers.
2. **One Authoritative Acquisition Fabric**: A single capability-aware acquisition runtime handles all internet data fetching, platform adapters, fallback chains, and telemetry attribution.
3. **Pure Domain Logic**: Domain evaluation gates (relevance, entity resolution, temporal eligibility, epistemic consensus) contain zero network or I/O side effects.
4. **Autonomous Domain Agents**: Each domain agent (BrandShield, Trending, Scout, Personal Watch) owns its query strategy, entity extraction, and domain response schemas, but delegates all network fetching to the acquisition fabric.
5. **Deterministic Auditability**: Every finding is backed by an immutable cryptographic hash chain and reproducible evidence lineage.

---

## 2. Target Layering & Directory Topology

```mermaid
graph TD
    subgraph Client Layer
        WebDashboards[Vanilla HTML/JS Analyst Consoles & REST Clients]
    end

    subgraph API Layer [backend/api/]
        Routers[FastAPI Routers: claims, agents, system, replay, threat_lab]
        Schemas[Pydantic Request & Response Schemas]
        Deps[Dependency Injection: get_current_user, get_db, get_llm]
    end

    subgraph Application Layer [backend/application/]
        ClaimUseCase[Claim Verification Workflow]
        ResearchOrchestrator[Research Pipeline Orchestrator]
        ScanOrchestrator[Domain Scan Coordinator]
    end

    subgraph Domain Layer [backend/domain/]
        DomainModels[EvidenceItem, Finding, TruthDossier, QualityTensor]
        DomainPolicies[EntityResolver, TemporalGuard, RelevanceGate]
        LineageDAG[SourceLineage, AuditLineageValidator, ReplayLedger]
    end

    subgraph Agent Modules [backend/agents/]
        BrandShield[BrandShield: Counterfeit & Phishing Sentinels]
        Trending[Trending: Viral Velocity & 48h Freshness]
        Scout[Scout: SEC Filings & Financial Surveillance]
        PersonalWatch[Personal Watch: VIP Impersonation & Homographs]
    end

    subgraph Infrastructure Layer [backend/infrastructure/]
        subgraph Acquisition Runtime [infrastructure/acquisition/]
            AcqRouter[Capability Router & Dispatcher]
            PlatformAdapters[Web, News, Reddit, Twitter, YouTube, GitHub Adapters]
            SSRFValidator[SSRF & Private IP Validator]
            AcqTelemetry[Lineage Attribution & Health Tracking]
        end
        subgraph LLM Gateway [infrastructure/llm/]
            GeminiAdapter[Google Gemini Provider + Key Rotation]
            MockLLM[Deterministic Offline Mock Provider]
        end
        subgraph Persistence [infrastructure/persistence/]
            SupabaseRepo[Supabase Cloud Repository]
            SQLiteRepo[SQLite Local Fallback Repository]
        end
    end

    subgraph Cross-Cutting Core [backend/core/]
        Settings[Pydantic Validated Settings]
        Logging[Structured JSON Logging]
        Errors[Aegis Domain Error Hierarchy]
    end

    WebDashboards --> Routers
    Routers --> Schemas
    Routers --> Application Layer
    Application Layer --> Domain Layer
    Application Layer --> Agent Modules
    Agent Modules --> Domain Layer
    Agent Modules --> Acquisition Runtime
    Application Layer --> Infrastructure Layer
    Infrastructure Layer -.->|Implements Ports| Domain Layer
    Infrastructure Layer -.->|Implements Ports| Application Layer
```

### Destination File Tree
```
backend/
├── main.py                      # Application factory, lifespan, CORS, middleware
├── core/                        # Cross-cutting foundational modules
│   ├── settings.py              # Pydantic Settings (validated environment variables)
│   ├── logging.py               # Structured logging configuration
│   ├── errors.py                # Base Aegis exception hierarchy
│   └── telemetry.py             # OpenTelemetry / system metrics instrumentation
├── api/                         # FastAPI presentation layer
│   ├── dependencies.py          # FastApi Depends providers
│   ├── routers/
│   │   ├── claims.py            # Claim verification endpoints
│   │   ├── agents.py            # Agent sentinel endpoints
│   │   ├── system.py            # Health, Doctor, readiness probes
│   │   ├── agent_reach.py       # Acquisition REST API
│   │   ├── replay.py            # Forensic replay ledger API
│   │   └── threat_lab.py        # Mathematical threat simulation
│   └── schemas/                 # Request and response Pydantic schemas
├── domain/                      # Pure business rules, policies, and contracts
│   ├── models/                  # EvidenceItem, Finding, QualityTensor, TruthDossier
│   ├── policies/
│   │   ├── entity_resolver.py   # Named entity disambiguation & homograph rules
│   │   ├── temporal_guard.py    # 48h freshness window & timestamp integrity
│   │   ├── relevance_gate.py    # Deterministic multi-stage gating
│   │   └── source_quality.py    # Tier-1 / Tier-2 source credibility classification
│   └── lineage/
│       ├── replay_ledger.py     # SHA-256 cryptographic provenance chain
│       └── audit_validator.py   # Invariants A–H DAG verification
├── application/                 # Orchestration & Use Cases
│   ├── claims/                  # Ingestion, claim hashing, deduplication
│   ├── research/                # Composable 10-stage research pipeline orchestrator
│   └── scans/                   # Multi-agent threat coordination
├── agents/                      # Specialized Domain Sentinel Packages
│   ├── brandshield/             # BrandShield query strategies & extraction
│   ├── trending/                # Viral velocity models & trending extraction
│   ├── scout/                   # Financial source engines, SEC parsers, YFinance
│   └── personal_watch/          # VIP impersonation, bio parsers, homograph filters
└── infrastructure/              # Concrete external technology adapters
    ├── acquisition/             # Single authoritative acquisition runtime
    │   ├── contracts.py         # RetrievalRequest, EvidenceFragment, CandidateSource
    │   ├── routing/             # Channel router, capability matrix, route policy
    │   ├── adapters/            # Modular platform adapters (Web, News, Social, Jina)
    │   ├── security/            # SSRF filter, DNS rebinding defense, URL canonicalizer
    │   └── telemetry/           # Fallback tracking, channel health, latency records
    ├── llm/                     # Centralized LLM Provider Gateway
    │   ├── gateway.py           # Abstract LLMGateway protocol
    │   ├── gemini.py            # Gemini client with exponential backoff & rotation
    │   └── mock.py              # Zero-network offline mock provider
    └── persistence/             # Storage implementations
        ├── contracts.py         # ClaimRepository, EvidenceRepository protocols
        ├── supabase.py          # Cloud PostgreSQL/Supabase client
        └── sqlite.py            # Local zero-dependency SQLite fallback
```

---

## 3. Boundary Rules & Import Contracts

| Layer | Responsibility | May Import | Must NEVER Import | Test Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **API Layer** (`api/`) | HTTP serialization, status codes, OpenAPI docs | `application/`, `domain/`, `core/` | Low-level scraping tools, raw SQL/DB cursors | FastAPI `TestClient`, schema validation |
| **Application Layer** (`application/`) | Coordinates multi-step use cases, transaction scripts | `domain/`, `agents/`, `infrastructure/contracts.py`, `core/` | FastAPI request/response objects directly | Unit tests with mocked infrastructure ports |
| **Domain Layer** (`domain/`) | Pure business rules, gating, quality tensors, lineage | Standard library, `pydantic`, `core/errors.py` | Network libraries (`requests`, `httpx`), external SDKs | Pure unit tests (0ms I/O latency) |
| **Agent Modules** (`agents/`) | Domain threat policy, query generation, extraction | `domain/`, `infrastructure/acquisition/contracts.py`, `core/` | Private adapter internals, rival agent packages | Contract tests, domain benchmark queries |
| **Infrastructure** (`infrastructure/`) | Implements external network, LLM, and DB calls | External SDKs, `domain/models/`, `core/` | API route handlers, application use cases | Chaos tests, integration tests, contract tests |
| **Core** (`core/`) | Logging, settings, error definitions, telemetry | Standard library, `pydantic-settings` | Any higher layer (`domain`, `api`, `infrastructure`) | Framework unit tests |

---

## 4. Mapping: Current Codebase to Target Architecture

| Current Location | Target Location | Migration Strategy | Risk Level |
| :--- | :--- | :--- | :---: |
| `backend/services/agent_reach/native/router.py` (1,706 lines) | `backend/infrastructure/acquisition/routing/` + `adapters/` | Split into modular platform adapters; thin router orchestrates | **High** |
| `backend/services/agent_reach/adapter.py` (duplicate `retrieve`) | `backend/infrastructure/acquisition/service.py` | Reconcile duplicate signatures into single polymorphic contract | **Medium** |
| `backend/services/agent_reach/extraction/*` (1,093 lines) | Relocate to respective `backend/agents/{agent}/extraction/` | Move extraction logic to owning domain agents | **Medium** |
| `backend/services/agent_reach/scout/*` (2,106 lines) | Relocate into `backend/agents/scout/` | Unify financial discovery and ranking inside Scout package | **Medium** |
| `backend/services/research/research_engine.py` (581-line `investigate`) | `backend/application/research/pipeline.py` + stage handlers | Break monolithic method into 10 composable pipeline stages | **High** |
| `backend/services/gemini_service.py` + `intelligence.py` | `backend/infrastructure/llm/` | Unify behind `LLMGateway` protocol with injected mock mode | **Low** |
| `backend/db/database.py` (527 lines) | `backend/infrastructure/persistence/` | Separate Supabase and SQLite implementations behind repository interface | **Low** |
| `backend/config.py` (76 lines) | `backend/core/settings.py` | Upgrade to Pydantic `BaseSettings` with startup validation | **Low** |

---

## 5. Architectural Quality Attributes & Non-Functional Invariants

1. **Deterministic Offline Invariant**:
   - Running tests with `ENVIRONMENT=test` or `AEGIS_MOCK_LLM=true` must produce 100% deterministic results with zero outbound network calls to external APIs.
2. **SSRF Immune Acquisition**:
   - All external URL reads in acquisition must be validated by `SSRFValidator` to block IPv4/IPv6 loopback, link-local, private RFC 1918 ranges, and AWS/GCP cloud metadata endpoints (`169.254.169.254`).
3. **Temporal Freshness Invariant**:
   - Trending sentinel evaluations must reject articles with publication age > 48.0 hours.
4. **Lineage Completeness Invariant**:
   - 100% of generated intelligence findings must trace to an `EvidenceItem` in the `TruthDossier` with non-empty `source_url` and `retrieval_timestamp`.
