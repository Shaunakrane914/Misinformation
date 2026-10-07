# Aegis Protocol — No-Auth Public Social Media Benchmark

This directory contains empirical benchmark data evaluating whether Aegis can retrieve public social media evidence without personal user credentials.

## Directory Structure
- `cases.jsonl`: 36 standardized test cases across Reddit, X, and Facebook.
- `raw/`: Raw JSON/HTML payloads captured over the wire for every tool execution.
- `results.jsonl`: Normalized per-case observations matching Aegis EvidenceFragment specifications.
- `summary.json`: Aggregated metrics, success rates, latency percentiles, and failure taxonomies.
- `report.md`: Detailed benchmark analysis and architecture integration recommendations.