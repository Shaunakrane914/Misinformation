# Security and useful-source yield continuation — 2026-10-23

## Start here / status

[Detailed report](../testing/SECURITY_READER_OPPORTUNITY_AND_YIELD_2026-10-23.md) ·
[Selected live measurements](../testing/evidence/2026-10-23_hardening_reader_yield/measurements.json).

User requested vulnerability repair, larger/useful capture and repeated testing.
**Known defects repaired; offline suites green; overall research PARTIAL.**
Do not claim all vulnerabilities solved or all four agents complete.
No commit, push, merge or deployment. HEAD unchanged:
`39a514b68388450bbc5e6061aba97bda2077fc7f`, branch
`fix/p0-lenovo-acquisition-20261018`, inherited dirty work preserved in
`.scratch/phase9-remediation-20261016`.

## Implementation map / rationale

- [Shared HTTP budget](../../backend/infrastructure/acquisition/network/budget.py):
  locked discovery/read phase accounting reserves reader opportunity without
  increasing total/host/security ceilings.
- [Harvesting](../../backend/services/research/harvesting.py): truthfully stop
  unsubmitted discovery after reserved capacity, honor existing 20K capture
  requests rather than accidental 12K clamp, allow bounded **observed** publisher
  hub continuation for all four domains.
- [Publisher result fit](../../backend/infrastructure/acquisition/adapters/web/search_observations.py):
  a matching opaque wrapper is not a resolved publisher URL; the existing next
  provider can run. Ordinary discovery wrappers and title relevance stay intact.
- [Harvest projection](../../backend/application/research/harvest_pipeline.py):
  distinct source rejections and post-read losses are not navigation counts.
  [Diagnostic/wording decisions](2026-10-23_ACQUISITION_DIAGNOSTICS_REPAIR.md)
  cover no-mutation report assembly, raw/qualified separation and non-threatening
  product-safety wording.
- [Passage/currency decisions](2026-10-23_PASSAGE_SIGNAL_CONTROLS.md):
  remove question/title/logistics false findings, preserve exact result spans;
  bare dollars do not become USD. Issuer/period entailment remains partial.
- [Event security](../../backend/api/events.py),
  [Huginn](../../backend/infrastructure/acquisition/adapters/events/huginn.py):
  auth-first bounded ingestion, offloaded blocking I/O, idempotent persisted
  events, honest non-independence and conflict/failure statuses. Disabled by
  default. Shared-token auth is **not HMAC signing**, correcting older docs.
- [Firecrawl](../../backend/infrastructure/acquisition/adapters/web/firecrawl.py)
  and [Jina](../../backend/infrastructure/acquisition/adapters/web/jina.py):
  sanitized errors/origins and terminal upstream-denial handling; no bypasses.

Regression pointers:
[reader budget](../../tests/unit/test_reader_opportunity_reservation.py),
[resolution](../../tests/unit/test_publisher_resolution_transport.py),
[optional security](../../tests/unit/test_optional_reader_security.py),
[diagnostics](../../tests/unit/test_oct23_acquisition_diagnostics.py),
[passages](../../tests/unit/test_oct23_passage_signal.py),
[domain wording](../../tests/unit/test_specialist_domain_wording.py).

## Actual results, not an acceptance shortcut

Exactly six approved local AI-disabled DEEP investigations were consumed:
four named cases plus Mary Barra and Dyson once more after final fixes.
Each <=240s / 24 reads / 120 native helper admissions, no paid Firecrawl,
supplied URLs or audit-level retries. All six completed SSE results. Zero AI.

First four: 23 article bodies / **29,089 raw article words**, versus the older
12 bodies /11,952 snapshot under smaller bounds. Not a controlled benchmark.
Adobe: 13 qualified records,650 selected words; Dyson:1/48;
battery recycling:1/28; Mary Barra:0/0.
Last two: Dyson remains1/48 with corrected safety wording; Mary remains0/0
despite nine raw captures. More homepage text is not improved task intelligence.

First-four fingerprint `0430b4b49f0aff586a12e2f5fbbbe4a402b98e276645e1b937fe4a58a3c9eb3f`;
last-two/final fingerprint `7ac1b23a84c9798074933f93f99c253d428bf3cd1f2b32dc80446e50f5256bcd`.
Both batches stable. Do not describe the first four as final-code live proof.

Final checks: full **2,124 passed /69.58s**, fast **1,916 passed /63.36s**;
fatal lint0; nine Node scripts pass; smoke OFFLINE_SMOKE_PASS;
rollback OFFLINE_PERSISTENCE_PASS with historical archive/deployed rollback
NOT_VERIFIED; frozen hashes/protected tracked diff/whitespace clean.
Read-only focused review:32 passed, no new scoped blocker. Full commands,
intermediate failed attempts, limitations and evidence basenames are in report.
No hosted CI, new browser or production tests ran.

## Next agent / owner actions

Personal Watch remains the principal sampled failure: three unresolved publishers,
eight unread opaque leads and only a task-irrelevant appointment article after
the final rerun. Start with saved observations, not another unrestricted sweep.
**All six network permissions are consumed.** Ask for a new small bounded batch
only after another concrete offline repair. Never relax relevance/access checks
or manufacture identity-threat findings to fill a quota.

Broader financial accuracy, genuine brand-threat positives, multi-source trend
measurement, complete HTTP accounting, dependency/pentest security coverage and
independent citation review remain open. Historical malformed dossiers are
protected/unrecovered, not certified by isolated rollback smoke. Deployment is
not authorized by this continuation.

Use skills backend-security-coder, debugging-strategies and
python-testing-patterns: they guided auth/size/failure guards, measured
offline-first reproduction and adversarial tests. Preserve raw evidence and
keep synthetic/replay/live claims distinct.
