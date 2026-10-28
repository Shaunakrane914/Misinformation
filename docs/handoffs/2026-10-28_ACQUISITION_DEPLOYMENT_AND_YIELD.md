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

## Initial publication actually observed

Application `24bf73d069329fba63c84fb061e8a42fc7472c23` passed all five hosted
jobs ([run 40623394658](https://github.com/Shaunakrane914/Misinformation/actions/runs/40623394658)):
full 2,800; fast Python 3.12 2,592; other fast matrices, frontend and validators
also passed. Main promotion was a normal fast-forward, with matching main CI.
Render `dep-dbgm81cs728c7390kop0` became live at `2026-10-28T02:57:41Z`.
Cloudflare `2c4a7fbe` uploaded the matching frontend; nine assets matched Git
bytes. Public health returned 200 with the expected frontend CORS origin.

Four real production DEEP investigations completed, once each, without SSE
error events or audit retries:

| Agent / input | Seconds | Article bodies / raw article words | Qualified sources / retained body words | Published passage words |
| --- | ---: | ---: | ---: | ---: |
| Scout / Adobe | 72.44 | 7 / 7,933 | 2 / 1,923 | 603 |
| BrandShield / Dyson | 55.07 | 8 / 12,300 | 3 / 3,081 | 353 |
| Trending / battery recycling | 86.79 | 6 / 6,489 | 0 / 0 | 0 |
| Personal Watch / Mary Barra | 75.26 | 2 / 1,855 | 0 / 0 | 0 |

[Selected production measurements](../testing/evidence/2026-10-28_deployment_yield/initial-four-agent-measurements.json).
These are acquisition/publication observations, not independent fact verification.
Scout's two sources share one publisher. BrandShield's three reports date to
2020–2022. Trending lost five articles to explicit rights-exception review and
one to stale publication. Personal's two captured articles are 2014 executive
speculation, with no usable subject statement/identity passage. All four hit the
effective shared 14-read budget even though the selected profile is DEEP; this
lower runtime budget was preserved, not silently expanded beyond its configured
cap. Native HTTP admissions were 58/66/79/87 respectively, each under 120.

The local measurement formatter initially treated a query-record count as a
list, after saving intact native results and events. Read-only remeasurement
uses actual corpus query rows; no production investigation was repeated to
correct that instrumentation error. Raw native results remain in temporary
storage, rather than tracked as publisher-body republication.

AI runtime/search flags were enabled and the cap set to three/day without any
credential changes. **No generation succeeded or was observed:** the two weak
cases report `AdvisoryPolicyError`. Read-only configuration confirms the required
production `AEGIS_AI_POLICY_DB` is absent. Its persistent-ledger guard remains
intact; an ephemeral file was not substituted to claim durable quota enforcement.
Durable policy storage is a remaining owner/runtime requirement.

## User correction: historical information must remain visible

The user explicitly reaffirmed that fresh-source failure must not erase useful
older information. Added a separate `historical_background` projection and
frontend **Older background reading** section. It uses actual dated, permitted,
relevant article passages, preserves source identities and raw bytes, and does
not change current findings, qualified-source counts or velocity. Unknown/future
dates, discovery-only indexes, off-topic bodies and rights-blocked sources cannot
fill it. A detached projection passes normal semantic/passage checks; the
original current-evidence rejection remains untouched.

Saved genuine production captures yield one eligible Resource Recycling article
from May 27, 2026, with **179 background words**. This is **offline replay**, not
a post-fix live result. Focused historical/freshness/golden tests: **34 passed**;
frontend workbench/escape controls and fatal lint passed. Additional hosted CI,
publication and post-fix Trending proof are pending at this recording.

An initial browser replay harness used an incorrect health-stub status and
omitted CORS responses. After correction, Scout rendered at both widths, but
a host/network interruption produced `ERR_NETWORK_IO_SUSPENDED` and
`ERR_INTERNET_DISCONNECTED` for other pages. Those failures are retained and
are not application JavaScript exceptions or successful four-agent browser proof.
