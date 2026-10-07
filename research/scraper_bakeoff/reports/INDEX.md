# Aegis Protocol — Research Outputs Index (2026-10-06_17-10-59)

**Run Timestamp**: `2026-10-06_17-10-59`  
**Bundle Directory**: `2026-10-06_17-10-59`  
**Total Audited Tasks**: 740  
**Total Evaluated Candidates**: 18 across 10 platforms  

All research documents, datasets, raw observations, and scorecards for this run are consolidated in this single directory.

## File Manifest

| Filename | Format | Description |
|---|---|---|
| [`final_scorecard_v2.md`](final_scorecard_v2.md) | Markdown | Authoritative master scorecard (Table 1 & Table 2) with Wilson CIs, P50/P95 latencies, failure breakdowns |
| [`architecture_decision_v2.md`](architecture_decision_v2.md) | Markdown | Concrete technology selections per platform and target retrieval cascade |
| [`final_recommendation_v2.md`](final_recommendation_v2.md) | Markdown | Platform decision classifications (PRIMARY, SECONDARY, FALLBACK) and architectural invariants |
| [`claim_reconciliation_v2.md`](claim_reconciliation_v2.md) | Markdown | Forensic reconciliation of all past headline claims against empirical measurements |
| [`benchmark_integrity_audit.md`](benchmark_integrity_audit.md) | Markdown | Forensic integrity audit report identifying previous denominator, taxonomy, and evaluator bugs |
| [`final_benchmark_summary_v2.json`](final_benchmark_summary_v2.json) | JSON | Canonical machine-readable benchmark summary containing all computed metrics |
| [`report_metric_trace.json`](report_metric_trace.json) | JSON | Complete traceability map tracing every published metric back to raw observation IDs |
| [`head_to_head_paired_results.json`](head_to_head_paired_results.json) | JSON | Paired head-to-head resource and CLI vs in-process benchmark profiler results |
| [`all_observations_fullscale_live_1791285451.json`](all_observations_fullscale_live_1791285451.json) | JSON | Canonical 740 live over-the-wire observation records |
| [`head_to_head_cases.jsonl`](head_to_head_cases.jsonl) | JSONL | 250 controlled head-to-head cases where multiple candidates evaluate identical targets |
| [`benchmark_cases.jsonl`](benchmark_cases.jsonl) | JSONL | Frozen standardized 340-case benchmark dataset |