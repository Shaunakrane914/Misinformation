# Scraper repair and bounded native strength check — 2026-10-23

## Decision

**Reviewed repairs implemented; broad research acceptance remains PARTIAL.**
Firecrawl extraction/transport, conservative financial interpretation and unsafe
lead-based discovery stopping were repaired. Huginn is not needed or configured
for this milestone; its routes are disabled by default and its implementation is
not accepted. Do not deploy or claim an entirely green regression suite.

Four newly authorized, AI-disabled native investigations completed once each.
They acquired **12 article bodies / 11,952 words / 80.994 decimal KB**, but only
Adobe produced code-qualified evidence. Three empty specialist reports are not
proof of absent public information. The pipeline still needs better accessible
article resolution, task-specific selection and temporal coverage.

Worktree: `.scratch/phase9-remediation-20261016`; actual branch
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f` plus inherited dirty implementation.
No commit, push, merge, deployment, secret edit or access-flag change.

[Selected measurements and captured public URLs](evidence/2026-10-23_scraper_strength/measurements.json)
record the original native observations. Application hash was stable throughout
the batch: `7ef5c2b36683729fd53736a614a9edbd46748c2506ecd94d5140420722dc8410`.

## Implementation and reasoning

| Owner | Correction and boundary |
| --- | --- |
| [FirecrawlAdapter](../../backend/infrastructure/acquisition/adapters/web/firecrawl.py) | Fix missing imports; bounded raw capture and exact returned text; optional observed HTML uses the existing semantic extractor rather than treating long Markdown as an article. No discovery timestamp substituted for publication, no automatic primary-source label, no completeness claim based on word count. |
| [Shared HTTP transport](../../backend/infrastructure/acquisition/network/http.py) | Add `post_public_http`: same public numeric-address pinning, TLS, disabled environment proxies, response-size checks, deadline streams and shared admissions as GET. Exactly one POST attempt and zero followed redirects; oversized responses fail instead of silently truncating. |
| [Reader fallback](../../backend/infrastructure/acquisition/adapters/web/jina.py) | Native/alternate reader chain respects the original deadline; per-transmission caps remain. Explicit denials, challenges, SSRF blocks, throttles and exhausted budgets stop alternates. Typed transient native failures may reach the configured fallback. |
| [Firecrawl configuration](../../.env.example) | Public HTTPS endpoint required. `FIRECRAWL_API_BASE_URL` is canonical; `FIRECRAWL_BASE_URL` remains an alias. Configured status is unverified, not a live-health claim. Background remote crawl-job submission fails closed because its execution/credit use would outlive this investigation's bounds. Private/localhost bypasses were not added. |
| [Financial context](../../backend/services/research/financial_context.py) | Percentages/year labels do not become monetary amounts. Explicit currency/scale, original spans and comparative-baseline roles are retained; Decimal arithmetic precedes compatible numeric output. Bare `$` does not imply USD. |
| Same financial helper | Form/report year alone cannot establish an issuer's fiscal quarter. Exact fiscal metadata or an explicitly matching period-end date is required; two-digit years stay ambiguous. Even a period match leaves financial figures `UNVERIFIED_ASSERTION`. Amount/issuer/filing-content adjudication is not implemented by this metadata helper. |
| [HarvestingEngine.run](../../backend/services/research/harvesting.py) | Two matching publisher headlines no longer end discovery before any bodies are acquired. Existing query, concurrency, host, byte, HTTP and total deadlines remain bounded. This conservative repair forgoes the unproven early-exit speedup; it is not an interleaved-reading architecture rewrite. |
| [API registry](../../backend/api/__init__.py) | Do not import/initialize/register Huginn unless explicitly enabled and configured. No monitoring service is required for the four agents. Its deeper authentication, provenance, deduplication and retention issues remain deferred; do not enable it from this report. |
| [Offline isolation](../../scripts/validation/isolated_runtime.py), [pytest setup](../../tests/conftest.py), [terminal runner](../../scripts/audits/run_terminal_agent_quality.py) | Blank optional paid-reader credentials during normal tests/native audits; isolate optional storage in temp directories. The live batch cannot inherit paid Firecrawl access from the parent shell. |

No scraper/shim was removed, no source truth/relevance/freshness gate was weakened,
and no benchmark labels or historical source captures were modified. No new
search provider, proxy, CAPTCHA handling, paywall bypass or model call was added.
Remote Firecrawl behavior, account limits and provider compatibility remain
**live-unverified**: its repaired transport and normalization have offline proof.

## Actual checks

| Command/scope | Result |
| --- | --- |
| Six focused files: new repair controls, Firecrawl, staged queries, financial reconciliation/context, native bounded HTTP | Exit 0: **88 passed / 2.94s** |
| `python -m pytest tests/ -q --tb=short -p no:cacheprovider` | Exit 1: **2,018 passed, 1 failed / 82.49s** |
| `python -m pytest tests/unit tests/chaos tests/security -q --tb=short -p no:cacheprovider` | Exit 1: **1,810 passed, 1 failed / 65.77s** |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0: zero fatal findings |
| Every `tests/frontend/test_*.js` via Node | All nine scripts exited 0; simulated DOM/contracts, not a new browser audit |
| `python scripts/validate_release_candidate_smoke.py` | Exit 0: `OFFLINE_SMOKE_PASS` |
| `python scripts/validate_rollback_compatibility.py` | Exit 0: `OFFLINE_PERSISTENCE_PASS`; original historical archive and deployed rollback `NOT_VERIFIED` |
| `python scripts/validation/verify_frozen_benchmarks.py` | Exit 0: hashes match |
| Protected tracked diff / whitespace | Empty protected-path diff; `git diff --check` exit 0 |
| Four-case native terminal runner | Exit 0: four result events, no SSE errors, stable application bytes, zero AI reservations/observations |

The sole final failure in both Python gates is
`tests/unit/test_huginn_monitoring.py::test_huginn_inject_into_raw_pool`.
Its duplicate marker is lost by the optional scaffold. It was **not skipped,
xfail-marked, relabeled PASS or repaired outside the requested Huginn boundary**.
The optional router test now explicitly constructs its own app rather than
assuming that the normal application enables an unused monitoring service.

Earlier runs are not concealed: review reproduced 18 passes/5 failures; the
first repair full run had 2,015 passes/2 failures (including the old router
expectation). The final 27 new adversarial controls include a real local reader
over synthetic responses: two blocked first-wave leads, then an accessible
second-wave body. These tests are offline controls, not live source recall proof.

## Live method and accounting

Authorized subjects: Scout/Adobe, BrandShield/Dyson, Trending/battery recycling,
Personal Watch/Mary Barra. One normal local SSE request each; no supplied URLs,
audit retries, paid Firecrawl, model-capability probes, generation or deployment.
DEEP ceiling reduced to **180 seconds, 16 reads, 80 native HTTP admissions per
case**. Temporary SQLite/dossiers, background ingestion off, credentials for
notifications/cloud writes removed. No code changes during acquisition.

Recorded command (authorization **consumed**, not permission for another run):

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file <server-env> --output-dir <new-temp-directory> --research-profile DEEP --timeout-seconds 180 --max-deep-reads 16 --max-http-admissions 80 --case scout:Adobe --case brandshield:Dyson --case "trending:battery recycling" --case "personal_watch:Mary Barra"
```

