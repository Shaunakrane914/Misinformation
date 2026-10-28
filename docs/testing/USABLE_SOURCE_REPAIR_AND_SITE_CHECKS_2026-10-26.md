# Usable-source repair and individual website checks — 2026-10-26

## Actual result

**The four reviewed new text-source families were checked individually. None reached article extraction in this run.** PIB, GOV.UK and Global Voices failed DNS validation; the Sports Ministry failed connection establishment. This is not evidence that those websites lack content, and does not measure their article-text yield.

All **60 registered families/hosts** were inventoried. **Four received live direct-read probes; 48 unreviewed families were not fetched; eight existing native-route families were not rerun.** Do not describe this as 60 live scraping tests. The full [per-site CSV](evidence/2026-10-26_usable_sources/individual-sites.csv) and [diagnostic JSON](evidence/2026-10-26_usable_sources/individual-sites.json) preserve those distinctions.

| Individually probed site | Seconds | Native HTTP admissions | Retained body KB / words | First actual failure |
| --- | ---: | ---: | ---: | --- |
| PIB — `pib.gov.in` | 2.51 | 0 | 0 / 0 | `DNS_TIMEOUT` while validating the robots URL |
| GOV.UK — `gov.uk` | 2.51 | 0 | 0 / 0 | `DNS_TIMEOUT` while validating the robots URL |
| Global Voices — `globalvoices.org` | 2.52 | 0 | 0 / 0 | `DNS_TIMEOUT` while validating the robots URL |
| Sports Ministry — `yas.gov.in` | 1.24 | 1 | 0 / 0 | `CONNECTION_FAILURE` during robots acquisition |

Zero HTTP admissions can coexist with a DNS lookup: reservations occur after destination validation. An admission is not proof the server received an HTTP request. The captured 2.5-second failures identify unresolved DNS operations, not a proven provider block, private-IP rejection or a known cause in the user's network. No DNS bypass, alternate resolver, proxy, repeated source sweep or fabricated body was used.

## Scope and preservation

User requests: expand/repair usable coverage, then check the new sites individually. Existing constraints remain: no configured private publisher agreements, retain explicit gates; no push/merge/deployment. The user separately authorized two repaired normal investigations and one paced post-fix investigation; all three were run once and those allowances are consumed. The later individual-site request authorized direct diagnostics; these were separate from query-based investigations and used no AI.

Checkout `.scratch/phase9-remediation-20261016`, branch `release/specialist-task-20261024`, base `7ad13a5`, plus preserved dirty work. Earlier changes were copied to a fresh system-temp tree before this repair. Historical dossiers, benchmark data/manifests, research/artifacts and working scraper shims were preserved. Original main-worktree `.env` remains locally AI-enabled as requested; no credentials or production settings changed in this continuation.

## Repairs implemented

