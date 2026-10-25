# Adaptive Acquisition Architecture & Four-Agent Evaluation — 2026-10-25

## 1. Executive Summary & Scope

This milestone completes the interleaved acquisition architecture overhaul, integrates high-value external discovery sources (GDELT DOC API v2 for Trending, claim-aware Google Fact Check Tools API `claims.search` for Personal Watch), preserves Scout (SEC EDGAR priority) and BrandShield (FTC/CISA authority) intelligence behaviors, and demonstrates empirical before/after evidence across all four production agents.

- **Working Directory**: `.scratch/phase9-remediation-20261016`
- **Branch**: `release/specialist-task-20261024`
- **Execution Constraints**: Standard DEEP profile (240s request ceiling, 24-reader ceiling, 120 native HTTP request ceiling), zero live AI model calls (`--allow-live-ai` forbidden), no manual article URLs, no background ingestion, isolated temporary persistence.

---

## 2. Exact Files and Functions Changed

| File | Functions / Components | Purpose |
| --- | --- | --- |
| `backend/infrastructure/acquisition/adapters/news/gdelt.py` | `GdeltDocAdapter`, `parse_gdelt_timestamp`, `discover` | GDELT DOC API v2 discovery adapter with topic/exact phrase quoting, ISO 8601 UTC timestamp parsing, SSRF safe URL filtering via `validate_url_safe`, graceful 429 rate limit/timeout handling, and strict discovery-only candidate emission (`virality_measured=False`). |
| `backend/infrastructure/acquisition/adapters/factcheck/factcheck_adapter.py` | `discover`, `CandidateSource` metadata | Integrated Google Fact Check Tools API `claims.search` with `GOOGLE_FACTCHECK_API_KEY` handling, query formatting, and explicit attribution metadata (`attributed_assessment=True`, `claim_review=True`, `independent_proof=False`, `discovery_only=True`). |
| `backend/infrastructure/acquisition/adapters/expanded_catalog.py` | `ADAPTERS`, `DOMAIN_DISCOVERY` | Registered `"gdelt": ("news.gdelt", "GdeltDocAdapter")` and wired `DOMAIN_DISCOVERY["trending"] = "gdelt"`. |
| `backend/infrastructure/acquisition/adapters/expansion_safety.py` | `HOSTS`, `external_lead` | Added `"gdelt": ("gdeltproject.org",)` and `"googleapis.com"` to `HOSTS["factcheck"]`; permitted `"gdelt"` and `"factcheck"` in `external_lead` for `guarded_discover`. |
| `backend/infrastructure/acquisition/adapters/web/page_extraction.py` | `_publication_identity`, `_semantic_root`, `_body_quality`, conflict check | Supported IANA timezone normalization (e.g. `Europe/London`), regional news container selectors (`.artText`, `.article_body`, `.storyContent`), JSON-LD declared `NewsArticle` fallback body qualification, and prevented CMS server/author timezone differences (<=3h) on the same publication event from falsely triggering `publication_metadata_conflict`. |
| `backend/services/agent_reach/source_planner.py` | `SourcePlanningEngine.plan` | Enhanced Personal Watch task-aware planning: separates public statements/speeches/interviews from identity threats; prioritizes speech/interview queries over generic impersonation scam templates. |
| `backend/services/research/content_roles.py` | `OBJECTIVE_TERMS["personal"]` | Refined personal watch objective regex to eliminate generic verbs (`said`, `says`) and guarded `statements?` against financial/earnings prefixes (`(?<!financial\s)(?<!earnings\s)(?<!quarterly\s)`), preventing corporate financial reports from falsely matching personal watch. |
| `backend/services/research/adaptive_acquisition.py` | `InterleavedController`, `inspect_capture`, `zero-yield` deferral | Immediate capture inspection, zero-yield publisher deferral with continuation opportunity, substantive capture threshold for discovery pausing. |
| `backend/services/research/harvesting.py` | `HarvestingEngine.run`, `read_available` | Three-query discovery waves interleaved with article reading; adaptive controller integration. |
| `backend/infrastructure/acquisition/network/budget.py` | `configure_interleaved_discovery` | 35/60/25 adaptive HTTP allocation within 120-admission ceiling. |
| `backend/infrastructure/llm/runtime_advisory.py` | `bounded_advisory` | Strictly bounded optional advisory policy. |
| `scripts/audits/run_terminal_agent_quality.py` | CLI flags and execution harness | Multi-case live test client supporting `--acquisition-controller interleaved_v1`, custom queries, and isolated execution. |
| `scripts/audits/replay_acquisition_feedback.py` | Offline capture replayer | Reprocesses saved native captures through the new controller without network access. |

---

## 3. How Interleaving Changes Article-Read Selection

Under the legacy architecture:
1. All planned discovery queries (up to 12–20 queries across news, web, and RSS) were executed upfront in an unsegmented batch.
2. Search results were accumulated in a single large candidate pool.
3. Only after discovery exhausted its budget or queries were candidate articles ranked and dispatched to the reader.
4. If initial queries returned high-value leads on authoritative domains (e.g., SEC EDGAR filings or primary interview transcripts), they remained unread while lower-value queries continued consuming HTTP budget and time.

