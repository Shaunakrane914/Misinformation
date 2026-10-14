# Architecture remediation: testing and safe resume runbook

Date: 2026-10-12 (Asia/Calcutta). This is an executable handoff for the local architecture-review remediation, not a release certificate. Read [AGENTS.md](../../AGENTS.md) first, then the [remediation report](../architecture/ARCHITECTURE_REVIEW_REMEDIATION_2026-10-12.md). The existing package version remains **4.1.0**; aligning reported versions did not create a new release.

## 1. Establish the actual starting point

Run from the repository root. Preserve the current dirty implementation and unrelated owner changes. Record the branch, commit, status, interpreter and current test collection; do not infer these from an older handoff or milestone count.

```text
git branch --show-current
git rev-parse HEAD
git status --short
python --version
node --version
python -m pytest tests/ --collect-only -q -o "addopts=--tb=short -ra"
```

The recorded remediation base was `b3f3fc8` on `feat/phase7-2c-root-cleanup`, with no remediation commit/push/deployment. Verify whether that is still true before resuming. Python 3.11+ is required; Python 3.12 and Node 20 match the full CI job. Use an existing suitable virtual environment, or install dependencies into a newly created environment:

```text
python -m pip install -r requirements.txt pytest pytest-rerunfailures flake8
```

Dependency installation may require network access. That is environment preparation, not a live provider test. Do not update dependency declarations or lock files merely to obtain a green gate.

## 2. Recorded evidence, not a fabricated transcript

The following are **summary excerpts from the recorded local execution**, also preserved in the remediation report. Full raw stdout is not reconstructed here. Generate new logs with the commands below for new evidence.

| Recorded gate | Recorded outcome | How to interpret it |
|---|---|---|
| Full offline Python suite | `971 passed in 310.68s` | Four provider-CLI isolation cases were added after this full-suite collection. This is not a full run of every subsequently added case. |
| Final unit/chaos/security gate | `779 passed in 26.45s` | Includes those four CLI cases. Counts are historical observations, not future acceptance thresholds. |
| Final process-hardening subset | 23 tests passed | Includes guard behavior and output preservation checks. |
| Fatal lint | 0 errors | Only the explicitly selected fatal error codes were checked; this is not a claim of comprehensive style/type/security analysis. |
| All `tests/frontend/test_*.js` | PASS | Node behavioral tests with simulated DOM/fetch; not a real-browser visual, accessibility or deployed-host test. |
| Offline smoke | `OFFLINE_SMOKE_PASS` | Temporary storage, disabled acquisition and explicit test mocks. Zero evidence and `INSUFFICIENT_EVIDENCE` are honest offline results. |
| Rollback validator | `HISTORICAL_ARCHIVE_FAIL`, exit 1 | Fresh-process state reload, actual baseline readers and tamper checks passed; protected historical JSON inspection did not. |
| Frozen content hashes / protected tracked diff | PASS / no tracked changes | Frozen datasets and historical research outputs were not re-baselined or modified. |

One final smoke attempt hit the existing 180-second worker timeout. A fresh retry with the same guards passed at `2026-10-12T05:08:48Z` (10:38:48 Asia/Calcutta). Its cause was not reproduced or established. Do not suppress a recurrence, increase the timeout without investigation, or remove offline guards to obtain a pass.

The default archive inspection reported 2,445 readable `LEGACY_UNSEALED` records and 55 malformed JSON files. These are recorded archive observations, not constants to enforce in tests. The files remain protected and untouched. Read [rollback verification](../operations/ROLLBACK_VERIFICATION.md) for the recovery boundary.

## 3. Run the gates and keep new evidence safely

The subsequent documentation-handoff rerun passed all 975 full-suite cases in 307.08 seconds and 779 fast-suite cases in 30.26 seconds, including the four late-added CLI tests. Lint, both Node suites, frozen hashes and isolated smoke passed. Rollback still exited 1 for the same 55 protected JSON failures. These are new recorded results, not replacements for the earlier 971 snapshot; see the [work log](2026-10-12_ARCHITECTURE_REMEDIATION_WORK_LOG.md) and [context JSON](2026-10-12_ARCHITECTURE_REMEDIATION_CONTEXT.json).

The examples below create a unique **temporary log directory** and capture each exit code separately. They intentionally continue after a failed gate so that the archive failure does not hide later integrity checks. Continuing is not acceptance: review every `.exitcode`, `.log` and JSON report before concluding.

