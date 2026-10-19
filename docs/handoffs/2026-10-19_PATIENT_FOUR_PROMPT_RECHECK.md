# Four-prompt patient-window recheck — 2026-10-19

## Decision and scope

**Research acceptance: incomplete. Bounded local rendering: PASS.** More time
allowed searches and reads, but did not establish useful investigations for
BrandShield or Personal Watch. HTTP 200 and offline tests are not research or
deployment acceptance.

User request: check four different prompts again. Repeated Scout / Infosys,
Trending / NVIDIA (technology), BrandShield / Nike and Personal Watch / Tim Cook
for comparison with earlier checks. These are broad entity prompts, not an
independent labeled claim evaluation. This is an audit, not an implementation.

Checkout: `fix/p0-lenovo-acquisition-20261018`, HEAD
`3a0797edc2693bef135342b1786add9c3807988f`; application checkpoint
`69b48d64bc7ec8146a2da18bec5b8170dc7c861c`. Worktree started clean.
No application source, configuration, credentials, frozen benchmarks or old
dossiers changed. Only this report, new evidence and the handoff index changed.
No commit, push, merge, CI trigger or deployment in this recheck.

## Method

- Four sequential real local ASGI/SSE investigations through normal routes,
  one request per input, no audit POST retries. Existing finite acquisition
  fallbacks remain; four investigations are not four provider HTTP calls.
- Default 120s research window, about 54s discovery opportunity, about 48s
  reserved reading slice, 15s multi-step chains. No transport or policy changes.
- AI disabled by the runner; no `--allow-live-ai`, mock mode false, no generation
  or model-list requests. This does not validate live AI credentials/synthesis.
- Temporary SQLite/dossier storage, lifespan/background ingestion off, external
  persistence/notifications disabled. Local acquisition settings retained, not
  enabled by this audit or proof of provider authorization.
- Exact saved SSE replay through actual page buttons, stream client and shared
  renderers in Chromium. No acquisition request was forwarded during replay;
  no source-read follow-up clicked. Actual pinned Chart.js 4.4.1 served locally;
  external fonts blocked.
- Application fingerprint unchanged during both runs:
  `6218d514c146173b9354237c0e46cdb0a6a6e1a59d25a268bb2e936f5be052bc`.

Fresh raw responses, event streams, sanitized logs, temporary dossiers and all
screenshots remain in the system-temp tree named
`aegis-patient-four-70ac8794-4743-4cee-928a-26c7da893be7`.
Selected durable evidence: [measurements and screenshots](../testing/evidence/2026-10-19_patient_four_prompt_recheck/README.md).
Temporary outputs are not guaranteed to survive system cleanup.

## Measured results

Words are whitespace tokens in one retained native content/snippet per record.
KB = UTF-8 bytes / 1,000, excluding metadata/discovery projections. These are
not relevant-word counts, independently corroborated claims or website coverage.

| Agent / input | Seconds | Records | Words | KB | Findings | Discovery cards |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Scout / Infosys | 51.13 | 7 | 3,780 | 29.328 | 2 | 24 |
| Trending / NVIDIA | 28.28 | 3 | 874 | 5.927 | 1 | 5 |
| BrandShield / Nike | 36.08 | 0 | 0 | 0 | 0 | 22 |
| Personal Watch / Tim Cook | 32.59 | 1 | 8 | 0.059 | 0 | 9 |

All returned HTTP 200, one result event and no SSE error event. Nike's returned
status is **ACQUISITION_FAILED**. The other `COMPLETED` statuses are not evidence
of successful specialized research.

### Scout: useful financial capture, not claim adjudication

Two issuer PDFs retained 1,456 and 1,449 words; a P&L page retained 188 words.
Four other pages provide report/index context. USD and INR release versions
have near-duplicate opening paragraphs, not independent corroboration. Both
findings are long release excerpts (196/198 words), labeled `UNVERIFIED`.
Each canonical citation joins exactly one returned source; its normalized
statement occurs in that captured body. This does not verify the issuer's claims.
Six direct reads succeeded, plus one reused acquired record. Duplicate synthesis,
executive brevity and claim-specific financial comparison remain incomplete.

