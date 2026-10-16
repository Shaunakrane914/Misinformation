# Phase 9 evaluation integrity checkpoint — 2026-10-16

The inherited 88-case benchmark is a supplied-reference reasoning replay, not
live retrieval or independently measured misinformation accuracy. None of its
labels records human review. Keep development, regression and held-out cases
separate; no held-out examples were inspected to tune this remediation.

The old runner imported reference authority into runtime evidence, counted
nonempty citations as valid, and excluded abstentions from SUPPORT false
negatives. Its zero-error claims are not calibrated accuracy evidence.

The corrected runner defaults to runtime source classification. Explicit
`--reference-authority` retains the old oracle mode for historical reproduction.
Citation checks now join IDs, URLs and literal supplied excerpts, **not** logical
entailment. Abstention on a TRUE label counts as a support false negative;
permitted abstention and correct abstention are distinct. Binary precision/recall
are restricted to TRUE/FALSE labels; broader unsupported-support counts include
insufficient references. Undefined metrics stay null. Retrieval recall,
independent entailment and calibration remain unmeasured.

## Comparable baseline before application changes

| Split | Cases | Resolved / eligible | Unsupported SUPPORT | TRUE not supported |
|---|---:|---:|---:|---:|
| Development | 38 | 22 / 31 | 0 | 2 |
| Regression | 20 | 17 / 20 | 0 | 1 |
| Held-out | 30 | 8 / 28 | 0 | 8 |

Full baseline observations and dataset hashes are in
[the append-only evidence directory](evidence/2026-10-16_phase9_remediation/).
Captured against checkpoint `9e5b6e3` plus the runner-only changes, before the
application fixes. Historical oracle-mode reports remain untouched. The
application checkpoint preserves the previous uncommitted report work; it is
not deployed main acceptance.

## Reproduction

```powershell
python -m pytest tests/unit/test_phase9_evaluation_integrity.py -q
python scripts/evaluation/run_phase9_benchmark.py --split dev --output-dir "$env:TEMP/aegis-evaluation-new-run"
```

Choose a fresh output directory for each run. The runner requires an explicit
output path and refuses to replace existing result files. Never write over
tracked benchmark proof or change frozen retrieval labels to improve scores.

Subsequent application results, tradeoffs and live/browser limitations belong
in the remediation acceptance report, not retroactively in this baseline.
