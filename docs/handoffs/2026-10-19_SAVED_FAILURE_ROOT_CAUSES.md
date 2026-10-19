# Saved four-agent failures: root-cause follow-up — 2026-10-19

## Scope and decision

User requested another check of what went wrong. This follow-up diagnoses the
[existing four-prompt run](2026-10-19_PATIENT_FOUR_PROMPT_RECHECK.md), not another
live run. **Zero new provider requests and zero AI calls. No application fix,
commit, push, merge or deployment.** Prior uncommitted audit documentation and
screenshots were preserved. Branch `fix/p0-lenovo-acquisition-20261018`, HEAD
`3a0797edc2693bef135342b1786add9c3807988f` unchanged.

The principal failure is the **discovery-lead to readable-publisher transition**,
compounded by incorrect diversity grouping and no replacement-read loop. The
longer total investigation deadline was not exhausted. Browser replay already
showed the returned source counts; these missing bodies were not lost in the UI.

## 1. Wrapper domains collapse unrelated publishers into one read quota

[DeepReader selection](../../backend/services/research/deep_reader.py) groups
by `item.source_domain` before publisher URL resolution. In these captures,
articles from Bitdefender, Business Insider, WSJ, NBC News, Los Angeles Times,
ABC13 and other publishers all still carry `news.google.com` as that domain.
After two selected items, additional same-class leads are rejected; a novel
query class can admit a third. This treats a transport wrapper as publisher
identity. Distinct titles do not prove independent sources, but a shared wrapper
does not prove a single publisher either.

Observed selection reasons:

| Input | Selected | `same_domain_over_budget` | Background excluded |
| --- | ---: | ---: | ---: |
| Nike | 3 | 14 | 10 |
| Tim Cook | 4 (one X profile, three wrappers) | 6 | 0 |

Nike's selected third wrapper is a stock-price headline with
`objective_read_match: false`, while multiple counterfeit/fraud headlines have
`objective_read_match: true` but are rejected by that wrapper-domain quota.
The novelty-of-query-class exception can therefore admit off-task material
without opening the quota for additional task-related articles.

**Offline control:** network blocked with
`scripts.validation.isolated_runtime.block_live_network()`. Called actual
`DeepReader._select_read_candidates(..., max_reads=6)` on six synthetic, equally
scored, same-query-class news items. Six `news.google.com` domains selected only
two and rejected four as `same_domain_over_budget`; six distinct synthetic
publisher domains selected six. This isolates the grouping behavior, not a
prediction that six real publisher pages would be accessible or independent.
No URL/domain rewrite was applied to the actual saved investigation.

## 2. Selected wrappers fail resolution, not their total clock

All three Nike wrappers and all three Tim Cook article wrappers have
`wrapper_resolution.status: UNRESOLVED`. Each nested lookup recorded
`SUCCESS`, three raw results and three normalized results. None produced a
publisher lead accepted by the resolver. Nike lookups took about 0.59–0.78s
provider time; Tim Cook lookups about 0.66–2.95s, with some queue delay.

[`_resolve_wrapper`](../../backend/services/research/deep_reader.py) searches
one headline (up to 180 characters), examines at most three fragments and requires
a non-Google URL plus at least 75% title-token overlap. It does not acquire an
article when no candidate passes; that conservative behavior is correct.

**Important evidence limit:** saved resolution telemetry retains the query and
execution counts, but not returned candidate titles/URLs or individual rejection
reasons. It cannot establish whether these exact results were unrelated,
still wrappers, title variants below threshold, or some mixture. Do not assert
that the 75% threshold alone caused these six failures, lower it blindly, or
assume longer waiting would make the returned candidates relevant. A future fix
should retain bounded, sanitized resolution-candidate/rejection observations.

## 3. Failed reads do not trigger replacement reads

`DeepReader.deep_read` selects a fixed batch, attempts it and returns successful
items. [DeepReadingStage](../../backend/application/research/reading.py) has
additional observed-link reading only for a financial issuer-document chain;
it does not replace failed specialist reads with the next eligible lead.

