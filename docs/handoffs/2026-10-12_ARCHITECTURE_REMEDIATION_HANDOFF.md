# Next-agent handoff: architecture review remediation

Captured on 2026-10-12, Asia/Calcutta. Start with [AGENTS.md](../../AGENTS.md); this record preserves engineering context, not new authority to mutate protected research or deploy software.

## Where the previous agent stopped

- User scope: review architecture and defects, implement priority fixes, then leave durable explanations, execution records and safe continuation instructions.
- Observed branch: `feat/phase7-2c-root-cleanup`.
- Observed base/HEAD: `b3f3fc8248a92d0d15026327b5e9b14f273a0064`.
- Implementation and this handoff are **local and uncommitted**. No push, PR, production deployment, historical recovery or live provider audit was performed.
- Preserve the existing dirty worktree, including newly added untracked implementation/test files. A checkout of the base commit alone does not contain these fixes.
- Version remains the existing project metadata version `4.1.0`; this work does not mint a new release.
- No frozen candidates/labels/scenarios, historical dossier contents, research trees or tracked artifact proof were edited.

Read [the implementation report](../architecture/ARCHITECTURE_REVIEW_REMEDIATION_2026-10-12.md), [decision rationale](2026-10-12_ARCHITECTURE_REMEDIATION_DECISIONS.md), [testing runbook](2026-10-12_ARCHITECTURE_REMEDIATION_TESTING.md) and [execution work log](2026-10-12_ARCHITECTURE_REMEDIATION_WORK_LOG.md) together. The [context JSON](2026-10-12_ARCHITECTURE_REMEDIATION_CONTEXT.json) provides the same entry points for programmatic retrieval.

## First five minutes

From the repository root, inspect—not restore—the current state:

```sh
git status --short --untracked-files=all
git branch --show-current
git rev-parse HEAD
git diff --stat
git diff --check
python scripts/validation/verify_frozen_benchmarks.py
```

Then read the diff for the subsystem you will change and its linked regressions. If HEAD or files differ from this snapshot, treat this handoff as historical context and reconcile the differences. Do not overwrite newer work or assume the old results validate a changed checkout. Do not use `git clean -fdx`, destructive restore/reset, or benchmark re-baselining.

## Implementation map

These links point to maintained implementations, not duplicate source copies in documentation.

| Concern | Code entry points | Read first in tests |
|---|---|---|
| Operator writes and scan admission | [API security](../../backend/api/security.py), [agent endpoints](../../backend/api/agents.py) | [API hardening](../../tests/unit/test_api_hardening_regressions.py) |
| Shared public HTTP, DNS and redirects | [HTTP transport](../../backend/infrastructure/acquisition/network/http.py), [URL validator](../../backend/infrastructure/acquisition/security/url_validator.py), [Jina wrapper](../../backend/infrastructure/acquisition/adapters/web/jina.py) | [review security](../../tests/security/test_review_security_regressions.py), [safe HTTP](../../tests/security/test_safe_http_transport.py), [native transport](../../tests/unit/test_native_executor_bounded_http.py) |
| Exact source plans and operation policy | [acquisition service](../../backend/infrastructure/acquisition/service.py), [router](../../backend/infrastructure/acquisition/routing/router.py), [dispatcher](../../backend/infrastructure/acquisition/routing/channel_dispatcher.py), [runtime capabilities](../../backend/services/agent_reach/native/operation_capabilities.py) | [policy and budgets](../../tests/unit/test_acquisition_policy_integrity.py), [recovered routes](../../tests/unit/test_recovered_operation_routes.py) |
| Agent enrichment and metadata | [profiles](../../backend/services/agent_reach/profile.py), [native adapters](../../backend/services/agent_reach/native/adapters/) | [profiles](../../tests/unit/test_agent_retrieval_profiles.py), [shared fabric](../../tests/unit/test_shared_acquisition_fabric.py) |
| Research authority, synthesis and reads | [source quality](../../backend/services/research/source_quality.py), [synthesis](../../backend/application/research/synthesis.py), [reading stage](../../backend/application/research/reading.py), [deep reader](../../backend/services/research/deep_reader.py) | [review security](../../tests/security/test_review_security_regressions.py), [golden characterization](../../tests/unit/test_research_pipeline_golden.py) |
| Immutable publication and honest replay | [ledger](../../backend/services/research/replay_ledger.py), [replay API](../../backend/api/replay.py) | [replay verification](../../tests/unit/test_replay_verification.py), [structure cases](../../tests/unit/test_replay_structure_regressions.py) |
| Product honesty and health display | [system API](../../backend/api/system.py), [health client](../../frontend/operation-health.js), [dashboard](../../frontend/dashboard.js), [Netlify provider](../../frontend/netlify/functions/gemini.js) | [frontend security/health](../../tests/frontend/test_security_and_health_regressions.js), [operation health](../../tests/frontend/test_operation_health.js) |
| Configuration and isolated verification | [settings](../../backend/core/settings.py), [database](../../backend/db/database.py), [LLM gateway](../../backend/infrastructure/llm/gateway.py), [isolation support](../../scripts/validation/isolated_runtime.py), [test setup](../../tests/conftest.py) | [process hardening](../../tests/unit/test_process_hardening.py), [LLM gateway](../../tests/unit/test_llm_gateway.py) |
| Delivery gates | [active CI](../../.github/workflows/ci.yml), [smoke](../../scripts/validation/validate_release_candidate_smoke.py), [rollback](../../scripts/validation/validate_rollback_compatibility.py) | [testing runbook](2026-10-12_ARCHITECTURE_REMEDIATION_TESTING.md) |

