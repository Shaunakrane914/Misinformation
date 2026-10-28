# Read allocation and speaker attribution handoff — 2026-10-26

User approved the plan-first repair after Trending repeatedly returned zero. Worktree: remediation checkout, branch `release/specialist-task-20261024`, base `7ad13a5` plus preserved uncommitted work. **Nothing committed, pushed, merged or deployed.** Existing user edits, historical records and frozen benchmark files remain protected.

Read the [pre-implementation policy](../testing/READ_ALLOCATION_POLICY_2026-10-25.md), then [results and code map](../testing/READ_ALLOCATION_RESULTS_2026-10-26.md) and [durable evidence](../testing/evidence/2026-10-25_read_allocation/README.md). The earlier zero-result reports remain historical evidence, not the newest result.

## What is established

- Battery recycling now autonomously reads a fresh ECS publisher article and displays 185 exact cited words. Four authorized live cases used 334 native HTTP admissions, no investigation retries.
- Semiconductor manufacturing remains zero qualified evidence. Mary Barra remains 114 historical words. Tim Cook's original 204 words were transcript introductions: the offline correction retains 547 actual speaker words from one historical 2020 transcript, not fresh current coverage.
- Three bounded Gemini suggestions succeeded, 1,167 provider-reported tokens. A fourth reservation was denied locally; no ledger reset or extra generation call.
- Final full/fast suites: 2,574 / 2,366 passed, exit 0. Fatal lint, ten Node scripts, isolated smoke/persistence and frozen checks pass within their documented scopes. Eighteen saved-response browser states and 24 passage observations pass rendering/integrity checks. Historical archive recovery/deployed rollback remain NOT_VERIFIED.

## Code ownership and regression pointers

New `publisher_read_policy.py` partitions the unchanged host budget between discovery and articles. `pipelined_acquisition.py` applies feedback only to actual article/document outcomes and reserves an existing query slot for delayed advice. `candidate_selection.py` handles reordered topic tokens and weak statement routing; `harvesting.py` propagates observed feed hints. None of these accepts search snippets as acquired bodies or weakens final date/subject/security gates.

`content_roles.py`, `passage_records.py` and `evidence_workbench.py` now distinguish transcript editorial introductions, speaker rosters and observed speech. Next-speaker boundaries precede author shortcuts. `identity_authenticated` remains false. `rebuild_saved_workbench.py` creates evidence-only offline projections with empty findings, preserving original captures.

Regression owners: [allocation tests](../../tests/unit/test_publisher_read_allocation.py), [speaker tests](../../tests/unit/test_transcript_speaker_sections.py), and their labeled genuine Tim Cook fixture. Eighteen tests cover allocation/attribution; existing pipeline/specialist tests remain. The final generic unusable-article feedback and speaker changes postdate the live application fingerprint and have **offline proof only**.

## Portable verification

Run normal offline checks without live AI/source requests:

```text
python -m pytest tests/unit/test_publisher_read_allocation.py tests/unit/test_transcript_speaker_sections.py -q
python -m pytest tests/ -q
python -m pytest tests/unit tests/chaos tests/security -q
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
python scripts/validation/verify_frozen_benchmarks.py
python scripts/validate_release_candidate_smoke.py --output <fresh-temp-json>
python scripts/validate_rollback_compatibility.py --output <different-fresh-temp-json>
```

Run each Node `tests/frontend/test_*.js` script. See the results report and machine-readable command evidence for actual execution counts/timings. Do not reuse tracked evaluation output paths. The saved-body workbench tool supports `--help`; output must be a new path and clearly labeled offline. It cannot demonstrate fresh discovery or regenerate accepted agent verdicts.

## Next decisions

First inspect semiconductor's saved stock/company-page drift and Personal Watch's current statement-source gaps. Do not expand caps, remove freshness gates or describe historical statements as current threat intelligence. The approved four live cases and three advisory calls are consumed; request a small explicit new case budget before further live acquisition. No production changes are authorized by this handoff.

Temporary complete logs are under basename `aegis-read-allocation-o6nqsake`; durable selected evidence is linked above. Initial nonexistent-test invocation and fixture-control failures are disclosed in the results report. This is a reconstructed engineering handoff, not a raw transcript or private reasoning trace.
