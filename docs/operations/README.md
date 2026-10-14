# Aegis Protocol — Operations, Deployment & Runtime Runbook

**Document Version**: 4.1.0  
**Environment**: Production Docker / Cloud Run / Kubernetes / Local Workstation

---

## 1. System Topology & Operational Architecture

Aegis Protocol operates as a resilient modular monolith designed for zero-downtime execution and graceful degradation:

```
                      ┌──────────────────────┐
                      │    Reverse Proxy     │
                      │   (Caddy / Nginx)    │
                      └──────────┬───────────┘
                                 │ :8000
                                 ▼
                      ┌──────────────────────┐
                      │   Uvicorn / FastAPI  │
                      │    Aegis Protocol    │
                      └─────┬──────────┬─────┘
                            │          │
         ┌──────────────────┴──┐    ┌──┴──────────────────┐
         ▼                     ▼    ▼                     ▼
┌──────────────────┐ ┌────────────┐ ┌─────────────┐ ┌───────────────┐
│ Primary Database │ │ In-Memory  │ │ Live Gemini │ │ Offline Mock  │
│ Supabase / PG    │ │ SQLite     │ │ API Keys    │ │ Provider      │
│ (Active Mode)    │ │ (Fallback) │ │ (Key Cycle) │ │ (Zero-Crash)  │
└──────────────────┘ └────────────┘ └─────────────┘ └───────────────┘
```

---

## 2. Configuration Reference

All settings are resolved from system environment variables or local `.env`:

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `PORT` | Integer | `8000` | Port on which the HTTP server listens. |
| `HOST` | String | `0.0.0.0` | Bind host address. |
| `LOG_LEVEL` | String | `INFO` | Standard logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `GEMINI_API_KEY` | String | `None` | Primary Google Gemini API key. |
| `GEMINI_API_KEY_1`, `_2`, `_3` | String | `None` | Secondary keys for automatic key rotation on HTTP 429 quota exhaustion. |
| `AEGIS_MOCK_LLM` | Boolean | `false` | When `true`, all reasoning pipelines utilize deterministic offline mocks. |
| `SUPABASE_URL` | String | `None` | Supabase / PostgreSQL endpoint. |
| `SUPABASE_SERVICE_ROLE_KEY` | String | `None` | Elevated service role key for database operations. |
| `DASHBOARD_TTL` | Integer | `300` | In-memory stats cache time-to-live in seconds. |

---

## 3. Docker Container Deployment

### Container Hygiene & `.dockerignore`
Aegis Protocol enforces strict build context isolation via [`.dockerignore`](../../.dockerignore). The following sensitive and heavy artifacts are excluded from images:
- `.env`, `.env.*` (Secrets and credentials)
- `research/` (~338 MB ungrounded exploratory materials)
- `docs/visual-audit/` (~31 MB high-resolution visual regression frames)
- `aegis_local.db` (~17.6 MB local developer database)
- `.git`, `__pycache__`, `.pytest_cache`, `.venv`

### Docker Build & Run
```bash
# Build the production container
docker build -t aegis-protocol:latest .

# Run the container with environment variables
docker run -d \
  -p 8000:8000 \
  -e GEMINI_API_KEY="AIzaSy..." \
  -e LOG_LEVEL="INFO" \
  --name aegis-app \
  aegis-protocol:latest
```

---

## 4. Health Probes & Monitoring

Aegis Protocol provides dedicated probes for Kubernetes and container orchestrators:

### 1. Liveness Probe (`GET /healthz`)
- **Purpose**: Verifies the HTTP process is responsive.
- **Success Response**: `HTTP 200 OK`
```json
{
  "status": "ok",
  "version": "4.1.0",
  "timestamp": "2026-10-09T21:40:00Z"
}
```

### 2. Readiness Probe (`GET /api/healthz`)
- **Purpose**: Verifies database connectivity, memory pressure, and channel availability.
- **Success Response**: `HTTP 200 OK`
```json
{
  "status": "healthy",
  "database": "connected",
  "llm_gateway": "ready",
  "active_channels": 14
}
```

---

## 5. Fault Tolerance & Recovery Runbook

1. **Database Unreachable**:
   - *Behavior*: Aegis Protocol logs a warning and falls back to an in-memory SQLite store (`backend/db/database.py`).
   - *Action*: Inspect `SUPABASE_URL` and firewall egress; claims written to memory will not persist across process restarts.
2. **Gemini API Rate Limiting (HTTP 429)**:
   - *Behavior*: `GeminiService` engages jittered exponential backoff and cycles to the next configured backup key.
   - *Action*: Supply additional backup keys (`GEMINI_API_KEY_1`, `_2`) in production `.env`.
3. **SSRF Attempt Detected**:
   - *Behavior*: Inbound URL is rejected with HTTP 400 and logged to security telemetry.
   - *Action*: No operational intervention required; defenses are automated.
