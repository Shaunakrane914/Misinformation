# Architecture remediation: implementation decisions and maintenance guide

Date: 2026-10-12. Scope: the local correctness/security remediation described in the [implementation report](../architecture/ARCHITECTURE_REVIEW_REMEDIATION_2026-10-12.md). This is a decision record for the next coding agent, not a raw conversation transcript, a new architecture phase, or a claim of production deployment.

The changes intentionally preserve existing public interfaces and historical research while making authorization, evidence quality, failure states and test isolation more honest. The report records the executed gates and their limitations. Re-run the gates after subsequent changes; do not turn the recorded counts into a permanent acceptance target.

## Read this first

1. Read [AGENTS.md](../../AGENTS.md) and the [documentation portal](../index.md).
2. Read the [remediation report](../architecture/ARCHITECTURE_REVIEW_REMEDIATION_2026-10-12.md), then this decision record beside the linked implementations and tests.
3. Read [rollback verification](../operations/ROLLBACK_VERIFICATION.md) before touching persistence or asserting release readiness.
4. Inspect `git status --short` and preserve the existing worktree. This remediation was delivered locally without a commit, push or production deployment.

## Invariants preserved

- Do not edit the frozen [candidates](../../tests/retrieval_benchmark/candidates.jsonl), [labels](../../tests/retrieval_benchmark/labels.jsonl) or [scenarios](../../tests/retrieval_benchmark/scenarios.jsonl) to make a test pass.
- Do not rewrite, delete, re-seal or fabricate historical dossiers in `backend/data/dossiers/`. Do not erase `research/` or `artifacts/`.
- Preserve working scrapers, compatibility shims and the 16 recovered operation contracts. The current route tests are [test_recovered_operation_routes.py](../../tests/unit/test_recovered_operation_routes.py); the absent older `tests/contract/test_recovered_operations_contract.py` link was corrected in the orientation during this handoff.
- Missing evidence, missing credentials, policy blocks and timeouts must remain observable failures or uncertainty. They must not become positive evidence or green health badges.
- An empty explicit platform list is an opt-out. An empty validated source plan is a denial. Neither means "use all defaults."
- Operator credentials belong on the server, never in public JavaScript, repository reports or logs.
- Tests and validators write to temporary storage. Historical outputs are research artifacts, not disposable test fixtures.

## Decision 1: connect to the address that was actually validated

Implementation: [URL validation](../../backend/infrastructure/acquisition/security/url_validator.py), [shared public HTTP transport](../../backend/infrastructure/acquisition/network/http.py).

An earlier URL/DNS check could pass, followed by a second DNS lookup resolving to an internal address. A cached Boolean "safe" answer is therefore not authority to establish a connection.

The shared transport resolves fresh addresses at connection time, rejects the entire answer set if any address is private/reserved, and connects to a validated numeric socket address. The original hostname remains the HTTP Host and HTTPS TLS SNI/certificate identity. Environment proxies are disabled for this boundary. Redirects are validated, and credentials are stripped when scheme, hostname or effective port changes.

DNS work has a bounded caller wait and eight resolver slots. HTTP has connection/response wall-clock bounds, a default five-second connection budget, a one-million-byte response cap, bounded redirects and bounded retries. The response stream applies the remaining deadline to each underlying read so a slow trickle cannot extend the response indefinitely. Non-finite `Retry-After` values are rejected. A provider delay beyond the local retry budget is surfaced rather than slept through.

Rejected alternatives:

- A preflight-only `is_safe_url()` check leaves the DNS time-of-check/time-of-use gap.
- Resolving to an IP and replacing the URL hostname would break hostname-dependent routing and TLS identity.
- Trusting environment proxies would move destination enforcement outside this transport.

Tradeoffs and limits: mixed public/private DNS answers fail closed; capacity exhaustion may reject a legitimate request. Timed-out OS resolution cannot be forcibly terminated, so daemon workers finish independently. Retry and redirect limits bound a sequence, but a five-second connection budget is not a universal five-second investigation SLA. Some fixed-origin legacy/provider-tool paths still do not use this transport; do not claim universal network pinning.

Regression anchors: `test_connection_revalidates_after_cached_public_dns_answer`, `test_pinned_https_keeps_original_sni_and_does_not_reresolve`, `test_scheme_or_port_redirect_strips_credentials`, `test_slow_trickle_headers_and_body_obey_wall_clock_deadline` in [security regressions](../../tests/security/test_review_security_regressions.py), plus [safe HTTP tests](../../tests/security/test_safe_http_transport.py).

