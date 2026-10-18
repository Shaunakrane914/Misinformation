# Research-quality completion checkpoint — 2026-10-18

**Overall: PARTIAL. Independent accuracy acceptance and release remain pending.**
This is a focused specialist-intelligence checkpoint, not another architecture
phase. No additional websites, agents or frontend redesign were introduced.

## Observed scope

Worktree `.scratch/phase9-remediation-20261016`, branch
`feat/continuous-source-intelligence-20261017`, base
`314bf17697f1424bf9aa0d60704b42d87bf8e244`, plus existing and new local changes.
The model migration and Netlify removals predated this checkpoint and were
preserved. A branch name/old hosted CI result does not validate these changes.

AI generation was disabled throughout these investigations. There were **zero
live generation/model-list calls** in this checkpoint. Twelve normal local
investigations (two five-case specialist passes plus Scout/Trending) and four
separate guided-source investigations used normal acquisition. Each application
investigation can fan out into multiple provider queries; these are not counts
of upstream HTTP requests. Subsequent polish and browser checks reused saved
bytes/events, with no further acquisition. No 52-operation availability sweep.

Normal source checks used isolated SQLite/dossier directories, no notifications,
no Supabase writes, no background ingestion, real acquisition and no mock LLM.
Existing approval/credential gates were not enabled or weakened.

## What actual source captures established

Words count whitespace tokens in one retained native content/snippet per record;
KB is UTF-8 bytes / 1,000. These are not useful-fact counts or deduplicated web
coverage. Source size alone is not acceptance.

| Mode | Agent/input | Records | Words | KB | Research-quality observation |
| --- | --- | ---: | ---: | ---: | --- |
| Normal second specialist pass | BrandShield / Adidas counterfeit | 2 | 2,043 | 12.663 | Storefront plus encyclopedia; historical corporate text must not become a current complaint |
| Normal second specialist pass | BrandShield / Apple phishing | 3 | 692 | 4.221 | Home/support pages; no qualified incident, not proof of safety |
| Normal second specialist pass | Personal / Tim Cook | 1 | 8 | 0.059 | Profile only; normal discovery remains inadequate |
| Normal second specialist pass | Personal / Satya Nadella | 2 | 1,048 | 6.004 | Acquired joint Microsoft statement plus profile; speaker sections now retained separately |
| Normal second specialist pass | Personal / Fei-Fei Li | 1 | 18 | 0.185 | Profile only; unrelated equestrian source rejected, but general acquisition still inadequate |
| Normal local | Scout / MSFT | 6 | 5,555 | 35.649 | Mostly publisher material; no acquired filing established in the funnel and no claim-adjudication acceptance |
| Normal local | Trending / AMD | 0 | 0 | 0 | Three discovery leads, no acquired body; deadlines/qualification failures remain visible |
| Guided source URL | BrandShield / Nike / DOJ report | 4 | 1,518 | 11.330 | DOJ capture truncated at 4,000 characters before incident body; wrapper title/navigation are not incident evidence |
| Guided source URL | BrandShield / Apple support advisory | 3 | 948 | 5.839 | Protective advice, not an attacker URL; no authenticated threat established |
| Guided source URL | Personal / Tim Cook / Apple release | 1 | 689 | 4.046 | Substantive reported quotation retained; guided acquisition is not success of one-line discovery |
| Guided source URL | Personal / Fei-Fei Li / Substack root | 1 | 29 | 0.179 | Subscription/landing text only; not a substantive statement |

The earlier first specialist pass retained the unrelated `inside.fei.org` page
and promoted Adidas encyclopedia text into a customer complaint. Offline
reprocessing removes both errors without deleting the raw captures. The
Microsoft statement is a public observation, not proof of identity safety or
synthetic-media detection. Tim's reported quotation remains `UNVERIFIED`, not
authenticated identity or independently corroborated truth.

### Fixes supported by these observations and calibration regressions

- BrandShield uses complete selected paragraphs rather than an entire noisy
  body. Protective notices, reader-wrapper metadata, catalogs, disputed claims
  and encyclopedia background do not become attacker/incident findings.
  Explicit suspicious replica offers and credential solicitations remain
  investigable. Synthetic positive fixtures are **calibration**, not proof of
  actual threat discovery.
- A captured enforcement report is labeled as reporting, not the attacker's
  URL. No enforcement body was actually retained in the guided DOJ capture;
  that sample therefore does **not** prove positive enforcement interpretation.