### Trending: article plus minimal Reddit submissions

One publisher article retained 806 words; two Reddit link-submission records
account for the remaining 68 words. Those contain titles/authors/target URLs,
not substantive discussion or fetched linked articles. This is bounded local
metadata acquisition, not general Reddit access. Other Reddit searches still
timed out/rate-limited. Three of five reads succeeded; two Google News wrappers
could not resolve to publishers. The one `UNVERIFIED` finding cites
`ev_02bfb85bef74`, joins the article and occurs in its body. Virality, velocity
and independent product verification are not established.

**Remaining provenance defect:** native Trending evidence correctly carries
body author `Shreevar Rastogi`, discovery author `Gerardo Delgado` and
`attribution_conflict: true`. But `research_corpus.deep_read_sources.author` and
`unified_report.evidence.*.source.name` still use Gerardo Delgado. The shared UI
shows that feed attribution while the inspected body names Shreevar Rastogi.
The earlier native-adapter correction did not reach the shared projection.
Preserve both observations and the conflict when correcting this separately.

### BrandShield: acquisition failure, no threat conclusion

Nine query records report success and three Reddit chains timed out; query
success did not yield an acquired body. All three selected reads were Google
News wrappers and failed publisher resolution in about 0.76–1.34s. Twenty-two
discovery cards remain separate from zero bodies. The frontend prominently
displays **ACQUISITION FAILED — UNABLE TO RETRIEVE EVIDENCE**, not a claim that
Nike has no information or risk. No counterfeit/phishing/impersonation judgment
is established. Adaptive queries about `Wikipedia Nike` / `Nike Golf` with generic
announcement terms remain poorly aligned with threat intelligence. Publisher
resolution and task-specific source selection are more useful next work than
another blanket timeout increase.

### Personal Watch: profile-only

The sole record is eight words of X profile metadata. Captured role text is not
independently verified current identity. Three article-wrapper reads failed
publisher resolution in about 2.55–3.21s; nine discovery cards remain. No quote
verification, impersonation finding, media forensics or proof of safety is
established. The shared report discloses that limitation and returns no findings.

## Timing and lifecycle

| Input | Reported started / planned | Query success / timeout / failed | Discovery / adaptive / reading seconds | Total seconds remaining after processing |
| --- | ---: | --- | --- | ---: |
| Infosys | 14 / 14 | 9 / 3 / 2 | 30.066 / 12.464 / 7.458 | 69.491 |
| NVIDIA | 17 / 17 | 14 / 2 / 1 | 17.644 / 6.964 / 3.441 | 91.893 |
| Nike | 12 / 12 | 9 / 3 / 0 | 30.169 / 4.290 / 1.351 | 84.151 |
| Tim Cook | 12 / 12 | 10 / 0 / 2 | 18.830 / 10.403 / 3.213 | 87.528 |

- All **47 initial records** explicitly have `provider_started: true`. No
  `QUEUE_TIMEOUT`, `NOT_SUBMITTED` or `SKIPPED` records. Eight adaptive records
  have null provider-start/duration instrumentation; assembly counts starts using
  a status-based compatibility rule. Do not call all 55 independently measured
  provider starts. Adaptive lifecycle telemetry still needs improvement.
- All eight main query timeouts were started Reddit chains, about 15s each.
  This is not total-deadline starvation. Logs also contain Reddit 429s, but do
  not prove the same precise cause for every timeout.
- Cached capability snapshots took 0.170–0.206ms; zero synchronous doctor calls
  in all four cases. Scout resolution took 0.019ms, quote retrieval 395.015ms.
- Reading began with 59.098 / 77.362 / 67.523 / 72.748 seconds remaining in its
  stage window. None exhausted the total investigation clock.
- Infosys, NVIDIA and Tim Cook stopped adaptive expansion on the explicitly
  heuristic novelty policy. Nike's funnel says `BUDGET_CEILING`, but its ledger
  says `Completed standard budget` and more than 84s remained. The
  [assembly fallback label](../../backend/application/research/assembly.py)
  is not evidence of a wall-clock cutoff; stopping telemetry needs precision.
