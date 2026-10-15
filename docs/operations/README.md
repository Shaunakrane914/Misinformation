# Operations and runtime boundaries

Maintained against `abe547f` on 2026-10-14. **No production deployment or merge is authorized.** Use [current state](../CURRENT_STATE.md), [configuration](PRODUCTION_CONFIGURATION_MATRIX.md), [security](../security/README.md) and [rollback limits](ROLLBACK_VERIFICATION.md).

## Topology and persistence

FastAPI serves the API and static frontend. Specialist scans and claim verification share acquisition/research services, with optional authorized external providers. Persistence uses configured Supabase server credentials or **file-backed SQLite**, not an automatic in-memory demo. Dossiers have separate storage and integrity checks.

The [Dockerfile](../../Dockerfile) describes a Python 3.13 multi-stage, non-root container. It does not prove a zero-downtime, Kubernetes, Cloud Run or production deployment has been tested. [.dockerignore](../../.dockerignore) excludes environment secrets, local databases, research/artifact trees and workspace caches from build context; inspect the current rules rather than old disk-size estimates.

A deployment owner must explicitly choose writable database/dossier paths, mount durable storage, protect secrets, establish external access policy and prove reload/rollback. Do not copy local historical dossiers into a new image as a recovery strategy.

## Diagnostic checks

From the intended worktree, local-only startup is:

```text
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

| Read-only endpoint | Meaning |
|---|---|
| `GET /api/healthz` (alias `/healthz`) | Process liveness; not model/provider or evidence-quality acceptance. |
| `GET /api/readyz` (alias `/readyz`) | Runtime readiness observations; READY_UNVERIFIED is not healthy live providers. |
| `GET /api/agent-reach/capabilities` | Registry/operation inventory and current policy observations; registration is not successful acquisition. |
| `GET /api/agent-reach/doctor` | Diagnostic snapshot, not a universal connectivity certificate. |
| `GET /api/system/deployment-status` | Deployment/runtime observations; not authorization to launch. |

See [route map](../api/CURRENT_ENDPOINTS.md) and running OpenAPI for exact response fields. Do not copy old sample JSON into monitoring assertions.

## Operating safely

- Missing model credentials do not silently enable production mocks. Authorized live inference and deterministic fallback are different execution modes.
- Keep ADMIN_API_TOKEN and provider keys server-side. Missing operator configuration is 503; unauthenticated/invalid bearer calls to the guarded action are 401. Do not send a test response action or notification as a health check.
- Per-agent admission protects shared mutable state within a process; busy scans can return 429. It is not a distributed queue/lock or concurrency SLA.
- Honor operation-level authentication, capability policy and cooldowns. SEC needs an owner contact; FactCheck needs an authorized key.
- Network operations have bounded attempts/body/decode sizes. A per-attempt timeout is not an end-to-end API latency promise; some native extractor routes and auxiliary quote requests take longer.
- Run background RSS once in an approved worker, not independently in every API process.
- A safe URL, an official domain and a dossier hash are not proof that a factual claim is true.

## Incident and recovery triage

| Symptom | Safe response |
|---|---|
| Database unavailable / unexpected persistence path | Check selected backend, server credentials, file/volume permissions and reload evidence. Do not delete, silently relocate or overwrite data. |
| Corrupt or hash-invalid dossier | Preserve original bytes; record path/hash/error in a new read-only inventory; keep it out of verified conclusions. |
| Sparse evidence / unavailable source | Preserve coverage/failure telemetry and abstain. Do not generate filler evidence or label execution PASS as research PASS. |
| Rate limit / timeout | Keep the failure class and cooldown, reduce scoped work and respect provider restrictions. |
| Suspected source spoofing / XSS / injected instructions | Retain sanitized diagnostic context, run focused security regressions and review the relevant boundary. Passing a regex trap is not online model-injection proof. |
| Rollback needed | Use an owner-controlled staging exercise and the [rollback verification contract](ROLLBACK_VERIFICATION.md); current offline reader checks do not prove deployed rollback. |

The prior original-worktree inventory reported 55 malformed historical dossiers; this isolated worktree does not establish their repair or current archive count. Historical originals, frozen benchmark data and old proof must remain intact.

## Validation and release gate

Run [offline checks](../testing/README.md); independently authorize any live audits and use new output directories. Hosted [CI evidence](../handoffs/2026-10-14_PHASE8_INDEPENDENT_CI_CLOSEOUT.md) proves only its exact observed commit and configured jobs.

Release remains blocked on externally adjudicated research quality, claim-relevant coverage, authorized provider/model checks, evidence-rich manual accessibility/usability, historical-integrity disclosure and staging rollback. This guide describes operational preparation; it does not authorize or certify a launch.
