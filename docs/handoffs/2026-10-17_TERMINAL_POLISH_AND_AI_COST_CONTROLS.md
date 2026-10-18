# Terminal-first output work and AI cost controls — 2026-10-17

**Continued on 2026-10-18:** [Final local validation, new user-authorized single
AI check and remaining rendered/acquisition failures](2026-10-18_TERMINAL_QUALITY_CLOSEOUT.md).
Read that successor before interpreting the intermediate counts below.

## Scope / interruption

Started from clean branch `feat/continuous-source-intelligence-20261017`, HEAD
`d1ffcaf7a4801b0c9f15377be0312838a65adea5`. User requested better BrandShield /
Personal Watch output, terminal-first iteration, then frontend validation. During
live terminal investigation the user raised API overuse and requested smaller,
fast models for suggestions. Live testing was stopped. No further live generation
was requested after that objection. Changes below are local, uncommitted and
unpushed; no main merge, deployment, credential or access-policy changes.

## Cost incident / engineering conclusions

Normal agent execution can invoke source-plan advice and native threat synthesis;
the older provider retried / walked configured models after failures. Repeating
whole-agent matrices repeated those calls even when acquisition only yielded a
profile. This was not necessary for scraper output iteration.

Local log observations (not a project-wide billing/accounting ledger): baseline
three-person run logged nine Gemini 429 warnings; two later terminal processes
logged one each after the new process-local cooldown. One separate minimal live
diagnostic also returned 429. The baseline additionally has three 404 error log
lines; log lines are not a complete exact upstream request count. The dashboard
was an all-keys view and cannot be fully attributed from these local logs.

The diagnostic's allowlisted provider details identify DAILY_QUOTA_EXHAUSTED and
retry delay 23,023 seconds. It does not establish the quota or generation health
of Flash-Lite. Do not probe alternate keys/models to evade an exhausted quota.
No provider billing settings were changed. Official reference:
[Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

Implemented:

- `LLM_ADVISORY_MODEL=gemini-2.5-flash-lite` default, separate from the existing
  synthesis model. Source-plan and passage-selection advice use strict model
  identity, one attempt, 320 maximum output tokens and two-second deadline.
  No automatic larger-model fallback. Minimal diagnostic uses the same small
  model and 96 output tokens; it was **not rerun live** after this change.
- Gemini 429 responses now stop the immediate key/model/retry waterfall and
  establish a provider-instance cooldown, minimum 30 seconds and respecting
  bounded numeric RetryInfo/Retry-After delays. Allowlisted category/retry data
  only; never raw provider messages, account identifiers or credentials.
  This is process-local protection, not distributed quota enforcement or a
  daily spending budget. Simultaneous in-flight requests can still precede the
  first 429; new processes do not share the cooldown.
- Profile/metadata-only Personal Watch material skips native threat-generation
  calls and remains inspectable evidence; it cannot create synthetic claims.
- New `run_terminal_agent_quality.py` uses actual local ASGI SSE routes with
  isolated DB/dossiers, notifications/persistence integrations disabled and no
  ingestion lifespan. **AI credentials excluded by default**; `--allow-live`
  authorizes acquisition, not AI. Separate `--allow-live-ai` is required to send
  generation requests. Avoid that opt-in until an explicit request budget is
  agreed. Saved native responses/events support review and exact browser replay.

## Output fixes / still incomplete

- BrandShield no longer converts unmatched catalogs/homepages into “Genuine
  Issue” findings. Canonical evidence stays retained; background IDs are
  separate. Legacy `safe_count` is zero / `safety_assessment=NOT_ESTABLISHED`;
  genuine non-threat findings have a separate count. A focused native-to-shared
  regression confirms no catalog findings and preserved source inspection.
- Personal source plan splits deepfake and impersonation queries and adds
  specific news discovery before generic news. Specialist reads prioritize
  objective-bearing titles/snippets without removing other corpus candidates.
- Quoted-name web search now filters first-name-only false matches, allowing
  the existing secondary search when the primary is irrelevant.

These acquisition changes are **not accepted as successful live depth**. The
first two terminal passes retained only 18/8/10-word profiles. A third objective
pass still returned profiles for the first two cases and was terminated during
the third when the user objected to API usage. The initial baseline application
fingerprint also overlapped edits; it is diagnostic only, not stable acceptance.
No fresh browser run or final live acceptance was performed. The overall research
quality limitation remains. Next: use saved responses/offline cases first, then
AI-disabled bounded acquisition if needed, and only then one exact frontend
replay. Do not claim that changing model names fixed quota or profile-only depth.

## Validation (actual commands; no live AI)

- Focused seven test files: 80 passed, exit 0 (0.81s).
- First full pass: 1,368 passed / 3 failed; first fast: 1,160 passed / 3 failed.
  All failures were historical BrandShield catalog-as-finding counts. Preserved
  the golden JSON unchanged; the compatibility test now explicitly checks the
  exact three approved count deltas while checking every other old field.
- Former 429 retry-success unit control was intentionally replaced with
  no-immediate-retry assertions. New controls cover small-model options,
  allowlisted quota detail, cooldown expiry, no key/model waterfall and no
  profile-only AI calls. These tests mock transport; no billable requests.
- Fatal Flake8: exit 0 / zero findings. All eight Node frontend scripts exit 0.
- Release-candidate smoke: OFFLINE_SMOKE_PASS, exit 0.
- Rollback: OFFLINE_PERSISTENCE_PASS, exit 0; historical archive and deployed
  rollback remain NOT_VERIFIED in this isolated worktree.
- Frozen benchmark hash validator: exit 0. Historical dossiers, frozen JSONL,
  research/artifact trees and golden JSON were not modified.
- Terminal runner `--help`: exit 0; AI-off live execution is not yet verified.

Final full/fast reruns are recorded in the appended closeout below. Diagnostic
logs and partial responses are in a fresh system-temp `aegis-terminal-polish-*`
tree, not tracked artifacts. There is no invented raw transcript or new research
acceptance claim. The separate source-planner/query/read changes still need
focused acquired-text fixtures and browser replay before publication.
