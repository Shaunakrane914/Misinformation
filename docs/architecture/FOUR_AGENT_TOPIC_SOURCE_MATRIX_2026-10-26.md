# Four-agent topic and website coverage matrix — 2026-10-26

## Correction to the earlier shortlist

The user correctly identified that a technical-research shortlist cannot serve a Bollywood celebrity query. This document expands the [initial source research](SOURCE_COVERAGE_EXPANSION_RESEARCH_2026-10-26.md) into topic-specific selection for **each agent**. MIT/NIST/Europe PMC remain useful for appropriate subjects; they are not Trending's general default.

The [machine-readable candidate catalog](source_candidates_2026-10-26.json) records **58 source families**, with proposed mappings to Trending (38), Scout (23), BrandShield (27) and Personal Watch (36). These counts overlap and include existing adapters, conditional sources and new proposals. They are **not 58 newly implemented scrapers or proven available websites**. Every entry is research scope, globally `runtime_enabled: false`, with local acquisition `NOT_RUN`. Source mappings indicate possible relevance, not permission to query all mapped sites.

Official publisher directories/pages were reviewed through web research, building on the preceding official-source exploration. No Aegis investigation, crawler sweep, model call, credential change or application implementation was performed. Some web-tool fetches failed; those observations are retained below and in the catalog rather than silently presented as accessible bodies.

## Trending: broad topics, then specialist sources