- Funnel `deep_reads_count` counts acquired deep-read records here, not all
  attempts: actual attempts were 6 / 5 / 3 / 4. Initial and cumulative candidate
  counters also have different scopes (Nike found 22 initially, accepted 27
  cumulatively); do not present them as one additive funnel.

The [earlier repaired sample](2026-10-19_FOUR_PROMPT_REPAIR.md) retained Infosys
3,780 words, NVIDIA 806, Nike 893 background words and Tim Cook eight profile
words. This recheck retains the same Infosys/Tim Cook volume, 68 extra NVIDIA
metadata words and no Nike bodies, with longer requests. Separate live samples
have variable provider responses; this is not a controlled causal comparison.
Extra time did not demonstrate broader research-quality acceptance.

## Frontend and regression checks

Exact saved SSE replay passed **12 states** at 320/390/1440px: matching
finding/acquired/discovery counts, no missing finding text, no horizontal
overflow and no uncaught page exceptions. Keyboard Enter opened the first
acquired inspection in nine applicable states; Nike has no acquired card.
All four 390px report captures and two inspection captures were visually read.
Six console resource errors remain: four deliberately blocked font loads and
two static-harness 404 entries. These are not uncaught app exceptions or proven
production failures. Full accessibility, contrast, cross-browser behavior and
production parity remain unverified.

Actual command summaries, not a reconstructed raw transcript. Logs went to the
fresh temp tree; Python 3.13.5 / Node v22.17.1. Terminal/browser subprocesses used
`SERVER_MODE=1`; neither used `--allow-live-ai`.

| Command / gate | Exit | Result |
| --- | ---: | --- |
| `python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file <existing-env> --output-dir <new-terminal-dir> --case scout:Infosys --case trending:NVIDIA --case brandshield:Nike --case "personal_watch:Tim Cook"` | 0 | Four real results, AI disabled; limitations above |
| `python scripts/audits/run_phase9_four_agent_browser_audit.py --env-file <existing-env> --output-dir <new-browser-dir> --chart-js <pinned-chart-js> --replay-dir <saved-terminal-dir>` with the same four `--case` options | 0 | Exact-response replay, 12 states |
| `python -m pytest tests/ -q -o "addopts=--tb=short -ra"` | 0 | 1,474 passed, 67.16s |
| `python -m pytest tests/unit tests/chaos tests/security -q -o "addopts=--tb=short -ra"` | 0 | 1,266 passed, 45.38s |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | 0 | Zero selected fatal errors |
| Each of nine `tests/frontend/test_*.js` via `node` | 0 each | All passed |
| `python scripts/validate_release_candidate_smoke.py --output <new-smoke-json>` | 0 | `OFFLINE_SMOKE_PASS` |
| `python scripts/validate_rollback_compatibility.py --output <new-rollback-json>` | 0 | `OFFLINE_PERSISTENCE_PASS`; historical archive/deployed rollback **NOT_VERIFIED** |
| `python scripts/validation/verify_frozen_benchmarks.py` | 0 | Frozen hashes verified |
| Protected-path `git diff --exit-code HEAD -- ...` | 0 | Protected outputs unchanged |

Offline suites started after the four live investigations completed, avoiding
CPU competition during acquisition measurement. Rollback verified temporary
state and actual baseline readers; this isolated checkout has no historical
archive. The previously reported 55 corrupt originals were not repaired or
re-certified. Prior hosted CI at `69b48d6` is recorded in the
[preceding handoff](2026-10-19_PATIENT_RESEARCH_WINDOW.md), not a fresh CI run for
this documentation-only check. No deployment parity assertion is made.

## Next engineering priorities — not implemented here

1. Resolve selected news leads to actual publishers and choose relevant direct
   alternatives after wrapper failure; never count wrapper text as article bodies
   or evade provider access controls.
2. Make specialist follow-ups task-specific; profile metadata cannot satisfy
   Personal Watch's identity-threat research objective.
3. Preserve conflicting body/feed attribution through the shared projection;
   deduplicate Infosys release-version summaries.
4. Instrument adaptive starts/failures and distinguish work-count/novelty stops
   from actual elapsed deadlines.
5. Recheck positive/negative specialist cases after changes. This audit does not
   authorize additional live requests, source edits or deployment.
