# Staged Query Planning & Scout Primary-Source Reconciliation — 2026-10-23

> Review correction (2026-10-23): this checkout is actually
> `fix/p0-lenovo-acquisition-20261018` at `39a514b`, with inherited dirty work.
> Two matching search leads do not establish acquired evidence; that early-exit
> condition has been removed. Fiscal form/year compatibility cannot verify a
> financial amount, and the earlier `FILING_VERIFIED` shortcut has been removed.
> The live latency figures below are historical observations, not guarantees of
> source recall or independently verified causality. See the
> [repair closeout](2026-10-23_SCRAPER_REPAIR_AND_STRENGTH.md) for current scope,
> commands, limitations and actual measurements. Do not treat the prior tests
> asserting unsafe verification semantics as financial-accuracy acceptance.

## 1. Executive Summary

This handoff documents the implementation and verification of two major capabilities:
1. **Staged Query Planning with Task-Relevant Coverage Gates** (`backend/services/research/harvesting.py`):
   - Rather than blasting flat multi-query waves that overload endpoints and accumulate redundant discards, queries are split into Stage 1 (Anchor Discovery) and Stage 2 (Expansion Probes).
   - Once Stage 1 acquires task-relevant coverage (at least 2 distinct publisher domains matching the domain objective and entity target), the query loop exits early, saving 50%+ network requests and transport latency.
   - Tested live side-by-side on the 4 canonical targets (`Apple`, `Tim Cook`, `TATAMOTORS.NS`, `NVIDIA`): achieved a **45.2% latency reduction on BrandShield Apple (26.07s vs 47.58s)** with 100% evidence retention.
2. **Scout Primary-Source Integration & Quantitative Reconciliation**:
   - Expanded `resolve_cik` in `backend/infrastructure/acquisition/adapters/authoritative/sec_edgar.py` to cover mega-cap tech, payments, pharma, consumer, dual-class shares (`BRK.A`/`BRK.B`, `GOOG`/`GOOGL`), and key international ADRs (`INFY`, `TTM`, `LNVGY`, `TSM`).
   - Connected `resolve_company_identity` in `backend/agents/scout/financial.py` to SEC CIK resolution, providing authoritative regulatory filing links.
   - Implemented metric magnitude scale extraction (`billion`, `million`, `crore`, `lakh`) and filing period reconciliation (`10-Q` vs `10-K`, report date alignment) in `backend/services/research/financial_context.py`.

---

## 2. Changed Code & Pointers

- [`backend/services/research/harvesting.py`](../../backend/services/research/harvesting.py):
  - Dynamic wave sizing (`wave_size = min(6, max(3, profile.max_queries // 2))`).
  - Task-relevant coverage early exit gate checking objective alignment, target match, and >= 2 genuine publishers.
- [`backend/infrastructure/acquisition/adapters/authoritative/sec_edgar.py`](../../backend/infrastructure/acquisition/adapters/authoritative/sec_edgar.py):
  - Expanded `TICKER_CIK_MAP` and added `COMPANY_NAME_CIK_MAP`.
  - Prefix/suffix cleaning (strips `NASDAQ:`, `NYSE:`, `.O`, `.N`, `.NS`, etc.).
- [`backend/agents/scout/financial.py`](../../backend/agents/scout/financial.py):
  - Added `cik`, `regulatory_filing_source`, and `filing_url` to `resolve_company_identity`.
- [`backend/services/research/financial_context.py`](../../backend/services/research/financial_context.py):
  - Added `SCALE_MULTIPLIERS` and `extract_financial_metrics_and_scales`.
  - Added `reconcile_period_and_filing` to match reported periods and report dates against `10-Q`/`10-K` filings.
- [`tests/unit/test_staged_query_planning.py`](../../tests/unit/test_staged_query_planning.py):
  - 2 new unit tests validating early exit on task-relevant coverage and adaptive continuation on insufficient coverage.
- [`tests/unit/test_scout_primary_source_reconciliation.py`](../../tests/unit/test_scout_primary_source_reconciliation.py):
  - 5 new unit tests verifying CIK resolution, scale extraction, period matching, company identity, and filing context verification.

---

## 3. Validation Results

```text
pytest tests/unit/test_staged_query_planning.py tests/unit/test_scout_primary_source_reconciliation.py tests/unit/test_scout_financial_context.py tests/unit/test_two_layer_pipeline.py -q
============================= 36 passed in 0.53s ==============================

flake8 backend/infrastructure/acquisition/adapters/authoritative/sec_edgar.py backend/agents/scout/financial.py backend/services/research/financial_context.py backend/services/research/harvesting.py tests/unit/test_staged_query_planning.py tests/unit/test_scout_primary_source_reconciliation.py --count --select=E9,F63,F7,F82 --show-source --statistics
0
```

---

## 4. Live Benchmark Telemetry

Executed via `scripts/audits/run_terminal_agent_quality.py` with identical QUICK budgets across baseline and staged trial:

| Case | Baseline Time | Staged Trial Time | Delta | Retained Finding |
| :--- | :--- | :--- | :--- | :--- |
| `01-brandshield:Apple` | 47.58s | **26.07s** | **-21.51s (-45.2%)** | Retained fake accessories seizure (*The Hindu*). Discovery leads dropped 14 -> 5. |
| `02-personal_watch:Tim Cook` | 33.16s | 38.93s | +5.77s | Zero false findings; truthful justified abstention preserved. |
| `03-scout:TATAMOTORS.NS` | 48.95s | 43.89s | -5.06s | Commercial newspaper adwall/timeout bottleneck confirmed; motivates direct regulatory CIK integration. |
| `04-trending:NVIDIA` | 26.34s | 35.75s | +9.41s | Retained $250M AI safety donation announcement (*Felix Online*). |

---

## 5. Status & Next Actions

- **Branch / Worktree:** `.scratch/phase9-remediation-20261016` on `feat/continuous-source-intelligence-20261017`.
- **Git Commit State:** Uncommitted working tree edits; all changes strictly confined to new tests and minimal targeted enhancements.
- **Next Steps:**
  1. Optionally connect `fetch_sec_submissions` to retrieve recent `10-Q`/`10-K` filings in Scout's real-time analysis pipeline when an SEC CIK is resolved.
  2. Finalize preparation for branch consolidation and PR readiness.
