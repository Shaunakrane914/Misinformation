# Aegis Protocol — consolidated defect report

Date: 2026-10-19 (Asia/Calcutta). Status: **OPEN — research-quality acceptance incomplete.**

## 1. Executive assessment

The latest local runs prove that acquisition can retrieve financial PDFs and a
publisher article, and that the frontend can render their returned records.
They do **not** prove that all four agents reliably produce useful intelligence.
BrandShield/Nike acquired no bodies. Personal Watch/Tim Cook acquired only a
short profile. Increasing the overall research window did not resolve either.

The main failure chain is:

```text
Discovery returns headlines and Google News wrapper URLs
  -> wrappers are grouped as one publisher during read selection
  -> potentially useful leads are excluded by that shared-domain quota
  -> selected wrappers fail to resolve to acceptable publisher URLs
  -> specialist reading has no bounded replacement-candidate loop
  -> zero incident bodies, or a profile-only result
  -> generic expansion stops without answering the agent's actual objective
```

There are also evidence-integrity and presentation defects: conflicting author
attribution, an invented default LOW exposure label, non-contradictory headings
shown as disagreements, duplicate release excerpts, and misleading telemetry.
These deserve correction before another redesign, new source rollout or broad
live testing campaign.

This register contains **17 current defects or observed reliability failures**,
plus separately labeled external constraints, historical findings and acceptance
gaps. It is a consolidation of the inspected investigation/reporting path, **not
an exhaustive fresh security or whole-repository audit**. An uninspected area is
not certified defect-free. No new P0 vulnerability or data-loss event was
established by this review; that is not a security clearance.

## 2. Scope, version and evidence rules

- Branch: `fix/p0-lenovo-acquisition-20261018`.
- HEAD: `3a0797edc2693bef135342b1786add9c3807988f`.
- Application checkpoint: `69b48d64bc7ec8146a2da18bec5b8170dc7c861c`.
- Application fingerprint in the saved four-case run:
  `6218d514c146173b9354237c0e46cdb0a6a6e1a59d25a268bb2e936f5be052bc`.
- Earlier uncommitted audit documents/screenshots were preserved. This task
  changes documentation and adds selected diagnostic evidence only.
- **Zero new provider requests, zero AI calls and no new browser investigation.**
  Existing responses, nested execution records, rendered-text captures and code
  were inspected. Prior synthetic offline controls are cited, not newly invented.
- No application fix, environment edit, commit, push, merge or deployment.
- Production SHA, current provider account health, deployed configuration and
  historical archive inventory were not freshly attested.

Evidence terms used below:

| Label | Meaning |
| --- | --- |
| Current capture + code | Observed in the saved current-application output and explained by inspected code |
| Offline reproduction | Actual method exercised with controlled synthetic inputs and network blocked; not live acquisition proof |
| Observed failure | Failure is established; its precise provider-side cause is not fully captured |
| Acceptance gap | Required capability/validation is not demonstrated; not automatically a coding defect |
| Historical / not reverified | Earlier evidence exists, but this report does not assert a fresh production or archive observation |

Priorities: **P1** = evidence integrity, specialized investigation reliability or
acceptance blocker; **P2** = important correctness/observability/maintenance work.
Priority is not an exploitability score. Owners below are code areas, not assigned
people. Repairs are recommendations, not work completed by this report.

### Evidence index

- **E1:** [Four-prompt patient-window report](../handoffs/2026-10-19_PATIENT_FOUR_PROMPT_RECHECK.md),
  [measurements/screenshots](evidence/2026-10-19_patient_four_prompt_recheck/README.md).
- **E2:** [Saved-failure root-cause follow-up](../handoffs/2026-10-19_SAVED_FAILURE_ROOT_CAUSES.md):
  actual selection/planner offline controls and wrapper traces.
- **E3:** [Additional selected observations](evidence/2026-10-19_defect_register/observations.json):
  current saved field mismatches, missing doxxing assessment, raw change text and
  Scout disagreement headings. These are excerpts/measurements, not full dossiers.
