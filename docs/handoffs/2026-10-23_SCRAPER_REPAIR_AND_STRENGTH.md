# Firecrawl / conservative interpretation / native scraper-strength handoff

Date: 2026-10-23. User asked to repair Firecrawl and the other review issues,
leave Huginn unused, and measure scraper yield/relevance.

Actual checkout: `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, base HEAD `39a514b68388450bbc5e6061aba97bda2077fc7f`
plus substantial inherited uncommitted work. No commit/push/merge/deployment.
Do not follow the older handoff's conflicting branch/base or enablement advice.

Read the [complete report](../testing/SCRAPER_REPAIR_AND_STRENGTH_2026-10-23.md)
and [machine measurements](../testing/evidence/2026-10-23_scraper_strength/measurements.json).

## Implemented

- Firecrawl uses the existing pinned/budgeted HTTP stack through a new
  single-attempt, no-redirect POST helper. Missing imports, byte truncation,
  raw-text/optional HTML structure, canonical metadata, publication/depth and
  source-role overclaims corrected. A configured endpoint is not live-verified.
  Background remote crawl jobs fail closed; public HTTPS policy is unchanged.
- Reader fallback stops on denial/challenge/throttling/security/budget failures
  and respects the caller's original deadline.
- Financial percentages are not money; explicit scales/currencies/spans and
  comparison roles are preserved. Fiscal period metadata is conservative;
  period matching never emits `FILING_VERIFIED` for unverified amounts.
- Two promising publisher leads no longer suppress later discovery before
  any body is acquired. All original capacities/security gates remain.
- Huginn is not imported/registered in normal startup without explicit enablement
  and configuration. Its deeper defects are deferred, not claimed repaired.
- Normal tests/native audits blank Firecrawl credentials and isolate optional
  storage. `.env` and provider access approvals were not changed.

Regression pointers: [27 new adversarial controls](../../tests/unit/test_oct23_scraper_repairs.py),
[Firecrawl](../../tests/unit/test_firecrawl_adapter.py),
[staged discovery](../../tests/unit/test_staged_query_planning.py),
[financial reconciliation](../../tests/unit/test_scout_primary_source_reconciliation.py).
The optional Huginn router test explicitly constructs an isolated app; it does
not require enabling monitoring in the actual application.

## Actual results / interpretation

- Focused: 88 passed, exit 0. Full: 2,018 passed / 1 failed, exit 1.
  Fast: 1,810 passed / 1 failed, exit 1. Same remaining failure is the disabled
  Huginn raw-pool duplicate marker; not skipped or hidden.
- Fatal lint: zero. Nine Node frontend scripts pass. Smoke and isolated rollback
  pass; historical archive/deployed rollback remain unverified. Frozen hashes
  match and protected tracked paths have no diff. Full commands/timings and
  intermediate failures are in the report; these are dated results, not targets.
- Exactly four authorized native cases, once each, 180s/16 reads/80 native HTTP
  admissions each. Zero AI/capability probes, paid Firecrawl, retries or production
  mutations. Code hash stable throughout the live batch.
- Raw article yield: Adobe 9 bodies/9,460 words; Dyson 0; battery recycling
  2/2,008; Mary Barra 1/484. Only Adobe has code-qualified evidence, with passage
  quality defects still visible. Raw acquisition is not the same as correct
  intelligence. No whole-project/release PASS is claimed.

## Resume order

1. Fix misleading rejection/first-loss projections using saved responses.
2. Improve bounded search-versus-read opportunity, observed publisher resolution
   and fresh/task-specific article priority; preserve host/access restrictions.
3. Reject quiz/questions as financial propositions and improve the executive
   brief. Keep background/appointment context separate from actual threats.
4. Re-evaluate captured bytes offline, with zero model calls. Further live
   verification needs new approval: these four permissions are consumed.
5. Keep Huginn disabled. Do not confuse passing native regressions or source
   counts with its security/provenance acceptance, independent accuracy or CI.

All original dossiers, frozen benchmarks, research/artifact trees, working
scrapers and shims are preserved. This is an engineering decision/result log,
not a private reasoning transcript. Raw native evidence remains in new temp
basename `aegis-native-strength-22672d05ff0849d19830f006ba744ae2`; it may expire.
