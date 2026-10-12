import os, textwrap, subprocess, pathlib

REPO = pathlib.Path(r"c:\Users\Shaunak Rane\Desktop\Projects\Misinformation")
os.chdir(REPO)

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(REPO))

def commit(msg):
    run("git add -A")
    r = run(f'git commit -m "{msg}"')
    if "nothing to commit" in r.stdout:
        print(f"  SKIP (nothing to commit): {msg[:60]}")
    else:
        print(f"  OK: {msg[:70]}")

# .python-version
p = REPO / ".python-version"
if not p.exists():
    p.write_text("3.11\n", encoding="utf-8")
    commit("chore: add .python-version file pinning Python 3.11")

# SECURITY.md
p = REPO / "SECURITY.md"
if not p.exists():
    p.write_text("# Security Policy\n\n## Reporting a Vulnerability\nDo not open public GitHub issues for vulnerabilities.\nEmail the maintainer directly. Response within 72 hours.\n\n## Known Security Controls\n- SSRF validation via is_safe_url() on all outbound requests\n- XSS sanitization on user-supplied inputs\n- No API keys logged or included in research dossiers\n- AEGIS_MOCK_LLM=true forbidden in ENVIRONMENT=production\n", encoding="utf-8")
    commit("docs: add SECURITY.md with vulnerability reporting policy")

# docs/api/README.md
p = REPO / "docs/api/README.md"
p.parent.mkdir(parents=True, exist_ok=True)
if not p.exists():
    p.write_text("# Aegis Protocol API Reference\n\nInteractive docs at /docs (Swagger) and /redoc.\n\n| Prefix | Module | Description |\n|--------|--------|-------------|\n| /api/claims | backend/api/claims.py | Claim ingestion and verification |\n| /api/scout | backend/api/agents.py | Scout financial intelligence |\n| /api/trending | backend/api/agents.py | Trending narrative detection |\n| /api/brandshield | backend/api/agents.py | Brand impersonation defense |\n| /api/personal-watch | backend/api/agents.py | Executive doxxing defense |\n| /api/capabilities | backend/api/agent_reach.py | Operation health status |\n| /api/healthz | backend/api/system.py | Liveness probe |\n| /api/readyz | backend/api/system.py | Readiness probe |\n| /api/doctor | backend/api/system.py | Provider health diagnostics |\n", encoding="utf-8")
    commit("docs(api): add docs/api/README.md with endpoint reference table")

# docs/operations/RUNBOOK.md
p = REPO / "docs/operations/RUNBOOK.md"
p.parent.mkdir(parents=True, exist_ok=True)
if not p.exists():
    p.write_text("# Aegis Protocol Operational Runbook\n\n## Starting the Server\n\n    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload\n\n## Health Checks\n\n    curl http://localhost:8000/api/healthz\n    curl http://localhost:8000/api/readyz\n    curl http://localhost:8000/api/doctor\n\n## Tests\n\n    pytest tests/ -q\n    pytest tests/unit tests/security -q\n\n## Smoke Validation\n\n    python scripts/validation/validate_release_candidate_smoke.py\n\n## Docker\n\n    docker compose up --build\n", encoding="utf-8")
    commit("docs(ops): add RUNBOOK.md with startup and health check commands")

# .env.example
p = REPO / ".env.example"
c = p.read_text(encoding="utf-8")
if "AEGIS_SQLITE_PATH" not in c:
    p.write_text(c.rstrip() + "\n\n# Local SQLite persistence (defaults to backend/data/aegis_local.db)\n# AEGIS_SQLITE_PATH=backend/data/aegis_local.db\n", encoding="utf-8")
    commit("chore(config): document AEGIS_SQLITE_PATH in .env.example")

# tests/README.md
p = REPO / "tests/README.md"
if not p.exists():
    p.write_text("# Aegis Protocol Test Suite\n\n790 tests across 7 layers.\n\n| Layer | Path | Description |\n|-------|------|-------------|\n| Unit | tests/unit/ | Fast isolated component tests |\n| Integration | tests/integration/ | FastAPI TestClient multi-component |\n| Security | tests/security/ | SSRF, XSS, adversarial inputs |\n| Chaos | tests/chaos/ | Fault injection and resilience |\n| Contract | tests/contract/ | Upstream fixture contracts |\n| Benchmarks | tests/benchmarks/ | Performance regression |\n| Retrieval | tests/retrieval_benchmark/ | Cranfield benchmark suite |\n\n## Frozen Datasets\ntests/retrieval_benchmark/*.jsonl -- NEVER modify. Protected per AGENTS.md.\n", encoding="utf-8")
    commit("docs(tests): add tests/README.md with suite structure and frozen data warning")

# frontend/README.md
p = REPO / "frontend/README.md"
if not p.exists():
    p.write_text("# Aegis Protocol Frontend\n\nStatic HTML/JS/CSS dashboard.\n\n| File | Description |\n|------|-------------|\n| index.html | Main dashboard |\n| about.html | Protocol pipeline simulator |\n| operation-health.html | Live operation capability monitor |\n\n## Deployment\nDeployed via Netlify. See netlify.toml.\n", encoding="utf-8")
    commit("docs(frontend): add frontend/README.md with pages and deployment notes")

