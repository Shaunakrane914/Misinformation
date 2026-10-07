# SCOUT SOURCE ENGINE ARCHITECTURE AUDIT
**Aegis Protocol — Agent 1: Scout Proprietary Source Acquisition Engine**
*Phase 1 Deliverable — Repository Audit & Architectural Gap Analysis*

---

## Executive Summary

Scout in the Aegis Protocol is **Agent 1 — the Trading & News Intelligence Agent**. Its core mandate is to:
1. Detect market-moving catalysts and price/volatility anomalies.
2. Formulate targeted investigations for affected corporate entities and assets.
3. Discover, acquire, and extract structured financial evidence from public sources.
4. Distinguish between official filings, verified reporting, speculative rumors, and misinformation.
5. Identify contradictions, assess corroboration, and deliver structured trading/news intelligence.

The 200-case semantic retrieval benchmark (`semantic_retrieval_correctness_benchmark_20261007_003000`) conclusively demonstrated that:
- **Top-1 search selection is fundamentally flawed**: Naive search rank yields only **67% correct source selection** on Reddit and **34%** on X/Twitter.
- **Deeper candidate exploration is required**: Top-5 and Top-10 candidate generation with semantic validation boosts correct source selection to **76%+** and claim support to **72%+**.
- **Search results are merely candidates**, not verified evidence.

To achieve production excellence, Scout cannot rely on ad-hoc wrappers, generic scraping libraries, or monolithic dispatchers. It requires its own **proprietary source acquisition, structured extraction, financial entity parsing, and corroboration engine** built directly into Aegis.

---

## 1. Current Scout Architecture

### 1.1 The Agent Layer (`backend/agents/scout_agent.py`)
- **Current Responsibilities**:
  - Statistical anomaly detection (Z-score calculation, 2-sigma thresholds, daily closing price momentum).
  - Ticker & corporate entity resolution (`resolve_ticker_and_company`).
  - Stock impact prediction (drift-dampened 1-hour projections based on empirical volatility envelopes).
  - External investigation delegation to `ResearchEngine` (`backend/services/research/research_engine.py`) via `ResearchRequest`.
  - Omni-channel social sentiment scanning via `agent_reach_service.omni_scan`.
  - Evidence synthesis and catalyst classification via `_synthesize_financial_intelligence` using Google Gemini with deterministic rule-based fallbacks.
- **Downstream Consumers**:
  - `backend/agents/coordinator_agent.py`: `CoordinatorAgent` (Strategic Crisis Governor) uses Scout as Step 1 ("Financial Surveillance").
  - `backend/api/agents.py`: Endpoints `POST /api/scout/analyze` and `POST /api/scout/task` serve the Scout intelligence stream to the web frontend and external callers.

### 1.2 The Research & Retrieval Subsystem
- `ScoutAgent.analyze_stock()` dispatches a `ResearchRequest` to `ResearchEngine.investigate()`.
- `ResearchEngine` utilizes `RetrievalPlanner` to generate 7 query classes (`latest_primary`, `official_statement`, `regulatory`, `investigative`, `independent_reporting`, `community_signal`, `contradiction`).
- `RetrievalPlanner` calls `AgentReachService` (`backend/services/agent_reach/adapter.py`).
- `AgentReachService` dispatches queries across heterogeneous channels (`NewsChannel`, `WebChannel`, `RssChannel`, `RedditChannel`, `TwitterChannel`, `YouTubeChannel`, `GitHubChannel`, `JinaReaderChannel`).
- Channels delegate to `NativeRouter` (`backend/services/agent_reach/native/router.py`), which executes native CLI tools, direct REST APIs, public mirrors (Arctic Shift, FxTwitter), or legacy scrapers.

---

## 2. Current Source Acquisition Flow

```text
ScoutAgent.analyze_stock()
       │
       ▼
ResearchEngine.investigate(ResearchRequest)
       │
       ▼
RetrievalPlanner.build_plan()
       │
       ▼
AgentReachService.retrieve_plan()
       │
       ▼
NativeRouter.execute_channel_query()
 ┌─────┴──────────────────┬───────────────────┬─────────────────────┐
 ▼                        ▼                   ▼                     ▼
Bing/Yahoo Search     Arctic Shift API     FxTwitter API      Jina Reader / Scraper
(Web / News)          (Reddit Mirror)     (X / Twitter)      (Full Document Read)
```

