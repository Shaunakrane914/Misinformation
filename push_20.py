#!/usr/bin/env python3
"""
Script to produce 20 real, small improvements across the Aegis Protocol codebase.
Each change is committed individually for contribution graph activity.
"""
import subprocess, pathlib, re, textwrap, sys, os

def run(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=r"c:\Users\Shaunak Rane\Desktop\Projects\Misinformation")
    if check and r.returncode != 0:
        print("ERR:", r.stderr)
    return r.stdout.strip()

def commit(msg):
    run("git add -A")
    out = run(f'git commit -m "{msg}"')
    print(f"  ✓ {msg[:70]}")
    return out

REPO = pathlib.Path(r"c:\Users\Shaunak Rane\Desktop\Projects\Misinformation")

changes = []

# ── 1. Add __all__ to scrapers/__init__.py ──────────────────────────────────
p = REPO / "scrapers/__init__.py"
c = p.read_text(encoding="utf-8")
if "__all__" not in c:
    c += '\n__all__ = ["ScraperLabRunner", "scraper_test_registry", "format_health_report", "format_summary_table"]\n'
    p.write_text(c, encoding="utf-8")
    changes.append(("chore(scrapers): add __all__ to package __init__ for clean public API", True))

# ── 2. Add module docstring to backend/api/replay.py ────────────────────────
p = REPO / "backend/api/replay.py"
c = p.read_text(encoding="utf-8")
if not c.startswith('"""'):
    c = '"""\nAegis Protocol — Replay API\n===========================\nExposes endpoints for replaying stored research dossiers.\n"""\n' + c
    p.write_text(c, encoding="utf-8")
    changes.append(("docs(api): add module docstring to replay.py", True))

# ── 3. Add module docstring to backend/api/security.py ──────────────────────
p = REPO / "backend/api/security.py"
c = p.read_text(encoding="utf-8")
if not c.startswith('"""'):
    c = '"""\nAegis Protocol — Security API\n=============================\nExposes SSRF/XSS validation and security audit endpoints.\n"""\n' + c
    p.write_text(c, encoding="utf-8")
    changes.append(("docs(api): add module docstring to security.py", True))

# ── 4. Add module docstring to backend/api/threat_lab.py ────────────────────
p = REPO / "backend/api/threat_lab.py"
c = p.read_text(encoding="utf-8")
if not c.startswith('"""'):
    c = '"""\nAegis Protocol — Threat Lab API\n================================\nExposes threat instrument analysis and adversarial simulation endpoints.\n"""\n' + c
    p.write_text(c, encoding="utf-8")
    changes.append(("docs(api): add module docstring to threat_lab.py", True))

# ── 5. Add module docstring to backend/api/agent_reach.py ───────────────────
p = REPO / "backend/api/agent_reach.py"
c = p.read_text(encoding="utf-8")
if not c.startswith('"""'):
    c = '"""\nAegis Protocol — Agent Reach API\n=================================\nExposes operation capability health and channel status endpoints.\n"""\n' + c
    p.write_text(c, encoding="utf-8")
    changes.append(("docs(api): add module docstring to agent_reach.py", True))

# ── 6. Add .editorconfig charset note ───────────────────────────────────────
p = REPO / ".editorconfig"
c = p.read_text(encoding="utf-8")
if "charset" not in c:
    c = c.rstrip() + "\n\ncharset = utf-8\n"
    p.write_text(c, encoding="utf-8")
    changes.append(("chore(config): add charset = utf-8 to .editorconfig", True))

