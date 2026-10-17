# Role-aware evidence and bounded AI assistance — 2026-10-17

## Scope and starting state

User authorized the suggested evidence-role, agent-intent, bounded financial PDF
and frontend improvements, and asked for an intervening AI suggestion layer.
Development checkout: `feat/continuous-source-intelligence-20261017`, starting
HEAD `d37b35f7372f734a65406919bf6bf7ead4a4ecf4`; initially clean.
No main merge/deployment, credential edit or access-policy changes authorized.
The previous [source/agent review](../testing/CONTINUOUS_SOURCE_INTELLIGENCE_REVIEW_2026-10-17.md)
remains the before observation, not acceptance of this implementation.

## Engineering decisions and implementation

- Shared `content_roles.py` separates document indexes/landing pages/profiles,
  author biographies/navigation/legal disclosures and substantive candidates.
  These are conservative heuristics, not calibrated truth labels. Raw capture
  is preserved. Passage selection now applies financial/brand/personal objectives.
- Source quality and post-read classification demote captured indexes without
  removing their provenance. Deep reads refresh stale feed-summary completeness.
- Brand/identity search actions move ahead of generic company searches; entity-only
  brand/personal flows do not consume publisher-product feeds as their main plan.
- Reused the existing source planner: automatic advice only when live credentials
  are configured and mock mode is off. At most one validated search suggestion
  enters the existing per-channel budget. No model-suggested reads, URLs or
  invented subreddits; deterministic/runtime capability gates still apply.
- New `evidence_advisor.py`: model selects whole enumerated captured paragraphs
  by canonical ID and exact offsets. Subject, content role and objective are
  rechecked. It cannot rewrite raw text, create URLs, set authority or adjudicate
  claim support. Calls skip personal-watch content and likely sensitive text;
  the PII guard is conservative, not comprehensive.
- Advisory calls have at most two outstanding workers process-wide, no queued
  accumulation, a 2–2.5s caller deadline, one provider attempt and output-token
  bounds. Late results cannot mutate research records. Unavailable models retain
  deterministic processing. This extends the centralized gateway, not a second
  inference stack.
- Gemini provider previously ignored caller timeout kwargs. It now honors
  per-call HTTP/total timeout, maximum attempts, token limits and optional JSON
  mode while preserving existing fallback behavior when these are omitted.
- Financial followups retain the existing read/time budget: up to two reserved
  followup reads and maximum three observed same-origin link hops. PDFs are
  actually parsed, not decoded as UTF-8/HTML.
- `pdf_text.py` uses pinned `pypdf==6.10.0` in a secret-stripped subprocess:
  1MB input, eight pages, 24k text characters, 2.5s wall limit, 384MiB process
  memory and two seconds CPU (POSIX resource limits / Windows Job Object).
  Resource-limit failure, encryption and malformed documents fail closed.
  Resource isolation is not a complete OS security sandbox. No OCR or verified
  table-cell/period/unit alignment is claimed. PDF layout text, page offsets,
  source hash and truncation reach source inspection on all four pages.
- `processing_notes.ai_passage_advice` exports only bounded status/count fields.
  Frontend labels it advisory, not entailment. Hostile status/PDF rendering
  controls are in the Node renderer tests.

## Tests and current observations

Actual final local suite: `pytest tests/ -q` exit 0, **1,359 passed (122.46s)**;
fast unit/chaos/security exit 0, **1,151 passed (67.18s)**.
All eight Node suites, fatal Flake8, smoke, persistence/rollback and frozen
validation passed. Historical archive is NOT_VERIFIED in this worktree;
this does not repair or certify the original damaged dossiers.
Existing research/agent golden manifests and frozen JSONL were not changed.

New controls: `tests/unit/test_evidence_role_advisor.py` (23) and
`tests/unit/test_bounded_pdf_text.py` (7). They cover role filtering, retained
negation/offsets, objective-specific passages, bounded provider attempts, privacy,
late-result isolation, stage→public-report advice, valid query execution budgets,
PDF page/encryption/resource bounds and native transport→inspection.

Intermediate failures were real and fixed: initial missing interfaces; nine
full-suite/six fast-suite BrandShield failures after applying article-style
entity/length constraints to the legacy short-lead taxonomy; corrected by keeping
legacy title-led leads separate from shared grounded findings. Generic/about text
is still excluded. An oversized pytest parameter initially produced Windows
temporary-path setup errors; explicit short case IDs fixed the test harness.
Adding NOT_NEEDED AI telemetry initially changed eleven golden result digests;
no-op advice is now omitted rather than replacing any historical hash. No
expected source bytes/findings were regenerated to hide failures.

Live AI diagnostic: model-list HTTP **200**, configured generation models
listed, but minimal structured inference returned **429**. No successful live
AI advice or exact quota diagnosis is claimed. Diagnostic exit 2 is intentional
UNAVAILABLE, not PASS. Existing secrets/models were not edited. Rerun securely:

```text
python scripts/diagnostics/check_ai_advisory_runtime.py --allow-live --env-file <existing-env> --output <new-json>
```

