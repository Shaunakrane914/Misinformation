# Phase 8 live acquisition evidence

These directories are append-only bounded live-probe records. Complete response
bodies and credentials are not stored.

Chronology:

- `2026-10-12_10-48-41Z`: discovery run that exposed false-positive depth and
  Xiaoyuzhou provenance defects. Superseded, retained as negative evidence.
- `2026-10-12_10-52-40Z`: full post-depth-fix run; GitHub unauthenticated quota
  exhausted near the end and the old Xiaoyuzhou implementation was rejected.
- `2026-10-12_10-55-07Z` and `2026-10-12_10-55-28Z`: bounded rate-limit
  diagnostics.
- `2026-10-12_10-58-45Z`: first direct Xiaoyuzhou fix verification; superseded
  by the provider-empty classification correction.
- `2026-10-12_10-59-51Z`: final GitHub releases and official Xiaoyuzhou probe
  sets used by acceptance.
- `2026-10-12_11-00-24Z`: corrected GitHub commit probe set used by acceptance.
- `2026-10-12_11-00-14Z`: interim consolidation; superseded.
- `2026-10-12_11-00-33Z`: pre-checkpoint consolidation; superseded.
- `2026-10-12_11-06-45Z`: authoritative consolidated Phase 8A acceptance at
  checkpoint `b2715406af219ca336b546ed7d42f54fe795cac4`.

Read `run_metadata.json`, `probe_records.jsonl` and `acceptance.json` together.
A gate pass means every protected operation produced at least one live usable
result; it does not erase failed edge cases or imply full-content coverage.