- **E4:** [Earlier deployed-output observations](../handoffs/2026-10-18_RELEASE_PREPARATION_AND_DEPLOYMENT.md):
  dated production findings, not a new deployment check.
- **E5:** [Rollback verification and recovery boundary](../operations/ROLLBACK_VERIFICATION.md),
  [2026-10-18 archive observation](RESEARCH_QUALITY_COMPLETION_REVIEW_2026-10-18.md).
- **E6:** [Independent reviewer packet](RESEARCH_QUALITY_REVIEWER_PACKET_2026-10-18.md):
  prepared procedure and 48 case slots, not completed independent labels.

## 3. Observed four-agent baseline

| Agent / input | Seconds | Native records | Retained words | Decimal KB | Findings | Discovery cards |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Scout / Infosys | 51.13 | 7 | 3,780 | 29.328 | 2 | 24 |
| Trending / NVIDIA | 28.28 | 3 | 874 | 5.927 | 1 | 5 |
| BrandShield / Nike | 36.08 | 0 | 0 | 0 | 0 | 22 |
| Personal Watch / Tim Cook | 32.59 | 1 | 8 | 0.059 | 0 | 9 |

Words are whitespace tokens in one retained native content/snippet per record.
KB = UTF-8 bytes / 1,000, excluding metadata and discovery projections. Counts
are not verified facts, independent corroboration, useful words or website coverage.

All requests returned HTTP 200 and a result event. Nike correctly returned
`ACQUISITION_FAILED`; that is not successful research. Other `COMPLETED` values
describe pipeline completion, not proof that the specialized job was accomplished.

The 120s clock was not exhausted. Remaining total time after processing was
69.491s / 91.893s / 84.151s / 87.528s respectively. All 47 initial query records
explicitly show provider starts; eight adaptive records lack equivalent fields.
No initial query was `QUEUE_TIMEOUT`, `NOT_SUBMITTED` or `SKIPPED`. Zero synchronous
doctor calls were recorded. These facts rule out total deadline starvation and
synchronous doctor work as the explanation for this particular four-case failure.

## 4. Current defect register

| ID | Priority | Defect / failure | Evidence |
| --- | --- | --- | --- |
| D01 | P1 | News wrappers collapse unrelated publishers into one diversity quota | E1/E2, offline reproduction |
| D02 | P1 | Selected relevant-looking headlines do not resolve into acquired publisher bodies | E1/E2, observed failure |
| D03 | P1 | Failed specialist reads do not schedule replacement candidates | E1/E2 + code |
| D04 | P1 | Adaptive planning loses agent intent and uses headline fragments as entities | E1/E2, offline reproduction |
| D05 | P2 | Query-class diversity admits off-task reads while incident leads are excluded | E1/E2 + code |
| D06 | P1 | Native and shared reports disagree on captured article attribution | E1/E3 + code |
| D07 | P1 | Missing Personal Watch doxxing assessment renders as LOW exposure | E3 + code |
| D08 | P1 | Scout factor headings become disagreements without an incompatible proposition | E3/E4 + code |
| D09 | P2 | Structured change events are displayed as stringified dictionaries | E3/E4 + code |
| D10 | P2 | Overlapping issuer-release versions become duplicate findings | E1 + captured excerpts |
| D11 | P2 | Generic stop label suggests budget exhaustion when work simply stopped | E1/E2 + code |
| D12 | P2 | Saturation summary key mismatch silently exports zero | E3 + code |
| D13 | P2 | Adaptive execution records lack measured provider lifecycle fields | E1/E2 + code |
| D14 | P2 | Funnel stages use mixed scopes and ambiguous read counters | E1 + code |
| D15 | P2 | Resolver diagnostics omit returned candidates and rejection reasons | E2 + code |
| D16 | P1 | Existing acceptance checks miss important semantic/reporting defects | E1/E2/E3 + tests |
| D17 | P2 | Documentation entry points contain stale current-state metadata | Current documentation |

### D01 — Wrapper-domain diversity collapse

**Owner:** [DeepReader._select_read_candidates](../../backend/services/research/deep_reader.py).
**Status:** confirmed current capture/code and reproduced offline.