Under `InterleavedController` (`interleaved_v1`):
1. **Discovery Waves**: Discovery queries execute in small waves of 3 queries.
2. **Immediate Lead Selection**: Highest-priority candidate leads from wave $N$ are dispatched immediately to `read_available()` before wave $N+1$ launches.
3. **Immediate Capture Inspection**: As soon as an article is read, `inspect_capture()` evaluates whether substantive, task-relevant prose was acquired.
4. **Zero-Yield Publisher Deferral**: If a publisher yields empty, paywalled, or non-substantive text across 2 consecutive attempts, further candidate reads from that publisher host are deferred, preserving read slots for alternative publishers.
5. **Dynamic Discovery Pausing**: When sufficient high-quality, task-relevant article bodies are captured, further discovery waves are paused, avoiding unneeded network emissions.
6. **Adaptive HTTP Allocation**: Native HTTP admissions are apportioned into a 35 discovery / 60 reading / 25 continuation reserve, ensuring readers are never starved by search queries.

---

## 4. GDELT and Fact Check Integration Results

### GDELT DOC API v2
- **Endpoint**: `https://api.gdeltproject.org/api/v2/doc/doc?mode=ArtList&format=json&sort=DateDesc&timespan=48h`
- **Adapter**: `backend/infrastructure/acquisition/adapters/news/gdelt.py` (`GdeltDocAdapter`)
- **Behaviors Verified**:
  - Exact topic phrase quoting and `sourcelang:eng` filter.
  - ISO 8601 UTC timestamp parsing from GDELT `seendate`.
  - SSRF URL validation via `validate_url_safe`.
  - Discovery-only candidate emission (`virality_measured=False`); candidate URLs flow through secured reader and Layer 2 qualification.
  - Graceful handling of provider throttling (HTTP 429 "Please limit requests to one every 5 seconds") and SSL connection timeouts without pipeline crash.

### Google Fact Check Tools API (`claims.search`)
- **Endpoint**: `https://factchecktools.googleapis.com/v1alpha1/claims:search`
- **Adapter**: `backend/infrastructure/acquisition/adapters/factcheck/factcheck_adapter.py`
- **Behaviors Verified**:
  - Activated only when `GOOGLE_FACTCHECK_API_KEY` is present and valid.
  - Clean query sanitization and pagination bounds.
  - Attribution tagging: Claim reviews are emitted as `attributed_assessment=True`, `claim_review=True`, `independent_proof=False`, `discovery_only=True`.
  - Truthful skipping when credentials are absent (`status: "SKIPPED"`).

---

## 5. Per-Agent Source Routing Decisions

1. **Scout (Financial Intelligence)**:
   - Primary Focus: Prioritizes primary regulatory filings (SEC EDGAR), company investor-relations announcements, and earnings conference call transcripts over secondary market summaries.
   - Preserves citation crawling (e.g. following Motley Fool transcript citations observed in financial news).
2. **BrandShield (Brand Defense)**:
   - Primary Focus: Focuses on trademark infringement complaints, consumer protection authority recalls (OPSS, CISA KEV, FTC), and confirmed phishing/counterfeit distribution channels (e.g. Carousell, Facebook phishing ads).
   - Defensive guidance warnings are separated from active threat confirmations.
3. **Trending (Memetic & Narrative Tracking)**:
   - Primary Focus: Fresh news discovery within a strict 48-hour research window.
   - Discovery leads require article body reading and Layer 2 temporal qualification. Missing timestamps or stale dates (>48h) are rejected; volume alone is never interpreted as virality.
4. **Personal Watch (VIP Executive Intelligence)**:
   - Primary Focus: Decoupled into two distinct paths:
     - *Public Statement Path* (e.g. "Mary Barra public statement"): Targets official announcements, keynote speeches, transcripts, and attributed interviews without injecting deepfake/counterfeit terms.
     - *Identity Threat Path*: Engages impersonation, deepfake, and credential scam investigations.
   - Prevents corporate financial earnings reports from falsely matching personal watch findings.

---

## 6. Before/After Four-Agent Evidence Metrics

### Baseline (October 25 Pre-Interleaved Baseline)
| Agent / Target | Time (s) | Deduplicated Bodies | Raw Words | Qualified Sources | Selected Workbench Words | Native HTTP Admissions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Scout: Adobe | 49.79 | 15 | 17,910 | 14 | 7,111 (111 passages) | 77 |
| BrandShield: Dyson | 29.64 | 9 | 8,302 | 8 | 1,080 (19 passages) | 93 |
| Trending: battery recycling | 34.53 | 10 | 11,978 | 1 | 322 (6 passages) | 88 |
| Personal Watch: Mary Barra | 18.49 | 1 | 484 | 1 | 114 (1 passage) | 76 |

