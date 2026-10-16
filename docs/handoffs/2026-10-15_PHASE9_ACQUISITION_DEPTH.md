# Phase 9 acquisition depth and strategic evidence UI — 2026-10-15

## State and authority

User requested all 16 protected operations, Reddit/X, additional useful sources, repeated extraction/evaluation and detailed frontend evidence. User subsequently confirmed **no approved source access is configured; retain explicit blocked states**. Do not activate Reddit, invent SEC contacts, configure credentials, bypass access controls or fabricate missing results.

Working branch/worktree: `feat/phase8-independent-audit-codex`, base/HEAD `abe547f1e17aab5b54e90ff55e2d4783afa95283`. Implementation remains uncommitted and unpushed. Original IDE worktree at `1e1c44e` and other-agent Phase 9 worktree at `7054575` were inspected read-only and preserved. The other branch's reasoning/benchmark work has not been merged or independently accepted here.

The new proof directory was initially covered by the existing artifact ignore rule. `.gitignore` now permits only the reviewed `artifacts/phase9_acquisition_depth/2026-10-15_checkpoint/` subtree, not arbitrary future scrape dumps. Evidence is approximately 24 MB; review payload/screenshot retention before an authorized commit. No files were staged. The temporary local rendering server was stopped; no background monitoring daemon or future live scraping schedule was installed.

Six pre-existing documentation edits and the untracked Phase 9 plan were preserved. Maintained guide/code-map additions resolve links created during that preceding documentation task. Do not stage another agent's changes by assumption. No merge, deployment, paid provider activation or production-secret change.

**Overall Phase 9: PARTIAL.** This delivers bounded acquisition/evaluation tooling, two real additive sources, evidence-inspection contracts and UI, and integrity fixes. It does not complete full-site extraction, financial XBRL/filing semantics, representative human-adjudicated accuracy or production acceptance. Blocked sources are expected, not faked PASS outcomes.

## Implementation and useful rationale

- [Community adapters](../../backend/infrastructure/acquisition/adapters/community.py) and [channel bridge](../../backend/infrastructure/acquisition/adapters/community_channel.py): Hacker News discovery is disclosed Algolia search, with original Firebase item reads; deep mode samples two parent-checked direct replies per selected story. Stack Exchange adapter is explicitly Stack Overflow questions, with body filter, in-process 60-second request caching, backoff/quota handling and no answer/full-history claim. Exact host/ID construction prevents payload-controlled endpoint selection. HN IDs are explicit because the legacy source-ID implementation drops query strings, which otherwise collapses HN item identities.
- Capability declarations, executable operations, native cohesive dispatch, shared service registration and direct-URL planning are wired into actual consumers. New unprobed channels stay NOT_PROBED, not assumed healthy or unavailable. Existing 16 operations and shims remain intact. New sources are opt-in/explicitly named rather than added indiscriminately to every investigation.
- [Pure evidence inspection](../../backend/schemas/evidence_inspection.py) is a serialization contract, not a new verdict engine or transport dependency. It exposes exact bounded captured-text chunks, offsets/hash/IDs, observed/missing fields, depth, numeric mentions and selected page observations. Metadata stays discovery-only. Numeric mentions, page corrections and quotations are not verified facts. Hash/offset scope is captured inspected text, not an assertion about remote completeness.
- [Unified schema](../../backend/schemas/unified_report.py) and [report builder](../../backend/services/report_builder.py) compute the additive inspection at the boundary instead of trusting stale serialized inspection metadata. Personal Watch's canonical evidence was being dropped; it now reaches unified evidence. Generic BrandShield records were unconditionally primary; grouping now respects explicit qualified roles/platforms. Scout preserves a bounded acquired body instead of only snippets. Unknown authors are no longer filled with source names or `@user` in the affected paths.
- [Native normalizer](../../backend/services/agent_reach/native/normalizer.py): missing X engagement remains unknown; invalid/missing profile handles do not invent a user; profile creation date is separate from publication. Personal normalization preserves content depth and whitelisted context metadata rather than discarding it and inventing engagement zeroes.
- [Native reader](../../backend/infrastructure/acquisition/routing/router.py), [handlers](../../backend/infrastructure/acquisition/routing/standard_handlers.py), [shared deep reader](../../backend/services/research/deep_reader.py) and service: explicit profile/video metadata kinds survive deep reads. Text length does not prove FULL_ARTICLE; ordinary unproven reads remain PARTIAL_CONTENT. X reader markdown respects requested bounds and no longer dumps the entire metrics metadata dictionary into evidence prose. Service deep-read character budget is bounded up to 20,000.
- [Extraction API](../../backend/api/agent_reach.py): new synchronous worker-pool `POST /api/agent-reach/extract` validates operation/budgets and uses native policy/credential/cooldown checks. Deep mode enables bounded existing follow-ups, never an exhaustive crawl. Response separates acquisition outcome, observed network, inspection and unassessed claim support.
- [Shared frontend renderer](../../frontend/unified-report-renderer.js)/theme: all four agents gain escaped passage/table/number inspection, coverage limits and explicit source-read control. Exact-host routing chooses existing operations; configured API resolver is used. Follow-up observations do not revise the original verdict. Disabled in-flight buttons, 30-second browser wait and nonrecursive follow-up cards prevent accidental repeated UI work; browser abort is not guaranteed backend cancellation.

