# Changelog

All notable changes to the Aegis Protocol multi-agent intelligence platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.6.1] - 2026-09-22

### Added
- **Trending Agent 2.0 Discovery & Intelligence Engine**: Rebuilt from headline aggregator into an investigative trend engine answering what, why, when, and where a trend started with velocity tracking and syndication clustering.
- **BrandShield 2.0 Brand Protection & Threat Intelligence**: Structured threat taxonomy (Counterfeits, Scams, Review Bombing, Impersonation) with verified threat dossiers and truthful telemetry.
- **Personal Watch 2.0 VIP Intelligence Sentinel**: Autonomous VIP protection with deepfake/synthetic media labeling, alert deduplication, and cooldowns.
- **Human-Centered 3-Tier Progressive Disclosure**: Universal presentation layer across all 7 agents displaying primary answers first, supporting evidence second, and technical telemetry in collapsibles.
- **Expanded 99-Test Passing Milestone**: Expanded automated pytest test suite to 99 verified passing unit, integration, and security tests with 100% clean Flake8 code linting.
- **WCAG 2.2 Accessibility Hardening**: Added focus-visible rings, reduced motion detection, and screen-reader utility classes across stylesheets.

---

## [3.6.0] - 2026-09-21

### Added
- **Central Agent Reach Capability Layer (`backend/services/agent_reach/`)**: Upgraded Aegis from ad-hoc scraping to a unified capability and evidence-acquisition layer featuring `CapabilityRegistry`, `RetrievalPlanner`, and `AgentReachService`.
- **14-Channel Capability Registry**: Tracks status (`AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, `AUTH_REQUIRED`) across 7 zero-config core channels (`reddit`, `twitter`, `youtube`, `news`, `jina_reader`, `github`, `rss`) and 7 optional authenticated channels (`linkedin`, `bilibili`, `xueqiu`, `xiaohongshu`, `instagram`, `facebook`, `v2ex`).
- **Domain-Adaptive Retrieval Planner**: Automatically crafts domain-tailored queries and channel priority rankings across 7 domains (`fact_check`, `financial`, `brand`, `personal`, `trending`, `technical`, `general`).
- **Technical Claim Domain & GitHub Channel**: Added GitHub repository, release, and CVE search integration for verifying software vulnerabilities, open-source packages, and code provenance.
- **Evidence Deduplication & Syndication Clustering**: Layered URL normalization and text clustering detect wire-service syndication (Reuters, AP, Bloomberg, PR Newswire) to prevent derivative republished articles from inflating independent confirmation counts.
- **Forensic Source Role & Tier Attribution**: Classifies evidence fragments into structured roles (`PRIMARY`, `SECONDARY`, `COMMUNITY`, `DIRECT_MEDIA`, `DISCOVERY`) and tiers (`TIER_1_ORIGINAL_DOCUMENT`, `TIER_2_REPORTED_PRESS`, etc.).
- **New API Endpoints**:
  - `GET /api/agent-reach/capabilities` — Channel inventory, status, and supported domains.
  - `GET /api/agent-reach/health` — Probe-based health diagnostic report across all 14 channels.
  - Enhanced `POST /api/agent-reach/omni-scan` — Exposes domain retrieval plans, source independence groupings, and channel health.
  - Enhanced `POST /api/agent-reach/read` — Pre-fetch SSRF-validated web extraction.
- **Comprehensive Test Suite**: Added 21 new unit and integration tests (`test_capability_registry.py`, `test_agent_reach_service.py`, `test_agent_reach_api.py`), bringing the verified passing test suite to 47 tests.

### Changed
- **Agent Fleet Migration**: Migrated `ResearchAgent`, `ScoutAgent`, `TrendingAgent`, `BrandShieldAgent`, and `PersonalWatchAgent` to use `agent_reach_service`.
- **Scraper Deprecation with Zero-Breakage Compatibility**: Marked `AgentReachScraper` as deprecated with clean backward-compatibility delegators (`omni_scan`, `unified_scan`, `doctor`) ensuring all existing callers and endpoints operate without disruption.

---

## [3.5.1] - 2026-09-20


### Added
- **20-Second Cinematic Launch Video**: Integrated [`latent-spaces/brag`](https://github.com/latent-spaces/brag) agent skill and [Hyperframes](https://hyperframes.heygen.com/) motion engine to produce an official launch teaser with synchronized electronic music, UI sound effects, and 4-scene narrative arc.
- **Interactive In-Browser Player Controls**: Added playback scrubber, auto-audio synchronization, and pause/resume controls to `brag-output/composition/index.html`.
- **Omni-Channel Social Launch Copy**: Created ready-to-publish launch copy tailored for 𝕏 / Twitter, LinkedIn, and Discord / Reddit in `brag-output/share-copy.md`.
- **Centralized Application Config (`backend/config.py`)**: Added type-safe dataclass-based settings with environment introspection for Gemini, Supabase, and Apify credentials.

---

## [3.5.0] - 2026-09-18

### Added
- **Synchronous Truth Dossier Verification (`/api/claims/verify`)**: Direct, synchronous generation of multi-agent verification dossiers with claim hash, verdict (`TRUE`, `FALSE`, `MISLEADING`), confidence scores, and dual-column refuting/supporting evidence tables.
- **Dedicated 7-Agent Cards UI (`frontend/agents.html`)**: Complete ergonomic redesign replacing congested multi-column grids with spacious standalone agent command cards, live telemetry pills, and direct in-card scan dispatchers.
- **Omni-Channel Social Radar (`frontend/submit.html`)**: Live multi-source social radar feed displaying actual scraped claims and discussions from Reddit, Twitter/X, YouTube, and Global News wires.
- **FastAPI OpenAPI & Swagger UI Matrix**: Enriched OpenAPI tags, parameter models, request schemas, and comprehensive documentation accessible at `/docs` and `/redoc`.
- **Domain-Specialized Scraping Fabric**: Upgraded `AgentReachScraper` with customized domain routing (`financial`, `brand`, `personal`, `trending`, `general`).

### Fixed
- **Removed 3D Card Tilt Wobble**: Eliminated perspective distortion and mousemove jitter from card elements across `aegis-nav.js` and `aegis-theme.css`.
- **Resilient Fallback Import System**: Added dual-try package import fallbacks for root, package, and script execution contexts across all 7 agents.

---

## [3.2.0] - 2026-09-17

### Added
- **Threat Intelligence Lab Instruments**: Mathematical physics simulators including Mandelbrot token rank-frequency regression, Hawkes self-exciting point processes, and Byzantine fault-tolerant swarm consensus.
- **Interactive Protocol Pipeline Simulator (`frontend/about.html`)**: Interactive step-by-step verification lifecycle walkthrough replacing static card grids.
- **Dense Telemetry Strips (`frontend/dashboard.html`)**: Replaced generic stat cards with continuous telemetry ribbons and real-time event logs.

---

## [3.0.0] - 2026-09-16

### Added
- **Multi-Agent Swarm Orchestration**: Integrated Coordinator, Scout, Trending, BrandShield, and Personal Watch agents into coordinated pipeline.
- **Supabase Cloud Database Layer**: Schema migrations and tables for claims, evidence, signals, and verified threat feeds.
- **Gemini 2.5 Flash Integration**: Multi-key rotation and epistemic reasoning for stance detection and contradiction classification.