Selection uses `item.source_domain` before resolving Google News wrapper URLs.
Distinct publisher leads therefore occupy one `news.google.com` quota. The
same-domain rule generally admits two entries, or a third for a novel query class.
Nike had 14 candidates rejected as `same_domain_over_budget`; Tim Cook had six.
These are leads whose publisher names appear in discovery titles, not authenticated
publishers or proof that all those stories would have been readable.

The network-blocked synthetic control selected two of six same-class wrapper
items, versus all six when their synthetic domains differed. No live source
domains were fabricated or rewritten to obtain that result.

**Impact:** an access wrapper, rather than actual publisher identity, narrows the
evidence pool. More request time does not change this deterministic exclusion.

**Repair:** distinguish transport identity from observed/resolved publisher
identity. Keep independence unknown until supported; do not equate different
wrapper tokens or title suffixes with independent reporting.

**Acceptance:** several wrapper leads representing distinct observed publishers
must not be excluded solely because they share a transport host. True same-publisher
and syndicated duplicates must still obey finite diversity/read limits.

### D02 — Publisher resolution does not deliver article bodies

**Owner:** [DeepReader._resolve_wrapper](../../backend/services/research/deep_reader.py),
shared acquisition search/read boundaries. **Status:** observed reliability failure;
the exact candidate-rejection cause remains unverified.

All three selected Nike wrappers and all three selected Tim Cook article wrappers
remained `UNRESOLVED`. Each nested lookup reported success with three raw and three
normalized fragments. None produced an acceptable publisher lead. The resolver
searches one headline, takes up to three results, excludes Google destinations
and requires at least 75% title-token overlap before the protected direct read.

**Impact:** promising incident headlines remain discovery-only. Nike has zero
bodies; Tim Cook retains only a profile. This is not evidence that information
does not exist, nor proof that the 75% threshold itself is wrong.

**Repair:** first close D15's evidence gap; evaluate bounded observed publisher
links, metadata and alternative direct leads. Preserve URL safety, access policy,
entity/event matching and claim attribution. Do not invent URLs, count search
snippets as bodies, or relax matching merely to increase counts.

**Acceptance:** saved positive/negative resolution cases identify why candidates
pass/fail, only matching actual URLs reach direct reading, and a resolved lead
becomes a captured body or an accurately reported read failure.

### D03 — No replacement-read scheduling after specialist failure

**Owner:** [DeepReadingStage.run](../../backend/application/research/reading.py),
[DeepReader.deep_read](../../backend/services/research/deep_reader.py).
**Status:** confirmed code and current output.

The reader selects a fixed batch and returns its successful acquisitions.
Additional observed-link reads exist for financial issuer chains, not a general
specialist failure-replacement loop. Nike's three selected reads fail, but no next
eligible lead is tried. Tim Cook likewise stops after its article failures.

**Impact:** useful remaining budget is idle: approximately 84s/88s remained in the
two specialist cases. The system cannot benefit from extra time without new work.

**Repair:** a finite, objective-aware replacement queue. Count every attempt,
respect remaining time/bytes/concurrency/access policy, avoid repeats and return
explicit failure when no eligible alternative remains.

**Acceptance:** with first reads mocked to fail and a later eligible candidate
readable, that candidate reaches reading within the same fixed attempt/deadline
budget. An all-fail case terminates honestly; late results cannot mutate a report.

### D04 — Adaptive planning loses task intent

**Owner:** [RetrievalPlanner.plan_adaptive_follow_ups](../../backend/services/agent_reach/planner.py),
[AdaptiveExpansionStage](../../backend/application/research/adaptive.py).
**Status:** captured examples, code and offline synthetic reproduction.

The method has no explicit domain/intent parameter. A capitalized-word regex
accepts title fragments as entities and adds `announcement statement partnership`.
Captured examples include `Wikipedia Nike`, `Nike Golf`, and `Amid Hype` for Tim
Cook. This spends follow-ups on generic relationships rather than counterfeit,
phishing, impersonation, original quotations or deepfake allegations.