| User topic | Selected candidate websites / source families | What the agent should seek |
| --- | --- | --- |
| Bollywood celebrities, films, interviews, box office | [Bollywood Hungama RSS](https://www.bollywoodhungama.com/rss-feed/), [Filmfare](https://www.filmfare.com/), [Hindustan Times directory](https://www.hindustantimes.com/rss), [Indian Express entertainment sections](https://indianexpress.com/rss/), [NDTV movies](https://www.ndtv.com/rss?site=classic), [Yash Raj Films](https://www.yashrajfilms.com/) when entity-linked | Dated reporting, original interview or studio statement. Distinguish announcement, promotional copy, rumour, reported quotation and box-office estimate. |
| Hindi/regional entertainment and local developments | [Live Hindustan](https://www.livehindustan.com/rss), Indian Express regional/Tamil sections, relevant Filmfare regional interviews; original studio sources identified from the actual subject | Native-language text, regional titles/aliases and attributed quotes. This first catalog adds Hindi/regional coverage but does not establish all Indian-language coverage. |
| Hollywood, television, international entertainment | [Variety](https://variety.com/), [Deadline](https://deadline.com/), HT Hollywood, Filmfare Hollywood, conditional [Guardian](https://open-platform.theguardian.com/access/); original production announcements where relevant | Industry reporting with dates and attribution. Variety and Deadline returned web-tool 402 responses here; both remain conditional, not accessible positive controls. |
| Cricket and sports figures | [BCCI](https://www.bcci.tv/), [ICC](https://www.icc-cricket.com/news), Indian Express sports, NDTV sports, [Business Standard sports directory](https://www.business-standard.com/rss-feeds/listing), HT sports | Official squad/result/disciplinary announcements plus reporting and original press conferences. Broader sports require the relevant federation/team source; cricket coverage alone is not all-sport coverage. |
| Indian politics, elections, public policy | [PIB](https://www.pib.gov.in/ViewRss.aspx?lang=1&reg=1), [ECI](https://www.eci.gov.in/), [PRS](https://prsindia.org/), Indian Express, NDTV and regional reporting | Original notice/speech/record, independent reporting and fact-checks of the exact claim. ECI fetch timed out in this research; do not assume runtime access. PRS is legislative analysis, not the issuing government record. |
| International public affairs | [GOV.UK](https://www.gov.uk/help/reuse-govuk-content), conditional Guardian, existing permitted international reporting sources, appropriate originating public body | Jurisdiction-specific statement/document plus independent reporting. This shortlist remains English/India-heavy; it does not establish worldwide coverage. |
| Technology, startups, semiconductors, manufacturing | [TechCrunch](https://techcrunch.com/), [The Register](https://www.theregister.com/), [NIST topic feeds](https://www.nist.gov/coo/nist-rss-feeds), [MIT topic feeds](https://news.mit.edu/rss), [NSF](https://www.nsf.gov/rss), relevant company engineering/news releases | Dated technical/industry articles. Topic queries must not default to stock-profile pages or unrelated founder biographies. |
| Health, medicine, science | [WHO](https://www.who.int/news-room), [Europe PMC](https://europepmc.org/RestfulWebService), [Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/), relevant NSF/MIT sources and reporting | Original study/advisory, publication status, evidence limits and proper dates. Crossref metadata is discovery; eligible Europe PMC full text is a different acquisition depth. |
| Business, products, consumer topics | [Mint](https://www.livemint.com/rss), [Business Standard](https://www.business-standard.com/rss-feeds/listing), [Economic Times](https://economictimes.indiatimes.com/rss.cms), [Moneycontrol Hindi](https://hindi.moneycontrol.com/rss), issuer releases and relevant regulator records | Actual developments, separately labeled sponsored/product material and independent reporting. Price movement and promotional claims do not establish public attention. |
| Viral claims across these topics | [BOOM](https://www.boomlive.in/about-us), [AFP Fact Check](https://factcheck.afp.com/How-we-work), [Full Fact](https://fullfact.org/about/), existing authorized YouTube/Bluesky/Reddit/X routes | Exact claim/media context, original statement and corrections. Community posts are leads; virality requires observations over time, not an article count or social-profile bio. |

Bollywood Hungama explicitly lists news, features, reviews, release dates and box-office feeds. That makes it a more relevant discovery candidate for this example than a science repository. A film announcement still does not verify a celebrity rumour or establish popularity. Publisher RSS restrictions and linked-body access remain separate checks.

## Scout: financial coverage across company types and markets

| Research need | Candidate websites / source families | Interpretation requirement |
| --- | --- | --- |
| US and foreign issuers filing in the US | [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), entity-linked issuer investor relations | Actual accession/filing/table; reporting period, currency, units, restatements and issuer statement role. Existing SEC configuration gate remains. |
| Indian company announcements | [NSE](https://www.nseindia.com/static/rss-feed), [BSE](https://www.bseindia.com/corporates/ann.html), issuer filings/IR | Exchange and symbol validation; access/usage review before automation. BSE returned 403 in the research tool; no undocumented endpoint/bypass is proposed. |
| Indian regulation and banking | [SEBI](https://www.sebi.gov.in/rss.html), [RBI](https://www.rbi.org.in/Scripts/rss.aspx), PIB ministry releases | Distinguish rule, allegation, interim/final order, policy statement and company-specific fact. |
| Hong Kong listings | [HKEXnews](https://www.hkexnews.hk/index.htm?sc_lang=en), issuer annual/interim reports | Correct listing/market/currency; document search is documented, automated ingestion remains unverified. Useful for companies whose primary listing is outside US/India. |
| UK corporate identity / regulated firms | [Companies House](https://developer-specs.company-information.service.gov.uk/guides/quickStart), [FCA](https://www.fca.org.uk/consumers/warning-list-unauthorised-firms) | Companies House API requires a key; filed identity is not a guarantee of legitimacy. FCA warnings need exact firm/domain matching. |
| Business reporting / executive context | Mint, Business Standard, Economic Times, Moneycontrol Hindi, Indian Express business, NDTV business, The Register/TechCrunch when sector-relevant | Independent reporting and claim-specific passages. Conditional Guardian for suitable international coverage; do not use a headline or market landing page as financial proof. |
| Monetary and policy context | [Federal Reserve](https://www.federalreserve.gov/feeds/feeds.htm), GOV.UK, RBI, PRS | Clearly distinguish macroeconomic context from evidence for the company's own financial claim. |

The manifest maps 23 candidate families to Scout. The generic issuer IR family remains dynamically entity-linked, not an ever-growing list of special cases. Existing Yahoo market telemetry remains separate from newly proposed article sources and is not counted as a new integration here.

## BrandShield: cover different threat types, not just product pages

| Threat / issue family | Candidate websites / source families | Interpretation requirement |
| --- | --- | --- |
| Named fraud, deception and legal cases | [FTC](https://www.ftc.gov/news-events/stay-connected/ftc-rss-feeds), [DOJ](https://www.justice.gov/developer/api-documentation/api_v1), SEBI, SEC and GOV.UK agencies where relevant | Match actual entity, action and case stage. A press release's allegation is not a conviction; a generic warning is not an observed attack. |
| Financial clone firms / unauthorised sellers | [FCA Warning List](https://www.fca.org.uk/consumers/warning-list-unauthorised-firms), RBI/SEBI notices, [Scamwatch](https://www.scamwatch.gov.au/) | Match domain/product/jurisdiction. No listing on a warning page is not proof of safety or authorisation. |
| Product-safety events | [CPSC](https://www.cpsc.gov/Newsroom/CPSC-RSS-Feed), [FDA](https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts), [EU Safety Gate](https://ec.europa.eu/safety-gate-alerts/screen/webReport) | Product model/batch and exact recall action. These are safety sources, not automatic counterfeit findings. Safety Gate exposed only a JS shell in this research. |
| Phishing / reported cyber incidents | [SecurityWeek](https://www.securityweek.com/), [BleepingComputer](https://www.bleepingcomputer.com/), The Register, relevant original vendor advisories | Specific reported campaign/incident and primary technical references. BleepingComputer timed out in this tool; access remains unverified. |
| Technical vulnerability context | [CISA](https://www.cisa.gov/known-exploited-vulnerabilities-catalog), [CERT-In](https://www.cert-in.org.in/), existing NVD, NIST | Vulnerability/exploitation context is not proof that the investigated company was breached. CISA web fetch returned 403; CERT-In yielded no readable text. |
| Misleading ads / endorsements | [ASA rulings](https://www.asa.org.uk/codes-and-rulings/rulings.html), FTC and exact-claim fact-checks from BOOM/AFP | Preserve upheld/not-upheld/informal outcomes. Celebrity endorsement rumours require original ad/statement evidence. |
| Complaints and suspected impersonation leads | Existing Trustpilot review family, permitted Reddit/Bluesky/X observations, entity-linked official warnings | Complaints and public accusations remain allegations with sampling/access limits. Do not treat multiple copies of one complaint as independent corroboration. |

The manifest maps 27 candidate families to BrandShield; shared families are counted once in the overall catalog. Marketplace listings can be useful direct inputs, but this plan does not claim Amazon/Flipkart or authenticated marketplace crawling without a verified permitted integration.

## Personal Watch: choose by the person's role and the allegation

| Subject / task | Candidate websites / source families | Interpretation requirement |
| --- | --- | --- |
| Bollywood / regional actors | Bollywood Hungama, Filmfare interviews, HT entertainment, Indian Express entertainment, NDTV interviews, Live Hindustan; actual studio/representative statements such as YRF when relevant | Exact speaker attribution, original-language quotation and event date. Gossip or a profile cannot verify a false quote or identity claim. |
| International actors / musicians | Conditional Variety/Deadline/Guardian, relevant HT/Filmfare international coverage, original interview/publisher recording | Do not imply access to unavailable trade sites. A publicist statement is attributed first-party evidence; a publisher repeating it is not independent confirmation. |
| Executives / entrepreneurs | [Apple newsroom directory](https://www.apple.com/ca/rss/), [Microsoft Source](https://news.microsoft.com/source/), issuer IR, Mint/ET/Business Standard, TechCrunch and original interview recordings | Reported speech versus commentary; current role/identity ambiguity preserved. Companies House/filings provide limited identity context, not authenticated speech. |
| Athletes | BCCI/ICC releases and original press conferences, sports interviews from topic publishers | Official team announcement versus player statement; quotation must match the actual speaker. Other sports need their relevant originating organizations. |
| Politicians / public officials | PIB, GOV.UK speeches, Federal Reserve, ECI records where relevant, PRS plus news reporting | Authority of the issuing institution, speech/event date, translation and quoted claim. Official publication is not independent agreement with its claim. |
| False quotations / synthetic-media allegations | BOOM, AFP Fact Check, Full Fact, originating recording/document, authorized public-post routes | Match the exact claim/media version; cite the fact-check's underlying evidence. Do not infer that acquired text alone performs audio/image forensics. |
| Reported impersonation scams | FTC/DOJ/Scamwatch named incidents, official subject warning, relevant reporting/community leads | Distinguish the impersonated person from an alleged perpetrator; generic advice is not a verified incident. |

The manifest maps 36 candidate families to Personal Watch. This is role-dependent selection, not permission to query all of them for every name. Public statements, identity context and reported identity threats remain separate evidence roles.

## Routing contract and example

Use **agent task + topic + subject type + language + jurisdiction + time window**, with confidence and explicit ambiguity. Support multiple topics when justified; unknown subjects use neutral broad discovery and classification from observed titles/pages before specialist fan-out. An optional bounded AI suggestion may propose a validated query; deterministic routing must work without a generation call.

For an ordinary Bollywood-celebrity query (illustrative plan, not a new investigation):

1. Establish that the name refers to an entertainment figure; preserve same-name ambiguity and regional-language aliases.
2. Select an initial three to five relevant sources, such as Bollywood Hungama plus eligible entertainment reporting and an observed original interview/studio source. Choose from actually available/approved sources, not all catalog rows.
3. Search for named subject plus requested event/claim and date window. A category's recent feed is not a complete celebrity archive; older exact-claim tasks may require the site's permitted search or ordinary indexed discovery.
4. Read the strongest observed article URLs. Separate news, interview, promotion, rumour and fact-check. Compare event date to article publication/update dates and maintain quote offsets.
5. If reads fail or yield irrelevant coverage, reallocate the remaining bounded discovery budget to another eligible entertainment source. If none provides evidence, report the real failure/gap; do not fall back to unrelated technical sources to inflate counts.
6. Render sourced developments or attributed passages. A single coverage snapshot may show recent reporting; it cannot establish narrative acceleration or virality without repeated comparable observations.

Same routing mechanism, different task: a financial allegation about a film studio routes Scout to company filings/financial reporting, not box-office gossip; a fake celebrity-endorsed product routes BrandShield to the actual ad, subject statement, incident sources and exact-claim fact-checks.

## Availability, terms and implementation order

Source relevance, network access and applicable usage rights are three independent properties. Official RSS directories were found for Bollywood Hungama, HT, Indian Express, NDTV, Live Hindustan, Mint, Business Standard, Economic Times and Moneycontrol Hindi. Only the Hindi Moneycontrol directory was reviewed, so the catalog does not assert an English Moneycontrol feed.

Indian Express, NDTV, Mint and Economic Times publish feed-use restrictions; these entries require an intended-use decision and, where applicable, appropriate permission/licensing before Aegis product ingestion/redistribution. This is not an instruction to bypass restrictions by changing readers, using mirrors or extracting bodies through a different provider. Filmfare's page exposes interviews and content-usage links, but this exploration did not establish an automated-use licence. Source bodies and screenshot/republication rights remain separate.

The catalog also records research-tool failures rather than hiding them: Variety/Deadline 402; BSE/CISA 403; ECI/BleepingComputer timeout; Safety Gate/CERT-In no usable rendered text. These are observations from this browser research, not measured Aegis provider health. Guardian/Companies House remain key-dependent; existing Reddit/X access gates remain. No credentials or access flags were changed.

Implementation sequence:

1. Add the topic/role/language mapping and availability filtering to the existing planner with deterministic offline tests: Bollywood name, regional actor, athlete, unfamiliar company, ambiguous name, politics and semiconductor topic. The JSON here is reference research, not imported runtime configuration.
2. Integrate a small approved entertainment/regional-news slice and original-statement discovery, alongside task-specific regulator/incident routing. Reuse existing RSS/web parsing; do not create a full scraper class per hostname when the common reader suffices.
3. Validate one discovered article body per family under an agreed bounded pilot, then evaluate diverse subjects. Publisher snapshots and robots/access/use checks must precede enabling a source; this research has not supplied those runtime proofs.
4. Add failures/candidates/selected bodies/qualified passages/word yield by topic and source. Assess both exact-claim support and abstention, not only large text counts.
5. Use the fixed total budgets and adaptive read reservations. Broader catalog size must not multiply each request's cost. Run impacted, full/fast, security, frontend and source-to-browser checks when code changes stabilize; no deployment until acceptance.

## Validation scope

Documentation/catalog only. New JSON schema invariants, URL structure, agent/topic coverage, relative links and whitespace were checked locally. No live Aegis/AI calls, application changes, suite reruns or deployment. Existing dirty work, dossiers and frozen data remain preserved. This plan expands proposed coverage; it does not claim every public figure/topic can now be researched or every catalog site can be scraped.