Raw bodies, responses, logs and fresh isolated dossiers remain under system-temp
basename `aegis-native-strength-22672d05ff0849d19830f006ba744ae2`. Temp storage may
expire. Durable selected measurements exclude body text and credentials.
The existing read-only `summarize_raw_harvest.py` also produced a fresh temp JSON;
neither it nor this measurement extraction performs provider requests.

Words are whitespace-delimited retained source tokens, not verified facts.
KB is UTF-8 bytes / 1,000, excluding JSON metadata. Code-qualified excerpt words
are a selected subset, not manually adjudicated useful information. Host counts
do not establish independent reporting. Native admissions may fail before
transmission and include redirects/retries; rejected reservations are counted
separately. These are not complete remote HTTP or billing counts.

## Per-case acquisition strength

| Agent / input | Seconds | Discovered / eligible leads | Read attempts / captures | Article bodies | Article words / KB | Code-qualified sources / excerpt words | Native HTTP admissions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Scout / Adobe | 34.73 | 35 / 34 | 16 / 10 | 9 | 9,460 / 63.260 | 9 / 420 | 65 |
| BrandShield / Dyson | 40.56 | 10 / 10 | 8 / 4 | 0 | 0 / 0 | 0 / 0 | 79 |
| Trending / battery recycling | 35.21 | 36 / 36 | 12 / 7 | 2 | 2,008 / 14.725 | 0 / 0 | 80 |
| Personal Watch / Mary Barra | 27.11 | 16 / 16 | 6 / 1 | 1 | 484 / 3.009 | 0 / 0 | 73 |

Totals: 42 read attempts, 22 captures, 12 article bodies, 11,952 article words.
The full raw pool retained 24,000 words, including navigation, homepages, indexes
and unqualified/background material. Only Adobe's nine sources reach native
evidence display. **Mary Barra did acquire a 484-word body internally**; a zero
native source count must not be mistaken for zero captured bytes.

This is not a valid word-count increase comparison with the October 21 matrix:
subjects/budgets/provider observations differ. It measures current bounded yield,
not a controlled before/after quality improvement or all recovered operations.

### Website-level retained captures

