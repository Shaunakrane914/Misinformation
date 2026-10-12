# Phase 8B bounded live extraction spot-checks

These are append-only, pre-commit live observations from 2026-10-12 UTC.
The runner retained bounded normalized excerpts and transport hashes, not
complete response bodies. The `run_metadata.json` in each directory records
the observed checkout and dirty-worktree state; do not reinterpret it as a
post-commit or hosted-CI result.

| Run | Purpose | Result |
|---|---|---|
| [17:09:44Z](2026-10-12_17-09-44Z/) | Early GitHub/RSS probes | **Invalid as isolated-worktree proof:** file-path invocation loaded the editable-installed outer checkout's backend. Retained as negative verification evidence. |
| [17:14:16Z](2026-10-12_17-14-16Z/) | Early field-presence probes | Same checkout-contamination limitation. |
| [17:14:36Z](2026-10-12_17-14-36Z/) | Early YouTube metadata probe | Same checkout-contamination limitation; its summary is superseded. |
| [17:20:41Z](2026-10-12_17-20-41Z/) | First web probes after code edit | Same checkout-contamination limitation; its `DIRECT_FULL_CONTENT` claim must **not** be cited for the isolated branch. |
| [17:21:39Z](2026-10-12_17-21-39Z/) | Guarded web probes | `router_source` proves this checkout; both targets returned bounded partial page text with no invented dates. |
| [17:21:49Z](2026-10-12_17-21-49Z/) | Guarded GitHub/RSS/YouTube probes | `router_source` proves this checkout. Two live scenarios each; README partial content, mixed feed summary/content, video metadata. Contains corrected all-16 summary. |

The latest [`richness_summary_v2.json`](2026-10-12_17-21-49Z/richness_summary_v2.json)
selects the latest matching operation/scenario across the Phase 8A artifact
and **only the guarded** 17:21 runs. It scores only observed normalized sample
fields, not raw-provider schema completeness. Older samples that did not
record a field are marked *unobserved*, not treated as empty. See the
[Phase 8B schema matrix](../../docs/architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md)
for current gaps and gate status.

No credentials were used to bypass access, and no protected historical
dossier or frozen benchmark input was touched by these runs.