## Decision 2: unsafe fallback is not recovery

Implementation: [typed WebAdapter](../../backend/services/agent_reach/native/adapters/web.py), [canonical router](../../backend/infrastructure/acquisition/routing/router.py), [Jina adapter](../../backend/infrastructure/acquisition/adapters/web/jina.py).

The compatibility method `_fetch_scrapling()` now delegates to the bounded public transport. The Playwright helper remains present, but normal acquisition no longer invokes automatic browser rescue: browser subrequests cannot currently enforce the pinned destination boundary. A rejected read must not silently switch to a transport that bypasses the rejection. Structured policy, rate-limit and authentication failures also remain failures.

Keeping the old automatic rescue would increase retrieval success at the cost of invalidating the security guarantee. Deleting all browser/scraper code would unnecessarily break compatibility. The chosen boundary preserves implementations while withholding automatic authorization.

JS-only pages can now fail honestly. Re-enable browser rescue only after the entire navigation/subresource/redirect boundary has a reviewed enforceable policy and adversarial tests. A successful browser launch or a single preflight URL check is insufficient.

Regression anchors: [acquisition chaos tests](../../tests/chaos/test_agent_reach_chaos.py), [native bounded HTTP tests](../../tests/unit/test_native_executor_bounded_http.py), and the browser/fallback assertions in the security/acquisition suites.

## Decision 3: original sources and official authorities are different concepts

Implementation: [source quality](../../backend/services/research/source_quality.py), [grounded synthesis](../../backend/application/research/synthesis.py), [agent enrichment](../../backend/services/agent_reach/profile.py).

Source trust comes from the parsed canonical URL hostname. A caller-supplied `source_domain` cannot override it. Registry membership uses exact hostname or dot-delimited subdomain matching, not substring matching: `sec.gov.attacker.example` is not `sec.gov`. Corporate identity is an explicit verified-domain mapping, injectable into `SourceQualityEngine`; an unknown company name is not converted into a guessed official hostname.

`primary_source` means original/direct material, not necessarily official authority. An arbitrary GitHub document can remain primary/original while `official_source` is false. Synthesis no longer upgrades any primary source to `KNOWN_FACT`. Its current deterministic rule requires the leading item to be both official and primary, or at least two credible independent groups with exactly the same normalized statement; contradictions take precedence as `CONTESTED`. Sharing a query class alone is not corroboration.

The rule is deliberately conservative, not a complete semantic fact-verification system. Explicit registries still require ownership review, and exact normalized agreement misses paraphrases. `KNOWN_FACT` is a current heuristic classification, not cryptographic or universal truth proof. Do not broaden a substring rule or count unrelated citations to improve apparent coverage.

Profiles enrich acquisition results without inventing article depth. Unknown publication dates remain unknown rather than being filled with the current time.

Regression anchors: `test_impostor_domains_never_become_official_or_primary`, `test_unknown_company_name_is_not_a_verified_domain`, `test_original_github_document_is_not_automatically_a_known_fact`, `test_unrelated_secondary_results_do_not_become_fact_from_group_count` in [security regressions](../../tests/security/test_review_security_regressions.py), and `test_scout_never_promotes_snippets_or_attacker_domain_to_primary` in [acquisition policy tests](../../tests/unit/test_acquisition_policy_integrity.py).

## Decision 4: a persisted ID must identify a complete, non-overwritten dossier

Implementation: [ReplayLedger](../../backend/services/research/replay_ledger.py).

New IDs use `R-<YEAR>-<32HEX>` from a full UUID. Existing shorter historical IDs remain accepted by the bounded ID grammar. Path validation happens before memory-cache access and rejects traversal and existing symlink escapes.

The writer validates structure, writes a complete temporary file in the target directory, flushes and fsyncs it, and publishes with an exclusive hard link. A collision retries allocation instead of replacing an existing file. Cache insertion and returning the ID occur only after successful publication; failures propagate and temporary files are cleaned. Returned dossier dictionaries are defensive copies, so a caller cannot mutate the cached record accidentally.

Rejected alternatives:

- A six-hex-character suffix has a materially smaller collision space.
- Direct `open(..., 'w')` or an overwrite-style replace can destroy an earlier investigation.
- Returning an ID after swallowing an I/O failure falsely implies durable persistence.

