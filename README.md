<div align="center">

# 🛡️ Aegis Protocol

### Multi-Agent Evidence Verification Architecture & Research Benchmark Suite

[![Python](https://img.shields.io/badge/Python-3.11+-3b82f6?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-10b981?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-AI-8b5cf6?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Supabase](https://img.shields.io/badge/Supabase-Database-3ecf8e?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![License](https://img.shields.io/badge/License-MIT-f59e0b?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-530%20Passed-success?style=for-the-badge&logo=pytest&logoColor=white)](docs/TESTING.md)
[![Evaluation](https://img.shields.io/badge/Evaluation-Audited%20ML%20Baseline-blueviolet?style=for-the-badge)](docs/EVALUATION.md)

**Aegis Protocol is an evidence-first claim verification system and research framework. It combines cross-platform evidence retrieval, learned candidate reranking, source-independence clustering, contradiction analysis, and multi-perspective LLM reasoning with abstention-aware classification.**

[📚 Documentation Portal](docs/index.md) · [🏛️ Target Architecture](docs/architecture/TARGET_ARCHITECTURE.md) · [🗺️ Migration Plan](docs/architecture/MIGRATION_PLAN.md) · [System Architecture](docs/ARCHITECTURE.md) · [Feature Status & Truth Matrix](docs/FEATURE_STATUS.md) · [Scientific Evaluation](docs/EVALUATION.md) · [Testing Suite](docs/TESTING.md) · [Security Model](docs/SECURITY.md) · [Operations](docs/OPERATIONS.md)

</div>

---

## 🔬 System Capabilities & Status Matrix

To maintain strict scientific integrity, Aegis Protocol explicitly separates **what actually runs in production** from **simulation models**, **experimental heuristics**, and **research adapters**:

| Subsystem / Component | Technical Implementation | Operational Status | Benchmark / Verification |
| :--- | :--- | :--- | :--- |
| 🛡️ **Claim Ingestion Engine** | Unicode NFC normalization, whitespace collapsing, SHA-256 deduplication, dual-column extraction | **Production / Implemented** | Tested (`pytest`), 100% deterministic |
| 🌐 **Agent Reach Layer** | 14-channel capability registry, domain retrieval planner, wire syndication clustering, SSRF defense | **Production / Implemented** | Tested (`pytest`), RFC 3986 URL parsing |
| ⚡ **Learned Evidence Reranker** | 7-feature linear ranking model (pairwise cross-entropy fit on train pairs, evaluated on held-out test queries) | **Production / Tested** | **MRR: 0.20 → 1.00 (+0.80)**, 0.26ms p50 |
| 📊 **Classical Supervised Baseline** | Deduplicated TF-IDF (10k unigram+bigram) + L2 Logistic Regression on held-out test split | **Production / Implemented** | **88.50% Accuracy, 0.8850 F1** ($N=2,948$) |
| ⚖️ **Investigator Agent** | Structured forensic case dossiers, 6-verdict taxonomy, evidence limitations disclosure | **Production / Implemented** | Tested (`pytest`), schema validated |
| 🔬 **Research Agent** | Multi-source investigation, primary source escalation, corroboration scoring | **Production / Implemented** | Tested (`pytest`), passage extraction |
| 🔍 **Scout Agent (Financial)** | Yahoo Finance real-time price feeds, volume z-scores, event-clustered news correlation | **Production / Implemented** | Tested (`pytest`), ticker validation |
| 📈 **Trending Agent (Viral Claims)** | Multi-channel RSS discovery, velocity estimation, narrative summary dossiers | **Production / Implemented** | Tested (`pytest`), sentiment baseline |
| 🛡️ **BrandShield Agent** | Brand threat cards, suspicious listing audit, coordinated astroturfing heuristic | **Production / Implemented** | Tested (`pytest`), 4-question threat cards |
| 👤 **Personal Watch Agent** | Executive & public figure monitoring across news and web channels with severity triage | **Production / Implemented** | Tested (`pytest`), diff classification |
| 🇮🇳 **India Multilingual Track** | Curated gold benchmark across English, Hindi, Marathi, and Hinglish across 5 civic domains (14 claims) | **Research / Prototype** | Gold institutional annotations (Curated Prototype) |
| ⚡ **Hawkes Process Blast Radius** | Point-process self-excitation simulation ($\lambda(t) = \mu + \sum \alpha e^{-\beta(t-t_i)}$), $R_0$ velocity | **Simulated / Demonstration** | Algorithmic model demo |
| 📐 **Zipf-Mandelbrot Detector** | Token-rank power-law fit ($P(r) = P_0(r+\beta)^{-\gamma}$) evaluating $R^2$, Shannon entropy, TTR | **Simulated / Experimental** | Statistical distribution analysis |
| 🏛️ **Byzantine Swarm Consensus** | Multi-node consensus with Weighted Mean Subsequence Reduction (W-MSR) outlier pruning | **Simulated / Experimental** | Resilient aggregation model |
| 📚 **AVeriTeC Adapter** | NeurIPS 2023 claim verification benchmark loader (1.2 GB corpus) | **Research / Ready** | Adapter created; reports `NOT RUN` locally |

---

## 📊 Scientific Evaluation & Ground-Truth Leakage Prevention

### Invalidation of the Prior 93.33% Claim
Earlier project documentation cited a **93.33% accuracy** on a 50-sample slice of WELFake. Code audit revealed that this benchmark ran under `gemini.mock_mode = True` while using dataset ground-truth labels to generate synthetic evidence strings that the mock provider then regurgitated. **That number was an artifact of mock circularity and has been formally retired.**

### Audited Real-World Baselines

1. **Supervised Classical ML Baseline (WELFake Held-Out Test Split, $N=2,948$)**:
   - **Accuracy**: **88.50%** (95% Wilson Score CI: `[87.30%, 89.60%]`)
   - **Macro-F1**: **0.8850** (95% Non-parametric Bootstrap CI: `[0.8731, 0.8958]`)
   - **Macro-Precision**: 0.8850 | **Macro-Recall**: 0.8850
   - **Expected Calibration Error (ECE)**: 0.0887 | **Brier Score**: 0.0945
   - **Inference Throughput**: ~72,000 samples/sec (CPU-only, 0.041s for 2,948 items)
   - **Zero ground-truth or content leakage**: 800 duplicate titles removed pre-split; exact zero duplicate titles across train ($N=13,752$), val ($N=2,947$), and test ($N=2,948$) partitions.

2. **Learned Evidence Reranker Evaluation (Pairwise-Trained on Held-Out Test Queries)**:
   - **Training Protocol**: Pairwise cross-entropy fit (`reranker.fit()`) via L-BFGS on training claim-evidence candidate pairs.
   - **Evaluation**: Evaluated on held-out test queries with 15 candidate documents each (including distracting negatives).
   - **Mean Reciprocal Rank (MRR)**: Raw Search = 0.2000 → Reranked = **1.0000** ($\Delta +0.8000$)
   - **Recall@5**: 1.0000 | **Recall@10**: 1.0000
   - **Median Latency (p50)**: **0.26 ms** | **Model Size**: 136 bytes

For full methodology, calibration reliability diagrams, and ablation analysis, see [`docs/EVALUATION.md`](docs/EVALUATION.md).

---

## 🏗️ Architecture

```
User / External Ingestion
         │
         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  /api/claims │  │  /api/scout  │  │/api/trending │  │/api/brand- │  │
│  │   /submit    │  │   /analyze   │  │    /scan     │  │   shield   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│         │                 │                 │                │         │
│  ┌──────▼─────────────────▼─────────────────▼────────────────▼──────┐  │
│  │                      Agent & Capability Layer                    │  │
│  │  • ClaimIngestionAgent: Unicode NFC + SHA-256 deduplication      │  │
│  │  • Agent Reach Layer: 14-channel capability router + SSRF guard  │  │
│  │  • Learned Evidence Reranker: 7-dim TF-IDF feature ranker        │  │
│  │  • Source Independence Engine: Wire syndication clustering       │  │
│  │  • Contradiction Detector: Polarity & conflict matrix            │  │
│  │  • InvestigatorAgent: Multi-perspective 6-verdict reasoning      │  │
│  └──────┬───────────────────────────────────┬───────────────────────┘  │
│         │                                   │                          │
│  ┌──────▼──────┐                     ┌──────▼──────┐                   │
│  │  Supabase   │                     │ Gemini API  │                   │
│  │ PostgreSQL  │                     │ Key Cycle   │                   │
│  └─────────────┘                     └─────────────┘                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Clone & Environment Setup

```bash
git clone https://github.com/Shaunakrane914/Misinformation.git
cd Misinformation

python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Google Gemini (Supports key rotation across multiple keys)
GEMINI_API_KEY=AIzaSy...your_primary_key
GEMINI_API_KEY_1=AIzaSy...backup_key_1

# Supabase Storage & Persistence
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Operational Settings
DASHBOARD_TTL=300
LOG_LEVEL=INFO
```

### 3. Run Application Server

```bash
python main.py
```
Open [http://localhost:8000](http://localhost:8000) for the UI and [http://localhost:8000/docs](http://localhost:8000/docs) for the OpenAPI specification.

---

## 🧪 Scientific Benchmark CLI

Run reproducible, leak-free evaluations directly from the command line:

```bash
# 1. Run all offline ML benchmarks (WELFake Classical ML + Learned Reranker)
python scripts/evaluate_dataset.py --mode all_offline --seed 42

# 2. Run only the Supervised Classical ML Baseline
python scripts/evaluate_dataset.py --mode classical_ml --seed 42

# 3. Run only the Learned Evidence Reranker Evaluation
python scripts/evaluate_dataset.py --mode reranker --seed 42

# 4. Check AVeriTeC Benchmark Adapter Status
python scripts/evaluate_dataset.py --mode averitec_status

# 5. Execute full test suite (530 regression tests)
pytest
```

---

## 🗺️ Workbenches & Specialized Interfaces

| Route | Workbench | Function & Specialized Capabilities |
| :--- | :--- | :--- |
| `/` | **Landing Page** | System overview, capability matrix, and architecture entry points |
| `/dashboard` | **Live Claims Feed** | Verified claims feed with evidence badges, confidence, and source provenance |
| `/submit` | **Claim Submission** | Ingestion portal with live normalization, status polling, and dossier generation |
| `/investigator-agent` | **Investigator** | Forensic evidence dossiers, timeline reconstructor, contradiction matrix, and verdict synthesis |
| `/research-agent` | **Research** | Deep research workspace, extracted passage citations, source quality scores, and reading list |
| `/scout-agent` | **Scout (Financial)** | Market anomaly monitor, ticker volatility correlation, and event-clustered news signals |
| `/trending-agent` | **Trending (Viral)** | Multi-channel trend discovery, velocity estimation, and narrative defense statements |
| `/brandshield-agent` | **BrandShield** | Brand reputation defense, 4-question threat cards, and astroturfing review audit |
| `/personal-watch-agent` | **Personal Watch** | Executive & public persona defense, change-first diffs, and compact alert history |
| `/about` | **Methodology** | System architecture, scientific evaluation taxonomy, and research methodology |
| `/status` | **System Health** | Real-time health metrics, provider status, and endpoint telemetry |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
