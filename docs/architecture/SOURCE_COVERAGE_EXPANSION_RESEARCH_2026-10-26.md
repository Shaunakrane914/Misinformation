# Website and source-family expansion research — 2026-10-26

Expanded at user request: [four-agent topic, celebrity, regional and specialist source matrix](FOUR_AGENT_TOPIC_SOURCE_MATRIX_2026-10-26.md).
The shortlist below is an initial specialist slice, not Trending's universal source set.

## Recommendation

Expand topic, jurisdiction and evidence-type coverage through documented feeds/APIs and observed article links. First prioritize technical research articles, incident-specific regulatory reporting and attributable public statements. Reuse the shared acquisition boundary and the four specialist qualification layers.

**This is researched scope, not implemented or live scraper acceptance.** Official documentation/pages were inspected with web research. No new Aegis investigation, source sweep, model call, credential registration, production mutation or deployment occurred. Application code and existing dirty work are preserved. No assertion of improved word yield is made.

The latest [read-allocation results](../testing/READ_ALLOCATION_RESULTS_2026-10-26.md) demonstrate one fresh battery article but zero qualified semiconductor evidence and historical-only Personal Watch output. Those gaps determine the priorities below. Adding more government and corporate sources alone will not establish independent journalistic corroboration.

## Existing implementation boundary

In the remediation checkout, `expanded_catalog.py` registers Wikipedia, Substack, Yahoo Finance, Trustpilot, Wikidata, Bluesky, Telegram, newswires and GDELT. Its `DOMAIN_DISCOVERY` still chooses one default expanded adapter per domain. The authoritative channel separately handles SEC EDGAR, arXiv, NVD and fact-check discovery. RSS/web readers already support ordinary observed publisher links.

`news/wires_adapter.py` already declares PIB, BBC, AP, Reuters and other hosts. A domain declaration is neither a working endpoint nor a licence/permission assertion. PIB and SEC below are **existing coverage to improve**, not new website integrations. NIST news is a distinct source family from the existing NVD CVE route. Apple/Microsoft pages may already be readable by the generic reader; the proposed addition is reliable discovery and attribution, not a claim that their domains are unsupported today.

Files inspected: [expanded catalog](../../backend/infrastructure/acquisition/adapters/expanded_catalog.py), [planner](../../backend/services/agent_reach/source_planner.py), [authoritative adapters](../../backend/infrastructure/acquisition/adapters/authoritative/channel.py), [newswire adapter](../../backend/infrastructure/acquisition/adapters/news/wires_adapter.py), [safety boundary](../../backend/infrastructure/acquisition/adapters/expansion_safety.py). The original IDE checkout and remediation checkout contain different local states; implementation claims here refer to the remediation checkout.

## Ranked source families

All rows remain **LOCAL ACQUISITION UNVERIFIED** in this exploration. A documented feed proves an intended distribution route; linked-body access, current endpoint behavior, applicable reuse conditions and qualification must still be checked. Priorities are engineering judgments, not guarantees of recall or truth.

