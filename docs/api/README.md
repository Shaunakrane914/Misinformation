# Aegis Protocol — API Specification & Routing Reference

**Document Version**: 4.1.0  
**Framework**: FastAPI 0.110+  
**Interactive Documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 1. Overview & Architecture

Aegis Protocol decomposes its REST interface into 7 modular sub-routers mounted to the root application in `backend/main.py`:

```
backend/api/
├── claims.py         # /api/claims/*      (Claim submission, status, verification, statistics)
├── scout.py          # /api/scout/*       (Financial anomaly scanner, Yahoo Finance feeds)
├── trending.py       # /api/trending/*    (Viral trend emergence, multi-channel RSS)
├── brandshield.py    # /api/brandshield/* (Brand threat cards, astroturfing detection)
├── personal.py       # /api/personal/*    (Executive identity defense, smear monitoring)
├── replay.py         # /api/replay/*      (Cryptographic replay ledger, provenance chains)
└── healthz.py        # /healthz, /api/*   (Liveness, readiness, system capability telemetry)
```

---

## 2. Router Specifications

### 1. Claims Router (`/api/claims`)
Handles claim ingestion, normalization, background verification, and truth dossier generation.

| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/claims/submit` | Submit claim for autonomous verification. Runs Unicode NFC normalization, SHA-256 deduplication, and queues verification task. | `ClaimSubmissionRequest` (`claim_text`, `source_url`, `context`) | `ClaimSubmissionResponse` (`claim_id`, `status`, `created_at`) |
| `GET` | `/api/claims/{claim_id}` | Retrieve claim status, forensic findings, and verdict dossier. | Path param: `claim_id` (UUID / SHA-256) | `ClaimDetailResponse` (includes `TruthDossier` and `UnifiedReport`) |
| `GET` | `/api/claims/` | Paginated list of ingested claims with verdict badges and confidence scores. | Query params: `page`, `limit`, `status` | `List[ClaimSummary]` |
| `GET` | `/api/claims/dashboard/stats` | Aggregated verification statistics (total claims, verdict distribution, average confidence). | None | `DashboardStatsResponse` |
| `POST` | `/api/claims/verify` | Direct synchronous verification with linguistic telemetry and Zipf-Mandelbrot fit. | `ClaimVerificationRequest` | `ClaimVerificationResponse` |

---

### 2. Scout Financial Router (`/api/scout`)
Coordinates financial intelligence, price anomaly correlation, and market rumour deconstruction.

| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/scout/analyze` | Scan financial ticker or rumour against real-time price feeds, SEC filings, and volume z-scores. | `ScoutAnalysisRequest` (`ticker`, `query`, `timeframe`) | `ScoutAnalysisResponse` (market telemetry, catalysts, anomalies) |
| `GET` | `/api/scout/catalysts` | Retrieve active market catalysts and correlated news narratives. | Query params: `ticker`, `limit` | `List[MarketCatalyst]` |

---

### 3. Trending Viral Router (`/api/trending`)
Monitors viral narratives, topic emergence, and velocity across multi-channel RSS feeds and social mirrors.

| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/trending/scan` | Execute discovery scan across RSS wires and zero-auth social channels. | `TrendingScanRequest` (`query`, `categories`, `threshold`) | `TrendingScanResponse` (narrative clusters, velocity metrics) |
| `GET` | `/api/trending/velocity` | Temporal velocity estimates and 48-hour freshness audit for trending claims. | Query params: `topic_id` | `VelocityReport` |

---

### 4. BrandShield Router (`/api/brandshield`)
Audits corporate brand reputation, counterfeit listings, coordinated astroturfing, and smear campaigns.

| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/brandshield/audit` | Comprehensive brand threat audit producing 4-question threat cards. | `BrandAuditRequest` (`brand_name`, `domains`, `channels`) | `BrandAuditResponse` (threat cards, counterfeit score) |
| `GET` | `/api/brandshield/threats` | Active threat alerts, review brigading indicators, and sentiment shifts. | Query params: `brand_name` | `List[BrandThreat]` |

---

### 5. Personal Watch Router (`/api/personal`)
Monitors public figures and executives for impersonation, deepfakes, and identity-targeted disinformation.

| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/personal/scan` | Scan OSINT news and public channels for identity threats against an executive profile. | `PersonalScanRequest` (`target_name`, `role`, `affiliations`) | `PersonalScanResponse` (identity diffs, threat severity) |
| `GET` | `/api/personal/alerts` | Active high-priority alerts with evidence provenance links. | Query params: `target_name`, `severity` | `List[PersonalAlert]` |

---

### 6. Replay Ledger Router (`/api/replay`)
Inspects immutable cryptographic provenance chains ensuring claim verification decisions are 100% reproducible.

| Method | Endpoint | Description | Request Body / Params | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/replay/{claim_id}` | Retrieve the full cryptographic Replay Ledger trace for an investigation. | Path param: `claim_id` | `ReplayLedgerRecord` (SHA-256 evidence hashes, pipeline stages) |
| `POST` | `/api/replay/verify` | Verify the SHA-256 hash integrity of an external dossier against the ledger. | `ReplayVerifyRequest` (`dossier_hash`, `claim_id`) | `ReplayVerifyResponse` (`valid: bool`, `chain_integrity`) |

---

### 7. Health & Telemetry Router (`/healthz`, `/api/healthz`)
Exposes liveness, readiness, and capability health checks.

| Method | Endpoint | Description | Response Schema |
| :--- | :--- | :--- | :--- |
| `GET` | `/healthz` | Lightweight Kubernetes / container liveness probe. | `{"status": "ok", "version": "4.1.0", "timestamp": "..."}` |
| `GET` | `/api/healthz` | Readiness probe verifying database connectivity, LLM gateway status, and channel registry. | `{"status": "healthy", "database": "active", "agents": 5}` |
| `GET` | `/api/capabilities` | Active 14-channel capability registry status and health metrics. | `List[CapabilityChannelStatus]` |

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
All 5 domain agents produce standard `UnifiedReport` outputs (`backend/schemas/unified_report.py`) containing:
- `_meta`: Schema version (`3.8.0`), agent identifier, query string, timestamp.
- `summary`: Markdown summary of findings and definitive verdict.
- `findings`: List of empirical factual points.
- `evidence`: Categorized evidence items (`primary`, `independent`, `community`, `contextual`).
- `trust`: Quality tensor (`relevance`, `independence`, `freshness`, `contradiction`) and query execution telemetry.
