# Aegis Protocol — AI Coding Agent Orientation Guide

**Target Audience:** Autonomous coding assistants (Google Antigravity, OpenAI Codex, Anthropic Claude) and software engineers  
**Repository:** `Shaunakrane914/Misinformation`  
**Current Milestone:** Phase 7.4 (Remediation Verification, Historical Data Recovery Assessment & CI Closeout)
**Historical Phase 7.2 Offline Baseline:** 787 / 787 tests passing
**Current Agent Handoff:** [Start here](docs/handoffs/README.md). Test totals and local validation evidence are dated snapshots, not permanent acceptance counts.

---

## 1. System Architecture at a Glance

Aegis Protocol is an evidence-first misinformation research platform featuring:
- **Four Production Agents**:
  1. `Scout`: Financial anomaly and corporate news intelligence.
  2. `Trending`: Emerging memetic virality and narrative velocity tracking.
  3. `BrandShield`: Corporate brand defense, impersonation, and smear detection.
  4. `Personal Watch`: VIP and executive doxxing and synthetic media defense.
- **Acquisition Fabric**: Centralized `NativeRouter` dispatching across 16 recovered operations + Reddit/X without fragile third-party scrapers.
- **Source Planning**: Claim-aware `SourcePlanningEngine` generating bounded source plans.
- **Runtime Capability Health**: `RuntimeOperationCapabilities` with dynamic status, cooldown, and credential tracking.
- **Frontend Health**: `frontend/operation-health.js` with 45s TTL cache, visibility revalidation, and honest stale-observation badges.
- **Centralized LLM Gateway**: `CentralizedLLMGateway` supporting failover and strict production mock guards (`AEGIS_MOCK_LLM=true` is forbidden when `ENVIRONMENT=production`).

---

## 2. Safe Edit Boundaries & Invariants

### ⛔ Non-Negotiable Invariants (DO NOT TOUCH)
1. **Never delete or modify frozen benchmark datasets**:
   - `tests/retrieval_benchmark/candidates.jsonl`
   - `tests/retrieval_benchmark/labels.jsonl`
   - `tests/retrieval_benchmark/scenarios.jsonl`
2. **Never delete or overwrite historical investigation dossiers**:
   - `backend/data/dossiers/*.json` (all historical files are protected, regardless of changing inventory counts).
3. **Never delete the research or artifact trees**:
   - `research/` (contains historical scraper bakeoffs and datasets).
   - `artifacts/` (contains empirical validation proof and benchmark metrics).
4. **Never run destructive mass git cleanup**:
   - Strictly avoid `git clean -fdx`. Do not rewrite Git history.
5. **Never delete working scrapers or compatibility shims**:
   - Keep `scrapers/` and `backend/services/agent_reach_scraper.py`.

### 🛡️ Safe Areas for Modification
- Bug fixes and optimizations in `backend/` adhering to existing interfaces.
- Design improvements in `frontend/` adhering to `aegis-theme.css`.
- New unit/integration tests in `tests/`.
- Documentation additions and updates in `docs/`.
- Dedicated scripts in `scripts/`.

---

## 3. Protected Operation Contracts (16 Recovered Routes)

The following 16 operations must remain registered, routable, and verified across all four agents:
```text
1.  github.read          5. github.releases      9.  v2ex.latest         13. web.read
2.  github.issues        6. youtube.read         10. v2ex.search         14. rss.read
3.  github.prs           7. youtube.transcript   11. v2ex.topic          15. xiaoyuzhou.podcast
4.  github.commits       8. youtube.comments     12. v2ex.replies        16. xiaoyuzhou.episodes
```
Contract test: [`tests/unit/test_recovered_operation_routes.py`](tests/unit/test_recovered_operation_routes.py).

---

## 4. Critical Commands for Agents

Always run these commands to verify changes before concluding work:

