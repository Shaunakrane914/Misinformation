# SCOUT ARCHITECTURE AUDIT
## Aegis Protocol — Agent 1: Scout Scraper Engine Architecture Baseline

**Document Version:** 1.0  
**Date:** October 7, 2026  
**Status:** Approved Architectural Audit (Phase 1 Baseline)  
**Author:** Agent 1 (Scout Core Engine)

---

## 1. Executive Summary

This document provides the mandatory **Phase 1 Architectural Audit** of the Aegis Protocol repository prior to implementing **Agent 1 — Scout Scraper Engine**. 

Recent empirical benchmarks on 200 unanchored test queries (100 Reddit + 100 X/Twitter) demonstrated conclusively that **first-result search selection is fundamentally flawed**:
* On Reddit, selecting Top-1 yielded only **67% source correctness** and **46% claim support** with a **26% false-positive rate**, whereas deep candidate retrieval (Top 5–10) with semantic ranking achieved **76% source correctness**, **72% claim support**, and reduced false positives to **18%**.
* Over **34% of winning Reddit evidence sources were ranked #2 or lower** by search engines.
* On X/Twitter, direct status searching across raw engines failed on 51% of queries due to crawler login walls, while discovered profile and mirror paths provided high-fidelity evidence when properly classified and extracted.

**Scout's mandate** is to replace ad-hoc, single-shot search calls with a **dedicated, production-grade source discovery, acquisition, extraction, validation, and provenance engine** operating as a shared infrastructure layer for downstream reasoning agents (`ResearchAgent`, `InvestigatorAgent`).

---

## 2. Current Retrieval Flow Analysis

The current Aegis retrieval pipeline flows through several loosely coupled modules:

```text
ClaimIngestionAgent
       │
       ▼ (normalized text, claim hash)
ResearchAgent.gather_evidence_structured()
       │
       ▼ (ResearchRequest)
ResearchEngine.investigate()
       │
       ├─► Stage 1: RetrievalPlanner.build_multi_channel_queries()
       │
       ├─► Stage 2: AgentReachService.retrieve_many()
       │         │
       │         └─► CapabilityRegistry.get_channel()
       │                   │
       │                   └─► Channel.search() [channels_impl.py]
       │                             │
       │                             └─► NativeRouter.execute_channel_query()
       │                                       │
       │                                       ├─► Platform Mirror (ArcticShift / FxTwitter)
       │                                       ├─► Native CLI Tools (yt-dlp, gh)
       │                                       ├─► Jina Reader (r.jina.ai)
       │                                       └─► Web Search Index (Bing / Yahoo)
       │
       ├─► Stage 3: EvidenceItem.from_evidence_fragment()
       ├─► Stage 3b: Hard Relevance Gate (relevance_gate.py)
       ├─► Stage 4: Syndication Clustering (source_independence.py)
       ├─► Stage 5: Candidate Ranking (candidate_ranker.py)
       ├─► Stage 8: Diversity Deep Reading (deep_reader.py)
       └─► Stage 9: Passage Extraction (passage_extractor.py)
                   │
                   ▼ (ResearchResult with Findings)
InvestigatorAgent.determine_verdict()
       │
       ▼ (Truth Verdict + Forensic Evidence Chain)
```

### Flow Walkthrough & Observations
1. **Ingestion**: `ClaimIngestionAgent` normalizes claim text (Unicode NFC, whitespace collapsing, punctuation trimming) and stores claim hashes in PostgreSQL/Supabase.
2. **Query Planning**: `RetrievalPlanner` generates keyword queries and selects channels based on domain (`financial`, `brand`, `personal`, `fact_check`).
3. **Dispatch**: `AgentReachService` runs bounded concurrent queries across registered `Channel` objects.
4. **Execution**: Every channel delegates directly to `NativeRouter.execute_channel_query()`, which acts as a monolithic dispatch bottleneck handling mirrors, CLI tools, scraping, and fallbacks.
5. **Post-Processing**: Evidence items pass through the 9-stage `ResearchEngine` pipeline where relevance gating, clustering, and ranking are performed *after* acquisition has completed.

