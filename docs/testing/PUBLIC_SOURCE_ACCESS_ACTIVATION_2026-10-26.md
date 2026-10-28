# Latest continuation

[October 28 deployment, four-agent yield and live Trending historical fallback](DEPLOYED_FOUR_AGENT_WORD_YIELD_2026-10-28.md).
The dated observations below remain preserved as historical evidence.

# Public-source access activation and bounded checks — 2026-10-26

## Decision and scope

**Scoped access controls implemented; useful live article acquisition not demonstrated in this batch.**
FTC's RSS feed was retrieved. Its observed article failed, DOJ acquired no body,
and CPSC's corrected API attempt timed out. There are **zero acquired articles,
zero recall records and zero published evidence words** in these checks. A public
licence review does not establish network access, relevance or claim accuracy.

The user accepted reviewing legitimate public-access routes while retaining
publisher gates. Work is in `.scratch/phase9-remediation-20261016`, branch
`release/specialist-task-20261024`, base `7ad13a59f86a78802e45685ecfd1fd4999a2e5ce`
plus preserved uncommitted work. No publisher agreements were supplied. No
credentials, system DNS/network configuration, historical records, frozen
benchmarks or production services were changed. No commit, push or deployment.

Preceding checkpoint: [individual-site checks](USABLE_SOURCE_REPAIR_AND_SITE_CHECKS_2026-10-26.md).
New [source measurements](evidence/2026-10-26_public_source_access/individual-source-checks.json),
[CPSC recheck](evidence/2026-10-26_public_source_access/cpsc-postfix.json) and
[DNS comparisons](evidence/2026-10-26_public_source_access/dns-comparison.json)
preserve failures as well as progress. Source bodies are not republished in these artifacts.

## What is actually enabled

The operational inventory remains **60 families**, now **61 declared hosts** after
adding the documented CPSC API host. Seven families have scoped public-text/API
reviews, eight retain their existing native-route policy, nine explicitly require
an intended-use agreement, and 36 remain unreviewed. These are configuration
categories, not counts of working scrapers. Earlier evidence inventories remain unchanged.

| Family | Approved scope | Excluded / unproven |
| --- | --- | --- |
| DOJ | Agency-authored OPA press-release text under `/opa/pr/`; `/news` as a discovery directory | Court filings, FOIA, attachments, third-party works, other subdomains and contrary rights notices. No live article acquired here. |
| FTC | Agency-authored `/news-events/news/press-releases/` text; the officially linked press RSS feed for discovery | Public comments, filings, attachments, third-party works and media. Feed text cannot become article evidence. |
| CPSC | Documented recall JSON endpoint, bounded native IDs, dates, descriptions, hazards and remedies | No website-wide body/media grant; API records are agency assertions, not fraud or counterfeit verdicts. Automatic article routing remains disabled. |

