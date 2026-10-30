# GOV.UK original speech reuse - 2026-10-31

**Two new speeches acquired: 5,500 raw speech words, 4,850 exact cited words
through Personal Watch/API/SSE and the local frontend.** Speaker and issuing
organisation are separate; original delivery/publication dates remain distinct.
[Actual URLs, dates, metadata and citation checks](../testing/evidence/2026-10-30_govuk_speech/results.json).

Current-main base `51a12e2` (application parent `5ffb6ac`), isolated continuation
branch `fix/govuk-speech-20261030`; older dirty worktrees preserved. Existing saved
GOV.UK bytes were guidance search results, not speech bodies. User explicitly
approved four admissions/120s: one speech-only search, one robots GET and two
Content API reads. All returned HTTP 200, four admissions total, no retries,
redirects, alternate reader, AI or paid service. Live activity is closed.

| Speaker / issuer | Delivered / first published (UTC) | Raw words | Main replay -> repaired cited/frontend words |
| --- | --- | ---: | ---: |
| Amanda Spielman / Ofsted | 2018-02-01 00:00 /11:25 | 2,477 | 0 ->2,462 |
| Emma Howard Boyd / Environment Agency | 2019-10-31 18:00 /18:38:50 | 3,023 | 0 ->2,388 |

Both actual APIs use `links.speaker`. The no-profile optional field has synthetic
coverage only. API `base_path` must match the observed public URL. Existing GOV.UK
speech URLs now use the existing Content API adapter. Issuer/publisher are not
personal authors. Hash-bound speech scope, issuer and dates survive pool and
Personal normalization; public passage projection retains separate visible
speaker/delivery/publication labels. Missing/conflicting speaker never becomes
an issuing-department attribution; identity remains unauthenticated.

Short adjacent original speech fragments share exact contiguous citation spans;
headings, separators and third-party quotations stop grouping. Existing 80-passage,
20,000-character/source, reader/HTTP/byte/access limits are unchanged. Real list
items no longer fail merely for lacking final punctuation. Greetings and other
people's quotations remain in the raw body but are excluded from speaker output.
No display-budget omissions remain. Wrong-speaker control retains Amanda's body
but produces zero Emma statements/cited words.

Before/after is identical captured-body processing through read-only exported
main and repaired code, not two live experiments. Same IDs/URLs/titles/publication
dates/body hashes/text; all exact offsets and 4,850 frontend words verified in one
local renderer session with no external requests. Historical speeches are not
recent statements or independently authenticated recordings.

Focused GOV.UK/Duke/rights controls: **33 passed /0.67s**, exit0; modified-file
fatal lint, whitespace and protected-path checks pass. Full/fast suites, hosted
CI, deployment and unrelated crawls NOT RUN. Legacy unsupported Inspect task
cards are excluded from evidence counts; broader claim/UI cleanup is separate.
Publication pending at authoring; skip CI/Render markers used for requested Git
publication. Private originals: temp basename
`aegis-govuk-speech-20261030-3d266ca0c01d4ca280080f81988059e6`; may expire.

Permitted source API bytes/pools are also preserved outside Git under the
original repository `.scratch/acquisition-captures/2026-10-30_govuk_speech/`
with a hash manifest, so future offline reuse does not depend on temp retention.

The migrated GOV.UK boundary opts into preserving original typed HTTP errors:
401/403/429 remain terminal, one attempt and zero redirects. Other adapters keep
their existing exception contract. Focused denial controls pass.

## Observed Git publication

Application `6971bc447efe6c04cc98ebee9a7dfdcc95584c20` fast-forwarded main and was pushed;
GitHub main ref confirmed the exact SHA. No force push/history rewrite.
CI/deployment skip markers retained; no deployment, production investigation or
hosted CI result is claimed. This small documentation closeout is pushed next.