---

## 3. Current Weaknesses & Bottlenecks

### 3.1 "Search Result = Correct Source" Fallacy
Before our recent benchmark improvements, retrieval assumed that whichever URL Bing or Yahoo returned at rank 1 was the intended evidence source. The empirical benchmark proved:
* Rank 1 on Reddit contains irrelevant noise or generic subreddit feeds in **33% of queries**.
* Search engine rank is optimized for SEO clicks, not forensic truth verification or semantic claim support.

### 3.2 Monolithic & Entangled Router (`NativeRouter`)
`backend/services/agent_reach/native/router.py` exceeds 1,360 lines and currently combines:
* Transport session management
* Search engine scraping (Bing and Yahoo HTML parsing)
* URL redirect resolution
* Mirror API communication (Arctic Shift, FxTwitter)
* Tool CLI execution
* Channel telemetry recording
* Deep reading logic

This violates the Single Responsibility Principle and makes adding new sources or extraction rules error-prone.

### 3.3 Ad-Hoc & Unstructured Extraction
`NativeRouter._read_url_deep()` relies almost exclusively on Jina Reader (`r.jina.ai/<url>`) or basic string concatenation. It lacks:
* Structured metadata extraction (JSON-LD, OpenGraph, Twitter Cards, Schema.org)
* Semantic article element parsing (headings, lead paragraphs, bylines, publication timestamps)
* Separation of article text from boilerplates, advertisements, and navigation menus when Jina is unreachable.

### 3.4 Rate Limiting & Fragile Search Concurrency
During benchmark runs, firing multiple concurrent Bing/Yahoo queries without pacing resulted in HTTP 500/429 errors and temporary IP challenges. A robust acquisition engine requires:
* Centralized request pacing and jittered exponential backoff
* Connection pooling and session reuse
* Engine health tracking with circuit breakers.

### 3.5 Name Collision in Existing Scout Agent
An existing file `backend/agents/scout_agent.py` implements a legacy financial anomaly detector using `yfapi.net` (Yahoo Finance API). It is completely unrelated to internet evidence scraping. This historical collision must be cleaned up: Scout must become the **dedicated evidence acquisition engine**, while financial market telemetry belongs in domain instruments.

---

## 4. Inventory of Reusable Components

Aegis already possesses high-quality components that Scout will reuse and extend:

| Component | File Location | Reusable Capabilities |
| :--- | :--- | :--- |
| **`EvidenceFragment`** | `backend/services/agent_reach/channels.py` | Canonical dataclass with complete provenance fields (`retrieval_mode`, `native_backend_id`, `fallback_reason`, `retrieval_lineage`, `raw_metadata`). |
| **`RetrievalMode`** | `backend/services/agent_reach/channels.py` | Granular classification enum (`ZERO_AUTH_PUBLIC_MIRROR`, `WEB_SEARCH_INDEX`, `NATIVE_TOOL_CLI`, `WEB_READER`, etc.). |
| **`url_validator`** | `backend/services/url_validator.py` | Production SSRF defense with IP range blocking (RFC 1918, loopbacks, cloud metadata `169.254.169.254`) and allowlisted mirror hosts. |
| **`NativeExecutor`** | `backend/services/agent_reach/native/executor.py` | Safe allowlisted command execution (`yt-dlp`, `gh`, `feedparser`) strictly using parameter arrays (never `shell=True`). |
| **`NativeNormalizer`** | `backend/services/agent_reach/native/normalizer.py` | Robust parsing and normalization of GitHub, YouTube, RSS, and social outputs into canonical `EvidenceFragment` objects. |
| **Anti-Token-Cheat Logic** | `backend/services/agent_reach/native/source_discovery.py` | `check_entity_semantic_match()` enforcing co-occurrence rules (preventing "Satya" incense from matching "Satya Nadella"). |
| **Deterministic Rubric** | `backend/services/agent_reach/native/source_discovery.py` | `evaluate_content_relevance()` scoring source correctness (0/1/2), content relevance (0/1/2), and claim support (0/1/2). |
| **Blind Adjudicator** | `backend/services/agent_reach/native/source_discovery.py` | `BlindSecondaryAdjudicator` for independent second-pass verification. |
| **Relevance Gate** | `backend/services/research/relevance_gate.py` | Hard entity alias dictionary, domain classifications, and negative keyword rejection. |
| **Public Mirror APIs** | Arctic Shift REST & FxTwitter REST | Zero-auth, credential-free retrieval of full Reddit submissions/comments and X/Twitter statuses/profiles. |

