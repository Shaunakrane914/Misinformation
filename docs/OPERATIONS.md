# Operations

## Local configuration

Use Python 3.11 or later and install `requirements.txt`. Copy `.env.example` to
an untracked `.env`. The example lists supported settings; placeholder values are
not valid credentials. Local SQLite operation is available without a Supabase account.

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

`ENVIRONMENT`, `PORT`, `ALLOWED_ORIGIN` and `ADMIN_API_TOKEN` control deployment
behavior. Restrict production origins and protect administrative operations.
Never configure `AEGIS_MOCK_LLM=true` in production. Offline fixtures are for tests.

Configure model keys only for providers you intend to call. Advisory features
have explicit enable flags and policy budgets; do not rotate credentials or reset
ledgers to evade quotas. A failed provider is not permission to fabricate evidence.

SEC public data does not require an API key. Its route requires a real approved
`SEC_USER_AGENT` contact. Source-specific credentials, review records and approval
flags remain necessary where the source requires them. Empty credentials and
unreviewed publishers must remain unavailable.

## Deployment

- `Dockerfile` builds the FastAPI application; `render.yaml` describes Render setup.
- The static `frontend/` can be served by FastAPI or uploaded to Cloudflare Pages.
- The current Cloudflare project uses direct uploads. A Git push alone does not
  establish that its frontend matches the backend release.
- Check `/api/healthz`, `/api/readyz` and `/api/system/deployment-status`; record
  actual revision and readiness observations before calling a release verified.

Provider timeouts, denied access and empty research outcomes need separate diagnosis.
Inspect candidate, read, body, qualified-source and passage counts rather than only
HTTP status or total text length. Do not bypass a 401/403/429 using another reader.

## Validation and data

```bash
python scripts/validate_release_candidate_smoke.py
python scripts/validate_rollback_compatibility.py
```

These validators use isolated offline storage. They do not prove live provider
health or deployed rollback. Back up local SQLite/dossiers separately and inspect
historical archive integrity explicitly. Keep runtime records, generated reports
and screenshots outside tracked source. See [testing](TESTING.md).
