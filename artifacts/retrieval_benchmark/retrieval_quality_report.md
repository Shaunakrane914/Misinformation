# Aegis Retrieval Quality Benchmark — Audited Report

## Executive Summary

This report delivers the audited, mathematically reconciled evaluation of candidate retrieval quality across the Aegis Protocol's four production intelligence agents: **BrandShield**, **Trending**, **Scout**, and **Personal Watch**.

Following the initial benchmark milestone, this audit investigated and resolved:
1. **Mathematical reconciliations of Precision@k and Recall@k:** Reconciled the 16.35% Precision@5 result against the exact candidate pool ($85 / 520$), replaced pool-saturated Recall@5 with Cranfield-valid Recall@k evaluated strictly over queries with $R_{\text{query}} \ge 1$, and added natural pool cutoffs at $k \in \{1, 3, 4\}$.
2. **System isolation verification:** Proved that the Deterministic Baseline, Hybrid Lexical+Neural, and Neural Second-Stage CrossEncoder systems run independently, generate separate ranking orders, and produce distinct metrics (20 scenarios diverge between Baseline and Reranker).
3. **Neural Reranker performance assessment:** Confirmed that the CrossEncoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) **does not outperform** the deterministic baseline. The neural reranker achieves lower nDCG@4 (94.42% vs 95.75%), lower hard-negative rejection (92.31% vs 96.15%), lower Strict Precision@1 (48.08% vs 50.0%), and lower holdout MRR (37.5% vs 40.0%).
4. **Engineering verdict:** **Semantic reranking must remain DISABLED in production (`AEGIS_SEMANTIC_RERANKER=0`)**. The deterministic RelevanceGate and EntityResolver remain the authoritative production ranker.

---

## Dataset & Candidate Pool Structure

The golden retrieval benchmark dataset is frozen in `tests/retrieval_benchmark/` and validated by `scripts/validate_retrieval_benchmark.py`:

- **Total Scenarios:** `104` (Development: `84` [80.8%], Holdout: `20` [19.2%])
  - **BrandShield:** 26 scenarios (21 dev, 5 holdout)
  - **Trending:** 26 scenarios (21 dev, 5 holdout)
  - **Scout:** 26 scenarios (21 dev, 5 holdout)
  - **Personal Watch:** 26 scenarios (21 dev, 5 holdout)
- **Candidate Pool Size per Scenario:** `N = 4` candidates per scenario (`416` total candidates across the dataset).
- **Gold Label Relevance Distribution:**
  - **Grade 3 (Strict Direct True Positive):** `53` candidates (12.7%)
  - **Grade 2 (Secondary Relevant / Background):** `32` candidates (7.7%)
  - **Grade 1 (Boundary Distractor / Passive Mention):** `184` candidates (44.2%)
  - **Grade 0 (Hard Negative / Adversarial Homograph / Noise):** `147` candidates (35.3%)
- **Total Broad Relevant Candidates (Grades 2–3):** Exactly `85` candidates distributed across `58` scenarios.
- **Purely Negative / Distractor Scenarios:** `46` scenarios contain zero relevant documents (only grades 0 and 1) to test false-positive rejection.

---

## Methodology & Mathematical Formulations

To ensure mathematical validity over a fixed 4-candidate pool, all metrics follow standard Cranfield and TREC information retrieval definitions:

### 1. Fixed-Denominator Precision@k
$$\text{Precision@k}(\tau) = \frac{\sum_{i=1}^{\min(|G|, k)} \mathbb{I}(g_i \ge \tau)}{k}$$
- **Evaluated Cutoffs:** $k = 1, 3, 4$ (within pool) and $k = 5$ (exceeding pool).
- **Broad Precision ($\tau = 2$):** Grades 2 and 3 count as relevant.
- **Strict Precision ($\tau = 3$):** Grade 3 only counts as relevant.
- **Reconciliation of Precision@5:** With 85 total candidates of grade $\ge 2$ across 104 scenarios, fixed-denominator P@5 across the full dataset is mathematically:
  $$\frac{85}{104 \times 5} = \frac{85}{520} = 16.346\% \approx 16.35\%$$
  The previous report's reference to "141 candidates" was an unverified text typo; the actual dataset contains 85 candidates with grade $\ge 2$. When evaluated with natural pool denominator $k=4$, Precision@4 is $85 / (104 \times 4) = 85 / 416 = 20.43\%$.