---

## 5. Duplicate & Deprecated Code Identification

The audit identified several instances of duplicate or overlapping code across the repository:

1. **Bing Search Scraping Duplication**:
   * `backend/services/agent_reach_scraper.py` (lines 64–92): Bing News RSS parsing.
   * `backend/services/agent_reach/native/router.py` (lines 1150–1195): Bing HTML search scraping with redirect unwrapping.
   * `research/semantic_retrieval_correctness_benchmark_20261007_003000/run_benchmark.py`: Local copy of Bing search query wrapper.
   * *Remediation*: Consolidate all search discovery into `scout/discovery/bing.py`.

2. **Reddit Extraction Duplication**:
   * `backend/services/agent_reach_scraper.py` (lines 94–140): Deprecated PullPush API caller.
   * `backend/services/agent_reach/native/router.py` (lines 350–450): Arctic Shift REST API caller.
   * *Remediation*: Decommission PullPush; standardize Arctic Shift in `scout/adapters/reddit.py`.

3. **URL Redirect Resolution Duplication**:
   * Implemented independently in `source_discovery.py` (`resolve_bing_redirect`), `router.py`, and `agent_reach_scraper.py`.
   * *Remediation*: Unify in `scout/transport/redirects.py`.

4. **Multiple `_call_gemini` Implementations**:
   * Independent Gemini callers with separate retry loops exist in `research_agent.py`, `investigator_agent.py`, and `coordinator_agent.py`.
   * *Remediation*: Route all Gemini calls through `backend/services/gemini_service.py`.

---

## 6. Existing Abstractions & Contracts

The Scout engine must interface smoothly with existing Aegis data contracts:

```python
# 1. EvidenceFragment (backend/services/agent_reach/channels.py)
@dataclass
class EvidenceFragment:
    platform: str
    title: str = ""
    content: str = ""
    url: str = ""
    author: str = ""
    published: str = ""
    snippet: str = ""
    score: float = 0.0
    retrieval_method: str = "agent_reach"
    retrieved_at: str = field(...)
    channel_name: str = ""
    content_depth: str = "SNIPPET"  # HEADLINE_ONLY | SNIPPET | PARTIAL_CONTENT | FULL_ARTICLE
    query_id: str = ""
    query_class: str = ""
    query_text: str = ""
    retrieval_mode: str = RetrievalMode.UNKNOWN.value
    native_backend_id: Optional[str] = None
    fallback_reason: Optional[str] = None
    is_authenticated: bool = False
    requested_channel: str = ""
    actual_retrieval_channel: str = ""
    retrieval_lineage: List[Dict[str, Any]] = field(...)
    raw_metadata: Dict[str, Any] = field(...)
```

Downstream consumers (`ResearchEngine`, `ResearchAgent`, `InvestigatorAgent`) expect and depend upon these exact attributes. Scout must emit **strict `EvidenceFragment` objects**, enriched with extraction confidence, semantic relevance scores, and candidate rank metadata stored in `raw_metadata`.

---

## 7. Current Source-Specific Adapters & Status

