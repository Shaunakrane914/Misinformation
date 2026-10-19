# Four-prompt acquisition repair — 2026-10-19

## Outcome and scope

The cross-request starvation reproduction, deadline leakage and source-selection
defects are repaired locally. **General research-quality acceptance remains
incomplete:** BrandShield/Nike still yields background only; Personal Watch/Tim
Cook still yields profile metadata only. No claim that either case establishes
safety, a threat, or absence of public information is justified.

Branch: `fix/p0-lenovo-acquisition-20261018`; base
`264a1c27857bf4cb36d516420dd6edf5ccc00adf`. The preceding
[four-prompt audit](2026-10-19_FOUR_PROMPT_VERIFICATION.md), its screenshots and
uncommitted index changes were preserved. This repair, tests and documentation
are **uncommitted/unpushed at this local-verification snapshot**; publication
updates belong in the ledger below. No merge, deployment, environment secret
change or provider-approval change was performed. Hosted CI for this patch must
be observed separately, not inferred from the preceding P0 checkpoint.

## Reproduction and decisions

1. A synthetic sequence of three timed-out Reddit requests (three queries each)
   exhausted the old eight-thread shared pool. A later mocked fast news query
   never started. The regression failed before the fix, then passed afterward.
   This reproduces a causal failure mode, not the exact thread history of the
   preceding live Tim Cook investigation.
2. Search now uses fixed two-worker pools for web, news, RSS, Reddit and Twitter,
   plus a two-worker shared pool for other channels: **12 search workers total**,
   not newly created pools per request. Existing 32-task admission capacity and
   cancellation/frozen-result guards remain. Social orphans cannot occupy the
   news/web/RSS workers. A saturated channel can still queue or fail honestly;
   no finite worker limit guarantees provider availability under arbitrary load.
3. A context-local monotonic deadline follows search, read, nested fallback and
   retry chains. Nested scopes cannot extend a parent deadline. Native HTTP
   requests/connection/header-body deadlines and retry sleeps consume remaining
   time; Reddit/X and public-identity lookups clamp their existing socket bounds.
   Expired empty adapter results are TIMEOUT, not successful empty acquisition.
4. Three legacy fallback paths called `feedparser.parse(remote_url)`, letting
   the parser own network I/O without the shared bounds. They now fetch bytes
   through the SSRF-checked 1MB bounded transport, then parse bytes locally.
   Remaining legacy requests calls clamp socket timeouts to the cooperative
   budget. Their existence is not a claim that every legacy transport has been
   redesigned into a fully pinned-IP wall-clock transport. Running Python/SDK
   threads are not forcibly killed; some third-party calls remain cooperative.
5. The previous Infosys auditor PDF failed the existing 1MB limit after 4,054ms;
   the next release got only 798ms. Observed compact press/earnings releases now
   sort ahead of auditor packs. No response cap or overall timeout was enlarged.
6. Financial careers landing pages are rejected unless the actual request is
   employment-related. Known specialist background destinations can be retained
   as discovery leads without getting a preferred read slot. Primary ownership
   no longer overrides an explicit objective exclusion. Search snippets can be
   misleading, so an investigated storefront may still become background after
   its body is read; it must not become a threat finding merely to fill the UI.
7. Google News opaque wrappers are not treated as article bodies. Each selected
   wrapper gets at most one bounded (up to 2s, within the same read deadline)
   title lookup. A publisher lead must match at least 75% of title tokens, then
   undergo the normal protected direct read. Failed resolution stays a failed
   read. Nested `publisher_url_resolution` query records, the wrapper URL and
   selected publisher URL are retained in attempt metadata. Canonical evidence
   IDs stay unchanged. These extra lookup records are **separate from the main
   initial-discovery query counters**. No Google private decoder or new account
   access was introduced. This is a bounded heuristic join, not entailment proof.
8. Brand queries use focused abuse terms rather than broad conjunctions. A
   storefront-only primary search no longer disables the existing secondary
   search for an abuse-specific query. Original leads remain inspectable.
9. Trending displays captured body author metadata when available. Discovery
   attribution and a body/source mismatch remain recorded; neither implies
   independent author authentication.

## Code and tests for the next agent

- [Service admission, bulkheads and lifecycle](../../backend/infrastructure/acquisition/service.py).
- [Cooperative deadline](../../backend/infrastructure/acquisition/network/budget.py),
  [native HTTP](../../backend/infrastructure/acquisition/network/http.py),
  [legacy compatibility scraper](../../backend/services/agent_reach_scraper.py).
  Reddit/X adapters, social resolver and social handlers use the same deadline.
- [Deep reader / wrapper resolution / provenance](../../backend/services/research/deep_reader.py)
  and [read stage](../../backend/application/research/reading.py).
- [Objective/content roles](../../backend/services/research/content_roles.py),
  [relevance](../../backend/services/research/relevance_gate.py),
  [source roles](../../backend/services/research/source_quality.py),
  [observed-link priority](../../backend/infrastructure/acquisition/adapters/web/page_extraction.py).
- [Source planning](../../backend/services/agent_reach/source_planner.py),
  [search fallback](../../backend/infrastructure/acquisition/routing/router.py),
  [Trending projection](../../backend/agents/trending/agent.py).
- [Twelve new offline controls](../../tests/unit/test_acquisition_followup_repairs.py).
  The existing P0 queued-worker test explicitly selects its injected pool now
  that production pools are partitioned; its assertion is unchanged.

