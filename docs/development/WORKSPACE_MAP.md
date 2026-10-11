# Aegis Protocol — Developer Workspace Map & Command Reference

**Phase:** 7.2 (Workspace Organization, Repository Hygiene & Safe Structural Consolidation)  
**Author:** Senior Software Architect & Developer Experience Engineer  
**Status:** Authoritative Developer Navigation Reference  

---

## 1. Quick Navigation: Where to Find Everything

This guide provides immediate file and directory locations for common developer and coding-agent tasks.

| Subsystem / Responsibility | Primary Location | Key Files & Modules |
| :--- | :--- | :--- |
| **Agent Logic: Scout** | [`backend/agents/scout/`](../../backend/agents/scout/) | `agent.py`, `models.py`, `scout_agent.py` (facade) |
| **Agent Logic: Trending** | [`backend/agents/trending/`](../../backend/agents/trending/) | `agent.py`, `models.py`, `trending_agent.py` (facade) |
| **Agent Logic: BrandShield** | [`backend/agents/brandshield/`](../../backend/agents/brandshield/) | `agent.py`, `scanning.py`, `models.py`, `brandshield_agent.py` (facade) |
| **Agent Logic: Personal Watch** | [`backend/agents/personal_watch/`](../../backend/agents/personal_watch/) | `agent.py`, `scanning.py`, `models.py`, `personal_agent.py` (facade) |
| **Claim Ingestion & Normalization** | [`backend/agents/claim_ingestion_agent.py`](../../backend/agents/claim_ingestion_agent.py) | Unicode NFC normalization, SHA-256 deduplication |
| **Investigator Agent** | [`backend/agents/investigator_agent.py`](../../backend/agents/investigator_agent.py) | 6-verdict truth taxonomy, multi-perspective synthesis |
| **Coordinator / Fleet Orchestrator** | [`backend/agents/coordinator_agent.py`](../../backend/agents/coordinator_agent.py) | Cross-agent task distribution, unified report compilation |
| **API Routers & Endpoints** | [`backend/api/`](../../backend/api/) | `claims.py`, `scout.py`, `trending.py`, `brandshield.py`, `personal_watch.py`, `agent_reach.py`, `healthz.py`, `replay.py` |
| **Main Application Entrypoint** | [`backend/main.py`](../../backend/main.py) | FastAPI app instance, CORS middleware, static asset mounting |
| **Native Acquisition Router** | [`backend/infrastructure/acquisition/routing/router.py`](../../backend/infrastructure/acquisition/routing/router.py) | `NativeRouter` — routes 16 recovered operations + Reddit/X |
| **Centralized LLM Gateway** | [`backend/infrastructure/llm/gateway.py`](../../backend/infrastructure/llm/gateway.py) | `CentralizedLLMGateway` — multi-model failover, mock guard |
| **Claim-Aware Source Planner** | [`backend/services/agent_reach/source_planner.py`](../../backend/services/agent_reach/source_planner.py) | `SourcePlanningEngine` — bounded source planning |
| **Runtime Capability Health** | [`backend/services/agent_reach/native/registry.py`](../../backend/services/agent_reach/native/registry.py) | `RuntimeOperationCapabilities` — health, cooldown, auth |
| **Entity & Identity Resolution** | [`backend/services/research/entity_resolver.py`](../../backend/services/research/entity_resolver.py) | Disambiguation of brands, VIPs, and corporate handles |
| **Frontend Consoles & UI** | [`frontend/`](../../frontend/) | `index.html`, `scout-agent.html`, `trending-agent.html`, `brandshield-agent.html`, `personal-watch-agent.html` |
| **Frontend Health Client** | [`frontend/operation-health.js`](../../frontend/operation-health.js) | TTL-bounded (45s) capability caching & visibility revalidation |
| **Design Tokens & Styles** | [`frontend/aegis-theme.css`](../../frontend/aegis-theme.css) | Color palette, typography, responsive layouts, badges |
| **Automated Tests (790 tests)** | [`tests/`](../../tests/) | `unit/`, `integration/`, `contract/`, `security/`, `chaos/`, `benchmarks/`, `evaluation/`, `frontend/` |
| **Frozen Benchmark Datasets** | [`tests/retrieval_benchmark/`](../../tests/retrieval_benchmark/) | `scenarios.jsonl`, `candidates.jsonl`, `labels.jsonl` (IMMUTABLE) |
| **Forensic Dossier Archive** | [`backend/data/dossiers/`](../../backend/data/dossiers/) | 2,359 historical investigation dossiers (PROTECTED) |
| **Empirical Audit Evidence** | [`artifacts/`](../../artifacts/) | Historical audit records, benchmark metrics, JSON summaries |
| **Development & Audit Scripts** | [`scripts/`](../../scripts/) | Release validation, benchmark harnesses, evaluation CLIs |
| **Project Showcase & Film** | [`docs/showcase/`](../showcase/) | Launch film composition, storyboard brief, social copy |
| **Standalone Scraper Lab** | [`scrapers/`](../../scrapers/) & [`scraper.py`](../../scraper.py) | Laboratory canary checks & schema drift monitoring |
| **Documentation Portal** | [`docs/`](../) | `index.md`, `architecture/`, `operations/`, `testing/`, `security/` |


---

## 2. Verified Common Commands

All commands below are tested and verified against the repository configuration:

### 2.1. Environment Setup & Installation
```bash
# 1. Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.2. Running the Application Server
```bash
# Recommended root development launcher (finds an open port 8000/8001/8080/5050):
python main.py

# Or directly with Uvicorn:
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
- Web Application: [http://localhost:8000](http://localhost:8000)
- OpenAPI Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- System Health Endpoint: [http://localhost:8000/api/healthz](http://localhost:8000/api/healthz)

### 2.3. Running Automated Tests
```bash
# Run the complete offline regression test gate (787 tests):
pytest tests/ -q

# Run fast unit, chaos, and security tests (591 tests, ~90 seconds):
pytest tests/unit tests/chaos tests/security -q

# Run API contract and integration tests:
pytest tests/contract tests/integration -q

# Run pure Node.js frontend operation-health tests:
node tests/frontend/test_operation_health.js
```

### 2.4. Code Quality & Linting
```bash
# Check for fatal syntax and undefined names:
flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics

# Standard codebase linting:
flake8 backend tests scripts --max-line-length=120 --statistics
```

### 2.5. Scientific Benchmarks & Evaluation
```bash
# Run all offline ML benchmarks (WELFake classical ML + Learned Reranker):
python scripts/evaluate_dataset.py --mode all_offline --seed 42

# Run Cranfield retrieval quality benchmark on frozen fixtures:
python scripts/benchmarks/run_retrieval_benchmark.py

# Run 4-agent quality evaluation harness:
python scripts/evaluate_all_agents.py
```

### 2.6. Release Candidate Validation & Rollback
```bash
# Run Phase 7.1 isolated staging-like smoke validation (11 gates):
python scripts/validate_release_candidate_smoke.py

# Validate database and dossier rollback compatibility:
python scripts/validate_rollback_compatibility.py
```

### 2.7. Scraper Laboratory Canaries & Health
```bash
# Display scraper health summary table (offline fixture mode):
python scraper.py health --offline

# Run canary tests across all supported websites (offline mode):
python scraper.py test-all --offline
```
