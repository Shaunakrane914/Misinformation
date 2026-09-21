# Aegis Intelligence System Architecture

Aegis is an enterprise-grade autonomous intelligence system engineered to detect, deconstruct, and neutralize high-velocity digital misinformation, viral market manipulation, and coordinated narrative attacks.

```
                            ┌──────────────────────────────────────┐
                            │        Client Applications           │
                            │ (Submit UI / Dashboards / Command)   │
                            └──────────────────┬───────────────────┘
                                               │ HTTP / REST
                                               ▼
                            ┌──────────────────────────────────────┐
                            │          FastAPI Gateway             │
                            │      (Routers, CORS, Auth, Pydantic) │
                            └──────────────────┬───────────────────┘
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐
               ▼                                                               ▼
 ┌───────────────────────────┐                                   ┌───────────────────────────┐
 │   Autonomous Agent Fleet  │                                   │ Omni-Channel Scraper Hub  │
 ├───────────────────────────┤                                   ├───────────────────────────┤
 │ 1. Coordinator (Consensus)│                                   │ • Reddit Pushshift/JSON   │
 │ 2. Scout (Financial/Ticker)│◄─────────────────────────────────┤ • Twitter/X Guest/Nitter  │
 │ 3. TrendPulse (Virality)  │         Telemetry & Ingestion     │ • YouTube Transcript/Meta │
 │ 4. BrandShield (Reputation│                                   │ • RSS News Realtime Wires │
 │ 5. PersonalWatch (VIP/Def)│                                   └───────────────────────────┘
 │ 6. Research (Fact/Evidence│
 │ 7. Adversary (Attribution)│
 └─────────────┬─────────────┘
               │
               ▼
 ┌───────────────────────────────────────────────────────────┐
 │               Verification & Synthesis Engine             │
 ├───────────────────────────────────────────────────────────┤
 │ • Byzantine Fault Tolerant Consensus Weighting            │
 │ • Multi-Tier Evidence Cross-Referencing & Scoring         │
 │ • Defensive Rebuttal & Counter-Narrative Package Gen      │
 └───────────────────────────────────────────────────────────┘
```

## Core Subsystems

### 1. Autonomous Agent Fleet
Each agent operates with domain-specialized semantic extractors, specialized heuristics, and dynamic threat scoring:
- **Coordinator Agent**: Orchestrates multi-agent debate, resolves divergent verdicts via weighted consensus, and compiles the Truth Dossier.
- **Scout Agent**: Specializes in financial misinformation, pump-and-dump detection, synthetic volatility, and market sentiment divergence.
- **Trending Agent**: Analyzes transmission velocity, memetic resonance, bot swarm amplification, and cross-platform spread patterns.
- **BrandShield Agent**: Defends corporate reputation against targeted smears, product disinformation, and brand disparagement campaigns.
- **Personal Watch Agent**: Guards public figures, executives, and VIPs against synthetic media, voice clones, deepfakes, and character defamation.
- **Research Agent**: Scours academic, scientific, and authoritative primary archives to supply empirical evidence citations.
- **Adversarial Agent**: Simulates coordinated attack vectors, reverse-engineers adversary strategies, and performs campaign attribution.

### 2. Agent Reach Internet Evidence-Acquisition Layer
Aegis v3.5.1+ establishes Agent Reach as the central internet evidence-acquisition capability layer:
```
                      CLAIM
                        │
                        ▼
               Claim Understanding
                        │
                        ▼
            ┌───────────────────────┐
            │   RetrievalPlanner    │
            │ (Domain Query Craft)  │
            └───────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   AgentReachService   │
            │ (Capability Registry) │
            └───────────┬───────────┘
                        │ Bounded Concurrency / Timeouts
       ┌────────────────┼────────────────┬────────────────┐
       ▼                ▼                ▼                ▼
 ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
 │   News    │    │  Reddit   │    │ Twitter/X │    │  GitHub   │
 │   & RSS   │    │ (Threads) │    │(Cashtags) │    │  (Repos)  │
 └─────┬─────┘    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
       │                │                │                │
       └────────────────┼────────────────┴────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   Evidence Normalizer │
            │ & Deduplication Engine│
            └───────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Source Independence  │
            │ (Syndication Cluster) │
            └───────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   ResearchAgent &     │
            │   InvestigatorAgent   │
            └───────────┬───────────┘
                        │
                        ▼
                 TRUTH DOSSIER
```

- **Capability Registry**: Tracks 14 channels (7 core zero-config channels: `reddit`, `twitter`, `youtube`, `news`, `jina_reader`, `github`, `rss`; 7 optional authenticated channels: `linkedin`, `bilibili`, `xueqiu`, `xiaohongshu`, `instagram`, `facebook`, `v2ex`).
- **Domain Query Planner**: Automatically crafts domain-specific queries across `fact_check`, `financial`, `brand`, `personal`, `trending`, `technical`, and `general`.
- **Syndication Clustering & Independence**: Clustered detection of wire syndication (Reuters, AP, Bloomberg, PR Newswire) ensures 4 derivative republished articles are counted as 1 underlying report, preventing false confirmation inflation.
- **SSRF Defense**: Strict pre-fetch validation blocking private RFC 1918, loopback, and cloud metadata (AWS/GCP) endpoints.
- **Source Role Attribution**: Classifies evidence into `PRIMARY`, `SECONDARY`, `COMMUNITY`, and `DIRECT_MEDIA` tiers.

### 3. Truth Dossier Verification Protocol
1. **Ingestion & Normalization**: Incoming claims are tokenized and key entity vectors extracted.
2. **Domain-Planned Retrieval**: `AgentReachService` executes concurrent queries across healthy channels with strict timeout budgets.
3. **Deduplication & Syndication Clustering**: Duplicate URLs and syndicated stories are normalized and grouped.
4. **Multi-Agent Evaluation**: Independent agent scoring across risk, virality, evidence quality, and attribution.
5. **Bayesian Consensus**: Weighted consensus resolution yielding confidence score, veracity verdict, and actionable mitigation measures.

