# Proposed Phase 9 — Evidence Depth & Strategic Investigation Workbench

Planning date: 2026-10-15. Status: PROPOSED, not implementation or release acceptance.

Implementation update, 2026-10-15: [acquisition-depth checkpoint](../handoffs/2026-10-15_PHASE9_ACQUISITION_DEPTH.md) implements a bounded subset of this plan, including all-operation evaluation, additive community sources, inspection contracts and UI follow-ups. The complete plan remains PARTIAL, not accepted. User confirmed no approved source access is configured and requested retaining explicit blocked states.

Planning update, 2026-10-16: [acquisition pipeline improvement plan](ACQUISITION_PIPELINE_IMPROVEMENT_PLAN_2026-10-16.md) defines the proposed implementation order for report preservation, one-line entity/intent planning, subreddit/source selection, source depth, shared budgets and four-agent evidence views. The operator subsequently enabled a local Reddit diagnostic; [its actual results](../handoffs/2026-10-16_LOCAL_REDDIT_PROBE.md) distinguish RSS from archive fallback. Production access was not enabled. These updates do not establish full Phase 9 acceptance.

## Objective and baseline

Maximize useful, authorized, claim-relevant evidence from existing sources and make its meaning, limits and next investigative actions clear on all four agent frontends. More bytes, cards, HTTP successes or model prose are not success metrics.

Planning baseline: independent-review branch `feat/phase8-independent-audit-codex`, observed HEAD `abe547f1e17aab5b54e90ff55e2d4783afa95283`. Five existing documentation edits were present and preserved when this plan was added; they are not a completed documentation closeout. Original and other-agent worktrees must remain untouched.

The [independent review](PHASE8_INDEPENDENT_REVIEW_2026-10-14.md) found bounded live samples for all 16 protected operations, but Phase 8B–8F remain PARTIAL. Its clean Apple four-agent API run returned 3/0/0/0 evidence records. Ten assistant-source-adjudicated reference cases had safe outcomes 10/10 but truth resolution 0/4; this is not human-ground-truth accuracy. These findings motivate the plan, not an assumption that all Phase 8 work is complete.

## Architectural decisions

- Retain the modular monolith, canonical acquisition service, research stages and report builder. No new orchestration framework, vector database, microservice split or generic scraper collection is required for this phase.
- Improve the complete vertical path: discovery → bounded acquisition → structured extraction → qualification → passage-linked findings → report → rendered inspection. Validate each source improvement through its actual consumer.
- Extend existing evidence and unified-report contracts additively, with explicit schema versioning and compatibility tests. Do not introduce a parallel evidence model or silently discard richer fields during normalization/report assembly.
- Separate source availability, document depth, provenance, relevance, independence and claim support. A credible publisher or matching citation ID does not establish entailment.
- Provide Quick and Deep investigation budgets. Deep is still bounded by request/page/byte/time limits, cancellation and concurrency controls. Display actual coverage and stop reasons; never silently imply an exhaustive website crawl.

## 9A — Baseline, source contracts and observability

Start from the [extraction matrix](PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md). For every protected operation and each auxiliary authoritative source, inventory intended fields, acquisition method, access constraints, current depth, downstream use and failure modes. Test ordinary, information-rich and unavailable/restricted examples. Keep all failures in the availability report.

Track the funnel per investigation: candidates discovered, documents fetched, meaningful bodies acquired, relevant passages accepted, independent origins, supported/contradicted/uncertain findings and rejected candidates with reasons. Keep a separate reason for no discovery, inaccessible content, irrelevant content, insufficient passage support and budget exhaustion.

Before implementation, establish baseline measurements and lock acceptance thresholds on a development set. Keep a separate evaluation set; never tune thresholds on held-out results or modify frozen retrieval data. Document source-specific eligible-field denominators rather than reporting a misleading universal completeness percentage.

Deliverables: source inventory, versioned contract changes, reproducible before/after harness and explicit budget telemetry. Gate: richer provider fields demonstrably survive to the report/UI contract, including unknown/missing values.

## 9B — High-value depth before broad expansion

Priority order is proposed; adjust only against measured investigation failures.

