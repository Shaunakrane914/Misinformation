# Changelog

All notable changes to the Aegis Protocol multi-agent intelligence platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