Nike ends with zero bodies after three failed wrappers despite about **84s**
total time remaining. Tim Cook returns one profile after three failed article
wrappers with about **88s** remaining. More total time does not execute work
that was never scheduled. Replacement must remain bounded by attempted-read,
provider, byte and total-time limits; do not implement unlimited retries.

## 4. Adaptive follow-ups lose the investigation objective

[RetrievalPlanner.plan_adaptive_follow_ups](../../backend/services/agent_reach/planner.py)
has no explicit domain/intent argument. Its capitalized-word regex treats
headline fragments as named entities and appends the generic terms
`announcement statement partnership`. Real saved follow-ups include
`"Nike" "Wikipedia Nike" ...`, `"Nike" "Nike Golf" ...` and
`"Tim Cook" "Amid Hype" ...`. These are not focused counterfeit/deepfake
verification questions.

A separate synthetic offline call to this actual method produced
`"Nike" "Nike Golf Wikipedia" announcement statement partnership` and
`"Tim Cook" "Amid Hype Deepfake" announcement statement partnership` from toy
titles. These are controlled examples, not extra live investigations.

For Nike the backend log explicitly says no new adaptive queries were generated
in round two. `BUDGET_CEILING` is the generic assembly fallback, not evidence that
the 120s clock ran out. Other runs stopped on heuristic marginal novelty. Query
novelty is not proof that relevant source acquisition is complete.

## 5. Attribution repair stops at the native Trending boundary

The deep reader stores conflicting body/feed authors in metadata but does not
change `source_name`. Trending's native adapter prefers the page's body author.
However [UnifiedEvidenceItem.from_evidence_item](../../backend/schemas/unified_report.py)
still creates `source.name` from `source_name`, so the shared report displays
Gerardo Delgado while the captured article names Shreevar Rastogi. This is a
cross-projection provenance bug, not a browser text-loss issue. Preserve both
observations and visibly represent the conflict; do not silently erase it.

Scout's two finding excerpts also come from overlapping USD/INR versions of
one issuer release; they are not two independent confirmations.

## 6. External limits and telemetry remain separate issues

All eight recorded main-query timeouts in the four-prompt run were started
Reddit chains. Logs also show repeated subreddit RSS HTTP 429s. Some minimal
NVIDIA Reddit submission metadata was obtained, but this does not establish
reliable platform access. Removing timeouts does not grant provider access.
Zero synchronous doctor calls were recorded; no total deadline was exhausted.

All 47 initial records have explicit provider-start instrumentation. Eight
adaptive records have null provider-start/duration fields and use status-based
counting. `SUCCESS` with three search fragments does not mean a readable article
was acquired. Stop labels, starts and acquisition depth must remain distinct.

## Checks actually run in this follow-up

- Read saved native responses, nested wrapper execution records, selection
  audits and backend logs; inspected their owning code paths. No browser/provider
  rerun, no API key inspection and no live AI validation.
- Two synthetic offline controls described above: exit 0, network blocked,
  actual selector/planner methods, no source mutation.
- `python -m pytest tests/unit/test_acquisition_followup_repairs.py tests/unit/test_patient_research_budget.py -q -o "addopts=--tb=short -ra"`:
  exit 0, **18 passed in 1.20s**. Their green result does not cover acceptance of
  this real multi-wrapper failure. Existing wrapper tests mock matching/mismatching
  search fragments; they do not validate production search relevance, replacement
  reads or the complete shared-author projection.
- Full regression was not repeated for this read-only diagnosis. The preceding
  report's 1,474/1,266 totals are dated prior runs, not new executions here.

## Recommended repair order — not implemented by this diagnosis

1. Separate unresolved-wrapper transport identity from observed publisher identity
   in selection; preserve unknown independence and existing access/SSRF controls.
2. Capture bounded resolver candidates/rejections, resolve relevant direct URLs,
   then use finite replacement reads when the selected source cannot be acquired.
3. Preserve agent intent and incident clues in adaptive queries; avoid generic
   title-fragment expansions and irrelevant fallback material.
4. Propagate attribution conflicts through shared reporting; deduplicate overlapping
   issuer-release findings; correct stopping/start telemetry.
5. Reproduce these saved failure patterns offline before another small live pass.
   AI suggestions may help query formulation, but cannot substitute for source
   bodies, citations, access permissions or independently supported conclusions.
