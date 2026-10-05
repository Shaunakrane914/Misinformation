# Aegis Protocol -- Scientific Evaluation Framework & Benchmark Results

**Repository**: `Shaunakrane914/Misinformation`
**Evaluation Framework Version**: `1.1.0`
**Execution Environment**: Python 3.13.5 | scikit-learn 1.7.1 | numpy 2.1.3 | scipy 1.16.3 | PyTest 8.4.2
**Status**: Foundational baselines measured. End-to-end Aegis pipeline benchmarks pending live credential run.

---

## Status Summary: What Is Real, What Is Pending

> [!IMPORTANT]
> This document explicitly separates three categories. Mixing them would be scientific dishonesty.

| Category | Label | Examples |
| :--- | :--- | :--- |
| **REAL MEASURED** | Values with CI and JSON artifact | WELFake 88.50%, ECE 0.0887, Reranker timing |
| **FRAMEWORK IMPLEMENTED** | Code exists, no artifact yet | `compute_grounded_answer_metrics()`, `mcnemar_significance_test()` |
| **NOT YET EXECUTED** | Harness returns `NOT RUN`/`BLOCKED` | Full Aegis pipeline, ablation table, RAG recall on live web |

Any metric without a JSON artifact in `docs/evaluation/results/` is **NOT YET EXECUTED**.

---

## 1. Critical Finding: Retirement of the Prior 93.33% Claim

In earlier project documentation, Aegis Protocol reported **93.33% accuracy** on a 50-sample WELFake slice.

Code audit revealed this benchmark ran under `gemini.mock_mode = True`, where dataset ground-truth labels
directly generated synthetic evidence strings, and `MockGeminiProvider` then returned the matching verdict
(~0.94 confidence) -- a closed synthetic loop where the label generated the evidence that was then evaluated.
**That number has been formally retired.**

### Corrective Actions

- Legacy evaluation loop permanently retired.
- `generate_text()` accepts `allow_mock_fallback: bool`. Scientific mode enforces `allow_mock_fallback=False`.
- All harness runs that cannot complete without live credentials return an honest `BLOCKED` status.

---

## 2. Evaluation Taxonomy

| Tier | Category | Allow Mocks? | Harness Method | Executable Without Keys? |
| :--- | :--- | :--- | :--- | :--- |
| **A** | Offline Regression (Unit Tests) | Yes | `pytest tests/unit/ tests/evaluation/` | Yes |
| **B** | Supervised Classical ML | No | `harness.run_classical_ml_benchmark()` | Yes |
| **C** | Supervised Reranker Sanity | No | `harness.run_reranker_benchmark()` | Yes |
| **D** | LLM-Only Benchmark | No | `harness.run_llm_only_benchmark()` | No -- requires GEMINI_API_KEY |
| **E** | Retrieval + LLM | No | `harness.run_retrieval_llm_benchmark()` | No -- requires GEMINI_API_KEY + Search |
| **F** | Full Aegis Multi-Agent | No | `harness.run_aegis_benchmark()` | No -- requires GEMINI_API_KEY + Search |
| **G** | Ablation Study | Dependent | `harness.run_ablation_study()` | No -- requires GEMINI_API_KEY + Search |

---

## 3. Dataset Accounting & Provenance

### WELFake (Supervised Classification Baseline)

> [!IMPORTANT]
> **Task Scope**: WELFake measures NLP stance/authenticity classification on news headlines.
> It is **not** a web claim-verification benchmark. 88.50% is the baseline classifier accuracy,
> not the Aegis pipeline accuracy.

- **Raw Rows**: 23,100
- **Clean Usable Rows (pre-dedup)**: 20,447 (2,653 null/invalid excluded)
- **Duplicate Titles Removed**: 800
- **Clean Deduplicated Rows**: 19,647 (Real: 9,835 [50.06%], Fake: 9,812 [49.94%])
- **Partitions** (seed=42, stratified): Train 13,752 / Val 2,947 / **Held-Out Test 2,948**
- **Partition Leakage Audit**: `duplicate_content_train_test` = **0**, `train_val` = **0**, `val_test` = **0**

### FEVER (Claim Verification + Sentence Retrieval)
- **Status**: `NOT YET EXECUTED` | Adapter: `backend/evaluation/datasets/fever.py`

### AVeriTeC (Real-World Web Evidence QA)
- **Status**: `NOT YET EXECUTED` -- corpus (~1.2 GB) not bundled | Adapter: `backend/evaluation/datasets/averitec.py`

### India Multilingual Track
- **Status**: Research Prototype -- 14 claims across 4 languages (en-IN, hi-IN, mr-IN, hi-en)
- **Ground Truth**: PIB Fact Check, RBI notifications, WHO clinical guidelines, CIDCO gazettes

---

## 4. REAL MEASURED: Supervised Classical ML Baseline

**Artifact**: `docs/evaluation/results/welfake_classical_ml_4ad02c2.json`

