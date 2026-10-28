# October 28 release reconciliation and benchmark audit

## Decision

**Reconciliation and scoped security correction completed; new research-yield
improvement over the released application is not demonstrated.** One complete
20-case aggregate report was recovered. Earlier ordered engine dossiers exist,
but the corresponding benchmark results/logs and original full response bodies
were not recovered. A launched or completed engine sequence is not counted as
a completed benchmark runner.

Most purported metadata/query/URL fixes already exist in application `ec5bef1`.
Unsafe root reader-fallback and deadline-extension changes were not ported.
The small useful Reddit empty-cache change was ported with bounded transport,
typed denial handling and cache provenance corrections. No commit, push, merge,
deployment, secret change, paid service or fresh investigation/model call.

## 1. Exact code lineage and preservation

| Checkout / reference | Branch / SHA | Observed state |
| --- | --- | --- |
| Original root | `feat/phase8-real-acquisition-proof`, `222a4ad358b4b74ee2fcfd899209fea51b0d8c6d` | Dirty; 13 tracked application modifications at initial inspection, subsequently 15, plus two untracked evaluation scripts. No root source was edited by this task. |
| `.scratch/phase9-remediation-20261016` | `release/specialist-task-20261024`, `7ad13a59f86a78802e45685ecfd1fd4999a2e5ce` | Extensive preserved dirty implementation/docs; not replaced with root files. |
| Current implementation checkout, `.scratch/deployment-20261028` | `fix/personal-evidence-20261028`, `8b5a9a55a8df030ccb86ccbd1f99be959e6885d7` | Preserved earlier uncommitted Personal Watch/selection work; this task adds a narrow RSS security/cache fix, tests and read-only audit tooling. |
| Released application | `ec5bef19ff701d62fc10546a4a9bcc7b569f95f8` | Baseline exported read-only with `git archive`; no checkout reset or history rewrite. |

Recorded `origin/main` is `8b5a9a5`, a documentation descendant of `ec5bef1`.
Local `main` is an older `ff6d246` reference. No remote fetch or deployment
inspection was performed in this task, and neither branch label alone is used
as production proof. The application directories have no committed differences
between `ec5bef1` and `8b5a9a5`; the latter closeout was documentation-only.

[Workspace snapshots](evidence/2026-10-28_reconciliation/workspaces.json) and
[per-file comparisons](evidence/2026-10-28_reconciliation/file-reconciliation.json)
record hashes and complete dirty-path inventories. Root `reading.py` and
`relevance_gate.py` appeared as additional edits during the audit; they were
reviewed separately and left untouched. No exact dirty-code fingerprint was
recorded by the historical benchmark, so these current hashes cannot attest
the code that ran either earlier attempt.

## 2. Already integrated versus root-only changes

