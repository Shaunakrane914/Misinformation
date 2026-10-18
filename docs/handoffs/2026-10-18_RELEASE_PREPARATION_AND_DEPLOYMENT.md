# Release preparation and deployment — 2026-10-18

## Authority and status

User requested required fixes/verification and explicitly replied **“push to
deployment.”** Production publication is authorized for this bounded release;
independent accuracy and historical archive recovery are not represented as
complete. At this commit: local validation complete, hosted CI/deployment pending.
Append actual publication outcomes below; do not replace prior dated evidence.

Worktree `.scratch/phase9-remediation-20261016`, branch
`feat/continuous-source-intelligence-20261017`, base `314bf17697f1424bf9aa0d60704b42d87bf8e244`.
Fetched `origin/main` is `ff6d246bfe1e9cfd0f21d8e32135582e631636f1`
and is an ancestor of the candidate; no history rewrite or unrelated-main
replacement is needed. Existing staged/unstaged Netlify/model changes and the
[research-quality checkpoint](2026-10-18_RESEARCH_QUALITY_COMPLETION.md) were
reviewed and preserved for publication. The outer checkout was not reset.

## Changes and reasons

- Reader markdown: select only a unique explicit heading matching its observed
  reader title **before** applying display bounds. Preserve raw reader text and
  hashes, qualifications and corrections. Duplicate/no matching headings keep
  an explicitly unscoped body. No sentence rewriting or keyword-based truth.
  Both native reader fallback and Jina facade use the same extraction helper.
  [Implementation](../../backend/infrastructure/acquisition/adapters/web/page_extraction.py),
  [tests](../../tests/unit/test_reader_markdown_selection.py).
- BrandShield: deduplicate reported enforcement across legacy keyword engines,
  keep the reporting URL distinct from an attacker, and classify it as an
  informational, unverified report rather than a current counterfeit/safety
  incident. Legacy source and evidence IDs remain inspectable.
  [Regression](../../tests/unit/test_release_specialist_semantics.py).
- Cloudflare: removed an unsupported external-domain `200` proxy rule. Home
  telemetry and ledger inspection/replay now use the existing direct Render
  resolver. Missing/empty ledger responses do not substitute a sample successful
  dossier. HTTP failures are visible and source IDs are URL-encoded.
  [Frontend contracts](../../tests/frontend/test_cloudflare_api_routing.js).
- Render: [configuration utility](../../scripts/operations/configure_render_release.py)
  previews by default and requires `--apply` for mutations. It verifies repo,
  branch, service URL and suspension state; individual non-secret updates never
  replace the full secret-bearing environment or trigger deployment. API
  redirects are refused, transport bounded, errors redacted, reports exclusive.
  [Tests](../../tests/unit/test_render_release_configuration.py).
  Blueprint now declares production/mock/ingestion/origin/light-model settings.