Environment switches documented in `.env.example`:
`AEGIS_SOURCE_PLANNER_LLM_ENABLED=auto` (false disables; true explicitly requests)
and `AEGIS_EVIDENCE_ADVISOR_ENABLED=true`. No real .env was changed.

## Publication and remaining acceptance

Application commit/push and exact-code hosted CI must be checked in the final
review/closeout; this initial handoff is not a CI claim. First live matrix
overlapped source edits and is diagnostic only (fingerprint invalidated).
A subsequent frozen-application twelve-input matrix, four new controls and
all-52-operation/display checks are being recorded separately. Temp raw outputs
use a fresh `aegis-ai-evidence-*` directory; do not overwrite tracked proof.

Do not declare Phase 9/research complete: live AI generation is unavailable,
financial table semantics remain unverified, legacy threat heuristics retain
title-led investigatory leads, and brand/identity acquisition is still uneven.
Frontend strategic explanations and independently reviewed claim-support
evaluation remain follow-up work. Preserve blocked providers and protected data.

## Subsequent live-discovered fix

The first stable native matrix reproduced a high-severity Nike counterfeit
false positive: substring `clone` matched the product name `Cyclone`. Fixed
word boundaries in both the native extractor and legacy heuristic, plus the
shared brand objective matcher. Two failing-before/passing-after controls are
now in the role-adviser test file (25 tests). This does not authenticate or
whitelist `nike.in`, nor suppress actual replica/clone listings.

After this fix: full suite exit 0 **1,361 passed (108.21s)**; fast suite exit 0
**1,153 passed (56.78s)**. All old research/agent goldens still pass unchanged.
Implementation `6666b08` passed all five hosted CI jobs; the boundary followup
and its final normal matrix must be verified independently in the closeout.

A direct native read of observed `q1-2027.pdf` succeeded through `native_pdf_text`.
The separate combined audited-results PDF failed the existing 1MB transport cap;
it is not a parser success or authorization to enlarge the cap. Normal financial
results still vary with read budgets/provider timing and often retain indexes.
Do not turn a successful direct PDF read into an accepted Scout investigation.

## Source-to-frontend metadata repair

Actual Scout PDF captures exposed that Scout's serializer replaced metadata with
only `truncated`. Added `public_capture_metadata` to the inspection contract and
used it at Scout/BrandShield boundaries: explicit field allowlist, bounded raw
capture/page observations, no auth/cookie/provider envelope passthrough. PDF page
offsets are clipped to the actual retained body; beyond-body pages are omitted,
partial pages remain labeled truncated. Known index/landing/profile roles are
explicitly discovery-only in inspection, not body support.

Two red-then-green controls are in `tests/unit/test_public_capture_metadata.py`.
Full suite exit 0 **1,363 passed (53.90s)**, fast exit 0 **1,155 passed (30.70s)**
after this repair. A fresh all-operation pass adds one observed public PDF URL:
**52 unique operations / 53 executions**, not 53 supported operations. It
captures 79 observations including the PDF, at a stable source fingerprint.
The final current-code normal matrix and display checks are in the review.

## Final measurement / CI closeout

[Two-section review](../testing/ROLE_AWARE_AI_EVIDENCE_REVIEW_2026-10-17.md),
[durable proof](../testing/evidence/2026-10-17_role_aware_ai_evidence/README.md).
Final current-code normal matrix: twelve cases / 24 viewports, stable application
hash `3d5290a779c290764ddb770c9168141d14d0731867da9fd1dbc339ebefc40d48`,
29 native records / 12,736 retained-text words. Two empty cases remain (OpenAI,
Brand/Tata); profiles/catalogs/indexes are not accepted research. Infosys now
retains a 1,456-word PDF and one separately cited UNVERIFIED financial passage;
EV has two article passages, no author biography. All twelve mobile report
captures and focused real-PDF display captures were visually inspected.

All final requests completed (HTTP 200 / 29 progress events); 24 states preserve
findings/source/discovery counts and text, no document overflow or uncaught page
exceptions. Console resource errors remain recorded. Source display: 69 samples,
12 states / zero measured failures; separate real-PDF-only scaffold: 12 states /
zero failures. These scaffolds are display checks, not normal investigations.

Application `3d628e1b1d16640af7bc3efb857d7d363ce2efec` was committed/pushed;
[all five exact-commit hosted jobs passed](https://github.com/Shaunakrane914/Misinformation/actions/runs/39053082338).
Earlier `6666b08` and `19bf350` also passed five hosted jobs. Documentation/evidence
closeout is a later successor with unchanged application code. Inspect current
Git/CI, not just an old branch label. No main merge or deployment.

**Next P1:** BrandShield's `agent.py` compatibility loop converts non-threat
evidence into “Genuine Issue” findings. Final Nike/Apple still display product
snippets despite shared objective gates; do not label this fixed or safe. Keep
background observations separate and preserve contracts deliberately. Further
priorities: financial table/period/unit alignment and oversized-document handling
within policy; concrete brand/identity abuse acquisition; case-specific strategic
briefs; independently reviewed claim-support evaluation. Live AI inference remains
unavailable (429), not verified by offline fake-provider controls.
