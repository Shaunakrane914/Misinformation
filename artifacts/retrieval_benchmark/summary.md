# Aegis Protocol — Retrieval Quality Benchmark Summary

**Total Scenarios Evaluated:** `104`
**Total Evaluated Candidates:** `416`
**Top-k Rank Cutoff:** `5`

## 1. System Comparison Matrix (Overall)

| Metric | Deterministic Baseline | Hybrid Scoring | Neural Reranker | Reranker vs Baseline Delta |
| :--- | :---: | :---: | :---: | :---: |
| **Precision@1** | 52.9% | 52.9% | 52.9% | **0.0%** |
| **Precision@3** | 27.2% | 27.2% | 27.2% | **0.0%** |
| **Precision@5** | 16.4% | 16.4% | 16.4% | **0.0%** |
| **Recall@5** | 100.0% | 100.0% | 100.0% | **0.000** |
| **MRR** | 54.3% | 54.3% | 54.3% | **0.000** |
| **nDCG@5** | 95.8% | 94.7% | 94.4% | **-0.013** |
| **Entity Accuracy** | 43.5% | 43.5% | 43.5% | **0.0%** |
| **Intent Accuracy** | 13.9% | 13.9% | 13.9% | **0.0%** |
| **False-Positive Rate** | 35.3% | 35.3% | 35.3% | **0.0%** |
| **Ambiguous Rate** | 44.2% | 44.2% | 44.2% | **0.0%** |
| **Hard-Negative Rejection** | 96.2% | 92.3% | 92.3% | **-3.8%** |

## 2. Development vs. Holdout Generalization

| Metric | Dev (Deterministic) | Dev (Reranker) | Holdout (Deterministic) | Holdout (Reranker) |
| :--- | :---: | :---: | :---: | :---: |
| **P@5** | 17.6% | 17.6% | 11.0% | 11.0% |
| **MRR** | 57.7% | 58.3% | 40.0% | 37.5% |
| **nDCG@5** | 95.9% | 95.0% | 95.1% | 91.8% |
| **Entity Acc** | 44.4% | 44.4% | 40.0% | 40.0% |
| **FP Rate** | 34.8% | 34.8% | 37.5% | 37.5% |

## 3. Per-Agent Performance Breakdown (Neural Reranker)

| Agent | P@1 | P@5 | MRR | nDCG@5 | Entity Acc | Intent Acc | FP Rate | Hard-Neg Rejection |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Brandshield** | 65.4% | 15.4% | 67.3% | 97.4% | 47.1% | 17.3% | 37.5% | 96.2% |
| **Trending** | 46.2% | 18.5% | 46.2% | 88.0% | 50.0% | 11.5% | 42.3% | 84.6% |
| **Scout** | 50.0% | 11.5% | 53.8% | 95.1% | 39.4% | 14.4% | 27.9% | 88.5% |
| **Personal_Watch** | 50.0% | 20.0% | 50.0% | 97.2% | 37.5% | 12.5% | 33.7% | 100.0% |
