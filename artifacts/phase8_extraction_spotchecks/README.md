# Phase 8B bounded live extraction spot-checks

These are append-only live observations beginning 2026-10-12 UTC.
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
| [17:37:38Z](2026-10-12_17-37-38Z/) | Guarded 16-operation common-case field-shape pass | All 16 yielded live, classified output on the sampled common target. Parsed adapter-item field names are retained without values. This does **not** prove raw-provider schema completeness or edge-case success. The run was dirty and predates the commit. |
| [02:49:51Z](2026-10-13_02-49-51Z/) | Important-field audit before HTTP decoding fix | The web common page was **falsely classified as usable**: its bounded excerpt contained compressed bytes decoded as text. Keep this ignored local run as negative evidence; do not cite it for content quality. |
| [02:53:55Z](2026-10-13_02-53-55Z/) | Guarded 16-operation common-case re-probe after decoding fix | All 16 classified usable; web common page title/headings were observed and its excerpt contained no replacement/control characters. The run was on a dirty worktree, not a post-commit or hosted-CI proof. |
| [02:55:36Z](2026-10-13_02-55-36Z/) | Guarded web common/high-content re-probe | Both web pages yielded readable bounded content, observed titles/headings and no replacement/control characters in the retained excerpts. This filtered run is **not** a 16-operation gate pass. |
| [03:08:05Z](2026-10-13_03-08-05Z/) | Guarded bounded page-detail re-probe | Both pages yielded readable titles/headings and observed page links; one exposed publisher-declared JSON-LD. No table, quotation, media caption or correction notice was observed on these two targets. All such fields are page observations, not verified source claims. |
| [03:32:27Z](2026-10-13_03-32-27Z/) | Final guarded page-detail re-probe after title/canonical correction | Both pages yielded readable title/headings and observed links; the common page no longer records a nonexistent canonical-verification field. The final important-field summary is v9. This remains a dirty-worktree, filtered pre-commit run. |
| [03:53:35Z](2026-10-13_03-53-35Z/) | Five GitHub operations after attribution/depth correction | Four common operations returned content or metadata; `github.issues` page 1 returned HTTP 200 but all three provider entries were PRs, filtered to zero issues. Its historical `NOT_FOUND` classification is **wrong** for a filtered page, not proof that the repository or issues are absent. |
| [03:55:58Z](2026-10-13_03-55-58Z/) | Guarded GitHub issue overfetch re-probe | One bounded request for ten provider entries yielded three actual issues. The probe returned `DIRECT_PARTIAL_CONTENT`. This did not fetch issue comments or prove all pages. The 03:53Z/03:55Z pair observed 61,088/112,197 raw bytes and 2,072/2,745 ms respectively; those two timings are not a controlled marginal-cost estimate. |
| [04:08:03Z](2026-10-13_04-08-03Z/) | Guarded post-normalization re-probe of YouTube, V2EX, RSS and Xiaoyuzhou | Ten selected common cases returned live classified output: 3 video, 4 V2EX, 1 RSS and 2 podcast operations. This is a dirty-worktree filtered run, so its `PHASE8A_GATE=PARTIAL` means six operations were intentionally not probed. It does not establish difficult-case, pagination or field completeness. |

The current [`richness_summary_v11.json`](2026-10-13_04-08-03Z/richness_summary_v11.json)
selects the latest matching operation/scenario from the Phase 8A artifact,
guarded 16-operation re-probe, web follow-up, GitHub probes and normalization
re-probe. It scores observed
normalized sample and bounded parsed adapter-item field names, **not** raw-provider
schema completeness. Older samples that did not record a field are marked
*unobserved*, not treated as empty. The old v3 summary remains historically
reproducible but its web common-page result is **invalid as text evidence**:
the raw gzip entity was decoded as UTF-8 without decompression. See the
[Phase 8B schema matrix](../../docs/architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md)
for current gaps and gate status.

No credentials were used to bypass access, and no protected historical
dossier or frozen benchmark input was touched by these runs.
