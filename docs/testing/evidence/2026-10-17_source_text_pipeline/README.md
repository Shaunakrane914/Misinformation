# Source-text pipeline evidence — 2026-10-17

[Review](../../SOURCE_TEXT_PIPELINE_REVIEW_2026-10-17.md) ·
[handoff](../../../handoffs/2026-10-17_SOURCE_TEXT_PIPELINE.md).

All JSON files here are copied from fresh local diagnostic output, not generated
research facts or refreshed frozen evaluation labels. No raw dossiers, raw
discussion corpus, `.env` contents or credentials are committed here.

- `baseline_round1.json`, `baseline_metadata.json`: 52 fixed production-dispatch
  operations before structural extraction/answer changes; measurement additions
  were already present. Default runtime, Reddit blocked.
- `after_round1.json`, `after_round2.json`, `after_metadata.json`: two repeated
  54-probe passes (52 operations plus Apple/PEP supplemental web reads). Stable
  source per run; no server environment loaded. These precede the final Reddit
  semantic/transport correction and NVD/arXiv transport flags.
- `configured_round1.json`, `configured_metadata.json`: all 52 operations with
  explicit existing source access configuration, before final Reddit correction.
  Boolean flag observation is not independent provider authorization.
- `final_recheck.json`, `final_recheck_metadata.json`: final eight-operation
  source recheck, including corrected Reddit comments and actual NVD/arXiv
  transport observations. Do not call this an all-52-operation rerun.
- `api_final.json`: four real FastAPI source-extraction requests with captured
  text metrics. No fake API responses, LLM inference or source-completeness proof.
- `four_agent_live.json`: twelve real local button/SSE investigations, three
  per agent, two viewport states each. Five records, eight empty inputs.
  Application fingerprint stable during this pass; focused final Reddit/CSS
  corrections were made afterward and tested separately.
- `source_display_browser.json`: original weak display-harness result. Its
  overflow predicate missed clipping. It is retained, not accepted as visual proof.
- `clipping_before.json`, `clipping_after.json`: strengthened 66-sample display
  harness, four pages/three widths. Eight failed states before, zero after.
  Exact captured inspections in a labeled test scaffold, not native agent reports.
- `source_display_scout_390.png`, `source_display_personal_1440.png`: original
  captures, including the clipping limitation.
- `source_display_*_after.png`: later framed captures. Smooth scrolling initially
  raced the capture and could show the page header; do not infer article
  readability from a screenshot that does not actually show the inspector.
- `instant_final_summary.json`, `instant_final_scout-agent-390.png`,
  `instant_final_personal-watch-agent-1440.png`: final instant-positioned display
  capture recheck, twelve states with zero failures. The mobile inspector capture
  was visually inspected and shows wrapped metrics and excerpt text. This is
  still the same saved source data, not another live acquisition.

Raw public samples, full screenshots, local logs, temporary SQLite/dossiers and
event streams remain in the fresh system-temp `aegis-source-quality-*` tree.
Metric JSON is the durable measurement record; temp availability is not promised.
Words are whitespace units; KB uses UTF-8 bytes / 1,000. Duplicated operations,
mirrors, caches, profile metadata and repeated rounds are not a unique corpus.

No human annotation, calibration, retrieval recall, screen-reader acceptance,
measured contrast, axe, production parity or provider authorization is inferred.

`ci_implementation.json` records the observed successful five-job hosted run for
implementation `f887c9c`, not research acceptance, deployment, or a future
documentation successor's own CI run.