| Priority / source | Target useful extraction | Important limit |
|---|---|---|
| P0 web and RSS | Claim-specific article discovery; direct linked-body reads; meaningful sections, tables, quotations, correction notices and declared publication/modification dates; original versus syndicated lineage | Feed entry is not an acquired article. Unknown dates stay unknown; page declarations cannot authenticate ownership. |
| P0 SEC / issuer disclosures | Issuer resolution, accession/document identity, actual filing sections and XBRL facts aligned by period, unit, currency, reporting scope and amendments | Requires authorized SEC contact. Submission metadata is discovery only; conflicting periods or units must not be combined. |
| P1 GitHub | Bounded issue/reply chronology, PR discussion/reviews/changed-file samples, commit patches where relevant, release-to-commit/source linkage | Repository README is not whole-repository analysis; public counters and verification metadata are provider observations. |
| P1 YouTube | Available timed transcript passages linked to video offsets; explicitly sampled comments/replies; language/track and retrieval boundaries | Captions are not visual or audio forensic verification. Missing transcripts must not be synthesized. |
| P1 Reddit / X | Permalink-led posts, available reply context, observed edits/times/engagement snapshots and source identity | Public or mirror visibility is incomplete. No platform-wide spread, bot, identity or deletion-history claim from a sample. |
| P2 V2EX / podcasts | Topic/reply context; episode show notes and referenced links; exposed pagination and available transcript access | V2EX node lookup is not general search. Episode metadata/audio links are not acquired transcript or audio semantics. |
| P2 NVD / arXiv / FactCheck | Relevant advisories/references, actual accessible paper sections where authorized, attributed fact-check metadata and linked review passages | NVD metadata is not exploitation prevalence; arXiv is not peer-review certification; FactCheck needs authorized credentials and publisher ratings remain attributed. |

Pagination must retain continuation state, requested/returned pages, sampled counts, truncation, exhausted budget and known remaining pages. Never infer a total when the provider does not expose one. Follow only relevant, policy-allowed links; retain SSRF/DNS/redirect, response-size and decompression protections.

Do not add sites merely to grow a source count. Add a source only when a representative unresolved investigation demonstrates an evidence gap and existing sources cannot fill it.

## 9C — Grounded strategic findings

Use existing qualification, relevance, independence, proposition-grounding and model-grounding modules. Build passage-addressable evidence with stable IDs, observed source URL, retrieval time, publication time when known, content hash, depth and lineage. Preserve permitted bounded excerpts and structured facts; raw payload retention must respect privacy, copyright and access policy.

Each finding must identify: the claim or investigative question, exact supporting passages, contradictory passages, scope/time/entity alignment, independent-origin groups, uncertainty and missing evidence. A source can mention an entity without supporting the claim. Syndicated copies must not inflate corroboration.

Strategic recommendations must distinguish observed facts, heuristic interpretation and recommended investigation. Include the evidence basis, why the item matters, what remains unknown and the next verification step. Do not generate automatic takedowns, trading instructions or accusations from a pattern flag.

Gate: every asserted source-backed finding resolves to the exact captured evidence; semantic support is independently evaluated, not inferred from valid IDs. Abstention remains available and is measured separately from successful resolution.

## 9D — Four-agent strategic frontend

Use one shared evidence inspection pattern with agent-specific analytical views. Preserve existing theme and vanilla frontend architecture; avoid another design-system rewrite.

| Agent | Primary analytical view | Necessary context / guardrail |
|---|---|---|
| Scout | Financial event dossier, issuer/period/unit-aligned fact table, filing passages, conflicting disclosures and catalyst chronology | Separate financial observations, allegations and verified contradictions. No causal stock-impact narrative without evidence. |
| Trending | Sampled narrative clusters, earliest observed source, time windows, independent origins and changing observations | Show sampling and denominator. Velocity requires comparable repeated observations; earliest observed is not proven origin. |
| BrandShield | Evidence-linked allegation clusters, suspicious domain/account observations, review patterns and prioritized review queue | Pattern or name similarity is not confirmed impersonation, fake reviews or coordinated smear. |
| Personal Watch | Candidate identity map, impersonation/quote context, privacy-pattern triage and source-linked exposure review | Candidate handles are not authenticated identities. Minimize/redact PII; no deepfake or unauthorized-exposure certification from text alone. |

