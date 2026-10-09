# Aegis Protocol — Historical & Audit Archive

This archive contains historical audit reports, legacy roadmap plans, and early milestone snapshots from earlier project iterations. These documents are preserved for audit lineage and historical reference, but are formally superseded by the active documentation tree.

---

## 🏛️ Superseded Audit Documents

| Archived Document | Original Milestone Date | Original Context | Canonical Modern Successor |
| :--- | :--- | :--- | :--- |
| [`docs/audit/ARCHITECTURE_REVIEW.md`](../audit/ARCHITECTURE_REVIEW.md) | October 2, 2026 | Initial assessment when `backend/main.py` was >2,100 lines | [`docs/architecture/CODEBASE_INVENTORY.md`](../architecture/CODEBASE_INVENTORY.md) & [`docs/architecture/TARGET_ARCHITECTURE.md`](../architecture/TARGET_ARCHITECTURE.md) |
| [`docs/audit/IMPROVEMENT_PLAN.md`](../audit/IMPROVEMENT_PLAN.md) | September 2026 | Initial 8-phase plan on branch `aegis/full-project-improvement` | [`docs/architecture/MIGRATION_PLAN.md`](../architecture/MIGRATION_PLAN.md) |
| [`docs/audit/BASELINE_AUDIT.md`](../audit/BASELINE_AUDIT.md) | September 2026 | First repository discovery audit | [`docs/architecture/CODEBASE_INVENTORY.md`](../architecture/CODEBASE_INVENTORY.md) |
| [`docs/audit/TESTING_BASELINE.md`](../audit/TESTING_BASELINE.md) | September 2026 | Initial 180-test baseline | [`docs/TESTING.md`](../TESTING.md) (530 tests) |
| [`docs/audit/FEATURE_VERIFICATION_MATRIX.md`](../audit/FEATURE_VERIFICATION_MATRIX.md) | October 2026 | Preliminary sentinel status audit | [`docs/FEATURE_STATUS.md`](../FEATURE_STATUS.md) |
| [`docs/audit/PROGRESS.md`](../audit/PROGRESS.md) | October 2026 | Legacy sprint tracker | [`docs/architecture/MIGRATION_PLAN.md`](../architecture/MIGRATION_PLAN.md) |
| [`docs/audit/SECURITY_FINDINGS.md`](../audit/SECURITY_FINDINGS.md) | September 2026 | Preliminary SSRF/XSS assessment | [`docs/SECURITY.md`](../SECURITY.md) |

---

## 🔒 Retention & Immutability Policy

1. **Do Not Rewrite History:** These historical documents must not be deleted or modified to retroactively match newer implementations.
2. **Clear Labeling:** All archived documents must carry an explicit `[SUPERSEDED]` header alert directing analysts to the canonical modern document.
3. **Container Exclusion:** All historical audit documents and experiment logs are excluded from Docker container builds via `.dockerignore`.
