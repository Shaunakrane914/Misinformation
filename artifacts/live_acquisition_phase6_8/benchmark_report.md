# AEGIS PROTOCOL — PHASE 6.8.1 EVIDENCE INTEGRITY BENCHMARK REPORT
## Entity-to-Social-Source Resolution & Evidence Integrity Audit

**Audit Timestamp:** `2026-10-10T13:30:08.722518+00:00`  
**Reddit RSS Sunset Governance Date:** `2026-11-13`  
**Total Test Probes Executed:** `38`  

---

## 1. Executive Summary & Objective Verification

Phase 6.8.1 closes all evidence integrity items from Phase 6.8 with strict fail-closed guarantees:
1. **Token-Boundary Relevance Scoring:** Eliminated substring false positives (e.g. `sons` inside `lessons`).
2. **Separation of Source Content vs Metadata:** Scores post titles and extracted post bodies separately from subreddit names and URLs.
3. **Fail-Closed Platform Fallbacks:** Returns zero social fragments and records `DEGRADED/NO_VALID_PLATFORM_RESULTS` when queries yield only off-platform sites.
4. **Honest Attribution Metrics:** Profiles are reported as profile metadata, NEVER conflated with discussion posts.
5. **Dynamic Live Wikidata Resolution:** Validates live Wikidata P2002 resolution for non-curated entities (`Anthropic`, `Infosys`) with explicit verification method provenance (`LIVE_WIKIDATA_P2002_REST` vs `CURATED_ENTERPRISE_MAP`).
6. **Runtime Feature Flag Telemetry:** Dynamic evaluation of `AEGIS_REDDIT_RSS_ENABLED` across resolver, adapter, and handlers.

---

## 2. Core Curated Entity Benchmark Matrix (5 Entities × 3 Conditions)

| Entity | Platform | Condition | Status | Discussion Posts | Profiles | Full Posts | Feed Summs | Comments | X Statuses | Index Snips | Off-Platform | Entity Matches | Body Chars | Meta Chars | Total Bytes | Latency |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tata Sons** | `reddit` | 1. Baseline | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.539s |
| **Tata Sons** | `reddit` | 2. New Res | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10.307s |
| **Tata Sons** | `reddit` | 3. Source Off | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8.691s |
| **Tata Sons** | `twitter` | 1. Baseline | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.126s |
| **Tata Sons** | `twitter` | 2. New Res | `SUCCESS` | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 103 | 105 | 1.339s |
| **Tata Sons** | `twitter` | 3. Source Off | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.101s |
| **Nvidia** | `reddit` | 1. Baseline | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.289s |
| **Nvidia** | `reddit` | 2. New Res | `SUCCESS` | 6 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 8015 | 1339 | 9392 | 1.993s |
| **Nvidia** | `reddit` | 3. Source Off | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8.917s |
| **Nvidia** | `twitter` | 1. Baseline | `SUCCESS` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 139 | 139 | 0.348s |
| **Nvidia** | `twitter` | 2. New Res | `SUCCESS` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 139 | 139 | 0.0s |
| **Nvidia** | `twitter` | 3. Source Off | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.741s |
| **OpenAI** | `reddit` | 1. Baseline | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8.976s |
| **OpenAI** | `reddit` | 2. New Res | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12.681s |
| **OpenAI** | `reddit` | 3. Source Off | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8.531s |
| **OpenAI** | `twitter` | 1. Baseline | `SUCCESS` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 129 | 133 | 0.365s |
| **OpenAI** | `twitter` | 2. New Res | `SUCCESS` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 129 | 133 | 0.0s |
| **OpenAI** | `twitter` | 3. Source Off | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.77s |
| **Tesla** | `reddit` | 1. Baseline | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8.769s |
| **Tesla** | `reddit` | 2. New Res | `SUCCESS` | 10 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 10 | 1063 | 2770 | 3837 | 1.175s |
| **Tesla** | `reddit` | 3. Source Off | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8.726s |
| **Tesla** | `twitter` | 1. Baseline | `SUCCESS` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 57 | 57 | 0.484s |
| **Tesla** | `twitter` | 2. New Res | `SUCCESS` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 57 | 57 | 0.0s |
| **Tesla** | `twitter` | 3. Source Off | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.448s |
| **Reliance Industries** | `reddit` | 1. Baseline | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.937s |
| **Reliance Industries** | `reddit` | 2. New Res | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10.32s |
| **Reliance Industries** | `reddit` | 3. Source Off | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.397s |
| **Reliance Industries** | `twitter` | 1. Baseline | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.466s |
| **Reliance Industries** | `twitter` | 2. New Res | `SUCCESS` | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 231 | 231 | 1.438s |
| **Reliance Industries** | `twitter` | 3. Source Off | `DEGRADED` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9.743s |

---

## 3. Dynamic Live Wikidata Entity Resolution (Non-Curated Probes)

| Entity Query | Channel | Status | Discovered Handle | Verification Method | Confidence | Discussion Posts | Profiles | Latency |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Anthropic** | `reddit` | `SUCCESS` | `N/A` | `N/A` | 0.00 | 3 | 0 | 4.743s |
| **Anthropic** | `twitter` | `SUCCESS` | `@AnthropicAI` | `LIVE_WIKIDATA_P2002_REST` | 0.95 | 0 | 1 | 0.397s |
| **Infosys** | `reddit` | `DEGRADED` | `N/A` | `N/A` | 0.00 | 0 | 0 | 12.978s |
| **Infosys** | `twitter` | `SUCCESS` | `@infosys` | `LIVE_WIKIDATA_P2002_REST` | 0.85 | 0 | 1 | 0.391s |

