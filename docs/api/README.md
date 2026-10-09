# Aegis Protocol — API Specification & Routing Reference

**Document Version**: 4.1.0  
**Framework**: FastAPI 0.110+  
**Interactive Documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Overview & Architecture

Aegis Protocol decomposes its REST interface into 6 modular sub-routers in `backend/api/`, assembled in `backend/api/__init__.py` and mounted to the application in `backend/main.py`:

```
backend/api/
├── claims.py         # /api/claims/*       (Claim submission, status, verification, statistics)
├── agents.py         # /api/scout/*, /api/trending/*, /api/brandshield/*, /api/personal/*, /api/warroom/*
├── agent_reach.py    # /api/agent-reach/*  (Channel capability discovery, query execution telemetry)
├── threat_lab.py     # /api/threat-lab/*   (Zipf-Mandelbrot fit, Hawkes point-process, consensus)
├── replay.py         # /api/replay/*       (Cryptographic replay ledger, provenance chains)
└── system.py         # /healthz, /api/healthz, /api/system/*, /api/capabilities (Liveness & telemetry)
```

---

## 2. Router Specifications

### 1. Claims Router (`backend/api/claims.py` → `/api/claims`)
Handles claim ingestion, normalization, background verification, and truth dossier generation.

| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/claims/submit` | Submit claim for autonomous verification. Runs Unicode NFC normalization, SHA-256 deduplication, and queues verification task. | `ClaimSubmissionRequest` (`claim_text`, `source_url`, `context`) | `ClaimSubmissionResponse` (`claim_id`, `status`, `created_at`) |
| `GET` | `/api/claims/{claim_id}` | Retrieve claim status, forensic findings, and verdict dossier. | Path param: `claim_id` (UUID / SHA-256) | `ClaimDetailResponse` (includes `TruthDossier` and `UnifiedReport`) |
| `GET` | `/api/claims/` | Paginated list of ingested claims with verdict badges and confidence scores. | Query params: `page`, `limit`, `status` | `List[ClaimSummary]` |
| `GET` | `/api/claims/dashboard/stats` | Aggregated verification statistics (total claims, verdict distribution, average confidence). | None | `DashboardStatsResponse` |
| `POST` | `/api/claims/verify` | Direct synchronous verification with linguistic telemetry and Zipf-Mandelbrot fit. | `ClaimVerificationRequest` | `ClaimVerificationResponse` |

---

### 2. Sentinel Agents Router (`backend/api/agents.py`)
Hosts specialized endpoints for the autonomous intelligence sentinels and war room incident response.

#### Scout Financial Intelligence (`/api/scout`)
| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/scout/analyze` | Scan financial ticker or rumour against real-time price feeds, SEC filings, and volume z-scores. | `ScoutAnalysisRequest` (`ticker`, `query`, `timeframe`) | `ScoutAnalysisResponse` (market telemetry, catalysts, anomalies) |
| `GET` | `/api/scout/catalysts` | Retrieve active market catalysts and correlated news narratives. | Query params: `ticker`, `limit` | `List[MarketCatalyst]` |

#### Trending Viral Monitor (`/api/trending`)
| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/trending/scan` | Execute discovery scan across RSS wires and zero-auth social channels. | `TrendingScanRequest` (`query`, `categories`, `threshold`) | `TrendingScanResponse` (narrative clusters, velocity metrics) |
| `GET` | `/api/trending/velocity` | Temporal velocity estimates and 48-hour freshness audit for trending claims. | Query params: `topic_id` | `VelocityReport` |

#### BrandShield Asset Protection (`/api/brandshield`)
| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/brandshield/audit` | Comprehensive brand threat audit producing 4-question threat cards. | `BrandAuditRequest` (`brand_name`, `domains`, `channels`) | `BrandAuditResponse` (threat cards, counterfeit score) |
| `GET` | `/api/brandshield/threats` | Active threat alerts, review brigading indicators, and sentiment shifts. | Query params: `brand_name` | `List[BrandThreat]` |