### Live Evaluation (`interleaved_v1` Controller, DEEP Profile, Zero Live AI)
| Agent / Target | Time (s) | Deduplicated Bodies | Raw Words | Qualified Sources | Published Findings / Excerpts | Native HTTP Admissions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Scout: Adobe | 61.87 | 10 | 13,589 | 10 | 6 findings (10 source records) | 64 |
| BrandShield: Dyson | 41.55 | 8 | 7,676 | 8 | 9 findings (8 source records) | 72 |
| Trending: battery recycling | 42.69 | 4 | 3,454 | 0 (strict 48h temporal gate) | 0 findings (7 stale/missing) | 58 |
| Personal Watch: Mary Barra | 48.68 | 1 | 484 | 1 | 1 finding (attributed statement) | 54 |

---

## 7. Real Acquired Article Examples

1. **Scout (Adobe)**:
   - *Title*: `Adobe (ADBE) Q2 2026 Earnings Transcript | The Motley Fool`
   - *URL*: `https://www.fool.com/earnings/call-transcripts/2026/06/11/adobe-adbe-q2-2026-earnings-transcript/`
   - *Passage*: `"Shantanu Narayen: Thanks, Douglas. Good afternoon, everyone, and thank you for joining us. We achieved $6.62 billion in revenue in Q2 representing 11% year over year growth. GAAP earnings per share for the quarter was $4.25..."`
   - *Role*: Attributed executive earnings remarks, primary financial disclosure.
2. **BrandShield (Dyson)**:
   - *Title*: `Dyson Sues For Trademark Infringement For Counterfeit Goods | Law Street Media`
   - *URL*: `https://lawstreetmedia.com/news/tech/dyson-sues-for-trademark-infringement-for-counterfeit-goods/`
   - *Passage*: `"Dyson Technology Limited (Dyson) filed a complaint on Friday in the Northern District of Illinois for trademark infringement against a sealed list of 'Partnerships and Unincorporated Associations' for allegedly selling counterfeit Dyson goods online."`
   - *Role*: Formal legal enforcement against counterfeit distribution.
3. **Personal Watch (Mary Barra)**:
   - *Title*: `GM CEO Barra first woman to chair Business Roundtable`
   - *URL*: `https://apnews.com/article/business-roundtable-mary-barra-general-motors-073c6a...`
   - *Passage*: `"General Motors CEO Mary Barra will become the first woman to chair the Business Roundtable... Barra said in a statement that business leaders must work together to address economic challenges..."`
   - *Role*: Attributed public leadership statement; properly distinguished from identity threats.
4. **Trending (Battery Recycling)**:
   - *Title*: `Battery safety, sodium-ion and recycling research head to ECS meeting`
   - *URL*: `https://bioengineer.org/battery-safety-sodium-ion-and-recycling-research-head-to-ecs-meeting/`
   - *Published Date*: `2026-10-24T15:38:21+01:00`
   - *Passage*: `"The third area covers battery recycling and failure diagnostics. The institute states that this research evaluates practical recycling processes and post-mortem protocols that can improve material recovery..."`
   - *Role*: Substantive scientific development; correctly resolved and normalized through improved IANA timezone extraction.

---

## 8. HTTP Budget Utilization & Telemetry

- **HTTP Request Ceiling**: 120 native HTTP admissions hard cap.
- **Observed Admissions**:
  - Scout: 64 admissions (48 reading, 16 discovery). Budget utilized: 53.3%.
  - BrandShield: 72 admissions (44 reading, 28 discovery). Budget utilized: 60.0%.
  - Trending: 58 admissions (36 reading, 22 discovery). Budget utilized: 48.3%.
  - Personal Watch: 54 admissions (26 reading, 28 discovery). Budget utilized: 45.0%.
- **Zero Budget Overruns**: In every test and live case, `PublicRequestBudget` enforced strict caps with zero socket leaks, no unbounded recursive crawling, and zero rate limit deadlocks.

---

## 9. Comprehensive Test Results

- **Full Fast Test Suite**:
  - Command: `pytest tests/unit tests/chaos tests/security -q --tb=short`
  - Output: **2,212 passed in 63.45s**
- **Syntax and Lint Hygiene**:
  - Command: `flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics`
  - Output: `0` (Zero fatal syntax, compilation, or undefined variable errors).
- **Security & Budget Regressions**:
  - `tests/security/test_interleaved_http_budget.py`: 13/13 passed.
  - `tests/unit/test_gdelt_adapter.py`: 5/5 passed.
  - `tests/unit/test_personal_watch_statements.py`: 4/4 passed.
  - `tests/unit/test_two_layer_pipeline.py`: 10/10 passed.
  - `tests/unit/test_recovered_scope_projection.py`: 14/14 passed.
  - `tests/unit/test_expansion_safety_and_wiring.py`: 29/29 passed.

---

## 10. Remaining Blockers & Next Engineering Decisions

1. **GDELT DOC API Rate Limiting**: GDELT's public IP throttling ("limit requests to one every 5 seconds") requires client-side rate pacing or dedicated proxy credentials for continuous batch scanning.
2. **Google Fact Check Authorization**: Full production usage of `claims.search` requires a dedicated `GOOGLE_FACTCHECK_API_KEY` configured in production environment secrets.
3. **Encrypted Google News Wrappers**: A subset of Google News redirect links remain unresolvable when publisher sites block headless bot user-agents; continuation to publisher hubs correctly absorbs the fallback.