---

## 4. Explicit Profile & Subreddit URL Tests

| Target URL | Platform | Condition | Items | Direct Platform URLs | Discussion Posts | Profiles | Latency |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `https://x.com/OpenAI` | `twitter` | `1_baseline` | 1 | 1 | 0 | 1 | 0.0s |
| `https://x.com/OpenAI` | `twitter` | `2_new_resolution` | 1 | 1 | 0 | 1 | 0.0s |
| `https://reddit.com/r/technology` | `reddit` | `1_baseline` | 10 | 10 | 10 | 0 | 1.041s |
| `https://reddit.com/r/technology` | `reddit` | `2_new_resolution` | 10 | 10 | 10 | 0 | 0.0s |

---

## 5. Entity Disambiguation & Provenance Table

| Entity Query | Resolved Entity ID | Resolved Label | Candidate Handle / Subreddit | Relationship | Verification Method | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **Tata Sons** (X) | `Q331715` | Tata Group | `@TataCompanies` | `PARENT_COMPANY` | `CURATED_ENTERPRISE_MAP` | 0.92 |
| **Tata Sons** (Reddit) | N/A | Tata Sons | `r/IndianStockMarket, r/IndiaInvestments, r/india` | `COMMUNITY_HUB` | `TAXONOMY_MAP` | 0.90 |
| **Nvidia** (X) | `Q182477` | Nvidia | `@nvidia` | `OFFICIAL` | `CURATED_ENTERPRISE_MAP` | 0.98 |
| **Nvidia** (Reddit) | N/A | Nvidia | `r/nvidia, r/stocks, r/hardware` | `COMMUNITY_HUB` | `TAXONOMY_MAP` | 0.90 |
| **OpenAI** (X) | `Q21708200` | OpenAI | `@OpenAI` | `OFFICIAL` | `CURATED_ENTERPRISE_MAP` | 0.98 |
| **OpenAI** (Reddit) | N/A | OpenAI | `r/OpenAI, r/technology, r/artificial` | `COMMUNITY_HUB` | `TAXONOMY_MAP` | 0.90 |
| **Tesla** (X) | `Q478214` | Tesla, Inc. | `@Tesla` | `OFFICIAL` | `CURATED_ENTERPRISE_MAP` | 0.98 |
| **Tesla** (Reddit) | N/A | Tesla | `r/teslamotors, r/stocks, r/electricvehicles` | `COMMUNITY_HUB` | `TAXONOMY_MAP` | 0.90 |
| **Reliance Industries** (X) | `Q908931` | Reliance Industries Limited | `@RIL_Updates` | `OFFICIAL` | `CURATED_ENTERPRISE_MAP` | 0.95 |
| **Reliance Industries** (Reddit) | N/A | Reliance Industries | `r/IndianStockMarket, r/IndiaInvestments, r/india` | `COMMUNITY_HUB` | `TAXONOMY_MAP` | 0.90 |
| **Anthropic** (X) | `Q116758847` | Anthropic | `@AnthropicAI` | `OFFICIAL` | `LIVE_WIKIDATA_P2002_REST` | 0.95 |
| **Anthropic** (Reddit) | N/A | Anthropic | `r/OpenAI, r/technology, r/artificial` | `COMMUNITY_HUB` | `TAXONOMY_MAP` | 0.90 |
| **Infosys** (X) | `Q26989` | Infosys limited | `@infosys` | `OFFICIAL` | `LIVE_WIKIDATA_P2002_REST` | 0.85 |
| **Infosys** (Reddit) | N/A | Infosys | `r/stocks, r/wallstreetbets, r/investing` | `COMMUNITY_HUB` | `TAXONOMY_MAP` | 0.90 |

---

## 6. Architectural Integrity & Quality Closeout

1. **Relevance Scoring Truth:** `filter_and_rank_posts()` strictly enforces word boundaries (`\b`). Substrings like `sons` in `lessons` are 100% rejected. Subreddit community membership is strictly isolated and never counts as proof of entity match.
2. **Fail-Closed Fallback Integrity:** When zero platform-domain URLs exist, the handler returns 0 items with `DEGRADED/NO_VALID_PLATFORM_RESULTS`. Corporate and third-party sites are never labeled as social evidence.
3. **Truthful Content Accounting:** Profiles return `discussion_posts_acquired = 0` and `profile_metadata_acquired = 1`. No synthetic expansion or false success counts.
4. **Dynamic Live Wikidata Grounding:** Non-curated entities resolve dynamically via Wikidata P2002 REST claims and carry `LIVE_WIKIDATA_P2002_REST` attribution.
5. **Runtime Feature Flag State:** `AEGIS_REDDIT_RSS_ENABLED` evaluated per-call across all layers, guaranteeing consistent deprecation telemetry.

---
*Report generated autonomously by Aegis Protocol Benchmark Suite (Phase 6.8.1 Closeout).* 