# Acquisition diagnostic projection repair — 2026-10-23

## Scope and status

Focused portion of the user-requested scraper repair: distinguish actual source
capture, qualification and publisher-link auditing; never inflate source counts
with navigation decisions or interpret an empty evidence list as empty acquisition.
This is implemented/offline-verified, not a fresh live recall or accuracy result.

Observed checkout: `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, plus preserved inherited dirty work.
No commit, push, merge, deployment, AI call, live provider call or protected-data
change was performed by this diagnostics work.

## Changes and rationale

- [Discovery funnel](../../backend/services/research/discovery_funnel.py):
  `summarize_qualification_decisions` separates parent-link audits from candidate
  rejection decisions, counts distinct URL/ID identities before diagnostic sample
  truncation, and preserves explicit stage/reason observations. A single rejected
  source may have multiple reasons; these counts must not be summed as disjoint
  source populations. Unknown-identity decisions remain observations, not invented
  source IDs. Repeated provider URL decisions no longer inflate unique sampled URL
  counts. Completed reads cannot point backward to candidate qualification simply
  because the post-read accepted list became empty.
- [Acquisition status](../../backend/services/research/acquisition_status.py):
  optional `raw_capture_count`/`qualified_count` preserve the distinction between
  transport failure and captured-but-ineligible content. Existing caller behavior
  remains compatible when those values are unavailable.
- [Report builder](../../backend/services/report_builder.py): expose raw capture,
  article and final displayed-qualified counts separately. Explain actual read
  failures and qualification decisions instead of `UNSPECIFIED: 100`. Reproject
  stale saved failure statuses conservatively if stronger raw capture observations
  exist, preserving the originally reported status. Prefer an eligible target
  financial performance assertion for the brief when its metadata exists; retain
  exact paragraph text, attribution, forecast/history scope and uncertainty.
- The saved replay also reproduced an input-mutation defect: report construction
  appended raw discovery records into the original corpus `ranked_candidates`
  list (Adobe: 49 to 89). Copy the working list before extending it; report
  construction no longer changes the input payload.

Root orchestration integrates normalized rejected/link counts into acquisition-first
legacy corpus/trace funnels separately; its verification is not claimed here.

## Actual offline checks

```text
python -m pytest tests/unit/test_oct23_acquisition_diagnostics.py tests/unit/test_autonomous_discovery_funnel.py tests/unit/test_completion_report_projection.py tests/unit/test_substantive_report_completion.py tests/unit/test_p0_acquisition_reliability.py -q --tb=short -p no:cacheprovider
```

Exit 0: **102 passed in 1.77 seconds**; 17 controls are new in
[the dedicated regression file](../../tests/unit/test_oct23_acquisition_diagnostics.py).
An earlier run before adding the no-mutation regression passed 101 tests. The
first saved-response reprojection stopped on the mutation assertion; it was not
passed off as a successful replay.

```text
python -m flake8 backend/services/report_builder.py backend/services/research/discovery_funnel.py backend/services/research/acquisition_status.py tests/unit/test_oct23_acquisition_diagnostics.py --count --select=E9,F63,F7,F82 --show-source --statistics
```

Exit 0: zero fatal findings. Targeted `git diff --check` also exited 0.

Existing genuine responses from the system-temp tree named
`aegis-native-strength-22672d05ff0849d19830f006ba744ae2` were read and reprojected
with external network blocked, isolated temporary runtime, empty credentials and
no writes to saved bodies, responses or dossiers. Reprojection completed without
changing any of the four in-memory input payloads:

| Saved case | Raw captures | Articles | Displayed qualified sources | Reprojected status |
| --- | ---: | ---: | ---: | --- |
| Adobe | 10 | 9 | 9 | COMPLETED |
| Dyson | 4 | 0 | 0 | INSUFFICIENT_EVIDENCE |
| battery recycling | 7 | 2 | 0 | INSUFFICIENT_EVIDENCE |
| Mary Barra | 1 | 1 | 0 | INSUFFICIENT_EVIDENCE |

Dyson's summary now reports its four raw captures, zero articles, three publisher
resolution failures and one provider failure; it no longer calls 100 sampled
navigation observations candidate-qualification rejections. Its old sample
contains only the first 100 audit rows, so replay does not claim to recover every
omitted historical decision. Fresh runtime computes counts before truncation.

The original Adobe findings still contain its old multi-company earnings-list
paragraph; display-only replay cannot fabricate the later improved passage
selection/metadata. Passage-selection changes are owned and tested separately.

## Post-batch specialist wording correction

After the subsequent four-case live batch completed, root delegated a small
additional repair based on its saved Dyson result. The live source calls were
performed by root, not by this subtask. No new source or model request was made
for this wording correction.

- [Specialist brief](../../backend/services/research/specialist_brief.py) now
  gives BrandShield brand/source coverage limitations rather than displaying
  profile counts and media-forensics limitations borrowed from Personal Watch.
  Personal Watch retains its domain-relevant identity/media wording unchanged.
- [Brand interpretation](../../backend/agents/brandshield/intelligence.py)
  uses product-safety/recall wording when a `PRODUCT_SAFETY` observation also has
  actual acquired recall/safety prose. It does not call that reporting an
  observed scam. `is_threat=False`, no actor URL and exact supporting spans remain.
  The correction-only regression exposed a singular `recall` matcher missing
  `recalled`/`recalls`; those ordinary forms are now recognized without increasing
  epistemic status or authenticating the report.

```text
python -m pytest tests/unit/test_specialist_domain_wording.py tests/unit/test_brand_source_context.py tests/unit/test_brand_incident_precedence.py tests/unit/test_specialist_completion.py tests/unit/test_completion_report_projection.py tests/unit/test_oct23_acquisition_diagnostics.py -q --tb=short -p no:cacheprovider
```

Final exit 0: **71 passed in 0.85 seconds**, including six new
[domain-wording controls](../../tests/unit/test_specialist_domain_wording.py).
The initial run was 70 passed/1 failed due to the inflected-recall omission; it
is not represented as a pass. Fatal lint for the two implementation files and
the new test file exited 0 with zero findings.

An offline, network-blocked, isolated reprojection of
`aegis-hardening-yield-a5abf902b68549aabd022efa70ddaba1/02-brandshield.json`
then confirmed removal of the misplaced profile/media-forensics language and
preservation of the exact source correction, including "only some toothbrushes"
and company response attribution. The normalized native observation stayed
unverified/non-threatening, with no actor URL. Saved data and in-memory input
were unchanged. This is presentation/interpretation replay, not a post-fix live
investigation or a correctness verdict on the publisher's product claim.

## Limits / next agent

These controls do not establish source accessibility, useful fresh article recall,
financial truth, provider health, independent accuracy, browser rendering, full
regression or deployment readiness. Preserve raw source content and frozen data.
Keep unknown/censored diagnostics labeled as samples. Reserve meaningful reader
opportunity and measure body qualification separately from query execution.