| Channel | Current Adapter | Auth Model | Current Status & Limitations |
| :--- | :--- | :--- | :--- |
| **Reddit** | Arctic Shift REST API (`router.py`) | Zero-Auth (Public Mirror) | High fidelity for posts and comments. Previously lacked subreddit feed candidate parsing. |
| **X / Twitter** | FxTwitter API (`router.py`) | Zero-Auth (Public Mirror) | High fidelity for numerical status IDs. Profile metadata was under-utilized. Search indexing is limited by X crawler blocks. |
| **YouTube** | `yt-dlp` CLI (`executor.py`) | Zero-Auth (Local Tool) | Extracts rich video metadata, chapter titles, and full transcripts when available. |
| **GitHub** | `gh` CLI + REST fallback (`executor.py`) | Optional Auth (CLI / REST) | High quality repository and release search. Rate limits on REST if unauthenticated. |
| **RSS / News** | `feedparser` (`executor.py`) | Zero-Auth (Public RSS) | Google News and Bing News RSS feeds. Provides fast headlines and snippets, but requires secondary reading for full body. |
| **General Web** | Bing HTML Scraping (`router.py`) | Zero-Auth (Search Index) | Extracts search snippets and destination URLs. Prone to redirect lag and occasional bot verification. |
| **Web Reader** | Jina Reader `r.jina.ai` (`executor.py`) | Zero-Auth (Public Reader) | Excellent clean Markdown conversion. Needs direct HTTP fallback with structured extraction when Jina times out. |

---

## 8. Provenance & Telemetry Baseline

Aegis enforces strict provenance rules: **never disguise fallbacks as native sources**.

### Current Provenance Invariants
1. `requested_channel`: The platform the caller asked for (e.g., `reddit`).
2. `actual_retrieval_channel`: Where the data was actually obtained (e.g., `reddit` or `web`).
3. `retrieval_mode`: The exact mechanical mode (e.g., `zero_auth_public_mirror` vs `web_search_index` vs `unauthenticated_syndicated_fallback`).
4. `native_backend_id`: Machine identifier of the backend (e.g., `arctic_shift`, `fxtwitter`, `bing-search-index`).
5. `fallback_reason`: Must be explicitly populated when degrading (e.g., `ARCTIC_SHIFT_UNAVAILABLE`, `RATE_LIMITED`).
6. `is_authenticated`: Must remain `False` across all zero-auth operations.

Scout will extend this provenance contract by recording:
* `candidate_discovery_rank`: The position of the candidate in raw search results (1, 2, 5, etc.).
* `semantic_selection_score`: The composite relevance score that justified selecting this candidate.
* `adjudication_status`: Whether the candidate was accepted or rejected by the verification rubric.

---

## 9. Failure Handling Baseline

The current system has rudimentary failure handling:
* Exceptions are caught inside per-channel methods and logged as debug statements.
* Channels return empty lists `[]` on failure without structured diagnostic codes.
* Telemetry records `"status": "FAILED"`, but downstream agents cannot distinguish between:
  * `DISCOVERY_EMPTY` (search engine found nothing)
  * `INVALID_URL` (URL structure did not match platform specifications)
  * `MIRROR_UNAVAILABLE` (public mirror was temporarily down)
  * `SEMANTICALLY_IRRELEVANT` (sources were found, but none related to the claim)
  * `RATE_LIMITED` (search engine or mirror triggered throttling)

Scout will introduce a formal **Structured Failure Model** (`ScoutFailureCode`) so that calling agents can make intelligent adaptive decisions (e.g., escalating to secondary query terms vs waiting on rate limits).

---

## 10. Recommended Integration Architecture for Scout

Scout should **not** be another high-level reasoning agent. It is a **foundational infrastructure service**:

```text
                     ┌────────────────────────────────────────┐
                     │              SCOUT ENGINE              │
                     │  backend/services/agent_reach/scout/   │
                     ├────────────────────────────────────────┤
                     │ 1. Request Contract (ScoutRequest)     │
                     │ 2. Multi-Engine Discovery              │
                     │ 3. Deep Candidate Pool Generation      │
                     │ 4. Deterministic Hard Gates            │
                     │ 5. Native / Mirror Acquisition         │
                     │ 6. Structured Multi-Strategy Extractor │
                     │ 7. Semantic Validation & Ranking       │
                     │ 8. Provenance & Telemetry Assembly     │
                     └───────────────────┬────────────────────┘
                                         │ EvidenceFragment[]
                     ┌───────────────────┴────────────────────┐
                     ▼                                        ▼
             ResearchEngine                           ResearchAgent /
         (Stage 2 Broad Discovery &             InvestigatorAgent Tools
          Stage 8 Deep Reading)
```

