# Aegis Protocol 2.0 (v4.1.0) — Final Production Deployment Guide

**Document Version:** 2.0.0  
**Classification:** Canonical Production Deployment Standard  
**Release Target:** Aegis Protocol 2.0 Enterprise Intelligence Engine  
**Date:** 2026-10-31  

---

## 1. System Overview & Release Architecture

Aegis Protocol 2.0 delivers an evidence-first, multi-perspective intelligence and misinformation verification platform.

```
                         ┌────────────────────────────────────────────────────────┐
                         │               Aegis Protocol 2.0 Web UI               │
                         │   (Pure SVG/Canvas Analytics & Intelligence Trans.)    │
                         └───────────────────────────┬────────────────────────────┘
                                                     │ HTTP / JSON
                                                     ▼
                         ┌────────────────────────────────────────────────────────┐
                         │               FastAPI Modular Gateway                 │
                         │    (/api/claims, /api/scout, /api/agent-reach, ...)   │
                         └───────────────────────────┬────────────────────────────┘
                                                     │
               ┌─────────────────────────────────────┼─────────────────────────────────────┐
               ▼                                     ▼                                     ▼
┌─────────────────────────────┐       ┌─────────────────────────────┐       ┌─────────────────────────────┐
│    Autonomous Sentinels     │       │     Acquisition Fabric      │       │     Security & Ledger       │
│  - Scout (Financial)        │       │  - NativeRouter (16 Ops)    │       │  - SSRF Guard (is_safe_url) │
│  - BrandShield (Brand)      │──────▶│  - SourcePlanningEngine     │──────▶│  - Bounded Buffer (1MB)     │
│  - Trending (Viral Claims)  │       │  - Zero-Auth Social (Reddit)│       │  - 5.0s Strict Timeouts     │
│  - Personal Watch (VIP)     │       │  - Zero-Auth Social (X/Twit)│       │  - SHA-256 Replay Ledger    │
└─────────────────────────────┘       └─────────────────────────────┘       └─────────────────────────────┘
               │                                     │                                     │
               └─────────────────────────────────────┼─────────────────────────────────────┘
                                                     │
                                                     ▼
                         ┌────────────────────────────────────────────────────────┐
                         │           Persistence & Centralized LLM                │
                         │   - SQLite / Supabase Dual Persistence                 │
                         │   - Gemini 2.5/3.8 Flash (Mock Guard in Production)    │
                         └────────────────────────────────────────────────────────┘
```

---

## 2. Environment Configuration Matrix

Create or verify the `.env` file before booting the service:

| Variable | Environment | Default / Example | Purpose & Invariant |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | All | `production` / `development` | When set to `production`, `AEGIS_MOCK_LLM=true` is forbidden. |
| `GEMINI_API_KEY` | Production | `AIzaSy...` | Primary LLM intelligence key for reasoning and synthesis. |
| `GEMINI_PRIMARY_MODEL` | All | `gemini-3.8-flash` | High-efficiency primary model for claim deconstruction. |
| `AEGIS_SQLITE_PATH` | All | `backend/data/aegis_local.db` | Local SQLite persistence path for dossiers and audit ledgers. |
| `SUPABASE_URL` | Optional | `https://xyz.supabase.co` | Remote PostgreSQL cloud database (optional fallback). |
| `SUPABASE_KEY` | Optional | `eyJhbG...` | Supabase API key (optional fallback). |
| `RSS_INGESTION_ENABLED`| Production | `false` (recommended) | Set to `false` for interactive multi-agent deployments to prevent background wire polling thread contention. |
| `PORT` | All | `8000` | HTTP service port. |
| `HOST` | All | `0.0.0.0` (Container) / `127.0.0.1` | Network binding interface. |

---

## 3. Pre-Deployment Verification Gate (Mandatory Checklist)

Before releasing to staging or production, run the automated verification sequence:

```bash
# 1. Full Fast Regression Suite (868 tests: unit, chaos, security)
pytest tests/unit tests/chaos tests/security -q
# Target: 868 passed, 0 failures

# 2. Static Code Syntax & Undefined Symbol Analysis
flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
# Target: 0 errors

# 3. Release Candidate Smoke Validation (11 gates)
python scripts/validate_release_candidate_smoke.py
# Target: OFFLINE_SMOKE_PASS

# 4. Rollback & Historical Archive Validation
python scripts/validate_rollback_compatibility.py
# Target: PASS on fresh process and historical readers (55 invalid legacy JSON files reported honestly)

# 5. Live Multi-Agent Real-Query Smoke Verification
python scripts/evaluation/quick_agent_check.py
# Target: All 4 agents yield real evidence and >1,000 words
```

---

## 4. Production Deployment Methods

### Method A: Direct Bare Metal / Systemd (Python 3.11+)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Launch with Uvicorn Worker**:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4 --timeout-keep-alive 30
   ```

### Method B: Docker & Container Orchestration

1. **Build Container Image**:
   ```bash
   docker build -t aegis-protocol:2.0 .
   ```
2. **Execute via Docker Compose**:
   ```bash
   docker compose up -d
   ```
3. **Verify Container Health**:
   ```bash
   curl http://localhost:8000/api/healthz
   ```

---

## 5. Health Probes & Monitoring Specification

| Probe | Endpoint | Expected Status | Description |
| :--- | :--- | :--- | :--- |
| **Liveness** | `GET /api/healthz` | `HTTP 200` | Verifies process responsiveness and registered router modules. |
| **Readiness** | `GET /api/readyz` | `HTTP 200` | Verifies capability registry status and subsystem readiness. |
| **Capabilities**| `GET /api/agent-reach/capabilities`| `HTTP 200` | Reports real-time status and cooldowns across all 18 channels. |
| **Diagnostics** | `GET /api/agent-reach/doctor` | `HTTP 200` | Comprehensive diagnostic check of all acquisition backends. |

---

## 6. Security & Operational Boundaries

1. **SSRF Guard**: All outbound fetches are pre-screened via `is_safe_url()`, rejecting private subnets, loopbacks, and metadata IPs (`169.254.169.254`).
2. **Bounded Buffer Caps**: Max payload size is bounded to `1,000,000` bytes. HTTP timeouts are capped at `5.0s`.
3. **Zero Secret Leakage**: No API keys or tokens are stored in persistent dossiers or log files.
4. **Zero Fabrication**: If sources are unreachable, the system reports `INSUFFICIENT_EVIDENCE`.

