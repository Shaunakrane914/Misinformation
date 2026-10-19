# Patient research window — 2026-10-19

## User scope and decision

The user explicitly requested more time and removal of premature cutoffs after
the acquisition repair. This supersedes the earlier P0 instruction not to raise
timeouts. Short **whole-investigation and multi-step chain cutoffs** are extended;
individual HTTP safety limits, worker isolation, finite fan-out, source policy,
response caps and AI budgets are not removed.

Branch/base: `fix/p0-lenovo-acquisition-20261018` / `9df3c37`.
The worktree was clean before this change. Previous dossiers and benchmark proof
remain untouched. No merge or deployment is part of this task.

| Boundary | Previous | New default |
| --- | --- | --- |
| Entire research pipeline | 20s server / 25s environment-loaded desktop | 120s both |
| Discovery slice | Usually cut at 9–10s | Up to 54s |
| Multi-step provider/read chain | 5s | 15s |
| Publisher URL lookup within a read | 2s | Up to 5s, still inside that read's deadline |
| Individual HTTP request | Existing bounded calls, normally at most 5s | Unchanged |
| Frontend analysis wait | 300s | Unchanged; longer than backend default |

This is **not unlimited waiting**. Research may finish before 120s when its
bounded work is complete or novelty is depleted. A blocked transport cannot own
a worker forever, and spending more time does not manufacture accessible bodies.
The change was announced as a two-minute window before implementation.

## Implementation and reasoning

- [ResearchBudget](../../backend/services/research/research_budget.py) uses
  120s / 15s defaults in both dataclass and environment factory. Explicit request
  budgets and environment overrides still work, including intentionally short
  regression controls. Query/read counts and maximum retries are unchanged.
- [Broad discovery](../../backend/application/research/acquisition.py) no longer
  applies a hidden `channel_timeout * 2` cap. It receives the actual remaining
  discovery slice and passes the chain timeout explicitly into shared retrieval.
  This allows queued work and multiple bounded fallback calls to finish without
  consuming the protected reading reservation.
- [Adaptive worker](../../backend/application/research/adaptive.py) installs the
  cooperative deadline inside its offloaded thread; context variables otherwise
  do not propagate automatically into executor threads.
- [Deep reader](../../backend/services/research/deep_reader.py) permits up to 5s
  for the one publisher-headline lookup. Its 15s read-chain budget leaves time
  for the publisher read afterward; the former 5s whole-read cap could discard
  useful later steps. Existing caller-requested shorter budgets still win.
- [Example configuration](../../.env.example) documents general and server/local
  override names. [Render blueprint](../../render.yaml) specifies server 120s / 15s
  for a future authorized rollout. No Render dashboard or running service was
  modified. Existing manually configured shorter values must be reconciled at
  rollout; code defaults alone do not prove deployed configuration.
- Six [new offline tests](../../tests/unit/test_patient_research_budget.py)
  cover server/desktop defaults, override precedence, hidden-cap removal,
  reading after 40s, and compatibility with the existing frontend wait.

The golden test's explicit historical 20s profile now also pins its original
5.0s channel budget. The first targeted run had 11 result-hash mismatches from
changing a fixture default; a second attempt used integer 5 instead of float
5.0, also changing serialized bytes. Correctly pinning the historical float
preserved every manifest. No frozen data, labels or expected hashes were edited.
The new production defaults are tested separately, not hidden by this fixture.

## Actual bounded live verification

One Tim Cook investigation ran through the normal local ASGI/SSE endpoint with
isolated temporary storage, background ingestion off, no notifications/remote
writes, mock generation false and AI credentials excluded. No POST retry.

- Backend log confirms `timeout=120.0s`.
- HTTP 200/result event after **36.02s**; 29 progress events and six heartbeats,
  no SSE error events. This is transport completion, not research acceptance.
