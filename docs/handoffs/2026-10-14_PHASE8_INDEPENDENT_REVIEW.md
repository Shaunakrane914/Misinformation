# Phase 8 independent review — handoff, 2026-10-14

## Scope and decisions

User requested independent review of Gemini's full Phase 8 implementation, targeted fixes, real acquisition/API/browser/evaluation evidence, dedicated Git/CI closeout and no merge/deployment. [Full assessment](../architecture/PHASE8_INDEPENDENT_REVIEW_2026-10-14.md) contains stage decisions and findings. **8A passed only its bounded sample; 8B–8F remain partial.** Neither test count nor API success proves research correctness.

Baseline `a10fde82467df21508b4a254507b414cd5b6e9fd`; dedicated branch `feat/phase8-independent-audit-codex`. Original and Gemini worktrees preserved. Code checkpoints `195ae0a` (provenance/grounding/agents/contracts), `220f16f` (audit separation/UI/evaluation), `d58c5ba` (BrandShield real-result narrative/mobile follow-up). Later commits package proof/docs. No merge, deployment, paid provider, production secret or protected archive change.

Useful engineering conclusions, not private reasoning transcripts: centralize origin policy; distinguish ownership from content authority; prefer conservative abstention to source-count certainty; never invent citations/dates/contacts; register native integrations in the actual service; normalize grouped agent contracts; treat pattern detection as triage; keep independent evaluation separate from development fixtures. Stricter labels deliberately change public specialist status values. Consumers should render unknown values as unverified, not infer truth from substring matches.

## Code and regression map

- [Origin qualification](../../backend/services/research/source_quality.py), [relevance](../../backend/services/research/relevance_gate.py), [passage alignment](../../backend/services/research/proposition_grounding.py), [claim intelligence](../../backend/services/research/claim_intelligence.py), [independence](../../backend/services/research/source_independence.py).
- [Acquisition service](../../backend/infrastructure/acquisition/service.py), [authoritative bridge](../../backend/infrastructure/acquisition/adapters/authoritative/channel.py), [FactCheck](../../backend/infrastructure/acquisition/adapters/authoritative/fact_check.py), [SEC](../../backend/infrastructure/acquisition/adapters/authoritative/sec_edgar.py), [safe HTTP](../../backend/infrastructure/acquisition/network/http.py), Scout legacy transport/adapters.
- Four agent assessment modules; [Personal dossier](../../backend/agents/personal_watch/dossier.py); [unified report builder](../../backend/services/report_builder.py). Do not reintroduce fallback citations or canned conclusions.
- [Specialist model boundary](../../backend/services/research/model_grounding.py), checkpoint `c420296`: valid IDs are necessary, not entailment; uncited records are removed and model statuses remain unverified. Regression covers an invented “verified” claim with a valid but unrelated ID. Online model injection/semantic correctness remain unverified.
- `0f5a659` follows screenshot inspection: missing publication dates stay blank through specialist scans/dossiers; sample counts do not imply acceleration; long Trending titles use bounded cards with full dossier disclosure. BrandShield scanning no longer overrides qualification using spoofable URL substrings. Its actual agent-path negative control covers origin and date together. Latest full/fast validation below applies to this final code tree.
- [Negative controls](../../tests/unit/test_phase8_independent_regressions.py), [audit/contract/security controls](../../tests/unit/test_phase8_audit_report_truth.py), [legacy transport boundaries](../../tests/security/test_scout_legacy_transport_boundaries.py), safe HTTP tests and specialist tests.
- Original Phase 4 golden manifest retained. New [reviewed manifest](../../tests/unit/fixtures/research_phase8_independent_golden.json) changes result/replay hashes for explicitly reviewed policy reasons, while asserting original candidate hashes/IDs/rejections.
- [Exact frontend verdicts](../../frontend/unified-report-renderer.js), [explorer semantics](../../frontend/forensic-explorer.js), shared CSS wrap/bounds and Node assertions.

## Executed verification

Windows PowerShell, Python 3.13.5, pytest 8.4.2. This is a reconstructed command/result log, not a raw transcript. Clean `220f16f` supplied the final API/operation proof; `d58c5ba` is the subsequent verified BrandShield follow-up. Test inventories are dated, not permanent acceptance targets.