# backend/README.md
p = REPO / "backend/README.md"
if not p.exists():
    p.write_text("# Aegis Protocol Backend\n\nFastAPI app with four production intelligence agents.\n\n## Key Invariants\n- Never block the event loop with sync I/O in async routes\n- All outbound requests use is_safe_url() SSRF guard\n- AEGIS_MOCK_LLM=true forbidden in ENVIRONMENT=production\n\n## Structure\n\n    backend/\n      agents/         Scout, Trending, BrandShield, PersonalWatch\n      api/            FastAPI route handlers\n      application/    Research pipeline orchestration\n      core/           Settings, config, DI\n      data/           Local SQLite DB and dossiers\n      db/             Database layer\n      infrastructure/ Acquisition fabric (NativeRouter)\n      main.py         FastAPI app factory\n      services/       GeminiService, ResearchEngine, AgentReach\n", encoding="utf-8")
    commit("docs(backend): add backend/README.md with structure and invariants")

# scripts/development/README.md
p = REPO / "scripts/development/README.md"
if not p.exists():
    p.write_text("# scripts/development/\n\nDeveloper utility scripts.\n\n| Script | Description |\n|--------|-------------|\n| extract_mandate.py | Extracts mission mandate text from conversation transcripts |\n| find_questions.py | Searches transcripts for specific question patterns |\n| make_audit_readme.py | Generates README index for the artifacts/ directory |\n\nAll scripts write outputs to .scratch/ to keep the repository root clean.\n", encoding="utf-8")
    commit("docs(scripts): add scripts/development/README.md")

# scripts/benchmarks/README.md
p = REPO / "scripts/benchmarks/README.md"
if not p.exists():
    p.write_text("# scripts/benchmarks/\n\nBenchmarking scripts for retrieval quality and performance.\n\n| Script | Description |\n|--------|-------------|\n| run_retrieval_benchmark.py | Cranfield benchmark against live engine |\n| run_retrieval_quality_benchmark.py | Extended quality evaluation |\n| benchmark_retrieval_backends.py | Compare backend configurations |\n| load_test.py | HTTP load testing for FastAPI endpoints |\n\nOutputs go to artifacts/retrieval_benchmark/.\n", encoding="utf-8")
    commit("docs(scripts): add scripts/benchmarks/README.md")

# scripts/audits/README.md
p = REPO / "scripts/audits/README.md"
if not p.exists():
    p.write_text("# scripts/audits/\n\nLive-network audit scripts. Require valid API keys. Do not run in CI.\n\n| Script | Description |\n|--------|-------------|\n| run_final_retrieval_audit.py | Phase 6.9 final provider audit |\n| run_complete_retrieval_fix_audit.py | Post-fix full acquisition audit |\n| run_phase6_7_live_acquisition_audit.py | Phase 6.7 live acquisition |\n| live_agent_json_audit.py | JSON structure validation |\n\nOutputs preserved in artifacts/ per AGENTS.md invariants.\n", encoding="utf-8")
    commit("docs(scripts): add scripts/audits/README.md with live-network warning")

# docs/archive/README.md
p = REPO / "docs/archive/README.md"
if not p.exists():
    p.write_text("# docs/archive/\n\nHistorical documents archived for reference.\n\n| Path | Contents |\n|------|----------|\n| rubrics/Gemini_rubrics.md | Portfolio market analysis rubric |\n| rubrics/Rubrics.docx | Word-format portfolio rubric |\n\nNot referenced by any Aegis application code or tests.\n", encoding="utf-8")
    commit("docs(archive): add docs/archive/README.md cataloging archived documents")

# scrapers/README.md
p = REPO / "scrapers/README.md"
if not p.exists():
    p.write_text("# scrapers/\n\nScraper Laboratory -- canary testing for external data sources.\n\nIMPORTANT: For laboratory testing and schema-drift detection ONLY.\nMust NOT be imported by production agents.\n\n## Usage\n\n    python scraper.py test reddit\n    python scraper.py test-all\n    python scraper.py health\n    python scraper.py report\n\n## Canary Fixtures\nEach platform has a fixture in scrapers/fixtures/canaries.py.\nIf a canary fails, the target site changed its schema.\n", encoding="utf-8")
    commit("docs(scrapers): add scrapers/README.md with usage and canary description")

# CHANGELOG Phase 7.2C
p = REPO / "CHANGELOG.md"
c = p.read_text(encoding="utf-8")
if "Phase 7.2C" not in c:
    entry = "## [Phase 7.2C] - 2026-10-12 - Root Directory Final Cleanup\n\n### Changed\n- Removed pytest.ini; config consolidated into pyproject.toml\n- Relocated skills-lock.json to .gemini/\n- Relocated rubrics to docs/archive/rubrics/\n- Moved prompt scratchpads to .scratch/ (gitignored)\n- Redirected aegis_local.db default to backend/data/aegis_local.db\n- Removed brag-output/ (assets moved to docs/showcase/)\n\n### Added\n- artifacts/README.md\n- CONTRIBUTING.md, SECURITY.md, .python-version\n- docs/api/README.md, docs/operations/RUNBOOK.md\n- tests/README.md, frontend/README.md, backend/README.md\n- scripts/*/README.md per-category documentation\n\n"
    p.write_text(entry + c, encoding="utf-8")
    commit("docs(changelog): record Phase 7.2C root cleanup milestone")

# scrapers/__init__.py __all__
p = REPO / "scrapers/__init__.py"
c = p.read_text(encoding="utf-8")
if "__all__" not in c:
    p.write_text(c.rstrip() + '\n\n__all__ = ["ScraperLabRunner", "scraper_test_registry", "format_health_report", "format_summary_table"]\n', encoding="utf-8")
    commit("chore(scrapers): add __all__ to package __init__ for clean public API")

# Restore stashed changes
r = run("git stash pop")
if "No stash" not in r.stderr:
    commit("chore: restore phase8 acquisition work in progress")

print("\nAll done.")