Cloudflare's [official redirect contract](https://developers.cloudflare.com/pages/configuration/redirects/)
does not permit external-domain proxying. Render's
[single-variable API](https://api-docs.render.com/reference/update-env-var)
avoids the [bulk replacement endpoint](https://api-docs.render.com/reference/update-env-vars-for-service),
which removes omitted credentials. The operation utility deliberately cannot
alter provider secrets, generate an admin credential, trigger a model request,
or deploy a commit.

## Actual source observations (not held-out acceptance)

One normal local guided Nike investigation returned three storefront records,
no findings, and failed/timed-out selected reads. That failure is preserved;
it is not declared a successful positive-threat discovery.

One additional bounded reader request to the observed public DOJ article
returned 16,747 raw characters. Heading selection begins at offset 8,888;
the selected body contains **702 words / 7,858 characters**. A 4,000-character
projection now retains **426 words** from the article, rather than navigation.
It contains the observed brand and enforcement text. Offline interpretation
with acquisition blocked demonstrated the reporter/actor distinction; a new
regression prevents duplicate current-threat counts. This is a guided reader
capture plus saved interpretation, **not** proof of normal discovery or a
new verified current threat. The source's 2024 publication date stays explicit.

Fresh source JSON and command logs are in a new system-temp directory prefixed
`aegis-release-preparation-`; no tracked benchmark/artifact/historical dossier
was overwritten. Zero live AI generation or model-list calls were made during
release preparation. AI remains an optional guarded suggestion layer; disabling
generation in tests does not remove it or set a production-wide off flag.

## Actual validation before publication

| Command | Outcome |
| --- | --- |
| `python -m pytest tests/ -q` | 1,431 passed, exit 0, 158.89s |
| `python -m pytest tests/unit tests/chaos tests/security -q` | 1,223 passed, exit 0, 108.57s |
| Fatal `flake8 backend tests scripts` selections | 0 errors, exit 0 |
| All Node `tests/frontend/test_*.js` | Nine discovered scripts passed |
| Release smoke | `OFFLINE_SMOKE_PASS`, exit 0 |
| Isolated rollback validator | `OFFLINE_PERSISTENCE_PASS`, exit 0; not a deployed rollback |
| Frozen benchmark hashes and protected-path diff | Hashes verified, no protected tracked changes |
| Render configuration preview | Eight non-secret variables and health path drift; no writes in preview |
| Public Render health, before deployment | `/api/healthz` 200; wildcard CORS, not proof of production configuration |
| Public Cloudflare `/api/healthz`, before deployment | 404, consistent with absence of external proxy support |

Live Render API observation before publication: service
`srv-d716v3dactks738os7d0`, repo `Shaunakrane914/Misinformation`, branch `main`,
auto-deploy enabled, free plan, not suspended, active code commit
`8c8ecf2b0074f658916a11688b21bdaad3544cd3`. Root `main:app` forwards to
`backend.main:app`; it is not a broken import. Existing health path was blank.
Service-level production/origin/model settings were absent; linked environment
groups are not inventoried by the API. Provider secrets were present but never
printed. Missing `ADMIN_API_TOKEN` keeps privileged writes disabled.

Cloudflare project inventory: `aegis-protocol`, production domain
`aegis-protocol-110.pages.dev`, direct uploads rather than Git integration.
Use an archive of the exact verified Git commit for upload, not a mixed dirty
workspace. Cached Wrangler 4.151.0 is available; unpinned `npx --no-install`
requested an unavailable newer package and was not used to install anything.

## Publication and recovery procedure

1. Review complete diff/untracked files and secret scan; commit and push the
   development candidate. Require the actual five hosted jobs at that commit.
2. Save a new non-secret Render preview. Apply only the reviewed environment
   keys/health path, preserving all provider keys. Re-preview for no drift.
3. Re-fetch main and prove ancestry again. Use a normal fast-forward push only;
   stop on divergence/conflict rather than force-pushing.
4. Observe Render's actual deployed commit/status; build success alone is not
   endpoint health. Upload an exact-commit frontend archive to the existing
   Cloudflare project and verify deployed asset bytes plus direct backend routing.
5. Check health/CORS, access guards, and bounded public research/stream behavior.
   Do not test privileged writes with real side effects, enable mocks, change
   approved-access gates, or generate a missing admin token as a workaround.
6. On a critical release failure, stop new publication, retain failed logs and
   prefer the previously observed good code/artifact without deleting data.
   Redeploy/rollback must be an owner-controlled operation, not a claim that
   offline reader compatibility proved production rollback. The previous
   Render deploy and prior Cloudflare deployment remain available for review.

## Still outside acceptance

The independent reviewer packet remains unfilled. Normal Tim/Fei discovery,
real BrandShield positive incident acquisition, financial claim/table
adjudication, genuine temporal trend measurement, screen-reader/contrast checks,
durable free-plan filesystem storage and actual staging rollback remain
unverified or partial. Original historical inventory remains 55 malformed JSON
files plus 2,445 legacy-unsealed files, unrecovered and protected. Do not export
them into a deployment or claim new persistence tests repaired them.

## Publication outcomes

Pending at initial candidate commit. Append exact Git/CI/deployment observations
and any failed checks after execution; no remote result is predeclared here.

### Observed closeout — 2026-10-18

**Deployment integration: bounded PASS. Research-quality acceptance: NOT COMPLETE.**

Application commit `725f4e251e3cb4cfbd97be90cf39c27811be556b` was pushed to the
development branch, then fast-forwarded to `main` after its five hosted jobs
passed. No force push or history rewrite. Both exact-commit runs completed:

- [Development CI](https://github.com/Shaunakrane914/Misinformation/actions/runs/39126422858): all five jobs successful.
- [Main CI](https://github.com/Shaunakrane914/Misinformation/actions/runs/39126603576): all five jobs successful.

The first staging command failed because its path list included an already
staged deletion; a PowerShell command chain continued and committed the older
index as `c3d574d`. That incomplete development snapshot was not the accepted
candidate. Strict exit-code checks then committed the complete reviewed tree
as `725f4e2`. The first development run was canceled, not counted as passing.
Main was advanced only after the complete candidate's CI succeeded. Future
Git command chains must stop explicitly on every nonzero `$LASTEXITCODE`.

Render deploy `dep-dbabh79srm7s73a93jl0` reached **live** at application commit
`725f4e2`. Service `srv-d716v3dactks738os7d0` serves
<https://misinformation-1ouh.onrender.com>. Applied the eight non-secret values
declared by the configuration utility and `/api/healthz` health path, preserving
provider credentials. Re-preview found no drift. No admin credential was
created; an unauthenticated empty-body `/api/deploy-response` probe returned 503,
not a successful mutation. Live health returned 200; the production Cloudflare
origin received its exact CORS allow-origin, while an untrusted origin received
no allow-origin header. An earlier rollout-time health timeout is not a pass.

After the user refreshed Wrangler OAuth, Cloudflare production publication
succeeded at <https://aegis-protocol-110.pages.dev>. Final artifact deployment:
<https://cff4d2f6.aegis-protocol-110.pages.dev>, source application commit
`725f4e2`. This is direct upload, not an automatic Git-integrated frontend.

The first exact-commit upload (`7ab25e2e`) used a Windows archive with CRLF
conversion. The verifier correctly stopped before research: all nine checked
assets differed from raw Git blob bytes, though normalized text matched. A
preceding availability check also failed before research. Repackaged with
`git -c core.autocrlf=false archive`; the final nine deployed assets match the
Git blobs byte-for-byte. Always disable archive conversion explicitly:

```text
git -c core.autocrlf=false archive --format=zip --output=<new-zip> 725f4e251e3cb4cfbd97be90cf39c27811be556b frontend
```

Extract into a fresh directory and deploy that directory's `frontend/`, not the
dirty worktree. Cached Wrangler 4.151.0 was used. Cloudflare `/api/healthz` is
still 404 by design: frontend code calls Render directly, not an unsupported
external rewrite. Preview-domain CORS was not authorized or accepted.

### Actual deployed browser observations

[Measurements and selected screenshots](../testing/evidence/2026-10-18_deployed_release/README.md)
are from real Cloudflare page buttons and Render SSE, with no transport stubs,
saved-response replay or API-base override. One sequential investigation per
agent, then the same completed response at 390 and 1440px. All four returned
HTTP 200, one result and 29 progress events, no SSE error events, matching
findings/evidence/discovery counts, visible shared reports, no detected document
overflow or uncaught page exceptions. **These are transport/rendering checks,
not correctness or full visual/accessibility acceptance.**

| Agent / input | Seconds | Retained records | Retained words | Discovery-only records |
| --- | ---: | ---: | ---: | ---: |
| Scout / MSFT | 51.03 | 5 | 5,272 | 22 |
| Trending / NVIDIA | 32.96 | 0 | 0 | 5 |
| BrandShield / Nike | 21.07 | 0 | 0 | 22 |
| Personal Watch / Satya Nadella | 19.53 | 0 | 0 | 3 |

Records/words are retained native text, not verified relevant propositions,
independent corroboration or an exhaustive source inventory. Nike reports six
failed/timed-out selected reads; Satya reports two. Zero-source reports remain
visible with honest acquisition limitations rather than invented findings.

Visual inspection of one actual viewport capture per agent found two additional
quality defects that this transport status does **not** waive:

1. Scout presents several distinct Microsoft headlines under “Contradictory
   evidence” without establishing an incompatible proposition. Do not accept
   those labels as a contradiction assessment. Follow the native contradiction
   records through shared-report normalization and require passage-level
   incompatibility, not merely different story headings.
2. Personal Watch displays a stringified baseline-change dictionary and a
   specialized “LOW” doxxing label despite zero acquired bodies. The summary
   correctly says exposure cannot be determined, but those legacy projections
   need human-readable change text and an unassessed/insufficient-evidence state.

No new application edit or additional provider investigation was made after
these observations. Preserve the saved responses for offline regression work;
do not call this a completed research-quality milestone. Screen-reader, measured
contrast, other browsers, full-page visual review, sustained health, source
inspection interactions and actual deployed rollback remain unverified.

### Reproduction and closeout scope

[Deployment diagnostic](../../scripts/diagnostics/verify_deployed_candidate.py)
first attests the Render live commit and nine frontend blobs. Default execution
makes **no research request**. `--allow-live-research` explicitly performs four
normal public investigations and creates new production dossiers; do not add
it to ordinary CI or repeat scans merely to reproduce a screenshot.

```text
python scripts/diagnostics/verify_deployed_candidate.py --env-file <existing-server-env> --expected-commit 725f4e251e3cb4cfbd97be90cf39c27811be556b --output-dir <fresh-temp-directory>
```

The final live invocation added `--allow-live-research` and exited 0 with
`BOUNDED_LIVE_BROWSER_TRANSPORT_PASS`. Raw responses/events and full command logs
remain in the fresh `aegis-release-preparation-*` system-temp tree; only selected
public measurements/screenshots are durable. This is a reconstructed command
and outcome ledger, not a verbatim terminal transcript or private reasoning log.

Zero live Gemini generation/model-list calls were requested in this task; the
four browser probes did not request advisory generation. Independent provider
usage/accounting is **NOT OBSERVED**, not a verified account-level zero.

The closeout adds only this diagnostic and documentation/evidence, not backend
or frontend code. Its publication uses `[skip render]` to avoid rebuilding the
already verified application ([Render skip contract](https://render.com/docs/deploys#skipping-an-auto-deploy)).
Thus a later main documentation SHA may differ from the live application SHA;
attest `725f4e2` until an intentional application release replaces it. No second
frontend upload is needed for documentation-only publication. Closeout CI is
separate from the two successful application runs above.

Closeout verification actually reran fatal Python lint (zero errors), all nine
Node frontend scripts, frozen hashes, protected tracked-path comparison,
`git diff --check`, diagnostic `--help`, evidence JSON parsing and relative-link
resolution: all completed with exit 0. A limited credential-pattern scan found
no matches; that is not a comprehensive secret audit. Backend/frontend/config
diff against `725f4e2` is empty. The full/fast suites above were not repeated
solely for these documentation/diagnostic additions; the new opt-in diagnostic
was exercised by the actual deployed four-case run.

Next owner priorities: repair the two observed projection defects offline;
diagnose saved failed-read outcomes without weakening relevance/access gates;
complete independent reviewer labels; establish durable storage and an actual
rollback exercise. The 55 corrupt historical dossiers remain untouched, and
production-launch readiness is not asserted.