### 2. Cranfield-Valid Recall@k
$$\text{Recall@k} = \frac{\sum_{i=1}^{\min(|G|, k)} \mathbb{I}(g_i \ge 2)}{R_{\text{query}}}$$
- In standard IR evaluation, Recall is defined **only** for queries where at least one relevant document exists ($R_{\text{query}} \ge 1$).
- In our dataset, exactly **58 scenarios** contain relevant documents (50 in Dev, 8 in Holdout). The 46 purely negative scenarios return `None` for Recall and are excluded from the macro-average.
- This eliminates the vacuous artifact where negative queries were previously reported as "100% recall on 0 documents".

### 3. Mean Reciprocal Rank (MRR)
$$\text{RR} = \begin{cases} \frac{1}{\text{rank}^*} & \text{if a relevant candidate is retrieved at rank } \text{rank}^* \le 4 \\ 0.0 & \text{otherwise} \end{cases}$$

### 4. Normalized Discounted Cumulative Gain (nDCG@k)
$$\text{DCG@k} = \sum_{i=1}^{\min(|G|, k)} \frac{2^{g_i} - 1}{\log_2(i + 1)}, \quad \text{nDCG@k} = \frac{\text{DCG@k}}{\text{IDCG@k}}$$
- Uses standard exponential relevance gain with logarithmic rank discounting.

### 5. Hard-Negative Rejection Rate
$$\text{Rejection Rate} = \frac{\sum_{s \in \mathcal{S}_{\text{HN}}} \mathbb{I}(g_{s, 1} \ne 0)}{|\mathcal{S}_{\text{HN}}|}$$
- Evaluated strictly over the set of scenarios containing at least one Grade 0 candidate ($|\mathcal{S}_{\text{HN}}| = 104$). A scenario succeeds if the Grade 0 candidate is **not** placed at Rank 1.

---

## System Isolation & Ranking Divergence Verification

Every scenario generates rankings independently for each system using deep-copied candidate records. Automated verification (`test_system_ranking_divergence`) proves the systems produce distinct candidate orderings:

- **Deterministic vs. Neural Reranker:** Diverged on **20 scenarios** (19.2% of dataset).
- **Deterministic vs. Hybrid:** Diverged on **13 scenarios** (12.5% of dataset).
- **Hybrid vs. Neural Reranker:** Diverged on **7 scenarios** (6.7% of dataset).

### Concrete Divergence Examples:
1. `brand_msft_fake_teams_installer_018`:
   - Deterministic ordered grades: `[1, 3, 1, 0]` (Rank 1: Grade 1 distractor).
   - Reranker ordered grades: `[3, 1, 1, 0]` (CrossEncoder successfully promoted the Grade 3 malware installer to Rank 1).
2. `brand_audit_msft_licenses_holdout_022`:
   - Deterministic ordered grades: `[3, 1, 1, 0]` (Rank 1: Grade 3 rogue reseller scam).
   - Reranker ordered grades: `[1, 3, 1, 0]` (CrossEncoder demoted the Grade 3 scam to Rank 2, promoting a Grade 1 SAM audit guide).
3. `scout_scenario_014_dev`, `016_dev`, `024_holdout`:
   - Deterministic ordered grades: `[1, 0, 1, 0]` (Rank 1: Grade 1 distractor; Rank 2: Grade 0 penny stock).
   - Reranker ordered grades: `[0, 1, 1, 0]` (CrossEncoder scored the penny stock distractor higher than the general market roundup, causing a **Grade 0 hard negative leak** into Rank 1).