Tradeoffs: publication requires a filesystem supporting the chosen hard-link operation; failure is explicit rather than an unsafe overwrite fallback. This is not a transactional distributed database or a guarantee against every filesystem/power-loss failure. Do not invent fallback overwrite behavior for an unsupported storage target.

Regression anchors: `test_new_dossier_id_and_snapshot_integrity`, `test_colliding_id_never_overwrites_existing_file`, `test_dossier_path_traversal_is_rejected`, `test_partial_write_failure_never_returns_a_persisted_id` in [security regressions](../../tests/security/test_review_security_regressions.py).

## Decision 5: replay verification must say what was checked

Implementation: [ledger verification/playback](../../backend/services/research/replay_ledger.py), [replay API](../../backend/api/replay.py), [rollback validator](../../scripts/validation/validate_rollback_compatibility.py).

New dossiers add exact captured candidate text, complete SHA-256 hashes and a versioned checksum manifest for the serialized payload. The old candidate-hash field remains a 16-character prefix for historical readers. Verification requires valid nested structures, matching snapshot/hash membership, captured-text hashes and payload checksum. It does not merely count hash fields.

These are drift-detection checksums, not signatures. A writer able to modify the record can recompute the manifest. A matching checksum does not authenticate authorship, prove a fetched statement true, or prove an external page is unchanged. In trace playback, `findings_verified` is a compatibility counter for intact recorded findings, not independent fact checking.

Legacy records without a manifest remain readable as `LEGACY_UNSEALED`, with zero integrity-verified candidate/finding counters. Malformed structures and checksum failures return `FAILED` before walking nested data or performing refetch network calls. Historical `quality_tensor: null` means an unknown metric and remains readable; replacing it with invented zeros or treating it as JSON corruption would misrepresent the archive.

The historical golden manifest was not re-baselined. [Golden tests](../../tests/unit/test_research_pipeline_golden.py) verify new additive fields separately and compare the legacy projection with the existing baseline. The exhausted-deadline scenario explicitly tests the corrected no-read behavior instead of silently updating historical proof.

The [rollback report](../operations/ROLLBACK_VERIFICATION.md) records 55 existing JSON parsing failures and 2,445 readable unsealed records. Those protected files were untouched. Accepting nullable unknown metrics does not conceal those parsing failures. Recovery needs trustworthy backups and owner direction, not synthesized contents or deletion.

Regression anchors: `test_unsealed_or_tampered_trace_never_claims_verified` in [security tests](../../tests/security/test_review_security_regressions.py), [legacy replay tests](../../tests/unit/test_replay_verification.py), and [malformed nested-shape tests](../../tests/unit/test_replay_structure_regressions.py). The rollback validator also exercises actual historical readers from a locally available baseline commit in separate processes; it does not prove a deployed full-application rollback.

## Decision 6: source plans authorize exact operations, not broad channels

Implementation: [acquisition service](../../backend/infrastructure/acquisition/service.py), [typed request router](../../backend/infrastructure/acquisition/routing/router.py), [operation dispatcher](../../backend/infrastructure/acquisition/routing/channel_dispatcher.py), [runtime capabilities](../../backend/services/agent_reach/native/operation_capabilities.py).

Typed retrieval executes the validated source plan's actions, including their exact operations such as read or transcript, rather than flattening them into channel searches. An empty plan returns no fragments. The router does not run separate strategy discovery on this path, which would acquire unapproved sources. Legacy discovery remains available but is constrained by explicit channel boundaries.

Runtime assessment is repeated at dispatch and direct-read boundaries. A previously approved operation can become unavailable through cooldown, credentials or policy before execution. A denied operation produces exclusion/defer telemetry without recording a new provider failure that would overwrite the observation which caused the denial. Legacy authentication probes do not disable actually public operations; runtime operation policy is the authority.

Agent-specific enrichment still runs after approved dispatch. In particular, Personal Watch redacts phone numbers, SSNs and residential addresses from snippet/content. Do not remove enrichment when simplifying the routing path. This regex protection is not a claim that all possible PII, titles, metadata or URLs are sanitized.

Regression anchors: `test_typed_plan_preserves_operations_and_never_runs_strategy_discovery`, `test_empty_validated_source_plan_fails_closed`, `test_direct_channel_dispatch_preserves_cooldown`, `test_direct_read_cannot_bypass_policy`, `test_typed_plan_keeps_personal_watch_redaction_without_depth_upgrade`, `test_empty_platform_optout_stays_empty` in [acquisition policy tests](../../tests/unit/test_acquisition_policy_integrity.py).