| Concern | Released implementation / current lineage | Root-only delta and decision |
| --- | --- | --- |
| Personal metadata/depth | `monitoring.attribution_metadata` and `normalize_item` preserve observed read/body/depth/quote context through a bounded public projection. | Root blindly copies the old metadata dictionary and adds depth. Do not overwrite the newer preservation/security projection. |
| Scout body text | `ScoutAgent` retains bounded source `content` plus capture metadata and depth. | Re-adding a body field is redundant; no port. |
| Trending body text | Released agent retains up to 12,000 characters with explicit truncation metadata and actual content depth. | Root removes a former 1,000-character cap without the newer projections. No wholesale replacement or unbounded copy. |
| News queries | Released `StandardChannelHandlers._execute_feed` has subject-aware relevance and bounded provider alternatives; source planning has specialized statement/identity actions. | Root strips all quote marks, removes words including “false”, “scams” and “statement”, shortens to four terms and makes extra feed requests. That can destroy exact-claim intent and needs evidence beyond raw yield; not ported. |
| URL normalization | Released `NativeNormalizer.normalize_rss_entries` accepts `link` or `url`, retains observed wrapper locators and decodes only recognized wrapper hosts. Web fallback also accepts either field. | Root's `link or url` addition is already present; its older substring wrapper logic must not replace host-checked decoding. |
| Feed concurrency | Released newswire discovery is sequential, retains its three-feed cap and source/query restrictions. | Root submits up to six worker threads and, for its entertainment subclass, up to eight feeds. It does not copy deadline/HTTP-budget/observation context into workers or impose a same-host admission guard. Do not port this concurrency implementation. |
| Trending source routing | Released route is topic-aware with GDELT and permitted source-family alternatives. | Root switches the default to an existing `TrendingPulseAdapter` entertainment feed set. The selector is registered, but this universal switch is not appropriate for every topic and does not establish access permission or body acquisition. Not ported. |
| DNS validation | Released validator uses eight bounded slots, typed DNS_CAPACITY/TIMEOUT/ERROR, a short transient failure cache, mixed/private-answer rejection and fresh pinned-address validation before connecting. | Root raises slots to 24 and waits at least 0.5 seconds even for a shorter caller allowance. Keeping a lookup denied is necessary; capacity is never permission to skip validation. Existing released protections retained. |
| RSS cache | Released subreddit RSS treats empty lists as misses. | Useful root intent: retain successful empty results. Ported narrowly, distinguishing a successful empty feed from a cached access failure. |
| Reader fallback | Released native/Jina boundaries terminate access denials/challenges; alternate routes retain source/security limits. | Root explicitly lets 401/403/429 and selected 5xx responses proceed toward another reader in both `NativeExecutor.execute_web_read` and Jina. Do not port access-bypass behavior. |
| Reading deadline | Current pipeline uses monotonic deadline budgeting and remaining request capacity. | Late root edit uses `max(time_left, reserved_read_floor)` and can read after request time is exhausted. Not ported. Reservations must be made within the request, not added afterward. |
| Freshness metadata | Current lineage separates current-article eligibility from explicitly labeled older background. | Late root edit propagates its older `temporal_fresh` flag. It is not a replacement for the current date/body/role gate; not ported. |

These decisions compare behavior and file contents, not the apparent age of a
branch name. Previous [Personal Watch repairs](PERSONAL_SELECTION_AND_TRANSCRIPT_REPAIR_2026-10-28.md)
remain uncommitted and separate from the release baseline.

## 3. Security findings and changes actually made

**P1, root-only regression:** explicit 401/403/429 reader failures could activate
another reader. Root was preserved; those hunks were excluded. Targeted tests
confirm a denied native read invokes neither Firecrawl nor Jina in the current
lineage, retaining the HTTP status rather than presenting empty success.

**P1, released legacy RSS boundary:** `fetch_reddit_subreddit_rss` used a direct
`urllib.request.urlopen` plus an unbounded `read()`. That path did not use the
shared DNS-pinned transport, decoded byte bound or native HTTP admissions.
Its broad exception handling also converted denials into empty feeds, allowing
subsequent social-reader fallbacks. Corrected in the current lineage:

- Use existing `fetch_public_http` with a five-second-or-less remaining allowance,
  1,000,000-byte wire/decoded caps, one attempt and zero redirects. The fixed
  subreddit endpoint cannot redirect into a differently authorized platform.
- Validate subreddit syntax and bound entry counts before transmission.
- Cache valid empty RSS results. A repeat uses no additional HTTP admission.
- Cache 401/403/429 as typed failures for a bounded cooldown; a cache hit retains
  the status with `network_observed=False` and zero new attempts. It is not an
  empty successful search. Actual provider quota usage is not inferred from
  native admissions.
- Detect an explicit denial page returned as HTTP 200 when it is not a feed.
- Propagate transport/security/source-permission failures. The entity-resolution
  loop cannot swallow one and use another reader to bypass the denial.

No Reddit approval flag or source permission was enabled. No proxy/mirror was
added. Generic HTTP redirects retain per-hop scope validation, sensitive-header
stripping and a fresh validated/pinned numeric destination. Existing security
regressions cover cross-origin and scheme/port credential stripping, DNS rebinding,
private/metadata destinations, response bounds, source permissions and rate limits.
The new capacity test confirms no socket opens when DNS slots are exhausted.

Files: [Reddit adapter](../../backend/infrastructure/acquisition/adapters/social/reddit.py),
[social routing](../../backend/infrastructure/acquisition/routing/social_handlers.py),
[new security controls](../../tests/security/test_oct28_acquisition_reconciliation.py).
This is a scoped review and correction, not certification that every historical
acquisition route is vulnerability-free.

## 4. Actual 20-case recovery

