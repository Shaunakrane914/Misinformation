# Aegis Protocol — Production Configuration Matrix
**Phase 7.1 Release Candidate Deliverable D**  
*Lead Production Reliability Engineer Audit*

---

## 1. Configuration Philosophy & Guardrails

Aegis Protocol enforces a fail-safe configuration contract managed centrally via [`backend/core/settings.py`](../../backend/core/settings.py) and ADR 0004.
All configuration is validated at process startup using Pydantic Settings.

### Core Guardrail Invariants
1. **No Synthetic Production Evidence**: When `ENVIRONMENT=production`, setting `AEGIS_MOCK_LLM=true` raises a startup `ValidationError` to prevent synthetic or fabricated evidence generation in production.
2. **Graceful Degradation**: Missing optional API keys (Gemini, Apify, Yahoo Finance, GitHub, Twitter) do **not** crash the process. The platform operates deterministically using zero-cost public adapters, reporting honest `AUTH_REQUIRED` or `DEGRADED` states at `/api/agent-reach/capabilities` and `/api/readyz`.
3. **No Secret Leakage**: API keys, auth cookies, and bearer tokens are excluded from all public endpoints (`/api/healthz`, `/api/readyz`, `/api/agent-reach/doctor`, `/api/agent-reach/capabilities`) and HTTP request logs.
4. **Isolated RSS Background Polling**: In multi-worker deployments (e.g. Gunicorn / Uvicorn workers), `RSS_INGESTION_ENABLED` must be set to `false` on API worker pods and enabled on a single dedicated worker to avoid duplicated network polling.

---

## 2. Configuration Inventory

### Category A: Required to Start Aegis (Mandatory)
These variables must be set for the container/process to initialize safely.

| Variable Name | Permitted Values | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | `production`, `staging`, `development`, `test` | `development` | Operating tier. In `production`, enforces strict origin validation and blocks mock modes. |
| `PORT` | `1024` – `65535` | `8000` | HTTP bind port for Uvicorn ASGI server. |
| `ALLOWED_ORIGIN` | Comma-separated URLs (e.g. `https://aegis.domain.com`) | `*` | In production, must be set to the explicit frontend origin. Wildcard `*` in production triggers an alert. |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` | Structured JSON log level. |

---

### Category B: Required for Selected Capabilities (Feature-Gated)
Without these, specific advanced reasoning or storage tiers degrade gracefully to their deterministic fallbacks.

| Variable Name | Purpose | Behavior When Missing |
|---|---|---|
| `GEMINI_API_KEY` | Generative reasoning, claim synthesis, and stance classification. | Falls back to deterministic rule-based consensus and factual extraction without hallucination. |
| `GEMINI_API_KEY_2`, `_3` | High-throughput round-robin model rotation. | Single primary key used without failover rotation. |
| `SUPABASE_URL` | Cloud PostgreSQL persistence for claims and evidence. | Automatically and safely falls back to local SQLite database (`aegis_local.db`). |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service-level access for mutations. | Local SQLite persistence used. |
| `APIFY_TOKEN` | Paparazzi direct actor scraping for Trending. | Direct Apify calls skipped; public Google News and RSS wire discovery utilized. |
| `YF_API_KEY` | Enhanced Yahoo Finance financial quotes for Scout. | Standard zero-cost Yahoo Finance endpoints utilized. |
| `GITHUB_TOKEN` | Authenticated GitHub REST queries (increases rate limits). | Public unauthenticated rate limits apply (60 req/hr). |

---

### Category C: Optional Third-Party Social Cookies & Mirror Flags
Used only if the operator has explicit authorization to query restricted platforms.

| Variable Name | Purpose | Default | Note |
|---|---|---|---|
| `REDDIT_APPROVED_ACCESS` | Acknowledges operator policy approval for Reddit queries. | `false` | When `false`, Reddit direct actions remain policy-blocked (`POLICY_BLOCKED`). |
| `RSS_INGESTION_ENABLED` | Starts background RSS wire ingestion loop. | `true` | Set to `false` in multi-worker pods to avoid duplicate polling. |
| `LINKEDIN_COOKIE` | Optional session cookie for LinkedIn profile extraction. | `""` | Reports `AUTH_REQUIRED` if unset. |
| `XUEQIU_COOKIE` | Optional session cookie for Xueqiu Asian market intelligence. | `""` | Reports `AUTH_REQUIRED` if unset. |
| `TWILIO_ACCOUNT_SID` | Optional SMS alerting for critical VIP threat triggers. | `""` | Alerts logged to database only if unset. |

---

### Category D: Strictly Forbidden or Unsafe in Production

| Configuration Pattern | Threat / Risk | Enforced Guardrail |
|---|---|---|
| `AEGIS_MOCK_LLM=true` in `ENVIRONMENT=production` | Generates fake/mock LLM evidence in production. | **BLOCKED**: Startup validator raises `ValidationError`. |
| `ALLOWED_ORIGIN=*` with credentials in production | Exposes session cookies and credentials to arbitrary websites. | **BLOCKED**: `CORSMiddleware` forces `allow_credentials=False` if `*` is present; logs security alert. |
| Hardcoded API keys in `.env` committed to Git | Credential compromise. | **BLOCKED**: `.dockerignore` and `.gitignore` exclude `.env` files. |
| Exposing SQLite database publicly via static mount | Database leakage. | **BLOCKED**: Static file handler only serves `frontend/` directory with strict path traversal checking. |
| Running background RSS loop on 10 Uvicorn workers | 10x duplicate requests to RSS wire endpoints. | **PREVENTED**: Documented runbook instructs setting `RSS_INGESTION_ENABLED=false` on multi-worker pods. |
