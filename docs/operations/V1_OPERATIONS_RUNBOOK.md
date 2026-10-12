# Aegis v1 operations runbook

## Scope and probes

- Liveness: `GET /api/healthz` or `GET /health`.
- Readiness: `GET /api/readyz`. `READY_UNVERIFIED` means the process can accept requests but no fresh provider success is proven.
- Detailed capability state: `GET /api/agent-reach/capabilities`.
- Diagnostics: `GET /api/agent-reach/doctor`.

Operation status, not a channel-wide green flag, is authoritative. Direct content, metadata, syndication, and search-index discovery are distinct.

## Configuration

Use `.env.example` as the inventory. Set `ENVIRONMENT=production`, an explicit `ALLOWED_ORIGIN`, and `LOG_LEVEL=INFO` in production. Gemini and persistence credentials are optional; missing keys must produce an unavailable/partial state, never live-looking mock evidence. Provider cookies/session values are optional and operation-specific. `REDDIT_APPROVED_ACCESS` stays false unless the operator has approved provider access.

Set `RSS_INGESTION_ENABLED=false` for API-only workers or when a single designated worker owns polling. With multiple workers, in-memory runtime health is worker-local and background RSS must not be duplicated accidentally.

Use `SQLITE_DB_PATH` for local persistence (legacy `AEGIS_SQLITE_PATH` remains an alias), `SUPABASE_SERVICE_ROLE_KEY` for explicit cloud server writes, and `AEGIS_DOSSIER_DIR` when configuring dossier storage. Defaults retain existing historical storage without moving or overwriting it. Set server-only `ADMIN_API_TOKEN` before using privileged response-deployment writes; absent configuration returns 503 and invalid bearer authorization returns 401. Never put this token in frontend JavaScript.

Public agent scans execute blocking work in worker threads rather than on the event loop. Each agent permits one synchronous scan at a time; simultaneous requests for the same agent fail fast with HTTP 429 and `Retry-After: 3`, without building an unbounded queue. Worker-local state and scan admission do not converge across multiple processes.

Dashboard records marked `record_origin=historical_dataset` are historical top-ups, not newly acquired/live findings. Investigation records use `record_origin=investigation`. Registered module counts and `NOT_PROBED` initialization status are not successful health measurements.

## Offline acceptance checks

`pytest tests/ -q` uses temporary storage, blank provider credentials and blocked real sockets/DNS before application imports. `python scripts/validate_release_candidate_smoke.py` is an isolated offline regression check, not a live scraping/deployment approval. It never overwrites historical artifacts; optional `--output <new-path>` creates a report exclusively.

`python scripts/validate_rollback_compatibility.py` validates fresh-process persistence, actual baseline readers and read-only dossier JSON integrity. It currently reports a historical archive failure for malformed pre-existing JSON; see [rollback verification](ROLLBACK_VERIFICATION.md). Protect these files and recover only with explicit owner direction and trustworthy backups.

## Expected partial failures

- 429: operation becomes temporarily deferred for the bounded provider cooldown.
- 401/auth failure: no retry; show authentication required where applicable.
- 403/policy failure: no transport retry; a permitted web-render rescue may occur only for the web reader.
- Empty 200: no evidence success.
- Metadata or index-only result: limited, not healthy direct content.
- External-tool transport: HTTP status may be unknown.

## Rollback

1. Stop accepting new investigations.
2. Revert the Phase 7 commits in reverse order on the working branch; do not alter frozen datasets or stored dossiers.
3. Restart one process and verify `/api/healthz`, `/api/readyz`, the 16-operation contract suite, and one deterministic four-agent integration run.
4. Preserve the failed run’s logs, commit SHA, query records, and evidence lineage. Do not deploy automatically.

