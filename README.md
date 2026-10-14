<div align="center">

# 🛡️ Aegis Protocol

### Multi-Agent Evidence Verification Architecture & Research Benchmark Suite

[![Python](https://img.shields.io/badge/Python-3.11+-3b82f6?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-10b981?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-AI-8b5cf6?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Supabase](https://img.shields.io/badge/Supabase-Database-3ecf8e?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![License](https://img.shields.io/badge/License-MIT-f59e0b?style=for-the-badge)](LICENSE)
[![CI](https://img.shields.io/badge/CI-Phase%208%20branch%20passing-success?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/Shaunakrane914/Misinformation/actions/runs/38420523255)
[![Evaluation](https://img.shields.io/badge/Evaluation-Audited%20ML%20Baseline-blueviolet?style=for-the-badge)](docs/EVALUATION.md)
[![Status](https://img.shields.io/badge/Status-Phase%208%20in%20progress-orange?style=for-the-badge)](docs/CURRENT_STATE.md)

**Aegis Protocol is an evidence-first claim verification system and research framework. It combines cross-platform evidence retrieval across 16 operations, claim-aware source planning, learned candidate reranking, source-independence clustering, contradiction analysis, and multi-perspective LLM reasoning with abstention-aware classification.**

[📚 Documentation Portal](docs/index.md) · [Current State](docs/CURRENT_STATE.md) · [🤖 Coding Agents Guide](AGENTS.md) · [🗺️ Workspace Map](docs/development/WORKSPACE_MAP.md) · [📜 Script Index](docs/development/SCRIPT_INDEX.md) · [🏛️ Target Architecture](docs/architecture/TARGET_ARCHITECTURE.md) · [Testing Suite](docs/testing/CI_COVERAGE_MATRIX.md)

</div>

---

The current Phase 8 branch has bounded live proof for 16 protected acquisition
operations and passing offline CI, but maximum extraction, research-quality
evaluation, complete frontend acceptance and deployed rollback are not finished.
The [independent Phase 8 review](docs/architecture/PHASE8_INDEPENDENT_REVIEW_2026-10-14.md)
corrected source spoofing, manufactured citations, unsupported specialist labels,
real API contract failures and mobile result overflow. Test/CI results are dated
checkpoints, not misinformation accuracy or production-launch approval. See the
[current-state matrix](docs/CURRENT_STATE.md) before using the historical
benchmarks and capability descriptions below.

## 🔬 System Capabilities & Status Matrix

To maintain strict scientific integrity, Aegis Protocol explicitly separates **what actually runs in production** from **simulation models**, **experimental heuristics**, and **research adapters**:

| Subsystem / Component | Technical Implementation | Operational Status | Benchmark / Verification |
| :--- | :--- | :--- | :--- |
| 🛡️ **Claim Ingestion Engine** | Unicode NFC normalization, whitespace collapsing, SHA-256 deduplication | **Implemented / offline-tested** | Deterministic contracts; not verdict-accuracy proof |
| 🌐 **Agent Reach Layer** | 16 protected routes, auxiliary channels, bounded acquisition, source planning and SSRF defense | **Implemented / sampled live proof** | [8A/8B status](docs/CURRENT_STATE.md); source availability and field depth vary |
| ⚡ **Learned Evidence Reranker** | 7-feature linear ranking model | **Offline benchmarked** | Historical held-out MRR 0.20 → 1.00; not a live-verdict score |
| 📊 **Classical Supervised Baseline** | Deduplicated TF-IDF + L2 Logistic Regression | **Offline benchmarked** | Historical WELFake 88.50% accuracy; not Aegis end-to-end accuracy |
| ⚖️ **Investigator Agent** | Claim verdict synthesis and evidence limitations | **Integrated / partially evaluated** | Abstains when inspectable evidence is insufficient; adversarial quality gate open |
| 🔬 **Research Agent** | Source planning, reading, qualification and synthesis | **Integrated / partially evaluated** | Source depth, coverage and entailment vary by investigation |
| 🔍 **Scout Agent (Financial)** | Financial signal and source research | **Implemented / offline-tested** | Prices and disclosures require actual live source availability |
| 📈 **Trending Agent (Viral Claims)** | Topic discovery and sampled narrative signals | **Implemented / offline-tested** | Source counts do not prove platform-wide reach or independent origins |
| 🛡️ **BrandShield Agent** | Brand-threat observation and review screening | **Implemented / offline-tested** | Empty results do not prove absence of threats or coordination |
| 👤 **Personal Watch Agent** | Public identity and impersonation research | **Implemented / offline-tested** | User-entered handles are unverified candidates; privacy limits apply |
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
│  │  • Agent Reach Layer: protected routes + SSRF guard           │  │
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

## 🧪 Benchmarks & Release Validation CLI

Run reproducible evaluations and release validation directly from the command line:

```bash
# 1. Run the full offline regression suite (current count varies)
pytest tests/ -q

# 2. Run isolated release-candidate smoke validation (all 4 agents)
python scripts/validate_release_candidate_smoke.py

# 3. Validate database and dossier rollback compatibility
python scripts/validate_rollback_compatibility.py

# 4. Run all offline ML benchmarks (WELFake Classical ML + Learned Reranker)
python scripts/evaluate_dataset.py --mode all_offline --seed 42

# 5. Run Cranfield retrieval quality benchmark on frozen fixtures
python scripts/benchmarks/run_retrieval_benchmark.py
```

---

## 🗺️ Workbenches & Specialized Interfaces

| Route | Workbench | Function & Specialized Capabilities |
| :--- | :--- | :--- |
| `/` | **Landing Page** | System overview, capability matrix, and architecture entry points |
| `/dashboard` | **Live Claims Feed** | Verified claims feed with evidence badges, confidence, and source provenance |
| `/submit` | **Claim Submission** | Ingestion portal with live normalization, status polling, and dossier generation |
| `/investigator-agent` | **Investigator entry** | Opens the claim-verification workspace; no standalone browser-side dossier generator |
| `/research-agent` | **Research entry** | Opens the claim-verification workspace; no standalone open-ended query API |
| `/scout-agent` | **Scout (Financial)** | Market anomaly monitor, ticker volatility correlation, and event-clustered news signals |
| `/trending-agent` | **Trending (Viral)** | Multi-channel trend discovery, velocity estimation, and narrative defense statements |
| `/brandshield-agent` | **BrandShield** | Brand reputation defense, 4-question threat cards, and astroturfing review audit |
| `/personal-watch-agent` | **Personal Watch** | Executive & public persona defense, change-first diffs, and compact alert history |
| `/about` | **Methodology** | System architecture, scientific evaluation taxonomy, and research methodology |
| `/status` | **System Health** | Real-time health metrics, provider status, and endpoint telemetry |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