- Personal discovery includes a bounded public-statement search. Full-name
  matching no longer counts repeated first-name tokens as corroborating context.
  Body context may qualify an acquired article, never a missing-body snippet.
- Observed speaker labels and unambiguous reported surname quotations can link
  paragraphs to a subject. A following speaker's section is not assigned to the
  first speaker. These links do not authenticate the speaker.
- Passage projections prioritize relevance before their 16-paragraph bound;
  exact offsets and complete qualifications remain inspectable.
- Equivalent monetary scales compare as Decimal quantities when reporting
  context/currency are comparable. Different currencies and guidance ranges
  are not silently converted into matching actual results.
- Trending no longer marks a headline `VERIFIED` merely because of publisher
  tier or `CONTRADICTED` because it contains “debunked.” Acquisition-count
  changes are not labeled audience reach or independently verified signals.
- Pure URL requests no longer become propositions. Specialist coverage briefs
  recognize observed statements and distinguish the subject from a query URL.

## Browser and release evidence

The final locked capture replay uses MSFT, AMD, Apple phishing and the guided
Tim source. It sends saved SSE through actual local buttons and native/shared
renderers at **320, 390 and 1440px**. All twelve states match returned finding,
acquired-source and discovery-card counts, with no missing finding strings,
horizontal overflow or uncaught JavaScript exception. Evidence inspection opens
with keyboard Enter in the nine states that contain an acquired record.
The four Google Fonts failures were intentionally blocked external resources.

Selected screenshots were visually inspected; they are not a full accessibility
or visual acceptance. The first Trending mobile capture contains a large blank
lower viewport area; keep it as a capture limitation, not fabricated proof of a
complete painted page. Desktop corroboration and DOM checks are recorded. Long
source URLs and long context previews remain a readability limitation.

An earlier replay mistakenly overwrote Trending's required query with an empty
optional override and displayed `General`. That run is superseded, retained in
temporary diagnostics, and excluded from the final measurements. The harness
now omits empty overrides; it does not reacquire or fabricate sources.

Read-only deployment check: Cloudflare `aegis-nav.js` returned HTTP 200 and
contains the Render backend origin. Render `/health` timed out after ten seconds
(earlier eight-second probes also timed out). This does not prove sleeping,
outage, successful streaming or deployed parity. No deployed investigation was
sent because generation-disabled server configuration was not established.

Local advisory policy is pinned to `gemini-3.5-flash-lite`, with 160 output
tokens and existing shared budget enforcement. This checkpoint did not repeat
the prior live model verification or establish production configuration parity.
Backend legacy compatibility aliases were intentionally preserved; deleted
Netlify function files are not a reason to delete public API compatibility.

## Historical persistence boundary

The original archive was inspected read-only through the rollback validator:
**2,445 legacy-unsealed/readable files and 55 failed files; zero cryptographically
verified files.** Overall `HISTORICAL_ARCHIVE_FAIL` (exit 1). Readability is not
cryptographic integrity. Originals were not repaired or overwritten.
The isolated worktree's fresh persistence checks pass, but cannot establish
recovery of the original archive or an actual deployed previous-version rollback.

## Acceptance and next bounded milestones

1. **Specialized intelligence (days 1–4):** prove real positive and negative
   BrandShield cases with acquired incident bodies; improve Tim/unfamiliar-person
   discovery without special-casing the examples. Keep the DOJ cutoff and
   Google News wrapper failures explicit. No storefront/profile-only demos.
2. **Independent research accuracy (days 5–9):** a reviewer chooses and freezes
   12 new cases per agent using the [reviewer packet](RESEARCH_QUALITY_REVIEWER_PACKET_2026-10-18.md).
   Score decisive errors, justified abstentions, retrieval and citation spans;
   manually review entailment/usefulness. Do not tune on held-out answers.
3. **Bounded v1 release preparation (days 10–14):** verify actual Cloudflare/Render
   routes, SSE, source inspection, strict AI controls and basic accessibility;
   document archive limitations and perform owner-controlled staging rollback.
   Only then request publication/merge/deployment authority for verified work,
   prepare a demo and freeze nonessential development.

This is a proposed timebox, not a claim that future work or independent labels
already exist. If the gates are unmet, retain a clearly limited beta; do not
declare complete misinformation detection to meet a calendar date.

See [proof index](evidence/2026-10-18_research_quality_completion/README.md) and
[implementation/testing handoff](../handoffs/2026-10-18_RESEARCH_QUALITY_COMPLETION.md).