Recovered protected file:
`artifacts/live_evaluation/five_prompt_four_agent_results.json`, timestamp
`2026-10-28T07:43:29.246117+00:00`, SHA-256
`23b44e4a8f13b67cbb802f3f7759c8fc1db822108bce25715763d28af8a33c99`.
It contains all 20 expected agent/input rows and is a **completed aggregate
result**, not an inferred background-task success. It is preserved unchanged;
a byte-identical copy is in [the evidence index](evidence/2026-10-28_reconciliation/README.md).

The runner writes one fixed filename only after completing its loop, overwriting
that path on every completed invocation. No second aggregate file or original
terminal log was recovered from the repository or matching system-temp filenames.
Protected dossiers reveal three ordered sequences of 20 completed engine records:

| Sequence, first/last dossier timestamps UTC | What is established |
| --- | --- |
| 06:09:59–06:21:39 | Additional earlier ordered engine sequence; aggregate/runner completion not attested |
| 06:59:12–07:06:05 | Prior ordered 20-engine sequence; original aggregate/runner exit/log unavailable |
| 07:32:18–07:43:29 | Latest ordered engine sequence, consistent with the one preserved complete aggregate |

Timestamps above are dossier creation times, not benchmark wall-clock start times.
Do not treat the first two sequences as successful complete benchmark runners.
The requested earlier attempt's per-case engine observations are recoverable;
its complete original agent results and aggregate metrics are not.

The original runner explicitly sets `AEGIS_MOCK_LLM=true`. It counts returned
`content or snippet` words, exact-text deduplicated bodies of any depth, distinct
vocabulary tokens, and records with certain depth labels. Its EXCELLENT/GOOD
labels are raw-length thresholds, not research acceptance. Returned Trending
records for Russell Brand, Taylor Swift and DeepSeek are explicitly snippets.
Some native fallback records are absent from their engine dossier's lineage;
the two layers must not be assumed to be one complete acquisition trace.

### Preserved latest aggregate values

The following are original reported metrics, **not acquired/qualified article
counts**. Dossier hosts count discovered lineage candidates, including rejected
leads; they are not independent qualified publishers or necessarily every native
fallback record. For every row, actual article bodies/words, qualified relevant
sources, deduplicated relevant passage words, actual read attempts and native
HTTP admissions are **not recorded sufficiently to verify**. They remain `null`
in the [machine-readable recovery](evidence/2026-10-28_reconciliation/benchmark-recovery.json),
rather than being substituted with these raw values or invented zeros.

| Agent / input | Returned records | Reported text words | Depth-labelled records | Dossier candidate hosts | Runner seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scout / NVDA | 0 | 0 | 0 | 19 | 39.49 |
| Scout / AAPL | 0 | 0 | 0 | 8 | 53.45 |
| Scout / TSLA | 0 | 0 | 0 | 16 | 41.92 |
| Scout / MSFT | 0 | 0 | 0 | 10 | 40.80 |
| Scout / AMZN | 0 | 0 | 0 | 10 | 62.37 |
| BrandShield / Nike | 1 | 4,069 | 1 | 9 | 24.64 |
| BrandShield / Rolex | 3 | 2,109 | 3 | 12 | 22.95 |
| BrandShield / Pfizer | 2 | 4,047 | 2 | 5 | 22.60 |
| BrandShield / Gucci | 3 | 237 | 3 | 11 | 22.46 |
| BrandShield / Sony | 1 | 65 | 1 | 8 | 25.55 |
| Trending / Russell Brand | 6 | 123 | 0 | 5 | 57.93 |
| Trending / Taylor Swift | 6 | 106 | 0 | 0 | 41.03 |
| Trending / OpenAI | 0 | 0 | 0 | 0 | 45.27 |
| Trending / Artificial Intelligence | 0 | 0 | 0 | 0 | 39.07 |
| Trending / DeepSeek | 6 | 79 | 0 | 0 | 52.06 |
| PersonalWatch / Satya Nadella | 0 | 0 | 0 | 8 | 22.22 |
| PersonalWatch / Tim Cook | 0 | 0 | 0 | 5 | 22.08 |
| PersonalWatch / Sam Altman | 0 | 0 | 0 | 9 | 25.77 |
| PersonalWatch / Sundar Pichai | 3 | 1,492 | 3 | 9 | 23.27 |
| PersonalWatch / Jensen Huang | 0 | 0 | 0 | 8 | 25.67 |

