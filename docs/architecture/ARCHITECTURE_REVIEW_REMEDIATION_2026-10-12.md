# Architecture review remediation — 2026-10-12

This implementation addresses the concrete security, correctness and delivery-process defects identified in the architecture review. It is local work on `feat/phase7-2c-root-cleanup`, based on `b3f3fc8`; no commit, push or production deployment was performed. The code-reviewer and backend-security-coder checklists guided the regression and fail-closed security boundaries.

For continuation, read the [coding-agent handoff](../handoffs/README.md). Its subsequent documentation-only rerun passed all 975 full-suite cases, including the four late CLI cases; the verification table below preserves the original implementation checkpoint rather than rewriting its historical counts.

## Implemented fixes

| Area | Remediation | Behavioral evidence |
|---|---|---|
| API authorization | Both response-deployment aliases require a server-side operator bearer token; missing configuration fails closed | `tests/unit/test_api_hardening_regressions.py` |
| Frontend injection | Personal Watch names use text nodes; dashboard evidence links require HTTP(S) and DOM construction | `tests/frontend/test_security_and_health_regressions.js` |
| Public HTTP boundary | Fresh DNS answers are validated and numeric destinations pinned, retaining original Host/TLS SNI; redirects strip credentials across origins; proxy bypasses are disabled | `tests/security/test_review_security_regressions.py`, `tests/security/test_safe_http_transport.py` |
| Slow/large responses | Shared HTTP bounds body size and connection/header/body wall-clock duration; non-finite retry delays fail closed | Security regressions above |
| Unsafe fallbacks | Automatic unpinned browser/legacy-reader fallbacks cannot bypass a rejected read; structured policy/rate failures remain failures | `tests/chaos/test_agent_reach_chaos.py`, native transport tests |
| Source authority | Trust uses actual URL host boundaries and explicit corporate identity mappings, not substrings or a supplied source-domain label | Security regressions above |
| Finding status | An arbitrary original GitHub document is not automatically a known fact; unrelated results sharing a query class do not establish corroboration | Security regressions above |
| Dossier persistence | Full UUID IDs, exclusive atomic publication, exact captured text and payload checksums, defensive cache copies, and validated paths | Security regressions above |
| Replay honesty | Legacy records are unsealed, not verified; tampered/malformed records fail without walking unsafe nested structures or claiming successful checks | `tests/unit/test_replay_verification.py`, `tests/unit/test_replay_structure_regressions.py` |
| Runtime planning | Exact approved operations survive source plans; cooldown/policy decisions apply at dispatch/read boundaries; empty plans/platform lists remain exclusions | `tests/unit/test_acquisition_policy_integrity.py` |
| Evidence metadata | Profiles no longer upgrade snippets to full articles; unknown dates stay unknown; all four strategies retain enrichment and Personal Watch redaction | Acquisition profile/fabric tests |
| Retrieval budgets | Zero read budgets, configured caps and exhausted deadlines are honored; executor shutdown no longer defeats deadlines; discovery invokes the correct signatures | Acquisition policy, research reading and golden tests |
| API scheduling | Blocking calls execute in worker threads; per-agent fail-fast admission prevents singleton scan-state mixing and returns 429 with Retry-After | API hardening regressions |
| Telemetry/UI honesty | Uncertainty remains uncertainty; zero-evidence BrandShield groups remain zero; agent inventory is explicitly unprobed; health badges repaint on TTL/visibility changes | API/frontend behavioral tests |
| Provider failure | Netlify never substitutes fabricated evidence for missing/exhausted keys; requests are bounded and production mock overrides forbidden | Frontend/Netlify behavioral tests, LLM gateway tests |
| Hosting cache/routes | Unhashed JS/CSS must revalidate on both hosts; unknown Netlify routes return genuine 404s | Frontend hosting configuration regressions |
| Configuration | SQLite aliases and server Supabase credentials are centralized; unsafe empty/in-memory persistence paths fail startup; package/API/frontend version aligned to existing 4.1.0 | `tests/unit/test_process_hardening.py` |
| Test safety | Temporary storage and blank secrets precede imports; live DNS/network/provider commands are blocked; persistence/runtime/DNS caches reset per test | Process hardening tests |
| CI and validators | All-branch workflow includes full offline suite, frontend checks and frozen hashes; smoke uses temporary subprocess state; rollback exercises fresh-process persistence and actual historical readers | Active workflow and process hardening tests |