| Priority / source | Agent and coverage | Documented route / content | Integration requirement and evidence boundary |
| --- | --- | --- | --- |
| P1 — [MIT News](https://news.mit.edu/rss) | Trending: electronics, energy, materials, manufacturing | Official directory lists main, school and topic RSS feeds, including electrical engineering, materials and energy | Start with topic feed links from the directory; read observed articles. University reporting is a first-party research announcement, not independent replication or measured virality. |
| P1 — [NIST News](https://www.nist.gov/coo/nist-rss-feeds) | Trending; BrandShield when a specific security topic applies | News, electronics, manufacturing, energy and cybersecurity RSS links | Adds topic news beyond existing NVD. A CVE or research announcement does not establish brand compromise, exploitation or impersonation. |
| P1 — [FTC](https://www.ftc.gov/news-events/stay-connected/ftc-rss-feeds) | BrandShield: enforcement, deception and scam warnings | Press releases, consumer protection and business/consumer blog feeds | Separate filed allegations, orders, settlements and generic education. A company's safety advice must not become an observed attacker finding. |
| P1 — [US Department of Justice](https://www.justice.gov/developer/api-documentation/api_v1) | BrandShield; Personal Watch for relevant fraud/impersonation cases | Documented title/date-filterable press-release JSON API, list/detail resources | Retrieve matching release bodies or observed release URLs. Preserve allegation/conviction status, case dates, named entities and attribution. Documentation is not fresh endpoint proof. |
| P1 — [CPSC](https://www.cpsc.gov/Newsroom/CPSC-RSS-Feed) | BrandShield: product safety and recalls | Official recall/news feeds and other published categories | A recall is a product-safety event, not counterfeit or phishing evidence. Requires correct product/company matching and recall identifiers. |
| P1 — [GOV.UK](https://www.gov.uk/help/reuse-govuk-content) | All four: UK notices, CMA decisions, speeches and policy changes | Content API exposes content/metadata for GOV.UK pages; reuse page identifies applicable Open Government Licence conditions | Discover actual pages through bounded search/feed routing, then use their observed paths with Content API. Attribute agency/speaker and separate announcement, guidance and decision. |
| P1 — [Apple newsroom source family](https://www.apple.com/ca/rss/) | Personal Watch/Scout: named executive quotations and issuer statements | Official Canadian RSS directory links Apple Newsroom; public newsroom pages exist | Resolve the observed feed link; do not assume the generic `/rss/` page is a feed. That URL redirected to Apple's homepage during this research. Quotations need exact speaker linkage; merchandising is not evidence of a statement. |
| P1 — [Microsoft Source](https://news.microsoft.com/source/) | Personal Watch/Scout: attributed executive posts, interviews and company statements | Public first-party newsroom with observed article links | The page's search interface says it uses AI and may contain mistakes. Treat any search answer as discovery only; read the underlying article. A feed endpoint was not verified in this exploration. |
| P2 — [NSF](https://www.nsf.gov/rss) | Trending: computing, materials, engineering and research developments | Official news RSS directory and links to full content | Use news as discovery; distinguish award announcements from completed research results. Preserve underlying paper/report links when observed. |
| P2 — [Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | Trending: DOI/title/date discovery and scholarly provenance | Public searchable JSON metadata API; documentation states, “No sign-up is required” | Discovery/metadata, not acquired publisher body. Use deposited publication dates with explicit basis; updates/index dates are different. Read only permitted linked content. Some abstracts have separate copyright. |
| P2 — [Europe PMC](https://europepmc.org/RestfulWebService) | Trending: health, biomedical and life-science claims | Search/metadata API and full-text XML for its open-access subset | Adds structured body acquisition where available. Keep abstracts separate from full text; preserve licence, publication status, retractions and study limitations. Not a general semiconductor source. |
| P2 — [Federal Reserve](https://www.federalreserve.gov/feeds/feeds.htm) | Scout; Personal Watch for relevant policymakers | Published feeds for releases, enforcement, speeches and testimony | Source-specific speaker/date extraction and macroeconomic context. These sources cannot answer arbitrary corporate or private-person queries. |
| P2 — [RBI](https://www.rbi.org.in/Scripts/rss.aspx) | Scout; BrandShield for Indian financial entities | Official RSS documentation lists releases, notifications, speeches and publications | Discover current feed links from the official directory, validate endpoint/access, preserve currency/period and regulatory context. |
| P2 — [SEBI](https://www.sebi.gov.in/rss.html) | Scout/BrandShield: Indian market regulation and enforcement | Official page publishes `https://www.sebi.gov.in/sebirss.xml` for releases, circulars and orders/rulings | Read observed linked order/release; preserve allegation vs final order. PDFs require bounded supported extraction; a filename/snippet is not a complete order. |
| Existing — [PIB](https://www.pib.gov.in/ViewRss.aspx?lang=1&reg=1) | Scout/Trending: Indian policy and ministry releases | Official directory shows press-release feed with `ModId`, language and region parameters | Existing adapter has a PIB feed declaration. Audit its query/region/language behavior rather than adding a duplicate adapter. Government statements remain attributed claims. |
| Existing — [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Scout: filings and period-specific structured financial facts | Submissions/XBRL APIs require no API key; automated access rules still apply | Keep the project's declared contact/User-Agent configuration gate and rate limits. No flag change or invented contact. Match accession, period, currency and units; SEC registration is already implemented. |

## Conditional and deferred candidates

| Source | Value | Current boundary |
| --- | --- | --- |
| [Guardian Open Platform](https://open-platform.theguardian.com/access/) | Independent reporting across politics, science, technology and business, with article text available through its API | Key required. Access page distinguishes developer/non-commercial from commercial use, with developer limits stated as 1 call/second and 500/day. Obtain a suitable key/use classification before integration. No key requested or API called here. |
| [OpenAlex authentication](https://help.openalex.org/api/authentication/) and [pricing announcement](https://blog.openalex.org/openalex-api-new-features-and-usage-based-pricing/) | Broad scholarly discovery, author/work linkage | Documentation evolved: current authentication guidance permits limited keyless basics; production-scale use needs a verified key/budget. Do not label it unrestricted or no-key production access. Metadata/full-text availability differ by work. No registration, email or spend initiated. |
| [OSTI documentation](https://www.osti.gov/api/v1/docs) and [FAQ](https://www.osti.gov/faqs) | Energy/materials research metadata and links to available full-text reports | API offers metadata search and a `has_fulltext` filter. FAQ asks AI/ML/LLM projects to contact OSTI; clarify intended use before integration. Not all records contain full text. One later FAQ fetch returned 502; search-indexed official text was available. |
| [BBC feed documentation](https://support.bbc.co.uk/platform/feeds/NewsFeeds.htm) | Existing independent-news discovery family | Feed documentation links terms. Existing registration does not establish permission for article extraction or republishing; review current provider terms and the intended product use before broadening it. |
| Reddit / X and gated fact-check providers | Community leads, original public posts and fact-check references | Preserve the project's current approval/authentication states. Adding other websites does not grant access to these services or authorize mirrors that circumvent restrictions. |

No claim of universal permission follows from public visibility, an RSS icon or an API specification. Prefer documented interfaces; make source-specific access and attribution decisions at integration time. This is implementation scoping, not a legal opinion.

## Apply the existing two-layer design

1. Resolve subject, jurisdiction, exact task and freshness window. A technical topic routes to technical article sources; a stock symbol is not the default interpretation of a topic phrase.
2. Choose a small relevant subset of source families. The entire catalog must not be searched for every request. Keep initial discovery/read/adaptive reservations, request accounting, per-host limits, cooldowns and the current total ceilings.
3. Normalize **discovery leads**: observed URL, title, provider/publisher, content type, dates with explicit basis and selection reason. A feed summary, DOI record or AI suggestion is not a body.
4. Acquire the actual body through the common safe reader, or a narrow structured-content adapter where documented. Capture URL, hash, timestamps, author/speaker, licence/access basis, truncation and extraction outcome. Validate redirected/API-provided URLs and private addresses normally.
5. Apply the specialist layer: Scout checks period/unit/claim support; Trending checks dates/topic and narrative grouping; BrandShield separates incidents/allegations/warnings; Personal Watch checks exact statement attribution versus commentary/identity allegations. No fabricated filler or lowered evidence gates.
6. Render the acquired, qualified passages with source role and limitations. Keep full inspectable source context distinct from the executive brief. First-party announcements and syndicated copies must not inflate independent-source counts.

## First implementation slice and acceptance

Start with **MIT and NIST topic feeds, FTC/DOJ/CPSC incident discovery, GOV.UK content, and observed company newsroom statements**. Use the existing feed/web reader where sufficient; add an API adapter only where it reduces uncertainty or captures structured content the reader cannot preserve. Then add Indian regulator routing and scholarly discovery. Gated commercial/identity services remain conditional.

Before enabling each family:

- Record one genuine discovery response and one linked body under a small explicit live budget, keeping credentialed/paid APIs disabled unless authorized. New investigation pilots need an agreed case/request ceiling; this research is not such a pilot.
- Build offline regressions for unrelated/empty/blocked results, redirect/access failures, missing/stale dates, duplicated syndication, actual body extraction and exact citations.
- Show the funnel: leads → eligible reads → acquired article/document bodies → qualified sources → useful displayed passages. Report words/KB for acquired bodies and selected passages separately, plus native HTTP admissions and latency.
- Review relevance/support manually. A reasonable initial engineering target is two task-relevant acquired sources where sources actually exist; source count alone cannot establish a supported verdict. Honest access failure/abstention remains valid, but does not pass positive-source acquisition acceptance.
- Use varied subjects and jurisdictions; no hardcoded article URLs or subject-specific shortcuts in production planning. No claim of 20× improvement until comparable observations establish it.

## Verification and state

Performed read-only code/catalog inspection, Git status inspection and official web documentation research. No application code was changed; normal Python/frontend suites were **not rerun for this documentation-only task**. The preceding [2,574/2,366 test snapshot](../testing/READ_ALLOCATION_RESULTS_2026-10-26.md) is dated evidence from the prior repair, not newly executed here. Documentation link/whitespace/protected-diff validation is recorded in the handoff.

No local live scraper acceptance, robots/terms review for every linked article, measured source throughput, new rendered-page proof or production verification was performed. No commit/push/merge/deployment. This document preserves actionable findings and access constraints rather than a private reasoning transcript.
