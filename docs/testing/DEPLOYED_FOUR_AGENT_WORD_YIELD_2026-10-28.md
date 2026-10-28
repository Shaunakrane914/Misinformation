# Deployed four-agent word yield and Trending background — 2026-10-28

**Deployment verified; substantial useful output across all four agents is not
yet achieved.** Trending now displays permitted older information when current
evidence is limited. Personal Watch's sampled investigation still has no useful
published passages.

## Actual production observations

One ordinary DEEP request per agent, with no supplied article URLs or audit
retries, was run against deployed `24bf73d`. The Trending-only follow-up against
`ec5bef1` verifies the subsequently requested historical fallback. Other agents'
processing was unchanged by that follow-up; their providers were not called again.

| Agent / input | Raw article bodies | Raw article words | Qualified current/task sources | Published passage words | Quality assessment |
| --- | ---: | ---: | ---: | ---: | --- |
| Scout / Adobe | 7 | 7,933 | 2 | 603 | Financial reporting/analysis, both from one publisher; no independent filing-based adjudication established |
| BrandShield / Dyson | 8 | 12,300 | 3 | 353 | Historical 2020–2022 incident/warning coverage; no newly established active attacker or counterfeit seller |
| Trending / battery recycling, initial | 6 | 6,489 | 0 | 0 | Five articles require rights review; one is outside the 48-hour freshness window |
| Personal Watch / Mary Barra | 2 | 1,855 | 0 | 0 | Two 2014 executive-speculation articles; no relevant statement or identity-threat passage |
| Trending / battery recycling, post-fix | 4 | 3,170 | 0 current; 4 background | **580 background** | Four dated older articles, one publisher; not fresh trend evidence or independent corroboration |

Raw article words are captured text volume, not verified facts or published
evidence. Published words count the report's passage collection, including pages
available through the workbench paginator. Background words are counted
separately from current evidence and findings. No 20× improvement is claimed.

Initial request times: 72.44 /55.07 /86.79 /75.26 seconds. Post-fix Trending:
106.19 seconds, 69 native HTTP admissions, 14 reads, one completed result event
and no SSE error events. The original four used 58/66/79/87 native admissions;
each was within the 120-admission cap. All hit the lower effective shared 14-read
budget despite selecting DEEP; this configured limit was not silently increased.

## What the fallback actually changes

The shared harvesting pipeline inspects all retained publisher captures. When
fewer than two current sources qualify, it builds a separate historical reading
projection from actual article bodies. Relevance, passage quality, original
publication and excerpt-permission checks remain. Missing/future dates, indexes,
off-topic material and rights-blocked text cannot fill the section. Source IDs,
authors, dates, links and body hashes are preserved. The original rejection as
current evidence is unchanged.

The fresh post-fix request autonomously acquired and displayed older reports on
Colorado/California battery bills, Illinois collection programs, Rice University
recycling research and Blue Whale operations. They are dated January–June 2026
and explicitly labeled **OLDER BACKGROUND**. All four are from Resource
Recycling: four articles do not establish four independent publishers. No URL
was supplied to force this outcome.

`RelevanceGate.evaluate_item` has an explicit historical-context mode used only
on detached background projections. `trending_background.historical_background`
performs the bounded selection. `run_harvest_pipeline`, `ReportBuilder` and the
shared renderer carry that separate data to the frontend. Current findings,
current source totals and velocity calculations do not consume it.

## Deployment and frontend verification

- Final application: `ec5bef19ff701d62fc10546a4a9bcc7b569f95f8`.
- Render: `dep-dbgn2i7b9u1s7393pcgg`, live `2026-10-28T03:54:10Z`.
- Cloudflare: <https://c9d0260f.aegis-protocol-110.pages.dev>;
  public site <https://aegis-protocol-110.pages.dev>.
- Nine checked public frontend files exactly match the application Git bytes.
  Public health returned 200 and allowed the exact frontend origin.
- [Candidate CI](https://github.com/Shaunakrane914/Misinformation/actions/runs/40628641314):
  all five jobs passed; full **2,811**, fast Python 3.12 **2,603**. Main CI also
  passed. Focused background/freshness/golden tests: **34 passed**; frontend
  escape/workbench controls and fatal lint passed.
- Exact saved production results were replayed through actual deployed page
  buttons at 390/1440px. All eight states rendered matching finding/first-page
  passage counts, with no horizontal overflow or uncaught page exceptions.
  Trending's DOM contained **four background sources and exactly 580 quoted
  words** at both widths. Focused captures were visually inspected. Browser
  replay validates rendering, not fresh acquisition, live progress or accuracy;
  API/health responses were explicit replay stubs and no research was repeated.

The first browser harness had health/CORS stub errors, followed by an observed
host/network interruption. Those attempts are retained in temp logs and not
reported as passing application checks. An initial local measurement formatter
also treated a query-record counter as a list; intact saved responses were
remeasured offline. Neither instrumentation correction repeated provider calls.

## Remaining limits

Personal Watch needs better statement/incident discovery. Scout needs primary
financial sources and claim adjudication. BrandShield needs recent incident
coverage beyond this historical sample. Trending still needs current permitted
sources and repeated observations before claiming virality. More registered
sites alone do not establish availability, relevance or display rights.

AI runtime/search flags are enabled with a three-call/day cap, but production's
required persistent `AEGIS_AI_POLICY_DB` is absent. The weak cases report
`AdvisoryPolicyError`; no successful generation or provider usage was observed.
The durable-budget guard was preserved, and no key, model or access flag was
substituted to manufacture success. Historical archive recovery and deployed
rollback remain unverified.

## Evidence

[Initial measurements](evidence/2026-10-28_deployment_yield/initial-four-agent-measurements.json),
[post-fix live result measurements](evidence/2026-10-28_deployment_yield/trending-background-live.json),
[exact deployment attestation](evidence/2026-10-28_deployment_yield/final-deployed-attestation.json),
[browser measurements](evidence/2026-10-28_deployment_yield/final-browser-replay.json),
[mobile capture](evidence/2026-10-28_deployment_yield/trending-background-390.png),
[desktop capture](evidence/2026-10-28_deployment_yield/trending-background-1440.png),
[implementation handoff](../handoffs/2026-10-28_ACQUISITION_DEPLOYMENT_AND_YIELD.md).

Full native responses, SSE, temporary audit scripts and logs remain in system-temp
basename `aegis-rollout-20261028-cy9uayz_`. Protected historical records and the
original root/release working changes were preserved. Source changes were
committed, pushed, normally promoted and deployed; this closeout is documentation
only. This is an engineering observation report, not independent truth acceptance.