| Owner | Correction and evidence |
| --- | --- |
| [search_observations.result_fit](../../backend/infrastructure/acquisition/adapters/web/search_observations.py) | Enforce positive/negative `site:` URL constraints, including alternative hosts, subdomains and path boundaries. A matching person name on the wrong host no longer disables the existing bounded secondary search. Ten genuine normalized Bumrah search decisions are retained in the [replay fixture](../../tests/unit/fixtures/oct26_topic_scope_drift.json); all ten are off-scope, not publisher article bodies. |
| [SourceRegistry.assess / select](../../backend/services/research/source_registry.py) | Existing native families can enter topic selection under their unchanged authentication/capability gates. A source-specific review remains required for new publishers. Prefer focused families over broad catch-alls, restrict India-specific families to India routing context, and prevent one issuer's newsroom being chosen for an unrelated company. |
| [topic_context.infer_context](../../backend/services/research/topic_context.py) | Explicit request geography and subject-matching observed titles may supply a tentative jurisdiction hint. Unrelated titles and conflicting observations preserve uncertainty. No hardcoded celebrity identity, nationality authentication or generated attribution. |
| [Operational definitions](../../backend/services/research/source_registry_data.json), [public-policy reviews](../../backend/services/research/source_public_licence_reviews.json) | Add Sports Ministry as the 60th family and conditionally review eligible PIB/Sports Ministry text. Four public-review families now exist. These two government sources are official statements, not independent corroboration or broad celebrity-news coverage. Other new publishers remain gated. |
| [SourceRegistry.discovery_entrypoints](../../backend/services/research/source_registry.py), [HarvestingEngine](../../backend/services/research/harvesting.py) | Selected reviewed families can supply at most two configured publisher directories inside the original read budget. Follow only actual captured same-family links using the existing bounded continuation path. No guessed article slugs or user-supplied article URL. Initial and observed-title-refined planning both reach this path. Directories remain discovery, not evidence. |
| [DeepReader](../../backend/services/research/deep_reader.py) | Separate wrapper-resolution search transport from article body-access scope. The actual resolved URL and body redirects still receive permission/robots/SSRF checks. Configuration-denied leads continue to preserve reader slots, as fixed in the preceding checkpoint. |
| [SourceRegistry.paced_request](../../backend/services/research/source_registry.py), [bounded HTTP](../../backend/infrastructure/acquisition/network/http.py) | The live first batch exposed a valid Global Voices `Crawl-delay: 10`. Implement a shared origin lease across threads, held until response completion; wait between requests inside the original research deadline, before the short HTTP socket deadline starts. For paced sources use one attempt and stop on redirects instead of following transfers without pacing. Oversized/expired waits fail before HTTP. No directive is ignored. |
| [NativeExecutor](../../backend/services/agent_reach/native/executor.py), [modular web reader](../../backend/infrastructure/acquisition/adapters/web/jina.py) | A typed source-policy denial propagates; it cannot masquerade as empty HTML and trigger another reader. |
| [Offline test environment](../../tests/conftest.py) | Explicitly disable ordinary AI suggestions and isolate their SQLite policy ledger before application import. Local server enablement cannot spend normal test quota or change test policy. Advisory tests opt in with mocks explicitly. |
| [Individual-site runner](../../scripts/audits/probe_source_families.py) | Inventory every family; only probe reviewed text families. Per family: 60 seconds, six native admissions, at most two reads; no AI/paid reader/audit retry. Retain actual cause, bytes/words, body kind and excerpt permission. No raw publisher bodies exported or findings generated. Homepage/policy prose cannot count as article yield. |

