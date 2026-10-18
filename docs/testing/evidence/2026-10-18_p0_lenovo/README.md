# P0 acquisition proof — 2026-10-18

[Engineering handoff](../../../handoffs/2026-10-18_P0_ACQUISITION_RELIABILITY.md) /
[measurements](measurements.json).

One real local, AI-disabled Lenovo investigation acquired an observed issuer
PDF. The [390px report image](lenovo-live-replay-390.png) replays that exact saved
SSE response through the real Scout page/renderer. It is not a second provider
run or deployed-code acceptance. The observation remains UNVERIFIED; its PDF
reference resolves to a source record. Five records include four index pages,
not five independent reports. Full responses/bodies stay temporary.

Separate **synthetic all-timeout controls**, not live investigations:

- [Scout](01-scout-synthetic-failure-390.png)
- [Trending](02-trending-synthetic-failure-390.png)
- [BrandShield](03-brandshield-synthetic-failure-390.png)
- [Personal Watch](04-personal_watch-synthetic-failure-390.png)

Each was replayed at 320/390/1440px with zero findings/sources and visible failure
text. Selected screenshots were visually inspected. Native page buttons and
shared rendering execute, but SSE/health are labeled replay stubs. External
fonts were blocked; resource errors are not silently counted as a clean console.
Not screen-reader/contrast certification, independent accuracy or production proof.
