# Aegis Protocol — End-to-End Cascade Validation Scorecard

**Execution Timestamp**: 2026-10-06T17:19:04.116933  
**Benchmark Scope**: 340 Frozen Cases x 4 Policies = 1,360 Cascade Executions  
**Hardware Platform**: 13th Gen Intel Core i5-13450HX (16 logical threads, 16GB RAM)  

## 1. End-to-End Policy Comparison

| Policy | Description | Cases | E2E Success | Useful Evidence | First-Party Direct | Direct + Meta | Fallback Dep. | Unresolved | P50 (ms) | P95 (ms) | Req/Case |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **POLICY_A** | Current Baseline (Jina Web / Social Fallback) | 340 | 100.0% | **73.2%** | **7.3%** | 7.3% | 85.6% | 0.0% | 504.4 | 2327.4 | 1.14 |
| **POLICY_B** | Proposed Fixed Pipeline (Native -> Spec -> Scrapling -> PW -> FB) | 340 | 100.0% | **67.3%** | **20.6%** | 34.1% | 65.9% | 0.0% | 908.34 | 6591.42 | 1.63 |
| **POLICY_C** | Search-First Baseline (Bing -> Reader -> Direct) | 340 | 100.0% | **58.8%** | **0.0%** | 0.0% | 100.0% | 0.0% | 456.39 | 1355.58 | 1.0 |
| **POLICY_D** | Optimized Empirical Cascade (Smart Task & Credential Router) | 340 | 100.0% | **67.3%** | **20.6%** | 34.1% | 65.9% | 0.0% | 592.76 | 6591.42 | 1.19 |

## 2. Platform-Level Cascade Results (Optimized Policy D)

| Platform | Cases | Useful Evidence | First-Party Direct | Metadata | Partial | Indexed (FB) | Fallback Dep. | Unresolved | P50 (ms) | P95 (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`general_web`** | 50 | 88.0% | 90.0% | 0 | 0 | 5 | 10.0% | 0.0% | 800.27 | 3296.4 |
| **`reddit`** | 50 | 100.0% | 0.0% | 0 | 0 | 50 | 100.0% | 0.0% | 490.97 | 802.17 |
| **`twitter`** | 50 | 100.0% | 0.0% | 0 | 0 | 50 | 100.0% | 0.0% | 1936.63 | 2437.77 |
| **`instagram`** | 50 | 100.0% | 0.0% | 0 | 0 | 50 | 100.0% | 0.0% | 381.18 | 539.55 |
| **`youtube`** | 50 | 20.0% | 0.0% | 46 | 0 | 4 | 8.0% | 0.0% | 5566.65 | 23876.23 |
| **`tiktok`** | 15 | 0.0% | 0.0% | 0 | 0 | 15 | 100.0% | 0.0% | 503.53 | 1381.94 |
| **`linkedin`** | 15 | 0.0% | 0.0% | 0 | 0 | 15 | 100.0% | 0.0% | 808.51 | 1537.38 |
| **`facebook`** | 15 | 0.0% | 0.0% | 0 | 0 | 15 | 100.0% | 0.0% | 632.91 | 1353.27 |
| **`github`** | 25 | 100.0% | 100.0% | 0 | 0 | 0 | 0.0% | 0.0% | 476.54 | 1443.46 |
| **`bilibili`** | 20 | 0.0% | 0.0% | 0 | 0 | 20 | 100.0% | 0.0% | 472.24 | 1512.63 |

## 3. Paired Statistical Tests Between Routing Policies

| Comparison | Metric Evaluated | McNemar chi2 | p-value | Significant (p<0.05)? | Empirical Verdict |
|---|---|---:|---|:---:|---|
| **A vs B** (Current vs Proposed Fixed Pipeline) | First-Party Direct Evidence | 43.0222 | p=0.01 | **YES** | Second policy wins on directness (+45 cases, p<0.01) |
| **A vs C** (Current vs Search-First Baseline) | First-Party Direct Evidence | 23.04 | p=0.01 | **YES** | First policy wins on directness (+25 cases, p<0.01) |
| **B vs C** (Proposed Pipeline vs Search-First) | First-Party Direct Evidence | 68.0143 | p=0.01 | **YES** | First policy wins on directness (+70 cases, p<0.01) |
| **B vs D** (Proposed Fixed vs Optimized Empirical) | First-Party Direct Evidence | 0.0 | p=1.0 | NO | Identical directness (34.1%), but Policy D cuts unnecessary requests and reduces latency |