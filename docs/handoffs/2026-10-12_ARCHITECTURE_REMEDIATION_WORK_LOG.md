# Architecture remediation execution work log

Date: 2026-10-12 (Asia/Calcutta). This is an edited reconstruction of implementation checkpoints and observed command-result excerpts from the coding session. It is **not** a verbatim conversation export or a complete raw stdout archive. No private reasoning traces, credentials, personal data or dossier bodies are included. The concise decision rationale is in [the decision record](2026-10-12_ARCHITECTURE_REMEDIATION_DECISIONS.md).

## Request and baseline

The user asked for architecture/code/process review, then authorized solving the identified issues, then explicitly requested durable documents and transcripts so another coding agent could understand the implementation and continue safely.

The remediation began from a clean worktree on `feat/phase7-2c-root-cleanup`, HEAD `b3f3fc8248a92d0d15026327b5e9b14f273a0064`. At handoff, changes are local and uncommitted. No push or deployment was performed. The existing `4.1.0` project version was aligned across package/API/frontend metadata, not incremented as a new release.

## Checkpoint transcript

| Order | Observed problem or result | Implementation response / conclusion |
|---|---|---|
| 1 | Review found authorization, XSS, DNS rebind, source-authority, replay integrity, truthful-result, deadline and delivery-process defects | Split implementation into acquisition/research, API/frontend, configuration/process, and root security/replay work; kept protected research untouched. |
| 2 | Existing router/service/import paths were used by callers and monkeypatch tests | Preserved compatibility interfaces; implemented canonical behavior behind them rather than deleting scrapers or shims. |
| 3 | First narrow regression run exposed an expected-directory assertion, Windows asyncio socketpair breakage, missing canonical read mocks and an obsolete legacy trace expectation | Fixed fixture boundaries and assertions. Restored only the standard-library socketpair exemption, not general loopback networking. Valid legacy records now assert unsealed, not verified. |
| 4 | Security/replay/golden checks progressed through 86 and 89 passes | Added pinning/SNI, slow-header/body, malformed-port, collision/no-overwrite, persistence-error, legacy/tamper and production mock guards. These intermediate totals are not current inventory. |
| 5 | External DNS isolation revealed tests that had relied on real DNS; an unmocked Yahoo-positive test and forced full-article expectations failed | Supplied scoped fake public DNS and deterministic stock data; kept the real scoring pipeline. Updated small-body expectations to truthful snippet depth instead of weakening production protections. |
| 6 | Typed exact-operation dispatch risked losing strategy-only enrichment | Factored enrichment for all four strategies and applied it after approved dispatch; added Personal Watch redaction regression. |
| 7 | Full fatal lint found a new imported/local `quote` name collision | Aliased URL quoting and tested successful bounded stock-provider output, rather than accepting a swallowed exception fallback. |
| 8 | Worker offloading exposed mutable singleton scan-state races | Added per-agent fail-fast worker-side admission locks; concurrent scan gets 429/Retry-After instead of mixed research. Verified release on failure. |
| 9 | A rejected/rate-limited read could fall through to unpinned legacy/browser code | Disabled automatic unsafe bypasses, retained interfaces, and required structured failures or bounded fallback behavior. |
| 10 | Independent review reproduced arbitrary GitHub primary evidence becoming `KNOWN_FACT`, plus malformed nested legacy queries raising exceptions | Distinguished original from official authority in synthesis and validated traversed dossier structure before playback/refetch/publication. |
| 11 | Strict structure audit briefly classified 476 historical `quality_tensor: null` records as failures in addition to 55 bad JSON files | Confirmed null means an unknown, non-traversed metric; accepted that historical schema value while still rejecting invalid shapes/checksums. Final archive result is 2,445 unsealed and 55 JSON parsing failures. No file was rewritten. |
| 12 | Focused acquisition matrix passed 267 tests; frontend behavior suites passed; fatal lint reported zero | Moved to full gates rather than treating targeted tests as release acceptance. |
| 13 | First full run passed 900 tests; later full run passed 971; final fast run passed 779 | Four provider-CLI cases were added after the 971 full collection and verified in the final fast/process gates. The extra CLI guard prevents tools such as `gh` from using locally persisted auth. |
| 14 | Rollback now inspected contents rather than just counting filenames | Fresh-process state, actual baseline readers and tamper checks passed; protected archive failed on 55 malformed JSON files. The failure remains visible. |
| 15 | One final smoke worker hit its existing 180-second timeout | Fresh retry passed; a bounded diagnostic also completed normally. Cause was not reproduced/established. Guards and timeout limits were not weakened. |
| 16 | User requested continuity documentation | Added the handoff entry point, decisions/code map, test runbook, this work log and machine context; fixed stale navigation and linked historical reports to current evidence. No further runtime implementation was introduced in this documentation task. |