**Repair:** propagate the investigation objective; extract concrete incident,
entity, event and original-source clues rather than arbitrary title casing.
Keep advisory AI optional and budgeted; deterministic planning must still work.

**Acceptance:** brand/person, financial and trend fixtures yield different,
task-relevant follow-ups; generic title fragments cannot fill scarce slots ahead
of incident/original-source questions. No special-casing the four audit entities.

### D05 — Off-task query-class novelty wins a read slot

**Owner:** specialist sorting in [reading.py](../../backend/application/research/reading.py)
and secondary selection in [deep_reader.py](../../backend/services/research/deep_reader.py).
**Status:** current capture + code.

Nike selected a stock-price headline with `objective_read_match: false` while
multiple fraud/counterfeit leads marked true were excluded. Sorting by objective
does not prevent the same-domain/query-class exception from admitting off-task
material after the first two matches.

**Impact:** finite read slots do not consistently serve the specialist objective.
Background may be worth retaining, but is not an equivalent incident read.

**Repair/acceptance:** combine objective priority with corrected diversity rules;
separately budget optional background. A financial-price headline must not displace
an eligible task-related incident solely because its query class differs. Keep
background inspectable without promoting it to threat evidence.

### D06 — Attribution conflict is not preserved consistently in display

**Owner:** [DeepReader](../../backend/services/research/deep_reader.py),
[Trending native adapter](../../backend/agents/trending/agent.py),
[UnifiedEvidenceItem.from_evidence_item](../../backend/schemas/unified_report.py).
**Status:** current capture + code.

For `ev_02bfb85bef74`, native author is Shreevar Rastogi, with discovery author
Gerardo Delgado and `attribution_conflict: true`. Corpus `deep_read_sources.author`
and shared `source.name` still use Gerardo Delgado. The UI therefore presents the
feed attribution while the inspected body names another author.

**Impact:** a stable citation ID does not prevent incorrect attribution. The
source record and different report projections disagree about provenance.

**Repair/acceptance:** represent publisher, captured byline and discovery/feed
attribution separately, with the conflict visible. A cross-layer test must join
the same canonical ID through native/corpus/shared/DOM projections and retain
both observations without declaring either independently authenticated.

### D07 — Missing doxxing assessment defaults to LOW

**Owner:** [renderAgentIntelligence](../../frontend/unified-report-renderer.js).
**Status:** confirmed current rendered-text capture, JSON and code.

Tim Cook has no returned `doxxing_exposure` assessment. His identity record alone
causes the specialized module to render; `dox.doxxing_risk_level || 'LOW'` fills
the missing assessment with LOW. The report otherwise correctly says its eight
profile words cannot determine identity-abuse exposure.

**Impact:** the specialized card gives false reassurance and contradicts the
conservative summary. This is a rendering default, not a measured backend risk.

**Repair/acceptance:** absent, failed, profile-only or unsupported assessment
must display UNASSESSED/INSUFFICIENT_EVIDENCE with scope. LOW may appear only when
an actual returned, bounded assessment supports that label; lack of observed
patterns must never become a general assertion of safety. Test missing/null/empty
objects, explicit observations and acquisition failure in native and shared UI.

### D08 — Scout headings are promoted to disagreements

**Owner:** [synthesize_financial_intelligence](../../backend/agents/scout/assessment.py),
[ReportBuilder.from_scout_result](../../backend/services/report_builder.py).
**Status:** current capture + code; related earlier production observation in E4.

The deterministic synthesis puts positive/negative/unresolved factor headings
under `contradictions.for/against/unresolved`. The builder flattens these into
shared disagreements. Current Infosys disagreements are `Results for the First
Quarter ended June 30, 2026` and `View past annual reports`, despite zero detected
corpus contradictions. Neither heading establishes incompatible propositions.

**Impact:** a user can mistake unrelated context or financial sentiment for
counter-evidence. Different headlines are not a contradiction assessment.