## Decision 7: deadlines apply to actual work, including executor cleanup

Implementation: [multi-query retrieval](../../backend/infrastructure/acquisition/service.py), [research reading stage](../../backend/application/research/reading.py), [deep reader](../../backend/services/research/deep_reader.py), [registry discovery](../../backend/services/agent_reach/registry.py).

Zero read budgets stay zero, configured caps constrain requests, and exhausted deadlines do not launch more reads. Source reads and subsequent searches consume the same retrieval deadline. Remaining time is passed to readers. Executors cancel pending futures and do not wait for running workers during deadline-return cleanup; a context-manager shutdown wait had previously defeated the deadline.

This protects caller latency, not forced cancellation of a running Python thread. Workers must retain their own network/time/size bounds. Never claim that returning at the deadline instantly stops external work. Further concurrency redesign should consider request-scoped state or cooperative cancellation instead of increasing thread counts without limits.

Regression anchors: `test_deep_reading_skips_zero_budget_or_expired_deadline`, `test_deep_reader_returns_at_deadline_without_executor_shutdown_wait`, `test_retrieve_many_returns_at_deadline_without_two_second_grace`, `test_source_read_consumes_same_deadline_and_does_not_launch_late_search`, `test_registry_discovery_deadline_is_bounded_and_reports_unknown` in [acquisition policy tests](../../tests/unit/test_acquisition_policy_integrity.py).

## Decision 8: protect mutations and bound shared-agent admission

Implementation: [operator authorization](../../backend/api/security.py), [agent endpoints](../../backend/api/agents.py), [acquisition endpoints](../../backend/api/agent_reach.py), [settings](../../backend/core/settings.py).

Both response-deployment aliases require the server-side `ADMIN_API_TOKEN` bearer secret before any database work. Missing configuration returns 503; missing/wrong credentials return 401. Constant-time comparison is used. Public research endpoints remain public: this is scoped operator authorization, not a full user/account/RBAC system.

Blocking synchronous scans execute in worker threads rather than on the ASGI event loop. Each shared mutable agent has a nonblocking per-process admission lock covering initialization and its entire synchronous scan. A second scan of that agent returns 429 with `Retry-After: 3`, rather than interleaving session state or building an unbounded wait queue. Errors release the lock. Different agents can still run independently.

The chosen fix preserves singleton interfaces with minimal disruption. Request-scoped agents or an explicit durable job queue would be a larger composition/workflow change and remain future architecture work. Locks are not distributed across processes, and they are not an abuse-prevention or tenant quota system. A client cancellation must not be interpreted as a completed worker scan.

Regression anchors: operator fail-closed/valid-token tests, `test_parallel_scans_are_bounded_and_cannot_share_session_state`, `test_scan_admission_releases_after_failure`, and event-loop/worker-thread tests in [API hardening tests](../../tests/unit/test_api_hardening_regressions.py).

## Decision 9: uncertainty is a product state, not an error to hide

Implementation: [dashboard/API projection](../../backend/api/system.py), [BrandShield grouping](../../backend/agents/brandshield/agent.py), [operation-health UI](../../frontend/operation-health.js), [dashboard rendering](../../frontend/dashboard.js), [Netlify provider function](../../frontend/netlify/functions/gemini.js), [LLM gateway](../../backend/infrastructure/llm/gateway.py).

Uncertain verdict labels remain uncertain rather than being coerced to false. Zero evidence creates zero groups, not a synthetic group. Agent inventory says unprobed instead of claiming every agent is online. Health subscriptions repaint on TTL expiry and visibility changes; expired/failed observations cannot remain indefinitely green. Mixed operation health is not a generic healthy channel.

Names and source links use safe DOM construction; source links require HTTP(S). The Netlify function returns genuine bounded provider failure when keys are missing/exhausted instead of fabricating attributed evidence. Production mock execution is prohibited both by normalized startup configuration and runtime override/`allow_mock` guards. Gateway last-response telemetry is execution-context-local.

The alternative of showing impressive default results would undermine the evidence-first contract. Offline success with `INSUFFICIENT_EVIDENCE` is a correct smoke outcome, not proof of live scraping. Frontend tests are behavioral script tests, not exhaustive browser/device/accessibility validation.

