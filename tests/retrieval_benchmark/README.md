# Aegis Protocol — Frozen Golden Retrieval Benchmark Dataset

## Overview
This directory contains the frozen golden benchmark dataset for evaluating retrieval precision,
entity disambiguation, and intent relevance across the four Aegis Protocol agents:
- **BrandShield** (Brand abuse, counterfeiting, phishing, impersonation)
- **Trending** (High-velocity viral narratives, syndication deduplication, temporal gating)
- **Scout** (Financial intelligence, SEC filings, material corporate catalysts)
- **Personal Watch** (VIP / executive protection, quotes, statements, homograph disambiguation)

## Statistics
- **Total Scenarios:** 104
  - BrandShield: 26 (21 dev, 5 holdout)
  - Trending: 26 (21 dev, 5 holdout)
  - Scout: 26 (21 dev, 5 holdout)
  - Personal Watch: 26 (21 dev, 5 holdout)
- **Split:** ~80% Development (84 scenarios), ~20% Holdout (20 scenarios)
- **Total Evaluated Candidates:** 416
- **Total Gold Labels:** 416
- **Average Candidates Per Scenario:** 4.0

## Grading Scale
- **3**: Exact target entity + exact agent intent (Direct True Positive)
- **2**: Correct entity + useful secondary context (Secondary Relevant / Background)
- **1**: Related entity/topic but wrong or weak intent (Boundary / Distractor)
- **0**: Irrelevant / wrong entity / adversarial distractor (Hard Negative / Homograph)

## Files
- `scenarios.jsonl`: Benchmark scenario specifications, query strings, and expected classifications.
- `candidates.jsonl`: Frozen candidate corpus for deterministic offline evaluation.
- `labels.jsonl`: Expert golden labels and rationale for every candidate.
- `test_benchmark_schema.py`: Pytest suite verifying schema integrity, zero-empty checks, and invariants.
