# Adobe post-fix verification handoff — 2026-10-20

[Report, exact funnel and remaining code owners](../testing/ADOBE_POSTFIX_LIVE_CHECK_2026-10-20.md)
and [selected proof](../testing/evidence/2026-10-20_adobe_postfix/README.md).
Read the [prior implementation handoff](2026-10-20_AUTONOMOUS_DISCOVERY_REPAIR.md),
AGENTS and current Git diff before editing. The isolated implementation worktree
is `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, plus preserved uncommitted work.

## What changed in acceptance

User approved one post-fix Adobe investigation, 120 seconds, six deep-reader
attempts, AI disabled, no retry/deployment. It ran once in **44.39 seconds** with
five attempts. **Autonomous native article acquisition is now demonstrated for
this one case:** query → newsroom → observed article link → 842-word / 5.957KB
native HTTP capture, with acquisition IDs and resolved report citation intact.
No manual URL. Asset links rejected. Two other captures are background context.

**Research quality remains unaccepted.** The financial objective gate skips the
main leadership-announcement paragraph and selects a 43-character earnings-call
heading instead. Metadata retains the actual page title, but the record/finding
title stays `Read more`. Body date is not structured publication metadata, and
CMS labels remain in the capture. These are downstream defects, not absent raw
text or a frontend citation-loss issue. No application/test/script fixes were
made in this verification-only turn; changes are documentation/new proof only.

Application fingerprint unchanged:
`93fa5595adbebce17f21b3ecbce9797cc843f0361b748ae3d5402ea83dd26fc8`.
No commit, push, merge, deployment, credential change or live AI call.
The one-case authorization is consumed. Do not reuse it for further live trials.

## Actual commands/results

The existing terminal runner used `--case scout:Adobe --timeout-seconds 120
--max-deep-reads 6 --allow-live`, existing server env and a new temp output path;
no `--allow-live-ai`. Exit 0; one real local SSE result, no error event.

Re-executed full suite: **1,532 passed / 51.46s**, exit 0. Fast:
**1,324 passed / 34.43s**, exit 0. Fatal flake8, nine Node scripts, frozen verifier,
protected-path diff, smoke and offline persistence/readers all exit 0.
Historical archive and deployed rollback remain NOT_VERIFIED. See the report for
actual command forms; this is a command/result record, not a fabricated transcript.

Read-only summarizer and exact fresh-SSE Chromium replay exit 0. Three widths
(320/390/1440) match 1 finding / 3 source cards / 19 discovery cards, no overflow
or uncaught page exception. Visual desktop inspection confirms the weak heading.
Readiness is a stub; external/API calls blocked. No new source acquisition.
Hosted CI/production and full accessibility were not verified.

Temporary tree basename `aegis-adobe-postfix-d2231ffc-f101-4356-82d6-2a7a965e0eeb`
contains original JSON/events, isolated dossiers, logs and screenshots. System-temp
data can expire; selected sanitized measurements/source hashes are durable.

## Recommended next authorized implementation

Use the saved article body for offline regressions of substantive paragraph versus
heading selection, corporate-event objectives, acquisition-title reconciliation
and explicit date semantics. Do not hardcode Adobe, delete raw text, invent dates,
weaken support gates or count a resolved citation as entailment. Further live
cases require new bounded permission. Overall discovery reliability, Dyson,
other agents, independent accuracy and release gates remain open.
