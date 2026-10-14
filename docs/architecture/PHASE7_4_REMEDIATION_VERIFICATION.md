# Phase 7.4 — remediation verification and recovery assessment

Captured on 2026-10-12 (Asia/Calcutta). This is a verification checkpoint for
the architecture remediation, not a production-deployment approval.

## Scope and disposition

| Area | Result | Evidence boundary |
|---|---|---|
| Security remediation | Locally verified | Targeted authorization, SSRF, replay, process-hardening and frontend regression suites pass. A separate delegated reviewer did not complete because its external service quota was exhausted, so a second-person independent security pass remains `NOT VERIFIED`. |
| Evidence integrity | Locally verified for new records | Atomic publication, checksum/tamper and malformed-shape tests pass. Checksums still do not authenticate writers or establish external truth. |
| Historical archive | Release blocker remains | 55 of 2,500 protected JSON files are malformed; originals were not changed. |
| Recovery candidates | None found locally | Repository filesystem and available Git history produced zero valid JSON candidates. This is not proof that owner-controlled external backups do not exist. |
| Privileged deployment authorization | Contract verified; deployment secret owner-controlled | Missing configuration fails with 503, invalid/missing credentials fail with 401 before database access, and valid credentials reach the handler in isolated tests. No production token was created or stored. |
| Hosted CI | PASS for tracked code; historical archive `NOT_VERIFIED` | Follow-up run 38236691625 passed every configured job. Historical dossier JSON is intentionally untracked and absent on the runner, so the hosted rollback output cannot verify or clear the local 55-file failure. |
| Production deployment | Blocked / not authorized | No deployment or live-provider probe is part of this phase. |

## Read-only historical dossier inventory

Run the reusable inventory from the repository root:

```bash
python scripts/validation/inventory_historical_dossiers.py --candidate-root . --include-git-history
```

The captured [machine-readable inventory](../handoffs/2026-10-12_HISTORICAL_DOSSIER_RECOVERY_INVENTORY.json)
contains only portable file paths, SHA-256 hashes, sizes, parser locations and
candidate metadata—never dossier contents. Its observed summary is:

- 2,500 JSON files inspected.
- 2,445 readable JSON files.
- 55 malformed JSON files with 55 distinct SHA-256 hashes.
- 51 `JSONDecodeError` results reported “Expecting property name enclosed in double quotes”.
- 4 `JSONDecodeError` results reported “Expecting ',' delimiter”.
- 0 filesystem or Git-history candidates and therefore 0 valid recovery candidates.
- Before/after archive hashes were identical.

The inventory is a recovery-assessment aid, not a repair tool. Its optional
`--output` path uses exclusive creation and refuses to overwrite an existing
report. Any future recovery requires a trustworthy external backup, provenance
review, owner approval and a separate non-destructive restoration plan.

## Security and configuration checks

The review confirmed that `ADMIN_API_TOKEN` is represented as Pydantic
`SecretStr`; raw token text is absent from both settings `repr` and JSON
serialization. The API dependency unwraps it only for constant-time comparison.
Examples and deployment configuration contain an empty placeholder, not a
credential. No high-confidence AWS, Google, GitHub, OpenAI-style or private-key
patterns were found in changed files by the local diff scan. Dedicated tools
such as Gitleaks, TruffleHog, Semgrep and Bandit were not installed, so their
results are `NOT RUN`, not assumed clean.

The active GitHub Actions workflow covers fatal Python lint, all frontend Node
contracts, frozen dataset hashes, Python 3.11–3.13 unit/chaos/security suites,
the complete Python suite, isolated smoke, rollback compatibility and tracked
research-output mutation checks. A configured workflow is not evidence of a
hosted run.

## Fresh local checkpoint evidence

These commands were run against the complete worktree immediately before the
Git checkpoint:

| Command | Observed result |
|---|---|
| `pytest tests/ -q -o addopts='--tb=short -ra'` | PASS — 977 passed in 291.10s |
| `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | PASS — 781 passed in 24.60s |
| `flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | PASS — 0 fatal errors |
| every `tests/frontend/test_*.js` | PASS — operation-health 8/8 and security/health regressions |
| `python scripts/validate_release_candidate_smoke.py` | PASS — `OFFLINE_SMOKE_PASS`; zero-evidence verdict remained `INSUFFICIENT_EVIDENCE` |
| `python scripts/validate_rollback_compatibility.py` | Expected exit 1 — new sealed dossier/restart, tamper detection, baseline readers and temporary-byte preservation passed; protected historical archive remained 2,445 `LEGACY_UNSEALED` / 55 `FAILED` |
| frozen-hash verifier and protected tracked diff | PASS — no changes to benchmark datasets, artifacts, research or historical dossiers |

The smoke run is offline and uses temporary storage with acquisition disabled.
The rollback result is intentionally not converted into a pass: the historical
archive failure remains a release blocker, while the successful new-record
subchecks prove that freshly written dossiers persist and verify correctly.

## First hosted run and portability correction

Checkpoint `62cc5e046f2d65c426a9ecbc082575d188c8294d` triggered GitHub Actions
[run 38236168290](https://github.com/Shaunakrane914/Misinformation/actions/runs/38236168290).
The hosted code-quality/frontend/frozen-data job and Python 3.11, 3.12 and
3.13 unit/chaos/security jobs all passed. The full-suite job collected all 977
tests but failed four semantic-ranking cases before smoke or rollback ran.

This exposed a real hermeticity defect: the tests relied on locally installed
PyTorch, Sentence Transformers and cached CrossEncoder weights even though
those packages are optional and absent from the declared CI environment. The
fix adds an explicit scorer-injection seam to `SemanticReranker` and uses a
deterministic offline scorer in tests and the frozen benchmark. Production
continues to use the real CrossEncoder path when installed and otherwise
reports the existing `UNAVAILABLE` fallback; CI does not download model weights.

After the correction, the four previously failing cases passed, then the fresh
local full suite passed 977 tests in 54.24s and the fast suite passed 781 tests
in 26.79s.

The correction commit `4768c0ba706e0d306cbe4bb971b7bb508ffd5728`
triggered [run 38236691625](https://github.com/Shaunakrane914/Misinformation/actions/runs/38236691625),
which passed every configured job. Hosted Python 3.12 collected and passed all
977 tests in 22.33s; Python 3.11, 3.12 and 3.13 fast matrices, frontend/lint,
frozen hashes, isolated smoke and tracked-output checks also passed.

The hosted rollback command passed fresh-process persistence, tamper detection
and actual baseline readers, but reported the historical archive as
`NOT_VERIFIED` because protected dossier JSON is intentionally untracked and
therefore absent from a GitHub checkout. Its green `OFFLINE_PERSISTENCE_PASS`
does **not** supersede the local `HISTORICAL_ARCHIVE_FAIL` finding. Deployment
remains blocked on the local 55-file limitation and owner-controlled recovery or
explicit release-risk acceptance.

## Release decision

Keep deployment blocked. A controlled release may be reconsidered only after:

1. the checkpoint commit is reviewed and hosted CI evidence is recorded;
2. the historical archive failure is accepted explicitly or recovered from a
   trustworthy source without overwriting originals; and
3. `ADMIN_API_TOKEN` is injected through an authorized server-side secret store
   and verified in the target environment.

Live acquisition, provider credentials, staging load, deployed rollback and
production behavior remain outside this local verification.
