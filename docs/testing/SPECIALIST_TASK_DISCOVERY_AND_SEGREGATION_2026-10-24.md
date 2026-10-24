# Specialist task discovery and segregation — 2026-10-24

## Decision / scope

**Specialist-plan wiring and evidence segregation implemented and verified
offline. Fresh live acquisition improvement remains UNVERIFIED.**

The user's “yes / continue” authorized the proposed BrandShield/Personal Watch
improvements: keep shared secure acquisition, specialize what is searched/read
and how captured evidence is interpreted. This is a targeted correction, not a
new architecture or another scraper.

Checkout `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, base HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f` plus inherited dirty work.
No commit, push, merge, deployment, new source/provider request, model call,
paid Firecrawl call or access/credential change. The prior six live permissions
were already consumed and were **not reused**.

[Offline selected controls and code hashes](evidence/2026-10-24_specialist_task_wiring/offline-controls.json)
are explicitly synthetic planning/saved-response observations, not a live funnel.

## What was wrong

1. **Plan dropped at orchestration:** the DEEP/shared harvest path created a
   claim-aware source plan, then discarded its core web/news/RSS actions while
   retaining at most two other-source actions. Broader domain templates drove
   actual core discovery.
2. **Precision lost even before that adapter:** Personal Watch's generic
   priority-zero identity queries could fill the planner's per-channel web cap
   before exact quotation lookup/denial queries. Reconnecting only the admitted
   subset did not repair that earlier loss. Actual-planner regressions, not just
   manually constructed plans, reproduced it.
3. **Subject matter overrode agent mission:** a Personal Watch quotation about
   quarterly revenue could be planned as financial research; hardware nouns
   could similarly displace speaker/quotation verification.
4. **Task disappeared through deduplication/continuation:** the same URL found
   by statement and identity queries kept only its first routing objective.
   Observed publisher children/hubs lacked complete task lineage.
5. **Read selection was only domain-specific:** complaint and phishing leads
   could tie even when the user explicitly asked about phishing. Unrelated
   generic fallback angles still consumed discovery.
6. **Personal interpretation conflated roles:** generic `PUBLIC_STATEMENT`
   paragraphs could receive the monitored person's speaker label without
   observed attribution. Disputed quotations were dropped instead of retained
   separately. Synthesis also mutated the caller's evidence/passages.

These are distinct from transport/access restrictions. A correct custom layer
cannot turn a homepage or irrelevant old appointment article into identity
evidence, and no keyword/task label establishes truth.

## Implemented boundaries and file map

| Layer / owner | Correction and preserved invariant |
| --- | --- |
| [SourcePlanningEngine / SourcePlan](../../backend/services/agent_reach/source_planner.py) | Task-aware ordering occurs before both global action and per-channel caps. Original validated query text/IDs/operations survive. Exact quote and false-quote denial queries outrank unrelated profile defaults. Personal domain attribution takes precedence over incidental finance/hardware terms; explicit brand-abuse/safety tasks avoid accidental financial routing. Non-specialist and entity-only ordering controls remain covered. |
| [specialist_planning](../../backend/services/research/specialist_planning.py) | Select existing validated actions only: at most six core searches plus two optional routes, still within the source-plan budget. Stale/mismatched projections, blocked capabilities and unsupported operations are rejected. Unsupported core direct-read actions receive an explicit routing limitation; they are not turned into searches. Diagnostics omit query/claim text. |
| [run_harvest_pipeline](../../backend/application/research/harvest_pipeline.py) | Pass selected task-aware core rows into the actual harvesting boundary. Report promoted source-plan selection separately from profile admission and actual submission; submission is not provider start or acquired evidence. |
| [HarvestingEngine / diversified_queries](../../backend/services/research/harvesting.py) | Explicit-task fallback angles remain on-task. Entity-only requests retain broader domain exploration. Title/snippet/URL-path observations prioritize candidate reads; query wording alone cannot make an unrelated lead relevant. No cap increase or automatic evidence acceptance. |
| `_merge_task_lineage` in harvesting | Canonical URL deduplication preserves bounded task, action-ID and objective lists. Observed hubs/children retain routing context. The first canonical record is not replaced and body bytes/citation IDs are not regenerated. |
| [RawAcquisitionPool](../../backend/services/research/raw_pool.py) | Bounded routing snapshots survive export/replay while qualification stays pending/rejected until normal body/passage gates run. Routing labels are not source assertions or corroboration. Existing raw captures remain unchanged. |
| [Personal Watch synthesis](../../backend/agents/personal_watch/assessment.py) | Actual target attribution is required for public statements. Separate bounded `disputed_claims` retain exact passage IDs, offsets, source citations and full context as UNVERIFIED publisher assertions. No target speaker, authenticated identity, proven falsehood or impersonation verdict is manufactured. Deep copies preserve caller inputs. |
| [Agent output](../../backend/agents/personal_watch/agent.py), [ReportBuilder](../../backend/services/report_builder.py), [renderer](../../frontend/unified-report-renderer.js) | Project disputes through scan/watch and shared reporting into a separate “Disputed attribution” section. Escape source text, validate links and retain explicit uncertainty. Quotes and disputes are not merged into one confirmed-speech list. |

