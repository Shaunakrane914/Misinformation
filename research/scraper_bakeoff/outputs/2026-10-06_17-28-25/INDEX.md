# Aegis Protocol — Cascade Validation Outputs (2026-10-06_17-28-25)

**Run Timestamp**: `2026-10-06_17-28-25`  
**Location**: `2026-10-06_17-28-25`  
All end-to-end cascade reports, paired comparisons, route distributions, and manifests for this validation are consolidated here.

## File Manifest

| Filename | Format | Description |
|---|---|---|
| [`cascade_scorecard.md`](cascade_scorecard.md) | Markdown | End-to-end policy comparisons (Policies A, B, C, D) and platform-level cascade results |
| [`final_route_distribution.md`](final_route_distribution.md) | Markdown | Distribution of resolved requests across Native, Specialist, Scrapling, Playwright, and Fallback |
| [`final_architecture_decision_v3.md`](final_architecture_decision_v3.md) | Markdown | Definitive architectural decisions, answers to all 12 core questions, and frozen production cascade |
| [`cascade_metric_trace.json`](cascade_metric_trace.json) | JSON | Machine-readable metrics, per-case traces, and case-to-route maps |
| [`reproducibility_manifest.json`](reproducibility_manifest.json) | JSON | Hardware, environment, timeout, and configuration manifest |
| [`paired_policy_results.json`](paired_policy_results.json) | JSON | Paired McNemar chi-squared and bootstrap latency tests (A vs B, A vs C, B vs C, B vs D) |
| [`benchmark_cases.jsonl`](benchmark_cases.jsonl) | JSONL | Immutable 340-case frozen benchmark dataset |
| [`all_observations_fullscale_live_1791285451.json`](all_observations_fullscale_live_1791285451.json) | JSON | 740 raw over-the-wire candidate observations |
| [`benchmark_integrity_audit.md`](benchmark_integrity_audit.md) | Markdown | Forensic integrity audit report |