These decisions prioritize useful data with traceable limitations over byte volume or additional provider counts. The efficient-codebase, AI-engineering and frontend-security skills guided localized owner changes, bounded instrumentation and escaped untrusted content; they do not establish independent security or research certification.

## Regression and reproduction map

- [Capture/report/depth regressions](../../tests/unit/test_phase9_extraction_quality.py): exact offsets, stable/mutated hashes, Unicode and caps, missing data, structured observations, report retention, null engagement and metadata-preserving deep reads.
- [Community source regressions](../../tests/unit/test_phase9_community_sources.py): original item reads after indexed discovery, identity uniqueness, bad targets, backoff, deleted/parent-checked bounded replies, all-agent direct-URL plans and truthful unprobed capability state.
- [Extraction API tests](../../tests/unit/test_phase9_extraction_api.py): native dispatch, deep bounds, policy denial and unsupported requests.
- [Node renderer tests](../../tests/frontend/test_unified_report_renderer.js): escaping and exact-host read selection, including host-spoof/path-token negatives.
- [Cycle runner](../../scripts/audits/run_phase9_extraction_cycle.py), [real extraction API smoke](../../scripts/audits/run_phase9_source_api_smoke.py), [Chromium inspector check](../../scripts/audits/audit_phase9_evidence_inspector.py). See the [portable runbook](../operations/PHASE9_EXTRACTION_RUNBOOK.md).

## Observed live and browser evidence

Append-only [checkpoint proof](../../artifacts/phase9_acquisition_depth/2026-10-15_checkpoint/) retains original observations, not rewritten success reports. Source HEAD is the recorded base with dirty implementation; never advertise these as clean-commit or hosted CI proof. Different runs are development checkpoints, not identical builds.

- Protected pre-change baseline: 16/16 bounded native operations returned samples, live transport observed. Script exit 0. Baseline ran before the new paths were wired, with existing docs/early untracked edits present, not a clean worktree.
- First cycle: two rounds × 28 operations with at least 60 seconds between rounds; protected samples passed both rounds. Reddit policy excluded; SEC config absent; FactCheck auth absent; NVD timeout/503. X mirror samples and Stack Overflow bodies acquired. HN story text was empty metadata, not an invented article.
- Follow-up: HN story `8863` went from metadata/0 body characters to 3 records/1,053 captured characters with actual sampled replies. HN search returned 6 story/reply records/2,888 characters. This demonstrates added context, not better claim accuracy or complete discussion coverage.
- Later full cycle: 28 operations, protected sample gate PASS, all-requested-source gate PARTIAL, 42 observed records. Reddit read/comments, SEC and FactCheck returned none. NVD later normalized one record but its network flag remained false, as did arXiv's; **do not claim fresh-network verification** for those authoritative adapters. Earlier NVD failures remain retained.
- Real extraction API smoke: HTTP 200 for all four requests; HN SUCCESS/3 inspected records/1,053 chars, Stack Overflow SUCCESS/1/1,009, X SUCCESS/1/24; Reddit SKIPPED/0/no network with policy reason. HTTP success is not all-source acquisition or truth.
- Actual four-agent Apple APIs: 4/0/0/1 records, four successful HTTP responses, mocks false and no live LLM key. After report fixes, unified evidence retains the 4 BrandShield and 1 Personal records. Source discovery remains sparse; no research-accuracy improvement is established. Separate date/depth follow-ups retain the correction sequence rather than altering old payloads.
- Chromium: 24 states at 320/390/1440 pixels, recorded real API reports plus explicitly synthetic hostile controls. Zero observed horizontal document overflow, script-bearing images, unsafe actionable links or page exceptions. Native details keyboard opening and synthetic source-read controls passed. A second 24-state date-corrected pass also passed. Screenshots were inspected, and exposed the joined-date and depth bugs subsequently fixed. Browser replay is not live browser/provider integration; no axe or manual screen-reader acceptance is claimed for these runs.