**Repair/acceptance:** keep catalysts, unresolved context and contradiction
records distinct. Require two comparable propositions, compatible period/unit/
subject context, linked passages and a reason for incompatibility. Two unrelated
headlines must not enter disagreements; a real conflicting financial claim must
remain representable and linked to its sources.

### D09 — Change events are stringified instead of normalized

**Owner:** [ReportBuilder.from_personal_result](../../backend/services/report_builder.py).
**Status:** current capture + code; also observed historically in E4.

Native `changes` contains a `BASELINE_INITIALIZED` object. Shared `changes` uses
`str(c)`, displaying dictionary punctuation/keys/timestamp in “What changed?”.

**Repair/acceptance:** map description, type, severity, timestamp and references
to a display contract. Explain that baseline initialization is not a new threat.
Fixtures for baseline/new/resolved/escalated changes must yield readable text,
preserve lineage and avoid raw object strings in native/shared views.

### D10 — Duplicate issuer-release observations

**Owner:** [grounded synthesis](../../backend/application/research/synthesis.py),
source/document grouping and report summarization. **Status:** current capture.

The two Infosys findings repeat the opening paragraphs of USD/INR versions of the
same issuer release. They remain UNVERIFIED and their citations join captured
bodies, which is correct. However, two long, near-duplicate findings obscure the
useful facts and may suggest more corroboration than exists.

**Repair/acceptance:** group overlapping same-event/source versions, retain
currency/reporting-basis differences and both citations, and summarize one
observation where appropriate. Do not collapse genuinely different consolidated/
segment, period or restatement values. Display independent confirmation only when
it is actually established. No benchmark relabeling to make counts look better.

### D11 — Stopping reason misidentifies the limiting resource

**Owner:** [CorpusAssemblyStage](../../backend/application/research/assembly.py),
[adaptive coordination](../../backend/application/research/adaptive.py).
**Status:** current capture + code.