### Proposed Directory Layout
```text
backend/services/agent_reach/scout/
├── __init__.py               # Public API exports (ScoutEngine, ScoutRequest, ScoutResult)
├── engine.py                 # Core ScoutEngine coordinator
├── models.py                 # ScoutRequest, ScoutResult, CandidateSource, ValidationResult
├── transport/
│   ├── __init__.py
│   ├── session.py            # Bounded connection pool, header rotation, timeout budgets
│   ├── rate_limiter.py       # Token bucket & polite per-domain pacing
│   └── redirects.py          # Unified redirect & canonical URL resolver
├── discovery/
│   ├── __init__.py
│   ├── base.py               # Abstract DiscoveryStrategy
│   ├── bing.py               # Bing search discovery
│   ├── yahoo.py              # Yahoo search discovery
│   └── query_expansion.py    # Deterministic platform query generator
├── adapters/
│   ├── __init__.py
│   ├── base.py               # Abstract SourceAdapter
│   ├── reddit.py             # Arctic Shift submission, comment & subreddit adapter
│   ├── twitter.py            # FxTwitter status & profile adapter
│   ├── youtube.py            # yt-dlp video & transcript adapter
│   ├── github.py             # gh CLI & REST adapter
│   ├── rss.py                # feedparser news & RSS adapter
│   ├── jina.py               # Jina Reader web reader adapter
│   └── generic_web.py        # Direct HTTP web adapter
├── extraction/
│   ├── __init__.py
│   ├── metadata.py           # JSON-LD, OpenGraph, Twitter Cards, Schema.org
│   ├── content.py            # Clean text, headings, lead paragraphs, markdown
│   ├── author.py             # Byline & handle extraction
│   └── timestamp.py          # ISO 8601 publication & update date parser
├── validation/
│   ├── __init__.py
│   ├── hard_gates.py         # Scope, URL structure, domain blacklist, anti-token-cheat
│   └── semantic_rubric.py    # Source correctness, content relevance, claim support
├── ranking/
│   ├── __init__.py
│   └── candidate_ranker.py   # Multi-candidate semantic scorer (replaces Top-1 blind pick)
├── cache/
│   ├── __init__.py
│   └── bounded_cache.py      # In-memory LRU cache with TTL and immutable ID caching
└── telemetry/
    ├── __init__.py
    └── metrics.py            # Request-level and candidate-level latency and provenance metrics
```

### Backward Compatibility & Migration Strategy
1. **Zero Breaking Changes**: `NativeRouter` and `AgentReachService` will retain their existing public method signatures (`execute_channel_query`, `retrieve_many`).
2. **Internal Delegation**: `NativeRouter.execute_channel_query()` will delegate search discovery and candidate fetching directly to `ScoutEngine`.
3. **Evidence Integrity**: All output will continue to be emitted as standard `EvidenceFragment` objects, fully compatible with `ResearchEngine`, `relevance_gate`, and `InvestigatorAgent`.

---

## 11. Conclusion & Next Steps

This audit establishes the foundation for Phase 2. The existing codebase has mature building blocks (Arctic Shift, FxTwitter, yt-dlp, Jina, EvidenceFragment), but lacks a unified, multi-candidate acquisition and structured extraction engine. 

**Immediate Next Actions**:
1. Complete **Phase 2: Scout Architecture & Interfaces** (`SCOUT_ENGINE_DESIGN.md`, `SCOUT_DATA_CONTRACT.md`, `SCOUT_FAILURE_MODEL.md`).
2. Proceed to **Phase 3: Core Transport & Discovery Framework**.