Per-case engine latency, query/channel status categories, snapshot checksums,
observed candidate hosts and supporting-reference resolution are preserved in
the recovery JSON. A reference resolving to a sealed short snapshot is an identity
check, not citation entailment or proof that a full article was read. The runner
records no code fingerprint/dirty diff, and sources changed during the broader
session. Attribution to an exact historical dirty-code revision remains unverified.

## 5. Tim Cook and Russell Brand: identical-input replay

The earlier Tim Cook demonstration is dossier
`R-2026-678A2D7C653B4850BB8D268FF5F1B25B`, created 07:22:43Z. Its prose summary
reports six deep-read documents and four findings. However, its eleven sealed
snapshots contain only 24–204 characters each, without body structure, read IDs,
read-attempt events, final HTTP transport or publication declarations. Snapshot
hashes match those short strings. They do not establish six actual reads or
the claimed three full articles. Those claims are **NOT VERIFIED**, not relabeled
as zero actual reads. The later complete batch returned zero Tim Cook records;
it must not be substituted for this separate demonstration.

The Russell demonstration and batch dossiers retain court-reporting headline/
snippet leads, allegations and reported denials. They are topically related,
but lack acquired article bodies and reliable publication timestamps. Words
such as “today” or a retrieval timestamp do not establish publication freshness.
They cannot establish a current verdict, an authenticated public statement,
independent corroboration or measured virality.

Four genuine sealed snippet sets were reconstructed **as discovery leads only**,
with their original source IDs/URLs/text hashes. No acquired ID, body depth,
article role or date was invented. Each was replayed through released `ec5bef1`
and the current agent/API/SSE pipeline with sockets, DNS and model generation
blocked. A separate genuine October 25 Tim Cook transcript fixture was used as
an explicitly historical-event positive control; it is not from the 20-case run.

| Same saved input | Released/current qualified records | Released/current deduplicated passage words | Native attributed statements, released → current |
| --- | ---: | ---: | ---: |
| Tim demonstration snippets | 0 / 0 | 0 / 0 | 0 → 0 |
| Tim latest-batch snippets | 0 / 0 | 0 / 0 | 0 → 0 |
| Russell demonstration snippets | 0 / 0 | 0 / 0 | Not an authenticated speaker task |
| Russell latest-batch snippets | 0 / 0 | 0 / 0 | Not an authenticated speaker task |
| Separate October 25 Tim transcript control | 1 / 1 | **547 / 547** | **0 → 15** |

Zeros above are replay output on the preserved input set, not a claim about
unrecorded original article acquisition. Historical control event context is
WWDC 2020; its publication date remains unknown where not established by metadata.
It is not a new 2026 development. The prior local transcript attribution allowlist
repair restores native statement enumeration without inflating sources or passage
words; the released workbench already retained those 547 words.

[Replay comparison](evidence/2026-10-28_reconciliation/replay-comparison.json).
All ten replay executions exited 0; exact original source identities, URLs,
dates and retained body hashes were preserved within each prepared input set.
The conversion from historical snippets is explicitly labeled and not presented
as an original complete native response or fresh investigation.

## 6. Production baseline stays separate

The earlier [October 28 production report](DEPLOYED_FOUR_AGENT_WORD_YIELD_2026-10-28.md)
observed Adobe 603 published words, Dyson 353, and Mary Barra zero on the first
production pilot; battery recycling later published 580 older-background words
and zero current evidence on `ec5bef1`. These are different subjects/source sets
from the root 20-case batch. They are not valid paired measurements of a root
patch's causal gain. No new production request was made here.

The prior isolated local continuation demonstrated other real sources and saved
processing repairs (Fei 5,773 words; Mary 99 words including 37 attributed words).
Those remain separate from this benchmark reconciliation and were not redeployed.
No increase in qualified Tim/Russell passage words over `ec5bef1` was demonstrated
from the recovered 20-case material.

## 7. Verification actually performed

New read-only tooling: [reconcile_saved_benchmark.py](../../scripts/audits/reconcile_saved_benchmark.py),
with [metric-integrity tests](../../tests/unit/test_saved_benchmark_reconciliation.py).
No agent is imported by the recovery tool. It creates only a new selected output,
never repairs historical dossiers or overwrites protected aggregate evidence.