- Discovery took 20.949s, adaptive work 11.280s and reading 3.601s.
- All **12** initial/adaptive queries started and returned SUCCESS. Query success
  does not prove a relevant acquired body.
- Reading began with **69.747s** before its stage ceiling; 84.130s remained in
  the total budget after processing. It was not cut off by the old 20s timer.
- Adaptive expansion stopped on marginal novelty (`0.05 < 0.08`), not a clock
  deadline. One profile record (8 words / 0.059 decimal KB) was retained; three
  article-wrapper resolutions remained unresolved after about 2.6–3.6s.
- No qualified findings. The extra time did **not** solve specialist source
  acquisition; research-quality acceptance remains incomplete.

Raw temporary outputs are in system-temp
`aegis-patient-research-5054b075-94aa-4227-b476-cd20dc2559f2`.
The application stayed unchanged throughout the live and replay runs.
Zero requested live AI/model-list calls; upstream account accounting unobserved.

Using the end-to-end testing skill, the exact saved SSE was replayed through
the actual Personal Watch page at 320/390/1440px, without another investigation.
All three states passed report/count, finding-text, overflow, source keyboard
inspection and page-exception checks. A 390px screenshot was visually inspected.
Blocked font and static-resource console errors remain disclosed in the runner
output; not a full accessibility, all-browser or production validation.
[Evidence index](../testing/evidence/2026-10-19_patient_research/README.md).

## Commands and observed validation

Executed summaries, not a raw transcript:

```text
python -m pytest tests/unit/test_patient_research_budget.py tests/unit/test_research_pipeline_golden.py -q --tb=short --show-capture=no
python -m pytest tests/ -q --tb=short --show-capture=no
python -m pytest tests/unit tests/chaos tests/security -q --tb=short --show-capture=no
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
python scripts/validate_release_candidate_smoke.py
python scripts/validate_rollback_compatibility.py
python scripts/validation/verify_frozen_benchmarks.py
```

18 focused cases passed; **1,474 full (64.15s) / 1,266 fast (46.04s)** passed.
All exit 0. Fatal lint zero errors; all nine frontend Node contract files ran
separately and passed. Isolated smoke/persistence and frozen hash checks passed.
Historical archive recovery and actual deployed rollback remain unverified.
Protected tracked data paths have no diff. Relative documentation links and
whitespace are checked before publication.

The live command used `SERVER_MODE=1` for its subprocess, then:

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file <existing-env> --output-dir <fresh-dir> --case "personal_watch:Tim Cook"
python scripts/audits/run_phase9_four_agent_browser_audit.py --env-file <existing-env> --output-dir <fresh-browser-dir> --chart-js <pinned-chart-js> --replay-dir <saved-dir> --case "personal_watch:Tim Cook"
```

Both exited 0; neither is research-quality PASS. No `--allow-live-ai`.

## Publication / remaining work

At this local-verification snapshot changes are uncommitted/unpushed. Any later
fix-branch commit and hosted CI outcome must be recorded below. No main merge
or deployment is authorized by a generous timeout or passing offline suite.
Source-selection/publisher-resolution failures still need independent work;
do not keep increasing budgets as a substitute for acquiring relevant evidence.

### Published checkpoint and observed CI

Application `69b48d64bc7ec8146a2da18bec5b8170dc7c861c` was committed and pushed
only to the existing fix branch. [Hosted run 39217416499](https://github.com/Shaunakrane914/Misinformation/actions/runs/39217416499)
passed all five jobs at that exact SHA. `gh run watch --exit-status` exited 0;
the run conclusion was checked separately. This includes full offline tests,
Python 3.11/3.12/3.13, frontend contracts and release validators.

Main remained `8471ee349efd48644519d3a8fecde2e724ebf6ae`; no merge/deployment.
This later ledger update is documentation-only and does not predeclare CI for
its own commit. Earlier uncommitted wording records the local snapshot. The
live result remains profile-only and research acceptance remains incomplete.