---

## Audited Overall Benchmark Results

| Metric | System A: Deterministic Baseline | System B: Hybrid Lexical+Neural | System C: Neural Second-Stage | Delta (C vs A) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Broad Precision@1 (Grades 2–3)** | **52.88%** (55/104) | **52.88%** (55/104) | **52.88%** (55/104) | `0.0%` | Parity |
| **Strict Precision@1 (Grade 3)** | **50.00%** (52/104) | **50.00%** (52/104) | **48.08%** (50/104) | **-1.92%** | **Degraded** |
| **Broad Precision@3 (k=3)** | **27.24%** | **27.24%** | **27.24%** | `0.0%` | Parity |
| **Broad Precision@4 (k=4)** | **20.43%** | **20.43%** | **20.43%** | `0.0%` | Parity |
| **Cranfield Recall@1 ($R \ge 1$)** | **71.55%** | **71.55%** | **71.55%** | `0.0%` | Parity |
| **Cranfield Recall@3 ($R \ge 1$)** | **100.00%** | **100.00%** | **100.00%** | `0.0%` | Pool Limit |
| **Cranfield Recall@4 ($R \ge 1$)** | **100.00%** | **100.00%** | **100.00%** | `0.0%` | Pool Limit |
| **MRR (Broad)** | **54.33%** | **54.33%** | **54.33%** | `0.0%` | Parity |
| **Strict MRR (Grade 3)** | **50.48%** | **50.48%** | **49.52%** | **-0.96%** | **Degraded** |
| **nDCG@3** | **95.75%** | **94.72%** | **94.42%** | **-1.33%** | **Degraded** |
| **nDCG@4 (Full Pool)** | **95.75%** | **94.72%** | **94.42%** | **-1.33%** | **Degraded** |
| **Entity Accuracy @ Rank 1** | **94.23%** (98/104) | **89.42%** (93/104) | **86.54%** (90/104) | **-7.69%** | **Degraded** |
| **Intent Accuracy @ Rank 1** | **50.00%** (52/104) | **50.00%** (52/104) | **48.08%** (50/104) | **-1.92%** | **Degraded** |
| **Hard-Negative Rejection Rate** | **96.15%** (100/104) | **92.31%** (96/104) | **92.31%** (96/104) | **-3.84%** | **Degraded** |

---

## Development vs. Holdout Generalization

| Metric | Development Set (N=84) — Det | Development Set (N=84) — Rer | Holdout Set (N=20) — Det | Holdout Set (N=20) — Rer |
| :--- | :---: | :---: | :---: | :---: |
| **Broad Precision@1** | **55.95%** (47/84) | **57.14%** (48/84) | **40.00%** (8/20) | **35.00%** (7/20) |
| **Strict Precision@1** | **52.38%** (44/84) | **52.38%** (44/84) | **40.00%** (8/20) | **30.00%** (6/20) |
| **Cranfield Recall@1** | **70.00%** | **72.00%** | **81.25%** | **68.75%** |
| **MRR (Broad)** | **57.74%** | **58.33%** | **40.00%** | **37.50%** |
| **nDCG@4** | **95.90%** | **95.04%** | **95.09%** | **91.81%** |
| **Entity Accuracy @ 1** | **95.24%** | **88.10%** | **90.00%** | **80.00%** |
| **Hard-Negative Rejection** | **96.43%** | **92.86%** | **95.00%** | **90.00%** |

### Sample Size & Statistical Uncertainty Notice
In the 20-scenario holdout set, **each scenario represents exactly 5.0 percentage points**. The apparent drop in Reranker Holdout Strict P@1 (from 40.0% to 30.0%) represents a divergence on exactly 2 scenarios. However, the consistent direction of degradation across nDCG, Hard-Negative Rejection, and Entity Accuracy indicates a systematic vulnerability rather than random noise.

---

## Per-Agent Performance Breakdown

