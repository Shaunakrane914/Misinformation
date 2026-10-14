# Phase 8 automated accessibility proof

The [final three-viewport axe-core run](2026-10-13_final_truthful_labels_axe/summary.json)
scanned the initial rendered state of the four static agent pages at
1440/390/320px. It found zero automated WCAG A/AA or best-practice violations
in these 12 states. The color-contrast rule was incomplete on gradient or
backdrop surfaces and needs manual review. Dossier-open states, actual
screen-reader behavior, and live backend responses were not covered by axe.

Earlier negative runs remain local append-only diagnostics. The audit script
requires an explicitly supplied axe-core distribution; no dependency or
binary is silently installed by the repository.