```bash
# 1. Run full offline regression test suite (discover the current inventory)
pytest tests/ -q

# 2. Run fast unit, chaos, and security suites (counts/timings vary)
pytest tests/unit tests/chaos tests/security -q

# 3. Check for fatal syntax or compilation errors
flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics

# 4. Run release candidate smoke validation
python scripts/validate_release_candidate_smoke.py

# 5. Run rollback compatibility validation
python scripts/validate_rollback_compatibility.py
```

See the [handoff testing runbook](docs/handoffs/2026-10-12_ARCHITECTURE_REMEDIATION_TESTING.md) for compact output, frontend checks, frozen-data validation, temporary logs, and failure interpretation. The historical archive currently has 55 invalid JSON files: rollback validation must report that failure honestly, not silently skip or repair protected dossiers. A passing offline suite does not establish live-provider health, remote CI, or deployed rollback.

---

## 5. Coding & Testing Conventions

1. **Async / Sync Boundaries**: Never block the event loop with synchronous network I/O. Use `async def` with awaited worker offloading for blocking agent calls, or FastAPI synchronous handlers that execute in its worker pool. CPU-bound scoring and deterministic regex routines remain synchronous. Preserve per-agent admission guards while singleton scan state is shared.
2. **Deterministic Fallbacks**: External network requests must have bounded timeouts (`timeout=5.0s`), maximum response size caps (`max_bytes=1_000_000`), and SSRF validation via `is_safe_url()`.
3. **No Secret Leaking**: Never log API keys, auth cookies, or authorization tokens. Strip credentials before generating report artifacts.
4. **Truthful Telemetry**: If evidence cannot be retrieved, return `INSUFFICIENT_EVIDENCE` or `status: "failed"`. Never fabricate fake positive search results.
5. **Cross-Platform Compatibility**: Always use `os.path.join` or `pathlib.Path`. Never hardcode Windows-specific (`C:\Users\...`) or POSIX-specific absolute paths.
6. **Documentation Links**: Use relative Markdown links (`../docs/...` or `docs/...`). Avoid absolute filesystem URLs (`file:///...`).

---

## 6. Authoritative Documentation Index

- [Documentation Portal](docs/index.md)
- [Developer Workspace Map](docs/development/WORKSPACE_MAP.md)
- [Script Index](docs/development/SCRIPT_INDEX.md)
- [Architecture Blueprint](docs/architecture/TARGET_ARCHITECTURE.md)
- [Production Configuration Matrix](docs/operations/PRODUCTION_CONFIGURATION_MATRIX.md)
- [Rollback Verification](docs/operations/ROLLBACK_VERIFICATION.md)
- [CI Coverage Matrix](docs/testing/CI_COVERAGE_MATRIX.md)
- [Latest Coding-Agent Handoff](docs/handoffs/README.md)
- [Remediation Decisions and Code Map](docs/handoffs/2026-10-12_ARCHITECTURE_REMEDIATION_DECISIONS.md)
- [Execution Work Log](docs/handoffs/2026-10-12_ARCHITECTURE_REMEDIATION_WORK_LOG.md)

## 7. Required Handoff for Subsequent Coding Agents

Before changing code, read the latest handoff, inspect `git status --short` and the relevant diff, and preserve the existing uncommitted implementation. Do not assume the branch name or old test count proves acceptance.

Before leaving an implementation task:

1. Leave a dated Markdown handoff under `docs/handoffs/` and link it from the handoff index.
2. Record the user-request scope, observed branch/base commit, changed code and regression-test pointers, decision rationale and tradeoffs, and outstanding risks or owner actions.
3. Record commands actually run, exit codes, results, and limitations. Label excerpts or reconstructed work logs accurately; do not invent a raw transcript, passing tests, CI runs, or live evidence.
4. State whether changes were committed/pushed. Keep secrets, credentials, private personal data and private reasoning traces out of documentation; preserve useful engineering conclusions instead.
5. Use relative links and portable commands. Save fresh diagnostic outputs only in temporary or explicitly new locations, never over tracked evaluation proof or historical dossiers.
6. Keep historical records intact, append new evidence, and make it easy to distinguish completed work from planned or unverified work.
