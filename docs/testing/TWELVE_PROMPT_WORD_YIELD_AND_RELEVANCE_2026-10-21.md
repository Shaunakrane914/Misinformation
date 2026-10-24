# Twelve-prompt live word-yield and relevance check — 2026-10-21

Latest specialist-layer repair: [task discovery and segregation](SPECIALIST_TASK_DISCOVERY_AND_SEGREGATION_2026-10-24.md).
BrandShield/Personal planning and interpretation are corrected offline; no new
live word-yield measurement is claimed. The original twelve-case results remain
unchanged below.

Later implementation: [acquisition reliability and evidence-selection repair](ACQUISITION_RELIABILITY_AND_EVIDENCE_SELECTION_2026-10-22.md).
It records transport corrections, genuine saved-body reprocessing and two newly
authorized live checks. This twelve-case audit remains a historical observation,
not the final post-repair state.

## Result

**More text, but four-agent research reliability and relevance are not complete.**
Ran three ordinary prompts for each agent, once each, through the real local
API/SSE routes with provider acquisition. Retained native text increased from
**1,948 to 15,461 words: +13,513, approximately 7.94 times / +693.7%** against the
October 16 identical-input matrix. However, **six of twelve cases still retained
zero evidence**. Scout and Trending produced article bodies; BrandShield and
Personal Watch did not return qualified evidence in this batch.

This is an observational engineering assessment, not independent held-out accuracy
acceptance. No application code, credentials, access gates or timeouts were edited
to improve the result. No source retries, model calls, quota probes, push, merge
or deployment. No browser rendering run was performed for these twelve responses.

## Method and comparability

- Worktree `.scratch/phase9-remediation-20261016`, branch
  `fix/p0-lenovo-acquisition-20261018`, HEAD
  `39a514b68388450bbc5e6061aba97bda2077fc7f` plus preserved dirty implementation.
- Reused the exact twelve inputs in the
  [October 16 Pass A](FOUR_AGENT_OUTPUT_AUDIT_2026-10-16.md), rather than comparing
  unrelated subjects. Its [original measurements](evidence/2026-10-16_agent_output_audit/measurements.json)
  remain unchanged. This is not a controlled before/after code ablation: source
  availability, date, provider state and budgets differ.
- One sequential twelve-case batch, no audit-level retries. Existing **DEEP**
  profile: at most 240 seconds, 24 reader attempts and 120 native HTTP admissions
  per case, with existing lower provider/per-host bounds still enforced. This
  is not a measurement of the default STANDARD profile or production deployment.
- Temporary SQLite/dossiers/raw pools; notifications and background ingestion
  disabled. Live AI disabled, no mock synthesis, zero model reservations/calls
  and no model capability lookup. Native HTTP admissions total **865**; this is
  bounded transport accounting, not complete network or billing accounting.
- Sum of case durations: **771.94 seconds**, about 12 minutes 52 seconds.
- Application fingerprint remained unchanged:
  `53ea40a1ab4ae48eb55fb6f72d98b0b4ff58e9e3d0935a9cec4cc3d408d15eb1`.

The evaluation skill informed the separation of volume, passage relevance and
actual task usefulness. No extra LLM judge was called. The coding agent's passage
review below is explicitly **not** independent human adjudication.

### Count definitions

**Before/now retained words** use whitespace tokens in one `content`, otherwise
`snippet`, per returned native source record. This matches the older metric,
which included corporate homepages and tiny profiles; it was not a useful-article
benchmark. Current **KB** is UTF-8 bytes / 1,000 for that retained native text.

**Raw article words** count captured records structurally classified as article
bodies, excluding same-capture duplicates. **Selected passage words** count the
pipeline's qualified excerpts. They are a code-selected subset, **not** a manual
estimate of all useful words, verified claims or independently relevant evidence.
Article bodies can be useful even when the chosen excerpt is poor. Captured hubs,
feeds and navigation remain available separately and do not inflate article words.
There is no deduplication across separate investigations.

