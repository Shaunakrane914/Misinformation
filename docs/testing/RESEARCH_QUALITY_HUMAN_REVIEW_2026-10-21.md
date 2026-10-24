# Human review of frozen research observations — 2026-10-21

This supplements, not replaces, the
[independent reviewer packet](RESEARCH_QUALITY_REVIEWER_PACKET_2026-10-18.md).
Its 48 slots are still blank. The coding agent has not supplied independent ground
truth. Evaluation controls below are synthetic tooling tests, not accuracy results.

## Workflow

1. An independent reviewer selects the held-out inputs, expected three-state
   verdicts and relevant URLs using the existing packet. Preserve supporting
   passages/period/currency/context. Freeze the label file's exact bytes and
   SHA-256 **before** operator investigation or tuning. Use the existing label
   template and required reviewer/freeze declarations, not this coding agent's
   calibration examples. Exploratory investigations use the packet's separate
   rubric; do not force a synthetic true/false verdict onto them.
2. The operator obtains observations under a separately authorized small source
   budget. Normal testing has zero AI calls. Save exact acquired content, hashes,
   citation IDs and end-exclusive spans in the existing observation format. Save
   failures and abstentions too. Compute the observation file's exact byte hash.
3. Copy the new [blank review sheet](reviewer_packets/2026-10-21/human-reviews.template.json)
   to a fresh owner-selected file. Populate both hashes. Review actual acquired
   passages, not just titles, snippets, extracted numbers or URL availability.
   Record all three dimensions per case: `acquisition_quality`,
   `citation_entailment`, `usefulness`. Each judgment uses an explicit `status`
   (`PASS`, `PARTIAL`, `FAIL`, `NOT_VERIFIED`) and a concise `rationale`.
4. Add one entry under each case's `citations` per observed citation, using its
   zero-based `citation_index`, status and rationale. A valid exact span proves
   recorded text identity, not that it supports the full claim. Check negation,
   speaker, reporting period, currency, forecast versus actual, warning versus
   incident and whether sources share the same reporting origin.
5. When human judgments exist, set `review_origin` to `INDEPENDENT_HUMAN_REVIEW`,
   identify the actual reviewer, and record a timezone-aware ISO `reviewed_at`.
   `AGENT_CALIBRATION` is available only for honestly labeled tooling/calibration
   work. Do not declare completed judgments under a pending-review origin.

The blank sheet intentionally cannot be scored before valid label/observation
files and their hashes exist. Missing case rows, dimensions or citation reviews
remain `NOT_VERIFIED`, not successful reviews. Unknown/duplicate case IDs and
out-of-range citation indices are rejected. A case cannot claim entailment PASS
with broken spans, missing citation reviews, or a decisive uncited verdict.

## Portable command

```text
python scripts/evaluation/reviewer_acceptance.py --labels <frozen-labels.json> --labels-sha256 <separately-recorded-sha256> --observations <observations.json> --reviews <completed-human-reviews.json> --output <new-summary.json>
```

The output file must not already exist. Do not write into tracked benchmark
outputs, protected evidence or historical dossiers. The script makes no network
or model requests. It reuses
[`evaluate_research_quality.py`](../../scripts/evaluation/evaluate_research_quality.py)
for all automatic verdict/span/hash mathematics, including per-agent subsets.
It records label, observation and review file hashes to bind the assessment.

The summary separates automatic counts from human acquisition, entailment and
usefulness judgments. Zero denominators remain unknown. “Declared independent
review complete” means collection complete, not passed accuracy: FAIL judgments
can be complete too. Reviewer independence and pre-freeze timing are declarations
the script cannot prove. Acceptance thresholds must be chosen by the owner before
evaluation, not retrofitted after seeing scores. Research-quality and release
acceptance remain explicitly unverified pending that owner decision and the
separate deployment/rollback gates.

Tool contract tests:

```text
python -m pytest tests/unit/test_reviewer_acceptance.py tests/unit/test_research_quality_evaluation.py -q
```
