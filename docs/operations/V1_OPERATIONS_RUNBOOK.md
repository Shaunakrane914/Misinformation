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