### Flow Breakdown:
1. **Search Query Generation**: `RetrievalPlanner` creates static queries combining entity name, ticker, and keywords (e.g., `"Tata Motors quarterly earnings"`).
2. **Search Index Query**: `NativeRouter._execute_web_search()` scrapes Bing HTML or Yahoo Search HTML using regex/BeautifulSoup.
3. **URL Extraction**: For Reddit and X, `source_discovery.py` parses URLs out of search snippets and queries Arctic Shift (`arctic-shift.photon-reddit.com`) or FxTwitter (`api.fxtwitter.com`).
4. **General Web Retrieval**: URLs are fetched either via Jina Reader (`r.jina.ai/<url>`) or direct HTTP with basic BeautifulSoup tag stripping.
5. **Fragment Packaging**: Extracted content is wrapped in `EvidenceFragment` and returned upstream.

---

## 3. Existing Reusable Infrastructure

Aegis contains robust, battle-tested components that Scout's new source engine will directly leverage rather than reinventing:

| Component | Location | Reusable Assets |
|---|---|---|
| **Data Models** | `backend/services/agent_reach/channels.py` | `EvidenceFragment`, `RetrievalMode`, `ChannelStatus`, `QueryExecutionRecord` |
| **Research Models** | `backend/services/research/research_models.py` | `EvidenceItem`, `SourceRole`, `SourceTier`, `ContentDepth`, `QualityTensor`, `FindingType` |
| **Source Discovery** | `backend/services/agent_reach/native/source_discovery.py` | `SourceDiscoveryResult`, `extract_reddit_source`, `extract_x_source`, `check_entity_semantic_match`, `calculate_candidate_score` |
| **URL Security** | `backend/services/url_validator.py` | `validate_url_safe`, SSRF protection, IP/port filtering, scheme enforcement |
| **Native Execution** | `backend/services/agent_reach/native/` | `native_doctor` (runtime probing), `native_executor` (safe CLI runner), `native_normalizer` |
| **LLM Reasoning** | `backend/services/gemini_service.py` | Multi-key rotational Gemini access for synthesis and classification |
| **Installed Libraries** | Python Environment | `requests`, `httpx`, `bs4`, `feedparser`, `scrapling`, `playwright`, `yt_dlp` |

---

## 4. Existing Duplicate & Fragile Retrieval Code

The audit revealed significant code duplication and maintenance friction:

1. **Duplicate Web Search Scrapers**:
   - `NativeRouter._execute_web_search()` (Bing scraping in `router.py`, lines 1152–1214).
   - `AgentReachScraper.search_reddit()` (Bing News RSS in `agent_reach_scraper.py`, lines 63–92).
   - `AgentReachScraper.search_news()` (Bing News RSS in `agent_reach_scraper.py`, lines 315–368).
2. **Duplicate Reddit Acquisition**:
   - `NativeRouter._fetch_arctic_shift_posts_batch()` (Arctic Shift in `router.py`, lines 85–158).
   - `AgentReachScraper.search_reddit()` (PullPush API in `agent_reach_scraper.py`, lines 94–140).
3. **Duplicate Web Extraction**:
   - `NativeRouter.execute_channel_read()` (Jina Reader + BS4 fallback in `router.py`, lines 1029–1150).
   - `AgentReachScraper.read_article_markdown()` (Jina Reader + BS4 fallback in `agent_reach_scraper.py`, lines 379–455).
4. **Duplicate Ticker & Entity Mappings**:
   - `ScoutAgent.resolve_ticker_and_company()` maintains an in-line dictionary in `scout_agent.py` (lines 486–493).
   - `TICKER_NAME_MAP` in `backend/services/agent_reach/planner.py` maintains an overlapping map.

---

## 5. Missing Capabilities in Current Architecture

Despite high functional coverage, the current system lacks critical capabilities required for a serious **Trading & News Intelligence Agent**:

1. **No Structured Financial Fact Extraction**:
   - Current scrapers extract raw unparsed text.
   - Numbers like `"$5.4B revenue"`, `"+15% YoY"`, `"$1.25 EPS"`, `"200 bps margin expansion"` are left as raw strings without normalized metrics, units, periods, or directions.
2. **No Structured Corporate Event Extraction**:
   - No formal categorization of corporate actions (`GUIDANCE_CHANGE`, `EARNINGS`, `M_AND_A`, `CAPEX_CHANGE`, `REGULATORY_ACTION`, `PRODUCT_LAUNCH`, `FINANCING`).
3. **No Separation of Publication Time vs. Event Time**:
   - Current systems conflate `published_at` (when an article was posted) with `event_at` (when the event occurred in the real world). This prevents evaluating whether the market has already digested the news.
4. **No Wire Syndication Deduplication**:
   - An AP or Reuters press release republished across Yahoo Finance, Investing.com, and MarketWatch is counted as multiple independent sources rather than 1 primary report + syndicated echoes.
