# Continuous source intelligence — 2026-10-17

## Scope and checkout

User requested repeated source → research → frontend implementation cycles,
starting with eight empty normal investigations, then all 52 executable
operations. Development branch only; no merge/deployment authorization.

Branch `feat/continuous-source-intelligence-20261017`, base
`1669b336ce509e5a789f7f83f2ff647702f9c82f`. Work is isolated in the remediation
worktree; the original workspace and other worktrees are untouched.

## First checkpoint: completed engineering, incomplete research acceptance

- Fixed legacy web fallback losing actual `url` fields and inventing `Recent`.
- Empty initial discovery no longer implies saturation; query-empty observations
  no longer suppress unrelated agents as if the provider were down. Genuine
  rate limits, failed transports and access gates remain enforced.
- Entity-only searches drop parenthesized ticker noise; case normalization
  fixes NVIDIA/Nvidia feed routing without rewriting literal factual claims.
- Added original publisher feed discovery (OpenAI/NVIDIA/Apple/Microsoft) and
  an Infosys issuer index route. Feed summaries are not linked article bodies.
- Preserve already-acquired native bodies rather than discarding/re-fetching
  them. Qualification and passage gates still apply.
- Added measured completed-stage timings. Timings are excluded from legacy
  semantic digests, with a separate contract test. Three zero-follow-up golden
  scenarios have a new reviewed hash overlay solely for corrected stopping
  telemetry. Historical manifests and frozen benchmark files are unchanged.
- Probe captures now retain public URL/ID/author/date fields; comparison script
  inventories saved responses without inventing accuracy or making requests.

Live baseline reproduced eight empty inputs. Cycle 1 rechecked three Scout
inputs; cycle 2 and cycle 3 each ran all twelve real page-button/backend/SSE
investigations with 390/1440px captures. NVIDIA cycle 3 acquired five dated
original publisher articles and one attributed, unverified quotation, versus
zero previously. Tata's new 444-word record is a mixed corporate homepage,
**not accepted financial evidence**. Infosys, Apple/Scout, OpenAI, EV and Nike
remain empty in cycle 3. Personal Watch still has profile metadata only.

All 52 operations were probed once at stable source; 16 protected operations
returned sampled observations, eleven operations returned none, overall PARTIAL
(a partial acquisition gate, not a crash). A display-only replay of 67 native samples passed
12 Chromium states across four pages and three widths. That scaffold is not
proof those sources are selected by normal investigations.

Commands actually run at this checkpoint:

| Command | Result |
| --- | --- |
| `pytest tests/ -q` | exit 0; 1,318 passed, 74.41s |
| `pytest tests/unit tests/chaos tests/security -q` | exit 0; 1,110 passed, 36.25s |
| Focused retrieval/golden/capability/progress tests | exit 0; 46 passed |
| Fatal Flake8 / all eight Node frontend contracts | exit 0; passed |
| Release smoke / rollback compatibility | exit 0; isolated OFFLINE_SMOKE_PASS / OFFLINE_PERSISTENCE_PASS |
| Frozen validator / protected-tree diff / diff whitespace | exit 0; unchanged |
| Three full native browser matrices | exit 0; rendering checks only, not research acceptance |

Initial full test run failed 12 result hashes after adding nondeterministic
timing diagnostics. Excluding only that diagnostic exposed three stopping-state
changes. Comparing old/new payloads showed changes only in saturation/halt
telemetry and its decision log; acquired bytes/IDs/query outcomes were stable.
Do not hide substantive evidence changes by regenerating historical manifests.

Public samples/logs/dossiers/screenshots are in a fresh system-temp tree prefixed
`aegis-intelligence-loop-`. Secrets were not printed/edited. Normal runtime uses
the operator's existing local Reddit flag; that is not independent authorization.
Remote persistence/notifications/background ingestion were disabled for audits.
OpenAI article bodies returned HTTP 403; no restriction bypass was attempted.

## Next cycle, already diagnosed