Never point logs or `--output` at an existing file in `artifacts/`, `research/`, frozen fixtures, or historical dossiers. The validators default to console output and temporary runtime storage; explicit report output uses exclusive creation and refuses to overwrite an existing file. A durable owner-chosen evidence directory is also acceptable if it is new and outside protected historical outputs. Review logs for secrets before sharing or committing them.

### PowerShell

```powershell
# Run from the repository root, with the intended virtual environment active.
$aegisLogDir = Join-Path ([System.IO.Path]::GetTempPath()) ("aegis-handoff-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $aegisLogDir | Out-Null

function Invoke-AegisGate {
    param([string]$Name, [string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments *> (Join-Path $aegisLogDir ($Name + ".log"))
    $aegisCode = $LASTEXITCODE
    Set-Content -LiteralPath (Join-Path $aegisLogDir ($Name + ".exitcode")) -Value $aegisCode
    Write-Host "$Name exit=$aegisCode"
}

$aegisProtectedPaths = @(
    "tests/retrieval_benchmark/candidates.jsonl",
    "tests/retrieval_benchmark/labels.jsonl",
    "tests/retrieval_benchmark/scenarios.jsonl",
    "backend/data/dossiers", "research", "artifacts"
)
Invoke-AegisGate -Name "protected-before" -Executable "git" -Arguments (@("diff", "--exit-code", "HEAD", "--") + $aegisProtectedPaths)
Invoke-AegisGate -Name "inventory" -Executable "python" -Arguments @("-m", "pytest", "tests/", "--collect-only", "-q", "-o", "addopts=--tb=short -ra")
Invoke-AegisGate -Name "fast" -Executable "python" -Arguments @("-m", "pytest", "tests/unit", "tests/chaos", "tests/security", "-q", "-o", "addopts=--tb=short -ra")
Invoke-AegisGate -Name "full" -Executable "python" -Arguments @("-m", "pytest", "tests/", "-q", "-o", "addopts=--tb=short -ra")
Invoke-AegisGate -Name "fatal-lint" -Executable "python" -Arguments @("-m", "flake8", "backend", "tests", "scripts", "--count", "--select=E9,F63,F7,F82", "--show-source", "--statistics")
Get-ChildItem -LiteralPath "tests/frontend" -Filter "test_*.js" | Sort-Object Name | ForEach-Object {
    Invoke-AegisGate -Name ("frontend-" + $_.BaseName) -Executable "node" -Arguments @($_.FullName)
}
Invoke-AegisGate -Name "frozen" -Executable "python" -Arguments @("scripts/validation/verify_frozen_benchmarks.py")
Invoke-AegisGate -Name "smoke" -Executable "python" -Arguments @("scripts/validate_release_candidate_smoke.py", "--output", (Join-Path $aegisLogDir "smoke.json"))
Invoke-AegisGate -Name "rollback" -Executable "python" -Arguments @("scripts/validate_rollback_compatibility.py", "--output", (Join-Path $aegisLogDir "rollback.json"))
Invoke-AegisGate -Name "protected-after" -Executable "git" -Arguments (@("diff", "--exit-code", "HEAD", "--") + $aegisProtectedPaths)
git status --short -- $aegisProtectedPaths
Write-Host "New logs: $aegisLogDir"
```

### POSIX shell