5. **No Financial Contradiction Detection**:
   - When Source A claims a deal value of `$2.0B` and Source B claims `$3.5B`, the system lacks logic to flag an explicit factual contradiction (`conflicting_information = True`).
6. **No Rumor vs. Confirmed Status Classification**:
   - Inability to distinguish unconfirmed social commentary or anonymous leaks from official regulatory filings or verified disclosures.
7. **Search Rank Dependency (Top-1 Bias)**:
   - Queries blindly prioritize the first returned search result without checking semantic relevance or evaluating deeper candidate sets.

---

## 6. Current Bottlenecks & Failure Modes

1. **Monolithic Router (`router.py`)**: At 1,379 lines and 73KB, `router.py` attempts to manage routing, HTTP fetching, social scraping, search engine HTML parsing, and caching in a single class.
2. **Search Engine Rate-Limiting**: Bing and Yahoo scrapers lack token-bucket pacing, risking bot challenges or IP blocks during concurrent multi-query sweeps.
3. **Jina Reader Latency & External Availability**: Relying on `r.jina.ai` introduces external network hops and potential latency spikes (1.5s–4.0s). Direct DOM extraction with structured metadata parsing (JSON-LD, OpenGraph) is faster and more reliable for most articles.
4. **Token-Cheat False Positives**: Naive searches for single tokens (e.g. "Satya" on Reddit) hit unrelated communities (e.g. `r/Incense`) unless strict multi-word context validation is enforced.
5. **Scope Leakage**: Failing to validate that a Reddit candidate matches the requested subreddit allows off-topic community posts to leak into financial intelligence.

---

## 7. Current Provenance & Telemetry Status

- **Existing Strengths**: `EvidenceFragment` and `EvidenceItem` track `query_id`, `query_class`, `channel`, `retrieval_mode`, and basic timestamps.
- **Current Deficits**:
  - Missing exact acquisition method (e.g. whether an article was fetched via direct structured JSON-LD, Scrapling, Jina Reader, or Playwright).
  - Missing source tier (`TIER_1_PRIMARY`, `TIER_2_PRESS`, `TIER_3_COMMUNITY`).
  - Missing corroboration count and independent source clustering ID.
  - Missing detailed latency breakdown across discovery, acquisition, extraction, and validation phases.

---

## 8. Recommended Scout Source Engine Architecture

Scout's proprietary source acquisition engine will be built under:
```text
backend/services/agent_reach/scout/
```
as a **dedicated, high-performance evidence acquisition infrastructure layer**.

### 8.1 Architectural Diagram

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        SCOUT INTELLIGENCE AGENT                        │
│                (Trading & News Intelligence Orchestrator)              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                        ScoutSourceRequest
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          SCOUT SOURCE ENGINE                           │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ 1. DISCOVERY ENGINE                                                │ │
│ │    • BingDiscovery     • YahooDiscovery    • DirectDomainDiscovery │ │
│ │    • CompanyIRDiscovery• SECDiscovery      • SocialDiscovery       │ │
│ │    • Query Expansion   • Candidate Deduplication & Normalization   │ │
│ └──────────────────────────────────┬─────────────────────────────────┘ │
│                                    │ CandidateSource[]                 │
│ ┌──────────────────────────────────▼─────────────────────────────────┐ │
│ │ 2. HARD GATES & CANDIDATE VALIDATION                               │ │
│ │    • Platform Scope Gate   • URL Structure Gate  • SSRF Gate       │ │
│ │    • Anti-Token-Cheat Gate • Domain Integrity Gate                 │ │
│ └──────────────────────────────────┬─────────────────────────────────┘ │
│                                    │ ValidatedCandidate[]              │
│ ┌──────────────────────────────────▼─────────────────────────────────┐ │
│ │ 3. ACQUISITION CASCADE (Connection Pooled & Bounded Concurrency)   │ │
│ │    Tier 1: Native / Direct REST API                                │ │
│ │    Tier 2: Public Zero-Auth Mirror (Arctic Shift / FxTwitter)       │ │
│ │    Tier 3: Direct HTTP + Connection Reused Session                 │ │
│ │    Tier 4: Scrapling / DOM Parser                                  │ │
│ │    Tier 5: Jina Reader / Playwright (when strictly justified)      │ │
│ └──────────────────────────────────┬─────────────────────────────────┘ │
│                                    │ RawSource[]                       │
│ ┌──────────────────────────────────▼─────────────────────────────────┐ │
│ │ 4. EXTRACTION ENGINE                                               │ │
│ │    • StructuredMetadataExtractor (JSON-LD, OpenGraph, microdata)   │ │
│ │    • FinancialNumberExtractor ($5.4B, 200 bps, EPS, currencies)    │ │
│ │    • CorporateEventExtractor (EARNINGS, M&A, GUIDANCE_CHANGE, etc) │ │
│ │    • TemporalExtractor (event_time vs publication_time)            │ │
│ │    • Content & Bylines Extractor                                   │ │
│ └──────────────────────────────────┬─────────────────────────────────┘ │
│                                    │ ExtractedSource[]                 │
│ ┌──────────────────────────────────▼─────────────────────────────────┐ │
│ │ 5. CORROBORATION & DEDUPLICATION ENGINE                            │ │
│ │    • URL & Content Canonicalization • Wire Syndication Clustering   │ │
│ │    • StoryCluster Construction      • Primary Source Verification  │ │
│ │    • Contradiction Detection        • Rumor vs. Confirmed Status   │ │
│ └──────────────────────────────────┬─────────────────────────────────┘ │
│                                    │                                   │
│ ┌──────────────────────────────────▼─────────────────────────────────┐ │
│ │ 6. RANKING, NORMALIZATION & PROVENANCE                             │ │
│ │    • Multi-Axis Quality Tensor Ranking                             │ │
│ │    • Canonical EvidenceFragment Normalization                      │ │
│ │    • Comprehensive Provenance & Telemetry Metadata                 │ │
│ └────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                               ScoutEvidence
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        SCOUT INTELLIGENCE AGENT                        │
│          (Market Impact Analysis, Catalysts, Risks & Synthesis)        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Implementation Plan & Deliverable Mapping

