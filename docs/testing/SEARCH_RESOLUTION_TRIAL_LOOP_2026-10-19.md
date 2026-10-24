# Search resolution and interpretation trial loop — 2026-10-19

## Outcome and authority

**Four focused corrections implemented. Automatic research remains unaccepted.**
The user requested iterative prompt → inspect → fix → rerun work. This is a bounded
engineering loop, not an unattended self-modifying agent or unlimited retries.

Branch `fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, plus the preserved earlier uncommitted
repairs. **Uncommitted/unpushed; no merge/deployment, secret/access-gate changes or
production configuration edits. Zero backend live AI generation calls.**

[Handoff](../handoffs/2026-10-19_SEARCH_RESOLUTION_TRIAL_LOOP.md) and
[selected proof](evidence/2026-10-19_search_resolution_trial/README.md).

## Measured iterations

The [preceding four-input audit](FOUR_RANDOM_PROMPT_RECHECK_2026-10-19.md) supplied
the failures. Fixed inputs were retained; no gate was relaxed to get a green count.

| Stage | Actual action | Result and interpretation |
| --- | --- | --- |
| Offline red controls | Nonempty unrelated search, inline markup, topic variants | Three intended failures reproduced after correcting a test-only resolver method typo |
| Search/topic repair | Correct fallback eligibility, word boundaries and non-person topic matching | Regression controls pass; not proof of upstream availability |
| Live rerun 1 | BrandShield / LEGO | 43.80s; zero bodies/findings; article resolutions still fail |
| Small direct probes | Bing plain/quoted, Yahoo, Bing News RSS, observed Google wrapper, DuckDuckGo HTML | Full Bing query echoed but first-word results dominate; Yahoo 500; news empty; wrapper no publisher link; alternative 202/empty |
| Live rerun 2 | Trending / quantum computing | 36.78s; zero bodies/findings; no surname error, but nothing fresh/relevant qualified |
| Live rerun 2 | Personal Watch / Lisa Su | 30.76s; one ten-word profile; zero findings |
| Explicit-source control | BrandShield / LEGO, externally located actual publisher URL supplied | 16.54s; one article, 666 words / 4.062 decimal KB; **not automatic discovery success** |
| Interpretation repair | Reprocess the exact captured article offline | Zero active threats, one informational SAFETY_ADVISORY; no counterfeit/impersonation entries or takedown instruction |
| Browser replay | Corrected saved BrandShield SSE | Three states at 320/390/1440px pass bounded rendering checks |

Four real local investigation POSTs occurred: three automatic cases and one
explicit-source control. Six standalone top-level public HTTP probe attempts were
made; normal searches, fallbacks and redirects are additional requests, not a
measured complete HTTP denominator. Two external web-research lookups checked
official documentation and located the publisher URL. They are **not** represented
as backend scraper discoveries. One inline diagnostic failed shell quoting before
any network request; the reusable script replaced it. No AI-key/model/quota probe.

## Defects and implementation

### Nonempty irrelevant results suppressed fallback

[NativeRouter._execute_web_search](../../backend/infrastructure/acquisition/routing/router.py)
previously used result presence and a few abuse terms to decide whether to try
the existing secondary search. An unrelated page containing “counterfeit” could
suppress it while failing the article-title join.

For `publisher_url_resolution`, the router now evaluates the same 75% headline
join as [DeepReader](../../backend/services/research/deep_reader.py), invokes the
existing Yahoo fallback once on mismatch and ranks observed title matches first.
The [shared helper](../../backend/infrastructure/acquisition/adapters/web/search_matching.py)
is lexical URL discovery, not claim support. Matching primary results do not add
a secondary request. Deadlines, byte limits, SSRF and protected reads remain.
No new runtime search provider/channel or unlimited retry chain was introduced.
Yahoo's measured 500 explains why this correction alone did not resolve the
sampled publisher URLs; its general availability is not certified.

### Inline markup merged title words

Bing/Yahoo parsers used `get_text(strip=True)`, joining words across inline tags,
for example `ExampleCocounterfeit`. Titles/snippets now use a space separator.
Live post-fix traces retain readable boundaries; they may still be unrelated.

### Topics entered person-name logic

[EntityResolver](../../backend/services/research/entity_resolver.py) now treats
general/topic/concept/product targets as multi-token subjects, not first-name/
surname pairs. Conservative inflection matching allows computing/computers, but
still requires all meaningful tokens or a strong explicit alias. An unrelated
“Quantum data storage” company remains rejected; person/company paths stay intact.

The new quantum-computing raw set contains 3 static references, 7 insufficient
multi-token matches and 10 stale items. The earlier set had 8 surname-ambiguity
rejections and 9 stale items. These are separate live observations, not identical
provider results. At least one topic variant now reaches freshness evaluation;
there is still no eligible current trend evidence. The 48-hour window is unchanged.

### Scam-awareness article became a counterfeit listing

The real [Bitdefender article](https://www.bitdefender.com/en-us/blog/hotforsecurity/international-lego-day-how-lego-scams-target-families-online)
was located externally and supplied explicitly to the normal local agent route.
It yielded 666 retained words. Two legacy keyword engines classified educational
text as counterfeit/listing signals, including a marketplace takedown instruction.
Calling that suspicion “unverified” did not correct the source/actor confusion.

[BrandShield assessment](../../backend/agents/brandshield/assessment.py) now recognizes
conservative educational-title patterns and normalizes these records to
`SAFETY_ADVISORY` / `REPORTS_SAFETY_ADVICE`: informational severity, `is_threat=false`,
no actor URL, no heuristic probability and no listing/takedown assertion. The
source, raw text and IDs remain inspectable. Duplicate legacy advisory signals
collapse. Actual enforcement reporting takes precedence; an explicit regression
preserves it. Existing complaint and unauthorized-offer controls still pass.

Legacy description and summary agree so an adapter cannot restore the accusation.
[ReportBuilder](../../backend/services/report_builder.py) replaces generic takedown
next steps for advice-only cases with source review and obtaining a specific
suspected listing/account/URL. Current saved-byte output has zero active threats,
empty counterfeit/impersonation arrays and one advisory, with the same captured
666 words. Two shared display strings are an unresolved request proposition and
the advice observation—not two verified threats. The source-only request/URL still
dominates parts of the UI; instruction-versus-proposition parsing remains a known
presentation/claim-classification limitation.

## Verification and failed attempts

New [seven controls](../../tests/unit/test_search_resolution_iteration.py) cover
search fallback, whitespace, topic/person separation, advisory deduplication and
retained enforcement. Focused run with BrandShield/research-quality tests:
**28 passed / 0.36s, exit 0**.

| Command/check | Actual final result |
| --- | --- |
| `python -m pytest tests/ -q` | Exit 0; **1,505 passed / 44.71s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **1,297 passed / 27.29s** |
| Fatal flake8 command from AGENTS | Exit 0, zero fatal findings |
| All nine Node scripts | Exit 0; no frontend code changed this task |
| Release smoke with fresh output | Exit 0; OFFLINE_SMOKE_PASS, final application |
| Rollback validator with fresh output | Exit 0; OFFLINE_PERSISTENCE_PASS; historical archive/deployed rollback NOT_VERIFIED |
| Frozen benchmark verifier | Exit 0; hashes match |
| Saved-byte reprocessing / browser replay | Exit 0 each; no further provider acquisition |

Initial three red regressions and the later advisory regression failed as intended.
A test-only wrong resolver method and nonexistent requested test path were
corrected; the latter collected no tests, not an application failure. Earlier
1,503-test runs predate the advisory controls and are not the final count.

Final application fingerprint:
`364663787ce194cc6c804fdc6980023216aa6f91158f348e485b30384e491073`.
Terminal saved-byte reprocessing and browser replay recorded unchanged application
bytes. Three viewport states preserve report/cards/text with no overflow or
uncaught page error; inspection opens by keyboard at all widths. A focused mobile
capture was viewed, and rendered text confirms SAFETY_ADVISORY and review-only
next steps. Readiness is stubbed; APIs/fonts blocked, resource errors disclosed.
No new four-agent browser matrix, production/CI, screen-reader/contrast/axe or
independent accuracy acceptance is claimed. Debugging, Python-testing and E2E
skills guided controlled failures and exact-source replay; no private reasoning
transcript is included.

## Next-loop procedure and remaining limits

Keep a fixed prompt and fresh isolated evidence directory. Reproduce its failing
boundary offline, make a general correction, reprocess saved bytes, then run one
affected live case only when upstream observation is needed. Evaluate actual
passages/attribution, not HTTP status or word volume. Replay the exact understood
result in the frontend. Do not weaken matching, guess article URLs, bypass a
challenge or endlessly retry unchanged provider failures.

[probe_public_search.py](../../scripts/audits/probe_public_search.py) supplies bounded
live-opt-in diagnostics: default plain/quoted Bing plus Yahoo (three top-level
fetches), or single modes for Bing News, an observed public wrapper, or the
official [DuckDuckGo non-JavaScript surface](https://duckduckgo.com/duckduckgo-help-pages/features/non-javascript).
The alternative's 202/empty result was not bypassed or integrated into runtime.
Fresh output, one attempt per probe, normal safe HTTP, no credentials/app/AI.
Exit 0 records observations; it is not a source-health or research PASS.

Reliable automatic discovery still needs an evaluated approved search or publisher
feed strategy. A credentialed integration may need owner configuration/cost choices;
none were created here. Useful issuer documents, personal statements, fresh trend
evidence, independent accuracy, existing telemetry/duplicate defects and historical
55-file corruption remain incomplete. Full raw source/HTML/events/logs and temporary
dossiers remain in a new `aegis-search-iteration-20261019-*` temp tree; no protected
history, frozen dataset or tracked benchmark proof was overwritten.