The [DOJ policy](https://www.justice.gov/legalpolicies) describes agency public-domain
material and third-party exceptions. The [FTC policy](https://www.ftc.gov/policy-notices/website-policy)
also distinguishes agency material from third-party submissions; lack of a copyright
mark is not sufficient. Both grants are limited to agency press text rather than whole domains.

CPSC's [official API documentation](https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information)
describes developer access to recall records. The official [dataset catalogue's search result](https://catalog.data.gov/dataset/recalls-api)
declared public-domain terms, but directly opening that catalogue URL returned 404
in the research tool. That discrepancy is retained, not described as a successful
current catalogue fetch. The review covers specified API text fields only, with
expiry and no assumption about manufacturer images or other submitted material.

The versioned reviews expire on **2027-01-01**. Static host/path limits remain
binding even if an external server review file grants broader scopes.

## Code changes and reasons

- [SourceRegistry](../../backend/services/research/source_registry.py): missing
  review is `UNVERIFIED`; an explicit restriction/denial is `PERMISSION_REQUIRED`.
  Review approval is separate from unknown or blocked runtime availability.
  Discovery, body, excerpt and external model-processing scopes are independent.
  New agency reviews require exact hosts/paths; encoded traversal and prefix
  collisions cannot widen the grant. Explicit denials also override legacy-route defaults.
- [Definitions](../../backend/services/research/source_registry_data.json) and
  [reviews](../../backend/services/research/source_public_licence_reviews.json):
  scoped DOJ/FTC/CPSC public routes added. Filmfare, Hindustan Times, BCCI, ICC
  and Guardian restrictions are explicit. Earlier Global Voices/GOV.UK/PIB/Sports
  Ministry text reviews remain; no external model scope was inferred for them.
- [EvidenceAdvisor](../../backend/services/research/evidence_advisor.py): rechecks
  model permission before constructing a paragraph prompt or loading/calling a
  gateway, including injected gateways. Optional target-only search advice retains
  existing enablement and shared budget; no model calls were made in this work.
- [PassageExtractor](../../backend/services/research/passage_extractor.py): imported
  text from a known controlled source cannot bypass excerpt permission by omitting
  a metadata flag. [Page extraction](../../backend/infrastructure/acquisition/adapters/web/page_extraction.py)
  retains an observed contrary-rights notice even when cleanup removes its footer.
  Exact raw text, offsets and identities remain preserved.
- [CpscRecallsAdapter](../../backend/infrastructure/acquisition/adapters/consumer/cpsc_recalls.py):
  one bounded JSON lookup, at most five validated records; no guessed IDs/URLs,
  repeated fetch or webpage fallback. Native record IDs and JSON field pointers
  survive normalization. [Expanded discovery](../../backend/infrastructure/acquisition/adapters/expanded_catalog.py)
  preserves bounded `cpsc_*` provenance as discovery-only metadata, without
  presenting snippets as acquired content. The ordinary HTML reader is not intercepted.
  Automatic API-to-report integration is **not** claimed complete.
- [Probe runner](../../scripts/audits/probe_source_families.py): explicit source
  selection, at most four families, 90s/six HTTP admissions/two reads per family.
  CPSC structured counts are separate from body/article/published word counts.
  No implicit sweep when another family gains a review.

### Defects found during these checks

**CPSC first loss: local access preflight.** Its API-only path grant rejected its
own robots document inside `source_body_scope`, before any HTTP admission.
`SourceRegistry.robots_decision` now creates an exact temporary robots-URL lease;
`enforce_scoped_body_access` permits only that document while it is being checked.
One attempt, 5s/128KB, zero redirects, ordinary SSRF/DNS validation and subsequent
robots decisions remain enforced. The lease cannot authorize another host, path,
query or a later direct robots read. The separate live recheck progressed to a
typed HTTP `TIMEOUT`, rather than reproducing this local rejection.

**DOJ/FTC failure cause was lost.** `jina._execute_web_read` discarded nonterminal
native failures when later readers also failed. Its generic result became
`PROVIDER_FAILURE` in DeepReader. [Jina](../../backend/infrastructure/acquisition/adapters/web/jina.py)
now retains the first typed cause and at most three sanitized route observations;
[DeepReader](../../backend/services/research/deep_reader.py) preserves HTTP status
and observed-network flags. Returned and raised access/permission denials remain
terminal. [Expansion safety](../../backend/infrastructure/acquisition/adapters/expansion_safety.py)
also distinguishes DNS/URL preflight failures from empty provider responses.
These corrections were tested offline. The original DOJ/FTC causes are
**irrecoverable from the saved summaries**; their timing does not prove 403 or timeout.

## Authorized live observations

Three initial individual checks ran once each, AI disabled, at most 90 seconds,
six native HTTP admissions and two reader selections per source. CPSC had one
separately approved post-fix recheck with the same bounds. No audit retries,
paid readers, added source sweep or investigation-generation request occurred.

| Check | Seconds | HTTP admissions | Retained discovery words | Articles / recall records | First observed loss |
| --- | ---: | ---: | ---: | ---: | --- |
| FTC | 11.96 | 3 | 937 | 0 / 0 | RSS HTTP200, observed press-article read failed; original typed cause lost |
| DOJ | 4.40 | 2 | 0 | 0 / 0 | Directory read failed; original typed cause lost |
| CPSC initial | 0.02 | 0 | 0 | 0 / 0 | Robots document locally rejected by API path scope |
| CPSC post-fix | 5.40 | 2 | 0 | 0 / 0 | HTTP request timed out; no response/records observed |

**Seven total native HTTP admissions**, not seven successful HTTP responses.
FTC's 937 retained words / 12.039KB came from `FEED_INDEX`; excerpt permission for
that index is false. They are not article-body or published evidence words.
The linked article URL was observed from the feed, not manually supplied.
Both source-check allowances are consumed. There were **zero AI calls**.

The four separately approved DNS-only operations compared OS `getaddrinfo` and
Aegis's public-address guard for DOJ and FTC. All returned public answers in
0.001–0.064s. They made no HTTP requests and changed no settings. Sequential
lookups can benefit from OS caches; these observations do not explain historical
DNS timeouts or establish HTTP access. No persistent resolver defect was proven.

## Private publisher access still needs an agreement

There is a legitimate access route, but public browsing/RSS availability is not
an agreement for this product. [Filmfare content usage](https://www.filmfare.com/copyright-and-content-usage-policy)
and [HT Syndication](https://www.htmedia.in/ht-syndication) provide clearance or
licensing paths. [Indian Express terms](https://indianexpress.com/terms-and-conditions/)
include a syndication route. [BCCI copyright](https://www.bcci.tv/news/article/copyright)
and [ICC terms](https://www.icc-cricket.com/about/the-icc/legal-notices/website-terms-of-use)
describe their clearance requirements. [Guardian access tiers](https://open-platform.theguardian.com/access/)
need an intended-use review; an API key alone is insufficient.

An agreement must cover the actual use: automated discovery, body retrieval and
retention, excerpt display with attribution, and external AI processing if wanted.
No enquiries were sent, account/key requested, payment made or agreement fabricated.
Restricted publishers remain gated. More public incident sources do not fill the
entertainment/sports coverage gap by themselves.

## Verification and limits

Final command results are recorded in the [handoff](../handoffs/2026-10-26_PUBLIC_SOURCE_ACCESS_ACTIVATION.md).
New controls cover scope separation, imported text, exact robots leases,
encoded paths, native recall provenance, article/index distinction, typed failures
and successful fallback preservation. Saved genuine event captures keep their
original expected classifications under explicitly synthetic test-only permission
fixtures; those fixtures do not approve their publishers for production.

No new rendered-browser run, fresh four-agent research matrix, independent
passage-accuracy evaluation, hosted CI, historical dossier recovery, deployed
rollback or production acceptance was performed. A passing offline suite cannot
convert the measured zero-article result into research acceptance. Next work is
bounded transport verification with the repaired diagnostics, plus obtaining
source-specific agreements for the desired entertainment/sports coverage.
