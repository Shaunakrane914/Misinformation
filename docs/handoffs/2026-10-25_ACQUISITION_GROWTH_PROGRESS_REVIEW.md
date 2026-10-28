# Acquisition growth progress review — 2026-10-25

Scope: review the user's significant local progress and continuation transcript. Reviewed
`release/specialist-task-20261024` at `7ad13a5` plus preserved uncommitted changes in
`.scratch/phase9-remediation-20261016`. No application code, credentials or access flags changed.

[Full review, reproduction details and actual commands](../testing/ACQUISITION_GROWTH_PROGRESS_REVIEW_2026-10-25.md)
records five findings: late worker candidate mutation, interrupted-read accounting, replay admission
provenance, missing AI hook in `pipelined_v1`, and undeclared resource-sampling dependency.

Current offline full/fast suites: **2,540 / 2,332 passed**, fatal lint and ten Node scripts pass;
smoke/frozen/isolated persistence checks pass within their documented scope. Two additional offline
diagnostics reproduce defects not covered by those passing tests. No new live or model requests.

Existing 72-run replay aggregate: legacy 51 qualified /2,899 selected words /572 modeled admissions;
two-worker pipeline 49 /2,774 /518. About 5.7% better modeled word efficiency, fewer total words;
neither 2× nor live improvement established. Fix cost/provenance modeling before relying on this ratio.

Next owner: isolate worker input and merge only eligible completed results; finalize all dispatched
attempts honestly; distinguish measured original admissions from replay estimates; connect the existing
strict advisory path to the experimental scheduler. Preserve genuine captures and qualification gates.
Then finish the measured pilot and independent passage review. Do not increase concurrency to paper over
the unresolved source-supply problem.

Only new review documents and a compact sanitized evidence aggregate were added by this review.
Application edits remain the user's. **No commit, push, merge or deployment.** Historical dossiers,
research/artifacts and frozen datasets preserved. Logs use fresh temporary paths; relative links are portable.
