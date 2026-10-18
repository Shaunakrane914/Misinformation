# Terminal output and AI-cost review — 2026-10-18

**Research acceptance: NOT COMPLETE. Frontend acceptance: PARTIAL.**
This checkpoint improves output integrity and cost controls, not source access
or upstream quota. Changes are local/uncommitted; no deployment or hosted CI.

## What changed

- BrandShield's compatibility loop no longer converts unmatched merchandising
  into “Genuine Issue” findings. Background evidence/IDs remain inspectable.
  `safe_count=0` is not a safety verdict; `safety_assessment=NOT_ESTABLISHED`.
- Personal Watch skips AI threat synthesis for profile/metadata-only input.
  Specific public deepfake/impersonation discovery precedes generic news.
  Specialist reads prioritize task-bearing text, without erasing other leads.
- Quoted-name search rejects first-name-only mismatches before using the existing
  secondary search. This does not fix unavailable publisher-body resolution.
- Specialist summaries now state capture/profile counts, discovery-only leads,
  failed reads and uncertainty. Next actions refer to actual discovered reports
  rather than assuming that a takedown/accusation is justified. These counts and
  keyword-derived task-text candidates are not entailment or calibrated risk.
- Advisory calls are pinned to `gemini-2.5-flash-lite`: one attempt, 320 maximum
  output tokens, two-second deadline, no larger-model fallback. Passage advice
  includes at most four paragraphs / 2,400 text characters, each at most 1,200;
  planning advice bounds entity/claim text to 200/1,000 characters. Raw captured
  evidence is not shortened to fit the AI prompt. Other synthesis configuration
  remains separate; this is not a claim that all existing LLM features changed.
- 429 responses stop the immediate model/key waterfall and apply a process-local
  provider cooldown. Separate processes/in-flight work are not a shared budget.
  Terminal and browser audit runners exclude AI credentials by default. Their
  `--allow-live-ai` flag is a separate opt-in, not an instruction to enable it.

## Real terminal matrix, then exact frontend replay

One normal local ASGI SSE request per input, isolated fresh DB/dossiers, no
background ingestion, notification targets or remote persistence. Live scraping
remained bounded by existing access/transport policies. **AI credentials were
excluded and mocks disabled.** No live AI generation was used by these twelve
requests. The browser then replayed their exact SSE results through real page
buttons and renderers, without reacquiring providers.

KB is UTF-8 bytes / 1,000 of one native retained content/snippet per record;
words are whitespace-delimited. Metadata/profiles/catalogs/indexes are included
in these capture counts but are not accepted evidence of the agent's objective.
Repeated sources across cases are not a unique research corpus.

| Agent / input | Records | Words | KB | Seconds | Shared finding strings |
|---|---:|---:|---:|---:|---:|
| Scout / TATAMOTORS.NS | 2 | 666 | 5.434 | 15.14 | 2 |
| Scout / INFY.NS | 6 | 2,331 | 17.207 | 25.56 | 4 |
| Scout / AAPL | 7 | 531 | 5.899 | 26.21 | 2 |
| Trending / OpenAI | 1 | 1,463 | 9.732 | 12.00 | 1 |
| Trending / NVIDIA | 4 | 4,795 | 31.780 | 14.38 | 3 |
| Trending / electric vehicles | 2 | 2,079 | 12.506 | 12.70 | 2 |
| BrandShield / Nike | 2 | 662 | 3.788 | 15.16 | 0 |
| BrandShield / Apple | 2 | 319 | 1.837 | 14.38 | 0 |
| BrandShield / Tata Motors | 1 | 444 | 3.009 | 13.86 | 0 |
| Personal Watch / Sam Altman | 1 | 18 | 0.101 | 13.77 | 0 |
| Personal Watch / Tim Cook | 1 | 8 | 0.059 | 13.28 | 0 |
| Personal Watch / Satya Nadella | 1 | 10 | 0.073 | 13.26 | 0 |

Total **30 retained records / 13,326 words / 91.425 KB**, not thirty independently
verified sources. No zero-record case does **not** mean zero insufficient cases.
The three Personal Watch cases remain profile-only. Brand captures remain
background material, now correctly excluded from findings. All six specialist
reports explicitly state insufficient evidence. Financial/Trending excerpts are
still UNVERIFIED; generic company assertions do not establish virality.

All twelve requests: HTTP 200, result event, no SSE error. Replay: 24 states at
390/1440px, matching finding/source/discovery counts, no missing finding text in
the DOM, no document overflow or uncaught page exceptions. Source inspection
keyboard controls passed where present. Eighteen console resource errors remain
recorded; external fonts were intentionally blocked. These are not clean-console,
screen-reader, contrast, axe, cross-browser or production acceptance claims.

All twelve mobile report captures were inspected. **Sam Altman shows partial
paint/text gaps; a focused exact-payload recheck again showed partial mobile
text and blank desktop cards despite populated DOM.** This is unresolved rendered
output, not a successful visual check or a proven data-loss bug. Do not dismiss
it as a screenshot-only issue without isolating the browser/compositor/styles.
No extra provider request was made for the recheck. Other selected captures
show the new summaries and retained inspections; screenshots are evidence, not
mockups. Scout also still projects seven unresolved index/disclosure labels into
Key Findings across its three cases; that remaining presentation/assembly issue
is not silently declared fixed.

## Low-budget AI check, separately authorized

Earlier diagnostic: model-list 200, generation 429 with allowlisted
`DAILY_QUOTA_EXHAUSTED`, retry delay 23,023 seconds. This was not a key-invalidity
diagnosis. After the user explicitly authorized using the potentially refreshed
key, the diagnostic reread `.env` and made **one** Flash-Lite generation attempt:
96 output-token cap, strict model, one attempt, two-second deadline, model-list
request skipped. It returned UNAVAILABLE / RuntimeError, with no HTTP status or
successful token-usage result captured. **Do not infer that it was another 429,
that the key was invalid, or that generation succeeded.** No retry/model switch.
The subsequent diagnostic code improves safe status/timeout extraction for a
future authorized run; it was not rerun to improve this result.

No credential values were printed, copied to proof, committed or edited. Existing
server configuration was not changed. Changing the local advisory default does
not deploy a production setting or prove that upstream quotas reset.

## Offline validation and remaining work

- Full: **1,375 passed, exit 0, 45.77s**; fast: **1,167 passed, exit 0, 23.99s**.
- All eight Node frontend scripts exit 0; fatal Flake8 zero, exit 0.
- Smoke / rollback / frozen validator exit 0. Historical archive and deployed
  rollback remain NOT_VERIFIED in this worktree. Protected data unchanged.
- Earlier failures were recorded: old retry-success expectation; three golden
  catalog-as-finding count expectations; a wall-clock deadline control failing
  once during concurrent checks (its 28-test file then passed); and a legacy
  “Nominal” summary assertion despite no body. Golden JSON remained untouched.
  Tests now explicitly assert the intended semantic changes, not regenerated data.
- Acquisition/read/brief tests and cost-control tests are offline mocks, not
  evidence of provider generation or successful original-publisher acquisition.

Next priorities: reliable authorized original-publisher resolution; relevant
brand/identity incident bodies; isolate the Sam rendering failure; move Scout
unresolved leads out of findings without losing their inspection/citations.
Only then reassess specialist research quality. Do not repeat full AI-enabled
matrices to solve transport or rendering problems.

[Measurements and selected screenshots](evidence/2026-10-18_terminal_quality/README.md)
· [Handoff and reproducible commands](../handoffs/2026-10-18_TERMINAL_QUALITY_CLOSEOUT.md).
