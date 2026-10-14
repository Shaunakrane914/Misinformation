# Phase 8 independent engineering review — 2026-10-14

## Decision

Phase 8 is **not fully accepted**. Acquisition and offline engineering improved substantially; trustworthy general-purpose misinformation adjudication has not been demonstrated. This review used the actual code, reproduced failures, implemented corrections, and retained both unsuccessful and successful observations. A normal API return, an internal relevance score, and a correct investigation are different outcomes.

Baseline: `a10fde82467df21508b4a254507b414cd5b6e9fd`, branch `feat/phase8-completion-gemini`. Its [five-job hosted run](https://github.com/Shaunakrane914/Misinformation/actions/runs/38452943080) was independently checked and successful. Work was isolated on `feat/phase8-independent-audit-codex`; the original and Gemini worktrees were not reset or edited. Implementation checkpoints: `195ae0a`, `220f16f` and `d58c5ba` (real-result BrandShield follow-up). Later commits package documentation and evidence, not a deployment.

| Stage | Assessment | What is actually established |
|---|---|---|
| 8A acquisition | PASS, bounded sample | Fresh public requests succeeded for all 16 protected operations. This is one scenario per operation, not an uptime SLA, complete pagination, or authorization to access restricted content. |
| 8B maximum extraction | PARTIAL | Richer typed metadata and bounded discussion samples exist; the [field matrix](PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md) still distinguishes unavailable/full/partial fields. SEC bodies/XBRL and full arXiv papers are not acquired by these new adapters. |
| 8C intelligence | PARTIAL | Important false-certainty and source-spoofing regressions are corrected. Lexical matching, entity resolution, contradiction axes and source grouping are not calibrated semantic adjudication. |
| 8D expansion | PARTIAL | Four adapters are now registered in the actual shared service as well as routable natively. NVD and arXiv returned live data; SEC requires an owner-approved contact; FactCheck requires a key. Added claim-level value is not established by connectivity. |
| 8E frontend | PARTIAL | Four pages, recorded API replays, hostile/large-input controls and real Chromium checks were exercised. The observed Scout overflow/accessibility-role failures were fixed. Screen-reader acceptance, complete contrast assessment and evidence-rich live investigations remain open. |
| 8F research acceptance | PARTIAL, release gate not met | Real in-process FastAPI scans and persistence execute. Live coverage is sparse; no independent population accuracy/recall or successful truth-resolution baseline was established. |

## Findings and implemented corrections

Additional checkpoint `c420296` applies a shared [model-extraction boundary](../../backend/services/research/model_grounding.py) to BrandShield and Personal Watch: drop uncited records and prevent model status labels from self-verifying a claim or threat. A valid ID still does not establish entailment; free-text assertions require review rather than automatic publication as truth.

Final code checkpoint `0f5a659` removes an additional BrandShield scan-layer substring override, proven with an agent-path spoofing control, and eliminates synthetic “Recent” dates through Scout/BrandShield/Personal Watch normalization and dossiers. Repeated personal sample counts no longer imply acceleration. Visual inspection of the long-topic stress screenshot led to bounded Trending cards while keeping full text available in dossiers. [Final browser replay](../../artifacts/phase8_independent_review/final_progressive_browser/summary.json) passes eight states; recorded historical payloads retain their original supplied wording/dates, not invented fresh content.

| Priority | Reproduction / owner | Correction and regression evidence |
|---|---|---|
| P0 evidence authority | `source_quality.py`: `sec.gov.attacker.example` plus filing words became primary regulatory evidence. Supplied `source_domain` and title hints could influence trust. | Canonical HTTP(S) hostname validation and exact/subdomain boundaries; observed redirect endpoint governs web provenance. Official ownership is separated from a filing/document. Spoofed, malformed, userinfo and landing-page controls in [independent regressions](../../tests/unit/test_phase8_independent_regressions.py). |
| P1 unrelated support | `ClaimIntelligenceEngine.evaluate_claim`: entity presence and high-authority counts supported unrelated acquisitions; missing date could become “Recent”. | [Conservative passage alignment](../../backend/services/research/proposition_grounding.py), polarity/period/scope checks, inspectable URLs, metadata abstention, no invented date and grouped origins. Confidence is explicitly uncalibrated. Initial controls had 12 failures/3 passes; final expanded controls pass. These are development regressions, not independent accuracy estimates. |
| P1 false contradictions | Numerical/geographic/temporal heuristics compared different reporting years, measurements or separate events. | Context checks, metric matching, no bare untyped year as measurement, explicit shared event for location conflicts, dated transition evidence for temporal changes. Ambiguous cases abstain. Complex multi-metric sentences remain a limitation. |
| P1 false independence | Publisher subdomains could count as separate corroboration. | Registrable-publisher heuristic groups common compound suffixes; existing wire/headline clustering retained. This is not a complete public-suffix, ownership or paraphrase-origin solution. |
| P1 fabricated citation | Personal Watch appended the first retrieved evidence ID to model allegations with invalid IDs; dossiers repeated that fallback. | Drop uncited model threats/claims; keep unlinked dossier chains empty and unknown dates blank. New regression checks both paths. Valid IDs still do not prove entailment. |
| P1 specialist certainty | Media-word matches became authentic recordings; lexical quote overlap became verified attribution; names/badges/similar handles became confirmed identity or impersonation; PII patterns became verified unauthorized exposure. | Text-only media reports stay unverified with zero assets analyzed. Quote, identity, impersonation and exposure screens use review-required/heuristic labels. No invented profile URLs or automatic emergency/legal escalation from a pattern alone. |
| P1 BrandShield live false positive | Actual Apple support/store navigation became two `confirmed` customer grievances in the first Apple API run. | Exclude owned navigation and require complaint-specific language. The reproduced support-page control passes; final fresh Apple scan returns three records and no threats. Legitimate delivery complaints remain separately classified as unverified reported grievances. |
| P1 review/bot attribution | Repeated negative or templated reviews could manufacture a fake-review/smear claim; handle/burst similarities could be labeled verified coordination/organic activity. | Repetition remains an observed heuristic, not manipulation. Actual `screen_review_patterns` no longer creates a `FAKE_REVIEW` allegation from repetition alone. Trending declares neither bot automation nor platform-wide organic provenance. |
| P1 audit misinformation | Live runner emitted canned Microsoft conclusions, unconditional PASS and internally derived “precision”. | [API audit runner](../../scripts/audits/run_realworld_investigation_audit.py) calls each real endpoint once; separates execution, acquisition, coverage, sufficiency and correctness; precision/recall remain null without independent adjudication. Full sanitized payloads retained. |
| P1 credential handling | FactCheck key was placed in URL; provider exceptions could contain credentials. | Header-based key, safe error types, auth/rate outcomes and no network when key absent. Cross-origin HTTP redirects remove API-key headers case-insensitively. [Transport tests](../../tests/security/test_safe_http_transport.py) and [audit tests](../../tests/unit/test_phase8_audit_report_truth.py). |
| P1 declared identity | SEC adapters sent an invented organization contact as a “compliant” User-Agent. | Real network calls require server-side `SEC_USER_AGENT` supplied by the owner. Missing configuration returns `CONFIG_REQUIRED` without traffic. No production setting or secret was changed. |
| P2 disconnected integration | New adapters passed direct-router tests but were missing from `AgentReachService.registry`; public capability inventory omitted them. | Small [authoritative channel bridge](../../backend/infrastructure/acquisition/adapters/authoritative/channel.py), actual shared registration and capability inventory. Runtime failures propagate rather than implying a successful scrape. No live-health assumption from registration. |
| P2 API/renderer mismatch | Scout grouped catalyst/contradiction dictionaries raised `KeyError: slice(...)`; grouped news/social keys could masquerade as source records. Personal summary telemetry became a Python dictionary displayed as narrative. | Normalize grouped record contracts, retain canonical Scout sources, keep telemetry separate from prose. Fresh final scans assemble all four unified reports. [Contract regressions](../../tests/unit/test_phase8_audit_report_truth.py). |
| P2 frontend semantics | Substring matching could render `UNSUPPORTED` as supported; heuristic source score looked like certified authority. | Exact verdict aliases, unknown-state abstention, explicitly heuristic score label. Node tests include unknown/adversarial status names. |
| P2 actual browser failures | Scout API replay width was 343px at a 320px viewport; explorer declared `tablist` without required tab semantics. | Constrain/wrap workspace content; use a labeled button group rather than incomplete ARIA tabs. Post-fix 320px replay/stress observations have no document overflow or axe violations. |
| P2 richer-result follow-up | Final Apple replay exposed 459px BrandShield narrative-grid/timeline width at 320px, absent in sparse fixtures. | Responsive grid minima and wrapping timeline, committed in `d58c5ba`. Failed [replay](../../artifacts/phase8_independent_review/final_result_browser/summary.json) and [corrected replay](../../artifacts/phase8_independent_review/final_result_browser_corrected/summary.json) retained; all eight corrected states pass. |

The read-only detached baseline passed its 12 historical golden scenarios. After provenance/policy fixes, serialization changed intentionally. A **new** reviewed [Phase 8 manifest](../../tests/unit/fixtures/research_phase8_independent_golden.json) records rationale; the original manifest is unchanged. Golden tests continue asserting original candidate bytes, IDs and rejection decisions, as well as the reviewed new result/replay hashes. This is an explicit policy change, not a blind refresh of frozen benchmark labels.

## Acquisition and extraction: 16-operation matrix

The [fresh operation evidence](../../artifacts/phase8_independent_review/operations/2026-10-14_04-18-12Z/REAL_ACQUISITION_CAPABILITY_MATRIX.md) retains endpoint, network observation, limit, depth and latency. The final clean-code re-probe is retained under [final operations](../../artifacts/phase8_independent_review/final_operations/). Exact endpoints and fallback paths are in its JSONL records, not inferred from a website count.

| Operation | Provider family / endpoint pattern | Observed useful depth | Completeness boundary |
|---|---|---|---|
| github.read | GitHub REST repositories/README | partial content, 1 record | README is not repository-wide content; owner/update time is not document authorship/publication. |
| github.issues | GitHub REST issues | partial content, 2 records | Sampled issue bodies/comments; no complete event history. |
| github.prs | GitHub REST pulls | partial content, 3 records | Bounded bodies/changed-file samples, not every review or diff. |
| github.commits | GitHub REST commits | metadata, 3 records | Commit identities/messages; not a complete file history. |
| github.releases | GitHub REST releases | partial content, 3 records | Release notes/assets metadata; no complete asset downloads/history. |
| youtube.read | public watch metadata / native extractor | metadata, 1 record | No video-byte/forensic analysis. |
| youtube.transcript | public captions / native extractor | direct caption content, 1 record | Caption track/language boundaries; not visual-content comprehension. |
| youtube.comments | public/native comment extraction | direct sample, 3 records | Not complete comment/reply history or platform-wide sentiment. |
| v2ex.latest | V2EX public topics | partial content, 3 records | Current list sample, not all topics. |
| v2ex.search | V2EX public node/topic discovery | partial content, 3 records | Node discovery is not unrestricted full-text search. |
| v2ex.topic | V2EX public topic | partial content, 1 record | One topic and available provider fields. |
| v2ex.replies | V2EX public topic replies | direct sample, 3 records | Sampled replies, no complete discussion guarantee. |
| web.read | public HTTPS document | partial content, 1 record | Bounded HTML/text/metadata; canonical declaration cannot authenticate its origin. |
| rss.read | public feed XML | syndicated summary, 3 records | Feed content differs from linked article body; enclosure links are not acquired assets. |
| xiaoyuzhou.podcast | public podcast page/state | metadata, 1 record | Identity/show metadata, no full audio transcript. |
| xiaoyuzhou.episodes | public podcast episode list/state | partial content, 3 records | Bounded show-note/episode samples, not complete pagination/transcripts. |

GitHub headers/rate limits, native YouTube restrictions, per-attempt network bounds, URL/DNS/redirect guards and pagination metadata remain relevant. Neither run tests every auth/rate-limit/provider-restricted variation. “Direct full” in an adapter outcome describes the returned sample/track, not the whole platform. A 5-second HTTP timeout is per attempt, not a universal 5-second end-to-end SLA; native extractor routes can be slower.

### New authoritative sources

[Config-safe probes](../../artifacts/phase8_independent_review/2026-10-14_sources_config_safe/summary.json) are separate from the earlier probe that exposed the invented SEC-contact problem.

| Adapter | Fresh outcome | Interpretation / missing capability |
|---|---|---|
| SEC EDGAR | Earlier submission request succeeded; corrected runtime is CONFIG_REQUIRED without owner contact | Ticker/CIK map and submission metadata only. No full filing body or company-facts/XBRL engine. Metadata is discovery, not acquired primary financial content. |
| NIST NVD | SUCCESS, one CVE | CVE description/CVSS/reference metadata; not proof of general product quality, exploitation prevalence or reputational risk. |
| arXiv | Initial timeout; later SUCCESS, three abstracts | IDs/authors/abstract/category/links; PDF URL is not acquired full paper or peer-review certification. |
| Google FactCheck | AUTH_REQUIRED, zero requests without key | Publisher-attributed ClaimReview metadata, not review body or Aegis truth verdict. Successful authenticated acquisition remains unverified. |

No additional provider was added merely to increase integration count. The demonstrated next gap is issuer/period/unit-aligned filing passages or XBRL facts and useful claim-specific discovery, not another generic search adapter. Official correction/IR/advisory feeds warrant scoped trials once such a gap is measured.

## Independent misinformation evaluation

[Held-out manifest](../../tests/evaluation/phase8_reference_holdout.json) and [before](../../artifacts/phase8_independent_review/holdout_before/summary.json)/[after](../../artifacts/phase8_independent_review/final_holdout/summary.json) results are separate from development controls and frozen retrieval data. Sources were checked directly: [SEC policy](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), [arXiv indexed paper](https://arxiv.org/abs/1706.03762). Labels were source-adjudicated by this coding assistant, **not by a human annotator**. Short retained excerpts, counterfactual provenance, exact claims, expected safe outcomes, output, citations and rationale are recorded per case. Replays do not claim new live retrieval.

- Ten cases: two true reference facts, two false counterfactuals, plus irrelevant announcement, quote, recency, spoof, metadata-only and conditional controls.
- Both baseline and corrected engine: 10/10 safe outcomes, **0/4 labeled truths resolved**. This holdout does not demonstrate an accuracy improvement. It reveals conservative false-negative/non-resolution behavior.
- No unsupported positive support verdicts in that sample. Abstention is safe but is not successful claim verification.
- Precision, recall and population accuracy are null: no retrieval recall denominator or representative human-ground-truth benchmark exists. Internal accepted-source ratios are not independent precision.
- Development regressions additionally cover financial scope/periods/negation, unrelated primaries, duplicate publishers, media/quote certainty, actual navigation contamination and missing citations. They are not a held-out accuracy set.

A balanced domain-diverse, externally adjudicated evaluation covering partially true/misleading/outdated claims, real impersonations, financial manipulation, syndicated misinformation, quotations and adversarial retrieval is still a release requirement. The twelve original “integration” scenarios largely exercise synthetic helper inputs, sometimes with manually assembled expected outcomes; they must not be advertised as end-to-end real-world accuracy.

## Four-agent assessment and real API path

[Initial Microsoft API payloads](../../artifacts/phase8_independent_review/2026-10-14_api/summary.json), [first Apple run](../../artifacts/phase8_independent_review/2026-10-14_apple_api/summary.json) and [clean implementation-head Apple run](../../artifacts/phase8_independent_review/final_apple_api/summary.json) retain exact requests and sanitized outputs. The initial Microsoft report writer failed on Trending's provider-summary mapping; its JSON was preserved and the writer corrected. Do not mistake that incomplete report for a successful final run.

Final API run at clean `220f16f`, mocks disabled, no configured live LLM key: BrandShield 3 records/15.224s, Trending 0/13.617s, Scout 0/26.148s, Personal Watch 0/10.124s. All four returned HTTP 200 and non-null unified reports. BrandShield produced no threats from the sampled Apple navigation pages. These requests reached real agent/research/planning/acquisition/qualification/persistence paths using temporary SQLite/dossiers; LLM reasoning degraded to honest deterministic fallback. API-level explicit network acquisition flags and conclusion correctness remain NOT_VERIFIED where absent, despite separate source-probe proof.

| Agent | Improved behavior | Remaining research limitation |
|---|---|---|
| Scout | Explicit official URL, period/unit and finite-number alignment; no fabricated SEC citation, canned momentum/risk or source-role title promotion; grouped output survives report assembly. | No live XBRL extraction, complete issuer/GAAP/currency semantics or financial causation proof. Price dispersion is not misinformation. Quote fallbacks add latency outside research budget. |
| Trending | Pattern similarity is labeled heuristic, not verified bots; no global organic/viral inference from sparse samples. | Live sample empty; observation windows/coverage and platform-wide velocity cannot be validated. Pairwise similarity remains sampling-sensitive. |
| BrandShield | Navigation is not a customer complaint; repetition is not fake reviews/smear; badge/lookalike is not confirmed executive impersonation. | Lexical threats and model-linked statements still require contextual adjudication. Ownership/solicitation authentication and real adversarial campaign evaluation are incomplete. |
| Personal Watch | No manufactured citations, recording authentication, quote certainty, authenticated identity or unauthorized-exposure claim from text patterns alone. | Sparse profiles do not prove identity, recency or global threat absence. No media bytes/forensics. LLM ID validation is necessary but does not prove citation entailment. |

## Frontend, architecture and performance

[Browser observations](../../artifacts/phase8_independent_review/2026-10-14_browser/summary.json) cover four initial/fixture/API states at 1440/390/320px. [Post-fix stress](../../artifacts/phase8_independent_review/stress_after/summary.json) covers eight 320px states: actual recorded API replay and separately marked synthetic 200-record/long-title/hostile-link inputs. No script-bearing images, `javascript:` links, page exceptions, document overflow or axe violations after fixes. Color-contrast remained incomplete on gradients; this is not WCAG certification or manual screen-reader acceptance. Modal open/focus/Escape checks passed in the earlier 12 fixture states, not a comprehensive focus-trap audit.

The later Apple result found an additional BrandShield overflow and canned consumer-discourse label; both were corrected after the clean `220f16f` API run. The final corrected browser replay uses the original recorded payload without fabricating fresh backend data. Its old narrative wording is historical payload content, not evidence that a new scan acquired consumer opinions. The latest backend emits sampled-reference/unassessed wording instead.

Screenshots were actually inspected, including Scout and Personal Watch narrow result views. They revealed misleading canned financial narrative and raw summary dictionary prose, both corrected in backend output. The dense stacked cards remain long on mobile; source lists use bounded presentation/progressive disclosure. Supplying 200 records is not proof every record was rendered or that the user can adjudicate hundreds efficiently. Evidence-rich **live** result usability remains unverified because these investigations were sparse. Recorded replay is not a fresh browser-to-server request.

The modular-monolith stages, compatibility shims, central safe HTTP transport and per-agent admission guards are sound foundations. This review consolidated authority policy in the shared source classifier and added one narrow registry bridge; it did not replace the architecture. Transitional singleton state, multiple finding/verdict engines, large endpoint/report builders, heuristic ownership/syndication grouping and inconsistent agent response shapes remain debt. Shared network worker deadlines can return while provider work finishes; per-process admission guards are not distributed limits.

Measured local suite: 1,156 tests/64.78s; fast suite 948/30.49s on Windows Python 3.13.5. Final four API requests took 10.124–26.148s. Post-fix rendering observed roughly 62–205ms in the earlier narrow replay/stress sample; noisy browser/network/test concurrency prevents a before/after speedup claim. Review similarity/contradiction loops are pairwise; bounded production source budgets are important. No production concurrency, memory endurance, p95 latency or distributed scaling benchmark was performed.

## Release and continuation gates

Keep deployment/merge blocked. Highest next priorities: externally adjudicated claim-to-passage evaluation, claim-relevant discovery coverage, real issuer/period/unit-aligned financial evidence, model citation entailment/injection evaluation with authorized keys, ownership/lineage validation and evidence-rich manual accessibility/usability acceptance. Configure SEC contact and FactCheck key only in authorized server-side settings; never invent or commit them. Historical corrupt dossiers remain protected and cannot be interpreted as trustworthy evidence.

See the [verification and continuation handoff](../handoffs/2026-10-14_PHASE8_INDEPENDENT_REVIEW.md) for exact commands, counts, evidence locations, commit/push state and hosted CI. This report is an independent engineering assessment, not a raw transcript, chain-of-thought record, or assurance that all possible defects were found.