## Bounded real observations

One sequential four-agent local ASGI/SSE matrix was run with AI credentials
excluded, mocks false, fresh temporary persistence and no notification/background
ingestion. No audit POST retries. The table compares with the prior audit, not
with deterministic provider fixtures; external data/timing changed too.

| Input | Before words / records | Repair-pass words / records | What was actually acquired |
| --- | ---: | ---: | --- |
| Infosys | 1,168 / 5 | 3,780 / 7 | Two observed IFRS release PDFs, P&L page and four indexes; no careers page |
| NVIDIA | 806 / 1 | 806 / 1 | Same publisher article; one unverified observation |
| Nike | 0 / 0 | 893 / 1 | Storefront background only; zero qualified findings |
| Tim Cook | 0 / 0 | 8 / 1 | Profile metadata only; zero qualified findings |

Infosys direct reads: 6 successful plus 1 carried index record, 29.328 decimal
KB. The observed IFRS USD/INR PDFs supplied 1,456 / 1,449 words respectively.
Both are same-issuer versions, **not independent corroboration**. Two source-linked
UNVERIFIED observations largely repeat the same opening passage; this remains a
presentation/deduplication limitation, not two independently resolved claims.

Query starts were Infosys 12/12, NVIDIA 13/14, Nike 9/9 and Tim Cook 10/10.
Tim Cook previously started 2/10. Every case recorded zero synchronous doctor
calls. NVIDIA still had one queued query. Reading opportunities and successful
HTTP results do not prove that specialist bodies were acquired.

A single additional two-case specialist recheck followed changing exact quoted
headline lookup to an unquoted title (same strict 75% token join). Nike returned
603 background words / 3.498KB; Tim Cook returned 8 profile words / 0.059KB.
Each started every main query (9/9 and 10/10); each recorded one timeout and no
queue timeout, and neither returned qualified findings. The lookup refinement
did **not** establish successful live publisher-body resolution. Its successful
lineage behavior is verified offline, not invented as a live success.

Both capture passes had stable application fingerprints within their own run.
Later legacy-feed deadline guards, expired-empty status and nested lookup IDs
were verified offline after these captures; **exact-final-build live parity is
not claimed**. Six normal investigations total were performed in this repair,
not repeated until a favorable answer appeared. Requested live AI/model-list
calls: **zero**; independent upstream account accounting was not observed.

## Frontend and durable evidence

The exact first repair-pass SSE responses were replayed through four real agent
pages and unchanged shared renderers at 320/390/1440px. All 12 states passed the
harness's count, finding-text, overflow, keyboard-inspection and page-exception
checks; no fresh research request was made. Four 390px report captures were
visually inspected. The UI truthfully shows zero specialist findings and the
limited retained background/profile text. Six console resource errors remained
(blocked fonts plus two 404s); this is not clean-console or accessibility
certification. The two-case specialist recheck was inspected in the terminal,
not claimed as another browser run.

[Selected screenshots and sanitized measurements](../testing/evidence/2026-10-19_four_prompt_repair/README.md).
Full raw reports, SSE, logs and isolated databases remain under system-temp
`aegis-four-repair-a6c00afd-3ba5-49a9-8484-6a76d955c905`.
Do not copy those bytes over historical dossiers or frozen evaluation proof.

## Executed validation (not a raw transcript)

```text
python -m pytest tests/unit/test_acquisition_followup_repairs.py -q --tb=short --show-capture=no
python -m pytest tests/ -q --tb=short --show-capture=no
python -m pytest tests/unit tests/chaos tests/security -q --tb=short --show-capture=no
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
python scripts/validate_release_candidate_smoke.py
python scripts/validate_rollback_compatibility.py
python scripts/validation/verify_frozen_benchmarks.py
```

Final results: **12 focused, 1,468 full (43.41s), 1,260 fast (33.68s) passed**,
all exit 0. Fatal lint zero errors; all nine Node `tests/frontend/test_*.js`
files executed separately and passed. Isolated smoke/persistence and frozen
hash checks passed. Historical archive recovery and deployed rollback remain
unverified. Protected tracked paths have no changes.

Initial tests exposed three selection defects, then the corrected cross-request
control reproduced queue starvation. An early full suite had four failures from
the new wrapper test restoring a bound method as an instance attribute, shadowing
later class-level compatibility mocks. Using scoped `patch.object` fixed the
test isolation; the affected 39-case group and subsequent full suite passed.
No production assertion or frozen expectation was weakened to hide this failure.

Terminal/browser commands use the existing runners described in the prior audit,
with fresh output directories and the same four cases. The second terminal pass
used only `brandshield:Nike` and `personal_watch:Tim Cook`. No `--allow-live-ai`.

## Remaining acceptance / safe next step

Do not deploy this as universal research-quality completion. Review the local
diff first. For specialist depth, replay saved wrapper resolution failures and
source-selection audits offline, then assess approved publisher availability
and source attribution. Do not raise all timeouts, relax SSRF/size protections,
invent threat findings, count profiles as substantive reports, or repeatedly
probe blocked providers. Independent held-out claim adjudication remains open.

## Publication ledger

After local validation, the repair checkpoint is intended only for the existing
dedicated fix branch so the user-requested hosted CI can execute. No main push,
merge or deployment is part of that publication. Inspect the exact pushed SHA
and run conclusion; the local counts above are not predeclared hosted results.