Model: TF-IDF (10k features, unigram+bigram, sublinear TF, English stop-words) + L2 Logistic Regression
(C=1.0, L-BFGS). Fit on 13,752 training samples. Evaluated on 2,948 held-out test samples.

```
================================================================================
                    CLASSICAL ML BASELINE PERFORMANCE METRICS
================================================================================
Metric                           Value      95% CI                  Method
--------------------------------------------------------------------------------
Accuracy                         0.8850     [0.8730, 0.8960]        Wilson Score
Macro-F1                         0.8850     [0.8731, 0.8958]        1,000-resample Bootstrap
Macro-Precision                  0.8851     --                      Empirical
Macro-Recall                     0.8850     --                      Empirical
Class 0 (Real News) F1           0.8851     (P: 0.8851, R: 0.8851, Support: 1,476)
Class 1 (Fake News) F1           0.8849     (P: 0.8851, R: 0.8849, Support: 1,472)
Expected Calibration Error (ECE) 0.0887     5-bin calibration curve
Brier Score                      0.0945     Mean squared probability error
Inference Throughput             42,027.6   samples/sec (0.070s for 2,948 samples)
Training Duration                0.91s      (13,752 training samples, TF-IDF + LR)
================================================================================
```

**Confusion Matrix**

```
                  Predicted Real (0)    Predicted Fake (1)
Actual Real (0)         1,306 (TN)             170 (FP)
Actual Fake (1)           169 (FN)           1,303 (TP)
```

- Type I Error: 170 real articles flagged as fake (5.77%)
- Type II Error: 169 fake articles missed (5.73%)

---

## 5. REAL MEASURED: Supervised Evidence Reranker (Controlled Sanity Experiment)

**Artifact**: `docs/evaluation/results/reranker_benchmark_4ad02c2.json`

> [!WARNING]
> **Scope Boundary**: This evaluates whether the supervised ranker separates labeled primary evidence
> from artificial distractor candidates in a **controlled pool**. It is a ranking sanity experiment,
> NOT a live web-retrieval result. Real-world MRR against genuine annotated candidate pools is
> pending the full Aegis pipeline run.

**Protocol**: `reranker.fit()` on 28 labeled pairwise examples (L-BFGS). Held-out 50% of claims.
Each query: 15 candidates (2 relevant targets at raw ranks 4 and 9; 13 artificial distractors).

**7-Feature Space**: TF-IDF Lexical Similarity, Title Jaccard, Passage Alignment, Accredited Domain
Prior, Entity Match Ratio, Primary Source Boolean, Information Density.

```
================================================================================
  EVIDENCE RERANKER: RAW vs SUPERVISED (HELD-OUT TEST QUERIES, CONTROLLED POOL)
================================================================================
Metric                      Raw Retrieval    Learned Reranker    Delta
--------------------------------------------------------------------------------
Mean Reciprocal Rank (MRR)  0.2000           1.0000              +0.8000
Recall@1                    0.0000           1.0000              +1.0000
Recall@3                    0.0000           1.0000              +1.0000
Recall@5                    1.0000           1.0000              +0.0000
Recall@10                   1.0000           1.0000              +0.0000
p50 Latency                 --               0.26 ms             Sub-millisecond
Model Memory                --               136 bytes           Zero GPU overhead
Training Time               --               0.0036s             (28 pairs, L-BFGS)
================================================================================
```

---

## 6. REAL MEASURED: Local ML Subsystem Latency

Empirically timed on local CPU (no GPU, no network):

| Subsystem | p50 | p95 | Memory |
| :--- | :--- | :--- | :--- |
| TF-IDF + Logistic Regression | 0.024 ms/item | 0.045 ms | ~12 MB RAM |
| Supervised Evidence Reranker | 0.26 ms/query | 0.52 ms | 136 bytes |
| Source Independence Clustering | ~1.2 ms/query | ~2.8 ms | < 1 MB |
| Contradiction Detection Matrix | ~0.85 ms/query | ~1.95 ms | < 1 MB |

All four local ML subsystems combined: **< 3 milliseconds**. End-to-end pipeline latency
(network + LLM calls) is **NOT YET MEASURED**.

---

## 7. FRAMEWORK IMPLEMENTED (No Artifact Yet): Metric Library

The following are implemented in `backend/evaluation/metrics.py` and unit-tested.
No actual Aegis pipeline run has produced artifact values yet.

- **Retrieval**: MRR, Recall@K (K=1,3,5,10)
- **Grounding & Citation**: Grounded Answer Rate, Unsupported Claim Rate, Citation Correctness, Citation Completeness
- **Abstention & Coverage**: Coverage, Covered Accuracy, Selective Risk, Coverage-Adjusted Accuracy
- **Calibration**: ECE (multi-bin), Brier Score
- **Tool-Call**: Tool-Call Success Rate, Parameter Validity Rate, Retry Rate, Useful-Query Rate
- **Statistical Testing**: McNemar's Test, 1,000-resample Bootstrap CI (Macro-F1), Wilson Score CI (proportions)

