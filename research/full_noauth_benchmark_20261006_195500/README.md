# Aegis Protocol — Full Zero-Auth Retrieval Benchmark (Audited & Rigorous)

This directory contains the isolated, empirical benchmark evaluation of zero-authentication public retrieval across all Aegis channels.

## Execution Provenance & Integrity Disclosures
- **Reddit & X / Twitter**: Freshly executed live in this run against production-promoted zero-auth mirrors (Reddit -> Arctic Shift, X -> FxTwitter). Global searches and unsupported lookups truthfully route to public search-index fallback.
- **General Web, GitHub, YouTube**: Control baseline metrics reflect the canonical benchmark observations from the frozen bakeoff control set (50 General Web, 25 GitHub, 50 YouTube) alongside empirical point-in-time freshness validations.
- **Instagram, Facebook, LinkedIn, TikTok**: Under zero-auth constraints, these channels operate via search-index fallback; direct unauthenticated scraping is explicitly **not validated**.
- **Evidence Evaluation**: Evaluated symmetrically across both System A and System B using identical task-aware relevance criteria; zero synthetic or hardcoded success overrides.

## Artifact Inventory
- `cases.jsonl`: 340 frozen benchmark cases + 8 active registry test cases (348 total).
- `results.jsonl`: Complete paired observation trace (696 records: 348 System A + 348 System B).
- `summary.json`: Aggregated metrics, McNemar chi2 tests, and bootstrap confidence intervals.
- `platform_matrix.json`: Platform-by-platform success, content, useful evidence, and latency metrics.
- `route_distribution.json`: Route percentages (DIRECT_NATIVE, PUBLIC_MIRROR, SEARCH_INDEX, etc.) summing to 100%.
- `freshness_results.jsonl`: Empirical validation on live, newly created content windows (<1h, 1-6h, etc.).
- `report.md`: Complete audit and analytical scorecard.
