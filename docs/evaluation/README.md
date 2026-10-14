# Aegis Protocol — Evaluation & Benchmark Methodology

**Document Version**: 4.1.0  
**Framework**: Cranfield Paradigm Evaluation, Supervised ML Baselines & Retrieval Hardening

---

## 1. Scientific Standards & Ground-Truth Integrity

Aegis Protocol adheres to strict scientific verification principles:
1. **Separation of Real vs. Simulated**: Evaluated production components are separated from simulation models (e.g., Hawkes point processes, Zipf-Mandelbrot fits).
2. **Elimination of Mock Circularity**: The legacy 93.33% synthetic metric on 50 WELFake samples has been permanently retired because it relied on label-generated mock evidence strings.
3. **Strict Partitioning**: The WELFake classical ML baseline enforces zero duplicate titles between train ($N=13,752$), validation ($N=2,947$), and test ($N=2,948$) splits.

---

## 2. Frozen Cranfield Retrieval Benchmark

Located in `tests/retrieval_benchmark/`:
- **104 Evaluation Scenarios** (`scenarios.jsonl`): Covering claims across political events, medical statements, corporate earnings, and viral rumors.
- **416 Candidate Documents** (`candidates.jsonl`): Exactly 4 candidates per scenario (1 primary source, 1 corroborated secondary source, 1 unrelated distractor, 1 hard-negative adversary).
- **Curated Relevance Annotations** (`labels.jsonl`): Graded relevance scores (0 to 3) assigned by domain annotators.

### Core Retrieval Metrics
| Metric | Baseline (Raw Search) | Production (Reranked + TemporalGuard) | Target |
| :--- | :--- | :--- | :--- |
| **MRR (Mean Reciprocal Rank)** | 0.4856 | **0.8423** | $\ge 0.8000$ |
| **NDCG@5** | 0.5210 | **0.8654** | $\ge 0.8000$ |
| **Precision@1 (Top-1 Correct)** | 51.92% | **84.62%** | $\ge 80.00\%$ |
| **Entity Precision** | 71.15% | **94.23%** | $\ge 90.00\%$ |
| **Hard-Negative Avoidance** | 82.69% | **96.15%** | $\ge 95.00\%$ |

---

## 3. Supervised Classical ML Baseline

Trained on the WELFake dataset ($N=19,647$ total items, with 800 duplicate titles purged pre-split):
- **Model**: Deduplicated TF-IDF (10,000 unigram + bigram features) + L2 Regularized Logistic Regression.
- **Held-Out Test Accuracy**: **88.50%** (95% Wilson Score CI: `[87.30%, 89.60%]`).
- **Macro-F1**: **0.8850** (95% Bootstrap CI: `[0.8731, 0.8958]`).
- **Calibration**: Expected Calibration Error (ECE) = **0.0887**, Brier Score = **0.0945**.
- **Inference Latency**: 0.041 seconds for 2,948 samples (~72,000 samples/sec on CPU).

---

## 4. Learned Reranker vs. Neural CrossEncoder Findings

- **Active Model (Learned Linear Reranker)**: 7-feature linear model trained via pairwise cross-entropy with L-BFGS.
  - MRR: 0.20 → 1.00 (+0.80) on test queries.
  - Latency: 0.26 ms p50.
  - Model size: 136 bytes.
- **Neural CrossEncoder Evaluation (ADR-0003)**:
  - Scored 832 query-candidate pairs using `cross-encoder/ms-marco-MiniLM-L-6-v2`.
  - While zero inference exceptions occurred, entity accuracy dropped from 94.23% to 86.54%, top-1 hard-negative avoidance dropped from 96.15% to 92.31%, and latency increased by ~100x.
  - **Decision**: Neural CrossEncoder disabled in production; fast learned linear reranker + BM25 lexical ranker retained.

---

## 5. Running Evaluations

```bash
# Run all offline ML benchmarks
python scripts/evaluate_dataset.py --mode all_offline --seed 42

# Run classical ML baseline only
python scripts/evaluate_dataset.py --mode classical_ml --seed 42

# Run learned reranker evaluation only
python scripts/evaluate_dataset.py --mode reranker --seed 42

# Run the controlled retrieval benchmark evaluation
pytest tests/test_retrieval_benchmark.py -v
```

For complete mathematical definitions and reliability diagrams, see [`docs/EVALUATION.md`](../EVALUATION.md).
