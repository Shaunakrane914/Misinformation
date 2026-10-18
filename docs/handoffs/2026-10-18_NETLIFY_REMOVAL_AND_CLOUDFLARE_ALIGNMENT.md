# Netlify Removal & Cloudflare Pages Alignment — 2026-10-18

## Scope and Intent
User requested complete removal of Netlify remnants while strictly preserving Cloudflare Pages configuration, Render backend APIs, and Render compatibility routes:
1. Delete legacy Netlify function files and `netlify.toml`.
2. Remove Netlify fallback from `frontend/gemini-client.js`.
3. Update tests and documentation that depended on Netlify files.
4. Preserve Cloudflare `_headers`, `_redirects`, and Render backend compatibility endpoints (`/.netlify/functions/gemini`, `/.netlify/functions/stock`).
5. Confirm old Netlify project status and disable live project.

Worktree: `.scratch/phase9-remediation-20261016` (branch `feat/continuous-source-intelligence-20261017`) and root workspace (`feat/phase8-real-acquisition-proof`).

## Code Changes & Removals

1. **Files Removed:**
   - `netlify.toml`: Removed from repository root.
   - `frontend/netlify/functions/gemini.js`: Removed.
   - `frontend/netlify/functions/stock.js`: Removed.
   - `frontend/netlify/`: Directory pruned.

2. **Client Fallback Cleaned:**
   - [`frontend/gemini-client.js`](../../frontend/gemini-client.js): Removed `'/.netlify/functions/gemini'` fallback endpoint. Calls now route strictly to `window.getAegisApiUrl('/api/gemini') || '/api/gemini'`.

3. **Tests Aligned to Cloudflare Pages:**
   - [`tests/unit/test_frontend_operation_health_contract.py`](../../tests/unit/test_frontend_operation_health_contract.py):
     - Removed dependency on `ROOT / "netlify.toml"`.
     - Renamed test to `test_unhashed_runtime_assets_revalidate_on_cloudflare_pages`, verifying cache-control revalidation on `frontend/_headers`.
     - Renamed test to `test_cloudflare_pages_does_not_mask_missing_routes_with_successful_homepage`, verifying fallback rules on `frontend/_redirects`.
   - [`tests/frontend/test_security_and_health_regressions.js`](../../tests/frontend/test_security_and_health_regressions.js): Removed `testNetlifyProxy()` function and invocation.

4. **Documentation & Scripts Updated:**
   - [`frontend/README.md`](../../frontend/README.md): Documented Cloudflare Pages (`https://aegis-protocol-110.pages.dev/`) as the static hosting environment.
   - [`frontend/dashboard.js`](../../frontend/dashboard.js): Updated comment from Netlify to Cloudflare Pages.
   - [`backend/main.py`](../../backend/main.py): Updated liveness docstring to mention Cloudflare Pages.
   - [`backend/api/claims.py`](../../backend/api/claims.py): Updated rebuttal link to `https://aegis-protocol-110.pages.dev/submit.html`.
   - [`scripts/diagnostics/verify_live_scan.py`](../../scripts/diagnostics/verify_live_scan.py): Added `pages.dev` to monitored request URLs.

5. **Compatibility Invariant Preserved:**
   - Render backend compatibility routes (`@router.post("/.netlify/functions/gemini")` in [`backend/api/system.py`](../../backend/api/system.py#L310) and `@router.get("/.netlify/functions/stock")` in [`backend/api/agents.py`](../../backend/api/agents.py#L140)) were strictly retained.
   - Cloudflare routing configuration (`frontend/_headers`, `frontend/_redirects`) was strictly retained.

6. **Netlify Project Status & Deletion:**
   - Executed `netlify sites:list`: Found project `agenticai914-old` (`be669db1-81eb-482d-aa91-93d1d0c4d19f`) linked to `Shaunakrane914/Misinformation`.
   - Executed `netlify sites:delete -f be669db1-81eb-482d-aa91-93d1d0c4d19f`: Successfully deleted the project from Netlify. Probing `https://agenticai914-old.netlify.app` now returns HTTP 404.

## Verification & Commands Run

- `python -m pytest tests/unit tests/chaos tests/security -q`: **1,194 passed** in 26.16s.
- `python -m pytest tests/unit/test_frontend_operation_health_contract.py -q`: **9 passed** in 0.60s.
- `node tests/frontend/test_security_and_health_regressions.js`: PASSED.
- All 7 node frontend test suites: ALL PASSED.
- `flake8 backend tests scripts --count --select=E9,F63,F7,F82`: 0 errors.
- `python scripts/validate_release_candidate_smoke.py`: `OFFLINE_SMOKE_PASS`.
- `python scripts/validate_rollback_compatibility.py`: `OFFLINE_PERSISTENCE_PASS`.
- `python scripts/validation/verify_frozen_benchmarks.py`: Hashes verified.
