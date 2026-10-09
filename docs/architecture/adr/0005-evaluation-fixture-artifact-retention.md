# ADR 0005: Evaluation Benchmark Data Governance and Artifact Retention Policy

## Status
**PROPOSED (Pending Architectural Review)**

## Date
2026-10-09

## Deciders
- Principal Software Architect & Migration Lead
- Aegis Protocol Core Engineering Team

---

## 1. Context and Problem Statement
The repository contains large quantities of evaluation fixtures, experimental datasets, historical benchmark runs, and media captures:
- The authoritative 104-scenario / 416-candidate frozen retrieval benchmark dataset in `tests/retrieval_benchmark/`.
- 338 MB of historical research files and PDF/JSON dumps in `research/`.
- 31 MB of PNG screenshots in `docs/visual-audit/`.
- Generated evaluation runs and summary files in `artifacts/`.

Without a clear data governance and retention policy:
1. Docker build contexts swell to >430 MB, copying local research scratchpads into production container images.
2. Git checkouts become bloated.
3. Confusion arises over which benchmark files are canonical golden fixtures versus obsolete scratch runs.

---

## 2. Decision Drivers
1. **Scientific Reproducibility**: The 104-scenario / 416-candidate benchmark must remain completely immutable and reproducible across git commits.
2. **Lean Production Artifacts**: Container images and deployment packages must contain zero research dumps, scratchpads, or screenshots.
3. **Audit Evidence Preservation**: Historical evaluation findings and verification reports must never be deleted indiscriminately; they must be archived with clear provenance manifests.
4. **Independent Gold-Label Separation**: Gold labels must be maintained independently from production ranker outputs and must never be altered to artificially inflate benchmark scores.

---

## 3. Considered Alternatives
- **Alternative 1: Delete all historical research and visual-audit files immediately via git-filter-repo**.
  - *Rejected*: Destructive; risks losing audit evidence and destroys commit history hashes.
- **Alternative 2: Leave everything in place with no boundaries**.
  - *Rejected*: Leaves repository at 51 MB tracked / 450 MB working directory, with high risk of secret and data leakage into production containers.
- **Alternative 3: Tiered Retention and Strict Build Exclusion (Chosen)**.
  - Classify all data into 6 explicit retention categories.
  - Enforce `.dockerignore` to immediately contain build contexts.
  - Separate frozen test fixtures from ephemeral research outputs.

---

## 4. Decision Outcome
Chosen option: **Alternative 3 — Tiered Retention and Strict Build Exclusion**.

### 4.1 Six-Tier Retention Classification

| Tier | Category | Location | Policy |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **Frozen Canonical Fixtures** | `tests/retrieval_benchmark/` | **Keep in source**: `scenarios.jsonl`, `candidates.jsonl`, `labels.jsonl`. Immutable; bit-for-bit preserved. |
| **Tier 2** | **Evaluation Harness Code** | `scripts/run_live_retrieval_quality_evaluation.py` | **Keep in source**: Versioned, tested evaluation tooling. |
| **Tier 3** | **Official Audit Reports** | `artifacts/live_retrieval_evaluation/`, `artifacts/retrieval_benchmark/` | **Tracked with manifests**: Markdown summaries and JSON metric manifests preserved. |
| **Tier 4** | **Historical Research Experiments** | `research/` (338 MB) | **Local / Archive**: Excluded from Docker (`.dockerignore`) and git tracking; preserved in developer storage. |
| **Tier 5** | **Visual Audit Screenshots** | `docs/visual-audit/` (31 MB) | **Dedicated Asset Archive**: Retained for portfolio/audit reference; excluded from production containers. |
| **Tier 6** | **Ephemeral Scratch & Cache** | `scratch/`, `.pytest_cache/`, `*.log`, `aegis_local.db` | **Git & Docker Ignored**: Strictly prohibited from commits and builds. |

### 4.2 Gold-Label Invariant
Under no circumstances may gold labels in `tests/retrieval_benchmark/labels.jsonl` be modified to accommodate or mask ranking algorithm deficiencies. Metrics must reflect true system performance.

---

## 5. Consequences

### Positive Consequences
- **Build Safety**: Production container size drops from >450 MB to ~20 MB build context.
- **Audit Traceability**: Every evaluation run in `artifacts/live_retrieval_evaluation/` preserves exact run ID, timestamp, and commit SHA.
- **No Git History Rewrites**: Preserves all existing commit hashes and external citations.

### Negative Consequences / Trade-offs
- Developers running manual ad-hoc evaluations must specify `--output` directories intentionally to adhere to artifact storage guidelines.
