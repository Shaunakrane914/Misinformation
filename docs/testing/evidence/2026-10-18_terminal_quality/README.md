# Terminal-first output proof — 2026-10-18

[Review](../../TERMINAL_OUTPUT_AND_AI_COST_REVIEW_2026-10-18.md) ·
[Measurements](measurements.json) ·
[Handoff](../../../handoffs/2026-10-18_TERMINAL_QUALITY_CLOSEOUT.md).

Twelve real, AI-disabled local SSE investigations; then exact saved-response
frontend replay at 390/1440px. Replay is not twelve new acquisitions. Selected
actual mobile captures: [Nike](nike-mobile.png), [Tim Cook](tim-cook-mobile.png),
[Infosys](infosys-mobile.png). Full responses, logs and remaining images are in
a fresh system-temp `aegis-terminal-polish-*` tree, not tracked evaluation data.

Terminal fingerprint covered tracked backend/frontend files only; its stable
flag does not certify then-untracked helper modules. The browser fingerprint
includes tracked and untracked application files and was stable during replay.
Between stages, legacy input-field accounting and AI-only prompt-size controls
changed; no normal-provider matrix was rerun to pretend these were identical
application snapshots. No backend/frontend source changed during either run.
The replay uses the exact original terminal responses, not freshly rebuilt ones.

DOM/layout checks passed for 24 states; **visual acceptance remains PARTIAL**.
Sam Altman's mobile capture had partial text paint, and its separate replay
again had mobile gaps / blank desktop cards despite populated DOM. This remains
unresolved; no screenshot fabricated or cropped to hide a failure. Selected
durable captures do not replace that limitation. Console resource errors and
other research gaps are documented in the review. No production readiness.
