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
