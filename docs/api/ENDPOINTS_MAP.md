# Aegis Enterprise - Complete API & Endpoint Map

## 🌐 Server Base URL: `http://127.0.0.1:8000` (Swagger UI: `http://127.0.0.1:8000/docs`)

---

## 🖥️ Frontend Routes

### Main Applications & Dashboards
- `GET /` → Home page (`index.html`)
- `GET /dashboard` → Live telemetry dashboard with real-time claims feed (`dashboard.html`)
- `GET /about` → Architecture & methodology explanation with interactive pipeline simulator (`about.html`)
- `GET /submit` → High-fidelity claim verification interface with multi-tier fallback and social radar (`submit.html`)
- `GET /agents` → Unified 7-Agent Command Center with dedicated cards and live telemetry (`agents.html`)
- `GET /status` → Cluster health, nodes, and worker telemetry (`status.html`)
- `GET /threat-intel` → Threat Intelligence Lab instruments & Hawkes contagion monitor (`threat-intel.html`)

### Specialized Agent Interfaces
- `GET /scout-agent` → Scout Sentinel (Financial market manipulation & volatility watchdog)
- `GET /trending-agent` → Trend Pulse Sentinel (Viral memetic spread & velocity tracker)
- `GET /brandshield-agent` → BrandShield Sentinel (Corporate brand disparagement & PR smear defense)
- `GET /personal-watch-agent` → Personal Watch Sentinel (VIP impersonation, deepfake detection & defamation monitoring)

---

## ⚡ Backend API Routes (FastAPI v3.5.0)

### System & Health Telemetry
- `GET /api/` → API system info, version, and active agents manifest
- `GET /api/healthz` → Live cluster health, uptime, and database connection status
- `GET /docs` → Interactive OpenAPI / Swagger UI documentation
- `GET /redoc` → ReDoc API reference documentation

### Autonomous 7-Agent Fleet Endpoints
- `POST /api/agents/scout/scan` → Execute market anomaly and ticker manipulation scan
- `POST /api/agents/trending/scan` → Detect virality velocity and synthetic amplification
- `POST /api/agents/brandshield/scan` → Execute brand smear and sentiment volatility analysis
- `POST /api/agents/personal/scan` → Detect VIP impersonation, deepfakes, and defamation
- `POST /api/agents/research/query` → Retrieve cross-referenced empirical evidence from scientific sources
- `POST /api/agents/adversary/analyze` → Run counter-adversarial deconstruction and coordinated campaign attribution
- `POST /api/agents/coordinator/orchestrate` → Multi-agent ensemble debate, byzantine consensus, and synthesis

### Agent Reach Internet Evidence-Acquisition Layer
- `GET /api/agent-reach/capabilities` → Channel capability inventory, supported domains, and server compatibility
- `GET /api/agent-reach/health` → Live probe health across all 14 channels (healthy, degraded, auth_required, unavailable)
- `GET /api/agent-reach/doctor` → Legacy zero-cost scraper diagnostic probe
- `POST /api/agent-reach/omni-scan` → Domain-directed multi-channel retrieval pass with provenance, deduplication, and syndication clustering
- `POST /api/agent-reach/read` → SSRF-protected clean markdown parsing of web documents
- `POST /api/agent-reach/scan` → Unified cross-platform scan across news, Reddit, Twitter/X, and YouTube


### Deep Verification & Truth Dossier
- `POST /api/verify/truth-dossier` → Full synchronous Truth Dossier report with multi-agent consensus
- `POST /api/claims/submit` → Async claim submission for pipeline queuing
- `GET /api/claims/{claim_id}` → Query claim verification progress and verdicts
- `GET /api/claims` → List all processed claims with pagination and verdict filters

### War Room & Crisis Mitigation
- `GET /api/war-room/signals` → Active systemic crash signals and coordinated attack alerts
- `GET /api/feed/live` → Real-time stream of verified digital threats
- `POST /api/deploy-response` → Issue defensive counter-narratives and verified rebuttal packages