To ensure zero downtime and complete backward compatibility, implementation will proceed systematically:

### Files to be Created:
1. `SCOUT_SOURCE_ENGINE_AUDIT.md` (Phase 1 — this audit).
2. `SCOUT_SOURCE_ENGINE_DESIGN.md` (Phase 2 — architectural specification).
3. `SCOUT_DATA_MODEL.md` (Phase 3 — strongly typed data contracts).
4. `SCOUT_SOURCE_POLICY.md` (Phase 3 — source tiering & acquisition policies).
5. `SCOUT_EXTRACTION_SPEC.md` (Phase 3 — financial numbers, events, and schemas).
6. `SCOUT_FAILURE_MODEL.md` (Phase 3 — structured failure taxonomy).
7. `backend/services/agent_reach/scout/__init__.py`
8. `backend/services/agent_reach/scout/models.py` (Request, Candidate, Fact, Event, Cluster, Evidence models).
9. `backend/services/agent_reach/scout/transport.py` (Session pooling, rate limiter, SSRF verification).
10. `backend/services/agent_reach/scout/discovery.py` (Multi-source discovery strategies).
11. `backend/services/agent_reach/scout/adapters/` (Web, News, Reddit, X, YouTube, GitHub, SEC/IR adapters).
12. `backend/services/agent_reach/scout/extraction/` (Structured metadata, financial numbers, events, temporal).
13. `backend/services/agent_reach/scout/deduplication.py` (URL hashing, syndication clustering).
14. `backend/services/agent_reach/scout/corroboration.py` (Story clustering, contradiction detection, rumor status).
15. `backend/services/agent_reach/scout/ranking.py` (Hard gates, scoring, candidate ranker).
16. `backend/services/agent_reach/scout/cache.py` (Bounded TTL cache with freshness tiers).
17. `backend/services/agent_reach/scout/telemetry.py` (Provenance ledger, metrics collection).
18. `backend/services/agent_reach/scout/engine.py` (Master `ScoutSourceEngine` orchestrator).
19. `tests/unit/test_scout_source_engine.py` (Comprehensive test suite).
20. `SCOUT_TEST_REPORT.md` (Test execution and verification report).

### Files to be Modified:
1. `backend/agents/scout_agent.py`: Wire `ScoutSourceEngine` directly into `ScoutAgent` while preserving existing public methods (`analyze_stock`, `process_task`, `correlate_social_rumors`).
2. `backend/services/agent_reach/adapter.py`: Integrate Scout engine capabilities into `AgentReachService` for unified evidence resolution.
3. `backend/services/agent_reach/native/router.py`: Route complex multi-candidate financial acquisitions through Scout's optimized adapters.

---

## 10. Audit Conclusion & Next Steps

The repository possesses strong foundational primitives, but lacks a dedicated, structured, financial-grade acquisition engine. By keeping Scout as the trading/news intelligence agent and building the `ScoutSourceEngine` as its proprietary internal capability, Aegis will eliminate top-1 search errors, extract structured financial facts with pristine provenance, and operate with maximum efficiency and zero credential requirements.

Proceeding to **Phase 2 & Phase 3**: Design documentation, data models, source policies, extraction specifications, and failure modeling.