- Initial targeted security/reconciliation subset: **95 passed**.
- Four legacy mirror tests initially failed because their fixtures mocked only
  Arctic Shift while implicitly trying RSS. The repository-wide offline guard
  blocked the unmocked socket paths. Fixtures now explicitly disable the unrelated
  RSS route; dedicated RSS/denial tests exercise it separately. No network guard
  or access rule was weakened. Focused rerun: **49 passed**.
- Ten offline native/API/SSE replays and ten Chromium viewport states completed.
  All rendered passage text/counts matched reports; no horizontal overflow or
  uncaught page exception. Tim historical mobile and Russell empty desktop views
  were visually inspected. API readiness is a replay stub, not live provider proof.
- Final full/fast/fatal-lint/frontend/frozen/smoke/persistence results are appended
  after closeout. Initial failures remain in temporary logs and are not called passes.

Final validation:

| Command / scope | Actual result |
| --- | --- |
| `python -m pytest tests/ -q` | Exit 0; **2,844 passed**, 121.41s pytest time |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **2,636 passed**, 97.32s pytest time |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; zero fatal findings |
| Each `tests/frontend/test_*.js` with Node | Ten scripts; exit 0 each |
| `python scripts/validation/verify_frozen_benchmarks.py` | Exit 0; protected frozen content unchanged |
| `python scripts/validate_release_candidate_smoke.py --output <fresh-temp-json>` | Exit 0; `OFFLINE_SMOKE_PASS` |
| `python scripts/validate_rollback_compatibility.py --output <fresh-temp-json>` | Exit 0; isolated `OFFLINE_PERSISTENCE_PASS`, not historical recovery or deployed rollback |
| Protected paths, whitespace and new relative links | Passed |
| Offline source/API/SSE replay | Ten executions; exit 0 each; no new provider/model calls |
| Local Chromium replay | Ten 390/1440px states; exact passage text/counts and honest empty states |

[Final gate accounting](evidence/2026-10-28_reconciliation/final-gates.json)
and [initial failed run](evidence/2026-10-28_reconciliation/initial-gates.json)
remain separate. Initial full/fast results were 2,840/2,632 passed with four
fixture-scope failures each, corrected as described above. One earlier new DNS
test expected the HTTP wrapper exception at the raw socket boundary; it was
corrected to the actual typed `DNSResolutionError`, preserving denial/no-socket
assertions. No security control was relaxed to obtain a pass.

A separate read-only syntax inventory of the original archive observed **2,543
readable JSON files and 55 malformed files**. Those malformed files remain
untouched and failed at JSON parsing; the archive does not pass historical
integrity/recovery acceptance. Isolated persistence uses temporary storage and
does not supersede that failure. The benchmark recovery skips unparsable files
for case metrics; this separate inventory reports them explicitly.

## 8. Remaining barriers

| Agent | Remaining barrier |
| --- | --- |
| Scout | The root batch returned no source records for five stocks. Discovery candidates/length do not establish financial amounts, period/currency agreement or claim adjudication. Released Adobe results remain a separate bounded example. |
| BrandShield | Large returned text is not necessarily incident evidence. Positive threat cases, actor/entity matching, source dates and allegations versus confirmed actions still need source-level review. Root aggregate EXCELLENT labels are not acceptance. |
| Trending | Recovered Russell outputs are snippets with inadequate dates/body proof. Preserve historic/context material separately; acquire current dated articles and repeated comparable observations before trend/virality claims. |
| Personal Watch | Metadata and statement attribution have stronger released/local protections, but the claimed new Tim articles/reads lack retained proof. Namesake records and reported quotations must stay distinct. Historical transcript enumeration now works without word inflation. |

The highest-value next evidence requirement is **a complete bounded native
capture**, with actual read attempts/HTTP observations, body structure, exact
passage offsets and code fingerprint. Do not start another 20-prompt batch or
infer missing bodies from summaries. Any further live check needs its separately
defined scope/budget and expected diagnostic value.

No new deployment or research-quality PASS is authorized or implied. Root and
remediation source changes, protected dossiers, frozen benchmark files, research
and artifact trees remain preserved. The historical malformed-dossier recovery
gate remains separate from isolated persistence tests. Full temporary work is
under system-temp basename `aegis-oct28-reconciliation-u098c0ob`; selected durable
evidence is indexed below and temporary files may expire.