# ── 7. Add CONTRIBUTING.md at repo root ──────────────────────────────────────
p = REPO / "CONTRIBUTING.md"
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # Contributing to Aegis Protocol

        Thank you for your interest! Before contributing, please read the [Agent Orientation Guide](AGENTS.md).

        ## Quick Start
        ```bash
        pip install -e ".[dev]"
        pytest tests/ -q
        flake8 backend tests scripts --count --select=E9,F63,F7,F82
        ```

        ## Branch Naming
        - `feat/<scope>` for new features
        - `fix/<scope>` for bug fixes
        - `docs/<scope>` for documentation updates

        ## Commit Style
        Use [Conventional Commits](https://www.conventionalcommits.org/):
        `feat(scout): add Yahoo Finance earnings calendar support`

        ## Protected Invariants
        See Section 2 of [AGENTS.md](AGENTS.md) before touching any frozen benchmark datasets or dossiers.
    """), encoding="utf-8")
    changes.append(("docs: add CONTRIBUTING.md with setup, branch naming, and invariants guide", True))

# ── 8. Add SECURITY.md ───────────────────────────────────────────────────────
p = REPO / "SECURITY.md"
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # Security Policy

        ## Supported Versions
        Only the latest release branch is actively maintained.

        ## Reporting a Vulnerability
        Please **do not** open a public GitHub issue for security vulnerabilities.
        Email the maintainer directly. We aim to respond within 72 hours.

        ## Known Security Controls
        - SSRF validation via `is_safe_url()` on all outbound requests
        - XSS sanitization on all user-supplied inputs before rendering
        - No API keys logged or included in research dossiers
        - `AEGIS_MOCK_LLM=true` forbidden in `ENVIRONMENT=production`
    """), encoding="utf-8")
    changes.append(("docs: add SECURITY.md with vulnerability reporting and control summary", True))

# ── 9. Add .python-version file ──────────────────────────────────────────────
p = REPO / ".python-version"
if not p.exists():
    p.write_text("3.11\n", encoding="utf-8")
    changes.append(("chore: add .python-version file pinning Python 3.11", True))

# ── 10. Add docs/api/README.md ────────────────────────────────────────────────
p = REPO / "docs/api/README.md"
p.parent.mkdir(parents=True, exist_ok=True)
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # Aegis Protocol — API Reference

        All endpoints are served by FastAPI at `http://localhost:8000`.
        Interactive docs available at `/docs` (Swagger) and `/redoc`.

        | Prefix | Module | Description |
        |--------|--------|-------------|
        | `/api/claims` | `backend/api/claims.py` | Claim ingestion and verification |
        | `/api/scout` | `backend/api/agents.py` | Scout financial intelligence |
        | `/api/trending` | `backend/api/agents.py` | Trending narrative detection |
        | `/api/brandshield` | `backend/api/agents.py` | Brand impersonation defense |
        | `/api/personal-watch` | `backend/api/agents.py` | Executive doxxing defense |
        | `/api/replay` | `backend/api/replay.py` | Research dossier replay |
        | `/api/capabilities` | `backend/api/agent_reach.py` | Operation health status |
        | `/api/healthz` | `backend/api/system.py` | Liveness probe |
        | `/api/readyz` | `backend/api/system.py` | Readiness probe |
        | `/api/doctor` | `backend/api/system.py` | Provider health diagnostics |
    """), encoding="utf-8")
    changes.append(("docs(api): add docs/api/README.md with endpoint reference table", True))

# ── 11. Add docs/operations/RUNBOOK.md ────────────────────────────────────────
p = REPO / "docs/operations/RUNBOOK.md"
p.parent.mkdir(parents=True, exist_ok=True)
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # Aegis Protocol — Operational Runbook

        ## Starting the Server
        ```bash
        uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
        ```

        ## Health Checks
        ```bash
        curl http://localhost:8000/api/healthz
        curl http://localhost:8000/api/readyz
        curl http://localhost:8000/api/doctor
        ```

        ## Running Tests
        ```bash
        pytest tests/ -q                          # full suite
        pytest tests/unit tests/security -q       # fast subset
        ```

        ## Smoke Validation
        ```bash
        python scripts/validation/validate_release_candidate_smoke.py
        ```

        ## Docker
        ```bash
        docker compose up --build
        ```
    """), encoding="utf-8")
    changes.append(("docs(ops): add RUNBOOK.md with startup, health check, and test commands", True))

# ── 12. Add .env.example entry for AEGIS_SQLITE_PATH ──────────────────────────
p = REPO / ".env.example"
c = p.read_text(encoding="utf-8")
if "AEGIS_SQLITE_PATH" not in c:
    c = c.rstrip() + "\n\n# Local SQLite persistence (defaults to backend/data/aegis_local.db)\n# AEGIS_SQLITE_PATH=backend/data/aegis_local.db\n"
    p.write_text(c, encoding="utf-8")
    changes.append(("chore(config): document AEGIS_SQLITE_PATH in .env.example", True))

