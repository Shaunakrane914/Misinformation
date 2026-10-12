# Phase 8B bounded live extraction spot-checks

These are append-only, pre-commit live observations from 2026-10-12 UTC.
The runner retained bounded normalized excerpts and transport hashes, not
complete response bodies. The `run_metadata.json` in each directory records
the observed checkout and dirty-worktree state; do not reinterpret it as a
post-commit or hosted-CI result.

| Run | Purpose | Result |
|---|---|---|
| [17:09:44Z](2026-10-12_17-09-44Z/) | GitHub README and RSS field extraction, two scenarios each | GitHub 2/2 partial README content; RSS 2/2 syndicated feed results. Includes first all-16 normalized richness summary. |
| [17:14:16Z](2026-10-12_17-14-16Z/) | Field-presence instrumentation for GitHub, YouTube, RSS common targets | 3/3 independently live usable, with normalized metadata field names; not a complete 16-operation gate. |
| [17:14:36Z](2026-10-12_17-14-36Z/) | Nested YouTube metadata presence after instrumentation | Video ID, channel ID, date, duration, engagement counters, tags/categories and availability field names observed on one target. Contains latest all-16 summary. |

The latest [`richness_summary.json`](2026-10-12_17-14-36Z/richness_summary.json)
selects the latest matching operation/scenario across the Phase 8A artifact
and these runs. It scores only normalized sample fields, not raw-provider
schema completeness. See the [Phase 8B schema matrix](../../docs/architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md)
for current gaps and gate status.

No credentials were used to bypass access, and no protected historical
dossier or frozen benchmark input was touched by these runs.