The legacy service/native router import paths remain compatibility interfaces. Do not create a parallel acquisition authority or delete shims solely because the canonical files moved.

## Acceptance and unresolved work

The [work log](2026-10-12_ARCHITECTURE_REMEDIATION_WORK_LOG.md) records commands actually run and separate old/new results. Use the [testing runbook](2026-10-12_ARCHITECTURE_REMEDIATION_TESTING.md) for a fresh run; test counts are not hardcoded acceptance criteria.

The final documentation-handoff run passed 975 full-suite tests, 779 fast-suite tests, fatal lint, both frontend suites, frozen hashes and isolated smoke. Rollback remains a disclosed failure for the 55 protected malformed JSON files; fresh-process persistence and actual baseline readers passed. No runtime code was changed during the documentation task.

| Priority | State | Safe next action |
|---|---|---|
| P1 | Historical archive has 55 malformed JSON files; 2,445 readable records are unsealed | Obtain trustworthy backup/recovery evidence and owner direction. Do not modify protected originals, invent content, delete failures or skip validation to make the gate green. |
| P1 before using privileged writes | `ADMIN_API_TOKEN` now guards both response-deployment aliases | Configure a server secret and verify valid/invalid credentials in an authorized environment; never embed it in frontend assets or documentation. |
| P2 | Some fixed-origin legacy social/resolver/provider-tool paths are outside the pinned transport | Inventory remaining paths and design a scoped migration with adversarial and compatibility tests before claiming universal SSRF coverage. Automatic unsafe browser rescue stays disabled. |
| P2 | Shared services, mutable singletons and process-local capability observations remain architectural debt | Preserve per-agent admission locks; consider request-scoped composition/cooperative cancellation and multi-worker health convergence in a separately scoped design. |
| P2 | Legacy refetch hashes have snippet/full-page comparison limitations | Design an explicit captured-content/comparison contract. Do not interpret trace checksums or heuristic refetch results as authenticity or full-page truth. |
| Follow-up diagnostic | One smoke worker timed out; successful retries did not reproduce it | If it recurs, capture bounded startup/shutdown stacks and stage progress. Keep network guards and timeout limits intact; cause is not established. |
| Owner-controlled validation | Remote CI, live scraping, production deployment, staging load and full deployed rollback remain unverified | Obtain scope/authority and record real execution evidence separately. Editing CI or passing offline mocks is not that evidence. |

Do not infer permission to commit, push, open a PR, perform live probes, change research labels, recover protected files or deploy from this document.

## Avoid reintroducing the original defects

- Do not use a cached DNS Boolean as connection authority; connect to freshly validated numeric addresses while retaining TLS identity.
- Do not restore automatic browser/legacy transport bypasses after policy, SSRF or rate failures merely to obtain more results.
- Do not equate original material with official authority, a guessed company hostname with identity, or unrelated citations with corroboration.
- Do not return a persisted dossier ID before exclusive publication succeeds, overwrite on collision, or retroactively seal old records.
- Do not treat nullable legacy unknown metrics as corruption or supply fabricated values; malformed traversed shapes still fail before playback/refetch.
- Do not flatten approved operations into search-only channels, interpret empty plans/platform lists as defaults, or drop Personal Watch redaction when routing is simplified.
- Do not use executor context-manager shutdown waits to defeat deadline returns or claim running threads were forcibly canceled.
- Do not change worker-thread handlers back to blocking event-loop code or remove admission protection while singleton state remains shared.
- Do not turn uncertain evidence into a false verdict, fake provider output, synthetic source attribution, fabricated groups or indefinite green health.
- Do not import application singletons before test storage/credentials are isolated or permit external provider CLIs to use locally stored credentials.

## Before the next handoff

Append a new dated record and update [the handoff index](README.md). Record scope, observed commit/worktree, actual code and tests, concise rationale/tradeoffs, commands/results including failures, protected-data checks, and unverified work. Preserve this snapshot rather than rewriting it as if future work had already passed.