The eligible-text review basis is the actual [PIB copyright policy](https://www.pib.gov.in/content/3622_2_CopyrightPolicy.aspx?lang=6&reg=17) and [Sports Ministry copyright policy](https://yas.gov.in/en/copyright-policy). Both require accurate, credited use and exclude third-party material. These conditional reviews do not override robots/access controls or grant media rights. Research also found [NewsOnAir restrictions](https://newsonair.gov.in/copyright-policy/) and [UNESCO/WHC syndication restrictions](https://whc.unesco.org/en/syndication); those were not enabled as substitutes. Tripura MyGov's [terms](https://tripura.mygov.in/simple-page/terms-conditions/) include explicit automated-access restrictions for that site; a generic reuse clause is not treated as a crawler grant.

## Normal query-based investigations — still no live article proof

These were actual local agent/SSE investigations, not the individual direct probes. Each had a 180-second, 16-read and 80-native-HTTP ceiling; body families restricted to PIB, Sports Ministry, Global Voices and GOV.UK. AI advice was optional under the existing shared daily policy. Temporary storage, no background ingestion, paid readers, retries at audit level or production writes. Application fingerprints were stable within each batch.

| Case | Seconds | Candidate URLs | Reader selections / actual read-service starts | Native HTTP admissions | Bodies / published words | First loss |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Trending/Bollywood cinema, repaired two-case batch | 26.25 | 3 | 2 / 0 | 42 | 0 / 0 | PIB robots HTTP 403; Global Voices crawl delay was unsupported at that captured code version |
| Personal/Jasprit Bumrah public statement, same batch | 29.54 | 34 | 2 / 0 | 38 | 0 / 0 | PIB robots HTTP 403; Sports Ministry connection failure |
| Trending/Bollywood cinema, separately approved paced check | 60.31 | 4 | 2 / 0 | 39 | 0 / 0 | Both configured directory robots lookups hit `DNS_TIMEOUT`; pacing/body extraction never began |

Compared with the earlier pilot, Personal's 16 blocked selections fell to two actual eligible directory selections; it continued discovery to 34 leads. That is corrected allocation, **not 34 relevant articles or research success**. Scoped provider drift is rejected and the cricket/India routing hypothesis reached PIB/Sports Ministry. No useful source body survived because access failed earlier. The source catalogue's larger size does not establish usable coverage.

All final statuses are `ACQUISITION_FAILED`, with zero acquired sources. HTTP 200/result events are not research acceptance. No positive threat, financial or celebrity finding was manufactured. Post-fix pacing has deterministic/synthetic offline proof; the paced live check did not exercise it successfully because DNS failed first.

### AI accounting

Two generation reservations were consumed across the new three investigations; no quota reset, key/model fallback or retry. The two-case batch records one successful `gemini-3.5-flash-lite` suggestion: HTTP 200, 307 prompt + 82 output = 389 provider tokens, 1,109.81ms. The paced case's suggestion timed out locally after 2,513.34ms and consumed one reservation, but its saved summary contains no provider outcome/token observation. Its provider usage is **unknown, not zero**. The shared UTC-day counter ends at three, including the earlier separate 40-token enablement check. Do not claim three successful generations or a complete monetary cost measurement. Individual-site probes, ordinary tests and browser replay made no model calls.

## Validation and remaining limits

Final counts and command exits are recorded in the [validation evidence](evidence/2026-10-26_usable_sources/validation-summary.json). The new [27 repair controls](../../tests/unit/test_usable_source_expansion.py) cover genuine normalized drift, scoped fallback, native auth/health admission, geography/issuer routing, directory-to-body continuation in both controllers, paced concurrency/deadlines and policy-denial propagation. [Probe-report controls](../../tests/unit/test_source_site_probe.py) verify the 60-family inventory and prohibit homepage/policy inflation.

| Command actually run | Exit / result |
| --- | --- |
| `python -m pytest tests/ -q --tb=short` | 0; **2,645 passed / 117.04s** |
| `python -m pytest tests/unit tests/chaos tests/security -q --tb=short` | 0; **2,437 passed / 98.88s** |
| Focused repair/registry/discovery/golden/runtime tests | 0; 133 passed / 4.42s |
| Probe-report and repair tests after the runner addition | 0; 29 passed / 0.98s |
| Fatal flake8 E9/F63/F7/F82 over backend/tests/scripts | 0; zero fatal findings |
| Each of ten frontend Node scripts | 0 each |
| Release smoke with fresh temporary output | 0; OFFLINE_SMOKE_PASS |
| Rollback compatibility with fresh temporary output | 0; OFFLINE_PERSISTENCE_PASS; historical archive and deployed rollback NOT_VERIFIED |
| Frozen verifier / protected-tree diff / whitespace check | 0; protected bytes unchanged |
| Two-case and one-case terminal investigations | 0 transport; both batches failed research acceptance |
| Individual-site CLI | 0; four probes completed, zero acquired bodies, no AI calls |
| Browser report replay | 0; nine empty-report states at 320/390/1440px, no detected overflow or uncaught page exceptions |

The first new directory test failed because a broad family displaced the more specific sporting source; specificity and jurisdiction were corrected. Ten characterization hashes then changed because an existing SEC query became eligible. Before accepting the delta, both saved-old/current registry configurations were executed over the same 12 scenarios: acquired candidates, corpus/dossier hashes, IDs, citations, findings and all non-result summary projections were unchanged; full-payload differences were confined to source-plan/generated-query disclosure. The [new reviewed delta](../../tests/unit/fixtures/research_topic_source_policy_deltas_20261026.json) records the new result hashes without overwriting historical manifests. Frozen retrieval datasets/manifests remain intact. No broad canonicalization exclusion was added.

Individual probes do not establish query-based discovery, article relevance, current publication dates, claim accuracy or source independence. No new article URL/date/qualified-word success can honestly be supplied. Native empty reports were replayed in real Chromium with external traffic blocked; this checks rendering only. Independent accuracy, production parity, hosted CI, historical malformed-dossier recovery and deployed rollback remain unverified.

Pacing is shared across threads in one process; multi-process coordination is not established. Paced redirects currently stop rather than follow. Those are explicit limits, not a claim of production-wide rate compliance. Do not bypass 403s, missing robots or DNS validation to obtain a passing result. The immediate unresolved runtime stage in the individual checks is DNS/connection establishment; adding more definitions cannot repair it.

No commit, push, merge or deployment performed. Original native responses, logs, pre-change copies, isolated dossiers and full browser outputs remain under system-temp basename `aegis-usable-source-repair-l_nnpdo1`; selected portable records are in the [evidence index](evidence/2026-10-26_usable_sources/README.md).