Every result page should expose, in this order:

1. Decision brief: what was observed, what can be concluded and what cannot.
2. Evidence/coverage strip: inspected documents, independent origins, content depth, missing sources and freshness.
3. Prioritized findings: importance rationale, exact citations, contradictions and review status.
4. Timeline and comparison views: publication, event and retrieval time kept distinct; unknown dates not filled in.
5. Evidence explorer: search/filter/sort, bounded or paginated results, full captured passage inspection and retrieval history.
6. Recommended next steps: evidence gaps, suggested verification action and rationale; no invented completion or external enforcement.

Use progressive disclosure to remain information-rich without congestion. Separate heuristic quality dimensions from calibrated probabilities; do not display invented confidence percentages. Handle empty, sparse, blocked, partial, stale and failed runs as designed states. Preserve keyboard navigation, focus return, semantic controls, contrast, safe URLs and responsive layouts.

Gate: actual backend contracts reach the rendered page without truncation-induced misrepresentation; representative real evidence-rich investigations are usable on desktop and mobile. Recorded payload replay and explicitly synthetic stress cases supplement, not replace, live-path validation.

## 9E — Independent acceptance and closeout

Create a proposed initial set of 40 independently adjudicated investigation cases, ten per agent, including positive, negative, ambiguous, outdated, inaccessible and adversarial cases. Domain experts or human reviewers must validate labels and supporting passages; assistant-only labels must remain disclosed. This is an initial acceptance sample, not a population-accuracy benchmark. Keep evaluation cases separate from development fixtures and frozen datasets.

Report source availability; eligible field coverage; body-versus-metadata rate; relevant-passage yield; duplicate-origin ratio; citation validity and entailment; unsupported-assertion rate; resolution and abstention rates; freshness/temporal alignment; per-mode p50/p95 latency, requests, bytes, concurrency and cancellation behavior. Distinguish direct fetch from search discovery and cached/replayed observations from fresh traffic. If recall lacks an annotated relevant-document denominator, mark it NOT MEASURED.

Run the [required offline commands](../../AGENTS.md), all Node frontend scripts, frozen hash checks, persistence smoke and rollback compatibility, live bounded source audits and exact-head hosted CI. Add browser tests at narrow/mobile/desktop widths with real populated, empty and failure states, manual accessibility review and user tasks such as finding a contradiction and opening its passage. Browser-unavailable checks remain UNVERIFIED, never PASS.

Acceptance requires no manufactured evidence, dates, citations, totals or authenticated-identity labels; no lost provenance through API/UI; no silent content truncation or false completeness; meaningful improvement against the locked baseline; and an honest remaining-gap report. Thresholds needing a baseline must be decided before tuning, not invented after seeing held-out outcomes.

## Delivery sequence and ownership

Deliver the first complete vertical slice through Scout plus web/RSS and SEC where credentials permit: real document → aligned fact/passage → grounded finding → report → frontend → independent case. Then extend shared contracts and inspection to Trending, BrandShield and Personal Watch, while deepening their most useful source paths. Keep unrelated protected operations routable and regression-covered throughout. Missing optional credentials need not stop independent work; that capability remains explicitly unverified.

Each slice must leave code/test pointers, sanitized new proof locations, measured results, exact Git/CI identity, decisions and an agent handoff. Maintain a single integration owner or non-overlapping worktrees to prevent concurrent agents sweeping each other's changes into commits. Complete and review the existing documentation checkpoint before advertising documentation closeout.

No merge, deployment, paid service activation, production-secret modification, auth/CAPTCHA/paywall bypass or historical data repair is authorized by this plan. Preserve frozen benchmarks, protected dossiers, research, historical artifacts, scrapers and compatibility shims. The original archive's 55 malformed dossiers remain a separate protected-data owner task.

## Plan verification record

This planning task read the independent-review handoff, review report, extraction matrix and relevant schema code at the observed review branch. `git diff --check` and relative-link existence checks are recorded at handoff; there was no implementation, new live-provider probe, browser run or fresh CI run for this plan. Earlier validation evidence remains dated and must not be advertised as testing these proposed features.