```sh
# Run from the repository root, with the intended virtual environment active.
aegis_log_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-handoff.XXXXXXXX")

run_aegis_gate() {
    aegis_gate_name=$1
    shift
    if "$@" >"$aegis_log_dir/$aegis_gate_name.log" 2>&1; then
        aegis_gate_code=0
    else
        aegis_gate_code=$?
    fi
    printf '%s\n' "$aegis_gate_code" >"$aegis_log_dir/$aegis_gate_name.exitcode"
    printf '%s exit=%s\n' "$aegis_gate_name" "$aegis_gate_code"
}

run_aegis_gate protected-before git diff --exit-code HEAD -- \
    tests/retrieval_benchmark/candidates.jsonl tests/retrieval_benchmark/labels.jsonl \
    tests/retrieval_benchmark/scenarios.jsonl backend/data/dossiers research artifacts
run_aegis_gate inventory python -m pytest tests/ --collect-only -q -o 'addopts=--tb=short -ra'
run_aegis_gate fast python -m pytest tests/unit tests/chaos tests/security -q -o 'addopts=--tb=short -ra'
run_aegis_gate full python -m pytest tests/ -q -o 'addopts=--tb=short -ra'
run_aegis_gate fatal-lint python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
for aegis_test in tests/frontend/test_*.js; do
    [ -f "$aegis_test" ] || continue
    run_aegis_gate "frontend-$(basename "$aegis_test" .js)" node "$aegis_test"
done
run_aegis_gate frozen python scripts/validation/verify_frozen_benchmarks.py
run_aegis_gate smoke python scripts/validate_release_candidate_smoke.py --output "$aegis_log_dir/smoke.json"
run_aegis_gate rollback python scripts/validate_rollback_compatibility.py --output "$aegis_log_dir/rollback.json"
run_aegis_gate protected-after git diff --exit-code HEAD -- \
    tests/retrieval_benchmark/candidates.jsonl tests/retrieval_benchmark/labels.jsonl \
    tests/retrieval_benchmark/scenarios.jsonl backend/data/dossiers research artifacts
git status --short -- tests/retrieval_benchmark/candidates.jsonl tests/retrieval_benchmark/labels.jsonl \
    tests/retrieval_benchmark/scenarios.jsonl backend/data/dossiers research artifacts
printf 'New logs: %s\n' "$aegis_log_dir"
```

`git diff ... HEAD` covers staged and unstaged tracked changes; it is read-only. `git status` also shows untracked files. If protected differences already exist before a run, preserve and report them; do not automatically restore, delete, or assume they are test-generated. Compare before/after evidence when attributing changes.

### Expected interpretation, not a fixed-count gate

| Gate | Expected healthy status | Investigate when |
|---|---|---|
| Collection | Exit 0; current inventory is recorded | Imports/collection fail or expected modules disappear |
| Fast/full Python | Exit 0 with every collected case passing | Any failure/error; do not accept an older numeric total in place of current collection |
| Fatal lint / each Node file | Exit 0 | Fatal errors, failed assertions, missing test files or execution environment |
| Frozen verifier | Exit 0; content hashes verified | Any changed frozen content, even if benchmarks still pass |
| Protected diff | Exit 0 when initially unchanged | New/staged/unstaged historical-output changes |
| Smoke | Exit 0; JSON `execution_mode: OFFLINE_REGRESSION`, `verdict: OFFLINE_SMOKE_PASS` | Worker error/timeout, definitive unsupported verdict, missing gates or artifact writes |
| Default rollback | Known current archive result is exit 1 / `HISTORICAL_ARCHIVE_FAIL` | Fresh reload/readers/tamper checks regress, archive failures change unexpectedly, or an apparent pass silently excludes the archive |

The known rollback exit 1 is a disclosed blocker, **not an acceptable release pass**. Do not weaken the checker, switch `--archive` to an empty directory, remove invalid historical files, or fabricate their contents. Recovery requires owner direction and trustworthy backups, with before/after integrity evidence. An empty archive or unavailable baseline reports `NOT_VERIFIED`; a zero process exit in those circumstances does not establish all rollback criteria.

## 4. Why offline isolation is implemented this way

Read [tests/conftest.py](../../tests/conftest.py), [isolated_runtime.py](../../scripts/validation/isolated_runtime.py), and [process-hardening regressions](../../tests/unit/test_process_hardening.py) before changing test setup.

- Temporary SQLite paths, temporary dossier storage, test environment, explicit LLM mock mode and disabled background RSS are configured **before application singleton imports**. Setting these afterward can leave a singleton connected to the owner's database or archive.
- Credentials are assigned empty values, including credential names discovered in the repository `.env`, rather than merely deleted. This prevents `load_dotenv` from restoring real keys. Tests must not access Supabase or local authenticated provider tools.
- Every test resets isolated database rows, all in-memory persistence stores, replay caches, runtime capability observations, native doctor observations and the DNS cache. This prevents order-dependent health/cooldown and evidence state from leaking into the next case.
- External DNS, actual socket connections and known network-capable provider commands are blocked before collection. Mock the intended canonical acquisition/network boundary when testing behavior; do not enable live I/O to fix a stale mock.
- Windows asyncio uses the standard library's `socketpair` for its internal wake-up pipe. Only the original socketpair call has a thread-local exemption. Ordinary TCP, including loopback, remains blocked; broad localhost exemptions would make this protection ineffective.
- The CLI guard also blocks `gh`, `opencli`, `twitter-cli` and `twitter`, which may use credentials persisted outside environment variables. These were the four late-added regression cases. Existing guarded commands include `agent-reach`, `yt-dlp`, `bird`, `curl`, `wget` and `gallery-dl`.
- This is application-level test protection, not an OS network sandbox or a guarantee that arbitrary newly introduced subprocess APIs are covered. Any new provider executable/launch path needs explicit isolation review and regression coverage.
- Smoke/rollback use the same isolated environment in fresh worker processes. Each worker is bounded by the existing 180-second parent timeout. Smoke uses the FastAPI lifespan via context-managed `TestClient`; offline acquisition is disabled. No existing artifact report is written by default.

