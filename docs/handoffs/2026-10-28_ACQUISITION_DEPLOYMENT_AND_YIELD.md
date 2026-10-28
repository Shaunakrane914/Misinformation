# Acquisition deployment and four-agent yield — 2026-10-28

User scope: deploy the latest acquisition repairs and measure real production
source text and displayed evidence for all four agents. Production publication
and bounded investigations are authorized; provider/access restrictions remain.

## Candidate and preservation

The deployment candidate is isolated on `release/acquisition-20261028`, based on
`7ad13a59f86a78802e45685ecfd1fd4999a2e5ce`, with the existing release worktree's
152 changed/new source, test, documentation and evidence files copied byte-for-byte.
The original root and release worktrees are preserved. No historical dossier,
frozen dataset, research or artifact tree is removed or rewritten.

The separately pushed root branch `222a4ad` diverges from main by 101 main-only
and 16 branch-only commits. Replacing main with that tree would remove newer
application features and protected historical evidence. Its useful direct-feed
locator improvement is integrated into the current release instead. Bing-first
news discovery, bounded wrapper resolution and extended body reads already exist
in this release. Strict freshness and source qualification remain; undated or
future pages are not relabeled as current evidence to fill a page minimum.

Additional release-boundary corrections:

- `DeepReader.deep_read` preserves parser-confirmed feed/sitemap scope, allowing
  observed feed summaries to select article reads while remaining discovery-only.
- `NativeNormalizer.normalize_rss_entries` decodes observed Bing/Yahoo publisher
  locators only for recognized wrapper hosts; preserves the original locator.
- New regressions exercise parsed RSS → DeepReader → harvesting continuation,
  plus wrapper-host spoofing and invalid-target controls.

This includes the preceding release fixes to controlled-source raw-pool scalar
metadata merging, compressed/native text acquisition, exact article extraction,
feed-summary read selection and honest BrandShield pipeline-failure reporting.

## Checks actually run before candidate publication

- Targeted affected tests: **130 passed**, exit 0. An initial new test used an
  incorrect telemetry key; corrected to the existing `successful` field, then
  rerun successfully. No production call was used for that test correction.
- Fatal flake8: exit 0, zero fatal findings.
- Frozen benchmark content verifier: exit 0.
- Isolated release smoke: exit 0, `OFFLINE_SMOKE_PASS`.
- Isolated persistence/rollback reader: exit 0, `OFFLINE_PERSISTENCE_PASS`.
  Original historical archive and deployed rollback remain **NOT_VERIFIED**;
  an isolated empty archive does not recover the historical 55 malformed files.
- Candidate scan against configured secret values: no matches in 154 candidate
  files at scan time; no credentials are added. Largest file: 818,167 bytes.
- Full/fast suites and frontend checks will run through hosted CI on the exact
  candidate. Their results are pending here, not assumed from older checkpoints.

## Deployment and measurement status

Pending at this initial handoff. Previous immutable recovery references:
Render `dep-dbe3r12jnfac73c1nc3g`, commit `443652e`; Cloudflare production
`6a2923aa-9c4f-4fb6-b6bf-44e1e0cc486c`, same commit.

Promotion requires exact-candidate hosted CI, normal fast-forward main update,
matching Render commit, public health/CORS, and frontend Git-byte attestation.
Keep optional AI within the shared advisory policy; no AI text becomes evidence.
Run four sequential normal DEEP investigations with native profile caps, then
inspect exact source records/passages and render those saved results in the
deployed frontend without repeating provider requests. Article-body words,
qualified-source words and unique published passage words must remain separate.

Success requires observed useful source text, not HTTP 200 or raw word volume.
Independent factual accuracy, source independence and measured virality are not
established by this bounded deployment pilot. Results and actual publication
identifiers will be appended after observation.