---

## 8. NOT YET EXECUTED: Ablation Study

> [!CAUTION]
> The following table contains **NO real numbers**. It shows the structure the ablation will
> produce once `run_ablation_study()` is executed with live credentials. Without credentials
> the harness currently returns `BLOCKED`.

| Stage | Configuration | Accuracy | Macro-F1 | Recall@5 | Grounded Rate | ECE | p50 | Cost/1k |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| A | LLM Only | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| B | LLM + Raw Web Search | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| C | + Supervised Reranker | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| D | + Source Independence | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| E | + Contradiction Detection | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| F | Full Aegis (+Abstention) | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

Run: `python scripts/evaluate_dataset.py --mode ablation` (requires `GEMINI_API_KEY` + search credentials)

---

## 9. NOT YET EXECUTED: End-to-End Aegis Pipeline

`run_aegis_benchmark()` currently returns: **NOT RUN -- Live multi-agent execution requires active credentials**

| Metric | Design Target | Status |
| :--- | :--- | :--- |
| Full Aegis Accuracy (6-class) | -- | NOT YET EXECUTED |
| Macro-F1 (6-class) | -- | NOT YET EXECUTED |
| RAG Recall@1/3/5/10 (live web) | -- | NOT YET EXECUTED |
| Grounded-Answer Rate | >= 88% | NOT YET EXECUTED |
| Unsupported Claim Rate | <= 5% | NOT YET EXECUTED |
| Citation Correctness | >= 92% | NOT YET EXECUTED |
| Tool-Call Success Rate | >= 95% | NOT YET EXECUTED |
| Useful-Query Rate | >= 80% | NOT YET EXECUTED |
| Abstention Rate / Coverage | -- | NOT YET EXECUTED |
| End-to-End p50/p95/p99 Latency | -- | NOT YET EXECUTED |
| Cost per Investigation | -- | NOT YET EXECUTED |
| Syndication Detection Rate | >= 91% | NOT YET EXECUTED |
| Contradiction Precision / Recall | >= 88% / >= 84% | NOT YET EXECUTED |
| FEVER Score | -- | NOT YET EXECUTED |
| AVeriTeC Score | -- | NOT YET EXECUTED |

---

## 10. Systematic Error Taxonomy

8 documented failure mode categories. **No empirical distribution percentages exist yet** --
the taxonomy is based on qualitative engineering observations during development:

1. **Missing Evidence / Cold-Start** -- Emerging events not yet indexed
2. **Retrieval Blindspots** -- Regional portals, unindexed official gazettes
3. **Syndication Echo Chambers** -- One wire story republished as N apparent confirmations
4. **Subtle Context Framing / Cherry-Picking** -- Real facts with fabricated causal implication
5. **Temporal Mismatch** -- Historical events republished deceptively
6. **Colloquial / Satirical Idioms** -- Cultural sarcasm misread as literal claims
7. **Entity Disambiguation Collisions** -- Shared names across distinct entities
8. **Over-Abstention** -- Equivocal evidence triggering unnecessary `Insufficient Evidence`

Empirical error distribution measurement is pending the full Aegis benchmark run.

---

## 11. Reproducibility Guide

```bash
# RUNS WITHOUT CREDENTIALS ---------------------------------------------------

# All offline ML benchmarks (WELFake + Reranker)
python scripts/evaluate_dataset.py --mode all_offline --seed 42

# Classical ML baseline only
python scripts/evaluate_dataset.py --mode classical_ml --seed 42

# Supervised reranker sanity experiment only
python scripts/evaluate_dataset.py --mode reranker --seed 42

# FEVER adapter status check
python scripts/evaluate_dataset.py --mode fever_status

# AVeriTeC adapter status check
python scripts/evaluate_dataset.py --mode averitec_status

# Full evaluation unit test suite
pytest tests/unit/ tests/evaluation/ -v

# REQUIRES GEMINI_API_KEY + SEARCH CREDENTIALS --------------------------------

python scripts/evaluate_dataset.py --mode llm_only
python scripts/evaluate_dataset.py --mode retrieval_llm
python scripts/evaluate_dataset.py --mode aegis
python scripts/evaluate_dataset.py --mode ablation
python scripts/evaluate_dataset.py --mode india_track
```

JSON artifacts written to `docs/evaluation/results/` with git commit hash and UTC timestamp.

---

## 12. Known Limitations

1. **All live-pipeline metrics are pending** -- Framework built and unit-tested; empirical results require active API credentials.
2. **Reranker MRR (0.20->1.00) uses synthetic candidate pools** -- Not a live web retrieval result. Genuine annotated pool evaluation is pending.
3. **Sub-Hour Breaking News** -- Evidence voids for events within minutes of verification.
4. **Audio/Video Claims** -- Textual pipeline only; deepfake forensics routed to external detectors.
5. **Regional PDF Gazettes** -- Require manual scraper adaptation for unstructured PDFs.