| Command / check | Exit | Actual result / boundary |
|---|---:|---|
| `pytest tests/ -q` | 0 | 1,156 passed in 64.78s. Earlier runs failed during development (including stricter specialist expectations, SEC contact and report contracts); these were not presented as passes. |
| `pytest tests/unit tests/chaos tests/security -q` | 0 | 948 passed in 30.49s. |
| `flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | 0 | Zero fatal findings. Not full style/security lint. |
| Each of seven `node tests/frontend/test_*.js` scripts | 0 each | Truth, report, security, capability-cache and Phase 8 intelligence contracts. |
| `python scripts/validation/verify_frozen_benchmarks.py` | 0 | Frozen content hashes unchanged. |
| `python scripts/validate_release_candidate_smoke.py --output <new temporary path>` | 0 | Isolated offline smoke; 22 declared service channels, no live provider/model proof. |
| `python scripts/validate_rollback_compatibility.py --output <new temporary path>` | 0 | Fresh reload, tamper handling and actual historical readers pass. Protected historical archive and deployed rollback **NOT_VERIFIED**, not repaired. |
| `git diff --check`; protected-path diff | 0 / empty | No whitespace failures; frozen datasets, old artifacts, research and historical dossiers unmodified. |
| `python scripts/audits/run_phase8_live_acquisition_audit.py --max-scenarios 1 --output-root <new root>` | 0 | First fresh 16-operation bounded gate PASS. Final clean-code re-probe uses `--require-pass`; retained under final_operations. |
| `python scripts/audits/run_phase8d_authoritative_source_live_probe.py --output-root <new directory>` | 0 | Script execution, **not all-provider acceptance**. Corrected SEC CONFIG_REQUIRED; NVD/arXiv SUCCESS; FactCheck AUTH_REQUIRED. |
| `python scripts/audits/run_realworld_investigation_audit.py --allow-live --profile apple --output-root <new directory>` | 0 | Actual four FastAPI agents, live acquisition permitted, mocks false, temporary persistence, no live LLM key. 3/0/0/0 records; all HTTP 200/unified reports; overall research PARTIAL. |
| `python scripts/evaluation/run_phase8_reference_holdout.py --output-root <new directory>` | 0 | Ten source-adjudicated component cases, safe outcomes 10/10, truths resolved 0/4. No human ground truth or population precision/recall claim. Baseline replay also 0/4. |
| Chromium initial/fixture/API renderer | 1 before fix | Twelve initial pages passed; Scout recorded API at 320px overflowed; output preserved. |
| Chromium 320px result stress + axe | 0 after fix | Eight replay/synthetic states, zero violations/unsafe links/script images/document overflow. Gradient contrast incomplete; no manual screen reader. |
| Apple result replay follow-up | 1 then 0 | Richer payload exposed BrandShield 459px width at 320px; `d58c5ba` corrected it. Failed and corrected directories are preserved separately. |

Full/fast logs and offline smoke/rollback JSON were generated in a unique OS temporary directory. Durable selected reports/screenshots are appended under [independent proof](../../artifacts/phase8_independent_review/). Earlier failed or dirty-source probes are retained with their metadata; final clean code proof uses `220f16f`. No prior Gemini/Codex artifacts were overwritten. Secret-pattern checks on new artifacts found no common API-key/token matches; credentials/private data are not intentionally retained. Redaction is not a universal privacy guarantee.

## Portable rerun examples

Use a **new** output directory each time (scripts reject overwrite). Live commands use network; do not run them as offline acceptance or bypass auth.

```text
pytest tests/ -q
pytest tests/unit tests/chaos tests/security -q
flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
python scripts/validate_release_candidate_smoke.py
python scripts/validate_rollback_compatibility.py
python scripts/validation/verify_frozen_benchmarks.py
python scripts/audits/run_phase8_live_acquisition_audit.py --max-scenarios 1 --require-pass --output-root <new-root>
python scripts/audits/run_phase8d_authoritative_source_live_probe.py --output-root <new-directory>
python scripts/audits/run_realworld_investigation_audit.py --allow-live --profile apple --output-root <new-directory>
python scripts/evaluation/run_phase8_reference_holdout.py --output-root <new-directory>
python -m http.server 8767 --bind 127.0.0.1 --directory frontend
python scripts/audits/audit_phase8_frontend_rendering.py --base-url http://127.0.0.1:8767 --output-root <new-directory> --test-fixtures --api-results <API-summary.json>
python scripts/audits/audit_phase8_result_stress.py --base-url http://127.0.0.1:8767 --api-results <API-summary.json> --output-root <new-directory> --axe-script <installed-axe.min.js>
```

Node: run every `tests/frontend/test_*.js` separately (seven currently). Browser commands require existing Playwright/Chromium and optional explicit axe path. Recorded API replay is not live browser integration; synthetic stress rows are test-only. Do not tune on the held-out manifest or rewrite frozen research labels.

## Remaining owners / release gates

1. Research owner: domain-diverse external adjudication, claim-specific discovery and citation entailment, with false positives/negatives and recall denominators. Current safe abstention is not strong misinformation accuracy.
2. Operator: authorized server-side SEC organization/contact and FactCheck/model credentials if those capabilities are desired. Never store these in frontend, reports or Git. Authenticated provider/model injection behavior remains unverified.
3. Source engineer: issuer/period/unit/XBRL or actual filing passages, full-body/abstract distinctions, corrections and lineage/ownership validation. SEC ticker map cannot resolve every company-name query.
4. UI/accessibility reviewer: evidence-rich real investigations, assistive technology, focus trap/return, contrast on gradients and mobile density. Current screenshots/axe do not establish launch readiness.
5. Data owner: 55 malformed historical dossiers previously inventoried in the original workspace remain untouched. Isolated checkout lacks the archive; do not interpret NOT_VERIFIED as recovered or silently regenerate missing evidence.
6. Infrastructure owner: distributed admission, p95/concurrency/memory tests, bounded completion of provider work beyond research deadline, and staging rollback. No merge/deploy authorized.

Hosted verification of the final pushed head is recorded in the separate [CI closeout](2026-10-14_PHASE8_INDEPENDENT_CI_CLOSEOUT.md); do not assume baseline CI verifies these changes.
