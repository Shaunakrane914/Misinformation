# Phase 8 frontend rendered-page proof

All directories here are append-only local audit runs. The negative baseline
and intermediate runs are intentionally retained rather than rewritten. The
selected committed proof is the
[final truthful-label run](2026-10-13_final_truthful_labels/summary.json):
Playwright Chromium, four pages, 1440/390/320px, initial states and explicitly
labeled synthetic contract fixtures. Screenshots show a localhost-served static
frontend, not live-provider responses. The summary records each view's
overflow, page errors, control naming, dynamic reveal, source-link safety, and
modal keyboard checks. A horizontally scrollable tab strip and a closed,
off-canvas provenance drawer can have child bounding boxes beyond the viewport
without widening the document; actual overflow uses document scroll width.

Only selected screenshots are committed to keep the repository bounded. Other
captures from this run can be regenerated with the audit script. Neither
automated geometry nor screenshots establish screen-reader usability or live
backend contract completeness.
