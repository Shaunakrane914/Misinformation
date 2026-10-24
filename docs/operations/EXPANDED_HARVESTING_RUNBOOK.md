# Acquisition-first profiles and offline requalification

Maintained 2026-10-20. [Actual results and limits](../testing/EXPANDED_HARVESTING_TWO_LAYER_REPORT_2026-10-20.md)
take precedence over illustrative commands. No production deployment is authorized.

## Runtime configuration

`AEGIS_RESEARCH_PROFILE=STANDARD` is the runtime default. API request models for
Scout, Trending, BrandShield and Personal Watch accept optional
`research_profile: QUICK | STANDARD | DEEP`. The setting is request-local and does
not mutate another investigation. Explicit legacy budgets without a profile remain
backward compatible. Existing server/local lower timeout/read/candidate overrides
still apply; restart a process to pick up environment changes.

| Mode | Candidates / queries / reads | Ceiling | Native HTTP admissions |
| --- | --- | --- | --- |
| QUICK | 24 / 6 / 6 | 60s | 40 |
| STANDARD | 60 / 12 / 14 | 150s | 80 |
| DEEP | 100 / 18 / 24 | 240s | 120 |

`AEGIS_HARVEST_HTTP_CAP` may further lower, not raise, the mode ceiling. Admission
includes native retries/redirects; it is not complete billable/network accounting.
Do not change provider approval flags or credentials to make an investigation pass.

## Raw material and replay

The full per-investigation pool is exported as
`research_corpus.raw_acquisition_pool`. Trace metadata is intentionally textless.
Default storage is bounded in memory; `AEGIS_RAW_POOL_PERSIST=true` enables an
atomic new owned system-temp snapshot, with the path in `raw_pool_snapshot`.
The terminal audit runner opts in so a later report-projection failure need not
erase the newly captured raw text. These snapshots are not historical dossiers.

Use temporary/new output paths. Never target frozen benchmarks, historical dossier
files, `research/` or existing empirical artifacts.

```text
python scripts/audits/requalify_raw_pool.py --input <saved-native-or-full-pool.json> --output <new-output.json> --target <subject> --domain financial
python scripts/audits/summarize_raw_harvest.py --run-dir <saved-terminal-run> --output <new-measurements.json>
```

Both make no source/model calls. Requalification blocks networking before app
imports, isolates persistence, checks exact hashes/counts and creates separate
decisions/offsets without changing source bytes. Trending replay can receive
`--reference-time <timezone-aware-ISO>` to fix the original observation time.

First-batch legacy alias collisions require explicit `--disambiguate-aliases`:
unique raw source IDs remain authoritative, ambiguous aliases are excluded from
lookup, and original aliases/captures remain in the original snapshot. This is
not old-citation or historical-corruption repair. Strict default import rejects
conflicting aliases and textless traces; do not suppress those errors silently.

Pool limits include 20MB overall, 1MB per source, bounded records and histories.
Cleanup is available only to the in-process pool that created its owned temp tree;
it verifies ownership/files first. Imported snapshots receive no deletion rights.
Do not use broad shell cleanup on `aegis-*` or other workspace/temp directories.
Inspect and archive wanted captures before owner-controlled retention cleanup.

## Live commands: new authorization required

The following describes commands already run; it grants no additional requests:

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --allow-live-ai --research-profile DEEP --env-file <server-env> --output-dir <new-temp-run> --case scout:Samsung --case scout:Unilever --case brandshield:Adidas --case "trending:grid-scale energy storage" --case "personal_watch:Sundar Pichai" --timeout-seconds 240 --max-deep-reads 24
python scripts/audits/run_terminal_agent_quality.py --allow-live --research-profile DEEP --env-file <server-env> --output-dir <different-new-temp-run> --case scout:Samsung --case "personal_watch:Sundar Pichai" --timeout-seconds 180 --max-deep-reads 16 --max-http-admissions 80
```

Ordinary runs omit `--allow-live-ai`; replay never permits it. Explicit AI batches
have at most five cases, one supported-model capability lookup, max three scoped
generation calls, max one per investigation and 160 output tokens, no key/model
fallback or retries. Suggestions never become evidence. A shared SQLite ledger and
cooldown remain authoritative. AI success is not research success.

Keep the host awake; the Windows audit process requests thread execution-state
only and releases it, without changing the power plan. Observation deadlines are
not worker cancellation. Do not retry a disconnected POST until its real worker
has finished. Preserve failure events and source-level errors.

## Acceptance review

Compare queries, provider observations, URL counts, read attempts, captures,
structural articles, raw words, duplicate removals, qualified passages and findings
separately. Inspect exact publisher URLs, dates/basis, hashes and citations.
Different hosts do not prove source independence; HTTP 200 does not prove research.
Read failure differs from a captured article rejected for subject/date/objective.

Run full/fast Python, fatal lint, every Node frontend script, frozen verifier,
smoke and rollback checks per AGENTS after stabilization. Save fresh gate outputs
outside protected proof. Mark rendered-browser, hosted CI, historical archive and
deployed checks UNVERIFIED when not actually performed.