The existing BrandShield complaint/warning/allegation/enforcement/suspicious-
behavior classifier is retained. This task strengthens its discovery and reading
strategy; it does not recategorize a recall as counterfeit detection.

## Offline proof / before → after

| Control | Before | After |
| --- | --- | --- |
| Validated core BrandShield/Personal rows at actual harvest boundary | Dropped | Passed with original action IDs |
| Actual personal false quote about quarterly revenue | Can misroute to financial; exact lookup/denial displaced by web cap | Attribution plan; exact lookup/denial survive original caps |
| Literal target quotation | Precise lookup can be crowded out | Literal quote query preserved; no generated quotation |
| Explicit brand phishing / recall | Broad subtype/unrelated fallback may spend slots | Existing claim-specific rows first; task-shaped fallback within same budget |
| Same URL found by statement + identity queries | Secondary objective lost | One capture, both routing objectives/action lineages retained |
| Observed hub → article | Task trace incomplete | Task/action lineage survives normal safe reading |
| Disputed quotation paragraph | Discarded or risk of wrong speaker projection | Separate UNVERIFIED source assertion with exact spans |
| Other speaker / metadata / index | Must not become target speech | Negative controls remain conservative |
| Non-specialist domain with accidental task argument | Potential internal list-index error | Task arguments do not alter financial/general/Trending queries |

Five fictional planning examples are saved with **synthetic eligible capability
decisions**, clearly not measured live capability health:

- Quartz Tools phishing incident.
- Quartz Tools product recall.
- Elena Rivera's literal quoted quarterly-revenue statement.
- Elena Rivera's disputed quoted quarterly-revenue statement.
- Elena Rivera entity-only broad investigation.

The real planner and task adapter are executed, but no provider is contacted.
Synthetic network/reader doubles exercise actual harvesting/qualification wiring
in tests; they are not presented as acquired publisher articles.

### Genuine saved-response negative controls

Read-only reprocessing of the last authorized native responses confirmed source
bytes and in-memory evidence unchanged:

- Mary Barra: native evidence still zero; public statements, disputes and
  suspected impersonations stay zero. The previous raw appointment article was
  not silently accepted to fill the new UI.
- Dyson: its one retained article remains a source-reported allegation. The
  earlier recall/correction is not converted to a confirmed threat.

Response hashes are in the evidence JSON. The old 781-word Dyson / 484-word raw
Mary observations are **historical acquisition measurements**, not new-code word
yield. No new before/after live word-count increase is claimed.

## Verification

Final results are recorded below after code freeze. Normal tests block external
networking, blank credentials and use temporary runtime storage.

