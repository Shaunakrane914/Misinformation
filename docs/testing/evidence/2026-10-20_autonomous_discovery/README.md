# Autonomous discovery repair evidence — 2026-10-20

See the [engineering report](../../AUTONOMOUS_DISCOVERY_REPAIR_2026-10-20.md)
and [handoff](../../../handoffs/2026-10-20_AUTONOMOUS_DISCOVERY_REPAIR.md).
This continues the October 19 checkpoint; the local session crossed midnight.

- `live-measurements.json`: the two approved fresh, AI-disabled normal-query
  investigations, **before** the post-capture index/asset/resolver corrections.
- `reprocess-measurements.json`: current processing of those same saved bytes,
  network blocked; **not a fresh discovery or rerun of provider availability**.
- `browser-summary.json`: exact saved-SSE replay of the current processing at
  320, 390 and 1440px. Readiness is a harness stub, other API calls blocked.
- Selected report screenshots retain the actual output, not invented content.

The summarizer is [read-only with respect to inputs](../../../../scripts/audits/summarize_discovery_funnel.py).
Native response SHA-256 hashes and source-text hashes permit comparison with
the full temporary captures. Provider counts are observed samples, including
nested resolution attempts; legacy transport is uninstrumented. They are not
unique source counts or complete HTTP accounting. The first live Adobe finding
is an index false positive, **not** accepted evidence. Saved processing removes it.
Saved reprocessing's provider rows combine historical observations and blocked
invocations; none are proof of fresh traffic or an acquisition improvement.

Selected captures: [Scout desktop](01-scout-1440-report.png) and
[BrandShield mobile](02-brandshield-390-report.png). The failure banner and
zero-finding states were visually inspected; see browser summary for limits.

Full source captures, events, isolated databases/dossiers, screenshots and gate
logs are in the session's new `aegis-autonomous-discovery-*` system-temporary
directory. They are not committed, and system cleanup may remove them. Durable
measurements deliberately omit full bodies, credentials and private settings.
No historical dossier, tracked benchmark or earlier proof was overwritten.
