# Environment setup and credential boundaries

Maintained against `abe547f` on 2026-10-14. This documents repository behavior, not provider pricing, quotas or permission to purchase/configure production services.

## Safe setup

1. Inspect [current state](../CURRENT_STATE.md) and the [configuration matrix](../operations/PRODUCTION_CONFIGURATION_MATRIX.md).
2. Inspect `.env.example`, not another user's private `.env`. Copy the template only when `.env` is absent.
3. Put credentials only in approved server-side settings or a secret manager. Never commit them, embed them in browser JavaScript, paste them into logs, or include them in URLs.
4. Restart the process after changing configuration: [settings](../../backend/core/settings.py) are cached. Check liveness/readiness and the actual relevant operation outcome, not merely disappearance of a startup warning.
5. Keep test persistence separate from historical evidence.

## Modes

| Mode | Behavior |
|---|---|
| Development with no provider keys | Application can start, uses persistent SQLite when Supabase server credentials are unavailable, and reports missing provider/model capability or qualified fallback. No automatic fabricated live evidence. |
| Explicit offline tests | Fixtures/validators select test mode, disable live network, use temporary storage and explicit synthetic LLM mocks. Outputs are not real investigations. |
| Live audit | Audit scripts explicitly allow network, disable mocks and use temporary persistence/new output directories. Missing keys remain disclosed. |
| Production | Mock LLM mode is forbidden. Startup or readiness does not establish provider health, authorization or research accuracy. Deployment remains outside the current task's authority. |

`ENVIRONMENT=test`/`testing` are test tiers; never label their mock results live or production. Do not switch to production merely to bypass a test warning.

## Variables by capability

| Variable | Purpose / missing behavior |
|---|---|
| `GEMINI_API_KEY`, `GEMINI_API_KEY_*`, `GEMINI_KEY_*` | Server-side inference credentials. No key means live inference is unavailable; deterministic agent fallback and explicit failures do not become verified conclusions. Configured model IDs must also be supported by the authorized provider. |
| `AEGIS_MOCK_LLM` | Explicit test/development synthetic mode; forbidden with production. |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | Server persistence. Legacy `SUPABASE_KEY` is supported; an anonymous key is not a server write credential. |
| `SQLITE_DB_PATH` | Persistent local database filename. `AEGIS_SQLITE_PATH` is a compatibility alias. Blank or `:memory:` paths are rejected. |
| `AEGIS_DOSSIER_DIR` | Dossier storage override for isolated tests/approved deployment storage. Never overwrite historical dossiers. |
| `ADMIN_API_TOKEN` | Server-side bearer authorization for the operator-guarded response action. Missing configuration yields 503; missing/invalid caller authorization yields 401. It is not a public-browser credential or blanket authorization for every route. |
| `SEC_USER_AGENT` | Owner-approved organization/contact for real SEC requests. Missing value returns CONFIG_REQUIRED without traffic; do not invent a contact. |
| `GOOGLE_FACTCHECK_API_KEY` | Authorized FactCheck key. Missing value returns AUTH_REQUIRED without traffic. Key is sent in a header; results are publisher-attributed metadata. |
| `GITHUB_TOKEN`, `YOUTUBE_API_KEY`, authorized native tool credentials | Enable selected operations/limits where implemented. Presence alone does not prove eligibility or healthy acquisition. |
| `APIFY_TOKEN`, `YF_API_KEY` | Optional specialist acquisition/telemetry enhancements. No guarantee of unrestricted scraping or real-time financial data. |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` | Notification configuration. Do not enable live notifications while testing or assume current task authorization. |
| `RSS_INGESTION_ENABLED` | Background RSS worker setting. Disable in tests and avoid duplicating polling across API workers. |
| `ALLOWED_ORIGIN` | CORS origin configuration. Production wildcard handling is documented in the matrix; it is not a credential/authentication policy. |

This is a selected inventory. Actual [settings](../../backend/core/settings.py), [runtime operation policy](../../backend/services/agent_reach/native/operation_capabilities.py) and adapter code govern behavior; not every adapter-specific variable is a Pydantic setting.

## Troubleshooting

- **Wrong checkout imported:** use this worktree's environment and root; inspect the module path without dumping credentials.
- **Data disappears after restart:** check the selected persistent file path/volume and permissions; do not replace a protected database to “fix” it.
- **AUTH_REQUIRED or CONFIG_REQUIRED:** inspect the exact operation's documented requirement, not a generic channel label. Never bypass restrictions.
- **RATE_LIMITED / timeout:** honor provider cooldowns and bounded retries. Multiple keys are not authorization to evade limits.
- **No evidence/model output:** missing credentials and sparse public coverage are legitimate limitations; return uncertainty, not cached fake proof.
- **Previously committed secret:** removing it from a working file does not revoke it. Follow owner-led credential rotation/remediation; do not rewrite Git history or expose it here.

Provider enrollment, costs and quotas must be checked against the provider's current official documentation by the owner. This guide deliberately does not repeat obsolete free-tier or monthly-price estimates.