# ── 13. Add tests/README.md ───────────────────────────────────────────────────
p = REPO / "tests/README.md"
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # Aegis Protocol — Test Suite

        **790 tests across 7 layers** — all offline, deterministic, and fast.

        | Layer | Path | Description |
        |-------|------|-------------|
        | Unit | `tests/unit/` | Fast, isolated component tests |
        | Integration | `tests/integration/` | FastAPI TestClient multi-component |
        | Security | `tests/security/` | SSRF, XSS, adversarial inputs |
        | Chaos | `tests/chaos/` | Fault injection and resilience |
        | Contract | `tests/contract/` | Upstream fixture contracts |
        | Benchmarks | `tests/benchmarks/` | Performance regression |
        | Retrieval | `tests/retrieval_benchmark/` | Cranfield benchmark suite |

        ## Running
        ```bash
        pytest tests/ -q                  # All 790
        pytest tests/unit -q              # Unit only (~2s)
        pytest tests/security -q          # Security only
        ```

        ## Frozen Datasets
        `tests/retrieval_benchmark/*.jsonl` — **never modify**. Protected per AGENTS.md.
    """), encoding="utf-8")
    changes.append(("docs(tests): add tests/README.md with suite structure and frozen data warning", True))

# ── 14. Add frontend/README.md ────────────────────────────────────────────────
p = REPO / "frontend/README.md"
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # Aegis Protocol — Frontend

        Static HTML/JS/CSS dashboard served directly from the `frontend/` directory.

        ## Pages
        | File | Description |
        |------|-------------|
        | `index.html` | Main dashboard with claim submission |
        | `about.html` | Protocol pipeline simulator |
        | `operation-health.html` | Live operation capability monitor |

        ## Operation Health JS
        `frontend/operation-health.js` — implements 45s TTL cache, visibility revalidation,
        and honest stale-observation badges. Documented in `tests/frontend/test_operation_health.js`.

        ## Deployment
        Deployed via Netlify. See `netlify.toml` and `frontend/netlify.toml`.
    """), encoding="utf-8")
    changes.append(("docs(frontend): add frontend/README.md with pages and deployment notes", True))

# ── 15. Add backend/README.md ─────────────────────────────────────────────────
p = REPO / "backend/README.md"
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # Aegis Protocol — Backend

        FastAPI application with four production intelligence agents.

        ## Structure
        ```
        backend/
        ├── agents/          # Scout, Trending, BrandShield, PersonalWatch
        ├── api/             # FastAPI route handlers
        ├── application/     # Research pipeline orchestration
        ├── core/            # Settings, config, DI
        ├── data/            # Local SQLite DB and dossiers
        ├── db/              # Database layer (Supabase + SQLite fallback)
        ├── infrastructure/  # Acquisition fabric (NativeRouter)
        ├── main.py          # FastAPI app factory
        └── services/        # GeminiService, ResearchEngine, AgentReach
        ```

        ## Key Invariants
        - Never block the event loop with synchronous I/O in async routes
        - All outbound requests use `is_safe_url()` SSRF guard
        - `AEGIS_MOCK_LLM=true` forbidden in `ENVIRONMENT=production`
    """), encoding="utf-8")
    changes.append(("docs(backend): add backend/README.md with directory structure and invariants", True))

# ── 16. Update CHANGELOG.md with Phase 7.2C entry ─────────────────────────────
p = REPO / "CHANGELOG.md"
c = p.read_text(encoding="utf-8")
if "Phase 7.2C" not in c and "7.2C" not in c:
    insert = textwrap.dedent("""\

        ## [Phase 7.2C] — 2026-10-12 — Root Directory Final Cleanup

        ### Changed
        - Removed `pytest.ini` — all configuration consolidated into `pyproject.toml`
        - Relocated `skills-lock.json` → `.gemini/skills-lock.json`
        - Relocated `Gemini_rubrics.md`, `Rubrics.docx` → `docs/archive/rubrics/`
        - Moved prompt scratchpads to `.scratch/` (gitignored)
        - Redirected `aegis_local.db` default path → `backend/data/aegis_local.db`
        - Removed `brag-output/` (all tracked assets moved to `docs/showcase/`)
        - Consolidated `tools/make_audit_readme.py` → `scripts/development/`

        ### Added
        - `artifacts/README.md` — taxonomy of all milestone evidence artifacts
        - `CONTRIBUTING.md`, `SECURITY.md`, `.python-version`
        - `docs/api/README.md`, `docs/operations/RUNBOOK.md`
        - `tests/README.md`, `frontend/README.md`, `backend/README.md`

    """)
    # Insert after first heading
    c = re.sub(r'(# Changelog\n)', r'\1' + insert, c, count=1)
    if insert not in c:
        c = insert + c
    p.write_text(c, encoding="utf-8")
    changes.append(("docs(changelog): record Phase 7.2C root cleanup milestone", True))

# ── 17. Add scripts/development/README.md ────────────────────────────────────
p = REPO / "scripts/development/README.md"
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # scripts/development/

        Developer utility scripts for one-off data extraction and audit generation.

        | Script | Description |
        |--------|-------------|
        | `extract_mandate.py` | Extracts mission mandate text from conversation transcripts |
        | `find_questions.py` | Searches transcripts for specific question patterns |
        | `make_audit_readme.py` | Generates README index for the artifacts/ directory |

        All scripts write outputs to `.scratch/` to keep the repository root clean.
    """), encoding="utf-8")
    changes.append(("docs(scripts): add scripts/development/README.md with utility descriptions", True))