## Recorded prior implementation commands/results

These excerpts preserve actual observations; omitted progress lines are not reconstructed.

```text
$ pytest tests/ -q -o addopts='--tb=short -ra'
900 passed in 374.19s (0:06:14)
exit 0

$ pytest tests/ -q -o addopts='--tb=short -ra'
971 passed in 310.68s (0:05:10)
exit 0

$ pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'
779 passed in 26.45s
exit 0

$ flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
0
exit 0

$ node tests/frontend/test_operation_health.js
ALL FRONTEND OPERATION HEALTH TESTS PASSED (8/8)!
exit 0

$ node tests/frontend/test_security_and_health_regressions.js
FRONTEND SECURITY AND HEALTH REGRESSIONS PASSED
exit 0

$ python scripts/validation/verify_frozen_benchmarks.py
Frozen benchmark content hashes verified
exit 0
```

The two full-suite counts are ordered checkpoints, not two versions of the same final inventory. The 971 run preceded collection of four new CLI isolation cases. The final 779 fast gate included them. Use a fresh collection/run for the current checkout.

### Smoke result and timeout disclosure

The passing retry at `2026-10-12T05:08:48Z` (10:38:48 Asia/Calcutta) reported `execution_mode: OFFLINE_REGRESSION`, `verdict: OFFLINE_SMOKE_PASS`, zero evidence and `INSUFFICIENT_EVIDENCE`. A bounded diagnostic completed in about ten seconds at `2026-10-12T05:09:30Z`, without its scheduled forty-second stack dump firing. Before those successful retries, one invocation raised `subprocess.TimeoutExpired` at the existing 180-second worker limit. No confirmed root cause was established; preserve this disclosure if a later run stalls.

### Rollback excerpt

```json
{
  "exit_code": 1,
  "verdict": "HISTORICAL_ARCHIVE_FAIL",
  "fresh_process_reload": "PASS",
  "actual_baseline_readers": "PASS",
  "baseline_commit": "258cb4f1fc71c379d0e882d8804c2a9770fc7f60",
  "historical_archive_counts": {
    "VERIFIED": 0,
    "LEGACY_UNSEALED": 2445,
    "FAILED": 55
  },
  "tamper_detection": "PASS",
  "temporary_dossier_bytes_preserved": "PASS",
  "deployed_previous_version": "NOT_VERIFIED"
}
```

This is a compact projection of the actual validator report, not its entire stdout. One malformed example is `R-2026-02617B.json`, JSON parsing failure at line 42, column 24. The archive was read-only. Do not infer missing dossier contents or authentication from these counts.

## Handoff documentation validation — separate rerun

The documentation task reran the required gates without changing runtime code. These new results are separate from the prior implementation evidence above.

Completed results:

- Fast gate: `779 passed in 30.26s`, exit 0.
- Fatal lint: `0`, exit 0.
- Isolated smoke: `OFFLINE_SMOKE_PASS` at `2026-10-12T05:15:39Z`, exit 0; zero-evidence guard still `INSUFFICIENT_EVIDENCE`.
- Rollback: exit 1 / `HISTORICAL_ARCHIVE_FAIL`; producer PID 27836, consumer PID 12096, historical-reader PID 20280; fresh state/readers/tamper checks passed; archive counts unchanged (2,445 unsealed / 55 failed).
- Full gate: `975 passed in 307.08s (0:05:07)`, exit 0, including the four CLI cases that were absent from the prior 971 collection.
- Both frontend Node suites passed; the frozen verifier passed and the protected-path tracked diff remained empty.
- Final documentation validation: 291 relative links and 41 context-file references resolved. `git diff --check` was rerun after correcting one added Markdown trailing-space warning.

```text
$ pytest tests/ -q -o addopts='--tb=short -ra'
975 passed in 307.08s (0:05:07)
exit 0

$ pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'
779 passed in 30.26s
exit 0
```

## Remaining evidence boundary

No remote GitHub Actions run, live-scraping proof, production deployment, deployed full-version rollback or staging load test was performed. The [testing runbook](2026-10-12_ARCHITECTURE_REMEDIATION_TESTING.md) records commands for reproduction and explains these limits. Source code and regression implementations remain in their canonical repository locations, linked from [the implementation map](2026-10-12_ARCHITECTURE_REMEDIATION_HANDOFF.md).
