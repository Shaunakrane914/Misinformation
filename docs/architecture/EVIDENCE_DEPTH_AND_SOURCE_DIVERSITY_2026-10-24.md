# Evidence depth and publisher diversity — 2026-10-24

## Decision and scope

The owner increased the proposed depth target from 10x to **20x** and authorized
implementation plus broader website discovery. Preserve the shared acquisition
fabric and add an explicit passage-publication boundary; do not create another
scraper stack, verdict engine, paid provider or unbounded crawler.

Implementation starts from `1a90d681361b8e027a12feb88266932a5cb5d1d1` on
`release/specialist-task-20261024`, initially clean. This milestone is local,
not permission to push, merge, change provider approval flags or redeploy.

## Contract and data flow

1. Existing source planner and capability checks produce executable searches.
2. Publisher-family search hints replace some repeated generic queries within
   the same QUICK/STANDARD/DEEP caps. Validated specialist actions and separately
   reserved optional channels retain priority. No article URL is guessed.
3. Candidate admission reserves diversity by limiting one observed publisher to
   roughly one third of discovery capacity (minimum four). Observed continuation
   links keep the existing separate reservation. Read ordering uses publisher
   repetition only after task/freshness/document-type priorities.
4. Native reads retain existing SSRF, host, HTTP, byte, deadline and access rules.
5. Existing body/temporal/subject gates still decide evidence eligibility.
6. The winning exact excerpt remains unchanged for compatibility. The passage
   extractor also retains up to 80 complete paragraphs/20,000 characters from
   that source which passed the same paragraph-level gates. They are **source
   assertions selected by heuristics**, not additional adjudicated claims.
7. Inspection recomputes full-body hashes and validates exact offsets before
   public projection. Stale hashes, mismatched IDs and discovery-only records
   cannot populate the evidence workbench. Native serializers preserve this
   narrow allowlisted metadata, never authentication/provider envelopes.
8. Shared reports include additive `evidence_workbench` v1: source records,
   exact passages, content roles, context labels, deduplication and accounting.
   Round-robin admission across sources prevents the first source monopolizing
   the bounded 512-passage/240,000 UTF-8 text-byte collection. This byte cap is
   passage text only, not the complete JSON envelope. Omissions are counted.
9. The frontend renders eight passages at a time, with local search, publisher
   and content-role filters and keyboard pagination. This is **client-side
   pagination of a bounded serialized collection**, not a new server-side
   pagination API or a persistent background-crawl service.

## Broader websites without broader permissions

`source_diversity.py` defines eight discovery families /24 domain selectors:

| Family | Search-hint domains |
| --- | --- |
| General reporting | reuters.com, apnews.com, bbc.com |
| Financial reporting | cnbc.com, marketwatch.com, business-standard.com |
| Regional reporting | theguardian.com, dw.com, aljazeera.com |
| Technology reporting | arstechnica.com, techcrunch.com, theverge.com |
| Science reporting | nature.com, sciencedaily.com, phys.org |
| Consumer safety | cpsc.gov, recalls.gov, gov.uk |
| Enforcement reporting | justice.gov, cbp.gov, europol.europa.eu |
| Consumer protection | ftc.gov, europa.eu, accc.gov.au |

These are **search hints, not 24 verified working integrations**, endorsement,
approved provider access or authenticated primary-source labels. Each domain
maps to three relevant families, with at most three scoped queries admitted
inside the existing budget. Unscoped discovery remains, including original
issuer/speaker sources. Existing site restrictions take precedence. Tasks and
Trending date hints survive diversification. A broad topic and unfamiliar
subject use the same rules; no subject-specific answer or article slug is added.

Blocked Reddit/X/SEC/FactCheck access is not enabled or routed around. A denied
article remains denied. An inaccessible website does not establish missing
public evidence. Publisher host diversity is not independent corroboration;
syndicated/identical text retains aliases and counts only once in word totals.

## Domain interpretation and exclusions

- Scout: preserve reported/forecast mixtures, historical publication scope,
  unknown currency/period and unperformed filing comparison. Calendar lists,
  live-coverage promos and quiz prompts do not become extra evidence passages.
- Trending: unchanged body and freshness gates; article acquisition is not
  measured virality. Failed/undated/stale candidates remain separately inspectable.
- BrandShield: safety reports, warnings, corrections, complaints and allegations
  remain distinct; more displayed text never creates an attacker URL or verdict.
- Personal Watch: existing observed attribution and disputed-quotation
  segregation remain; profiles and unrelated biography do not become findings.

## Measuring 20x honestly

The primary future acceptance metric is deduplicated, task-relevant exact
passage words accessible through the frontend, measured on a fixed representative
evaluation set at stated budgets and reviewed for relevance/attribution. Compare
the same output scope on both versions. A zero baseline requires an absolute
successful-retrieval target, not an infinite ratio.

The old selected-excerpt count is a useful compression diagnostic, but **not**
the entire previously inspectable UI corpus: old source cards already contained
bounded chunks and structured passages. Neither larger capacity, a synthetic
25-paragraph test, a 200 HTTP response, nor raw article words proves 20x research
improvement. `target_status` remains `NOT_EVALUATED` in reports; measured summaries
must not report the multiplier achieved without the paired relevance evaluation.

## Tradeoffs and rollout

More bounded serialized text increases payload/memory even when the DOM is
paginated. Relevance remains heuristic. Publisher-share limits can defer a
useful same-publisher result, and scoped queries can return fewer accessible
sources than unscoped queries. Live results must expose those failures rather
than changing access controls or accepting snippets. Existing caps were not
multiplied by twenty.

Validate saved genuine responses and adversarial synthetic controls first,
then the full/fast/security/frontend/frozen-data gates, then actual Chromium
pagination/filter/overflow checks. The owner separately approved exactly four
AI-disabled DEEP live cases: Adobe, Dyson, battery recycling and Mary Barra;
once each, <=240 seconds, 24 reads and 120 native HTTP admissions. No audit
retries, paid readers, model calls or deployment. Their outcomes belong in a
dated testing report, separate from replay and from release acceptance.