Rows combine captures on the same observed publisher host within a case.
Qualified means the pipeline's decision, **not** independent correctness.

| Case / host | Retained words / KB | Captured structure / qualification |
| --- | ---: | --- |
| Adobe / marketscreener.com | 1,543 / 12.005 | Article; code-qualified |
| Adobe / theglobeandmail.com | 1,154 / 7.437 | Article; code-qualified |
| Adobe / techtimes.com | 1,818 / 11.812 | Article; code-qualified |
| Adobe / stocktitan.net | 843 / 5.493 | Unclassified capture; rejected `NO_STRUCTURAL_BODY` |
| Adobe / cryptobriefing.com | 381 / 2.468 | Article; code-qualified |
| Adobe / note.com | 399 / 2.965 | Article; code-qualified, but quiz/question passage is not an acceptable financial finding |
| Adobe / fool.com | 775 / 4.887 | Article; code-qualified |
| Adobe / 247wallst.com | 1,612 / 10.077 | Article; code-qualified |
| Adobe / finance.yahoo.com | 748 / 4.870 | Article; code-qualified |
| Adobe / siliconangle.com | 1,030 / 6.739 | Article; historical merger context, not current earnings corroboration |
| Dyson / wral.com | 1,807 / 11.521 | Homepage and Not Found index; rejected |
| Dyson / trendlife.com | 351 / 2.307 | Unrelated homepage; rejected |
| Dyson / thisismoney.co.uk | 2,077 / 12.045 | Landing-page/unclassified text; rejected |
| Battery recycling / ess-news.com | 374 / 2.691 | Article; missing temporal/usable-passage support |
| Battery recycling / indexbox.io | 8,604 / 62.759 | Six captures; one stale article, others index/catalog/homepage material; none qualified |
| Mary Barra / auto.economictimes.indiatimes.com | 484 / 3.009 | Appointment article; no qualified identity-threat/public-statement passage |

These are 16 observed publisher hosts in four investigations, **not** verification
of the separately protected 16 operation routes or every supported website.

## Actual losses and remaining work

1. **Adobe: acquisition demonstrated, interpretation remains imperfect.** Nine
   bodies and six finding strings are not nine verified financial claims. One
   selected finding is a financial quiz question; the first shared brief is a
   multi-company earnings-preview lead. Periods/forecast context and current
   claim relevance still need stricter passage selection. No filing comparison
   or independent correctness acceptance is claimed.
2. **Dyson: relevant leads exist; the first substantive acquisition loss is
   publisher resolution/body acquisition.** Three opaque-wrapper resolutions
   fail; four captures are nonarticle pages. Two leads remain unread after the
   wrapper cap. There are six HTTP budget rejections, not an exhausted 180-second
   clock. Reconcile observed publisher identities and prioritize article paths;
   do not guess URLs or relax source qualification to increase counts.
3. **Trending: article reading works, current coverage does not.** Two bodies
   are acquired. The returned report explains missing/stale timestamps for the
   48-hour window; the saved IndexBox article is 2,537.7 hours old. The ESS article
   ultimately has `NO_RELEVANT_PASSAGE`. Most other reads are market catalogs.
   Thirteen HTTP-budget rejections and host/wrapper limits leave leads unread.
   Prefer fresh event articles and diversify observed publishers; do not label
   stale material current or claim virality from these observations.
4. **Mary Barra: partial acquisition, no demonstrated specialist intelligence.**
   One appointment article is captured, but not a usable threat/statement
   passage. Three publisher resolutions, one access denial and one provider
   failure occur; ten wrappers remain unread at the existing cap. Improve
   task-aware discovery and expose background separately rather than presenting
   it as a detected threat or erasing its existence behind a zero-source count.
5. **Telemetry remains imperfect.** Dyson's legacy funnel says 138 rejections
   and its brief reports `UNSPECIFIED: 100`, despite only ten retained candidate
   URLs. Link-audit decisions are not unique rejected sources. The legacy
   `first_observed_empty_boundary` can point to qualification even when reading
   already occurred. This report uses the actual harvest/read/pool observations
   above, not those misleading aggregate summaries. Fix these projections before
   using them as performance targets.

Next priority is **bounded discovery-to-reading allocation and task-specific
source selection**, not longer total waits, more websites, more model calls or
another UI redesign. HTTP admissions are already 79/80, 80/80 and 73/80 in the
weak cases; per-host and wrapper caps matter even when wall time remains.
An eventual optimization must reserve actual reader opportunity and inspect
article outcomes, never reintroduce headline-count evidence acceptance.

No fresh rendered-browser check, independent held-out truth evaluation, hosted
CI, production parity, recovery of historical malformed dossiers or deployed
rollback was performed. The four live permissions are consumed. Further live
acquisition requires a new bounded proposal; none is silently retried here.