Nike's funnel says `BUDGET_CEILING`, its novelty ledger says `Completed standard
budget`, and logs say no new adaptive queries were generated in round two.
Approximately 84s remained. Assembly supplies BUDGET_CEILING when no specific
reason exists, encouraging incorrect timeout diagnosis.

**Repair/acceptance:** distinguish no new queries, fixed attempt/round limit,
heuristic novelty, total/stage deadline, access failure and queue exhaustion.
Mock early no-new-query termination with ample time; it must not claim a
wall-clock cutoff. Preserve genuine deadline failures with measured remaining time.

### D12 — Saturation score is silently zeroed by a key mismatch

**Owner:** [evidence_saturation.get_summary](../../backend/services/research/evidence_saturation.py),
[assembly funnel](../../backend/application/research/assembly.py).
**Status:** newly identified current capture + code.

The tracker returns `final_saturation_index`. Assembly reads
`sat_summary.get('cumulative_saturation', 0.0)`. All four funnels consequently
export 0.0 while trace values are 0.747 / 0.747 / 0.451 / 0.747. This is a schema
mismatch, not evidence that saturation was independently measured as zero.

**Repair/acceptance:** use one explicit summary contract, with compatibility
handling if required. Assert funnel/trace consistency for nonzero and empty
summaries, distinguishing unavailable values from true zero. Continue labeling
the score as heuristic, not empirical web coverage or proof of topic exhaustion.

### D13 — Adaptive lifecycle fields are not measured end-to-end

**Owner:** [AdaptiveExpansionStage](../../backend/application/research/adaptive.py),
[query assembly](../../backend/application/research/assembly.py).
**Status:** current records + code.

Eight adaptive query records have null provider-start, queue and provider-duration
fields. Assembly falls back to status-based start counting. Thus “55 started”
combines 47 explicitly instrumented initial starts and eight legacy-style records.
Some failed adaptive queries have no detailed error, making empty output difficult
to distinguish from routing or provider failure.

**Repair/acceptance:** capture child channel executions and timestamps, including
capability skips, queue rejection, actual start, duration and censoring. A query
whose channels are all excluded must not be counted as a provider attempt.
Preserve per-query versus per-channel counts without double-counting fallbacks.

### D14 — Funnel counters mix initial, cumulative and acquired scopes

**Owner:** [assembly](../../backend/application/research/assembly.py), API/renderer
counter labels. **Status:** current records + code.

Nike reports 22 initially found candidates but 27 cumulatively accepted candidates.
That can be valid with adaptive additions, but is not one monotonic funnel.
`deep_reads_count` uses successful read records, whereas actual attempts are
6/5/3/4 across the cases. Nike can therefore show zero deep reads despite three
failed attempts. Reused acquisitions and nested wrapper lookups have other scopes.

**Impact:** users/operators cannot infer what was attempted, acquired or newly
discovered from the headline counters alone. Query success is not body acquisition.

**Repair/acceptance:** explicitly name initial/cumulative discovery, scheduled/
started read attempts, successful captures, reused bodies and resolution subqueries.
Add cross-layer invariants with adaptive additions, failures and reused bodies;
never rewrite a real nonzero attempt count to zero because all reads failed.

### D15 — Resolution logs cannot explain rejected search results

**Owner:** [DeepReader._resolve_wrapper](../../backend/services/research/deep_reader.py).
**Status:** confirmed diagnostic-contract omission.

Saved resolver traces contain execution counts but not the three returned
candidate titles/URLs, token-match scores or per-candidate rejection reasons.
The failure is observable, but its exact result-quality/matching cause cannot
be reconstructed offline. This forces avoidable speculation or repeated traffic.

**Repair/acceptance:** retain a small bounded sanitized candidate/rejection list,
query/backend/deadline observations and selected publisher when present. Strip
credentials/private data and avoid storing whole search pages. A failed resolution
must be explainable from its saved capture with zero additional provider calls.

### D16 — Structural tests do not establish semantic acceptance

**Owner:** [frontend renderer tests](../../tests/frontend/test_unified_report_renderer.js),
[acquisition regressions](../../tests/unit/test_acquisition_followup_repairs.py),
[browser audit](../../scripts/audits/run_phase9_four_agent_browser_audit.py), reviewer.
**Status:** demonstrated validation gap, not a claim that existing tests are useless.

The prior full suite passed 1,474 tests and all 12 replay viewport states passed
their structural assertions while D06–D09 remained present. The replay checks
count/text retention, overflow and page errors; they do not adjudicate whether
LOW, an author name or a disagreement is warranted. Existing mocked resolver
tests cover matching/nonmatching fragments, not this complete multi-wrapper path.

**Repair/acceptance:** add semantic regression assertions for every defect here,
including missing assessment -> UNASSESSED, conflict retention, no headings as
contradictions, replacement reads and distinct-wrapper selection. Separately use
E6's reviewer-selected held-out cases; report wrong decisive verdicts, justified
abstentions, source relevance and passage entailment. More unit tests or words
must not substitute for independently reviewed accuracy.

### D17 — Current-state documentation points to older checkpoints

**Owner:** [documentation portal](../index.md), [current-state ledger](../CURRENT_STATE.md),
[AGENTS orientation](../../AGENTS.md). **Status:** confirmed at initial inspection;
partially mitigated by the dated portal banner added with this report, not fully
reconciled across existing metadata.

The portal's older “Latest checkpoint” text points to 2026-10-17 with a generation-429
snapshot, while newer 2026-10-18/19 handoffs record subsequent model verification,
deployment work and fix-branch checks. AGENTS also carries old milestone/count
metadata. Historical snapshots are valuable, but undated “latest” labels create
contradictory operational guidance.

**Repair/acceptance:** one explicitly dated current entry point linking the
actual checked-out branch/application/verification ledger. Preserve historical
records, label superseded status and distinguish local/main/live SHAs. Verify
relative links. Do not claim a provider is currently healthy from an old model
test or declare deployment complete from a local document.

## 5. External constraints and acceptance gaps — not new coding bugs

### X01 — Reddit rate limits and partial access

All eight main-query timeouts in E1 were started Reddit chains; backend logs also
show subreddit RSS 429s. Two NVIDIA link-submission records total only 68 words.
Neither universal blocking nor reliable platform access is established. Local
approval flags are not proof of provider authorization. Keep cooldown, bounded
requests and explicit access/depth states; do not bypass platform controls.

### X02 — Bounded captures do not guarantee full documents

Response caps, unsupported authentication, opaque wrappers, dynamic pages and
provider failures limit coverage. A primary-document label is not full-document
completeness. Podcast notes, video metadata, profiles, feed excerpts and repository
samples must retain their actual depth. Do not remove byte/SSRF limits to hide
this distinction. No new full 16-operation/52-operation live matrix was run here.

### A01 — Agent-specific research-quality gates remain open

| Agent | Established in this sample | Still needed |
| --- | --- | --- |
| Scout | Captured issuer financial PDFs and linked excerpts | Claim-specific amount/period/currency/basis reasoning, contradiction semantics, unseen tables and independent review |
| Trending | One article, minimal social submissions and linked observation | Independent narrative clustering, time-series observations and justified change/velocity claims |
| BrandShield | Honest zero-body acquisition failure | Captured relevant positive/negative incident bodies; distinguish allegation, report, enforcement and actual unauthorized offer |
| Personal Watch | Profile retained with conservative overall brief | Substantive sources for varied subjects; original quote comparison and reported identity-abuse context, not identity or media-forensics claims from profiles |

These broad entity inputs do not support a true/false accuracy score. The
`UNVERIFIED` findings are appropriately cautious; their presence is not an error
merely because they do not adjudicate a specific claim. Unsupported specialized
labels and misleading projections remain defects, however.

### A02 — Independent accuracy acceptance is not complete

E6 prepares 48 slots, 12 per agent. That is a reviewer packet, not 48 labeled,
executed or passed cases. Expected answers must be selected independently of the
implementer and frozen before tuning. Citation ID joins are necessary but cannot
establish entailment, relevance, independence or a justified verdict.

### H01 — Historical dossier corruption remains unresolved

E5 reports 55 malformed originals and 2,445 readable `LEGACY_UNSEALED` records,
with no cryptographically verified legacy records in that historical observation.
The 2026-10-18 read-only review still reported the 55 failures. This task did not
rescan or repair the archive, so these are dated counts, not a fresh inventory.

The isolated checkout's `OFFLINE_PERSISTENCE_PASS` does not include that absent
archive; its historical-archive result was NOT_VERIFIED. Recovery requires trusted
backups and owner direction. Preserve originals, hashes and uncertainty; never
fabricate missing evidence or re-seal corruption to obtain a passing validator.

### A03 — Production parity and actual rollback are not attested here

The preceding fix-branch application had reported hosted CI, but this report does
not check the current live Render SHA, Cloudflare frontend blobs, environment
overrides, durable volume or access configuration. A local 120s default does not
prove production uses it. Historical reader compatibility does not boot an old
application on deployed storage. Controlled staging rollback and storage recovery
remain separate acceptance tasks. E5 also documents that automatic SQLite-to-
Supabase reconciliation is not implemented; do not confuse replay with replication.

### A04 — Accessibility and browser breadth remain bounded

E1 replay covered Chromium at 320/390/1440px, with matching counts and no overflow
or uncaught page exceptions. It is not manual screen-reader, measured contrast,
cross-browser, real-device or full deployed accessibility acceptance. Four blocked
font loads and two harness 404 entries were disclosed; they are not established
production bugs and must not be silently called fixed.

### A05 — AI configuration and cost are a separate evidence boundary

AI-off standard testing is intentional, not the cause of wrapper-domain grouping,
missing replacement reads or false renderer defaults. No new model/key/account
test was run for this report. Earlier 404/429/prefix failures must not automatically
be called current after later handoff changes; equally, older model success does
not prove current runtime availability. Keep all optional advice within the shared
budget and do not use generative suggestions as factual evidence or verdicts.

## 6. Previously repaired or superseded issues

These should not be reintroduced into the open-defect count without a current
reproduction:

- Shared search-worker starvation: per-channel bulkheads and cooperative budgets
  are in the [repair checkpoint](../handoffs/2026-10-19_FOUR_PROMPT_REPAIR.md).
  The current initial queries all started; arbitrary-load/provider reliability
  is still not guaranteed by finite worker pools.
- Expensive synchronous doctor work: zero calls in E1's acquisition-critical
  paths. This does not reconstruct the exact old Lenovo 9.7s incident.
- The earlier 20–25s whole-investigation window: now 120s locally, with explicit
  overrides and finite transport/read bounds. Removing every timeout is unsafe
  and would not schedule replacement work or grant provider access.
- BrandShield's historical zero-source early return: E1 now shows its complete
  shared failure report and discovery cards. This does not establish threat quality.
- Old fabricated zero market-price displays, weak metadata promoted to findings
  and generic product-text false positives have dated remediation records. This
  report does not freshly certify every old case or claim those guarantees globally.
- Netlify removal and model changes have later handoffs. They are not reasons to
  restore obsolete paths or rerun paid AI probes for a documentation task.

## 7. Focused repair and verification sequence

1. **Correct false meaning first:** D06–D09 and D12. Missing risk must remain
   unassessed; preserve attribution; remove non-contradictions; normalize changes;
   fix the summary key. Use saved captures and offline regression tests.
2. **Restore useful specialist acquisition:** D01/D02/D03/D05/D15. Record resolver
   rejection reasons, separate transport/publisher identity and schedule finite
   task-related alternatives after failed reads. No fan-out explosion or weaker
   relevance/access checks.
3. **Improve planning and lifecycle truthfulness:** D04/D11/D13/D14. Preserve
   intent, accurately describe stopped work and count real starts/attempts.
4. **Polish source-backed output:** D10 plus case-linked uncertainty/next steps.
   Do not remove relevant evidence to make the interface shorter.
5. **Prove, rather than infer, quality:** D16 and A01/A02. Run deterministic
   saved-failure regressions, a small authorized live check, exact frontend replay,
   then independent held-out evaluation. Avoid repeated live runs for screenshots.
6. **Release gate:** D17, H01 and A03/A04. Align documentation, attest actual
   Cloudflare/Render versions, verify durable storage and rollback scope, disclose
   archive limits, then obtain publication authority. This report authorizes none.

Release acceptance requires useful task-relevant captures or explicit access
failure, passage-supported claims, honest uncertainty, consistent citations and
attribution, and semantic agreement between native/shared/frontend projections.
HTTP 200, elapsed time, retained word volume, CI success and visual layout alone
are insufficient.

## 8. Validation ledger and safe handoff

This documentation task inspected current code and existing saved responses/text
captures. It did not rerun full tests or repeat provider/browser investigations.
Do not present the following prior results as new executions:

| Earlier execution | Actual recorded result | What it does not establish |
| --- | --- | --- |
| E1 full offline suite | 1,474 passed in 67.16s, exit 0 | Research accuracy or production parity |
| E1 fast offline suite | 1,266 passed in 45.38s, exit 0 | Specialist positive-case acquisition |
| E1 nine Node frontend scripts | All exit 0 | Warranted LOW/author/disagreement semantics |
| E1 smoke/frozen/fatal lint | Passed, exit 0 | Live-provider health or comprehensive security |
| E1 rollback | OFFLINE_PERSISTENCE_PASS, exit 0 | Historical archive or actual deployed rollback |
| E1 exact-response browser replay | 12 states passed bounded checks | Full accessibility or research usefulness |
| E2 focused regressions | 18 passed in 1.20s, exit 0 | Multi-wrapper real-world acceptance |
| E2 selector/planner controls | Network-blocked synthetic reproduction, exit 0 | Accessible bodies or independent sources |

New document checks are recorded in the [report handoff](../handoffs/2026-10-19_CONSOLIDATED_DEFECT_REPORT_HANDOFF.md).
No immutable benchmarks, artifacts, research archives, historical dossiers,
scrapers, compatibility shims, runtime credentials or application implementations
were changed. Retain evidence and regression pointers when repairing individual
IDs; mark an item closed only with its acceptance test and dated observed result.
