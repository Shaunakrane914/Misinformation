# Post-fix live demonstration — 2026-10-25

**Research-quality demonstration: NOT MET. Rendered-report checks: PASS within the scope below.**
User requested a demonstration after the [pipeline repairs](PIPELINE_REVIEW_REPAIRS_AND_BOUNDED_PILOT_2026-10-25.md).
Two new normal query-based local investigations ran once each on the current uncommitted code at
`release/specialist-task-20261024`, HEAD `7ad13a5`. No application code or configuration was changed
during this check. No supplied source URLs or saved bodies were injected into acquisition.

## Actual observations

| Case | Seconds | Read slots | Native HTTP admissions | Article bodies | Qualified sources | Frontend words |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Trending / battery recycling | 37.26 | 9 | 71 | 5 | 0 | 0 |
| Personal Watch / Mary Barra | 43.25 | 17 | 84 | 2 | 2 | 176 |

The actual Personal Watch duration is retained in the machine-readable measurement record; all
durations are local observations, not production latency promises. Bounds per case: 240 seconds,
24 reads, 120 native admissions. Total **155 admissions**, no whole-investigation retry, no paid
reader, no model generation/capability probe, no production persistence or deployment. AI remains
configured locally; this comparison deliberately used the native-only runner. Runner exit 0.

Application fingerprint remained unchanged throughout:
`df8e060ae054ad6c55793287bc1be5b25760dc79a3b68617ea151fff292650b1`.

## Trending: the known candidate still loses its read opportunity

Eighteen queries returned 17 successful query records and one failure. Success does not imply
useful articles: 24 candidate URLs were retained. Five acquired article bodies had publication
dates from 2018 through July 2026, all outside the strict 48-hour window; rejecting them is correct.

The prior premature `FUTILITY_STOP` did **not** recur. This run stopped with `NO_FURTHER_USEFUL_WORK`,
while 15 candidates were marked `HOST_READ_BUDGET_EXHAUSTED`. The publisher's eight-read allowance
was spent on its homepage, search index, comments feed and five older articles. The ECS meeting
article was automatically discovered with its actual observed headline, but remained unread for
that same host-budget reason.

For this known article, the first actual loss is **ranking/per-host read allocation**, before body
acquisition. Its publication date and accessibility were not re-established live because it was
not read. The earlier genuine saved fixture remains offline evidence only. The presence of a
correctly observed URL and headline does not establish an acquired source or a successful fix.

Next implementation priority: allocate the existing publisher budget more effectively between
date-bearing feed discovery, substantive articles and low-yield indexes/comments. Do not simply
increase the host cap, mark undated pages fresh or weaken qualification to claim success.

## Personal Watch: more text, still insufficient task evidence

The two retained sources are:

- A September 2021 Economic Times report containing an attributed Mary Barra statement:
  **114 displayed words**, historical context.
- A Deadline Detroit opinion/criticism article: **62 displayed words**, publication date unverified,
  labeled `UNVERIFIED_ALLEGATION`. This is not an additional verified public statement, identity
  confirmation or impersonation finding.

Two qualified text records therefore do not demonstrate the agent's intended job is complete.
Its previous 114-word historical-only result increased to 176 words, but current, relevant,
attributed statement/threat coverage remains inadequate.

## Exact source-to-frontend check

Both complete native responses were saved, then rendered through the actual shared renderer on the
native agent pages at **320, 390 and 1440 px**. Six states passed keyboard pagination, filters,
zero horizontal overflow and zero uncaught page exceptions. External browser traffic was blocked;
there was no second provider investigation. Both mobile workbench captures were visually inspected.

Personal Watch's two passages matched their raw source identities, SHA-256 hashes and exact body
slices. Trending honestly displayed an empty workbench. No display-budget omissions occurred: the
frontend is exposing these weak API results rather than hiding acquired qualifying evidence.
This is saved-report rendering, not fresh browser form submission, deployed-site verification or
screen-reader/contrast certification.

[Measurements](evidence/2026-10-25_postfix_demonstration/measurements.json) ·
[Browser checks](evidence/2026-10-25_postfix_demonstration/browser-measurements.json) ·
[Trending screenshot](evidence/2026-10-25_postfix_demonstration/trending-390.png) ·
[Personal Watch screenshot](evidence/2026-10-25_postfix_demonstration/personal_watch-390.png).

The prior 2,556 full /2,348 fast passing suites are recorded in the repair handoff; they were not
rerun for this read-only demonstration. A passing HTTP response and rendered page do not establish
research success. No new independent claim evaluation or hosted CI was performed. Historical
dossiers, frozen benchmarks, research and artifacts were preserved. No commit, push, merge or deploy.

Full native responses, event streams and isolated logs use fresh system-temp basename
`aegis-postfix-demonstration-9tpbd3iv`; selected sanitized evidence is durable above. These two
demonstration investigations are complete; no unreported retries or extra source sweeps occurred.