## Deliberate compatibility and behavior changes

- Existing shorter dossier IDs remain readable. New dossiers retain the old fields and add snapshots/checksums; an actual baseline reader is tested. Historical records are never rewritten or retrospectively sealed.
- Checksums detect content drift, not authenticated authorship or external truth. `TRACE_VERIFIED` requires a valid new manifest and captured-content checks; legacy records report `LEGACY_UNSEALED`.
- `ADMIN_API_TOKEN` must be configured server-side for privileged response deployment. It must not be embedded in public JavaScript. Public research endpoints remain public.
- Concurrent scans of a busy shared agent receive `429` and `Retry-After: 3`; the worker lock releases on errors.
- Automatic browser rescue is disabled until its entire network boundary can honor destination pinning. Scraper implementations and compatibility shims remain present. JS-only pages may now fail honestly instead of using an unsafe bypass.
- The historical Phase 4 golden manifest was not re-baselined. Tests compare its legacy dossier projection separately from new additive integrity fields, and explicitly test the corrected exhausted-deadline behavior.

## Verification

| Local gate | Result |
|---|---|
| `pytest tests/ -q -o addopts='--tb=short -ra'` | PASS: 971 tests in 310.68 seconds |
| `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | PASS: 779 tests in 26.45 seconds |
| Fatal lint scoped to `backend tests scripts` (`E9,F63,F7,F82`) | PASS: 0 errors |
| Every `tests/frontend/test_*.js` | PASS: operation-health and security/page behavior suites |
| `python scripts/validate_release_candidate_smoke.py` | PASS: `OFFLINE_SMOKE_PASS` |
| `python scripts/validate_rollback_compatibility.py` | FAIL, exit 1: protected historical archive; fresh persistence/readers/tamper checks PASS |
| Frozen benchmark verifier and protected-path tracked diff | PASS: frozen hashes match; no tracked changes |

Four provider-CLI isolation cases were added after full-suite collection. They passed in the final 779-test fast gate and in the 23-test process-hardening run; they are not included in the 971 full-suite count. The earlier full run also passed 900 tests before the final replay/cache regressions were added. Counts are actual executed results, not the older 787-test milestone total.

One final smoke invocation hit the existing 180-second worker timeout. A fresh retry with the same final guards passed at `2026-10-12T05:08:48Z`; the cause of that non-reproduced timeout is not established. Neither network isolation nor the timeout was weakened to obtain the pass.

The offline smoke passed with zero evidence and `INSUFFICIENT_EVIDENCE`. The final rollback run used producer PID 8304, consumer PID 21948 and historical-reader PID 14848. Actual baseline `258cb4f` SQLite/JSON readers, checksum tamper detection, and preservation of temporary dossier bytes passed. The read-only historical archive had 2,445 readable `LEGACY_UNSEALED` dossiers and 55 JSON parsing failures, with no authenticated/sealed historical records. Nullable legacy quality tensors remain unknown metrics, not corruption. See [rollback verification](../operations/ROLLBACK_VERIFICATION.md). This is not a production readiness or live-scraping claim.

Frozen candidate/label/scenario hashes are checked explicitly. No tracked frozen benchmark, research, artifact or historical dossier changes are part of this implementation.

## Remaining boundaries

- Protected historical archive failures require owner-directed recovery from trustworthy backups. Do not synthesize missing research, silently delete bad files, or claim archive acceptance.
- Some fixed-origin legacy social/resolver/provider-tool paths remain outside the shared HTTP transport. This work does not assert universal network pinning. Running threads cannot be forcibly canceled; callers return at deadlines while bounded workers finish.
- Refetch comparison of older records still has legacy snippet/full-page normalization limitations; it is not proof that the entire external page is unchanged.
- Architectural debt such as global service composition, remaining legacy imports and large modules is not eliminated by this correctness pass. Further decomposition should preserve the tested contracts.
- Remote GitHub Actions, live provider credentials, deployment rollback and staging load verification remain unverified until separately executed. The workflow change itself is not a successful remote run.
