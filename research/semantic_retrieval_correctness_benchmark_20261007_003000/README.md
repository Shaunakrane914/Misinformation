# Aegis Protocol — High-Fidelity Semantic Retrieval Correctness Benchmark

## Overview
This benchmark evaluates **Source Correctness, Content Relevance, Claim Support, and False Positive Control** across 100 Reddit SEARCH and 100 X SEARCH cases under zero-authentication constraints.

## Artifacts
- `cases.jsonl`: 200 realistic test cases including explicit scope/trap scenarios.
- `candidates.jsonl`: Full candidate record ledger (5-10 candidates per query) with all 17 fields.
- `results.jsonl`: Final evaluation record for each of the 200 cases.
- `adjudication.jsonl`: Independent double-adjudication comparison (primary vs blind secondary adjudicator).
- `manual_audit_sample.jsonl`: 100-case random stratified manual audit sample (50 Reddit + 50 X).
- `depth_ablation.json`: Candidate depth ablation (Top 1 vs Top 3 vs Top 5 vs Top 10).
- `engine_ablation.json`: Discovery engine ablation (Bing vs Bing+Yahoo vs Bing+Yahoo+Expansion).
- `summary.json`: Machine-readable summary statistics.
- `report.md`: Detailed audit and benchmark report.