#### Personal Watch Identity Audit (`/api/personal`)
| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/personal/scan` | Scan OSINT news and public channels for identity threats against an executive profile. | `PersonalScanRequest` (`target_name`, `role`, `affiliations`) | `PersonalScanResponse` (identity diffs, threat severity) |
| `GET` | `/api/personal/alerts` | Active high-priority alerts with evidence provenance links. | Query params: `target_name`, `severity` | `List[PersonalAlert]` |

#### War Room Incident Response (`/api/warroom`)
| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/warroom/signals` | Live incident response threat feeds and high-velocity alerts. | None | `WarRoomSignalsResponse` |
| `POST` | `/api/warroom/countermeasure` | Generate actionable mitigation response for high-severity narrative crisis. | `CountermeasureRequest` | `CountermeasureResponse` |

---

### 3. Agent Reach Router (`backend/api/agent_reach.py` → `/api/agent-reach`)
Exposes shared acquisition capabilities, live channel registry, and extraction telemetry.

| Method | Endpoint | Description | Response Schema |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/agent-reach/capabilities` | Health status and latency for all 14 capability channels. | `CapabilityRegistryStatus` |
| `POST` | `/api/agent-reach/retrieve` | Direct test retrieval through the acquisition routing fabric. | `RetrievalResponse` |

---

### 4. Replay Ledger Router (`backend/api/replay.py` → `/api/replay`)
Inspects immutable cryptographic provenance chains ensuring claim verification decisions are 100% reproducible.

| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/replay/{claim_id}` | Retrieve the full cryptographic Replay Ledger trace for an investigation. | Path param: `claim_id` | `ReplayLedgerRecord` (SHA-256 evidence hashes, pipeline stages) |
| `POST` | `/api/replay/verify` | Verify the SHA-256 hash integrity of an external dossier against the ledger. | `ReplayVerifyRequest` (`dossier_hash`, `claim_id`) | `ReplayVerifyResponse` (`valid: bool`, `chain_integrity`) |

---

### 5. Threat Lab Router (`backend/api/threat_lab.py` → `/api/threat-lab`)
Exposes physics-based threat instruments, power-law regression, and swarm consensus simulations.

| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/threat-lab/mandelbrot` | Calculate Zipf-Mandelbrot token-rank power-law fit ($R^2$, Shannon entropy, TTR). | `MandelbrotRequest` (`text`) | `MandelbrotResponse` |
| `POST` | `/api/threat-lab/hawkes` | Simulate Hawkes point-process viral cascade propagation ($\lambda(t)$). | `HawkesRequest` (`events`) | `HawkesResponse` (`is_simulation: True`) |
| `POST` | `/api/threat-lab/consensus` | Byzantine Swarm Consensus with W-MSR outlier pruning. | `ConsensusRequest` (`node_scores`) | `ConsensusResponse` (`is_simulation: True`) |

---

### 6. System & Telemetry Router (`backend/api/system.py`)
Exposes liveness, readiness, deployment status, and system telemetry probes.

| Method | Endpoint | Description | Response Schema |
| :--- | :--- | :--- | :--- |
| `GET` | `/healthz` or `/api/healthz` | Lightweight Kubernetes / container liveness probe. | `{"status": "ok", "system": "Aegis Protocol", "version": "...", "active_agents": 7}` |
| `GET` | `/api/system/deployment-status` | Empirical deployment facts (database investigations count, supported channels). | `DeploymentStatusResponse` |
| `GET` | `/api/capabilities` | Active 14-channel capability registry status and health metrics. | `List[CapabilityChannelStatus]` |
| `GET` | `/api/system/doctor` | Comprehensive self-diagnostic verifying SQLite, Supabase, LLM, and scrapers. | `SystemDoctorResponse` |

---

## 3. Standard Request/Response Envelopes

### Standard Error Envelope
All API endpoints return consistent HTTP error envelopes adhering to RFC 7807:
```json
{
  "detail": {
    "error_code": "INVALID_URL_SCHEME",
    "message": "Only HTTP and HTTPS URLs are permitted.",
    "blocked_host": "127.0.0.1"
  }
}
```

### Unified Report Schema (v3.8.0)
All domain sentinels produce standard `UnifiedReport` outputs (`backend/schemas/unified_report.py`) containing:
- `_meta`: Schema version (`3.8.0`), agent identifier, query string, timestamp.
- `summary`: Markdown summary of findings and definitive verdict.
- `findings`: List of empirical factual points.
- `evidence`: Categorized evidence items (`primary`, `independent`, `community`, `contextual`).
- `trust`: Quality tensor (`relevance`, `independence`, `freshness`, `contradiction`) and query execution telemetry.
