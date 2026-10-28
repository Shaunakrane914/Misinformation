# October 28 reconciliation evidence

- [Workspace status](workspaces.json) and [file hashes](file-reconciliation.json):
  released `ec5bef1`, older root checkout, dirty remediation tree and current
  isolated implementation are distinct observations. No historical dirty-run
  fingerprint was recorded; present file hashes are not substituted for it.
- [Original completed aggregate copy](completed-aggregate.original.json): exact
  protected 20-case result bytes, timestamp 07:43:29Z, SHA-256
  `23b44e4a8f13b67cbb802f3f7759c8fc1db822108bce25715763d28af8a33c99`.
  Original file remains in the root artifact tree, unchanged.
- [Benchmark/dossier recovery](benchmark-recovery.json): per-case reported metrics
  separated from unavailable actual article/read/HTTP/passage metrics. Three
  ordered engine sequences are identified; only one complete aggregate recovered.
- [Released/current identical-input replay](replay-comparison.json): four genuine
  sealed snippet sets plus a separate genuine historical transcript control,
  each replayed under both versions. No new acquisition or generation.
- [Browser checks](browser-summary.json): ten saved-SSE states on the current local
  frontend, exact workbench publication and empty states. [Tim historical mobile](tim-historical-control-390.png)
  and [Russell empty desktop](russell-batch-1440.png) were visually inspected.
- [Final gates](final-gates.json) and [initial failures](initial-gates.json): actual
  command scopes, exits and wall times. No remote CI or deployment.
- [Archive JSON inventory](archive-json-inspection.json): 55 protected malformed
  files remain failures; read-only syntax inspection is not full integrity or
  rollback acceptance. [Preservation check](preservation-check.json) confirms
  initial root source changes and aggregate bytes were preserved.

Full read-only Git export, prepared lead-only replays, native responses/SSE,
raw validation logs and intermediate results use system-temp basename
`aegis-oct28-reconciliation-u098c0ob`. They may expire. Source bodies were not
invented from snippets; article counts are not inferred from summary prose.

[Complete report](../../OCT28_RELEASE_RECONCILIATION_AND_BENCHMARK_AUDIT.md).
