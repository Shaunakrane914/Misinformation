# Aegis Protocol — Corrected Retrieval Quality Benchmark Summary

## Metric Formulation & Candidate Pool Documentation
- **Total Scenarios:** `104` (Development: `84`, Holdout: `20`)
- **Frozen Candidate Pool Size per Scenario:** `N = 4` (Total Candidates: `416`)
- **Relevance Labels in Corpus:** 85 broad relevant (grades 2–3) across 58 scenarios; 53 strict relevant (grade 3); 184 grade 1; 147 grade 0.
- **Evaluated Cutoffs:** Natural pool cutoffs at **k = 1, 3, 4** (plus fixed k=5 reference).
- **Recall Calculation:** Standard Cranfield macro-average evaluated strictly over the `58` scenarios containing at least one relevant document ($R_{query} \ge 1$).

## Neural CrossEncoder Execution Telemetry
- **Configured Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Execution Device:** `cpu`
- **Availability Status:** `AVAILABLE`
- **Pairs Scored:** `832`
- **Inference Duration:** `12.706s`
- **Inference Failures:** `0`
- **Fallback Invocations:** `0`

## 1. System Comparison Matrix (Overall, N=104)

| Metric | System A: Deterministic Baseline | System B: Hybrid Lexical+Neural | System C: Neural Second-Stage | Delta (C vs A) |
| :--- | :---: | :---: | :---: | :---: |
| **Broad Precision@1 (Grades 2-3)** | 52.9% | 52.9% | 52.9% | **0.0%** |
| **Broad Precision@3 (Grades 2-3)** | 27.2% | 27.2% | 27.2% | **0.0%** |
| **Broad Precision@4 (Grades 2-3)** | 20.4% | 20.4% | 20.4% | **0.0%** |
| **Strict Precision@1 (Grade 3)** | 50.0% | 50.0% | 48.1% | **-1.9%** |
| **Strict Precision@3 (Grade 3)** | 17.0% | 17.0% | 17.0% | **0.0%** |
| **Strict Precision@4 (Grade 3)** | 12.7% | 12.7% | 12.7% | **0.0%** |
| **Cranfield Recall@1 (R >= 1)** | 71.5% | 71.5% | 71.5% | **0.0%** |
| **Cranfield Recall@3 (R >= 1)** | 100.0% | 100.0% | 100.0% | **0.0%** |
| **Cranfield Recall@4 (Full Pool)** | 100.0% | 100.0% | 100.0% | **0.0%** |
| **MRR (Broad)** | 54.3% | 54.3% | 54.3% | **0.000** |
| **Strict MRR (Grade 3)** | 50.5% | 50.5% | 49.5% | **-0.010** |
| **nDCG@3** | 95.8% | 94.7% | 94.4% | **-0.013** |
| **nDCG@4 (Full Pool)** | 95.8% | 94.7% | 94.4% | **-0.013** |
| **Entity Accuracy @ Rank 1** | 94.2% | 89.4% | 86.5% | **-7.7%** |
| **Top-k Entity Density (Pool)** | 43.5% | 43.5% | 43.5% | **0.0%** |
| **Intent Accuracy @ Rank 1** | 50.0% | 50.0% | 48.1% | **-1.9%** |
| **Top-k Intent Density (Pool)** | 13.9% | 13.9% | 13.9% | **0.0%** |
| **Top-1 Hard-Negative Avoidance** | 96.2% | 92.3% | 92.3% | **-3.8%** |
| **Candidate Hard-Negative Rejection Rate** | 84.4% | 84.4% | 84.4% | **0.0%** |

## 2. Development (N=84) vs. Holdout (N=20) Generalization

| Metric | Dev (Deterministic) | Dev (Reranker) | Holdout (Deterministic) | Holdout (Reranker) |
| :--- | :---: | :---: | :---: | :---: |
| **Broad P@1** | 56.0% | 57.1% | 40.0% | 35.0% |
| **Broad P@4** | 22.0% | 22.0% | 13.8% | 13.8% |
| **Strict P@1** | 52.4% | 52.4% | 40.0% | 30.0% |
| **Cranfield Recall@3** | 100.0% | 100.0% | 100.0% | 100.0% |
| **MRR** | 57.7% | 58.3% | 40.0% | 37.5% |
| **nDCG@4** | 95.9% | 95.0% | 95.1% | 91.8% |
| **Top-1 Hard-Neg Avoidance** | 96.4% | 92.9% | 95.0% | 90.0% |
| **Candidate Hard-Neg Rejection** | 84.6% | 84.6% | 83.3% | 83.3% |

## 3. Per-Agent Performance Breakdown (Neural Reranker)

| Agent | Scenarios | Broad P@1 | Broad P@4 | Strict P@1 | Cranfield Recall@3 | nDCG@4 | Top-1 HN Avoidance | Cand HN Rejection |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Brandshield** | 26 | 65.4% | 19.2% | 53.8% | 100.0% | 97.4% | 96.2% | 94.9% |
| **Trending** | 26 | 46.2% | 23.1% | 38.5% | 100.0% | 88.0% | 84.6% | 59.1% |
| **Scout** | 26 | 50.0% | 14.4% | 50.0% | 100.0% | 95.1% | 88.5% | 89.7% |
| **Personal_Watch** | 26 | 50.0% | 25.0% | 50.0% | 100.0% | 97.2% | 100.0% | 100.0% |