Regression anchors: [API honesty tests](../../tests/unit/test_api_hardening_regressions.py), [frontend security/health tests](../../tests/frontend/test_security_and_health_regressions.js), [operation-health tests](../../tests/frontend/test_operation_health.js), [gateway tests](../../tests/unit/test_llm_gateway.py), and [product integrity tests](../../tests/unit/test_product_honesty_and_integrity.py).

## Decision 10: execution evidence must be safe and reproducible

Implementation: [test isolation](../../tests/conftest.py), [process regressions](../../tests/unit/test_process_hardening.py), [offline validation support](../../scripts/validation/isolated_runtime.py), [active CI](../../.github/workflows/ci.yml).

Temporary database/dossier locations and blank provider/cloud credentials are established before application imports. Network/DNS and locally authenticated provider CLI commands are blocked for offline runs; runtime, persistence and DNS state reset between tests. Windows event-loop socketpair plumbing is narrowly allowed without allowing ordinary loopback acquisition.

Validators use isolated subprocess storage; default smoke does not overwrite artifact reports. The CI workflow covers all branches, full offline tests, frontend scripts and frozen integrity checks. Editing the workflow does not mean remote CI ran. Reader compatibility, actual live acquisition, full deployed rollback and staging load are distinct gates.

Configuration now resolves canonical/legacy SQLite names consistently, rejects unsafe nonpersistent SQLite paths, prefers server Supabase credentials without promoting an anonymous key for server writes, and aligns versions to the existing 4.1.0 package version. Existing local data is not mass-migrated or overwritten. Automatic SQLite/cloud reconciliation remains unimplemented.

Use the [testing/CI matrix](../testing/CI_COVERAGE_MATRIX.md), [production configuration matrix](../operations/PRODUCTION_CONFIGURATION_MATRIX.md) and [operations runbook](../operations/V1_OPERATIONS_RUNBOOK.md) for commands and environment requirements.

## Condensed decision transcript

This is a factual summary of the engineering decisions, not a verbatim reconstruction of chat messages or private reasoning.

| Question raised by the review | Implemented conclusion | Next-agent guardrail |
|---|---|---|
| Can a safe URL check authorize later DNS resolution? | No; validate and pin the actual connection destination. | Keep the connection-time test even when optimizing caches. |
| Can a browser fallback rescue a security rejection? | Not automatically without equivalent network enforcement. | Preserve the helper, but do not re-enable unsafe fallback for coverage. |
| Does primary/original mean official or true? | No; role, authority and epistemic state remain distinct. | Never broaden hostname matching or count unrelated results as corroboration. |
| Is the presence of hashes enough to claim replay verified? | No; verify recorded bytes and structure; legacy remains unsealed. | Do not retrospectively seal protected historical data. |
| Can an empty plan fall back to default discovery? | No; exclusions remain exclusions and exact operations survive. | Test both service entrypoints and direct dispatch/read bypasses. |
| Is moving sync code into threads sufficient? | No; mutable shared agents also need bounded admission. | Preserve 429 behavior or replace it with reviewed request-scoped/job architecture. |
| Should offline smoke manufacture results? | No; zero evidence and honest uncertainty are valid. | Keep offline isolation and live-acquisition acceptance separate. |
| Should invalid historical files be removed to pass rollback? | No; report archive failure and recover only from trustworthy backups. | Treat the existing archive blocker as unresolved owner-directed work. |

## Safe continuation checklist

- Start with the current diff and linked regression tests. Run the isolated offline gates documented in the handoff/runbooks; never weaken isolation to make them pass.
- Keep protected archive and frozen hashes unchanged. If a command modifies tracked benchmark output, inspect and back up the diff before any narrowly authorized restore.
- Do not claim release acceptance while historical archive validation fails. Recover from owner-approved trustworthy backups; keep the original files and provenance intact.
- Add new official-domain mappings through reviewed identity knowledge, not guessed target-name matching. Test impostor suffixes and supplied-domain spoofing for each new classification rule.
- Any transport/fallback change needs cached-DNS-rebinding, redirect credentials, private mixed answers, slow trickles and size-cap tests.
- Any ledger change needs collision/no-overwrite, traversal, partial-write failure, tamper, malformed nested structures and actual old-reader compatibility tests.
- Any source-planning change needs operation preservation, cooldown, direct-read policy, empty exclusions and Personal Watch enrichment tests.
- Record newly executed results and explicit `NOT_VERIFIED` boundaries. Do not rewrite previous outcomes as if remote CI, live scraping or a deployed rollback had already occurred.