## Per-prompt comparison

| Agent / prompt | Before retained words | Now retained words | Change | Now KB | Selected passage words | Is it enough relevant information? |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Scout / TATAMOTORS.NS | 623 | 1,186 | +563 | 7.847 | 689 | **Limited:** branding/strategy article, not a financial verification dossier |
| Scout / INFY.NS | 0 | 2,845 | +2,845 | 17.577 | 113 | **Partial:** financial figures, but current and historical periods mixed |
| Scout / AAPL | 0 | 6,001 | +6,001 | 38.024 | 323 | **Useful bounded financial overview:** includes captured official earnings release; no claim/filing reconciliation |
| Trending / OpenAI | 0 | 1,765 | +1,765 | 12.094 | 89 | **Limited:** competitor-focused article, weak coverage of OpenAI itself |
| Trending / NVIDIA | 0 | 1,470 | +1,470 | 8.924 | 262 | **Partial:** useful bodies acquired, but selected developments favor background and an incidental mention |
| Trending / electric vehicles | 0 | 2,194 | +2,194 | 15.404 | 179 | **Useful bounded news brief:** three topical fresh articles, not measured virality |
| BrandShield / Nike | 0 | 0 | 0 | 0 | 0 | **No:** two nonqualifying captures, no acquired incident article |
| BrandShield / Apple | 666 | 0 | −666 | 0 | 0 | **No:** discovery succeeded, all selected reads failed |
| BrandShield / Tata Motors | 623 | 0 | −623 | 0 | 0 | **No:** discovery transport failed |
| Personal Watch / Sam Altman | 18 | 0 | −18 | 0 | 0 | **No:** discovery transport failed |
| Personal Watch / Tim Cook | 8 | 0 | −8 | 0 | 0 | **No:** discovery failures/timeouts |
| Personal Watch / Satya Nadella | 10 | 0 | −10 | 0 | 0 | **No:** discovery failures/timeouts |

The decreases do not prove that useful evidence was deleted: the older BrandShield
records were corporate homepages and Personal Watch records were short profiles.
The present failures are nevertheless real failures to serve these investigations.
They do not establish absence of public information, impersonation or threats.
Where the baseline is zero, a percentage increase is undefined, not infinity.

| Agent | Before → now retained words | Raw article words now | Selected passage words | Cases with retained evidence |
| --- | ---: | ---: | ---: | ---: |
| Scout | 623 → 10,032 | 10,032 | 1,125 | 3/3 |
| Trending | 0 → 5,429 | 8,134 | 530 | 3/3 |
| BrandShield | 1,289 → 0 | 0 | 0 | 0/3 |
| Personal Watch | 36 → 0 | 0 | 0 | 0/3 |
| Total | 1,948 → 15,461 | 18,166 | 1,655 | 6/12 |

The entire raw pool retained **61,374 words**, mostly not qualified article text.
Only **21 structural article bodies / 18,166 words** were acquired, of which
**17 records / 15,461 words** survived into native reports. These are not 17
independent publishers or adjudicated facts. The earlier matrix also had six
zero-source cases: the volume increased substantially, but zero-source coverage
did not improve in this single batch.

## Acquisition funnel and exact observed losses

