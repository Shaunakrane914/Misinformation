# Phase 7.4 closeout handoff

Captured on 2026-10-12 (Asia/Calcutta). Read [AGENTS.md](../../AGENTS.md) and
inspect the live branch before acting; this is a dated evidence record, not
authority to merge, deploy or alter protected research.

## Durable checkpoint

- Branch: `feat/phase7-2c-root-cleanup`.
- Remediation checkpoint: `62cc5e046f2d65c426a9ecbc082575d188c8294d`.
- Hosted-portability correction: `4768c0ba706e0d306cbe4bb971b7bb508ffd5728`.
- Both commits were pushed to the dedicated feature branch. Nothing was merged
  into `main`, deployed, or used for live-provider probing.
- The configured HTTPS OAuth token lacked GitHub's `workflow` scope and rejected
  the first push attempt because `.github/workflows/ci.yml` changed. The exact
  commit was then pushed through the machine's existing authenticated SSH Git
  identity. No credential was printed or stored in the repository.

## Hosted CI evidence

Initial [run 38236168290](https://github.com/Shaunakrane914/Misinformation/actions/runs/38236168290)
passed code quality and all Python fast/security matrices but failed four full-
suite semantic cases because CI lacked undeclared PyTorch/model state. That was
a valid portability finding, not dismissed as environmental noise.

Follow-up [run 38236691625](https://github.com/Shaunakrane914/Misinformation/actions/runs/38236691625)
passed every configured job:

- fatal Python lint, both frontend suites and frozen benchmark hashes;
- unit/chaos/security suites on Python 3.11, 3.12 and 3.13;
- all 977 tests on hosted Python 3.12;
- isolated offline smoke;
- fresh-process persistence, tamper detection and actual baseline readers; and
- tracked research-output mutation checks.

The semantic correction injects a deterministic offline scorer into tests and
the frozen benchmark. Production still loads the real CrossEncoder only when
its optional runtime dependencies are installed; unavailable models retain the
truthful fallback. CI no longer downloads model weights or relies on a local
cache.

GitHub emitted non-blocking notices that current actions are being forced from
Node 20 to Node 24 and that `ubuntu-latest` begins migrating to Ubuntu 26 on
2026-10-19. These are maintenance signals, not failures in this run.

## Historical archive remains unresolved

The read-only [machine inventory](2026-10-12_HISTORICAL_DOSSIER_RECOVERY_INVENTORY.json)
examined 2,500 local files and preserved every byte:

- 2,445 readable legacy-unsealed records;
- 55 distinct malformed JSON records;
- 51 property-name syntax errors and 4 missing-delimiter errors; and
- zero valid repository-filesystem or available Git-history recovery candidates.

Protected dossiers are ignored/untracked and therefore absent on GitHub runners.
The hosted rollback output correctly said historical archive `NOT_VERIFIED`; its
green job validates new persistence and readers, not the local archive. Local
rollback remains exit 1 / `HISTORICAL_ARCHIVE_FAIL`. Do not commit, edit, delete,
re-seal or synthesize these originals. Search owner-controlled backups next.

## Fresh local evidence after the CI correction

| Command | Result |
|---|---|
| `pytest tests/ -q -o addopts='--tb=short -ra'` | 977 passed in 54.24s |
| `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | 781 passed in 26.79s |
| fatal flake8 command from `AGENTS.md` | 0 |
| `python scripts/validate_release_candidate_smoke.py` | `OFFLINE_SMOKE_PASS` |
| `python scripts/validate_rollback_compatibility.py` | exit 1 only for 2,445 legacy-unsealed / 55 failed local historical records; all new-state subchecks passed |
| frozen verifier and protected tracked diff | PASS / unchanged |

The earlier pre-correction local full run also passed 977 tests because the
workstation had model dependencies/cache; that result did not establish CI
portability. Use the post-correction evidence above.

## Security and release boundaries

- `ADMIN_API_TOKEN` is an optional `SecretStr`, redacted from settings repr/JSON,
  and required for both privileged response-deployment aliases. Missing config
  returns 503; missing/wrong bearer credentials return 401 before database use.
- No production token was generated or configured. Inject it only through an
  authorized server-side secret store and verify the target environment.
- High-confidence local diff patterns found no AWS, Google, GitHub, OpenAI-style
  or private-key material. Gitleaks, TruffleHog, Semgrep and Bandit were not
  installed, so those specific scans remain `NOT RUN`.
- A delegated second security reviewer could not complete because of external
  service quota. Direct targeted verification and hosted tests passed, but a
  separate human/agent security review remains desirable before merge.
- Live acquisition, provider credentials, staging load, production deployment,
  full deployed rollback and external backup recovery remain `NOT VERIFIED`.

## Safe next actions

1. Review commits `62cc5e0` and `4768c0b`; open a PR if desired, but do not
   auto-merge while historical-data risk acceptance is unresolved.
2. Locate owner-controlled external backups and compare candidate bytes/hashes
   without overwriting the 55 originals. Record chain of custody and provenance.
3. Decide whether a controlled release may explicitly exclude legacy playback,
   or whether verified recovery is mandatory. Keep the limitation visible either
   way.
4. Configure and test `ADMIN_API_TOKEN` in staging through the secret manager.
5. Schedule action-version/Ubuntu 26 compatibility maintenance separately; do
   not mix it with dossier recovery.
