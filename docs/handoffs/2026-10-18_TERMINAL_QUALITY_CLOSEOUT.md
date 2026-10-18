# Terminal-first output / AI budget continuation — 2026-10-18

## Read first

[Review and exact limitations](../testing/TERMINAL_OUTPUT_AND_AI_COST_REVIEW_2026-10-18.md)
· [Measurements / screenshots](../testing/evidence/2026-10-18_terminal_quality/README.md)
· [Earlier implementation/cost incident log](2026-10-17_TERMINAL_POLISH_AND_AI_COST_CONTROLS.md).

Scope: improve specialist outputs using terminal iteration before browser checks;
user then objected to API usage, requested lower models for suggestions, and
later authorized one low-budget check of the latest `.env` key. No deployment,
credential/access-flag changes, main merge or archive recovery. Branch remains
`feat/continuous-source-intelligence-20261017`, base
`d1ffcaf7a4801b0c9f15377be0312838a65adea5`. Work is **uncommitted/unpushed**.
Preserve the current diff and untracked files; no new hosted CI claim.

## Code map / rationale

- `backend/agents/brandshield/agent.py`: unmatched records become background IDs,
  not invented “Genuine Issue” findings or safety counts. Preserve native sources.
- `backend/agents/personal_watch/assessment.py`: profile/metadata-only records
  do not trigger expensive native threat generation or synthetic fallback claims.
- `backend/services/agent_reach/source_planner.py`: separate specific public
  abuse queries; bounded strict Flash-Lite planning advice. Existing access gates.
- `backend/application/research/reading.py`: task-bearing specialist candidates
  get read priority, while the original ranked corpus is retained.
- `backend/infrastructure/acquisition/routing/router.py`: primary search returning
  only first-name matches does not disable the existing secondary search for an
  explicit quoted full name. Offline cases verify routing and candidate retention.
- `backend/services/research/specialist_brief.py` / `report_builder.py`: deterministic
  gap/coverage summaries and observed-lead next steps. No network or new verdicts.
  Metadata, generic content and keyword candidates are not corroboration.
- `backend/core/settings.py`, `evidence_advisor.py`: `LLM_ADVISORY_MODEL` default
  Flash-Lite, explicit model identity, one attempt / 320 output tokens / 2s;
  max four captured paragraphs totaling 2,400 characters. Raw text/IDs preserved.
- `backend/infrastructure/llm/providers/{gemini,rate_limit}.py`: fail fast on 429,
  allowlisted diagnostic category/delay, process-local cooldown, no immediate
  key/model waterfall. Not a distributed daily request/spending limiter.
- `scripts/audits/run_terminal_agent_quality.py`: normal local SSE acquisition
  with isolated persistence; no AI credentials unless separately opted in.
- `scripts/audits/run_phase9_four_agent_browser_audit.py`: same AI-off default;
  saved SSE replay and fingerprint includes untracked application files.
- `scripts/diagnostics/check_ai_advisory_runtime.py`: `--skip-model-list` allows
  one 96-token strict small-model generation without a listing request. Safe
  status/timeout extraction, not raw exceptions. Do not rerun without a clear
  request budget; a generation timeout is not a quota/key-invalidity diagnosis.

## Verification / commands actually run

Final current application, offline:

```text
python -m pytest tests/ -q
  exit 0: 1375 passed, 45.77s
python -m pytest tests/unit tests/chaos tests/security -q
  exit 0: 1167 passed, 23.99s
flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
  exit 0: 0 findings
python scripts/validate_release_candidate_smoke.py
  exit 0: OFFLINE_SMOKE_PASS
python scripts/validate_rollback_compatibility.py
  exit 0: OFFLINE_PERSISTENCE_PASS; archive/deployed rollback NOT_VERIFIED
python scripts/validation/verify_frozen_benchmarks.py
  exit 0: frozen hashes verified
```

All eight `tests/frontend/test_*.js` Node scripts exit 0, rerun after report work.
No protected dossier, frozen JSONL, research/artifact tree or golden JSON changed.
Regression pointers: `test_ai_advisory_cost_controls.py` (7),
`test_brand_background_findings.py` (2), `test_specialist_discovery_priority.py`
(3), existing evidence-adviser, unified-report, gateway and golden suites.
Historical golden expectations remain intact except explicit assertions for the
three intended background-count migrations. The old retry-success test is now a
no-immediate-retry control; the empty-body “Nominal” summary expectation is now
conservative. Earlier actual failures are preserved in the review and temp logs.

The final CLI-only diagnostic status-extraction improvement was made after the
full suite; it does not alter application paths or the one saved live result.
Final fatal lint/diff checks cover that script. No claim of its successful live
behavior or another generation request.

## Reproduce without spending AI quota

Create a **fresh** output directory under system temp. Commands are portable;
substitute existing secure environment/asset locations, never commit `.env`.

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file <existing-env> --output-dir <new-terminal-dir>
python scripts/audits/run_phase9_four_agent_browser_audit.py --env-file <existing-env> --chart-js <pinned-chart-js> --replay-dir <saved-terminal-dir> --output-dir <new-browser-dir>
```

Default matrix: three inputs per four agents. Prefer `--case "agent:input"` for
a bounded targeted check. AI credentials are absent unless `--allow-live-ai` is
explicitly added; **do not add it routinely**. Mocks remain off. Saved responses
can also be inspected or unit-replayed without network. The terminal run used
actual ASGI routes, not TCP socket transport; the browser used exact saved SSE,
not new provider investigations. Neither validates deployed parity.

If explicitly authorized to check generation again:

```text
python scripts/diagnostics/check_ai_advisory_runtime.py --allow-live --skip-model-list --env-file <existing-env> --output <new-json>
```

That command permits one capped generation; it is not an instruction to poll
repeatedly. Latest authorized attempt: Flash-Lite, maximum 96 output tokens,
UNAVAILABLE / RuntimeError, no HTTP status or successful token usage captured.
Do not retroactively call it 429 or a bad key. Earlier separate evidence reported
daily quota exhaustion with a 23,023-second delay. Keep those observations distinct.

## Acceptance / next actions

Actual AI-off terminal matrix: twelve completed SSE results, 30 records / 13,326
words, but brand material remains background and Personal Watch remains profiles
only. Frontend replay: 24 states preserve record/finding/lead counts, no document
overflow or uncaught page exceptions; 18 console resource errors recorded.
All twelve mobile report captures inspected. Sam Altman's text-paint gaps / blank
desktop cards reproduced in a focused saved-payload recheck despite populated
DOM. **Visual PARTIAL, research NOT COMPLETE**. No extra provider call for replay.

Next implementation should target original-publisher body resolution and approved
search access, not more model calls. Then specialist incident coverage. Also
isolate Sam's rendering/compositor/style issue and stop Scout's seven unresolved
index/disclosure labels from being presented as Key Findings without losing
their provenance. Preserve all blocked states. No new live AI tests, broad
provider sweeps, commit/push, or deployment are implied by this handoff.