1. Infosys index fetched successfully, but page-detail extraction selected an
   unrelated first `<article>` and exported zero links, while readable extraction
   correctly selected `<main>`. Use one semantic-root selector for both.
2. The generic entity resolver mistakes ticker tokens in `Infosys (INFY.NS)`
   for name tokens, rejecting the relevant issuer page. Fix structured aliases,
   not the entity confidence threshold; add unseen issuer controls.
3. Trending's native adapter truncates actual acquired bodies at 1,000 chars and
   drops raw capture/page/provenance metadata. Preserve the bounded research
   record and verify exact citation passage visibility after normalization.
4. Repeat live normal matrix and inspect substantive source content, not counts.
   Finish source-family scorecards, exact-code hosted CI and durable evidence.

No agent/research-quality completion, production acceptance, merge or deployment
is claimed. Subsequent updates below must distinguish later code and validation.

## Subsequent implemented cycles

The diagnosed semantic-root mismatch and structured financial aliases were
fixed. Text and linked-document observations now share one root. The Trending
native adapter retains up to 12,000 captured characters and original bounded
raw/page metadata instead of silently cutting bodies at 1,000 characters.

Later real runs exposed keyword-heavy legal disclosures winning passage
selection and distinct propositions inheriting one discovery query's citations.
Both defects have failing-before/fixed-after development controls. Disclosures
remain in raw/captured text; selected excerpts retain exact offsets and up to
2,000 characters rather than silently cutting qualifiers at 450. Distinct
captured propositions are separate UNVERIFIED observations, not corroboration.
Four reviewed development goldens now have two separately cited observations;
their old manifests, candidate bytes/IDs and query outcomes remain preserved.

Publisher feeds now include a specialist EV reporting endpoint, with explicit
topic aliases (not a lower entity threshold), and official Apple/Tata issuer
indexes. A fetched issuer index may contribute bounded observed child links;
one second-hop HTML read spends an existing remaining read slot. Maximum depth
is two, links remain same-origin and go through qualification/SSRF controls,
PDF leads remain visible but unread, and publisher grouping is recomputed.
Indexes/careers pages no longer become primary documents merely through issuer
ownership. Authentic-statement and identity-abuse queries are separate.

Missing dates no longer become `Recent` in Reddit RSS, Bilibili, LinkedIn,
Xueqiu or Meta embedding normalization. HTML entities decode to readable text.
An omitted ResearchRequest timeout now inherits configured engine bounds
(local default 25s/server 20s), rather than silently replacing them with 15s.
Adaptive calls enforce their remaining discovery deadline; late provider
results cannot mutate the returned investigation corpus. A second-hop HTML
selector looks past unread PDFs before applying its link-count bound.

Final implementation regression checkpoint: `pytest tests/ -q` exit 0,
**1,329 passed (79.03s)**; fast unit/chaos/security exit 0, **1,121 passed
(42.33s)**. Targeted retrieval/golden/stage controls: 45 passed. The final
52-operation probe completed at an unchanged source fingerprint, 78 observations,
11 operations without observations; all 16 protected operations sampled.
Live normal-matrix and publication evidence is recorded in the final review.

Intermediate audit limitations are retained: one all-source run invalidated its
fingerprint after an audit-script edit; another stopped before probing because
Windows decoded a Unicode Git diff as CP1252. The runner now explicitly reads
Git output as UTF-8; fresh stable passes succeeded. Initial test failures also
include a test-double method-name typo, then genuine red controls for passage,
mixed citations, dates, topic aliases, inherited timeout and adaptive deadline.
No unsuccessful run is silently substituted as acceptance.

The latest twelve normal investigations still cannot establish research
completion: financial statement PDFs/metric-period binding remain incomplete,
several brand/identity flows lack relevant bodies, OpenAI body reads return 403,
and live Gemini attempts report HTTP 429 plus a fallback model HTTP 404.
Configured credentials are not successful live synthesis. Do not bypass these
limits, promote profiles/feed summaries, or treat offline/CI success as launch
authorization.
