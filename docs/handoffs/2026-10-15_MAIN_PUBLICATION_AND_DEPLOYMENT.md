# Main publication and deployment checkpoint — 2026-10-15

## Scope and release decision

User explicitly requested “Push to main to deployment”. This supersedes the
earlier absence of merge/deployment authorization; it does not turn partial
research acceptance into a production-readiness PASS. Reddit, SEC and FactCheck
remain blocked/configuration-required. No credentials, approval flags, paid
plans, frozen datasets or historical dossiers were changed.

This is a reconstructed command/result record, not a raw transcript.

## Git preservation

- Observed remote main before publication: `83cbb814117e82b4c83303009593772a94490ef9`.
- Acquisition work began on `feat/phase8-independent-audit-codex` at
  `abe547f1e17aab5b54e90ff55e2d4783afa95283`. Main already had the same tree.
- Implementation and append-only proof committed as
  `14a8fc9dd02b778b935e0a161249d3a999d3ce00`.
- An isolated `release/phase9-acquisition-20261015` worktree was created from
  remote main. A normal merge produced
  `cba5cb60332e419edb54bc96e2cc08f51b09857c`, pushed with
  `git push origin HEAD:main` (exit 0). No force push or history rewrite.
- The other agent's `feat/phase9-intelligence-accuracy` branch at `7054575`
  was not merged or edited. The original IDE worktree was left untouched.
- Reviewed common secret-token patterns produced no matches in changed/new
  text. This is not a comprehensive privacy certification.
- Source/documentation diff whitespace checks passed. The complete checkpoint
  diff check reported nine trailing-space warnings in newly preserved generated
  Markdown reports. Those original observations were retained, not rewritten.
- See the [implementation handoff](2026-10-15_PHASE9_ACQUISITION_DEPTH.md) for
  changed-code/test pointers, rationale, evidence and remaining Phase 9 work.
  Its uncommitted/unpushed statements describe the earlier snapshot, not this
  publication.

## Validation actually performed

All commands below ran in the clean merged release candidate, before publication.

| Command/check | Exit/result |
|---|---|
| `python -m pytest tests/ -q` | 0; 1,207 passed in 75.06s |
| `python -m pytest tests/unit tests/chaos tests/security -q` | 0; 999 passed in 52.22s |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | 0; zero fatal errors |
| Each of the seven `node tests/frontend/test_*.js` scripts | All exit 0 |
| `python scripts/validation/verify_frozen_benchmarks.py` | 0; content hashes verified |
| `python scripts/validate_release_candidate_smoke.py` | 0; `OFFLINE_SMOKE_PASS` |
| `python scripts/validate_rollback_compatibility.py` | 0; `OFFLINE_PERSISTENCE_PASS` |
| Protected tracked-output diff after tests | 0; no modifications |

Offline smoke disables acquisition and uses explicit test mocks. Historical
archive inspection was NOT_VERIFIED because the isolated worktree lacks the
original archive. Deployed previous-version rollback was NOT_VERIFIED. The
previous inventory of 55 malformed historical dossiers is not resolved.

[Hosted CI run 38759820665](https://github.com/Shaunakrane914/Misinformation/actions/runs/38759820665)
completed successfully for exact merge `cba5cb6`: all five jobs green. Hosted
logs show 1,207 full-suite tests passed in 24.83s and 999 fast-suite tests each
on Python 3.11 (18.03s), 3.12 (16.63s) and 3.13 (12.61s). Smoke, persistence,
frontend contracts, fatal lint and tracked-output integrity checks passed.
This run does not certify future commits or live-provider accuracy.

## Frontend production deployment: VERIFIED for static publication

The existing Cloudflare Pages project is `aegis-protocol`, with production
domain [aegis-protocol-110.pages.dev](https://aegis-protocol-110.pages.dev).
It is a direct-upload project, not Git-connected. After the exact code commit
passed hosted CI, the existing authenticated Wrangler CLI was used:

```text
wrangler pages deploy frontend --project-name aegis-protocol --branch main --commit-hash cba5cb60332e419edb54bc96e2cc08f51b09857c --commit-message "Phase 9 bounded acquisition and evidence inspection" --commit-dirty=false
```

Exit 0; 27 assets uploaded, six already present, headers/redirects uploaded.
Production deployment ID `249a5425-a0cc-4f3a-a5b6-95df891863be` references
`main` / `cba5cb6`. Immutable URL:
[249a5425.aegis-protocol-110.pages.dev](https://249a5425.aegis-protocol-110.pages.dev).

Public GET checks returned HTTP 200 and exact SHA-256 byte matches against the
uploaded checkout for `/`, all four agent HTML pages,
`/unified-report-renderer.js` and `/aegis-theme.css`. This establishes static
publication, not browser-rendered, screen-reader or end-to-end research acceptance.
Initial requests without the later verification user agent returned 403; retries
succeeded. No access-control settings were weakened.

## Backend deployment: BLOCKED on expired Render login

The configured backend is `https://misinformation-1ouh.onrender.com`.
Read-only health and OpenAPI GETs returned 200 after initial cold-start timeouts.
The public OpenAPI document **did not contain `/api/agent-reach/extract`**:
health is not proof that this release is deployed. The new frontend source-read
action may therefore report unavailable until the backend is updated; it does
not fabricate a result or alter the original verdict.

No Render API key or deploy-hook setting was found in the relevant environment
configuration. An existing Render CLI v2.28.0 was found; `render whoami
--output json` failed with “your token is expired; run render login to get a
new one”. No credential file contents were printed and no new login, service,
deployment, account changes or secret updates were attempted.

Owner action: authenticate securely with `render login` (or configure an
existing approved server-side deployment credential). Then identify the
service whose URL matches the configured backend, inspect its current deploy,
and deploy an intended CI-green main commit, without clearing caches or
changing service settings by default:

```text
render services --output json
render deploys create <verified-service-id> --commit <verified-main-sha> --wait --confirm --output json
```

These two commands are a **continuation plan, not executed deployment proof**.
Verify service identity before substituting an ID. Confirm health, readiness,
the extraction route in OpenAPI, allowed frontend origin and unauthorized
privileged-request rejection. Do not send live research POSTs or alter stored
dossiers merely to prove deployment. Keep source approval gates unchanged.

The pre-release Git checkpoint is `83cbb81`; Pages deployment history retains
the prior production `bd1db21d-e067-4cd3-b6aa-aa5ae97493f7` (`a17976b`). Those
are rollback references, not proof that a rollback was performed. There were
no schema/data migrations in this publication. Research accuracy, full source
coverage, historical recovery and deployed rollback remain separate open gates.
