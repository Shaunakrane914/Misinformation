# Release reconciliation and actual benchmark recovery — 2026-10-28

User scope: reconcile the October 28 development session with released `ec5bef1`,
review security, recover both 20-case attempts where possible, replay actual
Tim Cook/Russell Brand material and verify without another live batch. No commit,
push, merge, deploy, secret changes, paid readers or fresh model/provider calls.

Implementation stays on `fix/personal-evidence-20261028`, HEAD
`8b5a9a55a8df030ccb86ccbd1f99be959e6885d7`, plus preserved previous dirty work.
The original root is `feat/phase8-real-acquisition-proof` / `222a4ad`; remediation
is `release/specialist-task-20261024` / `7ad13a5`, extensively dirty. Root initially
had 13 modified source files; two additional edits appeared during review. None
was overwritten. All 13 initially observed root source hashes remain unchanged.
Current snapshots/diffs do not attest exact code used by historical benchmarks.

Read the [full reconciliation](../testing/OCT28_RELEASE_RECONCILIATION_AND_BENCHMARK_AUDIT.md)
and [evidence index](../testing/evidence/2026-10-28_reconciliation/README.md).

## Decisions and code changes

Most root metadata/body/query/URL work is already present or more safely bounded
in `ec5bef1`. Do not copy the older root tree over the release lineage. Do not
port root 401/403/429-to-reader fallback, context-losing concurrent feed requests,
DNS slot expansion or the late deadline floor extending an expired request.
The entertainment pulse adapter exists in the root, but universal Trending
routing to it is not proof of topic coverage or permitted article access.

Useful port: successful empty subreddit RSS caching. The released function also
used a direct unbounded `urlopen/read`, bypassing shared HTTP admission and
pinned validation. Corrected `adapters/social/reddit.py` to use existing bounded
HTTP, one attempt, zero redirects, strict subreddit syntax and capped entries.
Access/200-denial pages remain typed failures; denial cache hits preserve status
with no new network attempt. `routing/social_handlers.py` no longer swallows
those failures and activates another reader. No source permission flag changed.

Eleven new security regressions plus existing transport/redirect/DNS/source
checks cover the behavior. Two mirror test fixtures now explicitly disable the
unrelated RSS path they do not mock; no denial control was relaxed. Added a
read-only `scripts/audits/reconcile_saved_benchmark.py` and two metric-integrity
tests. No historical dossier or frozen fixture was repaired/rewritten.

## What the recovered evidence establishes

One complete 20-case aggregate exists at the root protected artifact path,
timestamp `2026-10-28T07:43:29.246117+00:00`. Its original bytes/hash are preserved.
Three ordered 20-engine dossier sequences were found, including the previous
06:59:12–07:06:05Z and latest 07:32:18–07:43:29Z sequences. Earlier aggregate/log/
runner exits were not recovered; completed engine dossiers are not proof of a
completed benchmark runner. The script overwrites one result filename.

Its “deep_reads” are depth-labelled returned records, “unique_words” is vocabulary,
and “total_words” includes snippets. Actual read attempts, HTTP admissions, article
body structure/dates and qualified passage words are unavailable for these runs.
Keep those metrics unknown, not replaced with raw counts or inferred zeros.

The separate Tim demonstration says six deep-read documents but preserves only
24–204-character snapshots with hashes, no read ledger/full bodies. The later
complete batch returns zero Tim records. Six actual reads and three full articles
remain NOT VERIFIED. Russell snippets concern allegations and reported denials,
but lack body/date proof; they do not establish current developments or a verdict.

Ten offline API/SSE replays compared identical saved inputs against a read-only
`ec5bef1` export and current code. All four snippet sets yield zero qualified
sources/words in both. A separate genuine October 25 Tim transcript control yields
547 passage words in both; current native attribution lists 15 statements versus
zero in release. This restores enumeration, not acquisition/word growth. Ten
browser states match, with inspected Tim historical/Russell empty screenshots.

## Actual final checks

- Targeted acquisition/security/reconciliation subset: **95 passed**.
- Mirror fixture-scope + new security rerun: **49 passed**.
- `python -m pytest tests/ -q`: exit 0, **2,844 passed / 121.41s**.
- `python -m pytest tests/unit tests/chaos tests/security -q`: exit 0,
  **2,636 passed / 97.32s**.
- Fatal flake8 E9/F63/F7/F82: exit 0, zero fatal findings.
- Ten frontend Node scripts, frozen verifier, isolated smoke/persistence,
  protected-tree and whitespace checks: exit 0.
- Ten native/API/SSE replays and ten local browser states: passed, zero live
  acquisition/model calls. Readiness responses are replay stubs.
- Initial full/fast: four fixture-scope failures, 2,840/2,632 passed. Preserved,
  corrected and rerun; not represented as passes.

Original archive syntax inventory: **2,543 readable JSON, 55 malformed**. Those
files remain protected and failed, not silently recovered. Isolated persistence
does not verify historical archive integrity or deployed rollback. No remote CI.

## Remaining barriers

No newly demonstrated qualified Tim/Russell word increase over production.
Preserve the prior production observations as separate subjects/source sets,
not paired before/after claims. All four agents still need source-level review:
Scout financial adjudication, BrandShield specific incidents, Trending current
dated article/time-series evidence, and Personal Watch broader attributed sources.
The next evidence requirement is a complete bounded native capture with actual
read/HTTP records, body structure, exact passage offsets and code fingerprint.
No additional 20-case live batch or deployment is authorized by this handoff.

All changes remain uncommitted/unpushed. Full temporary artifacts/logs use
system-temp basename `aegis-oct28-reconciliation-u098c0ob`; selected summaries and
images are durable in the evidence folder. Temporary files may expire.
