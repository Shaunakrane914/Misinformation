# Aegis Protocol — End-to-End Cascade Validation Scorecard

**Execution Timestamp**: 2026-10-06T17:28:31.561709  
**Benchmark Scope**: 340 Frozen Cases x 4 Policies = 1,360 Cascade Executions  
**Hardware Platform**: 13th Gen Intel Core i5-13450HX (16 logical threads, 16GB RAM)  

## 1. End-to-End Policy Comparison

| Policy | Description | Cases | E2E Success | Useful Evidence | First-Party Direct | Direct + Meta | Fallback Dep. | Unresolved | P50 (ms) | P95 (ms) | Req/Case |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **POLICY_A** | Current Baseline (Jina Web / Social Fallback) | 340 | 100.0% | **73.2%** | **7.3%** | 7.3% | 85.6% | 0.0% | 470.79 | 2165.01 | 1.14 |
| **POLICY_B** | Proposed Fixed Pipeline (Native -> Spec -> Scrapling -> PW -> FB) | 340 | 100.0% | **67.3%** | **20.6%** | 34.1% | 65.9% | 0.0% | 834.91 | 6591.42 | 1.63 |
| **POLICY_C** | Search-First Baseline (Bing -> Reader -> Direct) | 340 | 100.0% | **58.8%** | **0.0%** | 0.0% | 100.0% | 0.0% | 396.61 | 992.26 | 1.0 |
| **POLICY_D** | Optimized Empirical Cascade (Smart Task & Credential Router) | 340 | 100.0% | **67.3%** | **20.6%** | 34.1% | 65.9% | 0.0% | 506.65 | 6591.42 | 1.19 |

## 2. Platform-Level Cascade Results (Optimized Policy D)

| Platform | Cases | Useful Evidence | First-Party Direct | Metadata | Partial | Indexed (FB) | Fallback Dep. | Unresolved | P50 (ms) | P95 (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`general_web`** | 50 | 88.0% | 90.0% | 0 | 0 | 5 | 10.0% | 0.0% | 800.27 | 3240.47 |
| **`reddit`** | 50 | 100.0% | 0.0% | 0 | 0 | 50 | 100.0% | 0.0% | 490.97 | 802.17 |
| **`twitter`** | 50 | 100.0% | 0.0% | 0 | 0 | 50 | 100.0% | 0.0% | 1936.63 | 2437.77 |
| **`instagram`** | 50 | 100.0% | 0.0% | 0 | 0 | 50 | 100.0% | 0.0% | 381.18 | 539.55 |
| **`youtube`** | 50 | 20.0% | 0.0% | 46 | 0 | 4 | 8.0% | 0.0% | 5566.65 | 23876.23 |
| **`tiktok`** | 15 | 0.0% | 0.0% | 0 | 0 | 15 | 100.0% | 0.0% | 395.79 | 584.65 |
| **`linkedin`** | 15 | 0.0% | 0.0% | 0 | 0 | 15 | 100.0% | 0.0% | 352.77 | 448.85 |
| **`facebook`** | 15 | 0.0% | 0.0% | 0 | 0 | 15 | 100.0% | 0.0% | 349.83 | 548.14 |
| **`github`** | 25 | 100.0% | 100.0% | 0 | 0 | 0 | 0.0% | 0.0% | 476.54 | 1443.46 |
| **`bilibili`** | 20 | 0.0% | 0.0% | 0 | 0 | 20 | 100.0% | 0.0% | 360.41 | 453.78 |

> [!NOTE]
> **YouTube Task-Aware Evaluation**: YouTube cases comprise video metadata extraction (46/50 = 92.0% transport success, 100% field completeness on available videos) and content verification. 4/50 videos are deleted/geo-blocked and resolved via search syndication (8.0% fallback, 0.0% unresolved). Generic semantic claim-evidence score is 20.0% (10/50); 46/50 successful metadata retrievals does NOT automatically mean 46/50 useful claim evidence.


## 3. Paired Statistical Tests Between Routing Policies

| Comparison | Metric Evaluated | Continuity-Corrected McNemar chi2 | Exact p-value | Significant (p<0.05)? | Empirical Verdict |
|---|---|---:|---|:---:|---|
| **A vs B** (Current vs Proposed Fixed Pipeline) | First-Party Direct Evidence | 43.0222 | p=5.41e-11 | **YES** | Second policy wins on directness (+45 cases, p<0.0001) |
| **A vs C** (Current vs Search-First Baseline) | First-Party Direct Evidence | 23.04 | p=1.59e-06 | **YES** | First policy wins on directness (+25 cases, p<0.0001) |
| **B vs C** (Proposed Pipeline vs Search-First) | First-Party Direct Evidence | 68.0143 | p=1.62e-16 | **YES** | First policy wins on directness (+70 cases, p<0.0001) |
| **B vs D** (Proposed Fixed vs Optimized Empirical) | First-Party Direct Evidence | 0.0 | p=1.0 | NO | Policy D is an operational optimization of Policy B: it preserves direct/evidence outcomes while reducing unnecessary route attempts and improving median latency |