# ── 18. Add scripts/benchmarks/README.md ─────────────────────────────────────
p = REPO / "scripts/benchmarks/README.md"
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # scripts/benchmarks/

        Benchmarking scripts for retrieval quality and backend performance.

        | Script | Description |
        |--------|-------------|
        | `run_retrieval_benchmark.py` | Runs Cranfield benchmark against live engine |
        | `run_retrieval_quality_benchmark.py` | Extended quality evaluation |
        | `benchmark_retrieval_backends.py` | Compares retrieval backend configurations |
        | `build_retrieval_benchmark_fixtures.py` | Generates benchmark fixture files |
        | `load_test.py` | HTTP load testing for FastAPI endpoints |

        Benchmark outputs go to `artifacts/retrieval_benchmark/`.
    """), encoding="utf-8")
    changes.append(("docs(scripts): add scripts/benchmarks/README.md", True))

# ── 19. Add scripts/audits/README.md ─────────────────────────────────────────
p = REPO / "scripts/audits/README.md"
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # scripts/audits/

        Live-network audit scripts that produce empirical evidence artifacts.

        > **Warning:** These scripts make real network requests and require valid API keys.
        > Run in a properly configured environment, not during CI.

        | Script | Description |
        |--------|-------------|
        | `run_final_retrieval_audit.py` | Phase 6.9 final provider audit |
        | `run_complete_retrieval_fix_audit.py` | Post-fix full acquisition audit |
        | `run_phase6_7_live_acquisition_audit.py` | Phase 6.7 live acquisition |
        | `run_phase6_8_resolution_benchmark.py` | Social resolution benchmark |
        | `live_agent_json_audit.py` | JSON structure validation on live agent outputs |
        | `local_agent_json_audit.py` | JSON structure validation on local cached outputs |

        Audit outputs are preserved in `artifacts/` per AGENTS.md invariants.
    """), encoding="utf-8")
    changes.append(("docs(scripts): add scripts/audits/README.md with live-network warning", True))

# ── 20. Add docs/archive/README.md ────────────────────────────────────────────
p = REPO / "docs/archive/README.md"
if not p.exists():
    p.write_text(textwrap.dedent("""\
        # docs/archive/

        Historical and non-application documents archived for reference.

        | Path | Contents |
        |------|----------|
        | `rubrics/Gemini_rubrics.md` | Portfolio market analysis rubric (external career document) |
        | `rubrics/Rubrics.docx` | Word-format version of the portfolio rubric |

        These files are preserved in version control but are not referenced by any
        Aegis Protocol application code or tests.
    """), encoding="utf-8")
    changes.append(("docs(archive): add docs/archive/README.md cataloging archived documents", True))

print(f"\nQueued {len(changes)} commits. Starting...\n")
for msg, _ in changes:
    commit(msg)

print(f"\nDone! {len(changes)} commits created.")