| Command / scope | Result |
| --- | --- |
| Full offline suite | Exit 0; **2,184 passed /85.09s** |
| Fast unit/chaos/security suite | Exit 0; **1,976 passed /73.69s** |
| New dedicated controls | 60 controls: 35 planning, 16 Personal segregation, nine harvest/projection controls; included in full/fast, not additional unique totals |
| Focused combined planner/segregation/scope/runtime run | Exit 0; 93 passed /1.31s before final non-specialist robustness control |
| Separate read-only final planner/harvest review | Exit 0; 98 passed /1.26s before that final robustness control; no blocking access/budget/evidence-promotion regression |
| Each of nine Node frontend scripts | Exit 0; disputed-claim escaping, unsafe-URL exclusion and quote/dispute separation checked |
| Fatal flake8 E9/F63/F7/F82 | Exit 0; zero fatal findings |
| Release smoke | Exit 0; OFFLINE_SMOKE_PASS, not live research |
| Rollback validator | Exit 0; OFFLINE_PERSISTENCE_PASS, historical archive/deployed rollback NOT_VERIFIED |
| Frozen benchmark verifier | Exit 0; hashes match |
| Protected tracked diff / whitespace | Exit 0; protected data unchanged relative to HEAD; CRLF conversion warnings only |
| New relative links / offline evidence hashes | Exit 0; 20 relative links resolve, all nine recorded implementation hashes match final code |

Portable main commands:

```text
python -m pytest tests/ -q --tb=short -p no:cacheprovider
python -m pytest tests/unit tests/chaos tests/security -q --tb=short -p no:cacheprovider
python -m pytest tests/unit/test_specialist_planning.py tests/unit/test_specialist_harvest_wiring.py tests/unit/test_personal_task_segregation.py -q --tb=short -p no:cacheprovider
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
node tests/frontend/test_unified_report_renderer.js
python scripts/validate_release_candidate_smoke.py
python scripts/validate_rollback_compatibility.py
python scripts/validation/verify_frozen_benchmarks.py
```

Intermediate failures are retained in this account: initial wiring tests exposed
the five intended gaps after correcting a missing synthetic result-domain field
and Counter fixture. Initial full/fast each exposed one existing test relying on
input mutation (2,177/1,969 other tests passed). That test now validates the same
recovered-article scope directly via `captured_passages` and asserts unchanged
input, instead of requiring mutation. Frozen fixtures/labels were not changed.
An attempted focused command named a nonexistent test path and collected zero;
the corrected 93-test command above passed. Earlier 2,183/1,975 green inventories
precede the final extra robustness control; they are not final totals.

## Remaining acceptance and next action

The repaired task strategy is **not yet shown to improve live publisher recall**
or Mary's actual evidence yield. Original publisher-resolution/access failures
can still occur. Core direct reads selected by source planning require a proper
observed-read route; this adapter reports that limitation instead of pretending
the URL was searched/acquired. Optional source availability remains governed by
existing capability/access checks.

No rendered-browser/visual/responsive acceptance was performed in this task;
Node rendering/security contracts do not replace that. No independent accuracy,
issuer/period adjudication, broad brand-threat positives, media forensics,
measured virality, hosted CI, production parity, rollback deployment or historical
dossier recovery is accepted here.

Next high-value check, requiring **new bounded live authorization**, is one
explicit brand-threat/safety query and one attributed-statement/quotation query
using the frozen code. Inspect query admission, resolved publisher URLs, native
article text and exact supporting passages—not merely query success or HTTP200.
Do not repeat unrestricted sweeps or reuse prior permissions. Keep all protected
datasets/dossiers/research/artifacts intact.

Skills used: debugging-strategies and python-testing-patterns drove controlled
reproduction and adversarial contracts; frontend-security-coder guided escaped
source text and safe-source links. This is an engineering decision record, not
a private reasoning transcript or an invented execution transcript.