## Validation record

This is a reconstructed engineering log, not a raw transcript or private reasoning trace. An intermediate full run passed 1,189 tests. Subsequent measured full/fast pairs were 1,193/985, 1,201/993 and 1,202/994 as regressions were added. Only actually run results are acceptance evidence; do not derive unrun counts. An early new direct-URL routing test failed because offline DNS is intentionally blocked; it was corrected with a narrow test-only URL-validation fixture, not weakened production checks. Later targeted depth/golden tests passed 55/55. Final full/fast results are appended below after completion.

## Final local validation

Final backend/source tree after metadata-depth correction:

| Actual command/check | Exit | Observed result |
|---|---:|---|
| `pytest tests/ -q` | 0 | 1,207 passed in 64.82s. |
| `pytest tests/unit tests/chaos tests/security -q` | 0 | 999 passed in 33.64s. |
| All seven `node tests/frontend/test_*.js` scripts, individually | 0 each | All passed; no browser acceptance inferred from Node. |
| `flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | 0 | Zero fatal findings. |
| `python scripts/validation/verify_frozen_benchmarks.py` | 0 | Frozen content hashes verified. |
| `python scripts/validate_release_candidate_smoke.py --output <new-path>` | 0 | Offline smoke completed. |
| `python scripts/validate_rollback_compatibility.py --output <new-path>` | 0 | Offline persistence/reader checks; protected historical archive and deployed rollback remain unverified. |

Fresh targeted Personal API after the deep-reader correction also exited 0 and is retained in `personal_depth_corrected/`; it must be interpreted independently of prior four-agent payloads. It retained one source with `PROFILE_METADATA` and null publication date. A fresh 390px Chromium rendering had document width 390 and zero unsafe actionable links; its actual screenshot was inspected. Earlier temporary logs are retained under `offline_validation/`; the final run wrote fresh logs/reports to `offline_validation_final/`. The last source smoke also passed under `source_api_final/`. A final HN provenance regression ensures original item and reply each retain their own transport endpoint; a failed optional reply no longer discards an already acquired original item. Full/fast final counts include that additional regression.

Changed Markdown local links pass the existence check. `git diff --check` passes; the tracked protected-path diff is empty and frozen hashes verified. Common API-key/token-pattern scan of new proof found no matches; this is not a universal privacy guarantee. Source-only fingerprint (including new untracked implementation files): `8692f205e383f71a73b0a0c0ed76e028944b50cd23da8ce06010f6bbf6e155c2`. Exact base HEAD remains `abe547f`; no new remote CI run is claimed.

## Remaining gates and safe continuation

1. Retain blocked Reddit/SEC/FactCheck states as explicitly requested. Credentials/contact/access policy remain operator-owned; never paste them into reports, source or chat.
2. Shared service query normalization does not yet expose every native optional follow-up to every specialist request. New explicit extraction endpoint and UI follow-up use native deep options; do not describe that as a comprehensive new Quick/Deep mode for the original four scan APIs.
3. Complete source-specific pagination, original filing/XBRL/period-unit semantics and citation entailment against independently reviewed cases. Existing fields/observations are not calibrated financial or misinformation facts. No frozen data/labels were modified.
4. Independently adjudicate representative cases and lock thresholds before tuning; no new population precision/recall, calibrated accuracy or external human labels were produced here. Preserve the other branch's benchmark work without assuming its labels prove accuracy.
5. Fix authoritative transport-flag consistency separately before calling those normalized responses fresh live proof. Native extractors and server workers can outlive a client deadline; caching/backoff and admission are process-local, not distributed guarantees.
6. Evidence-rich live usability, manual accessibility/contrast, production concurrency and staging rollback remain unverified. Source-read negative/transport UI controls are synthetic and labeled as such.
7. Original protected archive inventory reported 55 malformed dossiers; the isolated checkout's offline persistence PASS does not recover or validate that absent archive. No historical dossier was repaired or overwritten.
8. No commit/push or new hosted workflow was performed for these dirty changes. Review the complete diff and proof sensitivity before any authorized checkpoint; never sweep other worktrees into it. Do not declare the full Phase 9 plan or production launch accepted.