| Prompt | Candidates | Read attempts | Captures | Article bodies | Qualified records | Outcome / first decisive loss |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| TATAMOTORS.NS | 39 | 24 | 15 | 1 | 1 | Source returned; weak financial specificity |
| INFY.NS | 35 | 19 | 11 | 3 | 3 | Sources returned; mixed financial periods |
| AAPL | 45 | 24 | 9 | 6 | 6 | Sources returned; reconciliation not performed |
| OpenAI | 40 | 18 | 7 | 2 | 1 | Fresh source returned; peripheral topic coverage |
| NVIDIA | 61 | 24 | 14 | 6 | 3 | Fresh sources returned; event-passage selection weak |
| electric vehicles | 15 | 13 | 7 | 3 | 3 | Topical sources returned; trend velocity unmeasured |
| Nike | 19 | 11 | 2 | 0 | 0 | Article extraction/type/objective boundary |
| Apple / BrandShield | 66 | 24 | 0 | 0 | 0 | Reading: all attempts failed |
| Tata Motors / BrandShield | 0 | 0 | 0 | 0 | 0 | Discovery: 18 failed query records |
| Sam Altman | 0 | 0 | 0 | 0 | 0 | Discovery: 18 failed query records |
| Tim Cook | 0 | 0 | 0 | 0 | 0 | Discovery: 12 failed, 6 timed-out query records |
| Satya Nadella | 0 | 0 | 0 | 0 | 0 | Discovery: 12 failed, 6 timed-out query records |

All twelve returned HTTP 200 and result events without SSE error events. The
runner's exit 0 is **transport/observation success, not research acceptance**.
Nike correctly returned `INSUFFICIENT_EVIDENCE`; Apple/BrandShield and the last
four investigations returned `ACQUISITION_FAILED` rather than an empty success.

### 1. Downstream selection still loses good acquired information

NVIDIA provides a direct saved-body control: the first paragraphs of two captured
TechCrunch articles describe Google's TorchTPU announcement and AWS's TorchNeuron
release. The selected `recent_developments` instead quote PyTorch/CUDA history and
statistics. A third selected item is an interview with an ex-NVIDIA marketer turned
VC; its passage mentions NVIDIA as a destination for talent, not a new NVIDIA
company event. All three qualified records are from **one publisher**.

Thus the scraper did acquire relevant current material in this case. The next
layer failed to select the strongest new-event passages and suppress incidental
subject mentions. Inspect
[`PassageExtractor.extract_passages`](../../backend/services/research/passage_extractor.py)
and the [Trending recent-development projection](../../backend/agents/trending/agent.py).
The current lead bonus recognizes some auxiliary-verb patterns, but the observed
simple-past announcement lead still lost to keyword/number-rich background.
Fresh publication metadata does not make every paragraph a new development.

### 2. Financial text is richer, but period/context discipline is incomplete

- Tata Motors returns a substantive Tata.cars brand-identity article with strategy
  and restructuring context. Its selected excerpt is **689 words long**. That is
  not equivalent to a concise financial finding or earnings verification.
- Infosys returns financial figures from a 2026 results article, a **July 2010**
  earnings-preview article and a September 2025 buyback report. Their periods are
  inspectable, but a combined current-company report needs stronger separation
  of current facts, historical context and forecasts. A legacy positive-headline
  projection also appears alongside three source-derived passages; it is not a
  fourth newly corroborated proposition.
- Apple is the strongest financial sample: six substantive records include an
  acquired `apple.com/newsroom` earnings release and secondary reporting. The
  report explicitly says filing/claim comparison was **NOT_PERFORMED**. Useful
  source material exists; financial claim adjudication is not established.

### 3. Some topical sources are only peripheral or single-source context

OpenAI's sole retained article is primarily about DeepSeek's open-source inference
framework and competitive pressure on OpenAI/Anthropic. It is related industry
context, not adequate coverage of OpenAI's own latest developments.

Electric vehicles returns three fresh topic-relevant articles on driver attitudes,
digital-native buyers and charging/navigation cybersecurity research. They come
from two observed publisher groups, with two articles on TechXplore. This supports
a bounded news snapshot, not independent corroboration, prevalence, audience
growth, measured trend velocity or a real observed cyberattack.

### 4. BrandShield and Personal Watch failures are not missing evidence judgments

Nike captured 3,192 words across a fake-sneaker spotting guide/photostory and a
publisher homepage. The guide did not establish a structural incident article;
the homepage failed entity relevance. Eight wrapper candidates remained unread
under the existing bounded wrapper-read policy. The system did not fabricate an
observed counterfeit seller from general awareness guidance.