Do not move live probes into the offline gate. `tests/smoke_test_social_production.py` is an owner-authorized live probe, not evidence that the isolated suite scraped a platform successfully.

## 5. Where to start when a gate fails

| Symptom or changed boundary | Focused tests / implementation to read |
|---|---|
| Authority spoofing, DNS/redirect/slow response behavior | [review security regressions](../../tests/security/test_review_security_regressions.py), [safe HTTP tests](../../tests/security/test_safe_http_transport.py), [shared HTTP transport](../../backend/infrastructure/acquisition/network/http.py) |
| Approved operations, platform opt-outs, cooldown, budget/deadline | [acquisition policy regressions](../../tests/unit/test_acquisition_policy_integrity.py), [16 recovered-operation route contracts](../../tests/unit/test_recovered_operation_routes.py) |
| Authorization, uncertainty, event-loop blocking, concurrent scan state | [API regressions](../../tests/unit/test_api_hardening_regressions.py), [operator authorization](../../backend/api/security.py) |
| Replay legacy/malformed/tampered structures | [replay verification](../../tests/unit/test_replay_verification.py), [structure regressions](../../tests/unit/test_replay_structure_regressions.py), [ledger](../../backend/services/research/replay_ledger.py) |
| Config aliases, storage, mocks or validator safety | [process regressions](../../tests/unit/test_process_hardening.py), [LLM tests](../../tests/unit/test_llm_gateway.py), [settings](../../backend/core/settings.py) |
| Frontend uncertainty, XSS, TTL/visibility, Netlify failure honesty | [security/page behaviors](../../tests/frontend/test_security_and_health_regressions.js), [operation health behaviors](../../tests/frontend/test_operation_health.js) |
| Research serialization or deadline behavior | [Phase 4 golden characterization](../../tests/unit/test_research_pipeline_golden.py) |

Run an individual file using `python -m pytest <path> -q -o "addopts=--tb=short -ra"`. Start with the specific failure, then rerun the required full gates. A subset pass does not replace full regression evidence.

The Phase 4 golden manifest was deliberately **not** regenerated. New dossier snapshots/checksums are checked independently, then the legacy projection is compared to the historical serialization. The `discovery_timeout` scenario explicitly asserts the correctness exception: no deep reads after an exhausted deadline. Do not re-baseline that historic fixture to conceal a regression.

## 6. Rollback, CI and the next evidence boundary

The [rollback validator](../../scripts/validation/validate_rollback_compatibility.py) produces temporary state, reads it in a different process, and runs actual SQLite/JSON readers from baseline `258cb4f1fc71c379d0e882d8804c2a9770fc7f60` in another process. It verifies that reader execution leaves temporary dossier bytes unchanged. Baseline source is obtained with read-only `git show`; no checkout or history rewrite occurs. If the commit is missing locally, reader compatibility is `NOT_VERIFIED`. Do not label current-code reload as previous-version compatibility.

The [active CI workflow](../../.github/workflows/ci.yml) now defines all-branch lint/frontend/frozen checks, a Python 3.11/3.12/3.13 fast matrix, and a Python 3.12 full suite plus validators. Full CI uses `fetch-depth: 0` so the baseline can be available. The known historical archive failure can make the configured full job fail; keep that result visible. Configuration is not remote execution evidence. See the [coverage matrix](../testing/CI_COVERAGE_MATRIX.md).

Not verified by this work: a remote GitHub Actions run, live provider credentials/scraping, a production deploy, a full deployed earlier-version rollback, staging load, or browser visual/accessibility acceptance. Obtain separate authorization before those external actions. `readyz`, mock results, content checksums, or a Node VM pass do not prove them.

Before handing off again, record: exact branch/commit and dirty status; collection and executed counts; each command and exit code; interpreter versions; new log/report locations; protected-path before/after status; known archive/timeout failures; and any work not run. Preserve failures honestly and link the newest evidence rather than overwriting historical reports.