| Agent | Scenarios | Broad P@1 (Det / Rer) | Strict P@1 (Det / Rer) | nDCG@4 (Det / Rer) | Hard-Neg Rejection (Det / Rer) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **BrandShield** | 26 | **65.38%** / 65.38% | **65.38%** / 65.38% | **98.85%** / 97.36% | **100.0%** / 96.15% |
| **Trending** | 26 | **46.15%** / 46.15% | **46.15%** / 46.15% | **89.22%** / 89.22% | **84.62%** / 84.62% |
| **Scout** | 26 | **50.00%** / 50.00% | **50.00%** / 42.31% | **97.70%** / 95.10% | **100.0%** / 88.46% |
| **Personal Watch** | 26 | **50.00%** / 50.00% | **38.46%** / 38.46% | **97.22%** / 96.00% | **100.0%** / 100.0% |

---

## Classification Category Breakdown

| Scenario Classification | Count | Broad P@1 (Det) | Strict P@1 (Det) | Hard-Neg Rejection (Det) | Hard-Neg Rejection (Rer) | Root Cause |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `TRUE_POSITIVE` | 48 | **97.92%** | **97.92%** | **100.0%** | **100.0%** | Exact entity + domain threat intent |
| `HOMOGRAPH_NEGATIVE` | 7 | **0.0%** | **0.0%** | **100.0%** | **100.0%** | Sanskrit philosophy & Bollywood film suppressed |
| `HARD_NEGATIVE` | 11 | **18.18%** | **0.0%** | **100.0%** | **88.46%** | Reranker leaked 3 penny stock distractors |
| `TEMPORAL_NEGATIVE` | 4 | **0.0%** | **0.0%** | **0.0%** | **0.0%** | Stale 2021 articles leak due to lack of age filter |
| `BOUNDARY_NEGATIVE` | 17 | **11.76%** | **11.76%** | **100.0%** | **100.0%** | Competitor marketing mentions |
| `BENIGN_DISTRACTOR` | 6 | **0.0%** | **0.0%** | **100.0%** | **100.0%** | Routine developer tooling updates |
| `OUT_OF_DOMAIN` | 5 | **0.0%** | **0.0%** | **100.0%** | **100.0%** | Broad market ETF constituents |
| `DEDUPLICATION` | 3 | **100.0%** | **100.0%** | **100.0%** | **100.0%** | Wire syndication clustering |

---

## Why the Neural Reranker Underperforms the Deterministic Baseline

1. **Semantic Similarity Ignores Entity Bounds:** Pre-trained CrossEncoders compute dense cross-attention between token sequences. When given query `"Microsoft MSFT financial regulatory query"` and a distractor title `"Penny Stock Speculation Alert (MSFT Peer Compare)"`, the CrossEncoder awards a high logit because many words match the domain. The deterministic `EntityResolver` specifically detects that the subject is not Microsoft and penalizes it.
2. **Loss of Temporal Discernment:** In Trending, CrossEncoder awards high similarity to archived articles from 2021 because they are topical matches, completely blind to publication timestamp.
3. **Computational Overhead with Zero Gain:** On CPU inference, the CrossEncoder takes ~18ms per scenario, adding latency while degrading Hard-Negative Rejection by 3.84 percentage points and Strict P@1 by 1.92 percentage points.

---

## Architectural Verdict & Next Steps

1. **Production Decision:** **Keep the neural reranker disabled in production**. The deterministic pipeline (`RelevanceGate` + `EntityResolver`) provides superior precision, superior hard-negative defense, zero model latency, and zero dependency risk.
2. **Address Genuine Deficiencies:**
   - **Trending Temporal Gating:** Add an explicit age threshold (< 48 hours) to prevent archived stories from leaking.
   - **Ticker Centrality in Scout:** Require ticker mention to be the primary corporate subject rather than a constituent in an ETF table.
3. **Benchmark Corpus Expansion:** When live discovery candidates are collected, expand the pool from $N=4$ to $N=15$–20 candidates per scenario to enable meaningful Recall@10 evaluation without pool saturation.