Apple/BrandShield discovered 66 candidates and attempted 24 reads. One was an HTTP
failure, three provider failures, and **20 were recorded as ACCESS_REJECTED at the
SSRF layer**. Backend logs explicitly associate those rejections with **DNS
resolution failures (`getaddrinfo`, Windows 11001)** for the publisher hosts around
10:29:37 local time. This does not prove the pages resolved to private IPs or that
SSRF controls are wrong. Access controls must stay intact.

The remaining Tata Motors and Personal Watch cases then had zero candidates, with
instrumented provider transport failures and some query timeouts. Native HTTP
admissions/budgets were separately recorded per investigation; these observations
do not prove a leaked global deadline or HTTP cap. The exact underlying cause of
the later provider failures—host networking/resolver state, provider behavior or
another transport issue—was **not independently established**. No post-batch DNS
or HTTP probes, reordered batch, retries or additional investigations were run.
Consequently this batch cannot establish the agents' isolated semantic quality
under healthy networking, but it plainly fails real sequential-request reliability.

## Citation joins, scope and next priorities

Seventeen recorded finding-reference observations resolve to returned source
records. That verifies inspectable joins, not factual entailment. There are 18
displayed finding strings, including the extra Infosys legacy projection; do not
declare all displayed prose independently cited or verified. The current trust
panel reports observed publishers rather than invented independence counts.

Highest-value next work, **not implemented during this audit**:

1. Rank source-reported event passages over generic history; test against the
   genuine NVIDIA bodies before any fresh provider request.
2. Separate financial periods/forecasts and current versus historical statements;
   shorten giant selected passages without deleting context or inventing summaries.
3. Diagnose the recorded DNS/provider failure sequence with bounded transport
   diagnostics and honest DNS-versus-policy failure taxonomy. Do not bypass SSRF,
   raise all timeouts or infer that empty results mean no information exists.
4. Only after offline corrections, seek a small fresh authorization for failed
   cases under stable networking. No unlimited sweeps or model calls are needed
   to correct the observed passage-selection defects.

## Reproduction, tests and preserved evidence

Command actually run once; this record grants no new live authorization:

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --research-profile DEEP --env-file <server-env> --output-dir <new-temp-run> --timeout-seconds 240 --max-deep-reads 24 --max-http-admissions 120
python scripts/audits/summarize_raw_harvest.py --run-dir <saved-temp-run> --output <new-summary.json>
```

The first command's default is the fixed twelve inputs. It omits
`--allow-live-ai`. The second is saved-file analysis, not a second acquisition.
Only docs/new sanitized evidence were written to the repository.

| Verification actually run | Outcome |
| --- | --- |
| Full offline suite | Exit 0; **1,826 passed / 38.29s** |
| Fast unit/chaos/security | Exit 0; **1,618 passed / 25.21s** |
| Fatal flake8 / all nine frontend Node files | Exit 0 each |
| Frozen verifier / protected tracked diff before and after | Exit 0; original data unchanged |
| Release smoke | Exit 0; `OFFLINE_SMOKE_PASS` |
| Rollback validator | Exit 0; `OFFLINE_PERSISTENCE_PASS`; original historical archive and deployed rollback remain `NOT_VERIFIED` |
| Live terminal runner / read-only raw summarizer | Exit 0 each; six research failures/empty-evidence outcomes still disclosed |

No fresh browser, hosted CI, deployment, staging rollback, historical dossier
recovery, all-platform coverage or independent accuracy acceptance is claimed.
The regression counts do not override the observed live failures.

[Sanitized measurements and source metadata](evidence/2026-10-21_twelve_prompt_yield/README.md)
· [agent handoff](../handoffs/2026-10-21_TWELVE_PROMPT_WORD_YIELD.md).
