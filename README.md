<div align="center">

# 🛡️ Aegis Protocol

### Multi-Agent AI System for Real-Time Misinformation Detection

[![Python](https://img.shields.io/badge/Python-3.11+-3b82f6?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-10b981?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-AI-8b5cf6?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Supabase](https://img.shields.io/badge/Supabase-Database-3ecf8e?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![License](https://img.shields.io/badge/License-MIT-f59e0b?style=for-the-badge)](LICENSE)

**Four specialized AI agents work simultaneously — scanning financial markets, trending content, brand reputation, and personal profiles for misinformation threats before they spread.**

[Live Demo](#) · [API Docs](http://localhost:8000/docs) · [Changelog](frontend/changelog.html)

</div>

---

## ✨ What It Does

Aegis Protocol is a **production-grade, multi-agent misinformation detection platform**. Submit any claim and receive a `True / False / Misleading` verdict in ~18 seconds — backed by live web research, multi-pass AI reasoning, and confidence scoring.

Beyond claim verification, four specialized agents and an experimental Threat Intelligence Lab run autonomously:

| Agent / Instrument | Domain | Status |
|---|---|---|
| 🔍 **Scout** | Financial misinformation — stock crashes correlated with viral rumors | ✅ Live |
| 📈 **Trending** | Celebrity & viral content analysis via RSS + Apify | ✅ Live |
| 🛡️ **BrandShield** | Fake reviews, counterfeit listings, reputation attacks | ✅ Live |
| 👤 **Personal Watch** | Individual reputation monitoring across 5+ platforms | ✅ Live |
| ⚡ **Threat Lab** | Mandelbrot synthetic detector, Hawkes blast radius, Byzantine swarm consensus | ✅ Live |

---

## 🏗️ Architecture

```
User / External System
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (v3.0.0)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   /api/     │  │  /api/       │  │  /api/               │  │
│  │  claims/    │  │  dashboard/  │  │  brandshield/        │  │
│  │  submit     │  │  claims      │  │  personal/           │  │
│  └──────┬──────┘  └──────┬───────┘  │  scout/ trending/   │  │
│         │                │          └──────────────────────┘  │
│  ┌──────▼──────────────────────────────────────────────────┐  │
│  │                  Agent Layer                             │  │
│  │  ClaimIngestion → ResearchAgent → InvestigatorAgent     │  │
│  │  ScoutAgent    │  TrendingAgent │  BrandShieldAgent     │  │
│  │  PersonalWatchAgent                                      │  │
│  └──────┬──────────────────┬───────────────────────────────┘  │
│         │                  │                                    │
│  ┌──────▼──────┐   ┌───────▼────────┐                         │
│  │  Supabase   │   │  Gemini 2.5    │                         │
│  │  (claims,   │   │  Flash API     │                         │
│  │   evidence, │   │  (reasoning +  │                         │
│  │   signals)  │   │   analysis)    │                         │
│  └─────────────┘   └────────────────┘                         │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
  HTML/CSS/JS Frontend
  (aegis-theme.css design system)
```

### The 5-Step Claim Pipeline

```
01. Claim Ingested      02. Evidence Gathered     03. AI Investigation
ClaimIngestionAgent  →  ResearchAgent           →  InvestigatorAgent
Normalize, hash,        DuckDuckGo + News APIs      Multi-pass Gemini
deduplicate             5+ sources                  reasoning

04. Verdict Issued      05. Stored & Learned
True/False/Misleading →  Supabase DB
Confidence score         Feedback loop
Evidence citations        improves accuracy
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- A [Gemini API key](https://ai.google.dev) (free tier works)
- A [Supabase](https://supabase.com) project (free tier works)

### 1. Clone & Install

```bash
git clone https://github.com/Shaunakrane914/Misinformation.git
cd Misinformation

python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Gemini AI (supports multiple keys for load balancing)
GEMINI_API_KEY=your_primary_key
GEMINI_API_KEY_1=your_key_1
GEMINI_API_KEY_2=your_key_2

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Optional
YF_API_KEY=your_yahoo_finance_key     # For Scout Agent stock data
APIFY_TOKEN=your_apify_token          # For Twitter scraping in Personal Watch
RSS_INGESTION_ENABLED=true            # Auto-ingest from news RSS (15min interval)
DASHBOARD_TTL=300                     # Dashboard cache TTL in seconds
LOG_LEVEL=INFO
```

### 3. Run

```bash
python main.py
```

Open [http://localhost:8000](http://localhost:8000) — you're live.

---

## 🗺️ Pages & Routes

| Route | Description |
|---|---|
| `/` | Landing page with agent overview |
| `/dashboard` | Live claims feed with AI explanations |
| `/submit` | Submit any claim for fact-checking |
| `/agents` | All 4 agents overview |
| `/scout-agent` | Financial Watchdog — analyze any stock ticker |
| `/trending-agent` | Celebrity & content intelligence |
| `/brandshield-agent` | Brand reputation scanner |
| `/personal-watch-agent` | Individual reputation monitor |
| `/about` | System architecture details |
| `/changelog` | Version history |
| `/status` | System health |

---

## 📡 API Reference

### Claims

```bash
# Submit a claim for fact-checking
POST /api/claims/submit
{ "claim_text": "Tesla stock crashed because of a fake CEO tweet", "source_url": "https://..." }

# Poll for result
GET /api/claims/{claim_id}

# List all claims
GET /api/claims?limit=50&offset=0
```

### Dashboard

```bash
# Get 15 claims for live dashboard (Supabase-first, WELFake fallback)
GET /api/dashboard/claims

# AI explanation for a specific claim
POST /api/explain-claim
{ "claim": "...", "verdict": "False" }
```

### Agents

```bash
# Scout Agent — analyze a stock ticker
POST /api/scout/analyze
{ "ticker": "TATAMOTORS.NS" }

# BrandShield — scan a brand
POST /api/brandshield/scan
{ "brand_name": "Samsung Galaxy S24" }

# Personal Watch — scan a public figure
POST /api/personal/scan
{ "name": "Elon Musk" }

# Trending — scan a celebrity/asset
POST /api/trending/scan
{ "asset_name": "Virat Kohli" }

# Threat Intelligence Lab — Synthetic Text Detector (Mandelbrot Fit)
POST /api/lab/synthetic-detect
{ "text": "Aegis Nexus Corporation today announced..." }

# Threat Intelligence Lab — Hawkes Process Blast Radius Modeler
POST /api/lab/blast-radius
{ "topic": "Deepfake CEO Audio", "claim": "Emergency liquidity shortfall..." }

# Threat Intelligence Lab — Byzantine Swarm Consensus (W-MSR Filtered)
POST /api/lab/consensus
{ "claim": "Apollo 11 moon landing was staged in Nevada" }
```

### Health

```bash
GET /api/healthz          # → { "status": "ok", "version": "3.0.0" }
GET /api/                 # → full endpoint listing
```

---

## 🤖 Agent Deep Dive

### 🔍 Scout Agent (Financial Watchdog)
Monitors stock market anomalies and correlates crashes with viral misinformation using Yahoo Finance + Google News RSS. Features:
- **Predictive Impact Modeling** — Monte Carlo crash simulation
- **Autonomous Investigator Swarm** — Multi-agent AI debate on causality
- **Network Neutralization** — Bot graph mapping
- **Strategic Response Orchestrator** — Countermeasure generation
- **Self-Healing Feedback Loop** — Outcome learning from deployed responses

### 📈 Trending Agent (Content Intelligence)
Real-time analysis of celebrity, brand, and entertainment misinformation across RSS feeds and Apify-scraped social content. Generates AI defense statements for detected rumors.

### 🛡️ BrandShield Agent
Scans Amazon, Flipkart, Trustpilot, Reddit, and Google Reviews for:
- Coordinated fake review campaigns (with fake-score 0–100)
- Counterfeit product listings
- Brand reputation attacks and FUD campaigns
- AI analysis via Gemini with heuristic fallback

### 👤 Personal Watch Agent
Monitors online reputation for any individual across Twitter/X, LinkedIn, YouTube, Reddit, and Google News. Classifies findings as Defamation, Fake Quote, Harassment, False Rumor, or Legitimate Criticism with severity ratings.

### ⚡ Threat Intelligence Lab (Deterministic & Physics-First Verification)
Interactive, research-grade verification instruments hosted at `/lab`:
- **Mandelbrot Token-Rank Regression** ($P(r) = P_0 (r+\beta)^{-\gamma}$): Evaluates power-law fit ($R^2$), Shannon entropy, and Type-Token Ratio (TTR) to detect autoregressive synthetic text distributions.
- **Hawkes Point-Process Blast Radius Modeler** ($\lambda(t) = \mu + \sum \alpha e^{-\beta(t-t_i)}$): Computes effective reproduction number $R_0$, self-excitation cascades, and 24-hour network reach projections.
- **Byzantine Swarm Consensus Engine**: Executes multi-agent adversarial evaluation (Skeptic Node, Empirical Node, Adversary Node) and applies Weighted Mean Subsequence Reduction (W-MSR) to prune compromised or hallucinating outlier nodes.

---

## 🗄️ Database Schema (Supabase)

```sql
-- Core tables
claims          -- Submitted claims with verdicts, confidence, reasoning
evidence        -- Supporting evidence per claim

-- War Room tables (Scout Agent)
active_signals       -- Detected crash/volatility events
verified_threats     -- Correlated misinformation + crash events
deployed_measures    -- Crisis response deployments
```

Run `backend/setup_aegis_db.sql` in your Supabase SQL editor to create the War Room tables.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **AI** | Google Gemini 2.5 Flash (multi-key rotation) |
| **Database** | Supabase (PostgreSQL) |
| **Web Search** | DuckDuckGo Search, Apify (Twitter) |
| **News** | RSS/Atom feeds via feedparser, Google News |
| **Stock Data** | Yahoo Finance API |
| **Frontend** | Vanilla HTML/CSS/JS, Space Grotesk + JetBrains Mono |
| **Deployment** | Render (backend), Netlify (frontend proxy) |
| **Dataset** | WELFake (72,000 labeled news claims) |

---

## 📁 Project Structure

```
Misinformation/
├── main.py                          # Root entry point — mounts /api + frontend
├── requirements.txt
├── backend/
│   ├── main.py                      # FastAPI app, all routes (v3.0.0)
│   ├── agents/
│   │   ├── claim_ingestion_agent.py # Normalize & hash claims
│   │   ├── research_agent.py        # Evidence gathering
│   │   ├── investigator_agent.py    # AI verdict reasoning
│   │   ├── scout_agent.py           # Financial watchdog
│   │   ├── trending_agent.py        # Content intelligence
│   │   ├── brandshield_agent.py     # Brand reputation scanner
│   │   └── personal_agent.py        # Individual reputation monitor
│   ├── services/
│   │   ├── dashboard_loader.py      # WELFake dataset + cache
│   │   ├── intelligence.py          # Gemini key rotation + sentiment
│   │   ├── rss_ingestion.py         # Background RSS loop (15min)
│   │   ├── alerts.py                # Critical threat alerting
│   │   └── notifier.py              # WhatsApp/SMS via Twilio
│   ├── workers/
│   │   └── claim_worker.py          # Async claim processing pipeline
│   ├── db/
│   │   └── database.py              # Supabase client
│   ├── schemas/
│   │   └── claim_schemas.py         # Pydantic models
│   └── data/
│       └── WELFake_Dataset.xlsx     # 72k labeled news claims
└── frontend/
    ├── index.html                   # Landing page
    ├── dashboard.html               # Live claims feed
    ├── submit.html                  # Claim submission
    ├── agents.html                  # Agent overview
    ├── scout-agent.html             # Financial Watchdog
    ├── trending-agent.html          # Content Intelligence
    ├── brandshield-agent.html       # Brand Scanner
    ├── personal-watch-agent.html    # Reputation Monitor
    ├── about.html                   # Architecture details
    ├── changelog.html               # Version history
    ├── status.html                  # System health
    ├── aegis-theme.css              # Shared design system
    ├── aegis-nav.js                 # Shared navbar + cursor
    ├── dashboard.js                 # Dashboard live feed logic
    └── gemini-client.js             # Netlify proxy client (Scout/Trending)
```

---

## 🚢 Deployment

### Render (Backend)

The `render.yaml` is pre-configured. Connect your GitHub repo on [render.com](https://render.com), set environment variables, and deploy.

```yaml
# render.yaml
services:
  - type: web
    name: aegis-backend
    env: python
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Netlify (Frontend Proxy)

The `netlify.toml` + `frontend/netlify/functions/gemini.js` provide a secure Gemini proxy for the Scout and Trending agent pages. Set `GEMINI_API_KEY` in Netlify environment variables.

---

## 📊 Changelog

See [frontend/changelog.html](frontend/changelog.html) or the full [version history](ENDPOINTS_MAP.md).

| Version | Date | Highlights |
|---|---|---|
| **v3.0.0** | Sep 2026 | BrandShield backend agent, wired Personal Watch, fixed duplicate routes, codebase cleanup |
| **v2.0.0** | Late 2025 | Built-in RSS ingestion, Supabase-first dashboard, mobile overhaul |
| **v1.0.0** | 2025 | Hackathon launch — Scout + Trending agents, WELFake dashboard |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ and multi-agent AI

**[Aegis Protocol](https://github.com/Shaunakrane914/Misinformation)** · Shaunak Rane

</div>
